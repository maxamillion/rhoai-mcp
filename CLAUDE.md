# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RHOAI MCP Server is a hybrid Claude Code Plugin and MCP (Model Context Protocol) server that enables AI agents to interact with Red Hat OpenShift AI (RHOAI) environments. It provides:

- **Agent Skills** (`skills/`) -- markdown-based workflow guidance for training, deployment, exploration, and troubleshooting that Claude discovers contextually
- **MCP Tools** -- Kubernetes CRUD operations, monitoring, and value-add summaries exposed via MCP
- **Fallback Tool** (`get_workflow_guide`) -- serves skill content to MCP-only clients without skill support

## Build and Development Commands

```bash
# Setup development environment
uv sync                          # Install package
make dev                         # Alias for setup

# Run the server locally
uv run rhoai-mcp                 # Default (stdio transport)
uv run rhoai-mcp --transport sse # HTTP transport

# Testing
make test                        # All tests
make test-unit                   # Unit tests only (tests/training)
make test-integration            # Integration tests (tests/integration)
make test-skills                 # Skill format validation tests

# Code quality
make lint                        # ruff check
make format                      # ruff format + fix
make typecheck                   # mypy
make check                       # lint + typecheck

# Container operations
make build                       # Build container image
make run-http                    # Run with SSE transport
make run-stdio                   # Run with stdio transport
make run-dev                     # Debug logging + dangerous ops enabled
```

## Architecture

### Project Structure

```
rhoai-mcp/
├── .claude-plugin/
│   └── plugin.json              # Claude Code Plugin manifest
├── .mcp.json                    # MCP server config for plugin mode
├── skills/                      # Agent Skills (21 workflow guides)
│   ├── train-model/             # Fine-tune a model with LoRA/QLoRA
│   ├── deploy-model/            # Deploy model for inference
│   ├── explore-cluster/         # Discover cluster resources
│   ├── troubleshoot-training/   # Diagnose training issues
│   ├── ...                      # 17 more skills
│   └── diagnose-resource/       # Comprehensive resource diagnostics
├── src/
│   └── rhoai_mcp/               # Main package
│       ├── __init__.py
│       ├── __main__.py          # CLI entry point
│       ├── config.py            # Configuration (pydantic-settings)
│       ├── server.py            # FastMCP server
│       ├── hooks.py             # Pluggy hook specifications
│       ├── plugin.py            # Plugin protocol and base class
│       ├── plugin_manager.py    # Plugin lifecycle management
│       ├── clients/             # K8s client abstractions
│       ├── models/              # Shared Pydantic models
│       ├── utils/               # Helper functions + skill_loader
│       ├── domains/             # Domain modules (pure CRUD operations)
│       │   ├── projects/        # Data Science Project management
│       │   ├── notebooks/       # Kubeflow Notebook/Workbench
│       │   ├── inference/       # KServe InferenceService
│       │   ├── pipelines/       # Data Science Pipelines (DSPA)
│       │   ├── connections/     # S3 data connections
│       │   ├── storage/         # PersistentVolumeClaim
│       │   ├── training/        # Kubeflow Training Operator
│       │   ├── evaluation/      # Model evaluation jobs
│       │   └── registry.py      # Domain plugin registry (8 plugins)
│       └── composites/          # Cross-cutting composite tools
│           ├── cluster/         # Cluster summaries and status
│           ├── training/        # Training validators and storage
│           ├── fallback/        # get_workflow_guide for MCP-only clients
│           └── registry.py      # Composite plugin registry (3 plugins)
├── tests/                       # Test suite
├── docs/                        # Documentation
├── pyproject.toml               # Project configuration
└── Containerfile                # Container build
```

**Architecture**: Domain modules provide CRUD operations for Kubernetes resources. Composite modules provide value-add summaries and validators. Agent Skills provide multi-step workflow guidance as markdown instructions. The `get_workflow_guide` fallback tool serves skill content to MCP-only clients.

### Domain Module Structure

