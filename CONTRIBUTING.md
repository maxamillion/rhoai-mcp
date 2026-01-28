# Contributing to RHOAI MCP Server

This document describes the architecture and contribution guidelines for the RHOAI MCP Server.

## Repository Structure

```
rhoai-mcp/
├── src/
│   └── rhoai_mcp/            # Main package
│       ├── __init__.py
│       ├── __main__.py       # CLI entry point
│       ├── config.py         # Configuration
│       ├── server.py         # FastMCP server
│       ├── plugin.py         # Plugin protocol
│       ├── clients/          # K8s client abstractions
│       ├── models/           # Shared Pydantic models
│       ├── utils/            # Helper functions
│       └── domains/          # Domain modules
│           ├── projects/     # Data Science Project management
│           ├── notebooks/    # Kubeflow Notebook/Workbench
│           ├── inference/    # KServe InferenceService
│           ├── pipelines/    # Data Science Pipelines
│           ├── connections/  # S3 data connections
│           ├── storage/      # PersistentVolumeClaim
│           └── training/     # Kubeflow Training Operator
├── tests/                    # Test suite
│   ├── conftest.py
│   ├── training/             # Training domain tests
│   └── integration/          # Cross-component tests
├── pyproject.toml            # Project configuration
└── uv.lock                   # Lockfile
```

## Development Setup

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) - Fast Python package manager
- Access to a Kubernetes/OpenShift cluster (for integration testing)

### Getting Started

```bash
# Clone the repository
git clone https://github.com/admiller/rhoai-mcp-prototype.git
cd rhoai-mcp-prototype

# Install in development mode
make dev

# Or using uv directly
uv sync
```

### Running Tests

```bash
# Run all tests
make test

# Run unit tests only
make test-unit

# Run integration tests
make test-integration
```

### Code Quality

```bash
# Run linter
make lint

# Format code
make format

# Run type checker
make typecheck

# Run all checks
make check
```

### Running the Server Locally

```bash
# Run with SSE transport
make run-local

# Run with stdio transport
make run-local-stdio

# Run with debug logging
make run-local-debug
```

## Domain Module Architecture

### Domain Module Structure

Each domain module in `src/rhoai_mcp/domains/` follows this layout:

```
domains/<name>/
├── __init__.py          # Exports public API
├── client.py            # K8s resource client
├── models.py            # Pydantic models
├── tools.py             # MCP tool implementations
├── crds.py              # CRD definitions (if applicable)
└── resources.py         # MCP resources (optional)
```

### Adding a New Domain

1. Create a new directory under `src/rhoai_mcp/domains/`:
   ```
   domains/my-domain/
   ├── __init__.py
   ├── client.py
   ├── models.py
   └── tools.py
   ```

2. Implement the domain client:
   ```python
   from rhoai_mcp.clients.base import BaseClient

   class MyDomainClient(BaseClient):
       def list_resources(self, namespace: str) -> list[MyResource]:
           # Implement K8s API calls
           pass
   ```

3. Register the domain in `domains/registry.py`:
   ```python
   from rhoai_mcp.domains.my_domain import register_tools

   DOMAIN_REGISTRY = [
       # ... existing domains
       DomainInfo(
           name="my-domain",
           description="My domain description",
           register_tools=register_tools,
       ),
   ]
   ```

4. Add tests in `tests/my_domain/`

## Container Build

```bash
# Build container image
make build

# Test the build
make test-build

# Run container with HTTP transport
make run-http

# Run container with stdio transport
make run-stdio
```

## Pull Request Guidelines

1. Ensure all tests pass: `make test`
2. Ensure code is formatted: `make format`
3. Ensure no lint errors: `make lint`
4. Update relevant documentation
5. Add tests for new functionality
6. Keep changes focused

## Questions?

For questions, reach out to rhoai-mcp@redhat.com.
