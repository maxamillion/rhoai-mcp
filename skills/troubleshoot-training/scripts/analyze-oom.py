#!/usr/bin/env python3
"""Analyze OOM (Out of Memory) errors for a training job and suggest mitigations.

Examines Kubernetes events and pod status for OOM signals, then provides
specific recommendations for reducing memory usage including batch size
adjustments, quantization, and gradient checkpointing.

Usage:
    python3 analyze-oom.py --namespace NAMESPACE --job-name JOB_NAME

Output: JSON with OOM analysis and recommendations.
"""

import argparse
import json
import subprocess
import sys


def detect_cli() -> str:
    """Detect available CLI tool (oc or kubectl)."""
    for cli in ("oc", "kubectl"):
        try:
            subprocess.run(
                [cli, "version", "--client"],
                capture_output=True,
                check=True,
                timeout=10,
            )
            return cli
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            continue
    print("ERROR: Neither 'oc' nor 'kubectl' found in PATH.", file=sys.stderr)
    sys.exit(1)


def run_command(args: list[str], timeout: int = 30) -> str:
    """Run a command and return stdout, or empty string on failure."""
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def get_pod_info(cli: str, namespace: str, job_name: str) -> list[dict]:
    """Get pod information for the training job."""
    output = run_command([
        cli, "get", "pods",
        "-n", namespace,
        "-l", f"trainer.kubeflow.org/trainjob-name={job_name}",
        "-o", "json",
    ])
    if not output:
        return []
    try:
        data = json.loads(output)
        return data.get("items", [])
    except json.JSONDecodeError:
        return []


def get_events(cli: str, namespace: str, name: str) -> list[dict]:
    """Get Kubernetes events for a specific resource."""
    output = run_command([
        cli, "get", "events",
        "-n", namespace,
        "--field-selector", f"involvedObject.name={name}",
        "-o", "json",
    ])
    if not output:
        return []
    try:
        data = json.loads(output)
        return data.get("items", [])
    except json.JSONDecodeError:
        return []


def check_oom_signals(pods: list[dict], events: list[dict]) -> dict:
    """Check for OOM signals in pod statuses and events."""
    oom_detected = False
    oom_details: list[str] = []
    memory_limits: list[dict] = []

    for pod in pods:
        pod_name = pod.get("metadata", {}).get("name", "unknown")

        # Check container statuses for OOMKilled
        for cs in pod.get("status", {}).get("containerStatuses", []):
            # Current state
            terminated = cs.get("state", {}).get("terminated", {})
            if terminated.get("reason") == "OOMKilled":
                oom_detected = True
                oom_details.append(
                    f"Container '{cs['name']}' in pod '{pod_name}' was OOMKilled "
                    f"(exit code: {terminated.get('exitCode', 'unknown')})"
                )

            # Previous state
            last_terminated = cs.get("lastState", {}).get("terminated", {})
            if last_terminated.get("reason") == "OOMKilled":
                oom_detected = True
                oom_details.append(
                    f"Container '{cs['name']}' in pod '{pod_name}' was previously OOMKilled "
                    f"(exit code: {last_terminated.get('exitCode', 'unknown')})"
                )

        # Extract memory limits from containers
        for container in pod.get("spec", {}).get("containers", []):
            resources = container.get("resources", {})
            limits = resources.get("limits", {})
            requests = resources.get("requests", {})

            memory_info: dict = {"container": container.get("name", "unknown"), "pod": pod_name}
            if "memory" in limits:
                memory_info["memory_limit"] = limits["memory"]
            if "memory" in requests:
                memory_info["memory_request"] = requests["memory"]
            if "nvidia.com/gpu" in limits:
                memory_info["gpu_count"] = limits["nvidia.com/gpu"]

            memory_limits.append(memory_info)

    # Check events for OOM-related messages
    for event in events:
        message = event.get("message", "").lower()
        reason = event.get("reason", "").lower()
        if "oom" in message or "out of memory" in message or reason == "oomkilled":
            oom_detected = True
            oom_details.append(
                f"Event: {event.get('reason', 'unknown')} - {event.get('message', 'no message')}"
            )

    return {
        "oom_detected": oom_detected,
        "oom_details": oom_details,
        "memory_limits": memory_limits,
    }


