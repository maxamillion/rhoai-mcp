#!/usr/bin/env bash
# Analyze OOM (Out of Memory) errors for a training job.
#
# Checks pod events for OOMKilled, scans logs for CUDA OOM patterns,
# extracts current resource configuration, and outputs recommendations.
#
# Usage: ./analyze-oom.sh NAMESPACE JOB_NAME
# Output: JSON with oom_detected, oom_type, events, log_excerpts,
#         current_config, and recommendations.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

NAMESPACE="${1:-}"
JOB_NAME="${2:-}"

if [[ -z "$NAMESPACE" || -z "$JOB_NAME" ]]; then
    die "Usage: $0 NAMESPACE JOB_NAME"
fi

CLI=$(detect_cli)

# Verify namespace exists
require_namespace "$NAMESPACE"

# ---- Check pod events for OOMKilled ----

OOM_EVENTS=$("$CLI" get events -n "$NAMESPACE" \
    --field-selector reason=OOMKilling \
    -o json 2>/dev/null || echo '{"items":[]}')

OOM_EVENTS_FORMATTED=$(echo "$OOM_EVENTS" | jq '[.items[] | {
    type: .type,
    reason: .reason,
    message: .message,
    count: (.count // 1),
    involved_object: .involvedObject.name,
    timestamp: (.lastTimestamp // .eventTime // "unknown")
}]')

# ---- Get pods for this training job ----

PODS_JSON=$("$CLI" get pods -n "$NAMESPACE" \
    -l "trainer.kubeflow.org/trainjob-name=$JOB_NAME" \
    -o json 2>/dev/null || echo '{"items":[]}')

POD_NAMES=$(echo "$PODS_JSON" | jq -r '.items[].metadata.name // empty' 2>/dev/null)

# Check container statuses for OOMKilled
SYSTEM_OOM_DETECTED=false
POD_OOM_EVENTS="[]"

for POD in $POD_NAMES; do
    # Check current and last container states for OOMKilled
    POD_OOM=$(echo "$PODS_JSON" | jq --arg pod "$POD" '[
        .items[] | select(.metadata.name == $pod) |
        .status.containerStatuses // [] | .[] |
        select(
            (.state.terminated.reason == "OOMKilled") or
            (.lastState.terminated.reason == "OOMKilled")
        ) | {
            pod: $pod,
            container: .name,
            reason: (
                if .state.terminated.reason == "OOMKilled" then "OOMKilled (current)"
                else "OOMKilled (previous)"
                end
            ),
            exit_code: (.state.terminated.exitCode // .lastState.terminated.exitCode // null)
        }
    ]')

    if [[ $(echo "$POD_OOM" | jq 'length') -gt 0 ]]; then
        SYSTEM_OOM_DETECTED=true
        POD_OOM_EVENTS=$(echo "$POD_OOM_EVENTS $POD_OOM" | jq -s '.[0] + .[1]')
    fi

    # Also get events specific to each pod
    POD_EVENTS=$("$CLI" get events -n "$NAMESPACE" \
        --field-selector "involvedObject.name=$POD,reason=OOMKilling" \
        -o json 2>/dev/null || echo '{"items":[]}')

    POD_EVENTS_COUNT=$(echo "$POD_EVENTS" | jq '.items | length')
    if [[ "$POD_EVENTS_COUNT" -gt 0 ]]; then
        SYSTEM_OOM_DETECTED=true
    fi
done

# ---- Check training logs for CUDA OOM patterns ----

CUDA_OOM_DETECTED=false
LOG_EXCERPTS="[]"

if [[ -n "$POD_NAMES" ]]; then
    LOGS=$("$CLI" logs -n "$NAMESPACE" \
        -l "trainer.kubeflow.org/trainjob-name=$JOB_NAME" \
        --tail=500 2>/dev/null || echo "")

    PREV_LOGS=$("$CLI" logs -n "$NAMESPACE" \
        -l "trainer.kubeflow.org/trainjob-name=$JOB_NAME" \
        --tail=500 --previous 2>/dev/null || echo "")

    ALL_LOGS="$LOGS"$'\n'"$PREV_LOGS"

    # Scan for CUDA OOM patterns
    CUDA_PATTERNS="OutOfMemoryError|CUDA out of memory|torch.cuda.OutOfMemoryError"

    MATCHING_LINES=$(echo "$ALL_LOGS" | grep -iE "$CUDA_PATTERNS" 2>/dev/null | head -20 || true)

    if [[ -n "$MATCHING_LINES" ]]; then
        CUDA_OOM_DETECTED=true
        # Convert matching lines to JSON array
        LOG_EXCERPTS=$(echo "$MATCHING_LINES" | jq -R -s 'split("\n") | map(select(length > 0))')
    fi
fi

# ---- Determine OOM type ----

OOM_DETECTED=false
OOM_TYPE="none"

if [[ "$SYSTEM_OOM_DETECTED" == "true" && "$CUDA_OOM_DETECTED" == "true" ]]; then
    OOM_DETECTED=true
    OOM_TYPE="both"
elif [[ "$SYSTEM_OOM_DETECTED" == "true" ]]; then
    OOM_DETECTED=true
    OOM_TYPE="system"
elif [[ "$CUDA_OOM_DETECTED" == "true" ]]; then
    OOM_DETECTED=true
    OOM_TYPE="cuda"
fi

# ---- Extract current job configuration ----

CURRENT_CONFIG=$(echo "$PODS_JSON" | jq '{
    pods: [.items[] | {
        name: .metadata.name,
        containers: [.spec.containers[] | {
            name: .name,
            resources: {
                requests: (.resources.requests // {}),
                limits: (.resources.limits // {})
            },
            env_training_args: [
                (.env // [])[] |
                select(.name | test("BATCH_SIZE|GRADIENT|LEARNING_RATE|METHOD"; "i")) |
                {(.name): .value}
            ]
        }]
    }]
}')

# ---- Build recommendations ----

RECOMMENDATIONS="[]"

if [[ "$OOM_TYPE" == "cuda" || "$OOM_TYPE" == "both" ]]; then
    RECOMMENDATIONS=$(echo "$RECOMMENDATIONS" | jq '. + [
        {
            "priority": 1,
            "action": "Reduce batch size",
            "description": "Lower per_device_train_batch_size and increase gradient_accumulation_steps to maintain effective batch size."
        },
        {
            "priority": 2,
            "action": "Enable gradient checkpointing",
            "description": "Set gradient_checkpointing=true to trade compute time for GPU memory."
        },
        {
            "priority": 3,
            "action": "Switch from LoRA to QLoRA",
            "description": "Use 4-bit quantization (load_in_4bit=True) to reduce base model memory by ~33%."
        },
        {
            "priority": 4,
            "action": "Add more GPUs",
            "description": "Increase GPU count to distribute memory across devices using data or model parallelism."
        },
        {
            "priority": 5,
            "action": "Use a smaller model",
            "description": "Consider a smaller model variant (e.g., 7B instead of 13B) if other mitigations are insufficient."
        }
    ]')
fi

if [[ "$OOM_TYPE" == "system" || "$OOM_TYPE" == "both" ]]; then
    RECOMMENDATIONS=$(echo "$RECOMMENDATIONS" | jq '. + [
        {
            "priority": 6,
            "action": "Increase container memory limits",
            "description": "The container was OOMKilled by Kubernetes. Increase resources.limits.memory in the pod spec or training runtime."
        }
    ]')
fi

if [[ "$OOM_TYPE" == "none" ]]; then
    RECOMMENDATIONS=$(echo "$RECOMMENDATIONS" | jq '. + [
        {
            "priority": 1,
            "action": "No OOM detected",
            "description": "No OOM signals found in events or logs. The job may have failed for a different reason. Use the troubleshoot-training skill for broader diagnosis."
        }
    ]')
fi

# Sort recommendations by priority
RECOMMENDATIONS=$(echo "$RECOMMENDATIONS" | jq 'sort_by(.priority)')

# ---- Assemble output ----

jq -n \
    --arg job_name "$JOB_NAME" \
    --arg namespace "$NAMESPACE" \
    --argjson oom_detected "$OOM_DETECTED" \
    --arg oom_type "$OOM_TYPE" \
    --argjson events "$OOM_EVENTS_FORMATTED" \
    --argjson pod_oom_events "$POD_OOM_EVENTS" \
    --argjson log_excerpts "$LOG_EXCERPTS" \
    --argjson current_config "$CURRENT_CONFIG" \
    --argjson recommendations "$RECOMMENDATIONS" \
    '{
        job_name: $job_name,
        namespace: $namespace,
        oom_detected: $oom_detected,
        oom_type: $oom_type,
        events: $events,
        pod_oom_events: $pod_oom_events,
        log_excerpts: $log_excerpts,
        current_config: $current_config,
        recommendations: $recommendations
    }'
