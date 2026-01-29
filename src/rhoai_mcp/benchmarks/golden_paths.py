"""Golden path benchmark definitions.

This module defines standard benchmark cases representing
common RHOAI workflows for evaluating agent performance.
"""

from rhoai_mcp.benchmarks.suite import BenchmarkCase, BenchmarkSuite

# =============================================================================
# Workbench Benchmarks
# =============================================================================

WORKBENCH_LIST = BenchmarkCase(
    name="workbench_list",
    task_prompt="List all workbenches in the 'test-project' namespace.",
    required_tools=["list_workbenches"],
    forbidden_tools=["create_workbench", "delete_workbench"],
    optimal_trajectory=["list_workbenches"],
    max_steps=3,
    tags=["quick", "read-only", "workbench"],
    description="Simple workbench listing task",
)

WORKBENCH_CREATE_BASIC = BenchmarkCase(
    name="workbench_create_basic",
    task_prompt=(
        "Create a basic Jupyter workbench named 'test-nb' in project 'test-project' "
        "using the standard data science notebook image."
    ),
    required_tools=["list_notebook_images", "create_workbench"],
    forbidden_tools=["delete_workbench"],
    optimal_trajectory=["list_notebook_images", "create_workbench", "get_workbench"],
    acceptable_trajectories=[
        ["list_notebook_images", "create_workbench"],
        ["list_projects", "list_notebook_images", "create_workbench"],
    ],
    max_steps=5,
    tags=["quick", "workbench", "create"],
    description="Create a basic workbench with recommended workflow",
)

WORKBENCH_CREATE_GPU = BenchmarkCase(
    name="workbench_create_gpu",
    task_prompt=(
        "Create a GPU-enabled PyTorch workbench named 'ml-training' in project "
        "'ml-project' with 1 GPU and 50Gi storage for model training."
    ),
    required_tools=["list_notebook_images", "create_workbench"],
    optimal_trajectory=[
        "list_notebook_images",
        "create_workbench",
        "get_workbench",
    ],
    expected_results=[
        {
            "tool_name": "create_workbench",
            "required_fields": ["name", "status"],
        }
    ],
    max_steps=6,
    tags=["gpu", "workbench", "create"],
    description="Create GPU workbench for ML training",
)

WORKBENCH_LIFECYCLE = BenchmarkCase(
    name="workbench_lifecycle",
    task_prompt=(
        "Stop the workbench 'my-workbench' in project 'test-project' to save "
        "resources, then verify it stopped successfully."
    ),
    required_tools=["stop_workbench", "get_workbench"],
    forbidden_tools=["delete_workbench", "create_workbench"],
    optimal_trajectory=["stop_workbench", "get_workbench"],
    max_steps=4,
    tags=["quick", "workbench", "lifecycle"],
    description="Test workbench stop/start lifecycle",
)

WORKBENCH_SUITE = BenchmarkSuite(
    name="workbench",
    description="Benchmarks for workbench (notebook) operations",
    cases=[
        WORKBENCH_LIST,
        WORKBENCH_CREATE_BASIC,
        WORKBENCH_CREATE_GPU,
        WORKBENCH_LIFECYCLE,
    ],
    tags=["notebooks", "core"],
)

# =============================================================================
# Project Benchmarks
# =============================================================================

PROJECT_LIST = BenchmarkCase(
    name="project_list",
    task_prompt="List all Data Science Projects in the cluster.",
    required_tools=["list_projects"],
    optimal_trajectory=["list_projects"],
    max_steps=2,
    tags=["quick", "read-only", "project"],
    description="Simple project listing",
)

PROJECT_INSPECT = BenchmarkCase(
    name="project_inspect",
    task_prompt=(
        "Get detailed information about the project 'test-project' including "
        "its resources and status."
    ),
    required_tools=["get_project"],
    optimal_trajectory=["list_projects", "get_project"],
    acceptable_trajectories=[["get_project"]],
    max_steps=4,
    tags=["quick", "read-only", "project"],
    description="Inspect project details",
)

PROJECT_OVERVIEW = BenchmarkCase(
    name="project_overview",
    task_prompt=(
        "Give me a complete overview of the 'test-project' namespace including "
        "all workbenches, models, data connections, and storage."
    ),
    required_tools=[
        "get_project",
        "list_workbenches",
        "list_inference_services",
        "list_data_connections",
        "list_storage",
    ],
    optimal_trajectory=[
        "get_project",
        "list_workbenches",
        "list_inference_services",
        "list_data_connections",
        "list_storage",
    ],
    max_steps=8,
    tags=["read-only", "project", "comprehensive"],
    description="Complete project resource overview",
)

