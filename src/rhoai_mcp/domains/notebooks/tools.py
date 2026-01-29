"""MCP Tools for Notebook (Workbench) operations."""

from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import FastMCP

from rhoai_mcp.domains.notebooks.client import NotebookClient
from rhoai_mcp.domains.notebooks.models import WorkbenchCreate
from rhoai_mcp.tools.metadata import ToolExample, ToolMetadata, register_tool_metadata
from rhoai_mcp.utils.response import (
    PaginatedResponse,
    ResponseBuilder,
    Verbosity,
    paginate,
)

if TYPE_CHECKING:
    from rhoai_mcp.server import RHOAIServer


def _register_tool_metadata() -> None:
    """Register metadata for notebook domain tools."""
    # list_workbenches
    register_tool_metadata(
        ToolMetadata(
            name="list_workbenches",
            display_name="List Workbenches",
            description="List all workbenches (Jupyter notebook environments) in a project.",
            domain="notebooks",
            examples=[
                ToolExample(
                    name="basic_list",
                    description="List all workbenches in a project",
                    arguments={"namespace": "my-project"},
                    expected_result_summary="Paginated list of workbenches with names and status",
                    tags=["quick", "basic"],
                ),
                ToolExample(
                    name="minimal_verbosity",
                    description="List workbenches with minimal output to save tokens",
                    arguments={"namespace": "my-project", "verbosity": "minimal"},
                    expected_result_summary="Compact list with only names and status",
                    tags=["quick", "efficient"],
                ),
            ],
            prerequisites=["list_projects"],
            related_tools=["get_workbench", "create_workbench"],
            common_mistakes=[
                "Using wrong namespace name - use list_projects first to verify",
            ],
            tags=["read", "list"],
        )
    )

    # get_workbench
    register_tool_metadata(
        ToolMetadata(
            name="get_workbench",
            display_name="Get Workbench Details",
            description="Get detailed information about a specific workbench.",
            domain="notebooks",
            examples=[
                ToolExample(
                    name="full_details",
                    description="Get complete workbench information",
                    arguments={"name": "my-workbench", "namespace": "my-project"},
                    expected_result_summary="Full workbench details including resources, status, URL",
                    tags=["basic"],
                ),
                ToolExample(
                    name="status_check",
                    description="Quick status check with minimal output",
                    arguments={
                        "name": "my-workbench",
                        "namespace": "my-project",
                        "verbosity": "minimal",
                    },
                    expected_result_summary="Name and current status only",
                    tags=["quick"],
                ),
            ],
            prerequisites=["list_workbenches"],
            related_tools=["get_workbench_url", "start_workbench", "stop_workbench"],
            tags=["read", "detail"],
        )
    )

    # create_workbench
    register_tool_metadata(
        ToolMetadata(
            name="create_workbench",
            display_name="Create Workbench",
            description="Create a new Jupyter notebook workbench in a project.",
            domain="notebooks",
            examples=[
                ToolExample(
                    name="minimal_workbench",
                    description="Create a basic workbench with defaults",
                    arguments={
                        "name": "my-workbench",
                        "namespace": "my-project",
                        "image": "jupyter-datascience-notebook:2024.1",
                    },
                    expected_result_summary="Created workbench with name, status, and URL",
                    tags=["basic"],
                ),
                ToolExample(
                    name="gpu_workbench",
                    description="Create a GPU-enabled workbench for ML training",
                    arguments={
                        "name": "ml-workbench",
                        "namespace": "ml-project",
                        "image": "pytorch-notebook:2024.1",
                        "gpu_count": 1,
                        "size": "Large",
                        "storage_size": "50Gi",
                    },
                    expected_result_summary="GPU workbench created and starting",
                    tags=["gpu", "ml"],
                ),
                ToolExample(
                    name="workbench_with_connections",
                    description="Create workbench with S3 data connections mounted",
                    arguments={
                        "name": "data-workbench",
                        "namespace": "my-project",
                        "image": "jupyter-datascience-notebook:2024.1",
                        "data_connections": ["my-s3-connection"],
                    },
                    expected_result_summary="Workbench with S3 credentials as env vars",
                    tags=["data", "s3"],
                ),
            ],
            prerequisites=["list_notebook_images", "list_projects"],
            related_tools=["get_workbench", "get_workbench_url", "list_data_connections"],
            common_mistakes=[
                "Using invalid image name - call list_notebook_images first",
                "Using non-DNS-compatible name (uppercase, spaces, underscores)",
                "Requesting GPUs when none are available in cluster",
                "Not checking project exists before creating workbench",
            ],
            error_guidance={
                "ImagePullBackOff": "Image not found. Use list_notebook_images to get valid images.",
                "GPU unavailable": "No GPUs available. Set gpu_count=0 or check accelerator profiles.",
                "exceeded quota": "Reduce resource requests or contact administrator.",
                "already exists": "Workbench name taken. Use a different name.",
            },
            tags=["write", "create"],
        )
    )

    # start_workbench
    register_tool_metadata(
        ToolMetadata(
            name="start_workbench",
            display_name="Start Workbench",
            description="Start a stopped workbench.",
            domain="notebooks",
            examples=[
                ToolExample(
                    name="start",
                    description="Start a stopped workbench",
                    arguments={"name": "my-workbench", "namespace": "my-project"},
                    expected_result_summary="Workbench is starting with updated status",
                    tags=["basic"],
                ),
            ],
            prerequisites=["get_workbench"],
            related_tools=["stop_workbench", "get_workbench"],
            common_mistakes=[
                "Starting an already running workbench (harmless but unnecessary)",
            ],
            tags=["write", "lifecycle"],
        )
    )

    # stop_workbench
    register_tool_metadata(
        ToolMetadata(
            name="stop_workbench",
            display_name="Stop Workbench",
            description="Stop a running workbench to free resources.",
            domain="notebooks",
            examples=[
                ToolExample(
                    name="stop",
                    description="Stop a running workbench",
                    arguments={"name": "my-workbench", "namespace": "my-project"},
                    expected_result_summary="Workbench is stopping, data preserved",
                    tags=["basic"],
                ),
            ],
            prerequisites=["get_workbench"],
            related_tools=["start_workbench", "get_workbench"],
            tags=["write", "lifecycle"],
        )
    )

    # delete_workbench
    register_tool_metadata(
        ToolMetadata(
            name="delete_workbench",
            display_name="Delete Workbench",
            description="Permanently delete a workbench. PVC is preserved.",
            domain="notebooks",
            examples=[
                ToolExample(
                    name="delete_confirmed",
                    description="Delete a workbench with confirmation",
                    arguments={
                        "name": "my-workbench",
                        "namespace": "my-project",
                        "confirm": True,
                    },
                    expected_result_summary="Workbench deleted, PVC preserved",
                    tags=["dangerous"],
                ),
            ],
            prerequisites=["get_workbench"],
            related_tools=["create_workbench", "list_storage"],
            common_mistakes=[
                "Forgetting to set confirm=True",
                "Expecting PVC to be deleted (it's preserved)",
            ],
            tags=["write", "delete", "dangerous"],
        )
    )

    # list_notebook_images
    register_tool_metadata(
        ToolMetadata(
            name="list_notebook_images",
            display_name="List Notebook Images",
            description="List available container images for workbenches.",
            domain="notebooks",
            examples=[
                ToolExample(
                    name="list_images",
                    description="Get all available notebook images",
                    arguments={},
                    expected_result_summary="List of images with names and descriptions",
                    tags=["quick", "basic"],
                ),
            ],
            related_tools=["create_workbench"],
            tags=["read", "list"],
        )
    )

    # get_workbench_url
    register_tool_metadata(
        ToolMetadata(
            name="get_workbench_url",
            display_name="Get Workbench URL",
            description="Get the access URL for a running workbench.",
            domain="notebooks",
            examples=[
                ToolExample(
                    name="get_url",
                    description="Get the browser access URL",
                    arguments={"name": "my-workbench", "namespace": "my-project"},
                    expected_result_summary="URL and status indicating accessibility",
                    tags=["quick", "basic"],
                ),
            ],
            prerequisites=["get_workbench"],
            related_tools=["start_workbench"],
            common_mistakes=[
                "Getting URL before workbench is Running (URL exists but not accessible)",
            ],
            tags=["read"],
        )
    )


