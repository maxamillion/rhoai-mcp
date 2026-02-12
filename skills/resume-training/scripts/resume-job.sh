#!/usr/bin/env bash
# Resume a suspended TrainJob by patching spec.suspend to false.
#
# Usage: ./resume-job.sh NAMESPACE JOB_NAME
# Output: JSON with the result of the resume operation.

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

# Check if the job is actually suspended
IS_SUSPENDED=$(echo "$TRAINJOB_JSON" | jq -r '.spec.suspend // false')

if [[ "$IS_SUSPENDED" != "true" ]]; then
    # Check if there's a Suspended condition
    SUSPENDED_CONDITION=$(echo "$TRAINJOB_JSON" | jq -r '
        .status.conditions // [] | map(select(.type == "Suspended" and .status == "True")) | length')

    if [[ "$SUSPENDED_CONDITION" == "0" ]]; then
        echo "$TRAINJOB_JSON" | jq '{
            job_name: .metadata.name,
            namespace: .metadata.namespace,
            action: "resume",
            success: false,
            message: "TrainJob is not suspended. Current spec.suspend is false.",
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
fi

# Patch the TrainJob to resume
PATCH_RESULT=$("$CLI" patch "${TRAINJOB_PLURAL}.${TRAINJOB_GROUP}" "$JOB_NAME" \
    -n "$NAMESPACE" \
    --type merge \
    -p '{"spec":{"suspend":false}}' 2>&1) || die "Failed to patch TrainJob: $PATCH_RESULT"

# Verify the patch was applied
UPDATED_JSON=$("$CLI" get "${TRAINJOB_PLURAL}.${TRAINJOB_GROUP}" "$JOB_NAME" \
    -n "$NAMESPACE" -o json 2>/dev/null)

echo "$UPDATED_JSON" | jq '{
    job_name: .metadata.name,
    namespace: .metadata.namespace,
    action: "resume",
    success: true,
    message: "TrainJob resumed successfully. spec.suspend set to false.",
    suspend: (.spec.suspend // false),
    current_status: (
        if .status.conditions then
            (.status.conditions | sort_by(.lastTransitionTime) | last | .type + "=" + .status)
        else
            "Pending"
        end
    )
}'