PROJECT_SUITE = BenchmarkSuite(
    name="project",
    description="Benchmarks for project operations",
    cases=[PROJECT_LIST, PROJECT_INSPECT, PROJECT_OVERVIEW],
    tags=["projects", "core"],
)

# =============================================================================
# Model Serving Benchmarks
# =============================================================================

SERVING_LIST = BenchmarkCase(
    name="serving_list",
    task_prompt="List all deployed models in the 'test-project' namespace.",
    required_tools=["list_inference_services"],
    optimal_trajectory=["list_inference_services"],
    max_steps=3,
    tags=["quick", "read-only", "serving"],
    description="List deployed models",
)

SERVING_INSPECT = BenchmarkCase(
    name="serving_inspect",
    task_prompt=(
        "Get the status and endpoint URL for the model 'my-model' deployed "
        "in project 'test-project'."
    ),
    required_tools=["get_inference_service"],
    optimal_trajectory=["get_inference_service"],
    acceptable_trajectories=[["list_inference_services", "get_inference_service"]],
    max_steps=4,
    tags=["quick", "read-only", "serving"],
    description="Inspect deployed model details",
)

SERVING_SUITE = BenchmarkSuite(
    name="serving",
    description="Benchmarks for model serving operations",
    cases=[SERVING_LIST, SERVING_INSPECT],
    tags=["inference", "serving"],
)

# =============================================================================
# Training Benchmarks
# =============================================================================

TRAINING_LIST_RUNTIMES = BenchmarkCase(
    name="training_list_runtimes",
    task_prompt="List available training runtimes in the cluster.",
    required_tools=["list_training_runtimes"],
    optimal_trajectory=["list_training_runtimes"],
    max_steps=2,
    tags=["quick", "read-only", "training"],
    description="List training runtimes",
)

TRAINING_SUITE = BenchmarkSuite(
    name="training",
    description="Benchmarks for training operations",
    cases=[TRAINING_LIST_RUNTIMES],
    tags=["training"],
)

# =============================================================================
# End-to-End Benchmarks
# =============================================================================

E2E_SETUP_PROJECT = BenchmarkCase(
    name="e2e_setup_project",
    task_prompt=(
        "Set up a complete ML development environment in project 'ml-dev': "
        "1) Create a GPU workbench for training "
        "2) List available data connections "
        "3) Verify everything is set up correctly"
    ),
    required_tools=[
        "list_notebook_images",
        "create_workbench",
        "list_data_connections",
    ],
    optimal_trajectory=[
        "list_projects",
        "list_notebook_images",
        "create_workbench",
        "get_workbench",
        "list_data_connections",
    ],
    max_steps=10,
    tags=["e2e", "setup", "complex"],
    description="Complete ML environment setup",
)

E2E_SUITE = BenchmarkSuite(
    name="e2e",
    description="End-to-end workflow benchmarks",
    cases=[E2E_SETUP_PROJECT],
    tags=["e2e", "complex"],
)

# =============================================================================
# All Suites
# =============================================================================

ALL_SUITES: dict[str, BenchmarkSuite] = {
    "workbench": WORKBENCH_SUITE,
    "project": PROJECT_SUITE,
    "serving": SERVING_SUITE,
    "training": TRAINING_SUITE,
    "e2e": E2E_SUITE,
}


def get_suite(name: str) -> BenchmarkSuite | None:
    """Get a benchmark suite by name.

    Args:
        name: The suite name.

    Returns:
        The benchmark suite, or None if not found.
    """
    return ALL_SUITES.get(name)


def get_all_suites() -> list[BenchmarkSuite]:
    """Get all benchmark suites.

    Returns:
        List of all benchmark suites.
    """
    return list(ALL_SUITES.values())


def get_all_cases() -> list[BenchmarkCase]:
    """Get all benchmark cases from all suites.

    Returns:
        List of all benchmark cases.
    """
    cases = []
    for suite in ALL_SUITES.values():
        cases.extend(suite.cases)
    return cases


def get_quick_cases() -> list[BenchmarkCase]:
    """Get all cases tagged as 'quick' for fast CI runs.

    Returns:
        List of quick benchmark cases.
    """
    return [case for case in get_all_cases() if "quick" in case.tags]
