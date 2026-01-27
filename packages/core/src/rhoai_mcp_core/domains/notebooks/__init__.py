"""Notebooks domain - Workbench (Kubeflow Notebook) management."""

from rhoai_mcp_core.domains.notebooks.client import NotebookClient
from rhoai_mcp_core.domains.notebooks.crds import NotebookCRDs
from rhoai_mcp_core.domains.notebooks.models import (
    NotebookImage,
    Workbench,
    WorkbenchCreate,
    WorkbenchStatus,
)

__all__ = [
    "NotebookClient",
    "NotebookCRDs",
    "NotebookImage",
    "Workbench",
    "WorkbenchCreate",
    "WorkbenchStatus",
]
