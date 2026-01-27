"""Plugin interface for RHOAI MCP components.

This module defines the plugin protocol that all RHOAI MCP components must implement
to be discovered and loaded by the server.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from rhoai_mcp_core.clients.base import CRDDefinition
    from rhoai_mcp_core.server import RHOAIServer


@dataclass
class PluginMetadata:
    """Metadata describing an RHOAI MCP plugin.

    Each plugin must provide this metadata to identify itself and
    declare its requirements.
    """

    name: str
    """Unique plugin name, e.g., 'notebooks', 'inference'."""

    version: str
    """Plugin version following semver, e.g., '1.0.0'."""

    description: str
    """Human-readable description of what this plugin provides."""

    maintainer: str
    """Maintainer email or team, e.g., 'kubeflow-team@redhat.com'."""

    requires_crds: list[str] = field(default_factory=list)
    """List of CRD kinds this plugin requires to function.

    If any of these CRDs are not available in the cluster,
    the plugin will be marked as unavailable but the server
    will continue to run with other plugins.
    """


@runtime_checkable
class RHOAIMCPPlugin(Protocol):
    """Protocol defining the interface for RHOAI MCP plugins.

    All component packages (notebooks, inference, pipelines, etc.) must
    implement this protocol to be discovered and loaded by the server.

    Plugins are discovered via Python entry points in the 'rhoai_mcp.plugins'
    group. Each entry point should point to a factory function that returns
    an instance implementing this protocol.

    Example entry point in pyproject.toml:
        [project.entry-points."rhoai_mcp.plugins"]
        notebooks = "rhoai_mcp_notebooks.plugin:create_plugin"
    """

    @property
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata.

        This property must be implemented to provide information
        about the plugin including its name, version, and requirements.
        """
        ...

    def register_tools(self, mcp: FastMCP, server: RHOAIServer) -> None:
        """Register MCP tools provided by this plugin.

        This method is called during server startup to register all
        tools (functions) that this plugin provides.

        Args:
            mcp: The FastMCP server instance to register tools with.
            server: The RHOAI server instance for accessing K8s client and config.
        """
        ...

    def register_resources(self, mcp: FastMCP, server: RHOAIServer) -> None:
        """Register MCP resources provided by this plugin.

        This method is called during server startup to register all
        resources (data endpoints) that this plugin provides.

        Args:
            mcp: The FastMCP server instance to register resources with.
            server: The RHOAI server instance for accessing K8s client and config.
        """
        ...

    def get_crd_definitions(self) -> list[CRDDefinition]:
        """Return CRD definitions used by this plugin.

        This allows the core server to know about all CRDs without
        having to import component-specific code.

        Returns:
            List of CRDDefinition objects for CRDs this plugin uses.
        """
        ...

    def health_check(self, server: RHOAIServer) -> tuple[bool, str]:
        """Check if this plugin can operate correctly.

        This method is called during startup to verify that all
        required CRDs are available and the plugin can function.
        Plugins that fail health checks are skipped, allowing the
        server to gracefully degrade when some components are unavailable.

        Args:
            server: The RHOAI server instance for accessing K8s client.

        Returns:
            Tuple of (healthy, message) where healthy is True if the
            plugin can operate, and message provides details.
        """
        ...


class BasePlugin:
    """Base implementation of RHOAIMCPPlugin with common functionality.

    Component plugins can extend this class to get default implementations
    of optional methods.
    """

    def __init__(self, metadata: PluginMetadata) -> None:
        """Initialize the plugin with metadata.

        Args:
            metadata: Plugin metadata.
        """
        self._metadata = metadata

    @property
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return self._metadata

    def register_tools(self, mcp: FastMCP, server: RHOAIServer) -> None:
        """Register MCP tools. Override in subclass."""
        pass

    def register_resources(self, mcp: FastMCP, server: RHOAIServer) -> None:
        """Register MCP resources. Override in subclass."""
        pass

    def get_crd_definitions(self) -> list[CRDDefinition]:
        """Return CRD definitions. Override in subclass."""
        return []

    def health_check(self, server: RHOAIServer) -> tuple[bool, str]:
        """Check plugin health by verifying required CRDs are available.

        Default implementation checks that all CRDs listed in
        metadata.requires_crds are accessible in the cluster.
        """
        if not self._metadata.requires_crds:
            return True, "No CRD requirements"

        crd_defs = self.get_crd_definitions()
        crd_map = {crd.kind: crd for crd in crd_defs}

        missing_crds = []
        for crd_kind in self._metadata.requires_crds:
            if crd_kind not in crd_map:
                missing_crds.append(crd_kind)
                continue

            crd = crd_map[crd_kind]
            try:
                # Try to get the resource to verify CRD exists
                server.k8s.get_resource(crd)
            except Exception:
                missing_crds.append(crd_kind)

        if missing_crds:
            return False, f"Missing CRDs: {', '.join(missing_crds)}"

        return True, "All required CRDs available"
