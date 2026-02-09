"""Tests for ToolScope integration."""

from unittest.mock import MagicMock

import pytest

from rhoai_mcp.composites.toolscope.manager import ToolMatch, ToolScopeManager
from rhoai_mcp.composites.toolscope.plugin import ToolScopePlugin
from rhoai_mcp.config import RHOAIConfig, ToolScopeEmbedderType


class TestToolMatch:
    """Tests for ToolMatch dataclass."""

    def test_tool_match_creation(self) -> None:
        """Test creating a ToolMatch."""
        match = ToolMatch(
            name="train",
            description="Train a model",
            score=0.95,
            category="training",
            tags=["ml", "training"],
        )

        assert match.name == "train"
        assert match.description == "Train a model"
        assert match.score == 0.95
        assert match.category == "training"
        assert match.tags == ["ml", "training"]


class TestToolScopeManager:
    """Tests for ToolScopeManager."""

    def test_disabled_does_not_initialize(self) -> None:
        """Test manager skips initialization when disabled."""
        config = MagicMock(spec=RHOAIConfig)
        config.toolscope_enabled = False

        manager = ToolScopeManager(config)
        manager.initialize(MagicMock())

        assert not manager.is_initialized
        assert manager.tool_count == 0

    def test_search_returns_empty_when_not_initialized(self) -> None:
        """Test search returns empty list when not initialized."""
        config = MagicMock(spec=RHOAIConfig)
        config.toolscope_enabled = True

        manager = ToolScopeManager(config)
        results = manager.search("train a model")

        assert results == []

    def test_infer_category_training(self) -> None:
        """Test category inference for training tools."""
        config = MagicMock(spec=RHOAIConfig)
        manager = ToolScopeManager(config)

        assert manager._infer_category("prepare_training") == "training"
        assert manager._infer_category("train") == "training"
        assert manager._infer_category("get_training_progress") == "training"

    def test_infer_category_inference(self) -> None:
        """Test category inference for inference tools."""
        config = MagicMock(spec=RHOAIConfig)
        manager = ToolScopeManager(config)

        assert manager._infer_category("deploy_model") == "inference"
        assert manager._infer_category("model_endpoint") == "inference"
        assert manager._infer_category("serve_model") == "inference"

    def test_infer_category_workbenches(self) -> None:
        """Test category inference for workbench tools."""
        config = MagicMock(spec=RHOAIConfig)
        manager = ToolScopeManager(config)

        assert manager._infer_category("list_workbenches") == "workbenches"
        assert manager._infer_category("create_notebook") == "workbenches"

    def test_infer_category_storage(self) -> None:
        """Test category inference for storage tools."""
        config = MagicMock(spec=RHOAIConfig)
        manager = ToolScopeManager(config)

        assert manager._infer_category("create_storage") == "storage"
        assert manager._infer_category("pvc_status") == "storage"

    def test_infer_category_discovery(self) -> None:
        """Test category inference for discovery tools."""
        config = MagicMock(spec=RHOAIConfig)
        manager = ToolScopeManager(config)

        assert manager._infer_category("cluster_summary") == "discovery"
        assert manager._infer_category("explore_cluster") == "discovery"
        assert manager._infer_category("list_resources") == "discovery"

    def test_infer_category_other(self) -> None:
        """Test category inference falls back to 'other'."""
        config = MagicMock(spec=RHOAIConfig)
        manager = ToolScopeManager(config)

        assert manager._infer_category("unknown_tool") == "other"
        assert manager._infer_category("some_random_function") == "other"


class TestToolScopePlugin:
    """Tests for ToolScopePlugin."""

    def test_plugin_metadata(self) -> None:
        """Test plugin has correct metadata."""
        plugin = ToolScopePlugin()
        metadata = plugin.rhoai_get_plugin_metadata()

        assert metadata.name == "toolscope"
        assert metadata.version == "1.0.0"
        assert "semantic" in metadata.description.lower()
        assert metadata.requires_crds == []

    def test_manager_not_created_when_disabled(self) -> None:
        """Test manager is not created when ToolScope is disabled."""
        plugin = ToolScopePlugin()
        mcp = MagicMock()
        server = MagicMock()
        server.config.toolscope_enabled = False

        plugin.rhoai_register_tools(mcp, server)

        assert plugin.manager is None

    def test_manager_created_when_enabled(self) -> None:
        """Test manager is created when ToolScope is enabled."""
        plugin = ToolScopePlugin()
        mcp = MagicMock()
        server = MagicMock()
        server.config.toolscope_enabled = True

        plugin.rhoai_register_tools(mcp, server)

        assert plugin.manager is not None
        assert isinstance(plugin.manager, ToolScopeManager)

    def test_health_check_disabled(self) -> None:
        """Test health check when ToolScope is disabled."""
        plugin = ToolScopePlugin()
        server = MagicMock()
        server.config.toolscope_enabled = False

        is_healthy, message = plugin.rhoai_health_check(server)

        assert is_healthy is True
        assert "disabled" in message.lower()

    def test_health_check_not_initialized(self) -> None:
        """Test health check when ToolScope is enabled but not initialized."""
        plugin = ToolScopePlugin()
        plugin._manager = MagicMock()
        plugin._manager.is_initialized = False

        server = MagicMock()
        server.config.toolscope_enabled = True

        is_healthy, message = plugin.rhoai_health_check(server)

        assert is_healthy is True
        assert "fallback" in message.lower()

    def test_health_check_initialized(self) -> None:
        """Test health check when ToolScope is initialized."""
        plugin = ToolScopePlugin()
        plugin._manager = MagicMock()
        plugin._manager.is_initialized = True
        plugin._manager.tool_count = 42

        server = MagicMock()
        server.config.toolscope_enabled = True

        is_healthy, message = plugin.rhoai_health_check(server)

        assert is_healthy is True
        assert "42" in message
        assert "indexed" in message.lower()


class TestToolScopeConfig:
    """Tests for ToolScope configuration."""

    def test_default_config_values(self) -> None:
        """Test default configuration values."""
        config = RHOAIConfig()

        assert config.toolscope_enabled is True
        assert config.toolscope_embedder_type == ToolScopeEmbedderType.SENTENCE_TRANSFORMERS
        assert config.toolscope_embedder_model == "all-MiniLM-L6-v2"
        assert config.toolscope_embedder_url is None
        assert config.toolscope_default_k == 5

    def test_config_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test configuration from environment variables."""
        monkeypatch.setenv("RHOAI_MCP_TOOLSCOPE_ENABLED", "false")
        monkeypatch.setenv("RHOAI_MCP_TOOLSCOPE_EMBEDDER_TYPE", "http")
        monkeypatch.setenv("RHOAI_MCP_TOOLSCOPE_EMBEDDER_MODEL", "custom-model")
        monkeypatch.setenv("RHOAI_MCP_TOOLSCOPE_EMBEDDER_URL", "http://embeddings.local")
        monkeypatch.setenv("RHOAI_MCP_TOOLSCOPE_DEFAULT_K", "10")

        config = RHOAIConfig()

        assert config.toolscope_enabled is False
        assert config.toolscope_embedder_type == ToolScopeEmbedderType.HTTP
        assert config.toolscope_embedder_model == "custom-model"
        assert config.toolscope_embedder_url == "http://embeddings.local"
        assert config.toolscope_default_k == 10
