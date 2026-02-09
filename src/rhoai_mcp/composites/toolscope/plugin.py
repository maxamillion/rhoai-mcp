"""ToolScope plugin for semantic tool search."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rhoai_mcp.composites.toolscope.manager import ToolScopeManager
from rhoai_mcp.hooks import hookimpl
from rhoai_mcp.plugin import BasePlugin, PluginMetadata

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from rhoai_mcp.server import RHOAIServer


class ToolScopePlugin(BasePlugin):
    """Plugin providing semantic tool search with ToolScope."""

    def __init__(self) -> None:
        super().__init__(
            PluginMetadata(
                name="toolscope",
                version="1.0.0",
                description="Semantic tool search using ToolScope embeddings",
                maintainer="rhoai-mcp@redhat.com",
                requires_crds=[],
            )
        )
        self._manager: ToolScopeManager | None = None

    @property
    def manager(self) -> ToolScopeManager | None:
        """Get the ToolScope manager instance."""
        return self._manager

    @hookimpl
    def rhoai_register_tools(self, mcp: FastMCP, server: RHOAIServer) -> None:  # noqa: ARG002
        """Initialize manager (tools registered later in post_registration)."""
        if server.config.toolscope_enabled:
            self._manager = ToolScopeManager(server.config)

    @hookimpl
    def rhoai_post_registration(self, mcp: FastMCP, server: RHOAIServer) -> None:  # noqa: ARG002
        """Build ToolScope index after all tools are registered."""
        if self._manager:
            self._manager.initialize(mcp)

    @hookimpl
    def rhoai_health_check(self, server: RHOAIServer) -> tuple[bool, str]:
        """Check ToolScope health status."""
        if not server.config.toolscope_enabled:
            return True, "ToolScope disabled"
        if self._manager and self._manager.is_initialized:
            return True, f"ToolScope ready ({self._manager.tool_count} tools indexed)"
        return True, "ToolScope not initialized (fallback to keyword search)"
