"""Tests for simulation mode benchmarks."""

import json
import tempfile
from pathlib import Path

import pytest

from rhoai_mcp.benchmarks.fixtures import (
    EMBEDDED_SCENARIOS,
    SimulatedToolCall,
    SimulationScenario,
    get_all_scenarios,
    get_scenarios_by_tag,
    load_from_json,
    load_scenario,
    load_scenarios_for_case,
    load_scenarios_from_directory,
)
from rhoai_mcp.benchmarks.simulation import (
    SimulationBenchmarkRunner,
    SimulationExecutor,
    SimulationResult,
    create_simulation_executor,
    run_simulation_benchmarks,
)
from rhoai_mcp.benchmarks.suite import BenchmarkCase


class TestSimulatedToolCall:
    """Test SimulatedToolCall dataclass."""

    def test_create_basic_call(self) -> None:
        """Test creating a basic tool call."""
        call = SimulatedToolCall(
            tool_name="list_workbenches",
            arguments={"namespace": "test"},
            result={"workbenches": []},
        )

        assert call.tool_name == "list_workbenches"
        assert call.arguments == {"namespace": "test"}
        assert call.success is True
        assert call.error is None

    def test_create_failed_call(self) -> None:
        """Test creating a failed tool call."""
        call = SimulatedToolCall(
            tool_name="list_workbenches",
            success=False,
            error="Connection refused",
        )

        assert call.success is False
        assert call.error == "Connection refused"

    def test_to_dict(self) -> None:
        """Test serialization to dict."""
        call = SimulatedToolCall(
            tool_name="test_tool",
            arguments={"arg": "value"},
            result={"status": "ok"},
            duration_ms=100.0,
        )

        data = call.to_dict()

        assert data["tool_name"] == "test_tool"
        assert data["arguments"] == {"arg": "value"}
        assert data["result"] == {"status": "ok"}
        assert data["duration_ms"] == 100.0
        assert data["success"] is True


class TestSimulationScenario:
    """Test SimulationScenario dataclass."""

    def test_create_scenario(self) -> None:
        """Test creating a scenario."""
        scenario = SimulationScenario(
            name="test_scenario",
            case_name="test_case",
            description="A test scenario",
            tool_calls=[
                SimulatedToolCall(tool_name="tool_a"),
                SimulatedToolCall(tool_name="tool_b"),
            ],
            expected_pass=True,
            expected_score_min=0.80,
            expected_score_max=1.0,
            tags=["test", "quick"],
        )

        assert scenario.name == "test_scenario"
        assert scenario.case_name == "test_case"
        assert len(scenario.tool_calls) == 2
        assert scenario.expected_pass is True
        assert "quick" in scenario.tags

    def test_to_dict(self) -> None:
        """Test serialization."""
        scenario = SimulationScenario(
            name="test",
            case_name="case",
            description="desc",
            tool_calls=[SimulatedToolCall(tool_name="tool_a")],
        )

        data = scenario.to_dict()

        assert data["name"] == "test"
        assert data["case_name"] == "case"
        assert len(data["tool_calls"]) == 1


class TestEmbeddedScenarios:
    """Test embedded scenario definitions."""

    def test_embedded_scenarios_exist(self) -> None:
        """Verify embedded scenarios are defined."""
        assert len(EMBEDDED_SCENARIOS) >= 5

    def test_load_scenario_by_name(self) -> None:
        """Test loading scenario by name."""
        scenario = load_scenario("workbench_list_optimal")

        assert scenario is not None
        assert scenario.case_name == "workbench_list"
        assert "optimal" in scenario.tags

    def test_load_scenario_not_found(self) -> None:
        """Test loading nonexistent scenario."""
        scenario = load_scenario("nonexistent")

        assert scenario is None

    def test_load_scenarios_for_case(self) -> None:
        """Test loading scenarios for a case."""
        scenarios = load_scenarios_for_case("workbench_list")

        assert len(scenarios) >= 2
        assert all(s.case_name == "workbench_list" for s in scenarios)

    def test_load_scenarios_for_unknown_case(self) -> None:
        """Test loading scenarios for unknown case."""
        scenarios = load_scenarios_for_case("unknown_case")

        assert scenarios == []

    def test_get_all_scenarios(self) -> None:
        """Test getting all scenarios."""
        scenarios = get_all_scenarios()

        assert len(scenarios) == len(EMBEDDED_SCENARIOS)

    def test_get_scenarios_by_tag(self) -> None:
        """Test filtering by tag."""
        optimal = get_scenarios_by_tag("optimal")
        failure = get_scenarios_by_tag("failure")
        suboptimal = get_scenarios_by_tag("suboptimal")

        assert len(optimal) >= 3
        assert len(failure) >= 2
        assert len(suboptimal) >= 2
        assert all("optimal" in s.tags for s in optimal)
        assert all("failure" in s.tags for s in failure)
        assert all("suboptimal" in s.tags for s in suboptimal)


