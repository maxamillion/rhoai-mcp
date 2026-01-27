"""Training domain module for Kubeflow Training Operator integration.

This module provides MCP tools for managing training jobs, training runtimes,
and related resources on Red Hat OpenShift AI.
"""

from rhoai_mcp_core.domains.training.client import TrainingClient
from rhoai_mcp_core.domains.training.crds import TrainingCRDs
from rhoai_mcp_core.domains.training.models import (
    ClusterResources,
    GPUInfo,
    NodeResources,
    PeftMethod,
    ResourceEstimate,
    TrainingProgress,
    TrainingRuntime,
    TrainingState,
    TrainJob,
    TrainJobStatus,
)
from rhoai_mcp_core.domains.training.tools import register_tools

__all__ = [
    # Client
    "TrainingClient",
    # CRDs
    "TrainingCRDs",
    # Models
    "ClusterResources",
    "GPUInfo",
    "NodeResources",
    "PeftMethod",
    "ResourceEstimate",
    "TrainJob",
    "TrainJobStatus",
    "TrainingProgress",
    "TrainingRuntime",
    "TrainingState",
    # Tool registration
    "register_tools",
]
