"""MCP Tools for Model Serving (InferenceService) operations."""

from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import FastMCP

from rhoai_mcp.domains.inference.client import InferenceClient
from rhoai_mcp.domains.inference.models import InferenceServiceCreate

if TYPE_CHECKING:
    from rhoai_mcp.server import RHOAIServer


def register_tools(mcp: FastMCP, server: "RHOAIServer") -> None:
    """Register model serving tools with the MCP server."""

    @mcp.tool()
    def list_inference_services(namespace: str) -> list[dict[str, Any]]:
        """List all deployed models in a Data Science Project.

        Returns InferenceService resources representing deployed models
        that can serve predictions.

        Args:
            namespace: The project (namespace) name.

        Returns:
            List of deployed models with their status and endpoints.
        """
        client = InferenceClient(server.k8s)
        return client.list_inference_services(namespace)

    @mcp.tool()
    def get_inference_service(name: str, namespace: str) -> dict[str, Any]:
        """Get detailed information about a deployed model.

        Args:
            name: The InferenceService name.
            namespace: The project (namespace) name.

        Returns:
            Detailed model deployment information including status, endpoints,
            and resource configuration.
        """
        client = InferenceClient(server.k8s)
        isvc = client.get_inference_service(name, namespace)

        result: dict[str, Any] = {
            "name": isvc.metadata.name,
            "namespace": isvc.metadata.namespace,
            "display_name": isvc.display_name,
            "runtime": isvc.runtime,
            "model_format": isvc.model_format,
            "storage_uri": isvc.storage_uri,
            "status": isvc.status.value,
            "url": isvc.url,
            "internal_url": isvc.internal_url,
            "labels": isvc.metadata.labels,
            "annotations": isvc.metadata.annotations,
            "created": (
                isvc.metadata.creation_timestamp.isoformat()
                if isvc.metadata.creation_timestamp
                else None
            ),
        }

        if isvc.resources:
            result["resources"] = {
                "cpu_request": isvc.resources.cpu_request,
                "cpu_limit": isvc.resources.cpu_limit,
                "memory_request": isvc.resources.memory_request,
                "memory_limit": isvc.resources.memory_limit,
                "gpu_request": isvc.resources.gpu_request,
                "gpu_limit": isvc.resources.gpu_limit,
            }

        if isvc.conditions:
            result["conditions"] = [
                {
                    "type": c.type,
                    "status": c.status,
                    "reason": c.reason,
                    "message": c.message,
                }
                for c in isvc.conditions
            ]

        return result

    @mcp.tool()
    def deploy_model(
        name: str,
        namespace: str,
        runtime: str,
        model_format: str,
        storage_uri: str,
        display_name: str | None = None,
        min_replicas: int = 1,
        max_replicas: int = 1,
        cpu_request: str = "1",
        cpu_limit: str = "2",
        memory_request: str = "4Gi",
        memory_limit: str = "8Gi",
        gpu_count: int = 0,
    ) -> dict[str, Any]:
        """Deploy a model as an InferenceService.

        Creates a KServe InferenceService to serve model predictions.

        Args:
            name: Deployment name (must be DNS-compatible).
            namespace: Project (namespace) name.
            runtime: Serving runtime to use (use list_serving_runtimes to see options).
            model_format: Model format (onnx, pytorch, tensorflow, sklearn, etc.).
            storage_uri: Model location (s3://bucket/path or pvc://pvc-name/path).
            display_name: Human-readable display name.
            min_replicas: Minimum number of replicas (0 for scale-to-zero).
            max_replicas: Maximum number of replicas.
            cpu_request: CPU request per replica.
            cpu_limit: CPU limit per replica.
            memory_request: Memory request per replica.
            memory_limit: Memory limit per replica.
            gpu_count: Number of GPUs per replica.

        Returns:
            Created InferenceService information.
        """
        # Check if operation is allowed
        allowed, reason = server.config.is_operation_allowed("create")
        if not allowed:
            return {"error": reason}

        client = InferenceClient(server.k8s)
        request = InferenceServiceCreate(
            name=name,
            namespace=namespace,
            display_name=display_name,
            runtime=runtime,
            model_format=model_format,
            storage_uri=storage_uri,
            min_replicas=min_replicas,
            max_replicas=max_replicas,
            cpu_request=cpu_request,
            cpu_limit=cpu_limit,
            memory_request=memory_request,
            memory_limit=memory_limit,
            gpu_count=gpu_count,
        )
        isvc = client.deploy_model(request)

        return {
            "name": isvc.metadata.name,
            "namespace": isvc.metadata.namespace,
            "status": isvc.status.value,
            "message": f"Model '{name}' deployment initiated. It may take a few minutes to become ready.",
        }

    @mcp.tool()
    def delete_inference_service(
        name: str,
        namespace: str,
        confirm: bool = False,
    ) -> dict[str, Any]:
        """Delete a deployed model.

        Args:
            name: The InferenceService name.
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
                "message": f"To delete model deployment '{name}', set confirm=True.",
            }

        client = InferenceClient(server.k8s)
        client.delete_inference_service(name, namespace)

        return {
            "name": name,
            "namespace": namespace,
            "deleted": True,
            "message": f"Model deployment '{name}' deleted",
        }

    @mcp.tool()
    def list_serving_runtimes(namespace: str) -> list[dict[str, Any]]:
        """List available model serving runtimes.

        Serving runtimes define the model server that will be used to serve
        predictions (e.g., OpenVINO, vLLM, TGIS, etc.).

        Args:
            namespace: The project (namespace) name.

        Returns:
            List of available serving runtimes with supported model formats.
        """
        client = InferenceClient(server.k8s)
        return client.list_serving_runtimes(namespace)

    @mcp.tool()
    def get_model_endpoint(name: str, namespace: str) -> dict[str, Any]:
        """Get the inference endpoint URL for a deployed model.

        Returns the URL that can be used to send prediction requests
        to the model.

        Args:
            name: The InferenceService name.
            namespace: The project (namespace) name.

        Returns:
            Model endpoint information including URL and status.
        """
        client = InferenceClient(server.k8s)
        result = client.get_model_endpoint(name, namespace)

        if result["status"] == "Ready":
            result["message"] = "Model is ready to accept prediction requests"
        else:
            result["message"] = f"Model is {result['status']} - endpoint may not be available"

        return result
