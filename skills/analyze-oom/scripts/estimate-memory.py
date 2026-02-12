#!/usr/bin/env python3
"""Estimate GPU memory requirements for model fine-tuning and suggest mitigations.

Standalone script (no rhoai_mcp imports) that calculates approximate GPU memory
needs based on model size, fine-tuning method, and batch size, then compares
against available GPU memory and suggests specific parameter changes.

Usage:
    python3 estimate-memory.py --model-id meta-llama/Llama-2-7b-hf --method lora \
        --batch-size 32 --gpu-memory-gb 40
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys

# Memory multipliers for each fine-tuning method relative to base model memory.
# full = model weights + optimizer states + gradients (all in fp16/fp32)
# lora = frozen base model + small trainable adapter weights + optimizer for adapters
# qlora = 4-bit quantized base model + adapter weights + optimizer for adapters
# dora = similar to lora with additional weight decomposition overhead
METHOD_MULTIPLIERS: dict[str, float] = {
    "full": 4.0,
    "lora": 1.8,
    "qlora": 1.2,
    "dora": 1.8,
}

# Bytes per parameter in fp16
BYTES_PER_PARAM: int = 2


def _extract_param_count(model_id: str) -> float:
    """Extract parameter count in billions from a model identifier.

    Parses common naming patterns such as:
    - meta-llama/Llama-2-7b-hf  -> 7
    - Qwen/Qwen2.5-72B-Instruct -> 72
    - mistralai/mistral-7b       -> 7
    - TinyLlama-1.1B             -> 1.1
    - google/gemma-2b            -> 2

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

    return 7.0  # Conservative default


def _batch_size_memory_factor(batch_size: int) -> float:
    """Calculate the memory scaling factor for batch size.

    Each doubling from batch_size=1 adds approximately 10% more memory
    due to activation storage.
    """
    if batch_size <= 1:
        return 1.0
    doublings = math.log2(batch_size)
    return 1.0 + 0.10 * doublings


def estimate_memory(
    model_id: str,
    method: str = "lora",
    batch_size: int = 32,
    gpu_memory_gb: float = 40.0,
) -> dict:
    """Calculate memory estimates and compare against available GPU memory.

    Returns a dictionary with estimated parameters, memory requirements,
    whether the configuration fits, and suggestions for adjustments.
    """
    param_count = _extract_param_count(model_id)

    # Normalise method
    method = method.lower()
    if method not in METHOD_MULTIPLIERS:
        method = "lora"
    multiplier = METHOD_MULTIPLIERS[method]

    # Base model memory: params * bytes_per_param
    base_memory_gb = (param_count * 1e9 * BYTES_PER_PARAM) / (1024**3)

    # Apply method multiplier
    method_memory_gb = base_memory_gb * multiplier

    # Apply batch size factor
    batch_factor = _batch_size_memory_factor(batch_size)
    estimated_memory_gb = method_memory_gb * batch_factor

    # Round for readability
    estimated_memory_gb = round(estimated_memory_gb, 1)

    fits = estimated_memory_gb <= gpu_memory_gb

    # Generate suggestions if it does not fit
    suggestions: list[str] = []
    if not fits:
        # Suggestion 1: Reduce batch size
        # Find the largest batch size that would fit
        for candidate_bs in [batch_size // 2, batch_size // 4, batch_size // 8, 4, 2, 1]:
            if candidate_bs < 1:
                continue
            candidate_factor = _batch_size_memory_factor(candidate_bs)
            candidate_mem = round(method_memory_gb * candidate_factor, 1)
            if candidate_mem <= gpu_memory_gb:
                suggestions.append(
                    f"Reduce batch_size from {batch_size} to {candidate_bs} "
                    f"(estimated {candidate_mem} GB). Use "
                    f"gradient_accumulation_steps={batch_size // candidate_bs} "
                    f"to maintain effective batch size."
                )
                break
        else:
            suggestions.append(
                f"Even batch_size=1 may not fit. Estimated memory at batch_size=1: "
                f"{round(method_memory_gb, 1)} GB."
            )

        # Suggestion 2: Enable gradient checkpointing
        suggestions.append(
            "Enable gradient checkpointing (gradient_checkpointing=true) to reduce "
            "activation memory at the cost of ~20% slower training."
        )

        # Suggestion 3: Switch to a more memory-efficient method
        if method == "full":
            qlora_mem = round(
                base_memory_gb * METHOD_MULTIPLIERS["qlora"]
                * _batch_size_memory_factor(batch_size), 1
            )
            lora_mem = round(
                base_memory_gb * METHOD_MULTIPLIERS["lora"]
                * _batch_size_memory_factor(batch_size), 1
            )
            suggestions.append(
                f"Switch from full fine-tuning to LoRA (estimated {lora_mem} GB) "
                f"or QLoRA (estimated {qlora_mem} GB)."
            )
        elif method == "lora" or method == "dora":
            qlora_mem = round(
                base_memory_gb * METHOD_MULTIPLIERS["qlora"]
                * _batch_size_memory_factor(batch_size), 1
            )
            suggestions.append(
                f"Switch from {method.upper()} to QLoRA (estimated {qlora_mem} GB) "
                f"for ~33% memory reduction."
            )

        # Suggestion 4: More GPUs
        gpus_needed = math.ceil(estimated_memory_gb / gpu_memory_gb)
        if gpus_needed > 1:
            suggestions.append(
                f"Use {gpus_needed} GPUs to distribute memory across devices."
            )

        # Suggestion 5: Smaller model
        if param_count > 7:
            suggestions.append(
                f"Consider a smaller model variant. Current model has ~{param_count}B "
                f"parameters. A 7B model would need approximately "
                f"{round(7e9 * BYTES_PER_PARAM / (1024**3) * multiplier * _batch_size_memory_factor(batch_size), 1)} GB."
            )

    return {
        "model_id": model_id,
        "model_params_b": param_count,
        "method": method,
        "batch_size": batch_size,
        "estimated_memory_gb": estimated_memory_gb,
        "available_memory_gb": gpu_memory_gb,
        "fits": fits,
        "suggestions": suggestions,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Estimate GPU memory requirements for model fine-tuning."
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
        "--gpu-memory-gb",
        type=float,
        required=True,
        help="Available GPU memory in GB (e.g., 40 for A100-40GB)",
    )

    args = parser.parse_args()

    result = estimate_memory(
        model_id=args.model_id,
        method=args.method,
        batch_size=args.batch_size,
        gpu_memory_gb=args.gpu_memory_gb,
    )

    json.dump(result, sys.stdout, indent=2)
    print()  # trailing newline


if __name__ == "__main__":
    main()
