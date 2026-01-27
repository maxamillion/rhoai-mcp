"""MCP Tools for Data Science Project operations."""

from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import FastMCP

from rhoai_mcp_core.domains.projects.client import ProjectClient
from rhoai_mcp_core.domains.projects.models import ProjectCreate

if TYPE_CHECKING:
    from rhoai_mcp_core.server import RHOAIServer


def register_tools(mcp: FastMCP, server: "RHOAIServer") -> None:
    """Register project management tools with the MCP server."""

    @mcp.tool()
    def list_data_science_projects() -> list[dict[str, Any]]:
        """List all Data Science Projects in the cluster.

        Returns projects (namespaces) that have the opendatahub.io/dashboard=true label,
        indicating they are RHOAI Data Science Projects.

        Returns:
            List of project information including name, display name, description,
            model serving mode, and status.
        """
        client = ProjectClient(server.k8s)
        projects = client.list_projects()
        return [
            {
                "name": p.metadata.name,
                "display_name": p.display_name,
                "description": p.description,
                "requester": p.requester,
                "is_modelmesh_enabled": p.is_modelmesh_enabled,
                "status": p.status.value,
                "created": (
                    p.metadata.creation_timestamp.isoformat()
                    if p.metadata.creation_timestamp
                    else None
                ),
            }
            for p in projects
        ]

    @mcp.tool()
    def get_project_details(
        name: str,
        include_resources: bool = True,
    ) -> dict[str, Any]:
        """Get detailed information about a Data Science Project.

        Args:
            name: The project (namespace) name.
            include_resources: Whether to include resource counts (workbenches, models, etc.).

        Returns:
            Detailed project information including metadata, settings, and optionally
            resource summary counts.
        """
        client = ProjectClient(server.k8s)
        project = client.get_project(name, include_summary=include_resources)

        result: dict[str, Any] = {
            "name": project.metadata.name,
            "display_name": project.display_name,
            "description": project.description,
            "requester": project.requester,
            "is_modelmesh_enabled": project.is_modelmesh_enabled,
            "status": project.status.value,
            "labels": project.metadata.labels,
            "annotations": project.metadata.annotations,
            "created": (
                project.metadata.creation_timestamp.isoformat()
                if project.metadata.creation_timestamp
                else None
            ),
        }

        if project.resource_summary:
            result["resources"] = {
                "workbenches": project.resource_summary.workbenches,
                "workbenches_running": project.resource_summary.workbenches_running,
                "models": project.resource_summary.models,
                "models_ready": project.resource_summary.models_ready,
                "pipelines": project.resource_summary.pipelines,
                "data_connections": project.resource_summary.data_connections,
                "storage": project.resource_summary.storage,
            }

        return result

    @mcp.tool()
    def create_data_science_project(
        name: str,
        display_name: str | None = None,
        description: str | None = None,
        enable_modelmesh: bool = False,
    ) -> dict[str, Any]:
        """Create a new Data Science Project.

        Creates a Kubernetes namespace with the appropriate labels and annotations
        to be recognized as an RHOAI Data Science Project.

        Args:
            name: Project name (will be the namespace name, must be DNS-compatible).
            display_name: Human-readable display name for the project.
            description: Project description.
            enable_modelmesh: Enable ModelMesh (multi-model) serving. Default is
                single-model (KServe) serving.

        Returns:
            The created project information.
        """
        # Check if operation is allowed
        allowed, reason = server.config.is_operation_allowed("create")
        if not allowed:
            return {"error": reason}

        client = ProjectClient(server.k8s)
        request = ProjectCreate(
            name=name,
            display_name=display_name,
            description=description,
            enable_modelmesh=enable_modelmesh,
        )
        project = client.create_project(request)

        return {
            "name": project.metadata.name,
            "display_name": project.display_name,
            "description": project.description,
            "is_modelmesh_enabled": project.is_modelmesh_enabled,
            "status": project.status.value,
            "message": f"Project '{name}' created successfully",
        }

    @mcp.tool()
    def delete_data_science_project(
        name: str,
        confirm: bool = False,
    ) -> dict[str, Any]:
        """Delete a Data Science Project.

        WARNING: This deletes the entire namespace and ALL resources within it,
        including workbenches, models, pipelines, data connections, and storage.

        Args:
            name: The project (namespace) name to delete.
            confirm: Must be True to actually delete. This is a safety measure.

        Returns:
            Confirmation of deletion or error message.
        """
        # Check if operation is allowed
        allowed, reason = server.config.is_operation_allowed("delete")
        if not allowed:
            return {"error": reason}

        if not confirm:
            return {
                "error": "Deletion not confirmed",
                "message": (
                    f"To delete project '{name}', set confirm=True. "
                    "WARNING: This will delete ALL resources in the project."
                ),
            }

        client = ProjectClient(server.k8s)
        client.delete_project(name)

        return {
            "name": name,
            "deleted": True,
            "message": f"Project '{name}' deletion initiated",
        }

    @mcp.tool()
    def set_model_serving_mode(
        name: str,
        enable_modelmesh: bool,
    ) -> dict[str, Any]:
        """Set the model serving mode for a project.

        Args:
            name: The project (namespace) name.
            enable_modelmesh: True for multi-model serving (ModelMesh),
                False for single-model serving (KServe).

        Returns:
            Updated project information.

        Note:
            Changing the model serving mode may affect existing deployed models.
            It's recommended to remove existing models before changing modes.
        """
        # Check if operation is allowed
        allowed, reason = server.config.is_operation_allowed("update")
        if not allowed:
            return {"error": reason}

        client = ProjectClient(server.k8s)
        project = client.set_model_serving_mode(name, enable_modelmesh)

        mode = "multi-model (ModelMesh)" if enable_modelmesh else "single-model (KServe)"

        return {
            "name": project.metadata.name,
            "is_modelmesh_enabled": project.is_modelmesh_enabled,
            "message": f"Model serving mode set to {mode}",
        }
