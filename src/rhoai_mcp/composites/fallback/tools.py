"""Fallback MCP tool that serves skill content to MCP-only clients."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import FastMCP

from rhoai_mcp.hooks import hookimpl
from rhoai_mcp.plugin import BasePlugin, PluginMetadata
from rhoai_mcp.utils.skill_loader import SkillInfo, load_skills

if TYPE_CHECKING:
    from rhoai_mcp.server import RHOAIServer

# Cache loaded skills
_skills_cache: dict[str, SkillInfo] | None = None


def _get_skills() -> dict[str, SkillInfo]:
    """Get skills, loading from disk on first call."""
    global _skills_cache
    if _skills_cache is None:
        _skills_cache = load_skills()
    return _skills_cache


class FallbackPlugin(BasePlugin):
    """Plugin providing workflow guidance fallback for MCP-only clients.

    Exposes a single get_workflow_guide tool that returns skill content
    as plain text, allowing MCP clients without skill support to access
    the same workflow guidance.
    """

    def __init__(self) -> None:
        super().__init__(
            PluginMetadata(
                name="fallback",
                version="1.0.0",
                description="Workflow guidance fallback for MCP-only clients",
                maintainer="rhoai-mcp@redhat.com",
                requires_crds=[],
            )
        )

    @hookimpl
    def rhoai_register_tools(self, mcp: FastMCP, server: RHOAIServer) -> None:  # noqa: ARG002
        register_tools(mcp)

    @hookimpl
    def rhoai_health_check(self, server: RHOAIServer) -> tuple[bool, str]:  # noqa: ARG002
        return True, "Fallback plugin requires no external dependencies"


def register_tools(mcp: FastMCP) -> None:
    """Register fallback tools with the MCP server."""

    @mcp.tool()
    def get_workflow_guide(workflow: str) -> dict[str, Any]:
        """Get step-by-step workflow guidance for an RHOAI operation.

        Returns markdown instructions for common RHOAI workflows such as
        training models, deploying models, exploring clusters, and
        troubleshooting issues. Use this when you need guidance on
        how to accomplish a multi-step RHOAI task.

        Available workflows: train-model, monitor-training, resume-training,
        deploy-model, deploy-llm, test-endpoint, scale-model,
        explore-cluster, explore-project, find-gpus, whats-running,
        troubleshoot-training, troubleshoot-workbench, troubleshoot-model,
        analyze-oom, setup-training-project, setup-inference-project,
        add-data-connection, prepare-training, prepare-deployment,
        diagnose-resource.

        Args:
            workflow: Name of the workflow to get guidance for.

        Returns:
            Workflow guide content or error with available workflows.
        """
        skills = _get_skills()

        if workflow in skills:
            skill = skills[workflow]
            return {
                "workflow": workflow,
                "description": skill.description,
                "guide": skill.content,
            }

        return {
            "error": f"Unknown workflow: '{workflow}'",
            "available_workflows": sorted(skills.keys()),
            "hint": "Use one of the available workflow names listed above.",
        }
