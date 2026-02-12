---
name: analyze-oom
description: Diagnose and fix out-of-memory errors in training jobs. Checks for OOMKilled events and CUDA OOM in logs, estimates memory needs, and suggests mitigations like QLoRA or smaller batch sizes.
license: Apache-2.0
compatibility: Requires oc or kubectl, jq, and python3. Needs an OpenShift cluster with RHOAI and the Kubeflow Training Operator.
metadata:
  author: Red Hat
  version: "1.0"
  category: troubleshooting
---

# Analyze OOM

Diagnose and fix out-of-memory (OOM) errors in training jobs on Red Hat
OpenShift AI (RHOAI). This skill detects both system-level OOMKilled events
and CUDA GPU out-of-memory errors, estimates memory requirements for the
training configuration, and suggests targeted mitigations.

## Prerequisites

- `oc` or `kubectl` CLI installed and authenticated to the cluster
- `jq` installed for JSON processing
- `python3` installed (for memory estimation)
- Kubeflow Training Operator installed on the cluster

## Common OOM Causes

OOM errors in training jobs typically fall into two categories:

**System OOM (OOMKilled)**: The Linux kernel kills the container because it
exceeded its memory limit. This appears as an `OOMKilled` reason in the pod
status or events.

**CUDA OOM (GPU memory)**: The GPU runs out of memory during forward or
backward pass. This appears as `torch.cuda.OutOfMemoryError` or
`CUDA out of memory` in the training logs.

Common root causes include:
- Batch size too large for available GPU memory
- Model too large to fit on the selected GPU
- Gradient accumulation consuming excessive memory
- Lack of gradient checkpointing causing high activation memory
- Full fine-tuning when LoRA or QLoRA would suffice

## Mitigation Hierarchy

When an OOM error is detected, apply fixes in this order (least disruptive
first):

1. **Reduce batch size** -- Lower `per_device_train_batch_size` and increase
   `gradient_accumulation_steps` to maintain the same effective batch size.
   This is the simplest fix and often sufficient.

2. **Enable gradient checkpointing** -- Set `gradient_checkpointing: true` to
   trade compute time for memory. Recomputes activations during the backward
   pass instead of storing them all.

3. **Switch from LoRA to QLoRA** -- Use 4-bit quantization for the base model
   weights. QLoRA uses roughly 33% less memory than standard LoRA with
   minimal quality loss.

4. **Add more GPUs** -- Distribute the model across multiple GPUs using data
   parallelism or model parallelism. This requires changes to the training
   runtime configuration.

5. **Use a smaller model** -- If none of the above suffice, consider using a
   smaller model variant (e.g., 7B instead of 13B, or 3B instead of 7B).

## Workflow

### Step 1: Verify cluster authentication

```bash
bash skills/_shared/auth-check.sh
```

Confirm the CLI is authenticated and the cluster is accessible before
proceeding.

### Step 2: Analyze OOM errors

```bash
bash scripts/analyze-oom.sh NAMESPACE JOB_NAME
```

Replace `NAMESPACE` with the project namespace and `JOB_NAME` with the
TrainJob name. This script:

1. Checks pod events for OOMKilled signals
2. Scans training logs for CUDA out-of-memory patterns
3. Extracts the current job resource configuration
4. Outputs JSON with the OOM type, relevant events, log excerpts, current
   configuration, and recommended fixes

### Step 3: Estimate memory requirements

```bash
python3 scripts/estimate-memory.py --model-id MODEL_ID --method METHOD --batch-size BATCH_SIZE --gpu-memory-gb GPU_MEM
```

Replace:
- `MODEL_ID` with the model identifier (e.g., `meta-llama/Llama-2-7b-hf`)
- `METHOD` with the fine-tuning method (`lora`, `qlora`, `dora`, or `full`)
- `BATCH_SIZE` with the per-device batch size (default: 32)
- `GPU_MEM` with the actual GPU memory in GB (e.g., 40 for A100-40GB)

This script estimates total GPU memory needed and compares it against the
available memory, then suggests specific parameter changes to fit within the
budget.

### Step 4: Apply recommended mitigations

Review the JSON output from both scripts. The recommendations are ordered by
priority following the mitigation hierarchy above. Apply the highest-priority
fix first, re-run the training job, and iterate if needed.