class TestLoadFromJson:
    """Test loading scenarios from JSON files."""

    def test_load_single_scenario(self) -> None:
        """Test loading a single scenario from JSON."""
        scenario_data = {
            "name": "json_scenario",
            "case_name": "workbench_list",
            "description": "From JSON",
            "tool_calls": [
                {
                    "tool_name": "list_workbenches",
                    "arguments": {"namespace": "test"},
                    "result": {"workbenches": []},
                }
            ],
            "expected_pass": True,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(scenario_data, f)
            path = Path(f.name)

        try:
            scenarios = load_from_json(path)

            assert len(scenarios) == 1
            assert scenarios[0].name == "json_scenario"
            assert scenarios[0].case_name == "workbench_list"
            assert len(scenarios[0].tool_calls) == 1
        finally:
            path.unlink()

    def test_load_multiple_scenarios(self) -> None:
        """Test loading multiple scenarios from JSON array."""
        scenario_data = [
            {"name": "s1", "case_name": "c1", "description": "First"},
            {"name": "s2", "case_name": "c2", "description": "Second"},
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(scenario_data, f)
            path = Path(f.name)

        try:
            scenarios = load_from_json(path)

            assert len(scenarios) == 2
            assert scenarios[0].name == "s1"
            assert scenarios[1].name == "s2"
        finally:
            path.unlink()

    def test_load_file_not_found(self) -> None:
        """Test loading from nonexistent file."""
        with pytest.raises(FileNotFoundError):
            load_from_json("/nonexistent/path.json")

    def test_load_invalid_json(self) -> None:
        """Test loading invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json {{{")
            path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="Invalid JSON"):
                load_from_json(path)
        finally:
            path.unlink()


class TestLoadScenariosFromDirectory:
    """Test loading scenarios from a directory."""

    def test_load_from_directory(self) -> None:
        """Test loading from a directory of JSON files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = Path(tmpdir)

            # Create two JSON files
            (dir_path / "scenario1.json").write_text(
                json.dumps({"name": "s1", "case_name": "c1", "description": "First"})
            )
            (dir_path / "scenario2.json").write_text(
                json.dumps({"name": "s2", "case_name": "c2", "description": "Second"})
            )

            scenarios = load_scenarios_from_directory(dir_path)

            assert len(scenarios) == 2
            names = {s.name for s in scenarios}
            assert names == {"s1", "s2"}

    def test_load_from_nonexistent_directory(self) -> None:
        """Test loading from nonexistent directory."""
        with pytest.raises(NotADirectoryError):
            load_scenarios_from_directory("/nonexistent/directory")

    def test_skip_invalid_files(self) -> None:
        """Test that invalid JSON files are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = Path(tmpdir)

            (dir_path / "valid.json").write_text(
                json.dumps({"name": "valid", "case_name": "c1", "description": "Valid"})
            )
            (dir_path / "invalid.json").write_text("not valid json")

            scenarios = load_scenarios_from_directory(dir_path)

            assert len(scenarios) == 1
            assert scenarios[0].name == "valid"


class TestSimulationExecutor:
    """Test SimulationExecutor class."""

    def test_execute_returns_tool_calls(self) -> None:
        """Test executor returns predefined tool calls."""
        scenario = SimulationScenario(
            name="test",
            case_name="test_case",
            description="Test",
            tool_calls=[
                SimulatedToolCall(tool_name="tool_a", arguments={"x": 1}),
                SimulatedToolCall(tool_name="tool_b", arguments={"y": 2}),
            ],
        )

        executor = SimulationExecutor(scenario)
        result = executor.execute("ignored prompt")

        assert len(result) == 2
        assert result[0]["tool_name"] == "tool_a"
        assert result[0]["arguments"] == {"x": 1}
        assert result[1]["tool_name"] == "tool_b"

    def test_as_executor(self) -> None:
        """Test getting as AgentExecutor callable."""
        scenario = SimulationScenario(
            name="test",
            case_name="test_case",
            description="Test",
            tool_calls=[SimulatedToolCall(tool_name="tool_a")],
        )

        executor = SimulationExecutor(scenario)
        callable_executor = executor.as_executor()

        # Should be callable
        result = callable_executor("any prompt")
        assert len(result) == 1


class TestCreateSimulationExecutor:
    """Test create_simulation_executor factory."""

    def test_creates_executor(self) -> None:
        """Test factory creates executor."""
        scenario = SimulationScenario(
            name="test",
            case_name="case",
            description="desc",
        )

        executor = create_simulation_executor(scenario)

        assert isinstance(executor, SimulationExecutor)
        assert executor.scenario == scenario


class TestSimulationResult:
    """Test SimulationResult class."""

    def test_score_in_range_true(self) -> None:
        """Test score in range detection."""
        # Create a mock result with score
        from rhoai_mcp.benchmarks.runner import BenchmarkResult
        from rhoai_mcp.evaluation import CompositeEvaluationScore

        score = CompositeEvaluationScore(
            overall_score=0.85,
            grade="B",
            stability_score=0.90,
            performance_score=0.80,
            tool_selection_score=0.85,
            success_rate_score=1.0,
            parameter_precision_score=0.80,
            trajectory_score=0.70,
        )

        result = BenchmarkResult(
            case_name="test",
            passed=True,
            score=score,
            session=None,
        )

        scenario = SimulationScenario(
            name="test",
            case_name="test",
            description="Test",
            expected_score_min=0.80,
            expected_score_max=0.90,
        )

        sim_result = SimulationResult(scenario, result)

        assert sim_result.score_in_range is True

    def test_pass_matches(self) -> None:
        """Test pass/fail matching."""
        from rhoai_mcp.benchmarks.runner import BenchmarkResult

        result = BenchmarkResult(
            case_name="test",
            passed=True,
            score=None,
            session=None,
        )

        scenario = SimulationScenario(
            name="test",
            case_name="test",
            description="Test",
            expected_pass=True,
        )

        sim_result = SimulationResult(scenario, result)

        assert sim_result.pass_matches is True


class TestSimulationBenchmarkRunner:
    """Test SimulationBenchmarkRunner class."""

    def test_run_scenario(self) -> None:
        """Test running a single scenario."""
        case = BenchmarkCase(
            name="workbench_list",
            task_prompt="List workbenches",
            required_tools=["list_workbenches"],
        )

        scenario = SimulationScenario(
            name="test_scenario",
            case_name="workbench_list",
            description="Test",
            tool_calls=[
                SimulatedToolCall(
                    tool_name="list_workbenches",
                    arguments={"namespace": "test"},
                    result={"workbenches": []},
                )
            ],
            expected_pass=True,
        )

        runner = SimulationBenchmarkRunner()
        result = runner.run_scenario(case, scenario)

        assert result.result.case_name == "workbench_list"
        assert result.result.passed is True


class TestRunSimulationBenchmarks:
    """Test run_simulation_benchmarks function."""

    def test_run_quick_only(self) -> None:
        """Test running only quick scenarios."""
        results = run_simulation_benchmarks(quick_only=True)

        assert results["total_scenarios"] >= 1
        assert "validation_rate" in results
        assert "results" in results

    def test_run_all(self) -> None:
        """Test running all scenarios."""
        results = run_simulation_benchmarks(quick_only=False)

        assert results["total_scenarios"] >= len(EMBEDDED_SCENARIOS) - 1
        # Some scenarios may reference cases that don't exist in quick mode

    def test_optimal_scenarios_pass(self) -> None:
        """Verify optimal scenarios produce passing results."""
        results = run_simulation_benchmarks()

        optimal_results = [
            r for r in results["results"] if "optimal" in r.get("scenario", "")
        ]

        for r in optimal_results:
            assert r["actual_pass"] is True, f"Optimal scenario {r['scenario']} should pass"

    def test_missing_required_scenarios_fail(self) -> None:
        """Verify scenarios missing required tools fail.

        When a scenario doesn't call a required tool, it should fail
        because task_completed will be False.
        """
        results = run_simulation_benchmarks()

        missing_required = [
            r for r in results["results"]
            if r["scenario"].endswith("_missing_required")
        ]

        for r in missing_required:
            assert r["actual_pass"] is False, f"Scenario {r['scenario']} should fail"

    def test_error_scenarios_have_low_scores(self) -> None:
        """Verify scenarios with errors have low scores.

        When tool calls fail, the success_rate_score drops, resulting
        in a lower overall score (though still may pass if required
        tools were called).
        """
        results = run_simulation_benchmarks()

        error_results = [
            r for r in results["results"]
            if r["scenario"].endswith("_error")
        ]

        for r in error_results:
            # Error scenarios should have lower scores due to failed tool calls
            # The score is penalized but may still be above the pass threshold
            assert r["actual_score"] <= 0.75, (
                f"Scenario {r['scenario']} should have lower score, got {r['actual_score']}"
            )
