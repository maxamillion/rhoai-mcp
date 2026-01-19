# RHOAI MCP Server

An MCP (Model Context Protocol) server that enables AI agents to interact with Red Hat OpenShift AI (RHOAI) environments. This server replicates the capabilities of the OpenShift AI Dashboard through programmatic tools.

## Features

- **Project Management**: Create, list, and manage Data Science Projects
- **Workbench Operations**: Create, start, stop, and delete Jupyter workbenches
- **Model Serving**: Deploy and manage InferenceServices with KServe
- **Data Connections**: Manage S3 credentials for data access
- **Pipelines**: Configure Data Science Pipelines infrastructure
- **Storage**: Create and manage persistent volume claims

## Installation

### Using uv (recommended)

```bash
# Clone the repository
git clone https://github.com/admiller/rhoai-mcp-prototype.git
cd rhoai-mcp-prototype

# Install dependencies
uv sync

# Run the server
uv run rhoai-mcp
```

### Using pip

```bash
pip install -e .
rhoai-mcp
```

### Using Container (Docker/Podman)

```bash
# Build the image
make build

# Run with HTTP transport
make run-http

# Run with STDIO transport (interactive)
make run-stdio

# Run with debug logging
make run-dev
```

Or run directly without Make:

```bash
# Build
podman build -t rhoai-mcp:latest .

# Run with HTTP transport
podman run -p 8000:8000 \
  -v ~/.kube/config:/app/kubeconfig/config:ro \
  -e RHOAI_MCP_AUTH_MODE=kubeconfig \
  -e RHOAI_MCP_KUBECONFIG_PATH=/app/kubeconfig/config \
  rhoai-mcp:latest --transport sse

# Run with STDIO transport
podman run -it \
  -v ~/.kube/config:/app/kubeconfig/config:ro \
  -e RHOAI_MCP_AUTH_MODE=kubeconfig \
  -e RHOAI_MCP_KUBECONFIG_PATH=/app/kubeconfig/config \
  rhoai-mcp:latest --transport stdio
```

Available Make targets:

| Target | Description |
|--------|-------------|
| `make build` | Build the container image |
| `make run-http` | Run with SSE transport on port 8000 |
| `make run-streamable` | Run with streamable-http transport |
| `make run-stdio` | Run with STDIO transport (interactive) |
| `make run-dev` | Run with debug logging |
| `make run-token` | Run with token auth (requires TOKEN and API_SERVER) |
| `make stop` | Stop the running container |
| `make logs` | View container logs |
| `make clean` | Remove container and image |

### Kubernetes Deployment

For in-cluster deployment, apply the Kubernetes manifests:

```bash
kubectl apply -f deploy/kubernetes/deployment.yaml
```

This creates:
- Namespace `rhoai-mcp`
- ServiceAccount with RBAC for RHOAI resources
- Deployment running the MCP server with SSE transport
- Service exposing port 8000
- Route (OpenShift only) with TLS termination

## Configuration

The server can be configured via environment variables (with `RHOAI_MCP_` prefix) or a `.env` file.

### Authentication

The server supports three authentication modes:

1. **Auto (default)**: Tries in-cluster authentication first, falls back to kubeconfig
2. **Kubeconfig**: Uses a kubeconfig file
3. **Token**: Uses explicit API server URL and token

```bash
# Auto mode (default)
export RHOAI_MCP_AUTH_MODE=auto

# Kubeconfig mode
export RHOAI_MCP_AUTH_MODE=kubeconfig
export RHOAI_MCP_KUBECONFIG_PATH=/path/to/kubeconfig
export RHOAI_MCP_KUBECONFIG_CONTEXT=my-context

# Token mode
export RHOAI_MCP_AUTH_MODE=token
export RHOAI_MCP_API_SERVER=https://api.cluster.example.com:6443
export RHOAI_MCP_API_TOKEN=sha256~xxxxx
```

### Transport

```bash
# stdio (default) - for Claude Desktop and similar tools
export RHOAI_MCP_TRANSPORT=stdio

# HTTP transports
export RHOAI_MCP_TRANSPORT=sse
export RHOAI_MCP_HOST=127.0.0.1
export RHOAI_MCP_PORT=8000
```

### Safety Settings

```bash
# Enable delete operations (disabled by default)
export RHOAI_MCP_ENABLE_DANGEROUS_OPERATIONS=true

# Read-only mode (disable all write operations)
export RHOAI_MCP_READ_ONLY_MODE=true
```

## Usage with Claude Desktop

