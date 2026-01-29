"""Agent executor for benchmarks using Claude via Anthropic API.

This module provides an agent-based executor that uses Claude to make
real decisions about which tools to call, executing them via an MCP server.
"""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING, Any

from rhoai_mcp.benchmarks.golden_paths import get_all_cases, get_quick_cases
from rhoai_mcp.benchmarks.runner import BenchmarkRunner

if TYPE_CHECKING:
    from rhoai_mcp.config import RHOAIConfig

logger = logging.getLogger(__name__)

# Maximum tool calls per task to prevent runaway loops
MAX_TOOL_CALLS = 20


class AnthropicAgentError(Exception):
    """Error from the Anthropic agent executor."""

    pass


def check_agent_prerequisites(config: RHOAIConfig) -> tuple[bool, str | None]:
    """Check if prerequisites for agent mode are met.

    Args:
        config: The RHOAI configuration.

    Returns:
        Tuple of (ok, error_message).
    """
    # Check for anthropic package
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False, "anthropic package not installed. Run: pip install anthropic"

    # Check for API key
    if not config.anthropic_api_key:
        return False, (
            "Anthropic API key not configured. "
            "Set RHOAI_MCP_ANTHROPIC_API_KEY environment variable."
        )

    return True, None


def check_server_available(server_url: str, timeout: float = 5.0) -> tuple[bool, str | None]:
    """Check if the MCP server is available.

    Args:
        server_url: The server URL to check.
        timeout: Request timeout in seconds.

    Returns:
        Tuple of (available, error_message).
    """
    try:
        import httpx

        # Try to connect to the server
        with httpx.Client(timeout=timeout) as client:
            response = client.get(f"{server_url}/health")
            if response.status_code == 200:
                return True, None
            return False, f"Server returned status {response.status_code}"
    except httpx.ConnectError:
        return False, f"Cannot connect to MCP server at {server_url}"
    except Exception as e:
        return False, f"Error checking server: {e}"


class MCPToolCaller:
    """Calls MCP tools via HTTP requests to a running server."""

    def __init__(self, server_url: str) -> None:
        """Initialize the tool caller.

        Args:
            server_url: Base URL of the MCP server.
        """
        self._server_url = server_url.rstrip("/")
        self._tools: list[dict[str, Any]] = []

    def fetch_tools(self) -> list[dict[str, Any]]:
        """Fetch available tools from the MCP server.

        Returns:
            List of tool definitions.
        """
        import httpx

        with httpx.Client(timeout=30.0) as client:
            response = client.get(f"{self._server_url}/tools")
            response.raise_for_status()
            data = response.json()
            self._tools = data.get("tools", [])
            return self._tools

    def get_tool_definitions_for_claude(self) -> list[dict[str, Any]]:
        """Convert MCP tool definitions to Claude tool format.

        Returns:
            List of tool definitions in Claude format.
        """
        claude_tools = []
        for tool in self._tools:
            claude_tool = {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "input_schema": tool.get("inputSchema", {"type": "object", "properties": {}}),
            }
            claude_tools.append(claude_tool)
        return claude_tools

    def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> tuple[Any, float, bool, str | None]:
        """Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call.
            arguments: Tool arguments.

        Returns:
            Tuple of (result, duration_ms, success, error).
        """
        import httpx

        start_time = time.time()

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self._server_url}/tools/{tool_name}",
                    json={"arguments": arguments},
                )
                duration_ms = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    result = response.json()
                    return result, duration_ms, True, None
                else:
                    error = f"Tool call failed: {response.status_code} - {response.text}"
                    return None, duration_ms, False, error

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return None, duration_ms, False, str(e)


