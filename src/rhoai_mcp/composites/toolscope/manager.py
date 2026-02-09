"""ToolScope manager for semantic tool search."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from rhoai_mcp.config import RHOAIConfig

logger = logging.getLogger(__name__)


@dataclass
class ToolMatch:
    """A tool matched by semantic search."""

    name: str
    description: str
    score: float
    category: str
    tags: list[str]


class SentenceTransformerEmbedder:
    """Embedder using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts."""
        embeddings = self._model.encode(texts, convert_to_numpy=True)
        result: list[list[float]] = embeddings.tolist()
        return result


class ToolScopeManager:
    """Manages ToolScope index for semantic tool search."""

    def __init__(self, config: RHOAIConfig):
        self._config = config
        self._index: Any | None = None
        self._tool_metadata: dict[str, dict[str, Any]] = {}
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Check if the manager has been initialized."""
        return self._initialized

    @property
    def tool_count(self) -> int:
        """Get the number of indexed tools."""
        return len(self._tool_metadata)

    def initialize(self, mcp: FastMCP) -> None:
        """Build the ToolScope index from registered MCP tools."""
        import toolscope

        if not self._config.toolscope_enabled:
            logger.info("ToolScope disabled, skipping initialization")
            return

        # Extract tools from FastMCP
        tools = self._extract_tools(mcp)
        if not tools:
            logger.warning("No tools found for ToolScope indexing")
            return

        # Create embedder
        embedder = self._create_embedder()
        if embedder is None:
            logger.warning("Failed to create embedder, ToolScope disabled")
            return

        # Build index
        try:
            self._index = toolscope.index(tools, embedder=embedder)
            self._initialized = True
            logger.info(f"ToolScope index built with {len(tools)} tools")
        except Exception as e:
            logger.error(f"Failed to build ToolScope index: {e}")

    def _extract_tools(self, mcp: FastMCP) -> list[dict[str, Any]]:
        """Extract tool definitions from FastMCP."""
        tools = []

        # Access FastMCP's internal tool registry
        # FastMCP stores tools in _tool_manager or similar
        if hasattr(mcp, "_tool_manager"):
            tool_manager = mcp._tool_manager
            if hasattr(tool_manager, "list_tools"):
                for tool in tool_manager.list_tools():
                    tool_dict = {
                        "name": tool.name,
                        "description": tool.description or "",
                        "inputSchema": getattr(tool, "inputSchema", {}) or {},
                    }
                    tools.append(tool_dict)
                    self._tool_metadata[tool.name] = tool_dict
        else:
            # Fallback: try to access via _tools attribute
            tool_registry = getattr(mcp, "_tools", {})
            for name, tool in tool_registry.items():
                tool_dict = {
                    "name": name,
                    "description": getattr(tool, "__doc__", "") or "",
                    "inputSchema": {},
                }
                tools.append(tool_dict)
                self._tool_metadata[name] = tool_dict

        return tools

    def _create_embedder(self) -> Any | None:
        """Create embedder based on configuration."""
        import toolscope

        if self._config.toolscope_embedder_type.value == "disabled":
            return None

        if self._config.toolscope_embedder_type.value == "sentence-transformers":
            model = self._config.toolscope_embedder_model
            logger.info(f"Loading sentence-transformers model: {model}")
            return SentenceTransformerEmbedder(model)

        if self._config.toolscope_embedder_type.value == "http":
            if not self._config.toolscope_embedder_url:
                logger.error("HTTP embedder requires toolscope_embedder_url")
                return None
            return toolscope.EmbeddingConfig(
                url=self._config.toolscope_embedder_url,
                model=self._config.toolscope_embedder_model,
            )

        return None

    def search(
        self,
        query: str,
        k: int | None = None,
        categories: list[str] | None = None,
    ) -> list[ToolMatch]:
        """Search for tools matching the query."""
        if not self._initialized or self._index is None:
            return []

        k = k or self._config.toolscope_default_k

        try:
            results = self._index.filter(
                messages=query,
                k=k,
            )

            matches = []
            for tool in results:
                name = tool.get("name", "")
                matches.append(
                    ToolMatch(
                        name=name,
                        description=tool.get("description", ""),
                        score=tool.get("_score", 0.0),
                        category=self._infer_category(name),
                        tags=tool.get("tags", []),
                    )
                )

            # Filter by category if specified
            if categories:
                matches = [m for m in matches if m.category in categories]

            return matches
        except Exception as e:
            logger.error(f"ToolScope search failed: {e}")
            return []

    def _infer_category(self, tool_name: str) -> str:
        """Infer category from tool name."""
        # Map tool names to categories based on prefixes/patterns
        category_patterns = {
            "training": ["train", "prepare_training", "get_training"],
            "inference": ["deploy", "model", "endpoint", "serve"],
            "workbenches": ["workbench", "notebook"],
            "storage": ["storage", "pvc", "volume"],
            "connections": ["connection", "s3", "data_connection"],
            "pipelines": ["pipeline"],
            "projects": ["project"],
            "discovery": ["cluster", "explore", "summary", "list"],
        }

        for category, patterns in category_patterns.items():
            if any(p in tool_name.lower() for p in patterns):
                return category

        return "other"
