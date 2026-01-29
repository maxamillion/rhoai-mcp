"""Simulation executor for benchmark testing.

This module provides a simulation-based executor that replays predefined
tool call sequences for validating the benchmark scoring system.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from rhoai_mcp.benchmarks.fixtures import (
    SimulationScenario,
    get_all_scenarios,
    get_scenarios_by_tag,
    load_scenarios_for_case,
    load_scenarios_from_directory,
)
from rhoai_mcp.benchmarks.golden_paths import get_all_cases, get_quick_cases
from rhoai_mcp.benchmarks.runner import (
    AgentExecutor,
    BenchmarkResult,
    BenchmarkRunner,
)
from rhoai_mcp.benchmarks.suite import BenchmarkCase

logger = logging.getLogger(__name__)


class SimulationExecutor:
    """Executor that replays simulated tool calls.

    Instead of calling an actual agent, this executor returns
    predefined tool call sequences from simulation scenarios.
    """

    def __init__(self, scenario: SimulationScenario) -> None:
        """Initialize with a simulation scenario.

        Args:
            scenario: The scenario to replay.
        """
        self._scenario = scenario

    @property
    def scenario(self) -> SimulationScenario:
        """Get the current scenario."""
        return self._scenario

    def execute(self, _prompt: str) -> list[dict[str, Any]]:
        """Execute the simulation by returning predefined tool calls.

        Args:
            _prompt: The task prompt (ignored, scenario determines behavior).

        Returns:
            List of tool call dictionaries for the benchmark runner.
        """
        return [call.to_dict() for call in self._scenario.tool_calls]

    def as_executor(self) -> AgentExecutor:
        """Get as an AgentExecutor callable.

        Returns:
            The execute method as a callable.
        """
        return self.execute


def create_simulation_executor(scenario: SimulationScenario) -> SimulationExecutor:
    """Factory function to create a simulation executor.

    Args:
        scenario: The scenario to replay.

    Returns:
        A configured SimulationExecutor.
    """
    return SimulationExecutor(scenario)


class SimulationResult:
    """Result of running a simulation scenario through the benchmark."""

    def __init__(
        self,
        scenario: SimulationScenario,
        result: BenchmarkResult,
    ) -> None:
        """Initialize the simulation result.

        Args:
            scenario: The scenario that was run.
            result: The benchmark result from the runner.
        """
        self.scenario = scenario
        self.result = result

    @property
    def score_in_range(self) -> bool:
        """Check if the score is within expected range."""
        if self.result.score is None:
            return False
        score = self.result.score.overall_score
        return self.scenario.expected_score_min <= score <= self.scenario.expected_score_max

    @property
    def pass_matches(self) -> bool:
        """Check if pass/fail matches expected."""
        return self.result.passed == self.scenario.expected_pass

    @property
    def validation_passed(self) -> bool:
        """Check if this simulation validates correctly."""
        return self.pass_matches and self.score_in_range

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for reporting."""
        score = self.result.score.overall_score if self.result.score else 0.0
        return {
            "scenario": self.scenario.name,
            "case": self.scenario.case_name,
            "expected_pass": self.scenario.expected_pass,
            "actual_pass": self.result.passed,
            "expected_score_range": [
                self.scenario.expected_score_min,
                self.scenario.expected_score_max,
            ],
            "actual_score": score,
            "pass_matches": self.pass_matches,
            "score_in_range": self.score_in_range,
            "validation_passed": self.validation_passed,
        }


class SimulationBenchmarkRunner:
    """Runs benchmark cases using simulation scenarios."""

    def __init__(self, pass_threshold: float = 0.70) -> None:
        """Initialize the simulation runner.

        Args:
            pass_threshold: Minimum score to pass.
        """
        self._pass_threshold = pass_threshold

    def run_scenario(
        self,
        case: BenchmarkCase,
        scenario: SimulationScenario,
    ) -> SimulationResult:
        """Run a single scenario against a benchmark case.

        Args:
            case: The benchmark case definition.
            scenario: The simulation scenario to run.

        Returns:
            The simulation result with validation info.
        """
        runner = BenchmarkRunner(pass_threshold=self._pass_threshold)
        executor = create_simulation_executor(scenario)
        result = runner.run_case(case, executor.as_executor())
        return SimulationResult(scenario, result)

    def run_all_scenarios_for_case(
        self,
        case: BenchmarkCase,
    ) -> list[SimulationResult]:
        """Run all scenarios for a benchmark case.

        Args:
            case: The benchmark case.

        Returns:
            List of simulation results.
        """
        scenarios = load_scenarios_for_case(case.name)
        results = []
        for scenario in scenarios:
            result = self.run_scenario(case, scenario)
            results.append(result)
        return results


