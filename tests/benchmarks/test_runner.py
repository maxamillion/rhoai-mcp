"""Tests for benchmark runner."""

from typing import Any

import pytest

from rhoai_mcp.benchmarks.runner import (
    BenchmarkResult,
    BenchmarkRunner,
    BenchmarkRunResults,
)
from rhoai_mcp.benchmarks.suite import BenchmarkCase, BenchmarkSuite


class TestBenchmarkResult:
    """Test BenchmarkResult dataclass."""

    def test_create_passed_result(self) -> None:
        """Test creating a passed result."""
        result = BenchmarkResult(
            case_name="test_case",
            passed=True,
            score=None,
            session=None,
            duration_seconds=1.5,
        )

        assert result.case_name == "test_case"
        assert result.passed is True
        assert result.error is None
        assert result.duration_seconds == 1.5

    def test_create_failed_result_with_error(self) -> None:
        """Test creating a failed result with error."""
        result = BenchmarkResult(
            case_name="test_case",
            passed=False,
            score=None,
            session=None,
            error="Something went wrong",
        )

        assert result.passed is False
        assert result.error == "Something went wrong"

    def test_to_dict_minimal(self) -> None:
        """Test serialization without score or session."""
        result = BenchmarkResult(
            case_name="test",
            passed=True,
            score=None,
            session=None,
        )

        data = result.to_dict()

        assert data["case_name"] == "test"
        assert data["passed"] is True
        assert "score" not in data
        assert "session" not in data


class TestBenchmarkRunResults:
    """Test BenchmarkRunResults dataclass."""

    def test_empty_results(self) -> None:
        """Test empty results."""
        results = BenchmarkRunResults(suite_name="test")

        assert results.total_cases == 0
        assert results.passed_cases == 0
        assert results.failed_cases == 0
        assert results.pass_rate == 0.0
        assert results.average_score == 0.0
        assert results.grade == "F"

    def test_with_results(self) -> None:
        """Test with some results."""
        results = BenchmarkRunResults(suite_name="test")
        results.results = [
            BenchmarkResult(case_name="case1", passed=True, score=None, session=None),
            BenchmarkResult(case_name="case2", passed=True, score=None, session=None),
            BenchmarkResult(case_name="case3", passed=False, score=None, session=None),
        ]

        assert results.total_cases == 3
        assert results.passed_cases == 2
        assert results.failed_cases == 1
        assert abs(results.pass_rate - 0.667) < 0.01

    def test_to_dict(self) -> None:
        """Test serialization."""
        results = BenchmarkRunResults(suite_name="test")
        results.results = [
            BenchmarkResult(case_name="case1", passed=True, score=None, session=None),
        ]

        data = results.to_dict()

        assert data["suite_name"] == "test"
        assert data["total_cases"] == 1
        assert data["passed_cases"] == 1
        assert len(data["results"]) == 1


