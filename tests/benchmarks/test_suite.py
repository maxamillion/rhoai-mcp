"""Tests for benchmark suite and case definitions."""


from rhoai_mcp.benchmarks.suite import BenchmarkCase, BenchmarkSuite


class TestBenchmarkCase:
    """Test BenchmarkCase dataclass."""

    def test_create_minimal_case(self) -> None:
        """Test creating a minimal benchmark case."""
        case = BenchmarkCase(
            name="test_case",
            task_prompt="Do something",
        )

        assert case.name == "test_case"
        assert case.task_prompt == "Do something"
        assert case.required_tools == []
        assert case.forbidden_tools == []
        assert case.optimal_trajectory == []
        assert case.acceptable_trajectories == []
        assert case.expected_results == []
        assert case.max_steps == 10
        assert case.tags == []
        assert case.description == ""
        assert case.setup_requirements == []

    def test_create_full_case(self) -> None:
        """Test creating a benchmark case with all fields."""
        case = BenchmarkCase(
            name="full_case",
            task_prompt="Complete the full task",
            required_tools=["tool_a", "tool_b"],
            forbidden_tools=["tool_x"],
            optimal_trajectory=["tool_a", "tool_b", "tool_c"],
            acceptable_trajectories=[["tool_a", "tool_c"]],
            expected_results=[{"tool_name": "tool_a", "required_fields": ["name"]}],
            max_steps=5,
            tags=["quick", "test"],
            description="A full test case",
            setup_requirements=["project:test"],
        )

        assert case.name == "full_case"
        assert case.required_tools == ["tool_a", "tool_b"]
        assert case.forbidden_tools == ["tool_x"]
        assert case.optimal_trajectory == ["tool_a", "tool_b", "tool_c"]
        assert len(case.acceptable_trajectories) == 1
        assert len(case.expected_results) == 1
        assert case.max_steps == 5
        assert case.tags == ["quick", "test"]
        assert case.description == "A full test case"
        assert case.setup_requirements == ["project:test"]

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        case = BenchmarkCase(
            name="test",
            task_prompt="Test task",
            required_tools=["tool_a"],
            tags=["quick"],
        )

        data = case.to_dict()

        assert data["name"] == "test"
        assert data["task_prompt"] == "Test task"
        assert data["required_tools"] == ["tool_a"]
        assert data["tags"] == ["quick"]
        assert data["max_steps"] == 10


class TestBenchmarkSuite:
    """Test BenchmarkSuite dataclass."""

    def test_create_empty_suite(self) -> None:
        """Test creating an empty suite."""
        suite = BenchmarkSuite(
            name="empty_suite",
            description="An empty test suite",
        )

        assert suite.name == "empty_suite"
        assert suite.description == "An empty test suite"
        assert suite.cases == []
        assert suite.tags == []

    def test_create_suite_with_cases(self) -> None:
        """Test creating a suite with cases."""
        case1 = BenchmarkCase(name="case1", task_prompt="Task 1", tags=["quick"])
        case2 = BenchmarkCase(name="case2", task_prompt="Task 2", tags=["slow"])
        case3 = BenchmarkCase(name="case3", task_prompt="Task 3", tags=["quick", "gpu"])

        suite = BenchmarkSuite(
            name="test_suite",
            description="Test suite",
            cases=[case1, case2, case3],
            tags=["testing"],
        )

        assert len(suite.cases) == 3
        assert suite.tags == ["testing"]

    def test_get_cases_by_tag(self) -> None:
        """Test filtering cases by tag."""
        case1 = BenchmarkCase(name="case1", task_prompt="Task 1", tags=["quick"])
        case2 = BenchmarkCase(name="case2", task_prompt="Task 2", tags=["slow"])
        case3 = BenchmarkCase(name="case3", task_prompt="Task 3", tags=["quick", "gpu"])

        suite = BenchmarkSuite(
            name="suite",
            description="desc",
            cases=[case1, case2, case3],
        )

        quick_cases = suite.get_cases_by_tag("quick")

        assert len(quick_cases) == 2
        assert case1 in quick_cases
        assert case3 in quick_cases
        assert case2 not in quick_cases

    def test_get_quick_cases(self) -> None:
        """Test get_quick_cases helper."""
        case1 = BenchmarkCase(name="case1", task_prompt="Task 1", tags=["quick"])
        case2 = BenchmarkCase(name="case2", task_prompt="Task 2", tags=["slow"])

        suite = BenchmarkSuite(
            name="suite",
            description="desc",
            cases=[case1, case2],
        )

        quick = suite.get_quick_cases()

        assert len(quick) == 1
        assert quick[0].name == "case1"

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        case = BenchmarkCase(name="case1", task_prompt="Task")

        suite = BenchmarkSuite(
            name="suite",
            description="Suite description",
            cases=[case],
            tags=["tag1"],
        )

        data = suite.to_dict()

        assert data["name"] == "suite"
        assert data["description"] == "Suite description"
        assert data["total_cases"] == 1
        assert len(data["cases"]) == 1
        assert data["tags"] == ["tag1"]
