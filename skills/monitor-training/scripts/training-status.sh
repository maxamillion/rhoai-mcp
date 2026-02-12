#!/usr/bin/env bash
# Get the current status and conditions of a TrainJob.
#
# Extracts the job name, status from conditions, model/dataset identifiers,
# and creation time.
#
# Usage: ./training-status.sh NAMESPACE JOB_NAME
# Output: JSON with job status information.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

NAMESPACE="${1:-}"
JOB_NAME="${2:-}"

if [[ -z "$NAMESPACE" || -z "$JOB_NAME" ]]; then
    die "Usage: $0 NAMESPACE JOB_NAME"
fi

CLI=$(detect_cli)

# Get the TrainJob resource
TRAINJOB_JSON=$("$CLI" get "${TRAINJOB_PLURAL}.${TRAINJOB_GROUP}" "$JOB_NAME" \
    -n "$NAMESPACE" -o json 2>/dev/null) || die "TrainJob '$JOB_NAME' not found in namespace '$NAMESPACE'."

# Extract status from the TrainJob using jq
echo "$TRAINJOB_JSON" | jq '{
    name: .metadata.name,
    namespace: .metadata.namespace,
    status: (
        if .status.conditions then
            (.status.conditions | sort_by(.lastTransitionTime) | last |
                if .type == "Complete" and .status == "True" then "Completed"
                elif .type == "Failed" and .status == "True" then "Failed"
                elif .type == "Suspended" and .status == "True" then "Suspended"
                elif .type == "Created" and .status == "True" then "Running"
                else .type + "=" + .status
                end
            )
        else
            "Unknown"
        end
    ),
    conditions: (.status.conditions // []),
    suspend: (.spec.suspend // false),
    model_id: (
        .spec.modelConfig.name //
        .spec.labels["trainer.kubeflow.org/model-id"] //
        .metadata.labels["trainer.kubeflow.org/model-id"] //
        null
    ),
    dataset_id: (
        .spec.datasetConfig.name //
        .spec.labels["trainer.kubeflow.org/dataset-id"] //
        .metadata.labels["trainer.kubeflow.org/dataset-id"] //
        null
    ),
    runtime: (
        .spec.trainingRuntimeRef.name // null
    ),
    created: .metadata.creationTimestamp
}'
