#!/usr/bin/env bash
# Diagnose issues with a workbench (Kubeflow Notebook).
#
# Usage: ./diagnose-workbench.sh NAMESPACE WORKBENCH_NAME
#
# Performs comprehensive diagnostics:
#   - Notebook resource status and conditions
#   - Pod status for the workbench pod
#   - Events for Notebook and pod
#   - Container logs (current and previous if CrashLoopBackOff)
#   - PVC status for mounted volumes
#   - Common issue detection with suggested fixes
#
# Output: JSON with status, issues_detected, suggested_fixes, events,
#         logs_snippet, and related_resources.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

CLI=$(detect_cli)

# ---- Validate inputs ----
NAMESPACE="${1:-}"
WORKBENCH_NAME="${2:-}"

if [[ -z "$NAMESPACE" || -z "$WORKBENCH_NAME" ]]; then
    die "Usage: $0 NAMESPACE WORKBENCH_NAME"
fi

require_namespace "$NAMESPACE"

# ---- Check CRD ----
if ! "$CLI" api-resources --api-group="$NOTEBOOK_GROUP" 2>/dev/null | grep -q "$NOTEBOOK_PLURAL"; then
    die "Notebook CRD not found. Ensure the Kubeflow Notebooks operator is installed."
fi

# ---- Get Notebook resource ----
notebook_json=$("$CLI" get "${NOTEBOOK_PLURAL}.${NOTEBOOK_GROUP}" "$WORKBENCH_NAME" \
    -n "$NAMESPACE" -o json 2>/dev/null || true)

if [[ -z "$notebook_json" ]] || ! echo "$notebook_json" | jq -e '.metadata.name' &>/dev/null; then
    die "Notebook '$WORKBENCH_NAME' not found in namespace '$NAMESPACE'."
fi

