"""Shared pytest fixtures for RHOAI MCP evaluations."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from evals.config import ClusterMode, EvalConfig

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from evals.agent import MCPAgent
    from evals.mcp_harness import MCPHarness


@pytest.fixture(scope="session")
def eval_config() -> EvalConfig:
    """Load evaluation configuration from environment."""
    return EvalConfig()


@pytest.fixture(scope="session")
def is_mock(eval_config: EvalConfig) -> bool:
    """Whether we're running against a mock cluster."""
    return eval_config.cluster_mode == ClusterMode.MOCK


@pytest.fixture
async def harness(eval_config: EvalConfig) -> AsyncIterator[MCPHarness]:
    """Create an MCP harness with the configured cluster mode."""
    from evals.mcp_harness import MCPHarness

    async with MCPHarness.running(eval_config) as h:
        yield h


@pytest.fixture
async def agent(eval_config: EvalConfig, harness: MCPHarness) -> MCPAgent:
    """Create an LLM agent connected to the MCP harness."""
    from evals.agent import MCPAgent

    return MCPAgent(config=eval_config, harness=harness)
