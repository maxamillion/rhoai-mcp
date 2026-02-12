#!/usr/bin/env python3
"""Estimate GPU, memory, and CPU requirements for model serving.

Standalone script (no rhoai_mcp imports). Uses heuristics based on model
identifier to estimate parameter count and derive resource recommendations.

Usage:
    python3 estimate-serving-resources.py --model-id "meta-llama/Llama-2-7b-hf"
    python3 estimate-serving-resources.py --model-id "mistral-7b" --target-throughput 20
    python3 estimate-serving-resources.py --model-id "Qwen2.5-72B" --target-latency-ms 50

Output: JSON with resource estimates.
"""

import argparse
import json
import re
import sys

# Model size estimates by parameter count range (billions) -> approximate size in GB
MODEL_SIZE_ESTIMATES: dict[tuple[int, int], int] = {
    (0, 1): 2,       # < 1B params -> ~2GB
    (1, 3): 6,       # 1-3B params -> ~6GB
    (3, 7): 14,      # 3-7B params -> ~14GB
    (7, 13): 26,     # 7-13B params -> ~26GB
    (13, 30): 60,    # 13-30B params -> ~60GB
    (30, 70): 140,   # 30-70B params -> ~140GB
    (70, 200): 400,  # 70-200B params -> ~400GB
}

# Known LLM model family names
LLM_KEYWORDS = [
    "llama", "mistral", "qwen", "falcon", "gpt", "bloom",
    "opt", "phi", "gemma", "instruct", "chat",
]


def _extract_param_count(model_id: str) -> float:
    """Extract parameter count (in billions) from model ID string.

    Attempts to parse common patterns like:
    - Llama-2-7b-hf -> 7
    - Qwen2.5-72B-Instruct -> 72
    - mistral-7b -> 7
    """
    model_lower = model_id.lower()

    patterns = [
        r"(\d+(?:\.\d+)?)\s*b(?:illion)?",  # 7b, 70b, 7.1b, 7 billion
        r"-(\d+(?:\.\d+)?)b-",               # -7b-
        r"(\d+(?:\.\d+)?)b$",                # ends with 7b
    ]

    for pattern in patterns:
        match = re.search(pattern, model_lower)
        if match:
            return float(match.group(1))

    # Default if no pattern matched
    return 7.0


def _detect_model_format(model_id: str) -> str:
    """Detect model format from model ID string."""
    model_lower = model_id.lower()

    if "onnx" in model_lower:
        return "onnx"
    elif "tensorflow" in model_lower or "tf-" in model_lower:
        return "tensorflow"
    elif "gguf" in model_lower or "ggml" in model_lower:
        return "gguf"
    else:
        return "pytorch"


def _detect_is_llm(model_id: str) -> bool:
    """Detect whether the model is a large language model."""
    model_lower = model_id.lower()
    return any(keyword in model_lower for keyword in LLM_KEYWORDS)


def _estimate_size_gb(params_billion: float) -> float:
    """Estimate model size in GB from parameter count."""
    for (min_p, max_p), size in MODEL_SIZE_ESTIMATES.items():
        if min_p <= params_billion < max_p:
            return float(size)
    # Models larger than 200B
    if params_billion >= 200:
        return 800.0
    # Fallback
    return 14.0


def _estimate_resources(
    params_billion: float,
    size_gb: float,
    is_llm: bool,
) -> dict:
    """Estimate serving resources from model characteristics."""
    # GPU requirements
    gpu_count = 0
    min_gpu_memory_gb = 0

    if size_gb > 2:
        gpu_count = 1
        min_gpu_memory_gb = int(size_gb * 1.2)  # 20% overhead

    if size_gb > 40:
        gpu_count = 2
    if size_gb > 80:
        gpu_count = 4

    # Memory requirements
    if size_gb < 5:
        memory = "4Gi"
        memory_limit = "8Gi"
    elif size_gb < 15:
        memory = "8Gi"
        memory_limit = "16Gi"
    elif size_gb < 40:
        memory = "16Gi"
        memory_limit = "32Gi"
    else:
        memory = "32Gi"
        memory_limit = "64Gi"

    # CPU requirements
    cpu = "2" if params_billion > 3 else "1"
    cpu_limit = "4" if params_billion > 3 else "2"

    # GPU type recommendation
    if min_gpu_memory_gb <= 16:
        recommended_gpu = "NVIDIA T4 (16GB)"
    elif min_gpu_memory_gb <= 24:
        recommended_gpu = "NVIDIA A10 (24GB)"
    elif min_gpu_memory_gb <= 40:
        recommended_gpu = "NVIDIA A100-40GB"
    elif min_gpu_memory_gb <= 80:
        recommended_gpu = "NVIDIA A100-80GB"
    else:
        recommended_gpu = "NVIDIA H100 or multiple GPUs"

    return {
        "gpu_count": gpu_count,
        "min_gpu_memory_gb": min_gpu_memory_gb,
        "memory": memory,
        "memory_limit": memory_limit,
        "cpu": cpu,
        "cpu_limit": cpu_limit,
        "recommended_gpu_type": recommended_gpu,
        "recommended_replicas": 1,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Estimate serving resource requirements for a model"
    )
    parser.add_argument(
        "--model-id",
        required=True,
        help="Model identifier (e.g., 'meta-llama/Llama-2-7b-hf')",
    )
    parser.add_argument(
        "--target-throughput",
        type=int,
        default=None,
        help="Target requests per second (optional)",
    )
    parser.add_argument(
        "--target-latency-ms",
        type=int,
        default=None,
        help="Target latency in milliseconds (optional)",
    )
    args = parser.parse_args()

    model_id = args.model_id

    # Estimate model characteristics
    params_billion = _extract_param_count(model_id)
    size_gb = _estimate_size_gb(params_billion)
    model_format = _detect_model_format(model_id)
    is_llm = _detect_is_llm(model_id)

    # Estimate resources
    resources = _estimate_resources(params_billion, size_gb, is_llm)

    # Adjust for performance targets
    if args.target_throughput and args.target_throughput > 10:
        resources["recommended_replicas"] = max(1, args.target_throughput // 10)

    notes = []
    if args.target_latency_ms and args.target_latency_ms < 100:
        notes.append("Low latency target may require high-end GPU")

    if is_llm and resources["gpu_count"] == 0:
        notes.append("LLM detected but model is small enough to run without GPU")

    result = {
        "model_id": model_id,
        "params_billion": params_billion,
        "size_gb": size_gb,
        "format": model_format,
        "is_llm": is_llm,
        "gpu_count": resources["gpu_count"],
        "min_gpu_memory_gb": resources["min_gpu_memory_gb"],
        "memory": resources["memory"],
        "memory_limit": resources["memory_limit"],
        "cpu": resources["cpu"],
        "cpu_limit": resources["cpu_limit"],
        "recommended_gpu_type": resources["recommended_gpu_type"],
        "recommended_replicas": resources["recommended_replicas"],
    }

    if notes:
        result["notes"] = notes

    json.dump(result, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
