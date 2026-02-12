#!/usr/bin/env bash
# Create a TrainJob resource for model fine-tuning.
#
# Generates a TrainJob YAML manifest and applies it to the cluster.
# Supports LoRA, QLoRA, DoRA, and full fine-tuning methods with
# configurable hyperparameters, multi-node training, checkpoint
# storage, and HuggingFace credentials for gated models.
#
# Usage:
#   ./create-training-job.sh <NAMESPACE> <MODEL_ID> <DATASET_ID> <RUNTIME_NAME> [OPTIONS]
#
# Options:
#   --method lora|qlora|dora|full   Fine-tuning method (default: lora)
#   --epochs N                      Number of training epochs (default: 3)
#   --batch-size N                  Per-device batch size (default: 32)
#   --learning-rate RATE            Learning rate (default: 1e-4)
#   --gpus-per-node N               GPUs per node (default: 1)
#   --num-nodes N                   Number of training nodes (default: 1)
#   --checkpoint-pvc PVC_NAME       PVC for checkpoint storage
#   --hf-secret SECRET_NAME         Secret containing HuggingFace token
#   --dry-run                       Print manifest without applying
#
# Output: JSON confirmation or YAML manifest (with --dry-run).

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

# ---- Positional arguments ----

NAMESPACE="${1:-}"
MODEL_ID="${2:-}"
DATASET_ID="${3:-}"
RUNTIME_NAME="${4:-}"

if [[ -z "$NAMESPACE" || -z "$MODEL_ID" || -z "$DATASET_ID" || -z "$RUNTIME_NAME" ]]; then
    cat >&2 <<'USAGE'
Usage: create-training-job.sh <NAMESPACE> <MODEL_ID> <DATASET_ID> <RUNTIME_NAME> [OPTIONS]

Positional arguments:
  NAMESPACE       Kubernetes namespace for the training job
  MODEL_ID        Model identifier (e.g., meta-llama/Llama-2-7b-hf)
  DATASET_ID      Dataset identifier (e.g., tatsu-lab/alpaca)
  RUNTIME_NAME    Name of the ClusterTrainingRuntime to use

Options:
  --method lora|qlora|dora|full   Fine-tuning method (default: lora)
  --epochs N                      Number of training epochs (default: 3)
  --batch-size N                  Per-device batch size (default: 32)
  --learning-rate RATE            Learning rate (default: 1e-4)
  --gpus-per-node N               GPUs per node (default: 1)
  --num-nodes N                   Number of training nodes (default: 1)
  --checkpoint-pvc PVC_NAME       PVC for checkpoint storage
  --hf-secret SECRET_NAME         Secret containing HuggingFace token
  --dry-run                       Print manifest without applying
USAGE
    exit 1
fi

# Consume positional args
shift 4

# ---- Optional flags ----

METHOD="lora"
EPOCHS=3
BATCH_SIZE=32
LEARNING_RATE="1e-4"
GPUS_PER_NODE=1
NUM_NODES=1
CHECKPOINT_PVC=""
HF_SECRET=""
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --method)
            METHOD="$2"
            shift 2
            ;;
        --epochs)
            EPOCHS="$2"
            shift 2
            ;;
        --batch-size)
            BATCH_SIZE="$2"
            shift 2
            ;;
        --learning-rate)
            LEARNING_RATE="$2"
            shift 2
            ;;
        --gpus-per-node)
            GPUS_PER_NODE="$2"
            shift 2
            ;;
        --num-nodes)
            NUM_NODES="$2"
            shift 2
            ;;
        --checkpoint-pvc)
            CHECKPOINT_PVC="$2"
            shift 2
            ;;
        --hf-secret)
            HF_SECRET="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            die "Unknown option: $1"
            ;;
    esac
done

# ---- Validate method ----

case "$METHOD" in
    lora|qlora|dora|full) ;;
    *) die "Invalid method: $METHOD. Must be one of: lora, qlora, dora, full" ;;
esac

CLI=$(detect_cli)

# ---- Generate job name ----

# Sanitize model ID for use in the job name: take the part after '/' and
# convert to lowercase with only alphanumeric chars and hyphens.
MODEL_SHORT=$(echo "$MODEL_ID" | sed 's|.*/||' | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]/-/g' | sed 's/-\+/-/g' | sed 's/^-//;s/-$//')
TIMESTAMP=$(date +%s | tail -c 9)
JOB_NAME="train-${MODEL_SHORT}-${TIMESTAMP}"

# Truncate to 63 characters (Kubernetes name limit)
JOB_NAME="${JOB_NAME:0:63}"
# Ensure it ends with an alphanumeric character
JOB_NAME=$(echo "$JOB_NAME" | sed 's/-$//')

# ---- Build training args ----

TRAINING_ARGS=""
TRAINING_ARGS="    trainingArgs:
      num_train_epochs: ${EPOCHS}
      per_device_train_batch_size: ${BATCH_SIZE}
      learning_rate: ${LEARNING_RATE}"

if [[ "$METHOD" != "full" ]]; then
    TRAINING_ARGS="${TRAINING_ARGS}
      peft_method: ${METHOD}"
fi

if [[ -n "$CHECKPOINT_PVC" ]]; then
    TRAINING_ARGS="${TRAINING_ARGS}
      output_dir: /mnt/${CHECKPOINT_PVC}"
fi

# ---- Build manifest ----

MANIFEST="apiVersion: trainer.kubeflow.org/v1
kind: TrainJob
metadata:
  name: ${JOB_NAME}
  namespace: ${NAMESPACE}
spec:
  modelConfig:
    name: ${MODEL_ID}
  datasetConfig:
    name: ${DATASET_ID}
  trainer:
    numNodes: ${NUM_NODES}
    resourcesPerNode:
      requests:
        nvidia.com/gpu: \"${GPUS_PER_NODE}\"
${TRAINING_ARGS}
  runtimeRef:
    name: ${RUNTIME_NAME}"

# ---- Dry run ----

if $DRY_RUN; then
    echo "$MANIFEST"
    exit 0
fi

# ---- Apply manifest ----

echo "$MANIFEST" | "$CLI" apply -f - 2>&1

# ---- Output confirmation ----

jq -n \
    --arg job_name "$JOB_NAME" \
    --arg namespace "$NAMESPACE" \
    --arg model_id "$MODEL_ID" \
    --arg dataset_id "$DATASET_ID" \
    --arg runtime "$RUNTIME_NAME" \
    --arg method "$METHOD" \
    --argjson epochs "$EPOCHS" \
    --argjson batch_size "$BATCH_SIZE" \
    --arg learning_rate "$LEARNING_RATE" \
    --argjson gpus_per_node "$GPUS_PER_NODE" \
    --argjson num_nodes "$NUM_NODES" \
    '{
        success: true,
        job_name: $job_name,
        namespace: $namespace,
        model_id: $model_id,
        dataset_id: $dataset_id,
        runtime: $runtime,
        method: $method,
        epochs: $epochs,
        batch_size: $batch_size,
        learning_rate: $learning_rate,
        gpus_per_node: $gpus_per_node,
        num_nodes: $num_nodes,
        message: "Training job \($job_name) created. Use the monitor-training skill to track progress."
    }'
