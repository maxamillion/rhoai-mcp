"""Small model optimizer plugin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rhoai_mcp.composites.optimizer.manager import SmallModelOptimizer
from rhoai_mcp.config import SmallModelMode
from rhoai_mcp.hooks import hookimpl
from rhoai_mcp.plugin import BasePlugin, PluginMetadata

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from rhoai_mcp.server import RHOAIServer


class SmallModelOptimizerPlugin(BasePlugin):
    """Plugin for small model tool filtering.

    Installs the SmallModelOptimizer after all tools are registered,
    enabling dynamic tool filtering for small language models.
    """

    def __init__(self) -> None:
        super().__init__(
            PluginMetadata(
                name="small-model-optimizer",
                version="1.0.0",
                description="Dynamic tool filtering for small LLMs",
                maintainer="rhoai-mcp@redhat.com",
                requires_crds=[],
            )
        )
        self._optimizer: SmallModelOptimizer | None = None

    @property
    def optimizer(self) -> SmallModelOptimizer | None:
        """Get the optimizer instance."""
        return self._optimizer

    @hookimpl
    def rhoai_post_registration(self, mcp: FastMCP, server: RHOAIServer) -> None:
        """Install optimizer after all tools registered."""
        if server.config.small_model_mode == SmallModelMode.NONE:
            return

        # Get ToolScope manager
        toolscope_manager = self._get_toolscope_manager(server)

        self._optimizer = SmallModelOptimizer(server.config, toolscope_manager)
        self._optimizer.install(mcp)

    def _get_toolscope_manager(self, server: RHOAIServer) -> Any:
        """Get ToolScope manager from plugins."""
        try:
            from rhoai_mcp.composites.toolscope.plugin import ToolScopePlugin

            for plugin in server.plugins.values():
                if isinstance(plugin, ToolScopePlugin) and plugin.manager:
                    return plugin.manager
        except ImportError:
            pass
        return None

    @hookimpl
    def rhoai_health_check(self, server: RHOAIServer) -> tuple[bool, str]:
        """Check optimizer health status."""
        if server.config.small_model_mode == SmallModelMode.NONE:
            return True, "Small model optimization disabled"
        if self._optimizer and self._optimizer.is_installed:
            visible = self._optimizer.get_visible_tool_count()
            total = self._optimizer.get_total_tool_count()
            return True, (
                f"Optimizer active (mode={server.config.small_model_mode.value}, "
                f"{visible}/{total} tools visible)"
            )
        return True, "Optimizer not installed"
