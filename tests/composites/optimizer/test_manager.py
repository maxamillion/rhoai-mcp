"""Tests for SmallModelOptimizer."""

from dataclasses import dataclass
from unittest.mock import MagicMock

from rhoai_mcp.composites.optimizer.manager import SmallModelOptimizer
from rhoai_mcp.config import RHOAIConfig, SmallModelMode


@dataclass
class MockTool:
    """Mock tool for testing."""

    name: str
    description: str = "A mock tool"


class MockToolManager:
    """Mock FastMCP tool manager."""

    def __init__(self, tools: list[MockTool]):
        self._tools = tools
        self._list_tools_calls = 0

    def list_tools(self) -> list[MockTool]:
        self._list_tools_calls += 1
        return self._tools


class MockFastMCP:
    """Mock FastMCP server."""

    def __init__(self, tools: list[MockTool]):
        self._tool_manager = MockToolManager(tools)


class TestSmallModelOptimizer:
    """Tests for SmallModelOptimizer."""

    def _create_config(
        self,
        mode: SmallModelMode = SmallModelMode.MODERATE,
        max_tools: int = 5,
        pinned_tools: list[str] | None = None,
    ) -> RHOAIConfig:
        """Create a test config."""
        return RHOAIConfig(
            small_model_mode=mode,
            small_model_max_tools=max_tools,
            small_model_pinned_tools=pinned_tools or ["suggest_tools"],
            small_model_context_size=5,
        )

    def _create_mock_tools(self, names: list[str]) -> list[MockTool]:
        """Create mock tools from names."""
        return [MockTool(name=name) for name in names]

    def test_initialization(self):
        """Test optimizer initialization."""
        config = self._create_config()
        optimizer = SmallModelOptimizer(config, toolscope_manager=None)

        assert not optimizer.is_installed
        assert optimizer.get_total_tool_count() == 0

    def test_install_skipped_when_mode_none(self):
        """Test that install is skipped when mode is NONE."""
        config = self._create_config(mode=SmallModelMode.NONE)
        optimizer = SmallModelOptimizer(config, toolscope_manager=None)

        tools = self._create_mock_tools(["tool1", "tool2"])
        mcp = MockFastMCP(tools)

        optimizer.install(mcp)

        assert not optimizer.is_installed

    def test_install_caches_tools(self):
        """Test that install caches all tools."""
        config = self._create_config()
        optimizer = SmallModelOptimizer(config, toolscope_manager=None)

        tools = self._create_mock_tools(["tool1", "tool2", "suggest_tools"])
        mcp = MockFastMCP(tools)

        optimizer.install(mcp)

        assert optimizer.is_installed
        assert optimizer.get_total_tool_count() == 3
        assert set(optimizer.get_all_tool_names()) == {"tool1", "tool2", "suggest_tools"}

    def test_minimal_mode_returns_only_pinned(self):
        """Test MINIMAL mode only returns pinned tools."""
        config = self._create_config(
            mode=SmallModelMode.MINIMAL,
            pinned_tools=["suggest_tools", "list_tool_categories"],
        )
        optimizer = SmallModelOptimizer(config, toolscope_manager=None)

        tools = self._create_mock_tools([
            "suggest_tools",
            "list_tool_categories",
            "train",
            "deploy_model",
            "explore_cluster",
        ])
        mcp = MockFastMCP(tools)

        optimizer.install(mcp)

        # Call the filtered list_tools
        filtered = mcp._tool_manager.list_tools()
        names = [t.name for t in filtered]

        assert len(names) == 2
        assert "suggest_tools" in names
        assert "list_tool_categories" in names
        assert "train" not in names

    def test_moderate_mode_includes_defaults_without_context(self):
        """Test MODERATE mode includes default tools when no context."""
        config = self._create_config(
            mode=SmallModelMode.MODERATE,
            max_tools=5,
            pinned_tools=["suggest_tools"],
        )
        optimizer = SmallModelOptimizer(config, toolscope_manager=None)

        tools = self._create_mock_tools([
            "suggest_tools",
            "explore_cluster",
            "cluster_summary",
            "project_summary",
            "train",
            "deploy_model",
        ])
        mcp = MockFastMCP(tools)

        optimizer.install(mcp)

        filtered = mcp._tool_manager.list_tools()
        names = [t.name for t in filtered]

        # Should have pinned + defaults up to max_tools
        assert "suggest_tools" in names
        assert "explore_cluster" in names
        assert len(names) <= 5

    def test_record_context(self):
        """Test recording context for semantic filtering."""
        config = self._create_config()
        optimizer = SmallModelOptimizer(config, toolscope_manager=None)

        optimizer.record_context("train a model")
        optimizer.record_context("with LoRA adapter")

        assert optimizer.context.size == 2
        combined = optimizer.context.get_combined_query()
        assert "train a model" in combined
        assert "LoRA" in combined

    def test_get_visible_tool_count(self):
        """Test getting visible tool count."""
        config = self._create_config(
            mode=SmallModelMode.MINIMAL,
            pinned_tools=["suggest_tools"],
        )
        optimizer = SmallModelOptimizer(config, toolscope_manager=None)

        tools = self._create_mock_tools(["suggest_tools", "train", "deploy"])
        mcp = MockFastMCP(tools)

        optimizer.install(mcp)

        assert optimizer.get_visible_tool_count() == 1
        assert optimizer.get_total_tool_count() == 3

    def test_filtering_with_mock_toolscope(self):
        """Test filtering with a mock ToolScope manager."""
        config = self._create_config(
            mode=SmallModelMode.MODERATE,
            max_tools=5,
            pinned_tools=["suggest_tools"],
        )

        # Create mock ToolScope manager
        mock_match = MagicMock()
        mock_match.name = "train"

        mock_toolscope = MagicMock()
        mock_toolscope.is_initialized = True
        mock_toolscope.search.return_value = [mock_match]

        optimizer = SmallModelOptimizer(config, toolscope_manager=mock_toolscope)

        tools = self._create_mock_tools([
            "suggest_tools",
            "train",
            "deploy_model",
            "explore_cluster",
        ])
        mcp = MockFastMCP(tools)

        optimizer.install(mcp)

        # Add context to trigger semantic search
        optimizer.record_context("I want to train a model")

        filtered = mcp._tool_manager.list_tools()
        names = [t.name for t in filtered]

        # Should include pinned + semantic match + defaults
        assert "suggest_tools" in names
        assert "train" in names  # From semantic search