def get_logs_for_cuda_oom(cli: str, namespace: str, job_name: str) -> dict:
    """Check logs for CUDA out-of-memory errors."""
    output = run_command([
        cli, "logs",
        "-n", namespace,
        "-l", f"trainer.kubeflow.org/trainjob-name={job_name}",
        "--tail=200",
    ])

    cuda_oom = False
    cuda_details: list[str] = []

    if output:
        for line in output.splitlines():
            lower = line.lower()
            if "cuda out of memory" in lower or "cudaerrormemoryal" in lower:
                cuda_oom = True
                cuda_details.append(line.strip())
            elif "torch.cuda.outofmemoryerror" in lower:
                cuda_oom = True
                cuda_details.append(line.strip())
            elif "oom" in lower and ("gpu" in lower or "cuda" in lower or "memory" in lower):
                cuda_oom = True
                cuda_details.append(line.strip())

    return {
        "cuda_oom_detected": cuda_oom,
        "cuda_oom_details": cuda_details[:10],  # Limit to 10 entries
    }


def parse_memory_value(value: str) -> int | None:
    """Parse a Kubernetes memory value (e.g., '16Gi') into bytes."""
    if not value:
        return None
    try:
        value = value.strip()
        if value.endswith("Gi"):
            return int(float(value[:-2]) * 1024 * 1024 * 1024)
        if value.endswith("Mi"):
            return int(float(value[:-2]) * 1024 * 1024)
        if value.endswith("Ki"):
            return int(float(value[:-2]) * 1024)
        if value.endswith("G"):
            return int(float(value[:-1]) * 1000 * 1000 * 1000)
        if value.endswith("M"):
            return int(float(value[:-1]) * 1000 * 1000)
        if value.endswith("K"):
            return int(float(value[:-1]) * 1000)
        return int(value)
    except (ValueError, TypeError):
        return None