def run_simulation_benchmarks(
    quick_only: bool = False,
    scenario_dir: Path | str | None = None,
    pass_threshold: float = 0.70,
) -> dict[str, Any]:
    """Run benchmarks in simulation mode.

    Runs all embedded scenarios (and optionally custom scenarios from a directory)
    through the benchmark system to validate scoring behavior.

    Args:
        quick_only: Only run scenarios tagged 'quick'.
        scenario_dir: Optional directory containing custom JSON scenarios.
        pass_threshold: Minimum score to pass.

    Returns:
        Dictionary with results and statistics.
    """
    # Get benchmark cases
    cases = get_quick_cases() if quick_only else get_all_cases()
    case_by_name = {c.name: c for c in cases}

    # Get scenarios
    scenarios = get_scenarios_by_tag("quick") if quick_only else get_all_scenarios()

    # Add custom scenarios if directory provided
    if scenario_dir:
        try:
            custom_scenarios = load_scenarios_from_directory(scenario_dir)
            scenarios.extend(custom_scenarios)
            logger.info(f"Loaded {len(custom_scenarios)} custom scenarios from {scenario_dir}")
        except (NotADirectoryError, FileNotFoundError) as e:
            logger.warning(f"Could not load custom scenarios: {e}")

    runner = SimulationBenchmarkRunner(pass_threshold=pass_threshold)
    results: list[SimulationResult] = []

    for scenario in scenarios:
        case = case_by_name.get(scenario.case_name)
        if not case:
            logger.warning(
                f"Scenario '{scenario.name}' references unknown case '{scenario.case_name}'"
            )
            continue

        logger.info(f"Running simulation: {scenario.name}")
        result = runner.run_scenario(case, scenario)
        results.append(result)

        status = "VALID" if result.validation_passed else "INVALID"
        score = result.result.score.overall_score if result.result.score else 0.0
        logger.info(
            f"  {status}: pass={result.result.passed} (expected {scenario.expected_pass}), "
            f"score={score:.2f} (expected {scenario.expected_score_min:.2f}-{scenario.expected_score_max:.2f})"
        )

    # Compute statistics
    total = len(results)
    validated = sum(1 for r in results if r.validation_passed)
    pass_match = sum(1 for r in results if r.pass_matches)
    score_match = sum(1 for r in results if r.score_in_range)

    return {
        "total_scenarios": total,
        "validated": validated,
        "validation_rate": validated / total if total > 0 else 0.0,
        "pass_matches": pass_match,
        "score_in_range": score_match,
        "results": [r.to_dict() for r in results],
    }


def print_simulation_summary(results: dict[str, Any]) -> None:
    """Print a summary of simulation results.

    Args:
        results: Results from run_simulation_benchmarks.
    """
    print("\n" + "=" * 60)
    print("SIMULATION BENCHMARK RESULTS")
    print("=" * 60)

    total = results["total_scenarios"]
    validated = results["validated"]
    rate = results["validation_rate"]

    print(f"\nTotal Scenarios: {total}")
    print(f"Validated: {validated}/{total} ({rate:.1%})")
    print(f"Pass/Fail Matches: {results['pass_matches']}/{total}")
    print(f"Score In Range: {results['score_in_range']}/{total}")

    # Show failures
    failures = [r for r in results["results"] if not r["validation_passed"]]
    if failures:
        print(f"\nValidation Failures ({len(failures)}):")
        for f in failures:
            print(f"  - {f['scenario']}: pass={f['actual_pass']} (expected {f['expected_pass']}), "
                  f"score={f['actual_score']:.2f} (expected {f['expected_score_range']})")

    print("=" * 60)
