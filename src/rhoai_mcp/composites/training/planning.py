"""MCP Tools for training resource planning and validation.

Note: estimate_resources, check_training_prerequisites, and validate_training_config
have been consolidated into the unified training() tool
(action="estimate"/"prerequisites"/"validate").
"""

from __future__ import annotations

import hashlib
import re
from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import FastMCP

from rhoai_mcp.domains.training.client import TrainingClient
from rhoai_mcp.domains.training.models import (
    GPU_MEMORY_ESTIMATES,
    PEFT_MULTIPLIERS,
    PeftMethod,
)
from rhoai_mcp.utils.errors import NotFoundError

if TYPE_CHECKING:
    from rhoai_mcp.server import RHOAIServer


def register_tools(mcp: FastMCP, server: RHOAIServer) -> None:
    """Register training planning tools with the MCP server."""

    @mcp.tool()
    def setup_hf_credentials(
        namespace: str,
        token: str,
        secret_name: str = "hf-token",
    ) -> dict[str, Any]:
        """Set up HuggingFace credentials for model/dataset access.

        Creates a Kubernetes secret containing the HuggingFace API token.
        This is required for accessing gated models or private datasets.

        Args:
            namespace: The namespace to create the secret in.
            token: HuggingFace API token.
            secret_name: Name for the secret (default: "hf-token").

        Returns:
            Secret creation confirmation with usage instructions.
        """
        # Check if operation is allowed
        allowed, reason = server.config.is_operation_allowed("create")
        if not allowed:
            return {"error": reason}

        # Validate token format (should start with hf_)
        if not token.startswith("hf_"):
            return {
                "error": "Invalid token format",
                "message": "HuggingFace tokens should start with 'hf_'",
            }

        # Create or update secret
        try:
            # Check if secret exists
            try:
                server.k8s.get_secret(secret_name, namespace)
                # Secret exists, delete it first
                server.k8s.delete_secret(secret_name, namespace)
            except Exception:
                pass  # Secret doesn't exist

            # Create the secret
            server.k8s.create_secret(
                name=secret_name,
                namespace=namespace,
                data={"token": token},
                labels={
                    "app.kubernetes.io/managed-by": "rhoai-mcp",
                    "app.kubernetes.io/component": "hf-credentials",
                },
            )

            return {
                "success": True,
                "secret_name": secret_name,
                "namespace": namespace,
                "message": f"HuggingFace credentials stored in secret '{secret_name}'.",
                "usage": (
                    "The token will be automatically used by training jobs "
                    "that reference this secret."
                ),
            }
        except Exception as e:
            return {
                "error": f"Failed to create secret: {e}",
            }

    @mcp.tool()
    def prepare_training(
        namespace: str,
        model_id: str,
        dataset_id: str,
        runtime_name: str | None = None,
        method: str = "lora",
        create_storage: bool = True,
        storage_size_gb: int = 100,
    ) -> dict[str, Any]:
        """Complete pre-flight setup for a training job in a single call.

        This composite tool combines resource estimation, prerequisite checking,
        configuration validation, and optional storage creation. Use this before
        calling train() to ensure everything is ready.

        Args:
            namespace: The namespace for the training job.
            model_id: Model identifier (e.g., "meta-llama/Llama-2-7b-hf").
            dataset_id: Dataset identifier (e.g., "tatsu-lab/alpaca").
            runtime_name: Training runtime to use (auto-selected if None).
            method: Fine-tuning method: "lora", "qlora", "dora", or "full".
            create_storage: Whether to create checkpoint storage if needed.
            storage_size_gb: Size of checkpoint storage in GB.

        Returns:
            Complete preparation result with:
            - ready: Whether training can proceed
            - issues: List of problems found
            - resource_estimate: GPU/memory requirements
            - recommended_runtime: Runtime to use
            - storage_created: Whether storage was created
            - next_action: "train" or "fix_issues"
            - suggested_train_params: Parameters for train() call
        """
        from rhoai_mcp.composites.training.storage import create_training_pvc

        issues: list[str] = []
        warnings: list[str] = []
        storage_created = False
        recommended_runtime = runtime_name
        prereq_passed = True

        # Validate and normalize method parameter
        valid_methods = {"lora", "qlora", "dora", "full"}
        method = method.lower()
        if method not in valid_methods:
            issues.append(
                f"Invalid fine-tuning method: {method}. Must be one of: {', '.join(valid_methods)}"
            )
            prereq_passed = False

        # Step 1: Estimate resources
        resource_estimate = _estimate_resources_internal(model_id, method)

        # Step 2: Check prerequisites
        client = TrainingClient(server.k8s)

        # Check cluster connectivity and GPUs
        try:
            resources = client.get_cluster_resources()
            if not resources.has_gpus:
                issues.append("No GPUs available in cluster")
                prereq_passed = False
            elif resources.gpu_info:
                gpu_available = resources.gpu_info.available
                required = resource_estimate.get("recommended_gpus", 1)
                if gpu_available < required:
                    warnings.append(f"Only {gpu_available} GPUs available, {required} recommended")
        except Exception as e:
            issues.append(f"Failed to check cluster resources: {e}")
            prereq_passed = False

        # Check/select runtime
        try:
            runtimes = client.list_cluster_training_runtimes()
            if not runtimes:
                issues.append("No training runtimes available")
                prereq_passed = False
            elif not runtime_name:
                # Auto-select first available runtime
                recommended_runtime = runtimes[0].name
        except Exception:
            issues.append("Failed to list training runtimes")
            prereq_passed = False

        # Validate runtime if specified
        if runtime_name:
            try:
                from rhoai_mcp.domains.training.crds import TrainingCRDs

                server.k8s.get(TrainingCRDs.CLUSTER_TRAINING_RUNTIME, runtime_name)
            except Exception:
                issues.append(f"Runtime '{runtime_name}' not found")
                prereq_passed = False

        # Validate model/dataset ID format
        if "/" not in model_id:
            issues.append("Model ID should be in format 'organization/model-name'")
            prereq_passed = False
        if "/" not in dataset_id:
            issues.append("Dataset ID should be in format 'organization/dataset-name'")
            prereq_passed = False

        # Step 3: Handle storage
        pvc_name = _sanitize_pvc_name("training-checkpoints", namespace)
        storage_exists = False

        try:
            pvc = server.k8s.get_pvc(pvc_name, namespace)
            if pvc.status and pvc.status.phase == "Bound":
                storage_exists = True
        except NotFoundError:
            pass  # PVC doesn't exist

        if not storage_exists and create_storage:
            # Check if we're allowed to create
            allowed, reason = server.config.is_operation_allowed("create")
            if allowed:
                result = create_training_pvc(
                    k8s=server.k8s,
                    namespace=namespace,
                    pvc_name=pvc_name,
                    size_gb=storage_size_gb,
                )
                if result.get("created") or result.get("exists"):
                    storage_created = result.get("created", False)
                    # Verify PVC is actually Bound before considering it ready
                    try:
                        pvc = server.k8s.get_pvc(pvc_name, namespace)
                        if pvc.status and pvc.status.phase == "Bound":
                            storage_exists = True
                        else:
                            phase = pvc.status.phase if pvc.status else "Unknown"
                            warnings.append(
                                f"PVC '{pvc_name}' exists but is not bound (phase: {phase}). "
                                "Training may need to wait for PVC to be ready."
                            )
                    except NotFoundError:
                        warnings.append(f"PVC '{pvc_name}' creation reported but not found")
                elif result.get("error"):
                    warnings.append(result["error"])
            else:
                warnings.append(f"Cannot create storage: {reason}")

        # Build suggested parameters for train() call
        suggested_params: dict[str, Any] = {
            "namespace": namespace,
            "model_id": model_id,
            "dataset_id": dataset_id,
            "runtime_name": recommended_runtime,
            "method": method,
            "epochs": 3,
            "batch_size": 32,
            "learning_rate": 1e-4,
            "num_nodes": 1,
            "gpus_per_node": resource_estimate.get("recommended_gpus", 1),
        }

        if storage_exists:
            suggested_params["checkpoint_dir"] = f"/mnt/{pvc_name}"

        ready = prereq_passed and len(issues) == 0

        return {
            "ready": ready,
            "issues": issues if issues else None,
            "warnings": warnings if warnings else None,
            "resource_estimate": resource_estimate,
            "recommended_runtime": recommended_runtime,
            "storage_created": storage_created,
            "storage_pvc": pvc_name if storage_exists else None,
            "next_action": "train" if ready else "fix_issues",
            "suggested_train_params": suggested_params,
        }


