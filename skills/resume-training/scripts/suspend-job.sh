#!/usr/bin/env bash
# Suspend a running TrainJob by patching spec.suspend to true.
#
# Usage: ./suspend-job.sh NAMESPACE JOB_NAME
# Output: JSON with the result of the suspend operation.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

NAMESPACE="${1:-}"
JOB_NAME="${2:-}"

if [[ -z "$NAMESPACE" || -z "$JOB_NAME" ]]; then
    die "Usage: $0 NAMESPACE JOB_NAME"
fi

CLI=$(detect_cli)

# Verify the TrainJob exists
TRAINJOB_JSON=$("$CLI" get "${TRAINJOB_PLURAL}.${TRAINJOB_GROUP}" "$JOB_NAME" \
    -n "$NAMESPACE" -o json 2>/dev/null) || die "TrainJob '$JOB_NAME' not found in namespace '$NAMESPACE'."

# Check if the job is already suspended
IS_SUSPENDED=$(echo "$TRAINJOB_JSON" | jq -r '.spec.suspend // false')

if [[ "$IS_SUSPENDED" == "true" ]]; then
    echo "$TRAINJOB_JSON" | jq '{
        job_name: .metadata.name,
        namespace: .metadata.namespace,
        action: "suspend",
        success: false,
        message: "TrainJob is already suspended.",
        current_status: (
            if .status.conditions then
                (.status.conditions | sort_by(.lastTransitionTime) | last | .type + "=" + .status)
            else
                "Unknown"
            end
        )
    }'
    exit 0
fi

# Patch the TrainJob to suspend
PATCH_RESULT=$("$CLI" patch "${TRAINJOB_PLURAL}.${TRAINJOB_GROUP}" "$JOB_NAME" \
    -n "$NAMESPACE" \
    --type merge \
    -p '{"spec":{"suspend":true}}' 2>&1) || die "Failed to patch TrainJob: $PATCH_RESULT"

# Verify the patch was applied
UPDATED_JSON=$("$CLI" get "${TRAINJOB_PLURAL}.${TRAINJOB_GROUP}" "$JOB_NAME" \
    -n "$NAMESPACE" -o json 2>/dev/null)

echo "$UPDATED_JSON" | jq '{
    job_name: .metadata.name,
    namespace: .metadata.namespace,
    action: "suspend",
    success: true,
    message: "TrainJob suspended successfully. spec.suspend set to true. Training pods will be terminated.",
    suspend: (.spec.suspend // false),
    current_status: (
        if .status.conditions then
            (.status.conditions | sort_by(.lastTransitionTime) | last | .type + "=" + .status)
        else
            "Suspending"
        end
    )
}'
