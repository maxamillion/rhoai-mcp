"""Tests for ConversationContextBuffer."""

import time

from rhoai_mcp.composites.optimizer.context import (
    ContextEntry,
    ConversationContextBuffer,
)


class TestContextEntry:
    """Tests for ContextEntry dataclass."""

    def test_creation_with_defaults(self):
        """Test creating entry with default tool_calls."""
        entry = ContextEntry(query="test query", timestamp=time.time())
        assert entry.query == "test query"
        assert entry.tool_calls == []

    def test_creation_with_tool_calls(self):
        """Test creating entry with explicit tool_calls."""
        entry = ContextEntry(
            query="train a model",
            timestamp=time.time(),
            tool_calls=["prepare_training", "train"],
        )
        assert entry.query == "train a model"
        assert entry.tool_calls == ["prepare_training", "train"]


class TestConversationContextBuffer:
    """Tests for ConversationContextBuffer."""

    def test_initialization(self):
        """Test buffer initialization."""
        buffer = ConversationContextBuffer(max_size=5)
        assert buffer.size == 0
        assert buffer.max_size == 5

    def test_add_entry(self):
        """Test adding entries to buffer."""
        buffer = ConversationContextBuffer(max_size=5)
        buffer.add("train a model")
        assert buffer.size == 1

        buffer.add("deploy model", ["deploy_model"])
        assert buffer.size == 2

    def test_circular_buffer_behavior(self):
        """Test that old entries are evicted when max_size exceeded."""
        buffer = ConversationContextBuffer(max_size=3)

        buffer.add("query 1")
        buffer.add("query 2")
        buffer.add("query 3")
        assert buffer.size == 3

        # Adding fourth should evict first
        buffer.add("query 4")
        assert buffer.size == 3

        queries = [e.query for e in buffer.entries]
        assert "query 1" not in queries
        assert "query 4" in queries

    def test_get_combined_query(self):
        """Test combining recent queries."""
        buffer = ConversationContextBuffer(max_size=5)

        # Empty buffer returns empty string
        assert buffer.get_combined_query() == ""

        buffer.add("train a model")
        assert buffer.get_combined_query() == "train a model"

        buffer.add("with LoRA")
        buffer.add("on llama 2")
        # Should combine last 3 queries
        combined = buffer.get_combined_query()
        assert "train a model" in combined
        assert "with LoRA" in combined
        assert "on llama 2" in combined

    def test_get_combined_query_limits_to_three(self):
        """Test that combined query only uses last 3 entries."""
        buffer = ConversationContextBuffer(max_size=10)

        for i in range(5):
            buffer.add(f"query {i}")

        combined = buffer.get_combined_query()
        # Should only include queries 2, 3, 4 (last 3)
        assert "query 2" in combined
        assert "query 3" in combined
        assert "query 4" in combined
        # Should not include query 0 or 1
        assert "query 0" not in combined
        assert "query 1" not in combined

    def test_get_recent_tool_calls(self):
        """Test extracting tool calls from entries."""
        buffer = ConversationContextBuffer(max_size=5)

        buffer.add("train", ["prepare_training"])
        buffer.add("check status", ["get_training_progress"])
        buffer.add("deploy", ["deploy_model"])

        tools = buffer.get_recent_tool_calls()
        assert set(tools) == {"prepare_training", "get_training_progress", "deploy_model"}

    def test_get_recent_tool_calls_deduplicates(self):
        """Test that tool calls are deduplicated."""
        buffer = ConversationContextBuffer(max_size=5)

        buffer.add("first call", ["tool_a", "tool_b"])
        buffer.add("second call", ["tool_b", "tool_c"])

        tools = buffer.get_recent_tool_calls()
        # Should have unique tools only
        assert len(tools) == 3
        assert set(tools) == {"tool_a", "tool_b", "tool_c"}

    def test_clear(self):
        """Test clearing the buffer."""
        buffer = ConversationContextBuffer(max_size=5)
        buffer.add("query 1")
        buffer.add("query 2")
        assert buffer.size == 2

        buffer.clear()
        assert buffer.size == 0
        assert buffer.get_combined_query() == ""

    def test_entries_property(self):
        """Test accessing entries for inspection."""
        buffer = ConversationContextBuffer(max_size=5)
        buffer.add("query 1")
        buffer.add("query 2")

        entries = buffer.entries
        assert len(entries) == 2
        assert entries[0].query == "query 1"
        assert entries[1].query == "query 2"