class AnthropicAgentExecutor:
    """Executes benchmark tasks using Claude via Anthropic API."""

    def __init__(
        self,
        api_key: str,
        model: str,
        server_url: str,
    ) -> None:
        """Initialize the agent executor.

        Args:
            api_key: Anthropic API key.
            model: Claude model identifier.
            server_url: URL of the MCP server.
        """
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._tool_caller = MCPToolCaller(server_url)

    def execute(self, prompt: str) -> list[dict[str, Any]]:
        """Execute a task and return the tool calls made.

        Args:
            prompt: The task prompt.

        Returns:
            List of tool call records for benchmark scoring.
        """
        # Fetch available tools
        try:
            self._tool_caller.fetch_tools()
        except Exception as e:
            logger.error(f"Failed to fetch tools: {e}")
            return []

        tools = self._tool_caller.get_tool_definitions_for_claude()
        if not tools:
            logger.warning("No tools available from MCP server")
            return []

        tool_calls: list[dict[str, Any]] = []

        # Build initial messages
        messages: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": prompt,
            }
        ]

        system_prompt = (
            "You are an AI assistant that helps users manage Red Hat OpenShift AI resources. "
            "Use the available tools to complete the user's request. "
            "Be efficient and use the minimum number of tool calls needed."
        )

        # Conversation loop
        for _ in range(MAX_TOOL_CALLS):
            try:
                response = self._client.messages.create(
                    model=self._model,
                    max_tokens=4096,
                    system=system_prompt,
                    tools=tools,  # type: ignore[arg-type]
                    messages=messages,  # type: ignore[arg-type]
                )
            except Exception as e:
                logger.error(f"Anthropic API error: {e}")
                break

            # Process response
            assistant_content = response.content
            messages.append({"role": "assistant", "content": assistant_content})

            # Check for tool use
            tool_use_blocks = [b for b in assistant_content if b.type == "tool_use"]

            if not tool_use_blocks:
                # No more tool calls, we're done
                break

            # Process each tool call
            tool_results = []
            for tool_use in tool_use_blocks:
                tool_name = tool_use.name
                arguments = tool_use.input if isinstance(tool_use.input, dict) else {}

                logger.debug(f"Calling tool: {tool_name} with {arguments}")

                result, duration_ms, success, error = self._tool_caller.call_tool(
                    tool_name, arguments
                )

                # Record the call
                tool_calls.append({
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "result": result,
                    "duration_ms": duration_ms,
                    "success": success,
                    "error": error,
                })

                # Build result for Claude
                if success:
                    result_text = json.dumps(result, indent=2) if result else "Success"
                else:
                    result_text = f"Error: {error}"

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result_text,
                })

            # Add tool results to conversation
            messages.append({"role": "user", "content": tool_results})

            # Check stop reason
            if response.stop_reason == "end_turn":
                break

        return tool_calls


def create_agent_executor(config: RHOAIConfig) -> AnthropicAgentExecutor:
    """Factory function to create an agent executor.

    Args:
        config: The RHOAI configuration.

    Returns:
        A configured AnthropicAgentExecutor.

    Raises:
        AnthropicAgentError: If prerequisites are not met.
    """
    ok, error = check_agent_prerequisites(config)
    if not ok:
        raise AnthropicAgentError(error or "Prerequisites not met")

    if not config.anthropic_api_key:
        raise AnthropicAgentError("Anthropic API key not configured")

    return AnthropicAgentExecutor(
        api_key=config.anthropic_api_key,
        model=config.anthropic_model,
        server_url=config.benchmark_server_url,
    )


def run_agent_benchmarks(
    config: RHOAIConfig,
    quick_only: bool = False,
    pass_threshold: float = 0.70,
) -> dict[str, Any]:
    """Run benchmarks using the agent executor.

    Args:
        config: The RHOAI configuration.
        quick_only: Only run cases tagged 'quick'.
        pass_threshold: Minimum score to pass.

    Returns:
        Dictionary with benchmark results.
    """
    # Check prerequisites
    ok, error = check_agent_prerequisites(config)
    if not ok:
        return {
            "error": error,
            "total_cases": 0,
            "passed_cases": 0,
            "pass_rate": 0.0,
            "average_score": 0.0,
            "grade": "F",
            "results": [],
        }

    # Check server availability
    ok, error = check_server_available(config.benchmark_server_url)
    if not ok:
        return {
            "error": f"MCP server not available: {error}",
            "total_cases": 0,
            "passed_cases": 0,
            "pass_rate": 0.0,
            "average_score": 0.0,
            "grade": "F",
            "results": [],
        }

    # Create executor
    try:
        executor = create_agent_executor(config)
    except AnthropicAgentError as e:
        return {
            "error": str(e),
            "total_cases": 0,
            "passed_cases": 0,
            "pass_rate": 0.0,
            "average_score": 0.0,
            "grade": "F",
            "results": [],
        }

    # Get cases to run
    cases = get_quick_cases() if quick_only else get_all_cases()

    # Run benchmarks
    runner = BenchmarkRunner(pass_threshold=pass_threshold)
    results_list = []

    for case in cases:
        logger.info(f"Running agent benchmark: {case.name}")
        result = runner.run_case(case, executor.execute)
        results_list.append(result)

        score_str = f"{result.score.overall_score:.2f}" if result.score else "N/A"
        logger.info(
            f"  {'PASS' if result.passed else 'FAIL'} (score: {score_str})"
        )

    # Compute statistics
    total = len(results_list)
    passed = sum(1 for r in results_list if r.passed)
    scores = [r.score.overall_score for r in results_list if r.score]
    avg_score = sum(scores) / len(scores) if scores else 0.0

    # Compute grade
    if avg_score >= 0.90:
        grade = "A"
    elif avg_score >= 0.80:
        grade = "B"
    elif avg_score >= 0.70:
        grade = "C"
    elif avg_score >= 0.60:
        grade = "D"
    else:
        grade = "F"

    return {
        "total_cases": total,
        "passed_cases": passed,
        "pass_rate": passed / total if total > 0 else 0.0,
        "average_score": avg_score,
        "grade": grade,
        "results": [r.to_dict() for r in results_list],
    }
