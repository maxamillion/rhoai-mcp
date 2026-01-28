"""Notebooks domain - Workbench (Kubeflow Notebook) management."""

from rhoai_mcp.domains.notebooks.client import NotebookClient
from rhoai_mcp.domains.notebooks.crds import NotebookCRDs
from rhoai_mcp.domains.notebooks.models import (
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
