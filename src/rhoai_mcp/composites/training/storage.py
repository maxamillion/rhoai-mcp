"""MCP Tools for training storage management."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import FastMCP

from rhoai_mcp.utils.errors import NotFoundError, ResourceExistsError, RHOAIError

if TYPE_CHECKING:
    from rhoai_mcp.clients.base import K8sClient
    from rhoai_mcp.server import RHOAIServer

logger = logging.getLogger(__name__)


def create_training_pvc(
    k8s: K8sClient,
    namespace: str,
    pvc_name: str,
    size_gb: int,
    access_mode: str = "ReadWriteMany",
    storage_class: str | None = None,
) -> dict[str, Any]:
    """Create a PVC for training checkpoints and data.

    This is the shared implementation used by both setup_training_storage
    and prepare_training tools.

    Args:
        k8s: Kubernetes client instance.
        namespace: The namespace to create the PVC in.
        pvc_name: Name for the PVC.
        size_gb: Size in GB (must be >= 1).
        access_mode: Access mode (default: "ReadWriteMany" for distributed training).
        storage_class: Storage class to use (auto-detected if not specified).

    Returns:
        PVC creation result with success/error status.
    """
    # Validate size_gb
    if size_gb < 1:
        return {"error": "size_gb must be >= 1", "created": False}

    # Check if PVC already exists
    try:
        existing = k8s.get_pvc(pvc_name, namespace)
        # Defensive access pattern to avoid AttributeError
        size = "Unknown"
        if existing.spec and existing.spec.resources and existing.spec.resources.requests:
            size = existing.spec.resources.requests.get("storage", "Unknown")
        status = existing.status.phase if existing.status else "Unknown"
        return {
            "exists": True,
            "created": False,
            "pvc_name": pvc_name,
            "namespace": namespace,
            "size": size,
            "status": status,
            "message": f"PVC '{pvc_name}' already exists.",
        }
    except NotFoundError:
        pass  # PVC doesn't exist, proceed to create

    # If no storage class specified, try to find an NFS or RWX-capable one
    if not storage_class and access_mode == "ReadWriteMany":
        storage_class = _find_rwx_storage_class(k8s)

    # Create the PVC
    try:
        k8s.create_pvc(
            name=pvc_name,
            namespace=namespace,
            size=f"{size_gb}Gi",
            access_modes=[access_mode],
            storage_class=storage_class,
            labels={
                "app.kubernetes.io/managed-by": "rhoai-mcp",
                "app.kubernetes.io/component": "training-storage",
            },
        )

        return {
            "exists": False,
            "created": True,
            "pvc_name": pvc_name,
            "namespace": namespace,
            "size": f"{size_gb}Gi",
            "access_mode": access_mode,
            "storage_class": storage_class,
            "message": f"PVC '{pvc_name}' created. It may take a moment to bind.",
        }
    except ResourceExistsError:
        # Race condition: PVC was created between check and create
        return {
            "exists": True,
            "created": False,
            "pvc_name": pvc_name,
            "namespace": namespace,
            "message": f"PVC '{pvc_name}' already exists.",
        }
    except RHOAIError as e:
        return {
            "error": f"Failed to create PVC: {e}",
            "created": False,
        }


def register_tools(mcp: FastMCP, server: RHOAIServer) -> None:
    """Register training storage tools with the MCP server."""

    @mcp.tool()
    def setup_training_storage(
        namespace: str,
        pvc_name: str,
        size_gb: int = 100,
        storage_class: str | None = None,
        access_mode: str = "ReadWriteMany",
    ) -> dict[str, Any]:
        """Create a PVC for training checkpoints and data.

        Creates a PersistentVolumeClaim suitable for distributed training.
        Defaults to ReadWriteMany access mode to support multi-node training.

        Args:
            namespace: The namespace to create the PVC in.
            pvc_name: Name for the PVC.
            size_gb: Size in GB (default: 100).
            storage_class: Storage class to use (auto-detected if not specified).
            access_mode: Access mode (default: "ReadWriteMany" for distributed training).

        Returns:
            PVC creation confirmation.
        """
        # Check if operation is allowed
        allowed, reason = server.config.is_operation_allowed("create")
        if not allowed:
            return {"error": reason}

        result = create_training_pvc(
            k8s=server.k8s,
            namespace=namespace,
            pvc_name=pvc_name,
            size_gb=size_gb,
            access_mode=access_mode,
            storage_class=storage_class,
        )

        # Add success field for backward compatibility
        if result.get("created") or result.get("exists"):
            result["success"] = True

        return result

    # Note: list_storage and delete_storage are in domains/storage/tools.py
    # They are not registered here to avoid duplication.


def _find_rwx_storage_class(k8s: Any) -> str | None:
    """Find a storage class that supports ReadWriteMany."""
    # Common NFS/RWX storage class names
    common_names = [
        "nfs",
        "nfs-client",
        "nfs-csi",
        "ocs-storagecluster-cephfs",
        "managed-nfs-storage",
        "trident-nfs",
    ]

    try:
        # Try to list storage classes
        from kubernetes import client  # type: ignore[import-untyped]
        from kubernetes.client import ApiException  # type: ignore[import-untyped]
    except ImportError:
        logger.debug("kubernetes client not available for storage class detection")
        return None

    try:
        storage_api = client.StorageV1Api(k8s._api_client)
        storage_classes = storage_api.list_storage_class()

        for sc in storage_classes.items:
            name: str = sc.metadata.name
            if name.lower() in [n.lower() for n in common_names]:
                return name

        # Return first storage class as fallback
        if storage_classes.items:
            first_name: str = storage_classes.items[0].metadata.name
            return first_name
    except ApiException as e:
        logger.debug("Failed to auto-detect RWX storage class: %s", e)

    return None
