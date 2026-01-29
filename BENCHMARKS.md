# Benchmarks and Evaluation

This document describes the benchmark and evaluation systems in RHOAI MCP Server for measuring and analyzing agent performance.

## Overview

RHOAI MCP includes two complementary systems for agent evaluation:

1. **Evaluation Harness** - Runtime instrumentation layer using pluggy hooks to capture tool execution data
2. **Benchmark Framework** - Test harness for repeatable, automated evaluation against predefined "golden paths"

These systems are layered - the benchmark framework builds on top of the evaluation harness:

```
┌─────────────────────────────────────────────────────┐
│           Benchmark Framework                        │
│  - Defines test cases with golden paths             │
│  - Runs repeatable regression tests                 │
│  - Produces pass/fail grades                        │
├─────────────────────────────────────────────────────┤
│           Evaluation Harness                         │
│  - Captures tool calls via pluggy hooks             │
│  - Manages sessions and expectations                │
│  - Calculates 6-dimension composite scores          │
├─────────────────────────────────────────────────────┤
│           Pluggy Hook Infrastructure                 │
│  - rhoai_before_tool_call / rhoai_after_tool_call   │
│  - Non-invasive instrumentation                     │
└─────────────────────────────────────────────────────┘
```

## Evaluation Harness

The evaluation harness provides runtime instrumentation for capturing and analyzing agent behavior through pluggy hooks.

### Architecture

```
src/rhoai_mcp/
├── hooks.py                    # Pluggy hook specifications
├── evaluation/
│   ├── models.py               # Data structures (Session, ToolCall, etc.)
│   ├── session_manager.py      # Session lifecycle management
│   ├── metrics.py              # Six evaluation dimensions
│   ├── scoring.py              # Composite scoring calculations
│   └── validation.py           # Result validation
└── domains/evaluation/
    ├── plugin.py               # EvaluationPlugin (hook implementations)
    └── tools.py                # MCP tools for evaluation control
```

### Pluggy Hooks

The evaluation system uses pluggy hooks defined in `hooks.py`:

| Hook | Purpose |
|------|---------|
| `rhoai_before_tool_call` | Called before tool execution (logging) |
| `rhoai_after_tool_call` | Called after tool execution (captures metrics) |

These hooks fire automatically on every tool invocation, allowing non-invasive instrumentation without modifying tool code.

### Session-Based Tracking

Evaluation sessions provide context for grouping and analyzing tool calls:

```python
# Start a session before agent tasks
session = session_manager.start_session(
    name="my-evaluation",
    task_definition="Deploy a model to production",
    expected_outcome="Model deployed and serving"
)

# Tool calls are automatically captured via hooks
# ...agent performs task...

# End session and get results
session_manager.end_session(task_completed=True)
score = calculate_score_from_session(session)
```

### Six Evaluation Dimensions

The harness evaluates agent performance across six dimensions with configurable weights:

| Dimension | Default Weight | What It Measures |
|-----------|----------------|------------------|
| **Trajectory** | 25% | Path efficiency, goal achievement, similarity to optimal path |
| **Tool Selection** | 20% | Required tool coverage, forbidden violations, order violations |
| **Success Rate** | 15% | Tool execution success rate |
| **Stability** | 15% | Consistency across repeated calls |
| **Parameter Precision** | 15% | Correct parameter types and values |
| **Performance** | 10% | Latency (p50/p95/p99) vs baseline |

### Scoring

The composite score combines all dimensions into a 0.0-1.0 score with a letter grade:

| Grade | Score Range |
|-------|-------------|
| A | >= 0.90 |
| B | >= 0.80 |
| C | >= 0.70 |
| D | >= 0.60 |
| F | < 0.60 |

Custom weights can be provided:

```python
custom_weights = {
    "stability": 0.20,
    "performance": 0.05,
    "tool_selection": 0.25,
    "success_rate": 0.15,
    "parameter_precision": 0.10,
    "trajectory": 0.25,
}
score = calculate_score_from_session(session, weights=custom_weights)
```

### MCP Tools for Evaluation

The evaluation plugin exposes 18 MCP tools for controlling evaluation:

| Category | Tools |
|----------|-------|
| Session Management | `eval_start_session`, `eval_end_session`, `eval_cancel_session`, `eval_get_session_status`, `eval_list_sessions` |
| Expectations | `eval_add_expected_result`, `eval_set_expected_trajectory`, `eval_set_trajectory_spec`, `eval_set_parameter_specs` |
| Validation | `eval_validate_session_results` |
| Reports | `eval_get_report`, `eval_get_composite_score` |
| Metrics | `eval_get_stability_metrics`, `eval_get_performance_metrics`, `eval_get_trajectory_analysis` |

## Benchmark Framework

The benchmark framework provides repeatable test cases for automated agent evaluation.

### Architecture

