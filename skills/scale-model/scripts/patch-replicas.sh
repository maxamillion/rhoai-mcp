#!/usr/bin/env bash
# Scale a model deployment by patching InferenceService replicas.
#
# Updates the minReplicas and maxReplicas on the InferenceService predictor
# spec. Supports scale-to-zero (minReplicas=0) and horizontal scaling.
#
# Usage: ./patch-replicas.sh <NAMESPACE> <MODEL_NAME> <MIN_REPLICAS> [MAX_REPLICAS]
#
# If MAX_REPLICAS is omitted, it defaults to MIN_REPLICAS.
#
# Output: JSON confirmation with previous and new replica settings.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

# ---- Argument validation ----
NAMESPACE="${1:-}"
MODEL_NAME="${2:-}"
MIN_REPLICAS="${3:-}"
MAX_REPLICAS="${4:-$MIN_REPLICAS}"

if [[ -z "$NAMESPACE" || -z "$MODEL_NAME" || -z "$MIN_REPLICAS" ]]; then
    die "Usage: $0 <NAMESPACE> <MODEL_NAME> <MIN_REPLICAS> [MAX_REPLICAS]"
fi

# Validate replica values are non-negative integers
if ! [[ "$MIN_REPLICAS" =~ ^[0-9]+$ ]]; then
    die "MIN_REPLICAS must be a non-negative integer, got: $MIN_REPLICAS"
fi

if ! [[ "$MAX_REPLICAS" =~ ^[0-9]+$ ]]; then
    die "MAX_REPLICAS must be a non-negative integer, got: $MAX_REPLICAS"
fi

if [[ "$MAX_REPLICAS" -lt "$MIN_REPLICAS" ]]; then
    die "MAX_REPLICAS ($MAX_REPLICAS) must be >= MIN_REPLICAS ($MIN_REPLICAS)"
fi

CLI=$(detect_cli)

# ---- Get current replica settings ----
ISVC_JSON=$("$CLI" get inferenceservices.serving.kserve.io "$MODEL_NAME" \
    -n "$NAMESPACE" -o json 2>/dev/null)

if [[ -z "$ISVC_JSON" ]]; then
    jq -n \
        --arg name "$MODEL_NAME" \
        --arg namespace "$NAMESPACE" \
        '{
            "error": "InferenceService not found",
            "name": $name,
            "namespace": $namespace
        }'
    exit 1
fi

PREV_MIN=$(echo "$ISVC_JSON" | jq -r '.spec.predictor.minReplicas // 1')
PREV_MAX=$(echo "$ISVC_JSON" | jq -r '.spec.predictor.maxReplicas // 1')

# ---- Patch replicas ----
PATCH_JSON="{\"spec\":{\"predictor\":{\"minReplicas\":${MIN_REPLICAS},\"maxReplicas\":${MAX_REPLICAS}}}}"

if ! "$CLI" patch inferenceservices.serving.kserve.io "$MODEL_NAME" \
    -n "$NAMESPACE" --type merge -p "$PATCH_JSON" 2>&1; then
    die "Failed to patch InferenceService replicas"
fi

# ---- Output confirmation ----
jq -n \
    --arg name "$MODEL_NAME" \
    --arg namespace "$NAMESPACE" \
    --argjson prev_min "$PREV_MIN" \
    --argjson prev_max "$PREV_MAX" \
    --argjson new_min "$MIN_REPLICAS" \
    --argjson new_max "$MAX_REPLICAS" \
    '{
        "patched": true,
        "name": $name,
        "namespace": $namespace,
        "previous": {
            "min_replicas": $prev_min,
            "max_replicas": $prev_max
        },
        "current": {
            "min_replicas": $new_min,
            "max_replicas": $new_max
        },
        "message": (
            if $new_min == 0 then "Scale-to-zero enabled. Model will terminate when idle and restart on demand."
            elif $new_min > $prev_min then "Scaled up. New replicas may take a few minutes to become ready."
            elif $new_min < $prev_min then "Scaled down. Excess replicas will be terminated."
            else "Replica configuration updated."
            end
        )
    }'
