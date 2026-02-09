"""Tests for configuration module."""

import pytest
from pathlib import Path

from rhoai_mcp.config import (
    RHOAIConfig,
    AuthMode,
    TransportMode,
    LogLevel,
    SmallModelMode,
)


class TestRHOAIConfig:
    """Tests for RHOAIConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RHOAIConfig()

        assert config.auth_mode == AuthMode.AUTO
        assert config.transport == TransportMode.STDIO
        assert config.host == "127.0.0.1"
        assert config.port == 8000
        assert config.enable_dangerous_operations is False
        assert config.read_only_mode is False
        assert config.log_level == LogLevel.INFO

    def test_auth_mode_token_validation(self):
        """Test token auth mode validation."""
        config = RHOAIConfig(
            auth_mode=AuthMode.TOKEN,
            api_server="https://api.cluster.example.com:6443",
            api_token="sha256~token",
        )

        # Should not raise
        warnings = config.validate_auth_config()
        assert len(warnings) == 0

    def test_auth_mode_token_missing_server(self):
        """Test token auth mode without server raises error."""
        config = RHOAIConfig(
            auth_mode=AuthMode.TOKEN,
            api_token="sha256~token",
        )

        with pytest.raises(ValueError, match="api_server is required"):
            config.validate_auth_config()

    def test_auth_mode_token_missing_token(self):
        """Test token auth mode without token raises error."""
        config = RHOAIConfig(
            auth_mode=AuthMode.TOKEN,
            api_server="https://api.cluster.example.com:6443",
        )

        with pytest.raises(ValueError, match="api_token is required"):
            config.validate_auth_config()

    def test_is_operation_allowed_read_only(self):
        """Test read-only mode blocks write operations."""
        config = RHOAIConfig(read_only_mode=True)

        allowed, reason = config.is_operation_allowed("create")
        assert allowed is False
        assert "Read-only" in reason

        allowed, reason = config.is_operation_allowed("delete")
        assert allowed is False

        # Read should still be allowed
        allowed, reason = config.is_operation_allowed("get")
        assert allowed is True

    def test_is_operation_allowed_dangerous_disabled(self):
        """Test dangerous operations disabled by default."""
        config = RHOAIConfig(enable_dangerous_operations=False)

        allowed, reason = config.is_operation_allowed("delete")
        assert allowed is False
        assert "Dangerous operations are disabled" in reason

        # Non-dangerous operations should be allowed
        allowed, reason = config.is_operation_allowed("create")
        assert allowed is True

    def test_is_operation_allowed_dangerous_enabled(self):
        """Test dangerous operations when enabled."""
        config = RHOAIConfig(enable_dangerous_operations=True)

        allowed, reason = config.is_operation_allowed("delete")
        assert allowed is True
        assert reason is None

    def test_effective_kubeconfig_path_default(self):
        """Test default kubeconfig path."""
        config = RHOAIConfig()
        expected = Path.home() / ".kube" / "config"
        assert config.effective_kubeconfig_path == expected

    def test_effective_kubeconfig_path_explicit(self):
        """Test explicit kubeconfig path."""
        config = RHOAIConfig(kubeconfig_path="/custom/kubeconfig")
        assert config.effective_kubeconfig_path == Path("/custom/kubeconfig")

    def test_effective_kubeconfig_path_env(self, monkeypatch):
        """Test kubeconfig path from environment."""
        monkeypatch.setenv("KUBECONFIG", "/env/kubeconfig")
        config = RHOAIConfig()
        assert config.effective_kubeconfig_path == Path("/env/kubeconfig")

    def test_env_prefix(self, monkeypatch):
        """Test environment variable prefix."""
        monkeypatch.setenv("RHOAI_MCP_LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("RHOAI_MCP_PORT", "9000")

        config = RHOAIConfig()
        assert config.log_level == LogLevel.DEBUG
        assert config.port == 9000


class TestSmallModelConfig:
    """Tests for small model optimization configuration."""

    def test_default_small_model_mode(self):
        """Test default small model mode is NONE."""
        config = RHOAIConfig()
        assert config.small_model_mode == SmallModelMode.NONE

    def test_small_model_mode_from_env(self, monkeypatch):
        """Test small model mode from environment variable."""
        monkeypatch.setenv("RHOAI_MCP_SMALL_MODEL_MODE", "aggressive")
        config = RHOAIConfig()
        assert config.small_model_mode == SmallModelMode.AGGRESSIVE

    def test_small_model_mode_moderate(self, monkeypatch):
        """Test moderate small model mode."""
        monkeypatch.setenv("RHOAI_MCP_SMALL_MODEL_MODE", "moderate")
        config = RHOAIConfig()
        assert config.small_model_mode == SmallModelMode.MODERATE

    def test_small_model_mode_minimal(self, monkeypatch):
        """Test minimal small model mode."""
        monkeypatch.setenv("RHOAI_MCP_SMALL_MODEL_MODE", "minimal")
        config = RHOAIConfig()
        assert config.small_model_mode == SmallModelMode.MINIMAL

    def test_small_model_max_tools_default(self):
        """Test default max tools value."""
        config = RHOAIConfig()
        assert config.small_model_max_tools == 10

    def test_small_model_max_tools_from_env(self, monkeypatch):
        """Test max tools from environment variable."""
        monkeypatch.setenv("RHOAI_MCP_SMALL_MODEL_MAX_TOOLS", "5")
        config = RHOAIConfig()
        assert config.small_model_max_tools == 5

    def test_small_model_pinned_tools_default(self):
        """Test default pinned tools."""
        config = RHOAIConfig()
        assert "suggest_tools" in config.small_model_pinned_tools
        assert "list_tool_categories" in config.small_model_pinned_tools

    def test_small_model_compress_schemas_default(self):
        """Test default compress schemas is False."""
        config = RHOAIConfig()
        assert config.small_model_compress_schemas is False

    def test_small_model_context_size_default(self):
        """Test default context size."""
        config = RHOAIConfig()
        assert config.small_model_context_size == 5

    def test_small_model_context_size_from_env(self, monkeypatch):
        """Test context size from environment variable."""
        monkeypatch.setenv("RHOAI_MCP_SMALL_MODEL_CONTEXT_SIZE", "10")
        config = RHOAIConfig()
        assert config.small_model_context_size == 10
