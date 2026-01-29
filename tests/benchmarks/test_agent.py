"""Tests for agent mode benchmarks."""

from unittest.mock import MagicMock, patch

import pytest

from rhoai_mcp.benchmarks.agent import (
    MAX_TOOL_CALLS,
    AnthropicAgentError,
    AnthropicAgentExecutor,
    MCPToolCaller,
    check_agent_prerequisites,
    check_server_available,
    create_agent_executor,
    run_agent_benchmarks,
)
from rhoai_mcp.config import RHOAIConfig


class TestCheckAgentPrerequisites:
    """Test check_agent_prerequisites function."""

    def test_missing_api_key(self) -> None:
        """Test error when API key is not configured."""
        config = RHOAIConfig(anthropic_api_key=None)

        ok, error = check_agent_prerequisites(config)

        assert ok is False
        assert "API key" in (error or "")

    def test_valid_config(self) -> None:
        """Test success with valid configuration."""
        config = RHOAIConfig(anthropic_api_key="sk-ant-test")

        ok, error = check_agent_prerequisites(config)

        assert ok is True
        assert error is None


class TestCheckServerAvailable:
    """Test check_server_available function."""

    def test_server_available(self) -> None:
        """Test successful server check."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            ok, error = check_server_available("http://localhost:8000")

        assert ok is True
        assert error is None

    def test_server_returns_error(self) -> None:
        """Test server returning error status."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            ok, error = check_server_available("http://localhost:8000")

        assert ok is False
        assert "500" in (error or "")

    def test_server_connection_error(self) -> None:
        """Test connection error."""
        import httpx

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = httpx.ConnectError(
                "Connection refused"
            )

            ok, error = check_server_available("http://localhost:8000")

        assert ok is False
        assert "Cannot connect" in (error or "")


