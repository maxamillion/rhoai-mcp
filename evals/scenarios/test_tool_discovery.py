"""Scenario: Tool Discovery.

Tests that the agent can use meta tools to discover which tools
are available for a given workflow.
"""

from __future__ import annotations

import pytest
from deepeval import evaluate

from evals.agent import MCPAgent
from evals.config import EvalConfig
from evals.deepeval_helpers import build_mcp_server, result_to_single_turn_test_case
from evals.mcp_harness import MCPHarness
from evals.metrics.config import create_mcp_use_metric


@pytest.mark.eval
class TestToolDiscovery:
    """Evaluate agent's ability to discover relevant tools."""

    TASK = (
        "I want to set up a new project with storage, an S3 data connection, "
        "and a workbench. What tools should I use and in what order?"
    )

    @pytest.mark.eval
    async def test_tool_discovery(
        self,
        eval_config: EvalConfig,
        harness: MCPHarness,
        agent: MCPAgent,
    ) -> None:
        """Agent should use meta/discovery tools to suggest a workflow."""
        result = await agent.run(self.TASK)

        # The agent should provide tool recommendations
        assert result.final_output, "Agent should provide tool recommendations"

        mcp_server = build_mcp_server(harness)
        test_case = result_to_single_turn_test_case(result, mcp_server)

        metrics = [create_mcp_use_metric(eval_config)]

        eval_result = evaluate(
            test_cases=[test_case],
            metrics=metrics,
            run_async=True,
            print_results=True,
        )

        for metric_result in eval_result.test_results[0].metrics_data:
            assert metric_result.success, (
                f"Metric {metric_result.metric_name} failed: {metric_result.reason}"
            )
