"""Benchmark runner that integrates with the evaluation framework.

This module provides the BenchmarkRunner class for executing benchmark
cases and collecting results using the existing evaluation infrastructure.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rhoai_mcp.benchmarks.suite import BenchmarkCase, BenchmarkSuite
from rhoai_mcp.evaluation import (
    CompositeEvaluationScore,
    EvaluationSession,
    EvaluationSessionManager,
    calculate_score_from_session,
)

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Result of running a single benchmark case.

    Contains the score, session data, and pass/fail status.
    """

    case_name: str
    """Name of the benchmark case."""

    passed: bool
    """Whether the benchmark passed."""

    score: CompositeEvaluationScore | None
    """The composite evaluation score."""

    session: EvaluationSession | None
    """The evaluation session with all tool calls."""

    error: str | None = None
    """Error message if the benchmark failed to run."""

    duration_seconds: float = 0.0
    """Time taken to run the benchmark."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result: dict[str, Any] = {
            "case_name": self.case_name,
            "passed": self.passed,
            "duration_seconds": self.duration_seconds,
        }

        if self.error:
            result["error"] = self.error

        if self.score:
            result["score"] = {
                "overall": self.score.overall_score,
                "grade": self.score.grade,
                "stability": self.score.stability_score,
                "performance": self.score.performance_score,
                "tool_selection": self.score.tool_selection_score,
                "success_rate": self.score.success_rate_score,
                "parameter_precision": self.score.parameter_precision_score,
                "trajectory": self.score.trajectory_score,
            }

        if self.session:
            result["session"] = {
                "tool_count": self.session.tool_count(),
                "success_count": self.session.success_count(),
                "error_count": self.session.error_count(),
                "tool_sequence": self.session.get_tool_sequence(),
            }

        return result


@dataclass
class BenchmarkRunResults:
    """Aggregate results from running a benchmark suite.

    Contains overall statistics and individual case results.
    """

    suite_name: str
    """Name of the benchmark suite."""

    results: list[BenchmarkResult] = field(default_factory=list)
    """Individual case results."""

    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    """When the benchmark run started."""

    completed_at: datetime | None = None
    """When the benchmark run completed."""

    @property
    def total_cases(self) -> int:
        """Total number of cases run."""
        return len(self.results)

    @property
    def passed_cases(self) -> int:
        """Number of cases that passed."""
        return sum(1 for r in self.results if r.passed)

    @property
    def failed_cases(self) -> int:
        """Number of cases that failed."""
        return sum(1 for r in self.results if not r.passed)

    @property
    def pass_rate(self) -> float:
        """Percentage of cases that passed."""
        if not self.results:
            return 0.0
        return self.passed_cases / len(self.results)

    @property
    def average_score(self) -> float:
        """Average overall score across all cases."""
        scores = [r.score.overall_score for r in self.results if r.score]
        if not scores:
            return 0.0
        return sum(scores) / len(scores)

    @property
    def grade(self) -> str:
        """Letter grade based on average score."""
        avg = self.average_score
        if avg >= 0.90:
            return "A"
        if avg >= 0.80:
            return "B"
        if avg >= 0.70:
            return "C"
        if avg >= 0.60:
            return "D"
        return "F"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "suite_name": self.suite_name,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_cases": self.total_cases,
            "passed_cases": self.passed_cases,
            "failed_cases": self.failed_cases,
            "pass_rate": self.pass_rate,
            "average_score": self.average_score,
            "grade": self.grade,
            "results": [r.to_dict() for r in self.results],
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, path: Path | str) -> None:
        """Save results to a JSON file."""
        path = Path(path)
        path.write_text(self.to_json())


# Type alias for agent executor function
AgentExecutor = Callable[[str], list[dict[str, Any]]]


class BenchmarkRunner:
    """Runs benchmark cases and collects evaluation results.

    Integrates with the existing evaluation framework to track
    tool calls and calculate scores.
    """

    def __init__(self, pass_threshold: float = 0.70) -> None:
        """Initialize the benchmark runner.

        Args:
            pass_threshold: Minimum score to pass (default 0.70 = C grade).
        """
        self._session_manager = EvaluationSessionManager()
        self._pass_threshold = pass_threshold

    def setup_benchmark(self, case: BenchmarkCase) -> str:
        """Set up an evaluation session for a benchmark case.

        Configures the session manager with the case's expectations.

        Args:
            case: The benchmark case to set up.

        Returns:
            The session ID.
        """
        session = self._session_manager.start_session(
            name=case.name,
            task_definition=case.task_prompt,
            expected_outcome=f"Complete task using: {', '.join(case.required_tools)}",
        )

        # Set expected trajectory
        self._session_manager.set_expected_trajectory(
            required_tools=case.required_tools,
            forbidden_tools=case.forbidden_tools,
            expected_order=case.optimal_trajectory if case.optimal_trajectory else None,
        )

        # Set trajectory spec
        self._session_manager.set_trajectory_spec(
            goal_description=case.task_prompt,
            optimal_trajectory=case.optimal_trajectory,
            acceptable_trajectories=case.acceptable_trajectories,
            max_steps=case.max_steps,
            required_checkpoints=case.required_tools,
        )

        # Set expected results
        for expected in case.expected_results:
            self._session_manager.add_expected_result(
                tool_name=expected.get("tool_name", ""),
                required_fields=expected.get("required_fields", []),
                field_values=expected.get("field_values", {}),
            )

        return session.session_id

    def record_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        result: Any,
        duration_ms: float,
        success: bool,
        error: str | None = None,
    ) -> None:
        """Record a tool call during benchmark execution.

        Args:
            tool_name: Name of the tool called.
            arguments: Arguments passed to the tool.
            result: Result from the tool.
            duration_ms: Execution time in milliseconds.
            success: Whether the call succeeded.
            error: Error message if failed.
        """
        self._session_manager.record_tool_call(
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            duration_ms=duration_ms,
            success=success,
            error=error,
        )

    def complete_benchmark(
        self,
        session_id: str,
        task_completed: bool = True,
    ) -> BenchmarkResult:
        """Complete a benchmark and calculate the score.

        Args:
            session_id: The session ID from setup_benchmark.
            task_completed: Whether the task was completed successfully.

        Returns:
            The benchmark result with score.
        """
        session = self._session_manager.get_session(session_id)
        if not session:
            return BenchmarkResult(
                case_name="unknown",
                passed=False,
                score=None,
                session=None,
                error=f"Session {session_id} not found",
            )

        # End the session
        self._session_manager.end_session(
            session_id=session_id,
            task_completed=task_completed,
        )

        # Calculate score
        score = calculate_score_from_session(session)

        # Determine pass/fail
        passed = score.overall_score >= self._pass_threshold and task_completed

        return BenchmarkResult(
            case_name=session.name,
            passed=passed,
            score=score,
            session=session,
            duration_seconds=session.duration_seconds(),
        )

    def run_case(
        self,
        case: BenchmarkCase,
        agent_executor: AgentExecutor,
    ) -> BenchmarkResult:
        """Run a single benchmark case.

        Args:
            case: The benchmark case to run.
            agent_executor: Function that executes the task and returns tool calls.
                Should return a list of dicts with: tool_name, arguments, result,
                duration_ms, success, error.

        Returns:
            The benchmark result.
        """
        try:
            session_id = self.setup_benchmark(case)

            # Execute the task
            tool_calls = agent_executor(case.task_prompt)

            # Record all tool calls
            for call in tool_calls:
                self.record_tool_call(
                    tool_name=call.get("tool_name", "unknown"),
                    arguments=call.get("arguments", {}),
                    result=call.get("result"),
                    duration_ms=call.get("duration_ms", 0.0),
                    success=call.get("success", True),
                    error=call.get("error"),
                )

            # Check if required tools were called
            called_tools = {call.get("tool_name") for call in tool_calls}
            required_called = all(t in called_tools for t in case.required_tools)

            return self.complete_benchmark(
                session_id=session_id,
                task_completed=required_called,
            )

        except Exception as e:
            logger.exception(f"Benchmark case {case.name} failed: {e}")
            return BenchmarkResult(
                case_name=case.name,
                passed=False,
                score=None,
                session=None,
                error=str(e),
            )

    def run_suite(
        self,
        suite: BenchmarkSuite,
        agent_executor: AgentExecutor,
        quick_only: bool = False,
    ) -> BenchmarkRunResults:
        """Run all cases in a benchmark suite.

        Args:
            suite: The benchmark suite to run.
            agent_executor: Function that executes tasks.
            quick_only: Only run cases tagged 'quick'.

        Returns:
            Aggregate results for the suite.
        """
        results = BenchmarkRunResults(suite_name=suite.name)

        cases = suite.get_quick_cases() if quick_only else suite.cases

        for case in cases:
            logger.info(f"Running benchmark: {case.name}")
            result = self.run_case(case, agent_executor)
            results.results.append(result)
            score_str = f"{result.score.overall_score:.2f}" if result.score else "N/A"
            logger.info(
                f"Benchmark {case.name}: "
                f"{'PASS' if result.passed else 'FAIL'} "
                f"(score: {score_str})"
            )

        results.completed_at = datetime.now(timezone.utc)
        return results

    def run_all_suites(
        self,
        suites: list[BenchmarkSuite],
        agent_executor: AgentExecutor,
        quick_only: bool = False,
    ) -> dict[str, BenchmarkRunResults]:
        """Run multiple benchmark suites.

        Args:
            suites: List of benchmark suites to run.
            agent_executor: Function that executes tasks.
            quick_only: Only run quick cases.

        Returns:
            Dictionary mapping suite names to results.
        """
        all_results = {}

        for suite in suites:
            logger.info(f"Running suite: {suite.name}")
            results = self.run_suite(suite, agent_executor, quick_only)
            all_results[suite.name] = results
            logger.info(
                f"Suite {suite.name}: "
                f"{results.passed_cases}/{results.total_cases} passed "
                f"(grade: {results.grade})"
            )

        return all_results
