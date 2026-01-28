"""CRD definitions for Notebooks domain."""

from rhoai_mcp.clients.base import CRDDefinition


class NotebookCRDs:
    """Kubeflow Notebook CRD definitions."""

    # Kubeflow Notebooks
    NOTEBOOK = CRDDefinition(
        group="kubeflow.org",
        version="v1",
        plural="notebooks",
        kind="Notebook",
    )
