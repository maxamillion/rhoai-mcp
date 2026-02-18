"""MCP Tools for Notebook (Workbench) operations.

Note: list_workbenches, get_workbench, start_workbench, stop_workbench, and
delete_workbench have been consolidated into the cluster composite tools
(list_resources, get_resource, manage_resource).
"""

from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import FastMCP

from rhoai_mcp.domains.notebooks.client import NotebookClient
from rhoai_mcp.domains.notebooks.models import WorkbenchCreate

if TYPE_CHECKING:
    from rhoai_mcp.server import RHOAIServer


def register_tools(mcp: FastMCP, server: "RHOAIServer") -> None:
    """Register workbench management tools with the MCP server."""

    @mcp.tool()
    def create_workbench(
        name: str,
        namespace: str,
        image: str,
        display_name: str | None = None,
        size: str = "Small",
        cpu_request: str = "500m",
        cpu_limit: str = "2",
        memory_request: str = "1Gi",
        memory_limit: str = "4Gi",
        gpu_count: int = 0,
        storage_size: str = "10Gi",
        data_connections: list[str] | None = None,
        additional_pvcs: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new workbench (notebook environment).

        Creates a Kubeflow Notebook CR with the specified configuration,
        including a PVC for persistent storage.

        Args:
            name: Workbench name (must be DNS-compatible).
            namespace: Project (namespace) name.
            image: Container image to use (use list_notebook_images to see available options).
            display_name: Human-readable display name.
            size: Size selection name (Small, Medium, Large, X-Large).
            cpu_request: CPU request (e.g., '500m', '1').
            cpu_limit: CPU limit (e.g., '2', '4').
            memory_request: Memory request (e.g., '1Gi', '2Gi').
            memory_limit: Memory limit (e.g., '4Gi', '8Gi').
            gpu_count: Number of NVIDIA GPUs to request.
            storage_size: Size of the workbench PVC (e.g., '10Gi', '50Gi').
            data_connections: List of secret names to mount as environment variables.
            additional_pvcs: List of additional PVC names to mount.

        Returns:
            Created workbench information.
        """
        # Check if operation is allowed
        allowed, reason = server.config.is_operation_allowed("create")
        if not allowed:
            return {"error": reason}

        client = NotebookClient(server.k8s)
        request = WorkbenchCreate(
            name=name,
            namespace=namespace,
            display_name=display_name,
            image=image,
            size=size,
            cpu_request=cpu_request,
            cpu_limit=cpu_limit,
            memory_request=memory_request,
            memory_limit=memory_limit,
            gpu_count=gpu_count,
            storage_size=storage_size,
            data_connections=data_connections or [],
            additional_pvcs=additional_pvcs or [],
        )
        wb = client.create_workbench(request)

        return {
            "name": wb.metadata.name,
            "namespace": wb.metadata.namespace,
            "status": wb.status.value,
            "url": wb.url,
            "message": f"Workbench '{name}' created successfully. It will start automatically.",
            "_source": wb.metadata.to_source_dict(),
        }

    @mcp.tool()
    def list_notebook_images() -> list[dict[str, Any]]:
        """List available notebook images.

        Returns the standard RHOAI notebook images that can be used
        when creating workbenches.

        Returns:
            List of available images with display names and descriptions.
        """
        client = NotebookClient(server.k8s)
        images = client.list_notebook_images()

        return [
            {
                "name": img.name,
                "display_name": img.display_name,
                "description": img.description,
                "recommended": img.recommended,
            }
            for img in images
        ]

    @mcp.tool()
    def get_workbench_url(name: str, namespace: str) -> dict[str, Any]:
        """Get the access URL for a workbench.

        Returns the OAuth-protected route URL for accessing the workbench
        in a browser.

        Args:
            name: The workbench name.
            namespace: The project (namespace) name.

        Returns:
            The workbench URL and current status.
        """
        client = NotebookClient(server.k8s)
        wb = client.get_workbench(name, namespace)

        return {
            "name": wb.metadata.name,
            "namespace": wb.metadata.namespace,
            "url": wb.url,
            "status": wb.status.value,
            "message": (
                "Workbench is accessible at the URL"
                if wb.status.value == "Running"
                else f"Workbench is {wb.status.value} - URL may not be accessible"
            ),
        }
