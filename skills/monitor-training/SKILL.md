---
name: monitor-training
description: Monitor an active training job's progress, logs, events, and checkpoints on RHOAI. Use when the user wants to check on a running training job.
license: Apache-2.0
compatibility: Requires oc or kubectl and jq. Needs Kubeflow Training Operator installed.
metadata:
  author: Red Hat
  version: "1.0"
  category: training
---

# Monitor Training

Monitor an active training job's progress, logs, events, and checkpoints on
Red Hat OpenShift AI (RHOAI). This skill gathers real-time status, training
metrics, pod logs, and Kubernetes events for a running TrainJob.

## Prerequisites

- `oc` or `kubectl` CLI installed and authenticated to the cluster
- `jq` installed for JSON processing
- Kubeflow Training Operator installed on the cluster

## Workflow

### Step 1: Check job status

Get the current status and conditions of the training job.

```bash
bash scripts/training-status.sh NAMESPACE JOB_NAME
```

Replace `NAMESPACE` with the project namespace and `JOB_NAME` with the name of
the TrainJob. The script outputs JSON with the job name, current status derived
from conditions, model and dataset identifiers, and creation time.

### Step 2: Get training progress and metrics

Retrieve detailed training progress from the trainer status annotation.

```bash
bash scripts/training-progress.sh NAMESPACE JOB_NAME
```

This extracts the `trainer.opendatahub.io/trainerStatus` annotation from the
TrainJob, which contains live training metrics. The output includes:

- **trainingState**: Current state (e.g., `Training`, `Completed`, `Failed`)
- **currentEpoch / totalEpochs**: Epoch progress
- **currentStep / totalSteps**: Step progress
- **loss**: Current training loss value
- **learningRate**: Current learning rate
- **throughput**: Tokens or samples per second
- **gradientNorm**: Gradient norm for monitoring training stability
- **estimatedTimeRemaining**: Estimated time to completion

### Step 3: View logs

Get recent log output from the training pods.

```bash
bash scripts/training-logs.sh NAMESPACE JOB_NAME [TAIL_LINES]
```

The optional `TAIL_LINES` argument controls how many lines to retrieve (default
100). Logs come from all pods labeled with the TrainJob name.

### Step 4: Check events

Review Kubernetes events related to the training job and its pods.

```bash
bash scripts/training-events.sh NAMESPACE JOB_NAME
```

This collects events for the TrainJob resource itself and for pods associated
with the job. Events reveal scheduling decisions, image pulls, container
restarts, and other cluster-level activity.

## How to Interpret Training Metrics

- **Loss**: Should decrease over time. A loss that stops decreasing may indicate
  the learning rate is too high or the model has converged. A loss that increases
  may indicate training instability.
- **Learning rate**: Typically starts higher and decreases over training via a
  scheduler. Sudden changes may indicate a warmup phase ending or a scheduler
  step.
- **Epoch / Step**: Use these to estimate how far along training is. Compare
  currentEpoch to totalEpochs for overall progress.
- **Throughput**: Measures training speed. A drop in throughput may indicate
  resource contention or data loading bottlenecks.
- **Gradient norm**: Large gradient norms can indicate exploding gradients. If
  gradient norms are very large, consider enabling gradient clipping or reducing
  the learning rate.
- **Estimated time remaining**: Based on current throughput and remaining steps.
  This is an estimate and may fluctuate.
