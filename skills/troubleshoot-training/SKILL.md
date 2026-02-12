---
name: troubleshoot-training
description: Diagnose and fix issues with training jobs on RHOAI including OOM errors, scheduling failures, and image pull issues. Use when a training job is failing or stuck.
license: Apache-2.0
compatibility: Requires oc or kubectl, jq, and python3. Needs Kubeflow Training Operator installed.
metadata:
  author: Red Hat
  version: "1.0"
  category: training
---

# Troubleshoot Training

Diagnose and fix issues with training jobs on Red Hat OpenShift AI (RHOAI).
This skill identifies common failure patterns including OOM (Out of Memory)
errors, scheduling failures, image pull issues, and crash loops, then suggests
targeted fixes.

## Prerequisites

- `oc` or `kubectl` CLI installed and authenticated to the cluster
- `jq` installed for JSON processing
- `python3` installed (for OOM analysis)
- Kubeflow Training Operator installed on the cluster

## Workflow

### Step 1: Get job status and identify failure type

Start by checking the training job's current state and conditions:

```bash
bash ../monitor-training/scripts/training-status.sh NAMESPACE JOB_NAME
```

Replace `NAMESPACE` with the project namespace and `JOB_NAME` with the TrainJob
name. Look for conditions that indicate a failure, such as `Failed` status or
error messages in the conditions.

### Step 2: Run diagnostic script

Run the comprehensive diagnostic script to gather all relevant information:

```bash
bash scripts/diagnose-training.sh NAMESPACE JOB_NAME
```

This script performs a thorough diagnosis:

1. Gets the TrainJob status and conditions
2. Collects events for the job and its pods
3. Retrieves logs from training containers (including previous container logs)
4. Scans for common failure patterns:
   - **OOMKilled**: Container exceeded memory limits
   - **ImagePullBackOff**: Container image could not be pulled
   - **FailedScheduling**: Not enough resources to schedule the pod
   - **CrashLoopBackOff**: Container repeatedly crashing on startup

The output is JSON containing the status, detected issues, suggested fixes,
relevant events, and a log snippet.

### Step 3: Analyze OOM if applicable

If the diagnostic script detects an OOM (Out of Memory) error, run the OOM
analysis script for detailed recommendations:

```bash
python3 scripts/analyze-oom.py --namespace NAMESPACE --job-name JOB_NAME
```

This script:

1. Queries events and pod status for OOM signals
2. Examines the container's memory limits and GPU memory configuration
3. Suggests specific mitigations:
   - Reduce batch size
   - Switch to QLoRA (quantized LoRA) for lower memory usage
   - Enable gradient checkpointing
   - Increase GPU memory by using a larger GPU type
4. Estimates what batch size might work based on available memory

The output is JSON with detailed recommendations.

## Common Issues and Solutions

### OOMKilled (Out of Memory)

**Symptoms**: Pod terminated with reason `OOMKilled`, or CUDA out-of-memory
errors in logs.

**Solutions**:
- Reduce `per_device_train_batch_size` in the training configuration
- Enable gradient checkpointing (`gradient_checkpointing: true`)
- Switch from full fine-tuning to LoRA or QLoRA
- Use a GPU with more memory (e.g., A100-80GB instead of A100-40GB)

### ImagePullBackOff

**Symptoms**: Pod stuck in `ImagePullBackOff` status, events show image pull
errors.

**Solutions**:
- Verify the container image name and tag are correct
- Check that image pull secrets are configured in the namespace
- Verify network access to the container registry
- For private registries, ensure credentials are up to date

### FailedScheduling

**Symptoms**: Pod stuck in `Pending` state, events show `FailedScheduling`.

**Solutions**:
- Check GPU availability with the explore-cluster skill's GPU resources script
- Reduce the number of requested GPUs
- Wait for other workloads to complete and free resources
- Check node taints and tolerations match the pod configuration

### CrashLoopBackOff

**Symptoms**: Pod repeatedly restarting, status shows `CrashLoopBackOff`.

**Solutions**:
- Check the logs from the previous container run for error messages
- Verify the training script and entry point are correct
- Check that required environment variables and volume mounts are configured
- Ensure the training dataset is accessible from the pod
