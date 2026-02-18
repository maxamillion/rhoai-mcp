# MCP Evaluation Framework

This guide covers the DeepEval-based evaluation framework for testing how well LLM agents use the RHOAI MCP server's tools to accomplish real-world tasks.

## Overview

The evaluation framework measures whether an LLM agent can effectively use the MCP tools provided by the RHOAI server. Instead of checking tool implementations directly (that's what unit tests do), evals answer the question: **"Given a natural-language task, does the agent call the right tools in the right order and produce a useful result?"**

The framework uses:

- **A real LLM agent** (OpenAI-compatible) that receives tasks and calls MCP tools
- **The real RHOAI MCP server** running in-process with all plugins loaded
- **A mock K8s cluster** (or optionally a live cluster) providing realistic data
- **DeepEval metrics** with a judge LLM that scores the agent's tool usage and task completion

This replaces the earlier self-instrumentation approach (`ENABLE_EVALUATION` hooks) with an external, LLM-judged evaluation that better reflects real-world agent behavior.

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager
- An OpenAI-compatible API key (for the agent LLM and the DeepEval judge LLM)
- (Optional) A live OpenShift cluster with RHOAI installed, for live-cluster evals

## Setup

1. Copy the example environment file and fill in your API keys:

   ```bash
   cp .env.eval.example .env.eval
   ```

   At minimum, set `RHOAI_EVAL_LLM_API_KEY` and `RHOAI_EVAL_EVAL_API_KEY`:

   ```bash
   RHOAI_EVAL_LLM_API_KEY=sk-...
   RHOAI_EVAL_EVAL_API_KEY=sk-...
   ```

2. Install the eval dependency group:

   ```bash
   uv sync --group eval
   ```

## Running Evaluations

### Make targets

```bash
# Run all mock-cluster scenarios
make eval

# Run all scenarios including live-cluster tests
make eval-live

# Run a single scenario by name
make eval-scenario SCENARIO=cluster_exploration
make eval-scenario SCENARIO=training_workflow
make eval-scenario SCENARIO=model_deployment
make eval-scenario SCENARIO=troubleshooting
make eval-scenario SCENARIO=tool_discovery
```

### Direct pytest

```bash
# Mock-cluster scenarios only
uv run --group eval pytest evals/ -v -m "eval and not live" --tb=short

# All scenarios
uv run --group eval pytest evals/ -v -m "eval" --tb=short

# Single scenario file
uv run --group eval pytest evals/scenarios/test_cluster_exploration.py -v --tb=short
```

## Configuration Reference

All variables use the `RHOAI_EVAL_` prefix and can be set in `.env.eval` or as environment variables.

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `openai` | Agent LLM provider: `openai`, `vllm`, or `azure` |
| `LLM_MODEL` | `gpt-4o` | Model name for the agent LLM |
| `LLM_API_KEY` | (none) | API key for the agent LLM |
| `LLM_BASE_URL` | (none) | Base URL for vLLM or Azure endpoints |
| `EVAL_MODEL` | `gpt-4o` | Model name for the DeepEval judge LLM |
| `EVAL_API_KEY` | (none) | API key for the judge LLM |
| `EVAL_MODEL_BASE_URL` | (none) | Base URL for a custom judge endpoint |
| `CLUSTER_MODE` | `mock` | `mock` (no cluster needed) or `live` (real cluster) |
| `MCP_USE_THRESHOLD` | `0.5` | Minimum score for MCP tool usage metrics (0.0-1.0) |
| `TASK_COMPLETION_THRESHOLD` | `0.6` | Minimum score for task completion metrics (0.0-1.0) |
| `MAX_AGENT_TURNS` | `20` | Maximum LLM turns per scenario (1-100) |

## Architecture

```text
evals/
├── config.py                         # EvalConfig (pydantic-settings)
├── conftest.py                       # Shared pytest fixtures
├── mcp_harness.py                    # In-process MCP server lifecycle
├── agent.py                          # LLM agent loop
├── deepeval_helpers.py               # AgentResult -> DeepEval test case conversion
├── mock_k8s/
│   ├── cluster_state.py              # ClusterState dataclass + default data
│   └── mock_client.py                # MockK8sClient (subclasses K8sClient)
├── metrics/
│   ├── config.py                     # Metric factory functions
│   └── custom_llm.py                 # CustomEvalLLM for non-OpenAI judges
└── scenarios/
    ├── test_cluster_exploration.py    # Cluster discovery scenario
    ├── test_training_workflow.py      # Training job creation scenario
    ├── test_model_deployment.py       # Model serving scenario
    ├── test_troubleshooting.py        # Failed job diagnosis scenario
    └── test_tool_discovery.py         # Meta tool usage scenario
```

### How the pieces fit together

1. **`EvalConfig`** (`config.py`) loads settings from `RHOAI_EVAL_*` env vars or `.env.eval` using pydantic-settings.

2. **`MCPHarness`** (`mcp_harness.py`) starts the real RHOAI MCP server in-process. In mock mode, it injects a `MockK8sClient` before the server lifespan begins, so all domain logic, plugin loading, and tool registration execute for real — only the K8s API calls are faked. In live mode, it uses the server's normal lifespan with a real cluster connection.

3. **`MCPAgent`** (`agent.py`) implements an agent loop: it sends the task and all MCP tool schemas to an OpenAI-compatible LLM, executes any tool calls the LLM requests via the harness, feeds results back, and repeats until the LLM produces a final text response or hits the turn limit. It records all tool calls and messages in an `AgentResult`.

4. **`deepeval_helpers.py`** converts the `AgentResult` into DeepEval test case objects (`ConversationalTestCase` for multi-turn scenarios, `LLMTestCase` for single-turn), attaching the `MCPServer` tool definitions and `MCPToolCall` records.

5. **Metrics** (`metrics/config.py`) wrap DeepEval's built-in MCP metrics with configured thresholds. A judge LLM scores whether the agent used the right tools appropriately.

6. **Scenarios** (`scenarios/`) are pytest test classes marked with `@pytest.mark.eval`. Each defines a natural-language `TASK`, runs the agent, builds a DeepEval test case, and asserts that all metrics pass.

### Data flow

```text
Scenario TASK ──> MCPAgent.run()
                    │
                    ├──> LLM (OpenAI API) ──> tool_calls
                    │                              │
                    ├──< MCPHarness.call_tool() <──┘
                    │       │
                    │       └──> RHOAI MCP Server ──> MockK8sClient
                    │
                    └──> AgentResult
                            │
                            ├──> deepeval_helpers ──> ConversationalTestCase
                            │                              │
                            └──> DeepEval evaluate() <─────┘
                                    │
                                    └──> Judge LLM scores metrics
```

## Available Scenarios

| Scenario | File | Task | Metrics |
|----------|------|------|---------|
| Cluster Exploration | `test_cluster_exploration.py` | Discover projects, running workbenches, and GPU availability | `MultiTurnMCPUseMetric`, `MCPTaskCompletionMetric` |
| Training Workflow | `test_training_workflow.py` | Fine-tune Llama 3.1-8B with LoRA: check prerequisites, plan resources, create the job | `MultiTurnMCPUseMetric`, `MCPTaskCompletionMetric` |
| Model Deployment | `test_model_deployment.py` | Deploy granite model via vLLM runtime and verify status | `MultiTurnMCPUseMetric`, `MCPTaskCompletionMetric` |
| Troubleshooting | `test_troubleshooting.py` | Diagnose why `failed-training-001` failed (OOMKilled) | `MultiTurnMCPUseMetric`, `MCPTaskCompletionMetric` |
| Tool Discovery | `test_tool_discovery.py` | Discover which tools to use for project setup with storage and workbench | `MCPUseMetric` (single-turn) |

## Mock Cluster State

When `CLUSTER_MODE=mock`, the `create_default_cluster_state()` function in `evals/mock_k8s/cluster_state.py` pre-populates a realistic RHOAI cluster:

| Resource Type | Name | Namespace | Details |
|---------------|------|-----------|---------|
| Namespace/Project | `ml-experiments` | — | "ML Experiments" |
| Namespace/Project | `production-models` | — | "Production Models" |
| DataScienceCluster | `default-dsc` | — | All components ready |
| AcceleratorProfile | `nvidia-a100` | — | NVIDIA A100 80GB GPU |
| Notebook (Workbench) | `my-workbench` | `ml-experiments` | Running, Minimal Python image |
| TrainJob (completed) | `llama-finetune-001` | `ml-experiments` | Llama 3.1-8B fine-tune, completed |
| TrainJob (failed) | `failed-training-001` | `ml-experiments` | OOMKilled: GPU out of memory |
| ClusterTrainingRuntime | `torchtune-llama` | — | TorchTune LLaMA runtime |
| TrainingRuntime | `custom-training-runtime` | `ml-experiments` | Custom runtime |
| InferenceService | `granite-serving` | `production-models` | Granite 3B via vLLM, ready |
| ServingRuntime | `vllm-runtime` | `production-models` | vLLM serving runtime |
| DSPA | `dspa-default` | `ml-experiments` | Pipeline server, ready |
| Secret | `aws-connection-models` | `ml-experiments` | S3 data connection |
| PVC | `workbench-storage` | `ml-experiments` | 20Gi, bound |

The `MockK8sClient` subclasses the real `K8sClient` and overrides all methods to return data from this state. This means the MCP server's domain logic runs unmodified — only the underlying K8s API calls are replaced.

## Adding a New Scenario

1. Create a new file `evals/scenarios/test_<name>.py`:

```python
"""Scenario: <Description>.

<What this scenario tests>.
"""

from __future__ import annotations

import pytest
from deepeval import evaluate

from evals.agent import MCPAgent
from evals.config import EvalConfig
from evals.deepeval_helpers import build_mcp_server, result_to_conversational_test_case
from evals.mcp_harness import MCPHarness
from evals.metrics.config import create_multi_turn_mcp_use_metric, create_task_completion_metric


@pytest.mark.eval
class TestMyScenario:
    """Evaluate agent's ability to <do something>."""

    TASK = (
        "Natural language description of what the agent should accomplish. "
        "Be specific about resource names, namespaces, and expected actions."
    )

    @pytest.mark.eval
    async def test_my_scenario(
        self,
        eval_config: EvalConfig,
        harness: MCPHarness,
        agent: MCPAgent,
    ) -> None:
        """Agent should <expected behavior>."""
        result = await agent.run(self.TASK)

        # Basic sanity checks
        tool_names = result.tool_names_used
        assert len(tool_names) > 0, "Agent should call at least one tool"

        # Build DeepEval test case and evaluate
        mcp_server = build_mcp_server(harness)
        test_case = result_to_conversational_test_case(result, mcp_server)

        metrics = [
            create_multi_turn_mcp_use_metric(eval_config),
            create_task_completion_metric(eval_config),
        ]

        eval_result = evaluate(
            test_cases=[test_case],
            metrics=metrics,
            run_async=True,
            print_results=True,
        )

        for metric_result in eval_result.test_results[0].metrics_data:
            assert metric_result.success, (
                f"Metric {metric_result.metric_name} failed: {metric_result.reason}"
            )
```

2. If the scenario needs mock data that doesn't exist yet, add resources to `create_default_cluster_state()` in `evals/mock_k8s/cluster_state.py`.

3. Run the new scenario:

```bash
make eval-scenario SCENARIO=my_scenario
```

## DeepEval Metrics

The framework uses three DeepEval metrics, created via factory functions in `evals/metrics/config.py`:

### `MCPUseMetric`

Evaluates whether the agent selected and called appropriate MCP tools for a **single-turn** interaction. The judge LLM scores tool selection against the available tool set. Used by the tool discovery scenario.

### `MultiTurnMCPUseMetric`

Like `MCPUseMetric`, but evaluates the full multi-turn conversation. It considers the sequence and combination of tool calls across turns. Used by most scenarios.

### `MCPTaskCompletionMetric`

Evaluates whether the agent actually accomplished the task based on the tool call results and final output. Checks not just that the right tools were called, but that the overall task goal was met.

All metrics accept a `threshold` (0.0-1.0) configurable via `RHOAI_EVAL_MCP_USE_THRESHOLD` and `RHOAI_EVAL_TASK_COMPLETION_THRESHOLD`.

## Using Custom LLM Providers

### vLLM

Set the provider to `vllm` and provide the endpoint URL:

```bash
RHOAI_EVAL_LLM_PROVIDER=vllm
RHOAI_EVAL_LLM_MODEL=meta-llama/Llama-3.1-8B-Instruct
RHOAI_EVAL_LLM_API_KEY=token-placeholder
RHOAI_EVAL_LLM_BASE_URL=http://localhost:8000/v1
```

### Azure OpenAI

```bash
RHOAI_EVAL_LLM_PROVIDER=azure
RHOAI_EVAL_LLM_MODEL=gpt-4o
RHOAI_EVAL_LLM_API_KEY=your-azure-key
RHOAI_EVAL_LLM_BASE_URL=https://your-resource.openai.azure.com/openai/deployments/gpt-4o
```

### Custom judge endpoint

To use a self-hosted model as the DeepEval judge (instead of OpenAI), set the judge base URL:

```bash
RHOAI_EVAL_EVAL_MODEL=my-judge-model
RHOAI_EVAL_EVAL_API_KEY=token
RHOAI_EVAL_EVAL_MODEL_BASE_URL=http://localhost:8001/v1
```

The `CustomEvalLLM` class in `evals/metrics/custom_llm.py` wraps any OpenAI-compatible endpoint as a DeepEval judge LLM by implementing the `DeepEvalBaseLLM` interface.

## CI/CD

The GitHub Actions workflow (`.github/workflows/eval.yml`) runs mock-cluster evals on manual dispatch:

- **Trigger:** `workflow_dispatch` with optional `agent_model` and `judge_model` inputs
- **Defaults:** `gpt-4o-mini` for the agent, `gpt-4o` for the judge
- **Required secret:** `OPENAI_API_KEY`
- **Output:** JUnit XML results uploaded as an artifact

To trigger manually from the GitHub UI or CLI:

```bash
gh workflow run eval.yml --field agent_model=gpt-4o --field judge_model=gpt-4o
```

## Troubleshooting

### Missing API key

```
openai.AuthenticationError: Error code: 401
```

Ensure `RHOAI_EVAL_LLM_API_KEY` and `RHOAI_EVAL_EVAL_API_KEY` are set in `.env.eval` or the environment.

### Mock client errors

```
NotFoundError: <resource type> '<name>' not found
```

The agent asked for a resource that doesn't exist in the mock cluster state. If this is expected for your scenario, add the resource to `create_default_cluster_state()` in `evals/mock_k8s/cluster_state.py`.

### Agent reaches max turns

```
Agent reached maximum turns (20) without completing the task.
```

The agent couldn't finish within the turn limit. Try increasing `RHOAI_EVAL_MAX_AGENT_TURNS` or simplifying the task. This may also indicate the agent is stuck in a loop calling the same tools repeatedly.

### Metric failures

```
Metric MCPTaskCompletionMetric failed: <reason>
```

The judge LLM determined the agent didn't complete the task successfully. Check the `reason` field for details. You can lower the threshold temporarily to see partial scores:

```bash
RHOAI_EVAL_TASK_COMPLETION_THRESHOLD=0.3 make eval
```

### vLLM connection errors

```
openai.APIConnectionError: Connection error.
```

Verify your vLLM endpoint is running and accessible at the URL specified in `RHOAI_EVAL_LLM_BASE_URL`. The URL should include `/v1` (e.g., `http://localhost:8000/v1`).

### Verbose output

For more detail on what the agent is doing, enable debug logging:

```bash
RHOAI_EVAL_LLM_MODEL=gpt-4o uv run --group eval pytest evals/ -v -m "eval and not live" --tb=long -s --log-cli-level=DEBUG
```