class TestSmallModelOptimizerIntegration:
    """Integration-style tests for SmallModelOptimizer."""

    def test_pinned_tools_missing_from_registry(self):
        """Test handling when pinned tools don't exist in registry."""
        config = RHOAIConfig(
            small_model_mode=SmallModelMode.MINIMAL,
            small_model_pinned_tools=["nonexistent_tool", "also_missing"],
        )
        optimizer = SmallModelOptimizer(config, toolscope_manager=None)

        # Only have one tool, none of the pinned ones
        tools = [MockTool(name="some_tool")]
        mcp = MockFastMCP(tools)

        optimizer.install(mcp)

        filtered = mcp._tool_manager.list_tools()
        # Should return empty list since no pinned tools exist
        assert len(filtered) == 0

    def test_max_tools_respected(self):
        """Test that max_tools limit is respected."""
        config = RHOAIConfig(
            small_model_mode=SmallModelMode.MODERATE,
            small_model_max_tools=3,
            small_model_pinned_tools=["suggest_tools"],
        )
        optimizer = SmallModelOptimizer(config, toolscope_manager=None)

        # Create many tools
        tools = [MockTool(name=f"tool_{i}") for i in range(20)]
        tools.append(MockTool(name="suggest_tools"))
        tools.append(MockTool(name="explore_cluster"))
        tools.append(MockTool(name="cluster_summary"))
        tools.append(MockTool(name="project_summary"))
        mcp = MockFastMCP(tools)

        optimizer.install(mcp)

        filtered = mcp._tool_manager.list_tools()
        # Should not exceed max_tools
        assert len(filtered) <= 3