class TestMCPToolCaller:
    """Test MCPToolCaller class."""

    def test_fetch_tools(self) -> None:
        """Test fetching tools from server."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "tools": [
                {"name": "tool_a", "description": "Tool A"},
                {"name": "tool_b", "description": "Tool B"},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            caller = MCPToolCaller("http://localhost:8000")
            tools = caller.fetch_tools()

        assert len(tools) == 2
        assert tools[0]["name"] == "tool_a"

    def test_get_tool_definitions_for_claude(self) -> None:
        """Test converting tools to Claude format."""
        caller = MCPToolCaller("http://localhost:8000")
        caller._tools = [
            {
                "name": "list_workbenches",
                "description": "List workbenches",
                "inputSchema": {
                    "type": "object",
                    "properties": {"namespace": {"type": "string"}},
                },
            }
        ]

        claude_tools = caller.get_tool_definitions_for_claude()

        assert len(claude_tools) == 1
        assert claude_tools[0]["name"] == "list_workbenches"
        assert "input_schema" in claude_tools[0]

    def test_call_tool_success(self) -> None:
        """Test successful tool call."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            caller = MCPToolCaller("http://localhost:8000")
            result, duration, success, error = caller.call_tool(
                "list_workbenches", {"namespace": "test"}
            )

        assert success is True
        assert result == {"result": "success"}
        assert error is None
        assert duration > 0

    def test_call_tool_failure(self) -> None:
        """Test failed tool call."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            caller = MCPToolCaller("http://localhost:8000")
            result, duration, success, error = caller.call_tool(
                "list_workbenches", {"namespace": "test"}
            )

        assert success is False
        assert error is not None
        assert "500" in error


class TestAnthropicAgentExecutor:
    """Test AnthropicAgentExecutor class."""

    def test_execute_no_tools(self) -> None:
        """Test execution when no tools available."""
        import anthropic

        with patch.object(anthropic, "Anthropic") as mock_client_cls:
            mock_client_cls.return_value = MagicMock()

            executor = AnthropicAgentExecutor(
                api_key="sk-ant-test",
                model="claude-sonnet-4-20250514",
                server_url="http://localhost:8000",
            )

            # Mock empty tools
            with patch.object(executor._tool_caller, "fetch_tools", return_value=[]):
                result = executor.execute("List workbenches")

        assert result == []

    def test_execute_with_tool_calls(self) -> None:
        """Test execution with tool calls."""
        import anthropic

        # Create mock tool use block
        mock_tool_use = MagicMock()
        mock_tool_use.type = "tool_use"
        mock_tool_use.name = "list_workbenches"
        mock_tool_use.id = "tool_1"
        mock_tool_use.input = {"namespace": "test"}

        # Create mock text block for final response
        mock_text = MagicMock()
        mock_text.type = "text"

        # Create mock responses
        mock_response_1 = MagicMock()
        mock_response_1.content = [mock_tool_use]
        mock_response_1.stop_reason = "tool_use"

        mock_response_2 = MagicMock()
        mock_response_2.content = [mock_text]
        mock_response_2.stop_reason = "end_turn"

        with patch.object(anthropic, "Anthropic") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.messages.create.side_effect = [mock_response_1, mock_response_2]

            executor = AnthropicAgentExecutor(
                api_key="sk-ant-test",
                model="claude-sonnet-4-20250514",
                server_url="http://localhost:8000",
            )

            # Mock tool caller
            executor._tool_caller._tools = [
                {"name": "list_workbenches", "description": "List workbenches"}
            ]

            with (
                patch.object(
                    executor._tool_caller,
                    "fetch_tools",
                    return_value=executor._tool_caller._tools,
                ),
                patch.object(
                    executor._tool_caller,
                    "call_tool",
                    return_value=({"workbenches": []}, 50.0, True, None),
                ),
            ):
                result = executor.execute("List workbenches")

        assert len(result) == 1
        assert result[0]["tool_name"] == "list_workbenches"
        assert result[0]["success"] is True


class TestCreateAgentExecutor:
    """Test create_agent_executor factory."""

    def test_missing_api_key(self) -> None:
        """Test error when API key is missing."""
        config = RHOAIConfig(anthropic_api_key=None)

        with pytest.raises(AnthropicAgentError, match="API key"):
            create_agent_executor(config)

    def test_creates_executor(self) -> None:
        """Test successful executor creation."""
        import anthropic

        config = RHOAIConfig(
            anthropic_api_key="sk-ant-test",
            anthropic_model="claude-sonnet-4-20250514",
            benchmark_server_url="http://localhost:8000",
        )

        with patch.object(anthropic, "Anthropic"):
            executor = create_agent_executor(config)

        assert isinstance(executor, AnthropicAgentExecutor)


class TestRunAgentBenchmarks:
    """Test run_agent_benchmarks function."""

    def test_returns_error_without_api_key(self) -> None:
        """Test error returned when API key is missing."""
        config = RHOAIConfig(anthropic_api_key=None)

        results = run_agent_benchmarks(config)

        assert "error" in results
        assert results["total_cases"] == 0
        assert results["grade"] == "F"

    def test_returns_error_when_server_unavailable(self) -> None:
        """Test error returned when server is unavailable."""
        config = RHOAIConfig(
            anthropic_api_key="sk-ant-test",
            benchmark_server_url="http://localhost:9999",
        )

        with patch(
            "rhoai_mcp.benchmarks.agent.check_server_available",
            return_value=(False, "Connection refused"),
        ):
            results = run_agent_benchmarks(config)

        assert "error" in results
        assert "not available" in results["error"]


class TestMaxToolCallsLimit:
    """Test that MAX_TOOL_CALLS prevents runaway loops."""

    def test_max_tool_calls_defined(self) -> None:
        """Verify MAX_TOOL_CALLS is set appropriately."""
        assert MAX_TOOL_CALLS == 20
        assert MAX_TOOL_CALLS > 0
        assert MAX_TOOL_CALLS <= 50  # Reasonable upper bound