Each domain module in `src/rhoai_mcp/domains/` follows this layout:
```
domains/<name>/
├── __init__.py
├── client.py            # K8s resource client
├── models.py            # Pydantic models
├── tools.py             # MCP tool implementations
├── crds.py              # CRD definitions (if applicable)
└── resources.py         # MCP resources (if applicable)
```

The domain registry (`domains/registry.py`) defines all domains and provides them to the server for registration.

### Plugin Hooks

Plugins can implement these hooks (defined in `hooks.py`):
- `rhoai_register_tools`: Register MCP tools
- `rhoai_register_resources`: Register MCP resources
- `rhoai_get_crd_definitions`: Return CRD definitions
- `rhoai_health_check`: Check plugin health

### Claude Code Plugin

This repo also works as a Claude Code Plugin via `.claude-plugin/plugin.json`. In plugin mode:
- **Skills** in `skills/` are auto-discovered by description matching (user-invocable skills available via `/rhoai:` prefix)
- **MCP tools** are started via the `.mcp.json` config
- The `get_workflow_guide` MCP tool provides a fallback for MCP-only clients to access skill content

#### Available Skills (21 total)
- **Training**: `train-model`, `monitor-training`, `resume-training`
- **Deployment**: `deploy-model`, `deploy-llm`, `test-endpoint`, `scale-model`
- **Exploration**: `explore-cluster`, `explore-project`, `find-gpus`, `whats-running`
- **Troubleshooting**: `troubleshoot-training`, `troubleshoot-workbench`, `troubleshoot-model`, `analyze-oom`
- **Project Setup**: `setup-training-project`, `setup-inference-project`, `add-data-connection`
- **Auto-discovered** (not user-invocable): `prepare-training`, `prepare-deployment`, `diagnose-resource`

### Configuration

Environment variables use `RHOAI_MCP_` prefix. Key settings:
- `AUTH_MODE`: auto | kubeconfig
- `TRANSPORT`: stdio | sse | streamable-http
- `KUBECONFIG_PATH`, `KUBECONFIG_CONTEXT`: For kubeconfig auth
- `ENABLE_DANGEROUS_OPERATIONS`: Enable delete operations
- `READ_ONLY_MODE`: Disable all writes

### Key Dependencies

- `mcp>=1.0.0`: Model Context Protocol (FastMCP)
- `kubernetes>=28.1.0`: K8s Python client
- `pydantic>=2.0.0`: Data validation and settings

## Development Principles

### Test-Driven Development

Follow TDD for all code changes:

1. **Write tests first**: Before implementing any feature or fix, write failing tests that define the expected behavior
2. **Red-Green-Refactor**: Run tests to see them fail (red), write minimal code to pass (green), then refactor while keeping tests green
3. **Test coverage**: All new code must have corresponding tests; run `make test` before committing
4. **Test types**: Unit tests go in `tests/`, integration tests in `tests/integration/`

### Simplicity and Maintainability

Favor simple, maintainable solutions at all times:

- **KISS**: Choose the simplest solution that works; avoid premature optimization or over-abstraction
- **Single responsibility**: Each function, class, and module should do one thing well
- **Explicit over implicit**: Code should be self-documenting; avoid magic or clever tricks
- **Minimal dependencies**: Only add dependencies when truly necessary
- **Delete dead code**: Remove unused code rather than commenting it out
- **Small functions**: Keep functions short and focused; if a function needs extensive comments, it should be split

### Idiomatic Python

Write Pythonic code that follows community conventions:

- Use list/dict/set comprehensions where they improve readability
- Prefer `pathlib.Path` over `os.path` for file operations
- Use context managers (`with` statements) for resource management
- Leverage dataclasses and Pydantic models for structured data
- Use type hints consistently (required by mypy)
- Follow PEP 8 naming: `snake_case` for functions/variables, `PascalCase` for classes
- Use `typing` module for complex types; prefer `|` union syntax (Python 3.10+)
- Prefer raising specific exceptions over generic ones
- Use f-strings for string formatting

## Code Style

- Python 3.10+, line length 100
- Ruff for linting/formatting (isort included)
- Mypy with `disallow_untyped_defs=true`
- Pytest with `asyncio_mode = "auto"`
