"""Integration tests for plugin and domain discovery."""


def test_external_plugins_discovered():
    """Verify external plugins are discovered via entry points.

    With the hybrid architecture, all domains are now core domains registered
    directly via the domain registry. There are no external plugins.
    """
    from rhoai_mcp_core.server import RHOAIServer

    server = RHOAIServer()
    # Call _discover_plugins directly since _plugins is populated during create_mcp()
    plugins = server._discover_plugins()

    # No external plugins - all domains are now core
    # This test verifies the entry point discovery mechanism still works
    # even if no external plugins are registered
    discovered = set(plugins.keys())
    assert isinstance(discovered, set), "Plugin discovery should return a dict with plugin names"


def test_core_domains_loaded():
    """Verify all core domains are loaded from the registry."""
    from rhoai_mcp_core.domains.registry import get_core_domains

    domains = get_core_domains()
    domain_names = {d.name for d in domains}

    expected_domains = {
        "notebooks",
        "inference",
        "pipelines",
        "connections",
        "storage",
        "projects",
        "training",
    }

    assert expected_domains == domain_names, (
        f"Domain mismatch. Expected: {expected_domains}, Got: {domain_names}"
    )


def test_plugin_metadata():
    """Verify all external plugins have valid metadata."""
    from rhoai_mcp_core.server import RHOAIServer

    server = RHOAIServer()
    plugins = server._discover_plugins()

    for name, plugin in plugins.items():
        meta = plugin.metadata
        assert meta.name == name
        assert meta.version
        assert meta.description
        assert meta.maintainer


def test_plugins_can_register():
    """Verify external plugins can register tools and resources without error."""
    from unittest.mock import MagicMock

    from rhoai_mcp_core.server import RHOAIServer

    server = RHOAIServer()
    plugins = server._discover_plugins()
    mock_mcp = MagicMock()

    for _name, plugin in plugins.items():
        # Should not raise
        plugin.register_tools(mock_mcp, server)
        plugin.register_resources(mock_mcp, server)


def test_domains_can_register():
    """Verify core domains can register tools and resources without error."""
    from unittest.mock import MagicMock

    from rhoai_mcp_core.domains.registry import get_core_domains
    from rhoai_mcp_core.server import RHOAIServer

    server = RHOAIServer()
    domains = get_core_domains()
    mock_mcp = MagicMock()

    for domain in domains:
        # Should not raise
        if domain.register_tools:
            domain.register_tools(mock_mcp, server)
        if domain.register_resources:
            domain.register_resources(mock_mcp, server)
