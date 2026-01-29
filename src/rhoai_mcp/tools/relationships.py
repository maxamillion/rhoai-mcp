"""Tool relationships and workflow definitions.

This module defines semantic relationships between MCP tools to help
agents understand tool sequences and workflows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RelationType(str, Enum):
    """Types of relationships between tools."""

    PREREQUISITE = "prerequisite"
    """The source tool should typically be called before the target."""

    FOLLOW_UP = "follow_up"
    """The target tool is commonly called after the source."""

    ALTERNATIVE = "alternative"
    """The tools can be used interchangeably for similar purposes."""

    VALIDATES = "validates"
    """The target tool can verify results of the source tool."""

    REVERSES = "reverses"
    """The target tool can undo the action of the source tool."""


@dataclass
class ToolRelationship:
    """A relationship between two tools.

    Defines how tools relate to each other in common workflows.
    """

    source: str
    """The source tool name."""

    target: str
    """The target tool name."""

    relation: RelationType
    """The type of relationship."""

    description: str
    """Explanation of why this relationship exists."""


@dataclass
class Workflow:
    """A recommended workflow for achieving a goal.

    Groups related tool calls into a logical sequence for
    common tasks.
    """

    name: str
    """Short workflow name."""

    goal: str
    """Description of what this workflow achieves."""

    steps: list[str]
    """Ordered list of tool names to execute."""

    optional_steps: list[str] = field(default_factory=list)
    """Tools that may be used depending on context."""

    tags: list[str] = field(default_factory=list)
    """Tags for categorization (e.g., 'quick', 'setup', 'cleanup')."""


# Define common tool relationships
TOOL_RELATIONSHIPS: list[ToolRelationship] = [
    # Notebooks domain
    ToolRelationship(
        source="list_notebook_images",
        target="create_workbench",
        relation=RelationType.PREREQUISITE,
        description="Check available images before creating a workbench",
    ),
    ToolRelationship(
        source="list_workbenches",
        target="get_workbench",
        relation=RelationType.PREREQUISITE,
        description="List workbenches to find the one to inspect",
    ),
    ToolRelationship(
        source="create_workbench",
        target="get_workbench",
        relation=RelationType.FOLLOW_UP,
        description="Check workbench status after creation",
    ),
    ToolRelationship(
        source="create_workbench",
        target="get_workbench_url",
        relation=RelationType.FOLLOW_UP,
        description="Get URL for accessing the new workbench",
    ),
    ToolRelationship(
        source="start_workbench",
        target="get_workbench",
        relation=RelationType.VALIDATES,
        description="Verify workbench started successfully",
    ),
    ToolRelationship(
        source="stop_workbench",
        target="start_workbench",
        relation=RelationType.REVERSES,
        description="Start reverses the effect of stop",
    ),
    ToolRelationship(
        source="delete_workbench",
        target="create_workbench",
        relation=RelationType.REVERSES,
        description="Create reverses the effect of delete",
    ),
    # Projects domain
    ToolRelationship(
        source="list_projects",
        target="get_project",
        relation=RelationType.PREREQUISITE,
        description="List projects to find the one to inspect",
    ),
    ToolRelationship(
        source="list_projects",
        target="create_workbench",
        relation=RelationType.PREREQUISITE,
        description="Identify project namespace before creating resources",
    ),
    # Connections domain
    ToolRelationship(
        source="list_data_connections",
        target="create_workbench",
        relation=RelationType.PREREQUISITE,
        description="Check available data connections before mounting them",
    ),
    ToolRelationship(
        source="create_data_connection",
        target="list_data_connections",
        relation=RelationType.FOLLOW_UP,
        description="Verify connection was created",
    ),
    # Storage domain
    ToolRelationship(
        source="list_storage",
        target="create_workbench",
        relation=RelationType.PREREQUISITE,
        description="Check available storage before attaching to workbench",
    ),
    # Inference domain
    ToolRelationship(
        source="list_inference_services",
        target="get_inference_service",
        relation=RelationType.PREREQUISITE,
        description="List services to find one to inspect",
    ),
    ToolRelationship(
        source="deploy_model",
        target="get_inference_service",
        relation=RelationType.FOLLOW_UP,
        description="Check deployment status after deploying",
    ),
    # Training domain
    ToolRelationship(
        source="list_training_runtimes",
        target="create_training_job",
        relation=RelationType.PREREQUISITE,
        description="Check available runtimes before creating job",
    ),
    ToolRelationship(
        source="create_training_job",
        target="get_training_job_status",
        relation=RelationType.FOLLOW_UP,
        description="Monitor job status after creation",
    ),
]


# Define common workflows
WORKFLOWS: list[Workflow] = [
    Workflow(
        name="create_basic_workbench",
        goal="Create a new Jupyter notebook workbench in a project",
        steps=[
            "list_projects",
            "list_notebook_images",
            "create_workbench",
            "get_workbench",
            "get_workbench_url",
        ],
        optional_steps=["list_data_connections", "list_storage"],
        tags=["quick", "setup", "notebooks"],
    ),
    Workflow(
        name="create_gpu_workbench",
        goal="Create a GPU-enabled workbench for ML training",
        steps=[
            "list_projects",
            "list_notebook_images",
            "create_workbench",  # with gpu_count > 0
            "get_workbench",
        ],
        tags=["gpu", "ml", "notebooks"],
    ),
    Workflow(
        name="deploy_model_from_s3",
        goal="Deploy a model from S3 storage to KServe",
        steps=[
            "list_projects",
            "list_data_connections",
            "deploy_model",
            "get_inference_service",
        ],
        tags=["inference", "serving"],
    ),
    Workflow(
        name="start_training_job",
        goal="Create and monitor a distributed training job",
        steps=[
            "list_projects",
            "list_training_runtimes",
            "create_training_job",
            "get_training_job_status",
        ],
        optional_steps=["get_training_job_logs"],
        tags=["training", "ml"],
    ),
    Workflow(
        name="project_overview",
        goal="Get an overview of all resources in a project",
        steps=[
            "list_projects",
            "get_project",
            "list_workbenches",
            "list_inference_services",
            "list_data_connections",
            "list_storage",
        ],
        tags=["quick", "read-only"],
    ),
]


def get_tool_relationships(tool_name: str) -> list[ToolRelationship]:
    """Get all relationships involving a specific tool.

    Args:
        tool_name: The tool to get relationships for.

    Returns:
        List of relationships where the tool is source or target.
    """
    return [
        r for r in TOOL_RELATIONSHIPS if r.source == tool_name or r.target == tool_name
    ]


def get_prerequisites(tool_name: str) -> list[str]:
    """Get tools that should typically be called before this tool.

    Args:
        tool_name: The tool to get prerequisites for.

    Returns:
        List of tool names that are prerequisites.
    """
    prerequisites = []
    for r in TOOL_RELATIONSHIPS:
        if r.target == tool_name and r.relation == RelationType.PREREQUISITE:
            prerequisites.append(r.source)
    return prerequisites


def get_follow_ups(tool_name: str) -> list[str]:
    """Get tools that are commonly called after this tool.

    Args:
        tool_name: The tool to get follow-ups for.

    Returns:
        List of tool names that are common follow-ups.
    """
    follow_ups = []
    for r in TOOL_RELATIONSHIPS:
        if r.source == tool_name and r.relation == RelationType.FOLLOW_UP:
            follow_ups.append(r.target)
    return follow_ups


def get_workflow_for_goal(goal_keywords: str) -> list[Workflow]:
    """Find workflows matching a goal description.

    Args:
        goal_keywords: Keywords describing the goal (e.g., 'create workbench').

    Returns:
        List of matching workflows, sorted by relevance.
    """
    keywords = goal_keywords.lower().split()
    results = []

    for workflow in WORKFLOWS:
        # Score based on keyword matches in name, goal, and tags
        score = 0
        search_text = f"{workflow.name} {workflow.goal} {' '.join(workflow.tags)}".lower()

        for keyword in keywords:
            if keyword in search_text:
                score += 1

        if score > 0:
            results.append((score, workflow))

    # Sort by score descending
    results.sort(key=lambda x: x[0], reverse=True)
    return [wf for _, wf in results]


def get_all_workflows() -> list[Workflow]:
    """Get all defined workflows.

    Returns:
        List of all workflow definitions.
    """
    return WORKFLOWS.copy()
