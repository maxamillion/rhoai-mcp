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
    benchmark_parser.add_argument(
        "--mode",
        choices=["simulate", "agent"],
        default="simulate",
        help="Benchmark mode: simulate (default) or agent",
    )
    benchmark_parser.add_argument(
        "--scenario-dir",
        type=str,
        default=None,
        help="Directory containing custom JSON scenario files (simulation mode)",
    )
    benchmark_parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Claude model to use (agent mode, default: claude-sonnet-4-20250514)",
    )
    benchmark_parser.add_argument(
        "--server-url",
        type=str,
        default=None,
        help="MCP server URL (agent mode, default: http://127.0.0.1:8000)",
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


def run_benchmark_simulate(args: argparse.Namespace) -> int:
    """Run benchmarks in simulation mode."""
    from rhoai_mcp.benchmarks.simulation import (
        print_simulation_summary,
        run_simulation_benchmarks,
    )

    setup_logging(LogLevel.INFO)
    logger = logging.getLogger(__name__)

    logger.info("Running benchmarks in simulation mode")
    if args.quick:
        logger.info("Quick mode: only running scenarios tagged 'quick'")

    scenario_dir = Path(args.scenario_dir) if args.scenario_dir else None

    results = run_simulation_benchmarks(
        quick_only=args.quick,
        scenario_dir=scenario_dir,
        pass_threshold=args.threshold,
    )

    print_simulation_summary(results)

    # Save results if output specified
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(json.dumps(results, indent=2))
        logger.info(f"Results saved to: {output_path}")

    # Return non-zero if validation rate is below threshold
    if results["validation_rate"] < args.threshold:
        logger.error(
            f"Validation rate {results['validation_rate']:.1%} "
            f"is below threshold {args.threshold:.1%}"
        )
        return 1

    return 0


def run_benchmark_agent(args: argparse.Namespace) -> int:
    """Run benchmarks in agent mode using Claude via Anthropic API."""
    from rhoai_mcp.benchmarks.agent import (
        check_agent_prerequisites,
        run_agent_benchmarks,
    )
    from rhoai_mcp.config import get_config

    setup_logging(LogLevel.INFO)
    logger = logging.getLogger(__name__)

    config = get_config()

    # Override config with CLI args
    if args.model:
        config = type(config).model_validate(
            {**config.model_dump(), "anthropic_model": args.model}
        )
    if args.server_url:
        config = type(config).model_validate(
            {**config.model_dump(), "benchmark_server_url": args.server_url}
        )

    # Check prerequisites
    ok, error = check_agent_prerequisites(config)
    if not ok:
        logger.error(f"Agent mode prerequisites not met: {error}")
        return 1

    logger.info("Running benchmarks in agent mode")
    logger.info(f"Model: {config.anthropic_model}")
    logger.info(f"Server URL: {config.benchmark_server_url}")
    if args.quick:
        logger.info("Quick mode: only running cases tagged 'quick'")

    results = run_agent_benchmarks(
        config=config,
        quick_only=args.quick,
        pass_threshold=args.threshold,
    )

    # Print summary
    print("\n" + "=" * 60)
    print("AGENT BENCHMARK RESULTS")
    print("=" * 60)

    total = results["total_cases"]
    passed = results["passed_cases"]
    rate = results["pass_rate"]

    print(f"\nTotal Cases: {total}")
    print(f"Passed: {passed}/{total} ({rate:.1%})")
    print(f"Average Score: {results['average_score']:.2f}")
    print(f"Grade: {results['grade']}")

    # Show failures
    failures = [r for r in results["results"] if not r["passed"]]
    if failures:
        print(f"\nFailed Cases ({len(failures)}):")
        for f in failures:
            print(f"  - {f['case_name']}: score={f.get('score', 'N/A')}")
            if f.get("error"):
                print(f"    Error: {f['error']}")

    print("=" * 60)

    # Save results if output specified
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(json.dumps(results, indent=2))
        logger.info(f"Results saved to: {output_path}")

    # Return non-zero if pass rate is below threshold
    if rate < args.threshold:
        logger.error(f"Pass rate {rate:.1%} is below threshold {args.threshold:.1%}")
        return 1

    return 0


def run_benchmark(args: argparse.Namespace) -> int:
    """Run benchmark command."""
    from rhoai_mcp.benchmarks import (
        get_all_cases,
        get_quick_cases,
    )

    setup_logging(LogLevel.INFO)

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

    # Dispatch by mode
    mode = getattr(args, "mode", "simulate")
    if mode == "simulate":
        return run_benchmark_simulate(args)
    elif mode == "agent":
        return run_benchmark_agent(args)
    else:
        print(f"Unknown mode: {mode}")
        return 1


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
