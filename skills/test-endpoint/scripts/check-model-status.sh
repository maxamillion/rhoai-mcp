#!/usr/bin/env bash
# Get detailed status of a deployed model's InferenceService.
#
# Retrieves conditions, replica info, runtime, model format, and storage
# details for comprehensive status reporting.
#
# Usage: ./check-model-status.sh <NAMESPACE> <MODEL_NAME>
# Output: JSON with detailed model status.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

# ---- Argument validation ----
NAMESPACE="${1:-}"
MODEL_NAME="${2:-}"

if [[ -z "$NAMESPACE" || -z "$MODEL_NAME" ]]; then
    die "Usage: $0 <NAMESPACE> <MODEL_NAME>"
fi

CLI=$(detect_cli)

# ---- Get InferenceService ----
ISVC_JSON=$("$CLI" get inferenceservices.serving.kserve.io "$MODEL_NAME" \
    -n "$NAMESPACE" -o json 2>/dev/null)

if [[ -z "$ISVC_JSON" ]]; then
    jq -n \
        --arg name "$MODEL_NAME" \
        --arg namespace "$NAMESPACE" \
        '{
            "name": $name,
            "namespace": $namespace,
            "ready": false,
            "error": "InferenceService not found"
        }'
    exit 1
fi

# ---- Extract detailed status ----
echo "$ISVC_JSON" | jq '{
    "name": .metadata.name,
    "namespace": .metadata.namespace,
    "ready": (
        (.status.conditions // []) |
        map(select(.type == "Ready")) |
        if length > 0 then .[0].status == "True"
        else false
        end
    ),
    "conditions": [
        (.status.conditions // [])[] |
        {
            "type": .type,
            "status": .status,
            "reason": (.reason // null),
            "message": (.message // null),
            "last_transition": (.lastTransitionTime // null)
        }
    ],
    "replicas": {
        "min_replicas": (.spec.predictor.minReplicas // 1),
        "max_replicas": (.spec.predictor.maxReplicas // 1)
    },
    "runtime": (.spec.predictor.model.runtime // null),
    "model_format": (.spec.predictor.model.modelFormat.name // null),
    "storage_uri": (.spec.predictor.model.storageUri // null)
}'