class TestBenchmarkRunner:
    """Test BenchmarkRunner class."""

    @pytest.fixture
    def runner(self) -> BenchmarkRunner:
        """Create a benchmark runner."""
        return BenchmarkRunner(pass_threshold=0.70)

    def test_setup_benchmark(self, runner: BenchmarkRunner) -> None:
        """Test setting up a benchmark session."""
        case = BenchmarkCase(
            name="test_case",
            task_prompt="Do something",
            required_tools=["tool_a"],
            forbidden_tools=["tool_x"],
            optimal_trajectory=["tool_a", "tool_b"],
            max_steps=5,
        )

        session_id = runner.setup_benchmark(case)

        assert session_id is not None
        assert len(session_id) > 0

    def test_record_tool_call(self, runner: BenchmarkRunner) -> None:
        """Test recording a tool call."""
        case = BenchmarkCase(name="test", task_prompt="Test")
        runner.setup_benchmark(case)

        runner.record_tool_call(
            tool_name="test_tool",
            arguments={"arg": "value"},
            result={"status": "ok"},
            duration_ms=100.0,
            success=True,
        )

        # Should not raise

    def test_complete_benchmark(self, runner: BenchmarkRunner) -> None:
        """Test completing a benchmark."""
        case = BenchmarkCase(
            name="test_case",
            task_prompt="Test task",
            required_tools=["tool_a"],
        )

        session_id = runner.setup_benchmark(case)

        runner.record_tool_call(
            tool_name="tool_a",
            arguments={},
            result={"status": "ok"},
            duration_ms=50.0,
            success=True,
        )

        result = runner.complete_benchmark(session_id, task_completed=True)

        assert result.case_name == "test_case"
        assert result.score is not None
        assert result.session is not None

    def test_complete_nonexistent_session(self, runner: BenchmarkRunner) -> None:
        """Test completing a nonexistent session."""
        result = runner.complete_benchmark("nonexistent-session-id")

        assert result.passed is False
        assert result.error is not None
        assert "not found" in result.error

    def test_run_case(self, runner: BenchmarkRunner) -> None:
        """Test running a complete case."""
        case = BenchmarkCase(
            name="test_case",
            task_prompt="Do something",
            required_tools=["tool_a"],
        )

        def executor(_prompt: str) -> list[dict[str, Any]]:
            return [
                {
                    "tool_name": "tool_a",
                    "arguments": {},
                    "result": {"status": "ok"},
                    "duration_ms": 100.0,
                    "success": True,
                }
            ]

        result = runner.run_case(case, executor)

        assert result.case_name == "test_case"
        assert result.score is not None
        assert result.session is not None
        # Should pass since required tool was called
        assert result.passed is True

    def test_run_case_missing_required_tool(self, runner: BenchmarkRunner) -> None:
        """Test running a case that misses required tools."""
        case = BenchmarkCase(
            name="test_case",
            task_prompt="Do something",
            required_tools=["tool_a", "tool_b"],
        )

        def executor(_prompt: str) -> list[dict[str, Any]]:
            # Only call tool_a, missing tool_b
            return [
                {
                    "tool_name": "tool_a",
                    "arguments": {},
                    "result": {},
                    "duration_ms": 50.0,
                    "success": True,
                }
            ]

        result = runner.run_case(case, executor)

        # Should fail since tool_b was not called
        assert result.passed is False

    def test_run_case_with_exception(self, runner: BenchmarkRunner) -> None:
        """Test running a case that throws an exception."""
        case = BenchmarkCase(name="test", task_prompt="Test")

        def executor(_prompt: str) -> list[dict[str, Any]]:
            raise RuntimeError("Executor failed")

        result = runner.run_case(case, executor)

        assert result.passed is False
        assert result.error is not None
        assert "Executor failed" in result.error

    def test_run_suite(self, runner: BenchmarkRunner) -> None:
        """Test running a complete suite."""
        suite = BenchmarkSuite(
            name="test_suite",
            description="Test suite",
            cases=[
                BenchmarkCase(
                    name="case1",
                    task_prompt="Task 1",
                    required_tools=["tool_a"],
                    tags=["quick"],
                ),
                BenchmarkCase(
                    name="case2",
                    task_prompt="Task 2",
                    required_tools=["tool_b"],
                    tags=["quick"],
                ),
            ],
        )

        def executor(_prompt: str) -> list[dict[str, Any]]:
            # Return both tools to pass both cases
            return [
                {"tool_name": "tool_a", "arguments": {}, "result": {}, "duration_ms": 50, "success": True},
                {"tool_name": "tool_b", "arguments": {}, "result": {}, "duration_ms": 50, "success": True},
            ]

        results = runner.run_suite(suite, executor)

        assert results.suite_name == "test_suite"
        assert results.total_cases == 2
        assert results.passed_cases == 2
        assert results.completed_at is not None

    def test_run_suite_quick_only(self, runner: BenchmarkRunner) -> None:
        """Test running only quick cases."""
        suite = BenchmarkSuite(
            name="test_suite",
            description="Test suite",
            cases=[
                BenchmarkCase(name="quick1", task_prompt="Quick 1", tags=["quick"]),
                BenchmarkCase(name="slow1", task_prompt="Slow 1", tags=["slow"]),
                BenchmarkCase(name="quick2", task_prompt="Quick 2", tags=["quick"]),
            ],
        )

        def executor(_prompt: str) -> list[dict[str, Any]]:
            return []

        results = runner.run_suite(suite, executor, quick_only=True)

        # Should only run the 2 quick cases
        assert results.total_cases == 2
