"""Training tools for RHOAI MCP.

This module provides a single register_tools function that delegates to all
training tool submodules (domain-specific only).

Composite training tools (planning, unified, storage) have been moved to
rhoai_mcp.composites.training and are registered separately.

Most training operations are consolidated into the unified training() tool
in composites/training/unified.py. Domain tools here provide only non-duplicated
functionality (cluster resources, runtimes, container training, failure analysis,
wait-for-completion, job spec).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from rhoai_mcp.server import RHOAIServer


def register_tools(mcp: FastMCP, server: RHOAIServer) -> None:
    """Register domain-specific training tools with the MCP server.

    This function delegates to the individual tool submodules to register
    their specific tools. Composite tools (planning, unified, storage) are
    registered separately via the composites registry.

    Args:
        mcp: The FastMCP server instance.
        server: The RHOAIServer instance providing configuration and K8s access.
    """
    from rhoai_mcp.domains.training.tools import (
        discovery,
        lifecycle,
        runtimes,
        training,
    )

    # Register domain-specific tools only
    # Composite tools are in rhoai_mcp.composites.training
    discovery.register_tools(mcp, server)
    lifecycle.register_tools(mcp, server)
    runtimes.register_tools(mcp, server)
    training.register_tools(mcp, server)
