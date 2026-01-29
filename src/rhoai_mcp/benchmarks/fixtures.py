"""Simulation fixtures for benchmark testing.

This module provides dataclasses and embedded scenarios for simulating
agent tool calls, allowing validation of the scoring system without
requiring a real agent.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SimulatedToolCall:
    """A simulated tool call for benchmark testing.

    Represents a single tool invocation with its parameters and result.
    """

    tool_name: str
    """Name of the tool called."""

    arguments: dict[str, Any] = field(default_factory=dict)
    """Arguments passed to the tool."""

    result: Any = None
    """Result returned by the tool."""

    duration_ms: float = 50.0
    """Simulated execution time in milliseconds."""

    success: bool = True
    """Whether the call succeeded."""

    error: str | None = None
    """Error message if the call failed."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for the benchmark runner."""
        return {
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "result": self.result,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error": self.error,
        }


@dataclass
class SimulationScenario:
    """A complete scenario for simulating agent behavior.

    Groups tool calls with metadata about expected outcomes.
    """

    name: str
    """Unique name for this scenario."""

    case_name: str
    """Name of the benchmark case this scenario tests."""

    description: str
    """Description of what this scenario demonstrates."""

    tool_calls: list[SimulatedToolCall] = field(default_factory=list)
    """The sequence of tool calls to simulate."""

    expected_pass: bool = True
    """Whether this scenario should pass the benchmark."""

    expected_score_min: float = 0.0
    """Minimum expected score."""

    expected_score_max: float = 1.0
    """Maximum expected score."""

    tags: list[str] = field(default_factory=list)
    """Tags for categorization (e.g., 'optimal', 'suboptimal', 'failure')."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "case_name": self.case_name,
            "description": self.description,
            "tool_calls": [call.to_dict() for call in self.tool_calls],
            "expected_pass": self.expected_pass,
            "expected_score_min": self.expected_score_min,
            "expected_score_max": self.expected_score_max,
            "tags": self.tags,
        }


# =============================================================================
# Embedded Scenarios - Optimal Paths (High Scores)
# =============================================================================

WORKBENCH_LIST_OPTIMAL = SimulationScenario(
    name="workbench_list_optimal",
    case_name="workbench_list",
    description="Optimal path: single call to list_workbenches",
    tool_calls=[
        SimulatedToolCall(
            tool_name="list_workbenches",
            arguments={"namespace": "test-project"},
            result={"workbenches": [{"name": "wb-1"}, {"name": "wb-2"}]},
            duration_ms=45.0,
        ),
    ],
    expected_pass=True,
    expected_score_min=0.80,
    expected_score_max=1.0,
    tags=["optimal", "quick", "workbench"],
)

PROJECT_LIST_OPTIMAL = SimulationScenario(
    name="project_list_optimal",
    case_name="project_list",
    description="Optimal path: single call to list_projects",
    tool_calls=[
        SimulatedToolCall(
            tool_name="list_projects",
            arguments={},
            result={"projects": [{"name": "proj-1"}, {"name": "proj-2"}]},
            duration_ms=50.0,
        ),
    ],
    expected_pass=True,
    expected_score_min=0.80,
    expected_score_max=1.0,
    tags=["optimal", "quick", "project"],
)

WORKBENCH_CREATE_OPTIMAL = SimulationScenario(
    name="workbench_create_optimal",
    case_name="workbench_create_basic",
    description="Optimal path: list images then create workbench",
    tool_calls=[
        SimulatedToolCall(
            tool_name="list_notebook_images",
            arguments={},
            result={"images": [{"name": "jupyter-datascience"}]},
            duration_ms=30.0,
        ),
        SimulatedToolCall(
            tool_name="create_workbench",
            arguments={
                "name": "test-nb",
                "namespace": "test-project",
                "image": "jupyter-datascience",
            },
            result={"name": "test-nb", "status": "Running"},
            duration_ms=100.0,
        ),
    ],
    expected_pass=True,
    expected_score_min=0.80,
    expected_score_max=1.0,
    tags=["optimal", "quick", "workbench", "create"],
)

WORKBENCH_LIFECYCLE_OPTIMAL = SimulationScenario(
    name="workbench_lifecycle_optimal",
    case_name="workbench_lifecycle",
    description="Optimal path: stop workbench and verify status",
    tool_calls=[
        SimulatedToolCall(
            tool_name="stop_workbench",
            arguments={"name": "my-workbench", "namespace": "test-project"},
            result={"status": "Stopped"},
            duration_ms=80.0,
        ),
        SimulatedToolCall(
            tool_name="get_workbench",
            arguments={"name": "my-workbench", "namespace": "test-project"},
            result={"name": "my-workbench", "status": "Stopped"},
            duration_ms=40.0,
        ),
    ],
    expected_pass=True,
    expected_score_min=0.80,
    expected_score_max=1.0,
    tags=["optimal", "quick", "workbench", "lifecycle"],
)

# =============================================================================
# Embedded Scenarios - Suboptimal Paths (Passing but Lower Scores)
# =============================================================================

WORKBENCH_LIST_SUBOPTIMAL = SimulationScenario(
    name="workbench_list_suboptimal",
    case_name="workbench_list",
    description="Suboptimal: unnecessary project listing before workbench list",
    tool_calls=[
        SimulatedToolCall(
            tool_name="list_projects",
            arguments={},
            result={"projects": [{"name": "test-project"}]},
            duration_ms=50.0,
        ),
        SimulatedToolCall(
            tool_name="list_workbenches",
            arguments={"namespace": "test-project"},
            result={"workbenches": [{"name": "wb-1"}]},
            duration_ms=45.0,
        ),
    ],
    expected_pass=True,
    expected_score_min=0.80,
    expected_score_max=1.0,
    tags=["suboptimal", "workbench"],
)

WORKBENCH_CREATE_SUBOPTIMAL = SimulationScenario(
    name="workbench_create_suboptimal",
    case_name="workbench_create_basic",
    description="Suboptimal: extra project check before creating workbench",
    tool_calls=[
        SimulatedToolCall(
            tool_name="list_projects",
            arguments={},
            result={"projects": [{"name": "test-project"}]},
            duration_ms=40.0,
        ),
        SimulatedToolCall(
            tool_name="get_project",
            arguments={"name": "test-project"},
            result={"name": "test-project", "status": "Active"},
            duration_ms=35.0,
        ),
        SimulatedToolCall(
            tool_name="list_notebook_images",
            arguments={},
            result={"images": [{"name": "jupyter-datascience"}]},
            duration_ms=30.0,
        ),
        SimulatedToolCall(
            tool_name="create_workbench",
            arguments={
                "name": "test-nb",
                "namespace": "test-project",
                "image": "jupyter-datascience",
            },
            result={"name": "test-nb", "status": "Running"},
            duration_ms=100.0,
        ),
    ],
    expected_pass=True,
    expected_score_min=0.80,
    expected_score_max=1.0,
    tags=["suboptimal", "workbench", "create"],
)

# =============================================================================
# Embedded Scenarios - Failure Paths (Should Not Pass)
# =============================================================================

WORKBENCH_LIST_MISSING_REQUIRED = SimulationScenario(
    name="workbench_list_missing_required",
    case_name="workbench_list",
    description="Failure: calls wrong tool (list_projects instead of list_workbenches)",
    tool_calls=[
        SimulatedToolCall(
            tool_name="list_projects",
            arguments={},
            result={"projects": [{"name": "test-project"}]},
            duration_ms=50.0,
        ),
    ],
    expected_pass=False,
    expected_score_min=0.0,
    expected_score_max=0.70,
    tags=["failure", "missing_required", "workbench"],
)

WORKBENCH_CREATE_MISSING_IMAGES = SimulationScenario(
    name="workbench_create_missing_images",
    case_name="workbench_create_basic",
    description="Failure: creates workbench without listing images first",
    tool_calls=[
        SimulatedToolCall(
            tool_name="create_workbench",
            arguments={
                "name": "test-nb",
                "namespace": "test-project",
                "image": "some-image",
            },
            result={"name": "test-nb", "status": "Running"},
            duration_ms=100.0,
        ),
    ],
    expected_pass=False,
    expected_score_min=0.0,
    expected_score_max=0.80,
    tags=["failure", "missing_required", "workbench", "create"],
)

WORKBENCH_LIST_FORBIDDEN_TOOL = SimulationScenario(
    name="workbench_list_forbidden_tool",
    case_name="workbench_list",
    description="Suboptimal: calls forbidden delete tool (but still completes task)",
    tool_calls=[
        SimulatedToolCall(
            tool_name="list_workbenches",
            arguments={"namespace": "test-project"},
            result={"workbenches": [{"name": "wb-1"}]},
            duration_ms=45.0,
        ),
        SimulatedToolCall(
            tool_name="delete_workbench",
            arguments={"name": "wb-1", "namespace": "test-project"},
            result={"deleted": True},
            duration_ms=60.0,
        ),
    ],
    expected_pass=True,  # Passes because required tool was called
    expected_score_min=0.70,
    expected_score_max=1.0,
    tags=["suboptimal", "forbidden_tool", "workbench"],
)

WORKBENCH_LIST_ERROR = SimulationScenario(
    name="workbench_list_error",
    case_name="workbench_list",
    description="Error: tool call returns error (but required tool was called)",
    tool_calls=[
        SimulatedToolCall(
            tool_name="list_workbenches",
            arguments={"namespace": "test-project"},
            result=None,
            duration_ms=100.0,
            success=False,
            error="Connection refused",
        ),
    ],
    expected_pass=True,  # Passes because required tool name was called (even if error)
    expected_score_min=0.50,
    expected_score_max=0.80,
    tags=["error", "workbench"],
)

# =============================================================================
# Scenario Registry
# =============================================================================

EMBEDDED_SCENARIOS: list[SimulationScenario] = [
    # Optimal paths
    WORKBENCH_LIST_OPTIMAL,
    PROJECT_LIST_OPTIMAL,
    WORKBENCH_CREATE_OPTIMAL,
    WORKBENCH_LIFECYCLE_OPTIMAL,
    # Suboptimal paths
    WORKBENCH_LIST_SUBOPTIMAL,
    WORKBENCH_CREATE_SUBOPTIMAL,
    # Failure paths
    WORKBENCH_LIST_MISSING_REQUIRED,
    WORKBENCH_CREATE_MISSING_IMAGES,
    WORKBENCH_LIST_FORBIDDEN_TOOL,
    WORKBENCH_LIST_ERROR,
]

_SCENARIO_BY_NAME: dict[str, SimulationScenario] = {s.name: s for s in EMBEDDED_SCENARIOS}

_SCENARIOS_BY_CASE: dict[str, list[SimulationScenario]] = {}
for _scenario in EMBEDDED_SCENARIOS:
    if _scenario.case_name not in _SCENARIOS_BY_CASE:
        _SCENARIOS_BY_CASE[_scenario.case_name] = []
    _SCENARIOS_BY_CASE[_scenario.case_name].append(_scenario)


def load_scenario(name: str) -> SimulationScenario | None:
    """Load a scenario by name.

    Args:
        name: The scenario name.

    Returns:
        The scenario, or None if not found.
    """
    return _SCENARIO_BY_NAME.get(name)


def load_scenarios_for_case(case_name: str) -> list[SimulationScenario]:
    """Load all scenarios for a benchmark case.

    Args:
        case_name: The benchmark case name.

    Returns:
        List of scenarios for that case.
    """
    return _SCENARIOS_BY_CASE.get(case_name, [])


def get_all_scenarios() -> list[SimulationScenario]:
    """Get all embedded scenarios.

    Returns:
        List of all simulation scenarios.
    """
    return EMBEDDED_SCENARIOS.copy()


def get_scenarios_by_tag(tag: str) -> list[SimulationScenario]:
    """Get scenarios with a specific tag.

    Args:
        tag: The tag to filter by.

    Returns:
        List of matching scenarios.
    """
    return [s for s in EMBEDDED_SCENARIOS if tag in s.tags]


def load_from_json(path: Path | str) -> list[SimulationScenario]:
    """Load scenarios from a JSON file.

    Args:
        path: Path to the JSON file.

    Returns:
        List of loaded scenarios.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If the JSON is invalid.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Scenario file not found: {path}")

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}") from e

    scenarios = []
    scenario_list = data if isinstance(data, list) else [data]

    for item in scenario_list:
        tool_calls = [
            SimulatedToolCall(
                tool_name=tc.get("tool_name", "unknown"),
                arguments=tc.get("arguments", {}),
                result=tc.get("result"),
                duration_ms=tc.get("duration_ms", 50.0),
                success=tc.get("success", True),
                error=tc.get("error"),
            )
            for tc in item.get("tool_calls", [])
        ]

        scenario = SimulationScenario(
            name=item.get("name", "unnamed"),
            case_name=item.get("case_name", ""),
            description=item.get("description", ""),
            tool_calls=tool_calls,
            expected_pass=item.get("expected_pass", True),
            expected_score_min=item.get("expected_score_min", 0.0),
            expected_score_max=item.get("expected_score_max", 1.0),
            tags=item.get("tags", []),
        )
        scenarios.append(scenario)

    return scenarios


def load_scenarios_from_directory(directory: Path | str) -> list[SimulationScenario]:
    """Load all scenarios from JSON files in a directory.

    Args:
        directory: Path to the directory containing JSON files.

    Returns:
        List of all loaded scenarios.
    """
    directory = Path(directory)
    if not directory.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    scenarios = []
    for json_file in directory.glob("*.json"):
        try:
            scenarios.extend(load_from_json(json_file))
        except (ValueError, FileNotFoundError):
            # Skip invalid files
            continue

    return scenarios
