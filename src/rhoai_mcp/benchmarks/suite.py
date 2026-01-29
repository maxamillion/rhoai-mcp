"""Benchmark case and suite definitions.

This module provides dataclasses for defining benchmark cases and suites
that can be used to measure agent performance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BenchmarkCase:
    """A single benchmark test case.

    Defines a task with expected behavior and success criteria
    for evaluating agent performance.
    """

    name: str
    """Unique name for this benchmark case."""

    task_prompt: str
    """The prompt describing what the agent should do."""

    required_tools: list[str] = field(default_factory=list)
    """Tools that MUST be called to complete this task."""

    forbidden_tools: list[str] = field(default_factory=list)
    """Tools that should NOT be called for this task."""

    optimal_trajectory: list[str] = field(default_factory=list)
    """The ideal sequence of tool calls."""

    acceptable_trajectories: list[list[str]] = field(default_factory=list)
    """Alternative acceptable tool sequences."""

    expected_results: list[dict[str, Any]] = field(default_factory=list)
    """Expected result patterns for validation."""

    max_steps: int = 10
    """Maximum tool calls allowed before failure."""

    tags: list[str] = field(default_factory=list)
    """Tags for categorization (e.g., 'quick', 'complex', 'gpu')."""

    description: str = ""
    """Detailed description of the benchmark case."""

    setup_requirements: list[str] = field(default_factory=list)
    """Prerequisites that must exist (e.g., 'project:test-project')."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "task_prompt": self.task_prompt,
            "required_tools": self.required_tools,
            "forbidden_tools": self.forbidden_tools,
            "optimal_trajectory": self.optimal_trajectory,
            "acceptable_trajectories": self.acceptable_trajectories,
            "expected_results": self.expected_results,
            "max_steps": self.max_steps,
            "tags": self.tags,
            "description": self.description,
            "setup_requirements": self.setup_requirements,
        }


@dataclass
class BenchmarkSuite:
    """A collection of related benchmark cases.

    Groups benchmark cases by domain or functionality for
    organized testing.
    """

    name: str
    """Unique name for this suite."""

    description: str
    """Description of what this suite tests."""

    cases: list[BenchmarkCase] = field(default_factory=list)
    """The benchmark cases in this suite."""

    tags: list[str] = field(default_factory=list)
    """Tags for categorization."""

    def get_cases_by_tag(self, tag: str) -> list[BenchmarkCase]:
        """Get cases matching a specific tag.

        Args:
            tag: The tag to filter by.

        Returns:
            List of matching benchmark cases.
        """
        return [case for case in self.cases if tag in case.tags]

    def get_quick_cases(self) -> list[BenchmarkCase]:
        """Get cases tagged as 'quick' for fast CI runs.

        Returns:
            List of quick benchmark cases.
        """
        return self.get_cases_by_tag("quick")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "cases": [case.to_dict() for case in self.cases],
            "tags": self.tags,
            "total_cases": len(self.cases),
        }
