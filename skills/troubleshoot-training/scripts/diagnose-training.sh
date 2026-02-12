#!/usr/bin/env bash
# Comprehensive diagnosis of a TrainJob to identify failure causes.
#
# Checks TrainJob status, events, logs, and scans for common failure patterns
# such as OOMKilled, ImagePullBackOff, FailedScheduling, and CrashLoopBackOff.
#
# Usage: ./diagnose-training.sh NAMESPACE JOB_NAME
# Output: JSON with status, issues detected, suggested fixes, events, and logs.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

NAMESPACE="${1:-}"
JOB_NAME="${2:-}"

if [[ -z "$NAMESPACE" || -z "$JOB_NAME" ]]; then
    die "Usage: $0 NAMESPACE JOB_NAME"
fi

CLI=$(detect_cli)

# ---- Gather TrainJob status ----

TRAINJOB_JSON=$("$CLI" get "${TRAINJOB_PLURAL}.${TRAINJOB_GROUP}" "$JOB_NAME" \
    -n "$NAMESPACE" -o json 2>/dev/null) || die "TrainJob '$JOB_NAME' not found in namespace '$NAMESPACE'."

JOB_STATUS=$(echo "$TRAINJOB_JSON" | jq '{
    name: .metadata.name,
    namespace: .metadata.namespace,
    suspend: (.spec.suspend // false),
    conditions: (.status.conditions // []),
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
    )
}')

# ---- Gather events ----

JOB_EVENTS=$("$CLI" get events -n "$NAMESPACE" \
    --field-selector "involvedObject.name=$JOB_NAME" \
    -o json 2>/dev/null || echo '{"items":[]}')

JOB_EVENTS_FORMATTED=$(echo "$JOB_EVENTS" | jq '[.items[] | {
    type: .type,
    reason: .reason,
    message: .message,
    count: (.count // 1)
}]')

# ---- Gather pod information ----

PODS_JSON=$("$CLI" get pods -n "$NAMESPACE" \
    -l "trainer.kubeflow.org/trainjob-name=$JOB_NAME" \
    -o json 2>/dev/null || echo '{"items":[]}')

POD_STATUSES=$(echo "$PODS_JSON" | jq '[.items[] | {
    name: .metadata.name,
    phase: .status.phase,
    container_statuses: [(.status.containerStatuses // [])[] | {
        name: .name,
        ready: .ready,
        restart_count: .restartCount,
        state: (
            if .state.waiting then
                {status: "Waiting", reason: .state.waiting.reason, message: (.state.waiting.message // null)}
            elif .state.terminated then
                {status: "Terminated", reason: .state.terminated.reason, exit_code: .state.terminated.exitCode, message: (.state.terminated.message // null)}
            elif .state.running then
                {status: "Running", started_at: .state.running.startedAt}
            else
                {status: "Unknown"}
            end
        ),
        last_state: (
            if .lastState.terminated then
                {reason: .lastState.terminated.reason, exit_code: .lastState.terminated.exitCode, message: (.lastState.terminated.message // null)}
            else
                null
            end
        )
    }]
}]')

# Gather pod events
POD_NAMES=$(echo "$PODS_JSON" | jq -r '.items[].metadata.name // empty' 2>/dev/null)
ALL_POD_EVENTS="[]"

if [[ -n "$POD_NAMES" ]]; then
    COMBINED="["
    FIRST=true
    for POD in $POD_NAMES; do
        EVENTS=$("$CLI" get events -n "$NAMESPACE" \
            --field-selector "involvedObject.name=$POD" \
            -o json 2>/dev/null || echo '{"items":[]}')

        FORMATTED=$(echo "$EVENTS" | jq '[.items[] | {
            type: .type,
            reason: .reason,
            message: .message,
            count: (.count // 1),
            pod: .involvedObject.name
        }]')

        if $FIRST; then
            FIRST=false
        else
            COMBINED+=","
        fi
        COMBINED+="$FORMATTED"
    done
    COMBINED+="]"
    ALL_POD_EVENTS=$(echo "$COMBINED" | jq '[.[][]]')
fi

# ---- Gather logs ----

LOGS_SNIPPET=""
PREVIOUS_LOGS_SNIPPET=""

if [[ -n "$POD_NAMES" ]]; then
    # Get current logs (last 50 lines)
    LOGS_SNIPPET=$("$CLI" logs -n "$NAMESPACE" \
        -l "trainer.kubeflow.org/trainjob-name=$JOB_NAME" \
        --tail=50 2>/dev/null || echo "No current logs available")

    # Get previous container logs (useful for CrashLoopBackOff)
    PREVIOUS_LOGS_SNIPPET=$("$CLI" logs -n "$NAMESPACE" \
        -l "trainer.kubeflow.org/trainjob-name=$JOB_NAME" \
        --tail=50 --previous 2>/dev/null || echo "No previous logs available")
fi

# ---- Detect issues ----

# Combine all events and statuses into a single string to scan for patterns
ALL_TEXT=$(echo "$JOB_EVENTS_FORMATTED $ALL_POD_EVENTS $POD_STATUSES $LOGS_SNIPPET $PREVIOUS_LOGS_SNIPPET")

ISSUES="[]"
FIXES="[]"

# Check for OOMKilled
if echo "$ALL_TEXT" | grep -qi "OOMKilled\|OutOfMemory\|CUDA out of memory\|out of memory"; then
    ISSUES=$(echo "$ISSUES" | jq '. + ["OOMKilled: Container or GPU ran out of memory"]')
    FIXES=$(echo "$FIXES" | jq '. + [
        "Reduce per_device_train_batch_size in training configuration",
        "Enable gradient checkpointing (gradient_checkpointing: true)",
        "Switch from full fine-tuning to LoRA or QLoRA",
        "Use a GPU with more memory (e.g., A100-80GB instead of A100-40GB)",
        "Run: python3 scripts/analyze-oom.py --namespace NAMESPACE --job-name JOB_NAME for detailed analysis"
    ]')
fi

# Check for ImagePullBackOff
if echo "$ALL_TEXT" | grep -qi "ImagePullBackOff\|ErrImagePull\|ImagePullError"; then
    ISSUES=$(echo "$ISSUES" | jq '. + ["ImagePullBackOff: Container image could not be pulled"]')
    FIXES=$(echo "$FIXES" | jq '. + [
        "Verify the container image name and tag are correct",
        "Check that image pull secrets are configured in the namespace",
        "Verify network access to the container registry",
        "For private registries, ensure credentials are up to date"
    ]')
fi

# Check for FailedScheduling
if echo "$ALL_TEXT" | grep -qi "FailedScheduling\|Unschedulable\|Insufficient nvidia.com/gpu\|Insufficient memory\|Insufficient cpu"; then
    ISSUES=$(echo "$ISSUES" | jq '. + ["FailedScheduling: Pod could not be scheduled due to resource constraints"]')
    FIXES=$(echo "$FIXES" | jq '. + [
        "Check GPU availability with the explore-cluster skill",
        "Reduce the number of requested GPUs or memory",
        "Wait for other workloads to complete and free resources",
        "Check node taints and tolerations match the pod spec"
    ]')
fi

# Check for CrashLoopBackOff
if echo "$ALL_TEXT" | grep -qi "CrashLoopBackOff\|BackOff"; then
    ISSUES=$(echo "$ISSUES" | jq '. + ["CrashLoopBackOff: Container is repeatedly crashing on startup"]')
    FIXES=$(echo "$FIXES" | jq '. + [
        "Check logs from the previous container run for error messages",
        "Verify the training script and entry point are correct",
        "Check that required environment variables and volume mounts are configured",
        "Ensure the training dataset is accessible from the pod"
    ]')
fi

# If no issues detected
if [[ $(echo "$ISSUES" | jq 'length') -eq 0 ]]; then
    CURRENT_STATUS=$(echo "$JOB_STATUS" | jq -r '.status')
    if [[ "$CURRENT_STATUS" == "Completed" ]]; then
        ISSUES=$(echo "$ISSUES" | jq '. + ["No issues detected. Job completed successfully."]')
    elif [[ "$CURRENT_STATUS" == "Running" ]]; then
        ISSUES=$(echo "$ISSUES" | jq '. + ["No issues detected. Job is currently running."]')
    elif [[ "$CURRENT_STATUS" == "Suspended" ]]; then
        ISSUES=$(echo "$ISSUES" | jq '. + ["Job is suspended. Use resume-training skill to resume."]')
    else
        ISSUES=$(echo "$ISSUES" | jq '. + ["No common failure patterns detected. Review events and logs manually."]')
    fi
fi

# ---- Assemble output ----

jq -n \
    --argjson job_status "$JOB_STATUS" \
    --argjson pod_statuses "$POD_STATUSES" \
    --argjson issues "$ISSUES" \
    --argjson fixes "$FIXES" \
    --argjson job_events "$JOB_EVENTS_FORMATTED" \
    --argjson pod_events "$ALL_POD_EVENTS" \
    --arg logs "$LOGS_SNIPPET" \
    --arg previous_logs "$PREVIOUS_LOGS_SNIPPET" \
    '{
        job_status: $job_status,
        pod_statuses: $pod_statuses,
        issues_detected: $issues,
        suggested_fixes: $fixes,
        events: {
            job_events: $job_events,
            pod_events: $pod_events
        },
        logs_snippet: $logs,
        previous_logs_snippet: $previous_logs
    }'
