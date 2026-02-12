#!/usr/bin/env python3
"""Estimate GPU and memory requirements for model fine-tuning.

Standalone script (no rhoai_mcp imports) that calculates approximate resource
requirements based on model size, fine-tuning method, and training configuration.

Usage:
    python3 estimate-resources.py --model-id meta-llama/Llama-2-7b-hf --method lora
"""

from __future__ import annotations

import argparse
import json
import re
import sys

# GPU memory estimates by model size range (billions of parameters).
# Key: (min_params_inclusive, max_params_exclusive) -> base_memory_gb
GPU_MEMORY_ESTIMATES: dict[tuple[int, int], int] = {
    (0, 1): 2,
    (1, 3): 6,
    (3, 7): 14,
    (7, 13): 26,
    (13, 30): 48,
    (30, 70): 80,
    (70, 200): 160,
}

# Memory multipliers for each PEFT method relative to base model memory.
PEFT_MULTIPLIERS: dict[str, float] = {
    "full": 4.0,
    "lora": 1.8,
    "qlora": 1.2,
    "dora": 1.8,
}


def _extract_param_count(model_id: str) -> float:
    """Extract parameter count in billions from a model identifier.

    Attempts to parse common naming patterns such as:
    - meta-llama/Llama-2-7b-hf  -> 7
    - Qwen/Qwen2.5-72B-Instruct -> 72
    - mistralai/mistral-7b       -> 7
    - TinyLlama-1.1B             -> 1.1

    Falls back to 7.0 if no pattern matches.
    """
    model_lower = model_id.lower()

    patterns = [
        r"(\d+(?:\.\d+)?)\s*b(?:illion)?",  # 7b, 70b, 7.1b, 1.1billion
        r"-(\d+(?:\.\d+)?)b-",               # -7b-
        r"(\d+(?:\.\d+)?)b$",                # ends with 7b
    ]

    for pattern in patterns:
        match = re.search(pattern, model_lower)
        if match:
            return float(match.group(1))

    # Check for million-scale parameters (e.g., 350m)
    m_match = re.search(r"(\d+)m", model_lower)
    if m_match:
        return float(m_match.group(1)) / 1000

    # Heuristic defaults for well-known model families
    if "llama" in model_lower:
        return 7.0
    if "mistral" in model_lower:
        return 7.0
    if "qwen" in model_lower:
        return 7.0

    return 7.0  # Conservative default


def estimate_resources(
    model_id: str,
    method: str = "lora",
    batch_size: int = 32,
    sequence_length: int = 512,
    num_nodes: int = 1,
    gpus_per_node: int = 1,
) -> dict:
    """Calculate resource estimates for a training configuration.

    Returns a dictionary with memory breakdown, recommended GPU count/type,
    and storage requirements.
    """
    param_count = _extract_param_count(model_id)

    # Look up base memory from the estimates table
    base_memory = 16  # Default for unknown sizes
    for (min_p, max_p), mem in GPU_MEMORY_ESTIMATES.items():
        if min_p <= param_count < max_p:
            base_memory = mem
            break

    # Normalise method and get multiplier
    method = method.lower()
    if method not in PEFT_MULTIPLIERS:
        method = "lora"
    multiplier = PEFT_MULTIPLIERS[method]

    # Memory components
    model_memory = base_memory
    optimizer_memory = base_memory * 0.5 if method == "full" else base_memory * 0.1
    activation_memory = (batch_size * sequence_length * param_count * 2) / (1024 * 1024 * 1024)
    activation_memory = min(activation_memory, base_memory * 0.5)  # Cap estimate

    total_memory = (model_memory + optimizer_memory + activation_memory) * multiplier

    # Per-GPU memory
    total_gpus = num_nodes * gpus_per_node
    per_gpu_memory = total_memory / total_gpus if total_gpus > 0 else total_memory

    # Recommended GPU type based on per-GPU requirement
    if per_gpu_memory <= 16:
        recommended_gpu = "NVIDIA T4 (16GB)"
    elif per_gpu_memory <= 24:
        recommended_gpu = "NVIDIA A10 (24GB)"
    elif per_gpu_memory <= 40:
        recommended_gpu = "NVIDIA A100-40GB"
    elif per_gpu_memory <= 80:
        recommended_gpu = "NVIDIA A100-80GB"
    else:
        recommended_gpu = "NVIDIA H100 (80GB) or multiple GPUs"

    # Recommended GPU count (targeting 80 GB per GPU ceiling)
    recommended_gpus = 1
    if per_gpu_memory > 80:
        recommended_gpus = int((total_memory / 80) + 0.5)

    # Storage estimate: model checkpoints + buffer
    storage_gb = int(param_count * 4) + 50

    return {
        "model_id": model_id,
        "estimated_params_billion": param_count,
        "method": method,
        "model_memory_gb": round(model_memory, 1),
        "optimizer_state_gb": round(optimizer_memory, 1),
        "activation_memory_gb": round(activation_memory, 1),
        "total_required_gb": round(total_memory, 1),
        "per_gpu_memory_gb": round(per_gpu_memory, 1),
        "recommended_gpus": recommended_gpus,
        "recommended_gpu_type": recommended_gpu,
        "storage_gb": storage_gb,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Estimate GPU and memory requirements for model fine-tuning."
    )
    parser.add_argument(
        "--model-id",
        required=True,
        help="Model identifier (e.g., meta-llama/Llama-2-7b-hf)",
    )
    parser.add_argument(
        "--method",
        default="lora",
        choices=["lora", "qlora", "dora", "full"],
        help="Fine-tuning method (default: lora)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Per-device batch size (default: 32)",
    )
    parser.add_argument(
        "--sequence-length",
        type=int,
        default=512,
        help="Maximum sequence length (default: 512)",
    )
    parser.add_argument(
        "--num-nodes",
        type=int,
        default=1,
        help="Number of training nodes (default: 1)",
    )
    parser.add_argument(
        "--gpus-per-node",
        type=int,
        default=1,
        help="GPUs per node (default: 1)",
    )

    args = parser.parse_args()

    result = estimate_resources(
        model_id=args.model_id,
        method=args.method,
        batch_size=args.batch_size,
        sequence_length=args.sequence_length,
        num_nodes=args.num_nodes,
        gpus_per_node=args.gpus_per_node,
    )

    json.dump(result, sys.stdout, indent=2)
    print()  # trailing newline


if __name__ == "__main__":
    main()