```
src/rhoai_mcp/benchmarks/
├── suite.py          # BenchmarkCase and BenchmarkSuite dataclasses
├── golden_paths.py   # Predefined benchmark suites
├── runner.py         # BenchmarkRunner execution engine
└── __init__.py       # Public API exports
```

### Benchmark Case Structure

A `BenchmarkCase` defines a single test with expected behavior:

```python
from rhoai_mcp.benchmarks import BenchmarkCase

case = BenchmarkCase(
    name="workbench_create_basic",
    task_prompt="Create a Jupyter workbench named 'test-nb' in project 'test-project'",
    required_tools=["list_notebook_images", "create_workbench"],
    forbidden_tools=["delete_workbench"],
    optimal_trajectory=["list_notebook_images", "create_workbench", "get_workbench"],
    acceptable_trajectories=[
        ["list_notebook_images", "create_workbench"],
    ],
    max_steps=5,
    tags=["quick", "workbench", "create"],
    description="Create a basic workbench with recommended workflow",
)
```

| Field | Description |
|-------|-------------|
| `name` | Unique identifier for the case |
| `task_prompt` | Prompt describing what the agent should do |
| `required_tools` | Tools that MUST be called |
| `forbidden_tools` | Tools that should NOT be called |
| `optimal_trajectory` | Ideal sequence of tool calls |
| `acceptable_trajectories` | Alternative valid sequences |
| `max_steps` | Maximum tool calls before failure |
| `tags` | Categorization (e.g., "quick", "gpu") |
| `expected_results` | Result patterns for validation |

### Benchmark Suites

A `BenchmarkSuite` groups related cases:

```python
from rhoai_mcp.benchmarks import BenchmarkSuite

suite = BenchmarkSuite(
    name="workbench",
    description="Benchmarks for workbench operations",
    cases=[case1, case2, case3],
    tags=["notebooks", "core"],
)

# Filter by tag
quick_cases = suite.get_quick_cases()
```

### Predefined Golden Paths

The framework includes predefined suites in `golden_paths.py`:

| Suite | Cases | Description |
|-------|-------|-------------|
| `workbench` | 4 | Workbench CRUD and lifecycle operations |
| `project` | 3 | Project listing, inspection, and overview |
| `serving` | 2 | Model deployment operations |
| `training` | 1 | Training runtime operations |
| `e2e` | 1 | End-to-end workflow tests |

Access suites programmatically:

```python
from rhoai_mcp.benchmarks.golden_paths import (
    get_suite,
    get_all_suites,
    get_all_cases,
    get_quick_cases,
)

# Get specific suite
workbench_suite = get_suite("workbench")

# Get all suites
all_suites = get_all_suites()

# Get cases tagged "quick" for CI
quick_cases = get_quick_cases()
```

### Running Benchmarks

The `BenchmarkRunner` orchestrates execution:

```python
from rhoai_mcp.benchmarks import BenchmarkRunner, get_suite

# Create runner with pass threshold (default 0.70 = C grade)
runner = BenchmarkRunner(pass_threshold=0.70)

# Define agent executor - returns list of tool call dicts
def my_agent_executor(prompt: str) -> list[dict]:
    """Execute task and return tool calls."""
    # Your agent implementation here
    return [
        {
            "tool_name": "list_workbenches",
            "arguments": {"namespace": "test-project"},
            "result": {"items": []},
            "duration_ms": 150.0,
            "success": True,
            "error": None,
        },
        # ... more tool calls
    ]

# Run single case
result = runner.run_case(case, my_agent_executor)
print(f"Passed: {result.passed}, Score: {result.score.overall_score}")

# Run entire suite
suite = get_suite("workbench")
results = runner.run_suite(suite, my_agent_executor)
print(f"Pass rate: {results.pass_rate:.0%}, Grade: {results.grade}")

# Run quick cases only (for CI)
results = runner.run_suite(suite, my_agent_executor, quick_only=True)

# Run all suites
all_results = runner.run_all_suites(get_all_suites(), my_agent_executor)
```

### Benchmark Results

`BenchmarkResult` contains individual case results:

```python
result = runner.run_case(case, executor)

print(result.case_name)           # "workbench_create_basic"
print(result.passed)              # True/False
print(result.score.overall_score) # 0.85
print(result.score.grade)         # "B"
print(result.duration_seconds)    # 2.5
print(result.error)               # None or error message
```

`BenchmarkRunResults` aggregates suite results:

```python
results = runner.run_suite(suite, executor)

print(results.suite_name)      # "workbench"
print(results.total_cases)     # 4
print(results.passed_cases)    # 3
print(results.failed_cases)    # 1
print(results.pass_rate)       # 0.75
print(results.average_score)   # 0.82
print(results.grade)           # "B"

# Export to JSON
results.save("benchmark_results.json")
```

## Integration Points

### How Benchmark Framework Uses Evaluation Harness

The `BenchmarkRunner` creates an `EvaluationSessionManager` and uses it internally:

