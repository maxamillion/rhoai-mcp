"""MCP Tools for training job discovery.

Note: list_training_jobs and get_training_job have been consolidated into
the unified training() tool (action="list" / action="get").
"""

from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import FastMCP

from rhoai_mcp.domains.training.client import TrainingClient

if TYPE_CHECKING:
    from rhoai_mcp.server import RHOAIServer


def register_tools(mcp: FastMCP, server: "RHOAIServer") -> None:
    """Register training discovery tools with the MCP server."""

    @mcp.tool()
    def get_cluster_resources() -> dict[str, Any]:
        """Get cluster-wide compute resources available for training.

        Returns information about CPU, memory, and GPU resources across
        all nodes in the cluster. Useful for planning training jobs and
        understanding cluster capacity.

        Returns:
            Cluster resource summary including CPU, memory, and GPU info.
        """
        client = TrainingClient(server.k8s)
        resources = client.get_cluster_resources()

        result: dict[str, Any] = {
            "cpu_total": resources.cpu_total,
            "cpu_allocatable": resources.cpu_allocatable,
            "memory_total_gb": round(resources.memory_total_gb, 1),
            "memory_allocatable_gb": round(resources.memory_allocatable_gb, 1),
            "node_count": resources.node_count,
            "has_gpus": resources.has_gpus,
        }

        if resources.gpu_info:
            result["gpu_info"] = {
                "type": resources.gpu_info.type,
                "product": resources.gpu_info.product,
                "products": resources.gpu_info.products,
                "total": resources.gpu_info.total,
                "available": resources.gpu_info.available,
                "nodes_with_gpu": resources.gpu_info.nodes_with_gpu,
            }

        # Include per-node details
        result["nodes"] = [
            {
                "name": node.name,
                "cpu": node.cpu_allocatable,
                "memory_gb": round(node.memory_allocatable_gb, 1),
                "gpus": node.gpu_count,
                "gpu_product": node.gpu_product,
            }
            for node in resources.nodes
        ]

        return result

    @mcp.tool()
    def list_training_runtimes(namespace: str | None = None) -> dict[str, Any]:
        """List available training runtimes.

        Training runtimes define the container images, frameworks, and
        configurations used for training jobs. This includes both
        cluster-scoped and namespace-scoped runtimes.

        Args:
            namespace: Optional namespace to include namespace-scoped runtimes.

        Returns:
            List of available training runtimes.
        """
        client = TrainingClient(server.k8s)

        # Always get cluster-scoped runtimes
        runtimes = client.list_cluster_training_runtimes()

        # Optionally include namespace-scoped runtimes
        if namespace:
            ns_runtimes = client.list_training_runtimes(namespace)
            runtimes.extend(ns_runtimes)

        runtime_list = []
        for runtime in runtimes:
            runtime_list.append(
                {
                    "name": runtime.name,
                    "namespace": runtime.namespace,
                    "framework": runtime.framework,
                    "has_model_initializer": runtime.has_model_initializer,
                    "has_dataset_initializer": runtime.has_dataset_initializer,
                    "scope": "cluster" if runtime.namespace is None else "namespace",
                }
            )

        return {
            "count": len(runtime_list),
            "runtimes": runtime_list,
        }
