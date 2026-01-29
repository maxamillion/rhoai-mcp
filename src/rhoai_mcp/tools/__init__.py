"""Tool metadata and workflow utilities for RHOAI MCP server.

This package provides enhanced tool documentation, examples, and workflow
relationships to help AI agents better understand and use MCP tools.
"""

from rhoai_mcp.tools.metadata import (
    ToolExample,
    ToolMetadata,
    get_all_tool_metadata,
    get_tool_metadata,
    register_tool_metadata,
)
from rhoai_mcp.tools.relationships import (
    RelationType,
    ToolRelationship,
    get_follow_ups,
    get_prerequisites,
    get_tool_relationships,
    get_workflow_for_goal,
)

__all__ = [
    # Metadata
    "ToolExample",
    "ToolMetadata",
    "register_tool_metadata",
    "get_tool_metadata",
    "get_all_tool_metadata",
    # Relationships
    "RelationType",
    "ToolRelationship",
    "get_prerequisites",
    "get_follow_ups",
    "get_tool_relationships",
    "get_workflow_for_goal",
]
