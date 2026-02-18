"""MCP Tools for Data Science Project operations.

Note: list_data_science_projects and get_project_details have been consolidated
into the cluster composite tools (list_resources, get_resource, project_summary).
"""

from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import FastMCP

from rhoai_mcp.domains.projects.client import ProjectClient
from rhoai_mcp.domains.projects.models import ProjectCreate

if TYPE_CHECKING:
    from rhoai_mcp.server import RHOAIServer


def register_tools(mcp: FastMCP, server: "RHOAIServer") -> None:
    """Register project management tools with the MCP server."""

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
            "_source": project.metadata.to_source_dict(),
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
            "_source": {
                "kind": "Project",
                "api_version": "project.openshift.io/v1",
                "name": name,
                "namespace": None,
                "uid": None,
            },
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
            "_source": project.metadata.to_source_dict(),
        }
