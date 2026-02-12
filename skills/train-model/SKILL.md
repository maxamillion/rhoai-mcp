---
name: train-model
description: Fine-tune a model with LoRA/QLoRA/DoRA on Red Hat OpenShift AI. Use when the user wants to train, fine-tune, or adapt a model on their RHOAI cluster.
license: Apache-2.0
compatibility: Requires oc or kubectl, jq, and python3. Needs an OpenShift cluster with RHOAI and the Kubeflow Training Operator installed.
metadata:
  author: Red Hat
  version: "1.0"
  category: training
---

# Train a Model on RHOAI

Fine-tune a model using LoRA, QLoRA, DoRA, or full parameter fine-tuning on
Red Hat OpenShift AI. This skill walks through resource estimation, prerequisite
validation, runtime selection, and TrainJob creation on a cluster with the
Kubeflow Training Operator.

## Prerequisites

- `oc` or `kubectl` authenticated to an OpenShift cluster with RHOAI
- `jq` for JSON processing
- `python3` for resource estimation
- Kubeflow Training Operator installed (TrainJob CRD available)

## Workflow

### Step 1: Estimate Resources

Run the resource estimation script to determine GPU and memory requirements
for the chosen model and fine-tuning method:

```bash
python3 scripts/estimate-resources.py --model-id <MODEL_ID> --method <lora|qlora|dora|full>
```

This outputs a JSON object with estimated GPU memory, recommended GPU count and
type, and storage requirements. Review the output to ensure the cluster has
sufficient capacity before proceeding.

### Step 2: Check Prerequisites

Verify that the cluster has the required resources, CRDs, and configuration:

```bash
bash scripts/check-prerequisites.sh <NAMESPACE> <MODEL_ID> <DATASET_ID>
```

To also validate a checkpoint PVC:

```bash
bash scripts/check-prerequisites.sh <NAMESPACE> <MODEL_ID> <DATASET_ID> <CHECKPOINT_PVC>
```

This checks cluster connectivity, GPU availability, the TrainJob CRD, training
runtimes, model/dataset ID format, and optional PVC status.

### Step 3: List Available Runtimes

Find a training runtime to use for the job:

```bash
bash scripts/list-training-runtimes.sh
```

To also include namespace-scoped runtimes:

```bash
bash scripts/list-training-runtimes.sh <NAMESPACE>
```

This lists ClusterTrainingRuntimes and optionally TrainingRuntimes within a
namespace, showing the name, framework, and initializer capabilities.

### Step 4: Create Training Job

Create the TrainJob resource on the cluster:

```bash
bash scripts/create-training-job.sh <NAMESPACE> <MODEL_ID> <DATASET_ID> <RUNTIME_NAME> [OPTIONS]
```

Options for create-training-job.sh:
- `--method lora|qlora|dora|full` (default: lora)
- `--epochs N` (default: 3)
- `--batch-size N` (default: 32)
- `--learning-rate RATE` (default: 1e-4)
- `--gpus-per-node N` (default: 1)
- `--num-nodes N` (default: 1)
- `--checkpoint-pvc PVC_NAME`
- `--hf-secret SECRET_NAME` (for gated models)
- `--dry-run` (preview without creating)

### Step 5: Monitor Progress

Use the monitor-training skill to track progress.

## Common Fine-Tuning Methods

- **LoRA**: Low-Rank Adaptation - adds trainable adapter layers (~1.8x base memory)
- **QLoRA**: Quantized LoRA - 4-bit quantization reduces memory (~1.2x base memory)
- **DoRA**: Weight-Decomposed LoRA - similar to LoRA with direction component (~1.8x base memory)
- **Full**: Full parameter fine-tuning - most memory intensive (~4x base memory)

## GPU Memory Guide

| Model Size | Full FT | LoRA | QLoRA |
|-----------|---------|------|-------|
| 1-3B      | 24 GB   | 11 GB| 7 GB  |
| 7B        | 56 GB   | 25 GB| 17 GB |
| 13B       | 104 GB  | 47 GB| 31 GB |
| 70B       | 320 GB  | 144 GB| 96 GB|

## Notes

- **Gated models** (e.g., Llama) require a HuggingFace token. Create a secret
  with the token before training and pass it with `--hf-secret`.
- **Multi-node training** distributes the workload across nodes. Use
  `--num-nodes` and `--gpus-per-node` to control the topology.
- **Checkpointing** saves intermediate model state to a PVC. Use
  `--checkpoint-pvc` to enable this so training can be resumed if interrupted.
- **Dry run** mode (`--dry-run`) outputs the TrainJob YAML without applying it,
  which is useful for review or version control.
