"""Tool metadata registry for enhanced agent guidance.

This module provides dataclasses and functions for registering rich
metadata about MCP tools, including usage examples, prerequisites,
related tools, and error guidance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolExample:
    """A concrete usage example for a tool.

    Provides agents with examples of how to call a tool correctly,
    including expected arguments and results.
    """

    name: str
    """Short descriptive name for the example."""

    description: str
    """Explanation of what this example demonstrates."""

    arguments: dict[str, Any]
    """Example arguments to pass to the tool."""

    expected_result_summary: str
    """Summary of what the tool returns in this case."""

    tags: list[str] = field(default_factory=list)
    """Tags for categorizing examples (e.g., 'quick', 'gpu', 'basic')."""


@dataclass
class ToolMetadata:
    """Rich metadata for an MCP tool to improve agent usability.

    Extends basic docstrings with examples, prerequisites, related tools,
    and error guidance to help agents make better decisions.
    """

    name: str
    """Tool name (must match the MCP tool name)."""

    display_name: str
    """Human-readable display name."""

    description: str
    """Detailed description of what the tool does."""

    domain: str
    """Domain this tool belongs to (e.g., 'notebooks', 'inference')."""

    examples: list[ToolExample] = field(default_factory=list)
    """Concrete usage examples."""

    prerequisites: list[str] = field(default_factory=list)
    """Tool names that should typically be called before this one."""

    related_tools: list[str] = field(default_factory=list)
    """Other tools commonly used alongside this one."""

    common_mistakes: list[str] = field(default_factory=list)
    """Common mistakes agents make when using this tool."""

    error_guidance: dict[str, str] = field(default_factory=dict)
    """Error patterns mapped to recovery suggestions."""

    tags: list[str] = field(default_factory=list)
    """Tags for categorization (e.g., 'read', 'write', 'dangerous')."""

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to a dictionary for serialization."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "domain": self.domain,
            "examples": [
                {
                    "name": ex.name,
                    "description": ex.description,
                    "arguments": ex.arguments,
                    "expected_result_summary": ex.expected_result_summary,
                    "tags": ex.tags,
                }
                for ex in self.examples
            ],
            "prerequisites": self.prerequisites,
            "related_tools": self.related_tools,
            "common_mistakes": self.common_mistakes,
            "error_guidance": self.error_guidance,
            "tags": self.tags,
        }


# Global registry of tool metadata
_TOOL_METADATA_REGISTRY: dict[str, ToolMetadata] = {}


def register_tool_metadata(metadata: ToolMetadata) -> None:
    """Register metadata for a tool.

    Args:
        metadata: The tool metadata to register.
    """
    _TOOL_METADATA_REGISTRY[metadata.name] = metadata


def get_tool_metadata(tool_name: str) -> ToolMetadata | None:
    """Get metadata for a specific tool.

    Args:
        tool_name: The name of the tool.

    Returns:
        The tool metadata, or None if not registered.
    """
    return _TOOL_METADATA_REGISTRY.get(tool_name)


def get_all_tool_metadata() -> dict[str, ToolMetadata]:
    """Get all registered tool metadata.

    Returns:
        Dictionary mapping tool names to their metadata.
    """
    return _TOOL_METADATA_REGISTRY.copy()


def clear_tool_metadata() -> None:
    """Clear all registered tool metadata (useful for testing)."""
    _TOOL_METADATA_REGISTRY.clear()
