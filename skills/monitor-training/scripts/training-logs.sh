#!/usr/bin/env bash
# Get logs from training pods associated with a TrainJob.
#
# Retrieves logs from all pods labeled with the TrainJob name.
#
# Usage: ./training-logs.sh NAMESPACE JOB_NAME [TAIL_LINES]
# Output: JSON with log output from training pods.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

NAMESPACE="${1:-}"
JOB_NAME="${2:-}"
TAIL_LINES="${3:-100}"

if [[ -z "$NAMESPACE" || -z "$JOB_NAME" ]]; then
    die "Usage: $0 NAMESPACE JOB_NAME [TAIL_LINES]"
fi

CLI=$(detect_cli)

# Find pods associated with the TrainJob
PODS=$("$CLI" get pods -n "$NAMESPACE" \
    -l "trainer.kubeflow.org/trainjob-name=$JOB_NAME" \
    -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || true)

if [[ -z "$PODS" ]]; then
    jq -n --arg name "$JOB_NAME" --arg ns "$NAMESPACE" '{
        job_name: $name,
        namespace: $ns,
        pods_found: 0,
        message: "No pods found for this TrainJob. The job may not have started yet or pods may have been cleaned up.",
        logs: []
    }'
    exit 0
fi

# Collect logs from each pod
POD_LOGS="["
FIRST=true
POD_COUNT=0

for POD in $PODS; do
    POD_COUNT=$((POD_COUNT + 1))

    # Get pod phase
    POD_PHASE=$("$CLI" get pod "$POD" -n "$NAMESPACE" \
        -o jsonpath='{.status.phase}' 2>/dev/null || echo "Unknown")

    # Get logs from the pod
    LOG_OUTPUT=$("$CLI" logs -n "$NAMESPACE" "$POD" \
        --tail="$TAIL_LINES" 2>/dev/null || echo "ERROR: Could not retrieve logs for pod $POD")

    if $FIRST; then
        FIRST=false
    else
        POD_LOGS+=","
    fi

    # Escape the log output for JSON embedding
    POD_LOGS+=$(jq -n \
        --arg pod "$POD" \
        --arg phase "$POD_PHASE" \
        --arg logs "$LOG_OUTPUT" \
        --arg tail "$TAIL_LINES" \
        '{
            pod_name: $pod,
            phase: $phase,
            tail_lines: ($tail | tonumber),
            logs: $logs
        }')
done

POD_LOGS+="]"

jq -n \
    --arg name "$JOB_NAME" \
    --arg ns "$NAMESPACE" \
    --argjson count "$POD_COUNT" \
    --argjson pod_logs "$POD_LOGS" \
    '{
        job_name: $name,
        namespace: $ns,
        pods_found: $count,
        logs: $pod_logs
    }'