def _estimate_resources_internal(model_id: str, method: str) -> dict[str, Any]:
    """Internal helper for resource estimation used by prepare_training.

    Note: Uses a simplified formula without optimizer/activation overhead.
    For detailed estimates, use the estimate_resources() tool.
    """
    param_count = _extract_param_count(model_id)

    # Get base memory estimate
    base_memory = 16
    for (min_p, max_p), mem in GPU_MEMORY_ESTIMATES.items():
        if min_p <= param_count < max_p:
            base_memory = mem
            break

    try:
        peft_method = PeftMethod(method.lower())
    except ValueError:
        peft_method = PeftMethod.LORA

    multiplier = PEFT_MULTIPLIERS.get(peft_method, 1.8)
    total_memory = base_memory * multiplier

    recommended_gpus = 1
    if total_memory > 80:
        recommended_gpus = int((total_memory / 80) + 0.5)

    return {
        "model_id": model_id,
        "estimated_params_billion": param_count,
        "method": peft_method.value,
        "total_required_gb": round(total_memory, 1),
        "recommended_gpus": recommended_gpus,
        "storage_gb": int(param_count * 4) + 50,
    }


def _sanitize_pvc_name(base_name: str, suffix: str = "") -> str:
    """Sanitize a PVC name for DNS-1123 compliance.

    Kubernetes PVC names must:
    - Be at most 63 characters
    - Start and end with alphanumeric characters
    - Contain only lowercase alphanumeric characters or '-'

    Args:
        base_name: The base name to sanitize.
        suffix: Optional suffix to append (e.g., namespace).

    Returns:
        A DNS-1123 compliant name, truncated with hash suffix if needed.
    """
    # Build the full name
    full_name = f"{base_name}-{suffix}" if suffix else base_name

    # Lowercase and replace invalid characters with hyphens
    sanitized = re.sub(r"[^a-z0-9-]", "-", full_name.lower())
    # Collapse multiple hyphens
    sanitized = re.sub(r"-+", "-", sanitized)
    # Strip leading/trailing hyphens
    sanitized = sanitized.strip("-")

    # Ensure it starts with alphanumeric
    if sanitized and not sanitized[0].isalnum():
        sanitized = f"pvc-{sanitized}"

    # Handle empty result
    if not sanitized:
        sanitized = "pvc"

    # Truncate if needed, preserving uniqueness with hash suffix
    max_length = 63
    if len(sanitized) > max_length:
        # Use first 54 chars + "-" + 8-char hash suffix
        hash_suffix = hashlib.sha256(full_name.encode()).hexdigest()[:8]
        truncated = sanitized[: max_length - 9].rstrip("-")
        sanitized = f"{truncated}-{hash_suffix}"

    return sanitized


def _extract_param_count(model_id: str) -> float:
    """Extract parameter count from model ID.

    Attempts to parse common patterns like:
    - Llama-2-7b-hf -> 7
    - Qwen2.5-72B-Instruct -> 72
    - mistral-7b -> 7
    """
    model_lower = model_id.lower()

    # Try common patterns
    patterns = [
        r"(\d+(?:\.\d+)?)\s*b(?:illion)?",  # 7b, 70b, 7.1b
        r"-(\d+(?:\.\d+)?)b-",  # -7b-
        r"(\d+(?:\.\d+)?)b$",  # ends with 7b
    ]

    for pattern in patterns:
        match = re.search(pattern, model_lower)
        if match:
            return float(match.group(1))

    # Check for million parameters
    m_match = re.search(r"(\d+)m", model_lower)
    if m_match:
        return float(m_match.group(1)) / 1000

    # Default estimate based on common models
    if "llama" in model_lower:
        return 7.0
    if "mistral" in model_lower:
        return 7.0
    if "qwen" in model_lower:
        return 7.0

    return 7.0  # Default assumption
