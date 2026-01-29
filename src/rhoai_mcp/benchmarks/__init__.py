"""Benchmark framework for measuring agent response quality.

This package provides repeatable benchmarks for evaluating agent
performance when using RHOAI MCP tools.
"""

from rhoai_mcp.benchmarks.golden_paths import (
    ALL_SUITES,
    get_all_cases,
    get_all_suites,
    get_quick_cases,
    get_suite,
)
from rhoai_mcp.benchmarks.runner import (
    BenchmarkResult,
    BenchmarkRunner,
    BenchmarkRunResults,
)
from rhoai_mcp.benchmarks.suite import (
    BenchmarkCase,
    BenchmarkSuite,
)

__all__ = [
    # Suite definitions
    "BenchmarkCase",
    "BenchmarkSuite",
    # Runner
    "BenchmarkRunner",
    "BenchmarkResult",
    "BenchmarkRunResults",
    # Golden paths
    "ALL_SUITES",
    "get_suite",
    "get_all_suites",
    "get_all_cases",
    "get_quick_cases",
]
