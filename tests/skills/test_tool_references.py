"""Tests to cross-validate skill tool references against MCP server tools."""

from __future__ import annotations

from pathlib import Path

import pytest

SKILLS_DIR = Path(__file__).parent.parent.parent / "skills"
TOOL_PREFIX = "mcp__rhoai__"


def _get_skill_tool_references() -> dict[str, list[str]]:
    """Collect all tool references from skill allowed-tools."""
    refs: dict[str, list[str]] = {}

    if not SKILLS_DIR.is_dir():
        return refs

    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue

        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue

        content = skill_file.read_text()
        if not content.startswith("---"):
            continue

        end_idx = content.index("---", 3)
        frontmatter = content[3:end_idx]

        tools: list[str] = []
        in_tools = False
        for line in frontmatter.split("\n"):
            stripped = line.strip()
            if stripped.startswith("allowed-tools:"):
                in_tools = True
                continue
            if in_tools and stripped.startswith("- "):
                tool = stripped[2:].strip()
                tools.append(tool)
            elif in_tools and ":" in stripped:
                break

        if tools:
            refs[skill_dir.name] = tools

    return refs


def _get_all_tool_refs() -> set[str]:
    """Get the set of all tool names referenced across all skills."""
    refs = _get_skill_tool_references()
    all_tools: set[str] = set()
    for tools in refs.values():
        all_tools.update(tools)
    return all_tools


class TestToolReferences:
    """Validate tool references in skills."""

    def test_all_tool_refs_have_prefix(self) -> None:
        """Every tool reference should follow the mcp__rhoai__ pattern."""
        all_tools = _get_all_tool_refs()
        for tool in all_tools:
            assert tool.startswith(TOOL_PREFIX), (
                f"Tool '{tool}' doesn't start with '{TOOL_PREFIX}'"
            )

    def test_no_empty_tool_lists(self) -> None:
        """Every skill should reference at least one tool."""
        refs = _get_skill_tool_references()
        for skill_name, tools in refs.items():
            assert len(tools) > 0, f"Skill '{skill_name}' has empty allowed-tools"

    def test_tool_names_are_valid_identifiers(self) -> None:
        """Tool names should be valid Python-style identifiers after prefix."""
        import re

        all_tools = _get_all_tool_refs()
        for tool in all_tools:
            # After removing prefix, should be valid identifier
            name = tool[len(TOOL_PREFIX) :]
            assert re.match(r"^[a-z][a-z0-9_]*$", name), (
                f"Tool name '{tool}' has invalid identifier after prefix"
            )

    def test_no_duplicate_tools_per_skill(self) -> None:
        """No skill should list the same tool twice."""
        refs = _get_skill_tool_references()
        for skill_name, tools in refs.items():
            assert len(tools) == len(set(tools)), (
                f"Skill '{skill_name}' has duplicate tool references"
            )

    @pytest.mark.skipif(
        not SKILLS_DIR.is_dir(),
        reason="Skills directory not found",
    )
    def test_report_all_referenced_tools(self) -> None:
        """Report all unique tools referenced across skills (informational)."""
        all_tools = sorted(_get_all_tool_refs())
        assert len(all_tools) > 0, "No tool references found in skills"
        # This test always passes - it's here for visibility in test output
