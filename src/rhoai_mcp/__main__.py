"""Entry point for RHOAI MCP server."""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from rhoai_mcp import __version__
from rhoai_mcp.config import (
    AuthMode,
    LogLevel,
    RHOAIConfig,
    TransportMode,
)


def setup_logging(level: LogLevel) -> None:
    """Configure logging for the server."""
    logging.basicConfig(
        level=level.value,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="rhoai-mcp",
        description="MCP server for Red Hat OpenShift AI",
    )

    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Benchmark subcommand
    benchmark_parser = subparsers.add_parser(
        "benchmark",
        help="Run agent performance benchmarks",
    )
    benchmark_parser.add_argument(
        "--suite",
        choices=["all", "workbench", "project", "serving", "training", "e2e"],
        default="all",
        help="Benchmark suite to run (default: all)",
    )
    benchmark_parser.add_argument(
        "--quick",
        action="store_true",
        help="Only run quick benchmarks (tagged 'quick')",
    )
    benchmark_parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file for results (JSON format)",
    )
    benchmark_parser.add_argument(
        "--threshold",
        type=float,
        default=0.70,
        help="Minimum score to pass (default: 0.70)",
    )
    benchmark_parser.add_argument(
        "--list",
        action="store_true",
        dest="list_cases",
        help="List available benchmark cases without running",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    # Transport options
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default=None,
        help="Transport mode (default: from config or stdio)",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Host to bind HTTP server to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to bind HTTP server to (default: 8000)",
    )

    # Auth options
    parser.add_argument(
        "--auth-mode",
        choices=["auto", "kubeconfig", "token"],
        default=None,
        help="Authentication mode (default: auto)",
    )
    parser.add_argument(
        "--kubeconfig",
        default=None,
        help="Path to kubeconfig file",
    )
    parser.add_argument(
        "--context",
        default=None,
        help="Kubeconfig context to use",
    )

    # Safety options
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="Run in read-only mode (disable all write operations)",
    )
    parser.add_argument(
        "--enable-dangerous",
        action="store_true",
        help="Enable dangerous operations like delete",
    )

    # Logging
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=None,
        help="Logging level (default: INFO)",
    )

    return parser.parse_args()


