#!/usr/bin/env bash
# Get a quick snapshot of active workloads across the cluster.
#
# Lists running workbenches (Notebook CRs), active training jobs (TrainJob CRs),
# and deployed models (InferenceService CRs) across all namespaces.
#
# Usage: ./whats-running.sh
# Output: JSON object with workbenches, training_jobs, models, and summary.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

CLI=$(detect_cli)
check_auth

# ---- Check which CRDs are available ----

HAS_NOTEBOOKS=false
if "$CLI" api-resources --api-group="$NOTEBOOK_GROUP" 2>/dev/null | grep -q "$NOTEBOOK_PLURAL"; then
    HAS_NOTEBOOKS=true
fi

HAS_ISVC=false
if "$CLI" api-resources --api-group="$INFERENCE_SERVICE_GROUP" 2>/dev/null | grep -q "$INFERENCE_SERVICE_PLURAL"; then
    HAS_ISVC=true
fi

HAS_TRAINJOBS=false
if "$CLI" api-resources --api-group="$TRAINJOB_GROUP" 2>/dev/null | grep -q "$TRAINJOB_PLURAL"; then
    HAS_TRAINJOBS=true
fi

# ---- Collect workbenches ----

WORKBENCHES_JSON="[]"
if $HAS_NOTEBOOKS; then
    WORKBENCHES_JSON=$("$CLI" get "${NOTEBOOK_PLURAL}.${NOTEBOOK_GROUP}" \
        --all-namespaces -o json 2>/dev/null \
        | jq '[.items[] | {
            name: .metadata.name,
            namespace: .metadata.namespace,
            status: (
                if .status.conditions then
                    (.status.conditions | map(select(.type == "Ready")) | first | .status // "Unknown")
                else
                    "Unknown"
                end
            )
        }]' 2>/dev/null || echo "[]")
fi

# ---- Collect training jobs ----

TRAINING_JOBS_JSON="[]"
if $HAS_TRAINJOBS; then
    TRAINING_JOBS_JSON=$("$CLI" get "${TRAINJOB_PLURAL}.${TRAINJOB_GROUP}" \
        --all-namespaces -o json 2>/dev/null \
        | jq '[.items[] | {
            name: .metadata.name,
            namespace: .metadata.namespace,
            status: (
                if .status.conditions then
                    (.status.conditions | last | .type // "Unknown")
                else
                    "Unknown"
                end
            )
        }]' 2>/dev/null || echo "[]")
fi

# ---- Collect deployed models ----

MODELS_JSON="[]"
if $HAS_ISVC; then
    MODELS_JSON=$("$CLI" get "${INFERENCE_SERVICE_PLURAL}.${INFERENCE_SERVICE_GROUP}" \
        --all-namespaces -o json 2>/dev/null \
        | jq '[.items[] | {
            name: .metadata.name,
            namespace: .metadata.namespace,
            ready: (
                if .status.conditions then
                    (.status.conditions | map(select(.type == "Ready")) | first | .status == "True")
                else
                    false
                end
            )
        }]' 2>/dev/null || echo "[]")
fi

# ---- Build summary and output ----

jq -n \
    --argjson workbenches "$WORKBENCHES_JSON" \
    --argjson training_jobs "$TRAINING_JOBS_JSON" \
    --argjson models "$MODELS_JSON" \
    '{
        workbenches: $workbenches,
        training_jobs: $training_jobs,
        models: $models,
        summary: {
            total_workbenches: ($workbenches | length),
            total_training_jobs: ($training_jobs | length),
            total_models: ($models | length)
        }
    }'
