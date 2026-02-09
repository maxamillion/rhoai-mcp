"""Conversation context buffer for tool relevance tracking."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class ContextEntry:
    """A single context entry tracking a query and its tool calls."""

    query: str
    timestamp: float
    tool_calls: list[str] = field(default_factory=list)


class ConversationContextBuffer:
    """Circular buffer tracking recent conversation context.

    Used by SmallModelOptimizer to maintain context about recent queries
    and tool calls, enabling more relevant tool filtering over time.
    """

    def __init__(self, max_size: int = 5):
        """Initialize the context buffer.

        Args:
            max_size: Maximum number of entries to retain.
        """
        self._max_size = max_size
        self._entries: deque[ContextEntry] = deque(maxlen=max_size)

    def add(self, query: str, tool_calls: list[str] | None = None) -> None:
        """Add a context entry.

        Args:
            query: The user's query or intent.
            tool_calls: Optional list of tool names that were called.
        """
        self._entries.append(
            ContextEntry(
                query=query,
                timestamp=time.time(),
                tool_calls=tool_calls or [],
            )
        )

    def get_combined_query(self) -> str:
        """Combine recent queries for semantic search.

        Returns the last 3 queries joined together to provide
        context for semantic tool matching.

        Returns:
            Combined query string from recent entries.
        """
        queries = [e.query for e in self._entries]
        if queries:
            # Weight towards more recent queries
            return " ".join(queries[-3:])
        return ""

    def get_recent_tool_calls(self) -> list[str]:
        """Get tool names from recent entries.

        Returns:
            List of unique tool names from recent entries.
        """
        tools: set[str] = set()
        for entry in self._entries:
            tools.update(entry.tool_calls)
        return list(tools)

    def clear(self) -> None:
        """Clear the buffer."""
        self._entries.clear()

    @property
    def size(self) -> int:
        """Current buffer size."""
        return len(self._entries)

    @property
    def max_size(self) -> int:
        """Maximum buffer size."""
        return self._max_size

    @property
    def entries(self) -> list[ContextEntry]:
        """Get all entries (for inspection/testing)."""
        return list(self._entries)