Add to your Claude Desktop configuration (`~/.config/claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "rhoai": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/rhoai-mcp-prototype", "rhoai-mcp"],
      "env": {
        "RHOAI_MCP_KUBECONFIG_PATH": "/home/user/.kube/config"
      }
    }
  }
}
```

Or with an installed package:

```json
{
  "mcpServers": {
    "rhoai": {
      "command": "rhoai-mcp",
      "env": {
        "RHOAI_MCP_KUBECONFIG_PATH": "/home/user/.kube/config"
      }
    }
  }
}
```

## Available Tools

### Project Management (6 tools)

| Tool | Description |
|------|-------------|
| `list_data_science_projects` | List all RHOAI projects |
| `get_project_details` | Get project with resource summary |
| `create_data_science_project` | Create new project |
| `delete_data_science_project` | Delete project (requires confirmation) |
| `get_project_status` | Get comprehensive project status |
| `set_model_serving_mode` | Set single vs multi-model serving |

### Workbench Management (8 tools)

| Tool | Description |
|------|-------------|
| `list_workbenches` | List workbenches in project |
| `get_workbench` | Get workbench details |
| `create_workbench` | Create new workbench |
| `start_workbench` | Start a stopped workbench |
| `stop_workbench` | Stop a running workbench |
| `delete_workbench` | Delete workbench |
| `list_notebook_images` | List available images |
| `get_workbench_url` | Get OAuth-protected URL |

### Model Serving (6 tools)

| Tool | Description |
|------|-------------|
| `list_inference_services` | List deployed models |
| `get_inference_service` | Get model details |
| `deploy_model` | Create InferenceService |
| `delete_inference_service` | Delete deployed model |
| `list_serving_runtimes` | List available runtimes |
| `get_model_endpoint` | Get inference endpoint URL |

### Data Connections (4 tools)

| Tool | Description |
|------|-------------|
| `list_data_connections` | List connections in project |
| `get_data_connection` | Get connection details (masked) |
| `create_s3_data_connection` | Create S3 connection |
| `delete_data_connection` | Delete connection |

### Pipelines (3 tools)

| Tool | Description |
|------|-------------|
| `get_pipeline_server` | Get DSPA status |
| `create_pipeline_server` | Create DSPA |
| `delete_pipeline_server` | Delete DSPA |

### Storage (3 tools)

| Tool | Description |
|------|-------------|
| `list_storage` | List PVCs in project |
| `create_storage` | Create PVC |
| `delete_storage` | Delete PVC (requires confirmation) |

## MCP Resources

The server also exposes read-only resources:

| Resource URI | Description |
|--------------|-------------|
| `rhoai://cluster/status` | Cluster health and RHOAI status |
| `rhoai://cluster/components` | DataScienceCluster component status |
| `rhoai://cluster/accelerators` | Available GPU profiles |
| `rhoai://projects/{name}/status` | Project resource summary |
| `rhoai://projects/{name}/workbenches` | Workbench list with status |
| `rhoai://projects/{name}/models` | Deployed models with status |

## Example Interactions

### Create a Data Science Project

```
User: Create a new data science project called "fraud-detection" for my ML experiments
Agent: I'll create that project for you with a descriptive display name.
[Calls create_data_science_project with name="fraud-detection", 
 display_name="Fraud Detection ML", description="Machine learning experiments for fraud detection"]

Result: Project 'fraud-detection' created successfully
```

### Deploy a Model

```
User: Deploy my trained fraud model from S3 to the fraud-detection project

Agent: I'll deploy your model. First, let me check available serving runtimes.
[Calls list_serving_runtimes with namespace="fraud-detection"]
[Calls deploy_model with name="fraud-model", namespace="fraud-detection",
 runtime="ovms", model_format="onnx", 
 storage_uri="s3://models/fraud-detection/model.onnx"]

Result: Model 'fraud-model' deployment initiated. It may take a few minutes to become ready.
```

### Check Project Status

```
User: What's the status of my fraud-detection project?

Agent: [Calls get_project_status with namespace="fraud-detection"]

Result:
- Project: fraud-detection (Fraud Detection ML)
- Workbenches: 2 total, 1 running
- Models: 1 deployed, 1 ready
- Pipeline Server: Ready
- Data Connections: 1
- Storage: 3 PVCs
```

## Development

### Running Tests

```bash
# Install dev dependencies
uv sync --extra dev

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=rhoai_mcp
```

### Code Quality

```bash
# Format code
uv run ruff format

# Lint
uv run ruff check

# Type check
uv run mypy src/rhoai_mcp
```

## Architecture

The server is organized into:

- **clients/**: Kubernetes client abstractions for each resource type
- **models/**: Pydantic models for type-safe resource handling
- **tools/**: MCP tool definitions that wrap client operations
- **resources/**: MCP resource definitions for read-only data access
- **utils/**: Helper functions for annotations, labels, and errors

### Key CRDs Supported

| Resource | API Group | Purpose |
|----------|-----------|---------|
| Namespace | core/v1 | Data Science Projects |
| Notebook | kubeflow.org/v1 | Workbenches |
| InferenceService | serving.kserve.io/v1beta1 | Model serving |
| ServingRuntime | serving.kserve.io/v1alpha1 | Model server configs |
| DataSciencePipelinesApplication | datasciencepipelinesapplications.opendatahub.io/v1alpha1 | Pipeline infrastructure |
| AcceleratorProfile | dashboard.opendatahub.io/v1 | GPU profiles |

## License

MIT License - see [LICENSE](LICENSE) for details.