```python
# runner.py line 192
self._session_manager = EvaluationSessionManager()

# setup_benchmark() creates session with expectations
session = self._session_manager.start_session(
    name=case.name,
    task_definition=case.task_prompt,
    expected_outcome=f"Complete task using: {', '.join(case.required_tools)}",
)

# Set trajectory expectations from benchmark case
self._session_manager.set_expected_trajectory(
    required_tools=case.required_tools,
    forbidden_tools=case.forbidden_tools,
    expected_order=case.optimal_trajectory,
)

# complete_benchmark() uses evaluation scoring
score = calculate_score_from_session(session)
```

### Data Flow

```
1. Define benchmark case with task, required tools, optimal trajectory
2. BenchmarkRunner.setup_benchmark() creates evaluation session
3. Agent executes task using domain tools
4. Tool calls recorded via record_tool_call() or pluggy hooks
5. calculate_score_from_session() computes 6-dimension metrics
6. BenchmarkResult contains score (0.0-1.0), grade (A-F), session data
```

## Use Cases

| Use Case | Recommended System |
|----------|-------------------|
| CI/CD regression tests | Benchmark Framework |
| Manual agent testing with live observation | Evaluation Harness (via MCP tools) |
| Production monitoring | Evaluation Harness with hooks |
| Defining expected agent behavior | Golden paths in benchmark suites |
| Comparing agent implementations | Run same benchmark suite against different agents |

## Example: Adding a New Benchmark

```python
# In golden_paths.py or your own module

from rhoai_mcp.benchmarks import BenchmarkCase, BenchmarkSuite

# Define individual cases
MY_CASE_1 = BenchmarkCase(
    name="my_operation",
    task_prompt="Perform my specific operation...",
    required_tools=["tool_a", "tool_b"],
    forbidden_tools=["dangerous_tool"],
    optimal_trajectory=["tool_a", "tool_b", "tool_c"],
    max_steps=5,
    tags=["quick", "my-domain"],
)

MY_CASE_2 = BenchmarkCase(
    name="my_complex_operation",
    task_prompt="Perform complex multi-step operation...",
    required_tools=["tool_a", "tool_b", "tool_c", "tool_d"],
    optimal_trajectory=["tool_a", "tool_b", "tool_c", "tool_d"],
    acceptable_trajectories=[
        ["tool_a", "tool_c", "tool_b", "tool_d"],  # Alternative valid order
    ],
    max_steps=8,
    tags=["complex", "my-domain"],
)

# Group into suite
MY_SUITE = BenchmarkSuite(
    name="my-domain",
    description="Benchmarks for my domain operations",
    cases=[MY_CASE_1, MY_CASE_2],
    tags=["my-domain"],
)
```

## Example: Custom Evaluation Weights

```python
from rhoai_mcp.evaluation import calculate_score_from_session

# Prioritize trajectory and tool selection for agentic workflows
agentic_weights = {
    "trajectory": 0.35,       # Most important for agents
    "tool_selection": 0.25,   # Using right tools matters
    "success_rate": 0.15,
    "stability": 0.10,
    "parameter_precision": 0.10,
    "performance": 0.05,      # Less important for correctness
}

score = calculate_score_from_session(session, weights=agentic_weights)
```

## Example: CI Integration

```python
#!/usr/bin/env python
"""CI benchmark runner script."""

import sys
from rhoai_mcp.benchmarks import BenchmarkRunner
from rhoai_mcp.benchmarks.golden_paths import get_all_suites, get_quick_cases

def my_agent_executor(prompt: str) -> list[dict]:
    """Your agent implementation."""
    # ... agent logic ...
    return tool_calls

def main():
    runner = BenchmarkRunner(pass_threshold=0.70)

    # Run quick cases for fast CI feedback
    all_results = runner.run_all_suites(
        get_all_suites(),
        my_agent_executor,
        quick_only=True
    )

    # Check results
    failed_suites = []
    for suite_name, results in all_results.items():
        print(f"{suite_name}: {results.passed_cases}/{results.total_cases} ({results.grade})")
        if results.pass_rate < 0.70:
            failed_suites.append(suite_name)

    if failed_suites:
        print(f"FAILED: {', '.join(failed_suites)}")
        sys.exit(1)

    print("All benchmarks passed!")
    sys.exit(0)

if __name__ == "__main__":
    main()
```

## Summary

- **Evaluation Harness**: Runtime instrumentation via pluggy hooks for live monitoring and analysis
- **Benchmark Framework**: Repeatable test cases with golden paths for regression testing
- **Complementary Systems**: Benchmark framework consumes evaluation harness for scoring
- **Six Dimensions**: Trajectory, tool selection, success rate, stability, parameter precision, performance
- **Letter Grades**: A-F based on 0.0-1.0 composite scores
- **Extensible**: Add custom benchmark cases, suites, and scoring weights
