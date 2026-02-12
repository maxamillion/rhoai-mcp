#!/usr/bin/env bash
# Check training prerequisites before creating a TrainJob.
#
# Validates cluster connectivity, GPU availability, required CRDs,
# training runtimes, model/dataset ID format, and optional PVC.
#
# Usage: ./check-prerequisites.sh <NAMESPACE> <MODEL_ID> <DATASET_ID> [CHECKPOINT_PVC]
# Output: JSON with a checks array and overall pass/fail status.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

# ---- Argument validation ----

NAMESPACE="${1:-}"
MODEL_ID="${2:-}"
DATASET_ID="${3:-}"
CHECKPOINT_PVC="${4:-}"

if [[ -z "$NAMESPACE" || -z "$MODEL_ID" || -z "$DATASET_ID" ]]; then
    cat >&2 <<'USAGE'
Usage: check-prerequisites.sh <NAMESPACE> <MODEL_ID> <DATASET_ID> [CHECKPOINT_PVC]

Arguments:
  NAMESPACE       Kubernetes namespace for the training job
  MODEL_ID        Model identifier (e.g., meta-llama/Llama-2-7b-hf)
  DATASET_ID      Dataset identifier (e.g., tatsu-lab/alpaca)
  CHECKPOINT_PVC  (optional) PVC name for checkpoint storage
USAGE
    exit 1
fi

CLI=$(detect_cli)

# ---- Helpers ----

CHECKS="[]"
ALL_PASSED=true

add_check() {
    local name="$1"
    local passed="$2"
    local message="$3"

    CHECKS=$(echo "$CHECKS" | jq \
        --arg name "$name" \
        --argjson passed "$passed" \
        --arg message "$message" \
        '. + [{"name": $name, "passed": $passed, "message": $message}]')

    if [[ "$passed" == "false" ]]; then
        ALL_PASSED=false
    fi
}

# ---- Check 1: Cluster connectivity ----

if "$CLI" cluster-info &>/dev/null 2>&1; then
    add_check "Cluster connectivity" true "Connected to cluster"
else
    add_check "Cluster connectivity" false "Cannot connect to cluster. Run '$CLI login' or check KUBECONFIG."
fi

# ---- Check 2: GPU availability ----

GPU_COUNT=0
NODES_JSON=$("$CLI" get nodes -o json 2>/dev/null || echo '{"items":[]}')

if echo "$NODES_JSON" | jq empty 2>/dev/null; then
    GPU_COUNT=$(echo "$NODES_JSON" | jq '
        [.items[] |
            (.status.allocatable // {} | .["nvidia.com/gpu"] // "0" | tonumber)
        ] | add // 0
    ')
fi

if [[ "$GPU_COUNT" -gt 0 ]]; then
    add_check "GPU availability" true "$GPU_COUNT GPU(s) found in cluster"
else
    add_check "GPU availability" false "No GPUs detected in cluster nodes (nvidia.com/gpu)"
fi

# ---- Check 3: TrainJob CRD ----

if "$CLI" api-resources --api-group="$TRAINJOB_GROUP" 2>/dev/null | grep -q "$TRAINJOB_PLURAL"; then
    add_check "TrainJob CRD" true "TrainJob CRD ($TRAINJOB_PLURAL.$TRAINJOB_GROUP) is available"
else
    add_check "TrainJob CRD" false "TrainJob CRD not found. Install the Kubeflow Training Operator."
fi

# ---- Check 4: Training runtimes ----

RUNTIME_COUNT=0
if "$CLI" api-resources --api-group="$CLUSTER_TRAINING_RUNTIME_GROUP" 2>/dev/null \
    | grep -q "$CLUSTER_TRAINING_RUNTIME_PLURAL"; then

    CTR_JSON=$("$CLI" get \
        "${CLUSTER_TRAINING_RUNTIME_PLURAL}.${CLUSTER_TRAINING_RUNTIME_GROUP}" \
        -o json 2>/dev/null || echo '{"items":[]}')
    RUNTIME_COUNT=$(echo "$CTR_JSON" | jq '.items | length')
fi

if [[ "$RUNTIME_COUNT" -gt 0 ]]; then
    add_check "Training runtimes" true "$RUNTIME_COUNT ClusterTrainingRuntime(s) available"
else
    add_check "Training runtimes" false "No ClusterTrainingRuntimes found. Create one before training."
fi

# ---- Check 5: Model ID format ----

if echo "$MODEL_ID" | grep -q '/'; then
    add_check "Model ID format" true "Model ID '$MODEL_ID' is in org/name format"
else
    add_check "Model ID format" false "Model ID '$MODEL_ID' should contain '/' (e.g., org/model-name)"
fi

# ---- Check 6: Dataset ID format ----

if echo "$DATASET_ID" | grep -q '/'; then
    add_check "Dataset ID format" true "Dataset ID '$DATASET_ID' is in org/name format"
else
    add_check "Dataset ID format" false "Dataset ID '$DATASET_ID' should contain '/' (e.g., org/dataset-name)"
fi

# ---- Check 7: Namespace exists ----

if "$CLI" get namespace "$NAMESPACE" &>/dev/null 2>&1; then
    add_check "Namespace" true "Namespace '$NAMESPACE' exists"
else
    add_check "Namespace" false "Namespace '$NAMESPACE' not found"
fi

# ---- Check 8: Checkpoint PVC (optional) ----

if [[ -n "$CHECKPOINT_PVC" ]]; then
    PVC_JSON=$("$CLI" get pvc "$CHECKPOINT_PVC" -n "$NAMESPACE" -o json 2>/dev/null || echo "")
    if [[ -n "$PVC_JSON" ]]; then
        PVC_PHASE=$(echo "$PVC_JSON" | jq -r '.status.phase // "Unknown"')
        if [[ "$PVC_PHASE" == "Bound" ]]; then
            add_check "Checkpoint PVC" true "PVC '$CHECKPOINT_PVC' is Bound"
        else
            add_check "Checkpoint PVC" false "PVC '$CHECKPOINT_PVC' exists but is in phase: $PVC_PHASE"
        fi
    else
        add_check "Checkpoint PVC" false "PVC '$CHECKPOINT_PVC' not found in namespace '$NAMESPACE'"
    fi
fi

# ---- Output ----

jq -n \
    --argjson all_passed "$ALL_PASSED" \
    --argjson checks "$CHECKS" \
    '{
        all_passed: $all_passed,
        checks: $checks,
        ready_to_train: $all_passed
    }'
