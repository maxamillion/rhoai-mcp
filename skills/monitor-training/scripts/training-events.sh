#!/usr/bin/env bash
# Get Kubernetes events related to a TrainJob and its pods.
#
# Collects events for both the TrainJob resource and any associated pods.
#
# Usage: ./training-events.sh NAMESPACE JOB_NAME
# Output: JSON with job events and pod events.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

NAMESPACE="${1:-}"
JOB_NAME="${2:-}"

if [[ -z "$NAMESPACE" || -z "$JOB_NAME" ]]; then
    die "Usage: $0 NAMESPACE JOB_NAME"
fi

CLI=$(detect_cli)

# Get events for the TrainJob resource itself
JOB_EVENTS=$("$CLI" get events -n "$NAMESPACE" \
    --field-selector "involvedObject.name=$JOB_NAME" \
    -o json 2>/dev/null || echo '{"items":[]}')

JOB_EVENTS_FORMATTED=$(echo "$JOB_EVENTS" | jq '[.items[] | {
    type: .type,
    reason: .reason,
    message: .message,
    source: (.source.component // "unknown"),
    first_seen: .firstTimestamp,
    last_seen: .lastTimestamp,
    count: (.count // 1),
    involved_object: .involvedObject.name
}]')

# Find pods associated with the TrainJob and get their events
PODS=$("$CLI" get pods -n "$NAMESPACE" \
    -l "trainer.kubeflow.org/trainjob-name=$JOB_NAME" \
    -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || true)

POD_EVENTS="[]"
if [[ -n "$PODS" ]]; then
    # Collect events for all training pods
    ALL_POD_EVENTS="["
    FIRST=true

    for POD in $PODS; do
        EVENTS=$("$CLI" get events -n "$NAMESPACE" \
            --field-selector "involvedObject.name=$POD" \
            -o json 2>/dev/null || echo '{"items":[]}')

        FORMATTED=$(echo "$EVENTS" | jq '[.items[] | {
            type: .type,
            reason: .reason,
            message: .message,
            source: (.source.component // "unknown"),
            first_seen: .firstTimestamp,
            last_seen: .lastTimestamp,
            count: (.count // 1),
            involved_object: .involvedObject.name
        }]')

        # Merge into array
        if $FIRST; then
            FIRST=false
        else
            ALL_POD_EVENTS+=","
        fi
        ALL_POD_EVENTS+="$FORMATTED"
    done

    ALL_POD_EVENTS+="]"
    # Flatten the nested arrays
    POD_EVENTS=$(echo "$ALL_POD_EVENTS" | jq '[.[][]]')
fi

# Combine and output
jq -n \
    --arg name "$JOB_NAME" \
    --arg ns "$NAMESPACE" \
    --argjson job_events "$JOB_EVENTS_FORMATTED" \
    --argjson pod_events "$POD_EVENTS" \
    '{
        job_name: $name,
        namespace: $ns,
        job_events: $job_events,
        job_event_count: ($job_events | length),
        pod_events: $pod_events,
        pod_event_count: ($pod_events | length),
        warnings: [($job_events + $pod_events)[] | select(.type == "Warning")],
        warning_count: [($job_events + $pod_events)[] | select(.type == "Warning")] | length
    }'
