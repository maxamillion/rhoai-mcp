"""MCP Tools for tool discovery and workflow guidance."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import FastMCP

if TYPE_CHECKING:
    from rhoai_mcp.server import RHOAIServer


# Tool categories with workflow hints
TOOL_CATEGORIES: dict[str, dict[str, Any]] = {
    "discovery": {
        "description": "Start here to understand cluster state",
        "tools": ["cluster_summary", "project_summary", "explore_cluster", "list_resources"],
        "use_first": True,
    },
    "training": {
        "description": "Model fine-tuning operations",
        "tools": [
            "prepare_training",
            "train",
            "get_training_progress",
            "get_training_logs",
            "analyze_training_failure",
        ],
        "typical_workflow": [
            "prepare_training",
            "train (with confirmed=True)",
            "get_training_progress",
        ],
    },
    "inference": {
        "description": "Model deployment and serving",
        "tools": [
            "prepare_model_deployment",
            "deploy_model",
            "get_model_endpoint",
            "test_model_endpoint",
            "recommend_serving_runtime",
        ],
        "typical_workflow": [
            "prepare_model_deployment",
            "deploy_model",
            "test_model_endpoint",
        ],
    },
    "workbenches": {
        "description": "Jupyter notebook environments",
        "tools": [
            "list_workbenches",
            "create_workbench",
            "start_workbench",
            "stop_workbench",
            "get_workbench_url",
        ],
    },
    "diagnostics": {
        "description": "Troubleshooting and debugging",
        "tools": [
            "diagnose_resource",
            "analyze_training_failure",
            "get_job_events",
            "get_training_logs",
        ],
    },
    "resources": {
        "description": "Generic resource operations",
        "tools": [
            "get_resource",
            "list_resources",
            "manage_resource",
            "resource_status",
        ],
    },
    "storage": {
        "description": "Storage and data connections",
        "tools": [
            "list_storage",
            "create_storage",
            "setup_training_storage",
            "list_data_connections",
            "create_s3_data_connection",
        ],
    },
}


# Intent patterns for suggest_tools
INTENT_PATTERNS = [
    {
        "patterns": ["train", "fine-tune", "finetune", "lora", "qlora"],
        "category": "training",
        "workflow": ["prepare_training", "train"],
        "explanation": "Training workflow: First use prepare_training() to check prerequisites, "
        "then train() with confirmed=True to start the job.",
    },
    {
        "patterns": ["deploy", "serve", "inference", "predict"],
        "category": "inference",
        "workflow": ["prepare_model_deployment", "deploy_model"],
        "explanation": "Deployment workflow: First use prepare_model_deployment() to validate, "
        "then deploy_model() to create the InferenceService.",
    },
    {
        "patterns": ["debug", "troubleshoot", "failed", "error", "why", "broken"],
        "category": "diagnostics",
        "workflow": ["diagnose_resource"],
        "explanation": "Use diagnose_resource() to get comprehensive diagnostics including "
        "status, events, logs, and suggested fixes.",
    },
    {
        "patterns": ["explore", "overview", "cluster", "what's running", "status"],
        "category": "discovery",
        "workflow": ["explore_cluster"],
        "explanation": "Use explore_cluster() to get a complete overview of all projects "
        "and resources in the cluster.",
    },
    {
        "patterns": ["notebook", "workbench", "jupyter", "code"],
        "category": "workbenches",
        "workflow": ["list_workbenches", "create_workbench"],
        "explanation": "Use list_workbenches() to see existing notebooks, "
        "create_workbench() to create a new one.",
    },
    {
        "patterns": ["storage", "pvc", "volume", "data connection", "s3"],
        "category": "storage",
        "workflow": ["list_storage", "list_data_connections"],
        "explanation": "Use list_storage() for PVCs, list_data_connections() for S3 connections.",
    },
]

# Discovery pattern for fallback when no pattern matches
DISCOVERY_PATTERN = next(p for p in INTENT_PATTERNS if p["category"] == "discovery")


def _get_toolscope_manager(server: RHOAIServer) -> Any:
    """Get ToolScope manager from plugin registry."""
    try:
        from rhoai_mcp.composites.toolscope.plugin import ToolScopePlugin

        for plugin in server.plugins.values():
            if isinstance(plugin, ToolScopePlugin) and plugin.manager:
                return plugin.manager
    except ImportError:
        pass
    return None


def _record_optimizer_context(server: RHOAIServer, query: str) -> None:
    """Record query for small model optimizer context tracking."""
    try:
        from rhoai_mcp.composites.optimizer.plugin import SmallModelOptimizerPlugin

        for plugin in server.plugins.values():
            if isinstance(plugin, SmallModelOptimizerPlugin) and plugin.optimizer:
                plugin.optimizer.record_context(query)
                break
    except ImportError:
        pass


def _build_example_calls(workflow: list[str], context: dict[str, Any]) -> list[dict[str, Any]]:
    """Build example tool calls for a workflow."""
    namespace = context.get("namespace", "my-project")
    resource_name = context.get("resource_name", "my-resource")

    example_calls: list[dict[str, Any]] = []
    for tool in workflow:
        if tool == "prepare_training":
            example_calls.append({
                "tool": tool,
                "args": {
                    "namespace": namespace,
                    "model_id": "meta-llama/Llama-2-7b-hf",
                    "dataset_id": "tatsu-lab/alpaca",
                },
            })
        elif tool == "train":
            example_calls.append({
                "tool": tool,
                "args": {
                    "namespace": namespace,
                    "model_id": "meta-llama/Llama-2-7b-hf",
                    "confirmed": True,
                },
            })
        elif tool == "prepare_model_deployment":
            example_calls.append({
                "tool": tool,
                "args": {
                    "namespace": namespace,
                    "model_id": "meta-llama/Llama-2-7b-hf",
                },
            })
        elif tool == "deploy_model":
            example_calls.append({
                "tool": tool,
                "args": {
                    "namespace": namespace,
                    "name": "my-model",
                    "runtime": "vllm-runtime",
                    "model_format": "pytorch",
                    "storage_uri": "pvc://model-storage/model",
                },
            })
        elif tool == "diagnose_resource":
            example_calls.append({
                "tool": tool,
                "args": {
                    "resource_type": "training_job",
                    "name": resource_name,
                    "namespace": namespace,
                },
            })
        elif tool == "explore_cluster":
            example_calls.append({
                "tool": tool,
                "args": {},
            })
        else:
            example_calls.append({
                "tool": tool,
                "args": {"namespace": namespace},
            })

    return example_calls


def register_tools(mcp: FastMCP, server: RHOAIServer) -> None:
    """Register meta tools with the MCP server."""

    @mcp.tool()
    def suggest_tools(
        intent: str,
        context: dict[str, Any] | None = None,
        show_all: bool = False,  # noqa: ARG001
    ) -> dict[str, Any]:
        """Get recommended tools and workflow for a given intent.

        Uses semantic search (when ToolScope is enabled) or keyword matching
        to find the most relevant tools for your task.

        When small_model_mode is enabled, this tool can discover tools not
        currently visible in the filtered list. Calling this updates the
        context, which may cause related tools to appear in subsequent
        tools/list calls.

        Args:
            intent: What you want to do (e.g., "train a model", "debug failed job").
            context: Optional context like {"namespace": "...", "resource_name": "..."}.
            show_all: If True, searches all tools regardless of current filtering.

        Returns:
            Recommended tools with workflow, explanation, and example calls.
        """
        context = context or {}

        # Record context for small model optimizer
        _record_optimizer_context(server, intent)

        manager = _get_toolscope_manager(server)

        # Try semantic search first
        if manager and manager.is_initialized:
            matches = manager.search(intent, k=5)
            if matches:
                workflow = [m.name for m in matches[:3]]
                category = matches[0].category if matches else "discovery"

                # Build explanation
                explanation = (
                    f"Based on semantic search for '{intent}', these tools are most relevant. "
                )
                if category in TOOL_CATEGORIES:
                    cat_info = TOOL_CATEGORIES[category]
                    if "typical_workflow" in cat_info:
                        explanation += (
                            f"Typical workflow: {' -> '.join(cat_info['typical_workflow'])}"
                        )

                return {
                    "intent": intent,
                    "category": category,
                    "workflow": workflow,
                    "explanation": explanation,
                    "search_method": "semantic",
                    "matches": [
                        {
                            "name": m.name,
                            "score": round(m.score, 3),
                            "description": m.description[:100],
                        }
                        for m in matches
                    ],
                    "example_calls": _build_example_calls(workflow, context),
                    "all_categories": list(TOOL_CATEGORIES.keys()),
                }

        # Fallback to keyword matching
        intent_lower = intent.lower()
        best_match = None
        match_score = 0

        for pattern in INTENT_PATTERNS:
            score = sum(1 for p in pattern["patterns"] if p in intent_lower)
            if score > match_score:
                match_score = score
                best_match = pattern

        if not best_match:
            best_match = DISCOVERY_PATTERN

        return {
            "intent": intent,
            "category": best_match["category"],
            "workflow": best_match["workflow"],
            "explanation": best_match["explanation"],
            "search_method": "keyword",
            "example_calls": _build_example_calls(list(best_match["workflow"]), context),
            "all_categories": list(TOOL_CATEGORIES.keys()),
        }

    @mcp.tool()
    def list_tool_categories() -> dict[str, Any]:
        """List all available tool categories with descriptions.

        Returns a summary of tool categories organized by use case,
        helping you find the right tools for your task.

        Returns:
            Tool categories with descriptions and key tools.
        """
        categories = []
        for name, info in TOOL_CATEGORIES.items():
            categories.append(
                {
                    "category": name,
                    "description": info["description"],
                    "key_tools": info["tools"][:3],
                    "use_first": info.get("use_first", False),
                }
            )

        return {
            "categories": categories,
            "recommendation": "Start with 'discovery' tools like explore_cluster() "
            "to understand the cluster state before taking actions.",
        }