def run_benchmark(args: argparse.Namespace) -> int:
    """Run benchmark command."""
    from rhoai_mcp.benchmarks import (
        BenchmarkRunner,
        get_all_cases,
        get_all_suites,
        get_quick_cases,
        get_suite,
    )

    setup_logging(LogLevel.INFO)
    logger = logging.getLogger(__name__)

    # List mode - just show available benchmarks
    if args.list_cases:
        cases = get_quick_cases() if args.quick else get_all_cases()
        print(f"\nAvailable benchmark cases ({len(cases)} total):\n")
        for case in cases:
            tags = ", ".join(case.tags) if case.tags else "none"
            print(f"  - {case.name}")
            print(f"    Tags: {tags}")
            print(f"    Task: {case.task_prompt[:60]}...")
            print()
        return 0

    # Get suites to run
    if args.suite == "all":
        suites = get_all_suites()
    else:
        suite = get_suite(args.suite)
        if not suite:
            logger.error(f"Unknown suite: {args.suite}")
            return 1
        suites = [suite]

    logger.info(f"Running benchmarks: {', '.join(s.name for s in suites)}")
    if args.quick:
        logger.info("Quick mode: only running cases tagged 'quick'")

    # Create runner
    runner = BenchmarkRunner(pass_threshold=args.threshold)

    # Note: Without an actual agent executor, we just demonstrate the framework.
    # In a real scenario, you would integrate with an agent that executes tasks.
    def mock_executor(_prompt: str) -> list[dict[str, Any]]:
        """Mock executor for demonstration - returns empty tool calls."""
        logger.warning(
            "Using mock executor. In production, integrate with an actual agent."
        )
        return []

    # Run benchmarks
    all_results = runner.run_all_suites(suites, mock_executor, quick_only=args.quick)

    # Print summary
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)

    total_passed = 0
    total_failed = 0

    for suite_name, results in all_results.items():
        print(f"\n{suite_name.upper()} Suite:")
        print(f"  Passed: {results.passed_cases}/{results.total_cases}")
        print(f"  Pass Rate: {results.pass_rate:.1%}")
        print(f"  Average Score: {results.average_score:.2f}")
        print(f"  Grade: {results.grade}")

        total_passed += results.passed_cases
        total_failed += results.failed_cases

    print("\n" + "-" * 60)
    total = total_passed + total_failed
    overall_rate = total_passed / total if total > 0 else 0
    print(f"TOTAL: {total_passed}/{total} passed ({overall_rate:.1%})")
    print("=" * 60)

    # Save results if output specified
    if args.output:
        output_path = Path(args.output)
        combined_results = {
            name: results.to_dict() for name, results in all_results.items()
        }
        output_path.write_text(json.dumps(combined_results, indent=2))
        logger.info(f"Results saved to: {output_path}")

    # Return non-zero if any failures and below threshold
    if overall_rate < args.threshold:
        logger.error(f"Pass rate {overall_rate:.1%} is below threshold {args.threshold:.1%}")
        return 1

    return 0


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Handle benchmark subcommand
    if args.command == "benchmark":
        return run_benchmark(args)

    # Build config from args, falling back to environment/defaults
    config_kwargs: dict[str, Any] = {}

    if args.transport:
        transport_map = {
            "stdio": TransportMode.STDIO,
            "sse": TransportMode.SSE,
            "streamable-http": TransportMode.STREAMABLE_HTTP,
        }
        config_kwargs["transport"] = transport_map[args.transport]

    if args.host:
        config_kwargs["host"] = args.host

    if args.port:
        config_kwargs["port"] = args.port

    if args.auth_mode:
        auth_map = {
            "auto": AuthMode.AUTO,
            "kubeconfig": AuthMode.KUBECONFIG,
            "token": AuthMode.TOKEN,
        }
        config_kwargs["auth_mode"] = auth_map[args.auth_mode]

    if args.kubeconfig:
        config_kwargs["kubeconfig_path"] = args.kubeconfig

    if args.context:
        config_kwargs["kubeconfig_context"] = args.context

    if args.read_only:
        config_kwargs["read_only_mode"] = True

    if args.enable_dangerous:
        config_kwargs["enable_dangerous_operations"] = True

    if args.log_level:
        config_kwargs["log_level"] = LogLevel(args.log_level)

    # Create config
    config = RHOAIConfig(**config_kwargs)

    # Setup logging
    setup_logging(config.log_level)

    logger = logging.getLogger(__name__)
    logger.info(f"Starting RHOAI MCP server v{__version__}")

    # Validate auth config
    try:
        warnings = config.validate_auth_config()
        for warning in warnings:
            logger.warning(warning)
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    # Create and run server
    from rhoai_mcp.server import create_server

    mcp = create_server(config)

    # Run with appropriate transport
    # Note: Host/port are set via RHOAI_MCP_HOST/PORT env vars which FastMCP reads
    import os

    os.environ.setdefault("UVICORN_HOST", config.host)
    os.environ.setdefault("UVICORN_PORT", str(config.port))

    if config.transport == TransportMode.STDIO:
        logger.info("Running with stdio transport")
        mcp.run(transport="stdio")
    elif config.transport == TransportMode.SSE:
        logger.info(f"Running with SSE transport on {config.host}:{config.port}")
        mcp.run(transport="sse")
    elif config.transport == TransportMode.STREAMABLE_HTTP:
        logger.info(f"Running with streamable-http transport on {config.host}:{config.port}")
        mcp.run(transport="streamable-http")

    return 0


if __name__ == "__main__":
    sys.exit(main())
