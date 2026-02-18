"""MCP Tools for Storage (PVC) operations.

Note: list_storage has been consolidated into the cluster composite tool
list_resources(resource_type="storage").
"""

from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import FastMCP

from rhoai_mcp.domains.storage.client import StorageClient
from rhoai_mcp.domains.storage.models import StorageCreate

if TYPE_CHECKING:
    from rhoai_mcp.server import RHOAIServer


def register_tools(mcp: FastMCP, server: "RHOAIServer") -> None:
    """Register storage tools with the MCP server."""

    @mcp.tool()
    def create_storage(
        name: str,
        namespace: str,
        size: str = "10Gi",
        display_name: str | None = None,
        access_mode: str = "ReadWriteOnce",
        storage_class: str | None = None,
    ) -> dict[str, Any]:
        """Create a new persistent storage volume (PVC).

        Creates a PersistentVolumeClaim that can be mounted by workbenches
        or other pods in the project.

        Args:
            name: PVC name (must be DNS-compatible).
            namespace: Project (namespace) name.
            size: Storage size (e.g., '10Gi', '100Gi').
            display_name: Human-readable display name.
            access_mode: Access mode - ReadWriteOnce, ReadOnlyMany, or ReadWriteMany.
            storage_class: Storage class name (uses cluster default if not specified).

        Returns:
            Created storage information.
        """
        # Check if operation is allowed
        allowed, reason = server.config.is_operation_allowed("create")
        if not allowed:
            return {"error": reason}

        client = StorageClient(server.k8s)
        request = StorageCreate(
            name=name,
            namespace=namespace,
            display_name=display_name,
            size=size,
            access_mode=access_mode,
            storage_class=storage_class,
        )
        storage = client.create_storage(request)

        return {
            "name": storage.metadata.name,
            "namespace": storage.metadata.namespace,
            "size": storage.size,
            "status": storage.status.value,
            "message": f"Storage '{name}' created successfully",
            "_source": storage.metadata.to_source_dict(),
        }

    @mcp.tool()
    def delete_storage(
        name: str,
        namespace: str,
        confirm: bool = False,
    ) -> dict[str, Any]:
        """Delete a persistent storage volume (PVC).

        WARNING: This permanently deletes the PVC and all data stored in it.
        This operation cannot be undone.

        Args:
            name: The PVC name.
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
                    f"To delete storage '{name}', set confirm=True. "
                    "WARNING: All data in this PVC will be permanently lost."
                ),
            }

        client = StorageClient(server.k8s)
        client.delete_storage(name, namespace)

        return {
            "name": name,
            "namespace": namespace,
            "deleted": True,
            "message": f"Storage '{name}' deleted",
            "_source": {
                "kind": "PersistentVolumeClaim",
                "api_version": "v1",
                "name": name,
                "namespace": namespace,
                "uid": None,
            },
        }
