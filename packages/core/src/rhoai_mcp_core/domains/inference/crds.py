"""CRD definitions for Inference domain."""

from rhoai_mcp_core.clients.base import CRDDefinition


class InferenceCRDs:
    """KServe CRD definitions."""

    # KServe InferenceService
    INFERENCE_SERVICE = CRDDefinition(
        group="serving.kserve.io",
        version="v1beta1",
        plural="inferenceservices",
        kind="InferenceService",
    )

    # KServe ServingRuntime
    SERVING_RUNTIME = CRDDefinition(
        group="serving.kserve.io",
        version="v1alpha1",
        plural="servingruntimes",
        kind="ServingRuntime",
    )
