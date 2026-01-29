"""Tests for golden path benchmark definitions."""


from rhoai_mcp.benchmarks.golden_paths import (
    ALL_SUITES,
    E2E_SUITE,
    PROJECT_SUITE,
    SERVING_SUITE,
    TRAINING_SUITE,
    WORKBENCH_SUITE,
    get_all_cases,
    get_all_suites,
    get_quick_cases,
    get_suite,
)


class TestGoldenPathSuites:
    """Test that golden path suites are properly defined."""

    def test_workbench_suite_exists(self) -> None:
        """Test workbench suite is defined."""
        assert WORKBENCH_SUITE is not None
        assert WORKBENCH_SUITE.name == "workbench"
        assert len(WORKBENCH_SUITE.cases) > 0

    def test_project_suite_exists(self) -> None:
        """Test project suite is defined."""
        assert PROJECT_SUITE is not None
        assert PROJECT_SUITE.name == "project"
        assert len(PROJECT_SUITE.cases) > 0

    def test_serving_suite_exists(self) -> None:
        """Test serving suite is defined."""
        assert SERVING_SUITE is not None
        assert SERVING_SUITE.name == "serving"
        assert len(SERVING_SUITE.cases) > 0

    def test_training_suite_exists(self) -> None:
        """Test training suite is defined."""
        assert TRAINING_SUITE is not None
        assert TRAINING_SUITE.name == "training"

    def test_e2e_suite_exists(self) -> None:
        """Test e2e suite is defined."""
        assert E2E_SUITE is not None
        assert E2E_SUITE.name == "e2e"
        assert len(E2E_SUITE.cases) > 0

    def test_all_suites_dict(self) -> None:
        """Test ALL_SUITES dictionary."""
        assert "workbench" in ALL_SUITES
        assert "project" in ALL_SUITES
        assert "serving" in ALL_SUITES
        assert "training" in ALL_SUITES
        assert "e2e" in ALL_SUITES


class TestGetSuite:
    """Test get_suite function."""

    def test_get_existing_suite(self) -> None:
        """Test getting an existing suite."""
        suite = get_suite("workbench")

        assert suite is not None
        assert suite.name == "workbench"

    def test_get_nonexistent_suite(self) -> None:
        """Test getting a nonexistent suite."""
        suite = get_suite("nonexistent")

        assert suite is None


class TestGetAllSuites:
    """Test get_all_suites function."""

    def test_returns_all_suites(self) -> None:
        """Test that all suites are returned."""
        suites = get_all_suites()

        assert len(suites) == len(ALL_SUITES)
        names = {s.name for s in suites}
        assert "workbench" in names
        assert "project" in names


class TestGetAllCases:
    """Test get_all_cases function."""

    def test_returns_all_cases(self) -> None:
        """Test that all cases from all suites are returned."""
        cases = get_all_cases()

        # Should have cases from all suites
        expected_count = sum(len(s.cases) for s in ALL_SUITES.values())
        assert len(cases) == expected_count

    def test_case_names_unique(self) -> None:
        """Test that case names are unique."""
        cases = get_all_cases()
        names = [c.name for c in cases]

        assert len(names) == len(set(names)), "Duplicate case names found"


class TestGetQuickCases:
    """Test get_quick_cases function."""

    def test_returns_only_quick_cases(self) -> None:
        """Test that only quick cases are returned."""
        cases = get_quick_cases()

        assert len(cases) > 0
        for case in cases:
            assert "quick" in case.tags

    def test_quick_cases_subset_of_all(self) -> None:
        """Test that quick cases are a subset of all cases."""
        quick = get_quick_cases()
        all_cases = get_all_cases()

        quick_names = {c.name for c in quick}
        all_names = {c.name for c in all_cases}

        assert quick_names.issubset(all_names)


class TestBenchmarkCaseStructure:
    """Test that benchmark cases have required structure."""

    def test_all_cases_have_names(self) -> None:
        """Test all cases have names."""
        for case in get_all_cases():
            assert case.name, f"Case missing name: {case}"

    def test_all_cases_have_prompts(self) -> None:
        """Test all cases have task prompts."""
        for case in get_all_cases():
            assert case.task_prompt, f"Case {case.name} missing task_prompt"

    def test_all_cases_have_reasonable_max_steps(self) -> None:
        """Test all cases have reasonable max_steps."""
        for case in get_all_cases():
            assert case.max_steps > 0, f"Case {case.name} has invalid max_steps"
            assert case.max_steps <= 20, f"Case {case.name} has unreasonably high max_steps"

    def test_read_only_cases_have_no_write_requirements(self) -> None:
        """Test read-only tagged cases don't require write tools."""
        write_tools = {"create_", "delete_", "start_", "stop_", "update_"}

        for case in get_all_cases():
            if "read-only" in case.tags:
                for tool in case.required_tools:
                    is_write = any(tool.startswith(w) for w in write_tools)
                    assert not is_write, (
                        f"Read-only case {case.name} requires write tool: {tool}"
                    )