# Extract notebook status info
notebook_status=$(echo "$notebook_json" | jq '{
    name: .metadata.name,
    namespace: .metadata.namespace,
    image: (.spec.template.spec.containers[0].image // "unknown"),
    stopped: (.metadata.annotations["kubeflow-resource-stopped"] != null),
    conditions: (.status.conditions // []),
    created: .metadata.creationTimestamp,
    cpu_request: (.spec.template.spec.containers[0].resources.requests.cpu // "not set"),
    memory_request: (.spec.template.spec.containers[0].resources.requests.memory // "not set"),
    gpu_request: (.spec.template.spec.containers[0].resources.requests["nvidia.com/gpu"] // "0")
}')

is_stopped=$(echo "$notebook_status" | jq -r '.stopped')

# ---- Get Pod status ----
# Pod name matches the notebook name with a suffix
pod_json=$("$CLI" get pods -n "$NAMESPACE" \
    -l "notebook-name=$WORKBENCH_NAME" \
    -o json 2>/dev/null || echo '{"items":[]}')

pod_count=$(echo "$pod_json" | jq '.items | length')

pod_status="no_pod"
pod_phase=""
pod_conditions="[]"
container_statuses="[]"
restart_count=0

if [[ "$pod_count" -gt 0 ]]; then
    # Use the first (most recent) pod
    pod_phase=$(echo "$pod_json" | jq -r '.items[0].status.phase // "Unknown"')
    pod_conditions=$(echo "$pod_json" | jq '.items[0].status.conditions // []')
    container_statuses=$(echo "$pod_json" | jq '[.items[0].status.containerStatuses // [] | .[] | {
        name: .name,
        ready: .ready,
        restart_count: .restartCount,
        state: (
            if .state.running != null then "Running"
            elif .state.waiting != null then .state.waiting.reason
            elif .state.terminated != null then .state.terminated.reason
            else "Unknown"
            end
        ),
        state_message: (
            if .state.waiting.message != null then .state.waiting.message
            elif .state.terminated.message != null then .state.terminated.message
            else null
            end
        ),
        last_termination_reason: (.lastState.terminated.reason // null),
        last_termination_exit_code: (.lastState.terminated.exitCode // null)
    }]')
    restart_count=$(echo "$pod_json" | jq '[.items[0].status.containerStatuses // [] | .[].restartCount] | add // 0')
    pod_status="found"
fi

# ---- Get Events ----
# Events for the Notebook resource
notebook_events=$("$CLI" get events -n "$NAMESPACE" \
    --field-selector "involvedObject.name=$WORKBENCH_NAME,involvedObject.kind=Notebook" \
    -o json 2>/dev/null || echo '{"items":[]}')

notebook_events_formatted=$(echo "$notebook_events" | jq '[.items[] | {
    type: .type,
    reason: .reason,
    message: .message,
    last_seen: .lastTimestamp,
    count: (.count // 1)
}] | sort_by(.last_seen) | reverse | .[0:20]')

# Events for pods
pod_events="[]"
if [[ "$pod_count" -gt 0 ]]; then
    pod_name=$(echo "$pod_json" | jq -r '.items[0].metadata.name')
    pod_events_json=$("$CLI" get events -n "$NAMESPACE" \
        --field-selector "involvedObject.name=$pod_name" \
        -o json 2>/dev/null || echo '{"items":[]}')
    pod_events=$(echo "$pod_events_json" | jq '[.items[] | {
        type: .type,
        reason: .reason,
        message: .message,
        last_seen: .lastTimestamp,
        count: (.count // 1)
    }] | sort_by(.last_seen) | reverse | .[0:20]')
fi

# Merge events
all_events=$(jq -n --argjson nb "$notebook_events_formatted" --argjson pod "$pod_events" \
    '($nb + $pod) | sort_by(.last_seen) | reverse | .[0:30]')

# ---- Get Container Logs ----
logs_snippet="null"
previous_logs_snippet="null"

if [[ "$pod_count" -gt 0 ]]; then
    pod_name=$(echo "$pod_json" | jq -r '.items[0].metadata.name')

    # Current logs
    current_logs=$("$CLI" logs "$pod_name" -n "$NAMESPACE" \
        -c "$WORKBENCH_NAME" --tail=100 2>/dev/null || true)
    if [[ -n "$current_logs" ]]; then
        logs_snippet=$(echo "$current_logs" | jq -Rs '.')
    fi

    # Previous logs (if container has restarted)
    if [[ "$restart_count" -gt 0 ]]; then
        prev_logs=$("$CLI" logs "$pod_name" -n "$NAMESPACE" \
            -c "$WORKBENCH_NAME" --previous --tail=100 2>/dev/null || true)
        if [[ -n "$prev_logs" ]]; then
            previous_logs_snippet=$(echo "$prev_logs" | jq -Rs '.')
        fi
    fi
fi

# ---- Check PVC Status ----
pvc_statuses="[]"
pvc_names=$(echo "$notebook_json" | jq -r '.spec.template.spec.volumes[]? | select(.persistentVolumeClaim != null) | .persistentVolumeClaim.claimName')

if [[ -n "$pvc_names" ]]; then
    pvc_list="["
    pvc_first=true
    for pvc_name in $pvc_names; do
        pvc_json=$("$CLI" get pvc "$pvc_name" -n "$NAMESPACE" -o json 2>/dev/null || true)
        if [[ -n "$pvc_json" ]]; then
            pvc_info=$(echo "$pvc_json" | jq '{
                name: .metadata.name,
                phase: .status.phase,
                capacity: (.status.capacity.storage // "unknown"),
                access_modes: .status.accessModes,
                storage_class: (.spec.storageClassName // "default")
            }')
        else
            pvc_info=$(jq -n --arg name "$pvc_name" '{
                name: $name,
                phase: "NotFound",
                capacity: null,
                access_modes: null,
                storage_class: null
            }')
        fi
        if $pvc_first; then
            pvc_first=false
        else
            pvc_list+=","
        fi
        pvc_list+="$pvc_info"
    done
    pvc_list+="]"
    pvc_statuses="$pvc_list"
fi

# ---- Detect Issues ----
issues="[]"
fixes="[]"

# Check if stopped
if [[ "$is_stopped" == "true" ]]; then
    issues=$(echo "$issues" | jq '. + ["Workbench is stopped (kubeflow-resource-stopped annotation is set)"]')
    fixes=$(echo "$fixes" | jq '. + ["Start the workbench by removing the stopped annotation: use the start-workbench.sh script"]')
fi

# Check for no pod when not stopped
if [[ "$is_stopped" == "false" && "$pod_status" == "no_pod" ]]; then
    issues=$(echo "$issues" | jq '. + ["No pod found for the workbench even though it is not stopped"]')
    fixes=$(echo "$fixes" | jq '. + ["Check the Notebooks controller logs for errors creating the pod", "Verify the namespace has sufficient resource quota"]')
fi

# Check container statuses for common issues
if [[ "$pod_count" -gt 0 ]]; then
    # ImagePullBackOff
    has_image_pull=$(echo "$container_statuses" | jq '[.[] | select(.state == "ImagePullBackOff" or .state == "ErrImagePull")] | length')
    if [[ "$has_image_pull" -gt 0 ]]; then
        issues=$(echo "$issues" | jq '. + ["ImagePullBackOff: Cannot pull the container image"]')
        fixes=$(echo "$fixes" | jq '. + [
            "Verify the container image name and tag are correct",
            "Check that image pull secrets are configured in the namespace",
            "Verify network access to the container registry"
        ]')
    fi

    # CrashLoopBackOff
    has_crash_loop=$(echo "$container_statuses" | jq '[.[] | select(.state == "CrashLoopBackOff")] | length')
    if [[ "$has_crash_loop" -gt 0 ]]; then
        issues=$(echo "$issues" | jq '. + ["CrashLoopBackOff: Container is repeatedly crashing"]')
        fixes=$(echo "$fixes" | jq '. + [
            "Check the previous container logs for error messages",
            "Verify the notebook image is compatible with the RHOAI version",
            "Check that required environment variables and volume mounts are configured"
        ]')
    fi

    # OOMKilled
    has_oom=$(echo "$container_statuses" | jq '[.[] | select(.last_termination_reason == "OOMKilled")] | length')
    if [[ "$has_oom" -gt 0 ]]; then
        issues=$(echo "$issues" | jq '. + ["OOMKilled: Container exceeded memory limits"]')
        fixes=$(echo "$fixes" | jq '. + [
            "Increase the memory limit for the workbench",
            "Reduce memory usage in the notebook (close unused kernels, reduce dataset size)"
        ]')
    fi

    # FailedScheduling (check events)
    has_scheduling=$(echo "$all_events" | jq '[.[] | select(.reason == "FailedScheduling")] | length')
    if [[ "$has_scheduling" -gt 0 ]]; then
        scheduling_msg=$(echo "$all_events" | jq -r '[.[] | select(.reason == "FailedScheduling")][0].message // "unknown"')
        issues=$(echo "$issues" | jq --arg msg "$scheduling_msg" '. + ["FailedScheduling: " + $msg]')
        fixes=$(echo "$fixes" | jq '. + [
            "Check cluster resource availability with the explore-cluster skill",
            "Reduce CPU or memory requests for the workbench",
            "If requesting GPUs, verify GPU availability on the cluster"
        ]')
    fi

    # FailedMount (check events)
    has_mount=$(echo "$all_events" | jq '[.[] | select(.reason == "FailedMount" or .reason == "FailedAttachVolume")] | length')
    if [[ "$has_mount" -gt 0 ]]; then
        mount_msg=$(echo "$all_events" | jq -r '[.[] | select(.reason == "FailedMount" or .reason == "FailedAttachVolume")][0].message // "unknown"')
        issues=$(echo "$issues" | jq --arg msg "$mount_msg" '. + ["FailedMount: " + $msg]')
        fixes=$(echo "$fixes" | jq '. + [
            "Verify the PVC exists and is in Bound state",
            "Check that the PVC is not already mounted by another pod (if using ReadWriteOnce)",
            "Ensure the storage class is available and can provision volumes"
        ]')
    fi

    # Pending pod
    if [[ "$pod_phase" == "Pending" ]]; then
        has_known_issue=$(echo "$issues" | jq 'length')
        if [[ "$has_known_issue" -eq 0 || ("$has_scheduling" -eq 0 && "$has_mount" -eq 0) ]]; then
            issues=$(echo "$issues" | jq '. + ["Pod is in Pending state"]')
            fixes=$(echo "$fixes" | jq '. + ["Check events for scheduling or resource errors", "Verify resource quotas in the namespace"]')
        fi
    fi
fi

# Check PVC issues
pvc_not_found=$(echo "$pvc_statuses" | jq '[.[] | select(.phase == "NotFound")] | length')
if [[ "$pvc_not_found" -gt 0 ]]; then
    missing_pvcs=$(echo "$pvc_statuses" | jq -r '[.[] | select(.phase == "NotFound") | .name] | join(", ")')
    issues=$(echo "$issues" | jq --arg pvcs "$missing_pvcs" '. + ["PVC not found: " + $pvcs]')
    fixes=$(echo "$fixes" | jq '. + ["Create the missing PVC or recreate the workbench"]')
fi

pvc_not_bound=$(echo "$pvc_statuses" | jq '[.[] | select(.phase != "Bound" and .phase != "NotFound")] | length')
if [[ "$pvc_not_bound" -gt 0 ]]; then
    issues=$(echo "$issues" | jq '. + ["PVC is not in Bound state"]')
    fixes=$(echo "$fixes" | jq '. + ["Check the storage class and provisioner", "Verify storage quota in the namespace"]')
fi

# Determine overall status
overall_status="unknown"
if [[ "$is_stopped" == "true" ]]; then
    overall_status="stopped"
elif [[ "$pod_status" == "no_pod" ]]; then
    overall_status="no_pod"
elif [[ "$pod_phase" == "Running" ]]; then
    has_ready=$(echo "$container_statuses" | jq '[.[] | select(.ready == true)] | length')
    total_containers=$(echo "$container_statuses" | jq 'length')
    if [[ "$has_ready" -eq "$total_containers" && "$total_containers" -gt 0 ]]; then
        overall_status="healthy"
    else
        overall_status="degraded"
    fi
elif [[ "$pod_phase" == "Pending" ]]; then
    overall_status="pending"
else
    overall_status="error"
fi

# ---- Build Output ----
jq -n \
    --arg status "$overall_status" \
    --argjson notebook_info "$notebook_status" \
    --arg pod_phase "$pod_phase" \
    --argjson container_statuses "$container_statuses" \
    --argjson restart_count "$restart_count" \
    --argjson issues "$issues" \
    --argjson fixes "$fixes" \
    --argjson events "$all_events" \
    --argjson logs_snippet "$logs_snippet" \
    --argjson previous_logs "$previous_logs_snippet" \
    --argjson pvcs "$pvc_statuses" \
    '{
        status: $status,
        notebook: $notebook_info,
        pod: {
            phase: $pod_phase,
            container_statuses: $container_statuses,
            total_restarts: $restart_count
        },
        issues_detected: $issues,
        suggested_fixes: $fixes,
        events: $events,
        logs_snippet: $logs_snippet,
        previous_logs: $previous_logs,
        related_resources: {
            pvcs: $pvcs
        }
    }'
