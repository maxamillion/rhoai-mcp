"""LLM agent wrapper for RHOAI MCP evaluations.

Implements an agent loop that sends tasks and tool schemas to an
OpenAI-compatible LLM, processes tool calls via the MCP harness,
and records tool calls and conversation turns for DeepEval metrics.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from openai import AsyncOpenAI

from evals.config import EvalConfig, LLMProvider
from evals.mcp_harness import MCPHarness

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """Record of a single tool call made by the agent."""

    name: str
    arguments: dict[str, Any]
    result: str


@dataclass
class AgentResult:
    """Result of running an agent on a task."""

    task: str
    final_output: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    messages: list[dict[str, Any]] = field(default_factory=list)
    turns: int = 0

    @property
    def tool_names_used(self) -> list[str]:
        """Get the list of tool names called, in order."""
        return [tc.name for tc in self.tool_calls]


class MCPAgent:
    """LLM agent that interacts with the MCP server via tool calling.

    Uses the OpenAI Python client, which is compatible with OpenAI,
    vLLM, and Azure endpoints.
    """

    def __init__(self, config: EvalConfig, harness: MCPHarness) -> None:
        self._config = config
        self._harness = harness
        self._client = self._create_client()

    def _create_client(self) -> AsyncOpenAI:
        """Create an OpenAI-compatible async client."""
        kwargs: dict[str, Any] = {"api_key": self._config.llm_api_key}

        if self._config.llm_base_url:
            kwargs["base_url"] = self._config.llm_base_url
        elif self._config.llm_provider == LLMProvider.VLLM:
            raise ValueError("llm_base_url is required for vLLM provider")

        return AsyncOpenAI(**kwargs)

    async def run(self, task: str) -> AgentResult:
        """Run the agent on a task until completion or max turns.

        The agent loop:
        1. Send the task + tool schemas to the LLM
        2. If the LLM returns tool calls, execute them and feed results back
        3. Repeat until the LLM responds with plain text or max turns reached

        Args:
            task: The natural language task for the agent to perform.

        Returns:
            AgentResult with tool calls, messages, and final output.
        """
        tools = self._harness.get_openai_tools()
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are an AI assistant interacting with a Red Hat OpenShift AI "
                    "(RHOAI) environment through MCP tools. Use the available tools "
                    "to complete the user's request. Call tools as needed, then provide "
                    "a final summary of what you found or accomplished."
                ),
            },
            {"role": "user", "content": task},
        ]

        result = AgentResult(task=task, final_output="", messages=messages)
        max_turns = self._config.max_agent_turns

        for turn in range(max_turns):
            result.turns = turn + 1
            logger.debug(f"Agent turn {turn + 1}/{max_turns}")

            response = await self._client.chat.completions.create(
                model=self._config.llm_model,
                messages=messages,
                tools=tools if tools else None,
            )

            choice = response.choices[0]
            message = choice.message

            # Add assistant message to history
            messages.append(message.model_dump(exclude_none=True))

            # If the model didn't call any tools, we're done
            if not message.tool_calls:
                result.final_output = message.content or ""
                break

            # Process each tool call
            for tool_call in message.tool_calls:
                fn = tool_call.function
                tool_name = fn.name
                try:
                    tool_args = json.loads(fn.arguments) if fn.arguments else {}
                except json.JSONDecodeError:
                    tool_args = {}

                logger.debug(f"Calling tool: {tool_name}({tool_args})")
                tool_result = await self._harness.call_tool(tool_name, tool_args)

                tc = ToolCall(name=tool_name, arguments=tool_args, result=tool_result)
                result.tool_calls.append(tc)

                # Add tool result to conversation
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result,
                    }
                )
        else:
            # Max turns reached without a final text response
            result.final_output = (
                f"Agent reached maximum turns ({max_turns}) without completing the task."
            )

        result.messages = messages
        return result
