"""CRD definitions for Pipelines domain."""

from rhoai_mcp_core.clients.base import CRDDefinition


class PipelinesCRDs:
    """Data Science Pipelines CRD definitions."""

    # Data Science Pipelines Application
    DSPA = CRDDefinition(
        group="datasciencepipelinesapplications.opendatahub.io",
        version="v1alpha1",
        plural="datasciencepipelinesapplications",
        kind="DataSciencePipelinesApplication",
    )
