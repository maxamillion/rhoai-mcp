"""Domain registry for core RHOAI MCP modules.

This module replaces plugin entry point discovery for core domains.
Each domain module is registered directly with the server.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from rhoai_mcp_core.server import RHOAIServer


@dataclass
class DomainModule:
    """Core domain module definition.

    Similar to a plugin but registered directly rather than via entry points.
    """

    name: str
    """Domain name, e.g., 'notebooks', 'inference'."""

    description: str
    """Human-readable description of what this domain provides."""

    required_crds: list[str] = field(default_factory=list)
    """List of CRD kinds this domain requires to function."""

    register_tools: Callable[[FastMCP, RHOAIServer], None] | None = None
    """Function to register MCP tools."""

    register_resources: Callable[[FastMCP, RHOAIServer], None] | None = None
    """Function to register MCP resources."""

    health_check: Callable[[RHOAIServer], tuple[bool, str]] | None = None
    """Optional custom health check function."""


def get_core_domains() -> list[DomainModule]:
    """Return all core domain modules.

    Lazy imports are used to avoid circular dependencies.
    """
    # Import tool registration functions
    from rhoai_mcp_core.domains.connections.tools import (
        register_tools as connections_tools,
    )
    from rhoai_mcp_core.domains.inference.tools import register_tools as inference_tools
    from rhoai_mcp_core.domains.notebooks.tools import register_tools as notebooks_tools
    from rhoai_mcp_core.domains.pipelines.tools import register_tools as pipelines_tools
    from rhoai_mcp_core.domains.projects.resources import (
        register_resources as projects_resources,
    )
    from rhoai_mcp_core.domains.projects.tools import register_tools as projects_tools
    from rhoai_mcp_core.domains.storage.tools import register_tools as storage_tools

    return [
        DomainModule(
            name="projects",
            description="Data Science Project management",
            required_crds=[],
            register_tools=projects_tools,
            register_resources=projects_resources,
            health_check=lambda _: (True, "Projects uses core Kubernetes and OpenShift APIs"),
        ),
        DomainModule(
            name="notebooks",
            description="Workbench (Kubeflow Notebook) management",
            required_crds=["Notebook"],
            register_tools=notebooks_tools,
        ),
        DomainModule(
            name="inference",
            description="Model Serving (KServe InferenceService) management",
            required_crds=["InferenceService"],
            register_tools=inference_tools,
        ),
        DomainModule(
            name="pipelines",
            description="Data Science Pipelines (DSPA) management",
            required_crds=["DataSciencePipelinesApplication"],
            register_tools=pipelines_tools,
        ),
        DomainModule(
            name="connections",
            description="Data Connection (S3 secrets) management",
            required_crds=[],
            register_tools=connections_tools,
            health_check=lambda _: (True, "Data connections use core Kubernetes API"),
        ),
        DomainModule(
            name="storage",
            description="Storage (PVC) management",
            required_crds=[],
            register_tools=storage_tools,
            health_check=lambda _: (True, "Storage uses core Kubernetes API"),
        ),
    ]
