"""Small model optimizer for dynamic tool filtering."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from rhoai_mcp.composites.optimizer.context import ConversationContextBuffer
from rhoai_mcp.config import SmallModelMode

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from rhoai_mcp.composites.toolscope.manager import ToolScopeManager
    from rhoai_mcp.config import RHOAIConfig

logger = logging.getLogger(__name__)


class SmallModelOptimizer:
    """Dynamically filters tools exposed to MCP clients.

    Wraps FastMCP's list_tools method to return only a subset of
    relevant tools based on the configured mode and conversation context.
    This reduces token usage for small language models that struggle
    with large tool sets.
    """

    def __init__(
        self,
        config: RHOAIConfig,
        toolscope_manager: ToolScopeManager | None,
    ):
        """Initialize the optimizer.

        Args:
            config: RHOAI configuration with small model settings.
            toolscope_manager: Optional ToolScope manager for semantic search.
        """
        self._config = config
        self._toolscope = toolscope_manager
        self._context = ConversationContextBuffer(config.small_model_context_size)
        self._all_tools: dict[str, Any] = {}
        self._original_list_tools: Callable[[], list[Any]] | None = None
        self._installed = False

    @property
    def is_installed(self) -> bool:
        """Check if the optimizer has been installed."""
        return self._installed

    @property
    def context(self) -> ConversationContextBuffer:
        """Get the context buffer."""
        return self._context

    def install(self, mcp: FastMCP) -> None:
        """Install optimizer by wrapping list_tools.

        Args:
            mcp: The FastMCP server instance.
        """
        if self._config.small_model_mode == SmallModelMode.NONE:
            logger.info("Small model mode disabled, skipping optimizer install")
            return

        # Cache all tools from FastMCP
        if hasattr(mcp, "_tool_manager"):
            for tool in mcp._tool_manager.list_tools():
                self._all_tools[tool.name] = tool

        # Store original and replace using setattr to satisfy mypy
        self._original_list_tools = mcp._tool_manager.list_tools
        setattr(  # noqa: B010
            mcp._tool_manager, "list_tools", self._filtered_list_tools
        )

        self._installed = True
        logger.info(
            f"Small model optimizer installed: mode={self._config.small_model_mode.value}, "
            f"max_tools={self._config.small_model_max_tools}"
        )

    def _filtered_list_tools(self) -> list[Any]:
        """Return filtered tool list based on mode and context."""
        mode = self._config.small_model_mode

        if mode == SmallModelMode.NONE:
            return self._original_list_tools() if self._original_list_tools else []

        # Start with pinned tools
        pinned = set(self._config.small_model_pinned_tools)
        visible_names: set[str] = set()

        # Add pinned tools first
        for name in pinned:
            if name in self._all_tools:
                visible_names.add(name)

        if mode == SmallModelMode.MINIMAL:
            # Only pinned tools
            pass
        else:
            # Use ToolScope for semantic selection
            max_tools = self._config.small_model_max_tools
            remaining = max_tools - len(visible_names)

            if remaining > 0 and self._toolscope and self._toolscope.is_initialized:
                query = self._context.get_combined_query()
                if query:
                    matches = self._toolscope.search(query, k=remaining + 5)
                    for match in matches:
                        if match.name not in visible_names and match.name in self._all_tools:
                            visible_names.add(match.name)
                            if len(visible_names) >= max_tools:
                                break

            # If still under limit (no context yet), add high-value defaults
            if len(visible_names) < max_tools:
                defaults = ["explore_cluster", "cluster_summary", "project_summary"]
                for name in defaults:
                    if name in self._all_tools and name not in visible_names:
                        visible_names.add(name)
                        if len(visible_names) >= max_tools:
                            break

        # Build tool list
        return [self._all_tools[name] for name in visible_names if name in self._all_tools]

    def record_context(self, query: str, tool_calls: list[str] | None = None) -> None:
        """Record query for context-aware filtering.

        Args:
            query: The user's query or intent.
            tool_calls: Optional list of tool names that were called.
        """
        self._context.add(query, tool_calls)
        logger.debug(f"Recorded context: {query[:50]}...")

    def get_all_tool_names(self) -> list[str]:
        """Get all tool names (for discovery).

        Returns:
            List of all available tool names, regardless of filtering.
        """
        return list(self._all_tools.keys())

    def get_visible_tool_count(self) -> int:
        """Get the number of currently visible tools.

        Returns:
            Count of tools that would be returned by list_tools.
        """
        return len(self._filtered_list_tools())

    def get_total_tool_count(self) -> int:
        """Get the total number of available tools.

        Returns:
            Count of all indexed tools.
        """
        return len(self._all_tools)