# Register metadata on module load
_register_tool_metadata()


def register_tools(mcp: FastMCP, server: "RHOAIServer") -> None:
    """Register workbench management tools with the MCP server."""

    @mcp.tool()
    def list_workbenches(
        namespace: str,
        limit: int | None = None,
        offset: int = 0,
        verbosity: str = "standard",
    ) -> dict[str, Any]:
        """List workbenches in a Data Science Project with pagination.

        Workbenches are Jupyter notebook environments or other IDE environments
        running in the project.

        Args:
            namespace: The project (namespace) name.
            limit: Maximum number of items to return (None for all).
            offset: Starting offset for pagination (default: 0).
            verbosity: Response detail level - "minimal", "standard", or "full".
                Use "minimal" for quick status checks (~85% token savings).

        Returns:
            Paginated list of workbenches with metadata.
        """
        client = NotebookClient(server.k8s)
        workbenches = client.list_workbenches(namespace)

        # Apply config limits
        effective_limit = limit
        if effective_limit is not None:
            effective_limit = min(effective_limit, server.config.max_list_limit)
        elif server.config.default_list_limit is not None:
            effective_limit = server.config.default_list_limit

        # Paginate
        paginated, total = paginate(workbenches, offset, effective_limit)

        # Format with verbosity
        v = Verbosity.from_str(verbosity)
        items = [ResponseBuilder.workbench_list_item(wb, v) for wb in paginated]

        return PaginatedResponse.build(items, total, offset, effective_limit)

    @mcp.tool()
    def get_workbench(
        name: str,
        namespace: str,
        verbosity: str = "full",
    ) -> dict[str, Any]:
        """Get detailed information about a workbench.

        Args:
            name: The workbench name.
            namespace: The project (namespace) name.
            verbosity: Response detail level - "minimal", "standard", or "full".
                Use "minimal" for quick status checks.

        Returns:
            Workbench information at the requested verbosity level.
        """
        client = NotebookClient(server.k8s)
        wb = client.get_workbench(name, namespace)

        v = Verbosity.from_str(verbosity)
        return ResponseBuilder.workbench_detail(wb, v)

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
        }

    @mcp.tool()
    def start_workbench(name: str, namespace: str) -> dict[str, Any]:
        """Start a stopped workbench.

        Removes the kubeflow-resource-stopped annotation to allow the
        workbench pod to be scheduled.

        Args:
            name: The workbench name.
            namespace: The project (namespace) name.

        Returns:
            Updated workbench status.
        """
        # Check if operation is allowed
        allowed, reason = server.config.is_operation_allowed("update")
        if not allowed:
            return {"error": reason}

        client = NotebookClient(server.k8s)
        wb = client.start_workbench(name, namespace)

        return {
            "name": wb.metadata.name,
            "status": wb.status.value,
            "url": wb.url,
            "message": f"Workbench '{name}' is starting",
        }

    @mcp.tool()
    def stop_workbench(name: str, namespace: str) -> dict[str, Any]:
        """Stop a running workbench.

        Adds the kubeflow-resource-stopped annotation which causes the
        workbench pod to be terminated. The workbench can be restarted later.

        Args:
            name: The workbench name.
            namespace: The project (namespace) name.

        Returns:
            Updated workbench status.
        """
        # Check if operation is allowed
        allowed, reason = server.config.is_operation_allowed("update")
        if not allowed:
            return {"error": reason}

        client = NotebookClient(server.k8s)
        wb = client.stop_workbench(name, namespace)

        return {
            "name": wb.metadata.name,
            "status": wb.status.value,
            "stopped_time": wb.stopped_time.isoformat() if wb.stopped_time else None,
            "message": f"Workbench '{name}' is stopping",
        }

    @mcp.tool()
    def delete_workbench(
        name: str,
        namespace: str,
        confirm: bool = False,
    ) -> dict[str, Any]:
        """Delete a workbench.

        WARNING: This permanently deletes the workbench. The associated PVC
        is NOT automatically deleted to preserve data.

        Args:
            name: The workbench name.
            namespace: The project (namespace) name.
            confirm: Must be True to actually delete.

        Returns:
            Confirmation of deletion.
        """
        # Check if operation is allowed
        allowed, reason = server.config.is_operation_allowed("delete")
        if not allowed:
            return {"error": reason}

        if not confirm:
            return {
                "error": "Deletion not confirmed",
                "message": (
                    f"To delete workbench '{name}', set confirm=True. "
                    "Note: The workbench PVC will be preserved."
                ),
            }

        client = NotebookClient(server.k8s)
        client.delete_workbench(name, namespace)

        return {
            "name": name,
            "namespace": namespace,
            "deleted": True,
            "message": f"Workbench '{name}' deleted. PVC '{name}-pvc' was preserved.",
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