def generate_recommendations(oom_info: dict, cuda_info: dict) -> dict:
    """Generate OOM mitigation recommendations."""
    recommendations: list[dict] = []
    estimated_batch_size = None

    is_cpu_oom = oom_info["oom_detected"]
    is_gpu_oom = cuda_info["cuda_oom_detected"]

    if is_gpu_oom:
        recommendations.append({
            "priority": 1,
            "action": "Reduce batch size",
            "description": (
                "Reduce per_device_train_batch_size in the training configuration. "
                "Start by halving the current batch size and increase gradient_accumulation_steps "
                "to maintain the same effective batch size."
            ),
            "example": "per_device_train_batch_size: 1, gradient_accumulation_steps: 8",
        })
        recommendations.append({
            "priority": 2,
            "action": "Switch to QLoRA",
            "description": (
                "Use QLoRA (Quantized LoRA) instead of full fine-tuning or standard LoRA. "
                "QLoRA loads the base model in 4-bit precision, dramatically reducing GPU memory."
            ),
            "example": "Use BitsAndBytesConfig with load_in_4bit=True",
        })
        recommendations.append({
            "priority": 3,
            "action": "Enable gradient checkpointing",
            "description": (
                "Enable gradient checkpointing to trade compute for memory. This recomputes "
                "activations during the backward pass instead of storing them."
            ),
            "example": "gradient_checkpointing: true",
        })
        recommendations.append({
            "priority": 4,
            "action": "Use a larger GPU",
            "description": (
                "If available, switch to a GPU with more memory. "
                "A100-80GB has twice the memory of A100-40GB. "
                "H100-80GB provides even more memory with better performance."
            ),
            "example": "Update the training runtime or resource requests to use a larger GPU type",
        })

        # Estimate batch size based on available memory info
        for mem_info in oom_info.get("memory_limits", []):
            gpu_count = mem_info.get("gpu_count")
            if gpu_count:
                try:
                    gpus = int(gpu_count)
                    # Rough heuristic: if OOM at unknown batch size, suggest batch_size=1
                    # with gradient accumulation
                    estimated_batch_size = {
                        "suggested_per_device_batch_size": 1,
                        "suggested_gradient_accumulation_steps": 8,
                        "gpu_count": gpus,
                        "note": (
                            "Start with batch_size=1 and increase gradually. "
                            "Use gradient_accumulation_steps to maintain effective batch size."
                        ),
                    }
                except (ValueError, TypeError):
                    pass

    if is_cpu_oom:
        recommendations.append({
            "priority": 1 if not is_gpu_oom else 5,
            "action": "Increase memory limits",
            "description": (
                "The container was killed by Kubernetes for exceeding its memory limit. "
                "Increase the memory limit in the pod spec or training runtime."
            ),
            "example": "resources.limits.memory: 32Gi (or higher)",
        })

        # Calculate recommended memory based on current limits
        for mem_info in oom_info.get("memory_limits", []):
            mem_limit = mem_info.get("memory_limit")
            if mem_limit:
                mem_bytes = parse_memory_value(mem_limit)
                if mem_bytes:
                    recommended_gi = int((mem_bytes * 2) / (1024 * 1024 * 1024))
                    recommendations.append({
                        "priority": 6,
                        "action": "Recommended memory increase",
                        "description": (
                            f"Current memory limit is {mem_limit}. "
                            f"Try increasing to {recommended_gi}Gi (double the current limit)."
                        ),
                        "example": f"resources.limits.memory: {recommended_gi}Gi",
                    })

    if not is_cpu_oom and not is_gpu_oom:
        recommendations.append({
            "priority": 1,
            "action": "No OOM detected",
            "description": (
                "No OOM signals were found in pod statuses, events, or logs. "
                "The training job may have failed for a different reason. "
                "Use the diagnose-training script for a broader diagnosis."
            ),
            "example": "bash scripts/diagnose-training.sh NAMESPACE JOB_NAME",
        })

    # Sort by priority
    recommendations.sort(key=lambda r: r["priority"])

    return {
        "recommendations": recommendations,
        "estimated_batch_size": estimated_batch_size,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze OOM errors for a training job"
    )
    parser.add_argument(
        "--namespace", required=True,
        help="Kubernetes namespace containing the TrainJob",
    )
    parser.add_argument(
        "--job-name", required=True,
        help="Name of the TrainJob to analyze",
    )
    args = parser.parse_args()

    cli = detect_cli()

    # Gather pod information
    pods = get_pod_info(cli, args.namespace, args.job_name)
    if not pods:
        result = {
            "job_name": args.job_name,
            "namespace": args.namespace,
            "oom_detected": False,
            "message": (
                "No pods found for this TrainJob. The job may not have started "
                "or pods may have been cleaned up."
            ),
            "recommendations": [],
        }
        print(json.dumps(result, indent=2))
        sys.exit(0)

    # Gather events for all pods
    all_events: list[dict] = []
    for pod in pods:
        pod_name = pod.get("metadata", {}).get("name", "")
        if pod_name:
            all_events.extend(get_events(cli, args.namespace, pod_name))

    # Also get events for the TrainJob itself
    all_events.extend(get_events(cli, args.namespace, args.job_name))

    # Check for OOM signals
    oom_info = check_oom_signals(pods, all_events)

    # Check logs for CUDA OOM
    cuda_info = get_logs_for_cuda_oom(cli, args.namespace, args.job_name)

    # Generate recommendations
    rec_info = generate_recommendations(oom_info, cuda_info)

    # Assemble output
    result = {
        "job_name": args.job_name,
        "namespace": args.namespace,
        "cpu_oom_detected": oom_info["oom_detected"],
        "gpu_oom_detected": cuda_info["cuda_oom_detected"],
        "oom_details": oom_info["oom_details"],
        "cuda_oom_details": cuda_info["cuda_oom_details"],
        "memory_configuration": oom_info["memory_limits"],
        "recommendations": rec_info["recommendations"],
        "estimated_batch_size": rec_info["estimated_batch_size"],
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
