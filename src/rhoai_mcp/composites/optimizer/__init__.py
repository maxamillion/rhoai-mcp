"""Small model optimization for dynamic tool filtering.

This module provides the SmallModelOptimizer that dynamically filters
tools exposed to MCP clients based on conversation context and semantic
relevance. This reduces token usage for small language models that
struggle with large tool sets.
"""

from rhoai_mcp.composites.optimizer.context import (
    ContextEntry,
    ConversationContextBuffer,
)
from rhoai_mcp.composites.optimizer.manager import SmallModelOptimizer
from rhoai_mcp.composites.optimizer.plugin import SmallModelOptimizerPlugin

__all__ = [
    "ContextEntry",
    "ConversationContextBuffer",
    "SmallModelOptimizer",
    "SmallModelOptimizerPlugin",
]
