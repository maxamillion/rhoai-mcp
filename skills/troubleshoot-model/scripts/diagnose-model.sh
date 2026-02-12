#!/usr/bin/env bash
# Diagnose issues with a model deployment (KServe InferenceService).
#
# Usage: ./diagnose-model.sh NAMESPACE MODEL_NAME
#
# Performs comprehensive diagnostics:
#   - InferenceService status and conditions
#   - Predictor pod status
#   - Events for InferenceService and pods
#   - Container logs from predictor pods
#   - Serving runtime existence check
#   - Storage URI accessibility check
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
MODEL_NAME="${2:-}"

if [[ -z "$NAMESPACE" || -z "$MODEL_NAME" ]]; then
    die "Usage: $0 NAMESPACE MODEL_NAME"
fi

require_namespace "$NAMESPACE"

# ---- Check CRD ----
if ! "$CLI" api-resources --api-group="$INFERENCE_SERVICE_GROUP" 2>/dev/null | grep -q "$INFERENCE_SERVICE_PLURAL"; then
    die "InferenceService CRD not found. Ensure KServe is installed."
fi

# ---- Get InferenceService ----
isvc_json=$("$CLI" get "${INFERENCE_SERVICE_PLURAL}.${INFERENCE_SERVICE_GROUP}" "$MODEL_NAME" \
    -n "$NAMESPACE" -o json 2>/dev/null || true)

if [[ -z "$isvc_json" ]] || ! echo "$isvc_json" | jq -e '.metadata.name' &>/dev/null; then
    die "InferenceService '$MODEL_NAME' not found in namespace '$NAMESPACE'."
fi

# Extract InferenceService status info
isvc_status=$(echo "$isvc_json" | jq '{
    name: .metadata.name,
    namespace: .metadata.namespace,
    runtime: (
        .spec.predictor.model.runtime //
        .metadata.annotations["serving.kserve.io/deploymentMode"] //
        null
    ),
    model_format: (
        .spec.predictor.model.modelFormat.name //
        null
    ),
    storage_uri: (
        .spec.predictor.model.storageUri //
        .spec.predictor.model.storage.path //
        null
    ),
    ready: (
        [(.status.conditions // [])[] | select(.type == "Ready")] |
        if length > 0 then .[0].status == "True" else false end
    ),
    conditions: (.status.conditions // []),
    url: (.status.url // null),
    created: .metadata.creationTimestamp,
    min_replicas: (.spec.predictor.minReplicas // 1),
    max_replicas: (.spec.predictor.maxReplicas // 1)
}')

is_ready=$(echo "$isvc_status" | jq -r '.ready')

# ---- Get Predictor Pods ----
# KServe predictor pods are labeled with the InferenceService name
pod_json=$("$CLI" get pods -n "$NAMESPACE" \
    -l "serving.kserve.io/inferenceservice=$MODEL_NAME" \
    -o json 2>/dev/null || echo '{"items":[]}')

pod_count=$(echo "$pod_json" | jq '.items | length')

pod_phase=""
container_statuses="[]"
restart_count=0

if [[ "$pod_count" -gt 0 ]]; then
    # Use the most recent pod
    pod_phase=$(echo "$pod_json" | jq -r '.items | sort_by(.metadata.creationTimestamp) | last | .status.phase // "Unknown"')
    container_statuses=$(echo "$pod_json" | jq '[.items | sort_by(.metadata.creationTimestamp) | last | .status.containerStatuses // [] | .[] | {
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
    restart_count=$(echo "$pod_json" | jq '[.items | sort_by(.metadata.creationTimestamp) | last | .status.containerStatuses // [] | .[].restartCount] | add // 0')
fi

# Also check init container statuses
init_container_statuses="[]"
if [[ "$pod_count" -gt 0 ]]; then
    init_container_statuses=$(echo "$pod_json" | jq '[.items | sort_by(.metadata.creationTimestamp) | last | .status.initContainerStatuses // [] | .[] | {
        name: .name,
        ready: .ready,
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
        )
    }]')
fi

# ---- Get Events ----
# Events for the InferenceService
isvc_events=$("$CLI" get events -n "$NAMESPACE" \
    --field-selector "involvedObject.name=$MODEL_NAME" \
    -o json 2>/dev/null || echo '{"items":[]}')

isvc_events_formatted=$(echo "$isvc_events" | jq '[.items[] | {
    type: .type,
    reason: .reason,
    message: .message,
    last_seen: .lastTimestamp,
    count: (.count // 1)
}] | sort_by(.last_seen) | reverse | .[0:20]')

# Events for predictor pods
pod_events="[]"
if [[ "$pod_count" -gt 0 ]]; then
    pod_name=$(echo "$pod_json" | jq -r '.items | sort_by(.metadata.creationTimestamp) | last | .metadata.name')
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
all_events=$(jq -n --argjson isvc "$isvc_events_formatted" --argjson pod "$pod_events" \
    '($isvc + $pod) | sort_by(.last_seen) | reverse | .[0:30]')

# ---- Get Container Logs ----
logs_snippet="null"
previous_logs_snippet="null"

if [[ "$pod_count" -gt 0 ]]; then
    pod_name=$(echo "$pod_json" | jq -r '.items | sort_by(.metadata.creationTimestamp) | last | .metadata.name')

    # Try to get logs from the main serving container
    # KServe containers are typically named "kserve-container" or match the runtime
    container_name=$("$CLI" get pod "$pod_name" -n "$NAMESPACE" \
        -o jsonpath='{.spec.containers[0].name}' 2>/dev/null || echo "kserve-container")

    current_logs=$("$CLI" logs "$pod_name" -n "$NAMESPACE" \
        -c "$container_name" --tail=100 2>/dev/null || true)
    if [[ -n "$current_logs" ]]; then
        logs_snippet=$(echo "$current_logs" | jq -Rs '.')
    fi

    # Previous logs if container has restarted
    if [[ "$restart_count" -gt 0 ]]; then
        prev_logs=$("$CLI" logs "$pod_name" -n "$NAMESPACE" \
            -c "$container_name" --previous --tail=100 2>/dev/null || true)
        if [[ -n "$prev_logs" ]]; then
            previous_logs_snippet=$(echo "$prev_logs" | jq -Rs '.')
        fi
    fi
fi

# ---- Check Serving Runtime ----
runtime_name=$(echo "$isvc_json" | jq -r '.spec.predictor.model.runtime // empty')
runtime_status="null"

if [[ -n "$runtime_name" ]]; then
    # Check namespace-scoped ServingRuntime
    sr_json=$("$CLI" get "servingruntimes.serving.kserve.io" "$runtime_name" \
        -n "$NAMESPACE" -o json 2>/dev/null || true)
    if [[ -n "$sr_json" ]] && echo "$sr_json" | jq -e '.metadata.name' &>/dev/null; then
        runtime_status=$(echo "$sr_json" | jq '{
            name: .metadata.name,
            found: true,
            scope: "namespace",
            supported_formats: [.spec.supportedModelFormats[]?.name] | unique
        }')
    else
        # Check cluster-scoped ClusterServingRuntime
        csr_json=$("$CLI" get "clusterservingruntimes.serving.kserve.io" "$runtime_name" \
            -o json 2>/dev/null || true)
        if [[ -n "$csr_json" ]] && echo "$csr_json" | jq -e '.metadata.name' &>/dev/null; then
            runtime_status=$(echo "$csr_json" | jq '{
                name: .metadata.name,
                found: true,
                scope: "cluster",
                supported_formats: [.spec.supportedModelFormats[]?.name] | unique
            }')
        else
            runtime_status=$(jq -n --arg name "$runtime_name" '{
                name: $name,
                found: false,
                scope: null,
                supported_formats: []
            }')
        fi
    fi
fi

# ---- Check Storage URI ----
storage_uri=$(echo "$isvc_json" | jq -r '.spec.predictor.model.storageUri // .spec.predictor.model.storage.path // empty')
storage_status="null"

if [[ -n "$storage_uri" ]]; then
    if [[ "$storage_uri" == pvc://* ]]; then
        # Extract PVC name from pvc://pvc-name/path
        pvc_name=$(echo "$storage_uri" | sed 's|pvc://||' | cut -d'/' -f1)
        pvc_json=$("$CLI" get pvc "$pvc_name" -n "$NAMESPACE" -o json 2>/dev/null || true)
        if [[ -n "$pvc_json" ]] && echo "$pvc_json" | jq -e '.metadata.name' &>/dev/null; then
            storage_status=$(echo "$pvc_json" | jq --arg uri "$storage_uri" '{
                uri: $uri,
                type: "pvc",
                pvc_name: .metadata.name,
                pvc_phase: .status.phase,
                pvc_capacity: (.status.capacity.storage // "unknown"),
                accessible: (.status.phase == "Bound")
            }')
        else
            storage_status=$(jq -n --arg uri "$storage_uri" --arg pvc "$pvc_name" '{
                uri: $uri,
                type: "pvc",
                pvc_name: $pvc,
                pvc_phase: "NotFound",
                pvc_capacity: null,
                accessible: false
            }')
        fi
    elif [[ "$storage_uri" == s3://* ]]; then
        # Check for data connection secrets
        s3_secrets=$("$CLI" get secrets -n "$NAMESPACE" \
            -l "opendatahub.io/dashboard=true" -o json 2>/dev/null || echo '{"items":[]}')
        s3_count=$(echo "$s3_secrets" | jq '[.items[] | select(.metadata.annotations["opendatahub.io/connection-type"] != null)] | length')
        storage_status=$(jq -n --arg uri "$storage_uri" --argjson count "$s3_count" '{
            uri: $uri,
            type: "s3",
            data_connections_found: $count,
            accessible: ($count > 0)
        }')
    else
        storage_status=$(jq -n --arg uri "$storage_uri" '{
            uri: $uri,
            type: "other",
            accessible: null
        }')
    fi
fi

# ---- Detect Issues ----
issues="[]"
fixes="[]"

# Check if not ready
if [[ "$is_ready" != "true" ]]; then
    # Check specific condition reasons
    not_ready_reason=$(echo "$isvc_status" | jq -r '[.conditions[] | select(.type == "Ready" and .status != "True")] | if length > 0 then .[0].message // "Unknown reason" else "No Ready condition found" end')
    issues=$(echo "$issues" | jq --arg reason "$not_ready_reason" '. + ["Model not ready: " + $reason]')
fi

# No pods found
if [[ "$pod_count" -eq 0 && "$is_ready" != "true" ]]; then
    issues=$(echo "$issues" | jq '. + ["No predictor pods found for the InferenceService"]')
    fixes=$(echo "$fixes" | jq '. + [
        "Check that the serving runtime exists and is correctly configured",
        "Verify the InferenceService spec is valid",
        "Check the KServe controller logs for errors"
    ]')
fi

if [[ "$pod_count" -gt 0 ]]; then
    # ImagePullBackOff
    has_image_pull=$(echo "$container_statuses" | jq '[.[] | select(.state == "ImagePullBackOff" or .state == "ErrImagePull")] | length')
    init_image_pull=$(echo "$init_container_statuses" | jq '[.[] | select(.state == "ImagePullBackOff" or .state == "ErrImagePull")] | length')
    if [[ "$has_image_pull" -gt 0 || "$init_image_pull" -gt 0 ]]; then
        issues=$(echo "$issues" | jq '. + ["ImagePullBackOff: Cannot pull the container image"]')
        fixes=$(echo "$fixes" | jq '. + [
            "Verify the serving runtime container image exists and is accessible",
            "Check that image pull secrets are configured in the namespace",
            "Verify network access to the container registry",
            "For custom serving runtimes, ensure the image reference is correct"
        ]')
    fi

    # CrashLoopBackOff
    has_crash_loop=$(echo "$container_statuses" | jq '[.[] | select(.state == "CrashLoopBackOff")] | length')
    if [[ "$has_crash_loop" -gt 0 ]]; then
        issues=$(echo "$issues" | jq '. + ["CrashLoopBackOff: Predictor container is repeatedly crashing"]')
        fixes=$(echo "$fixes" | jq '. + [
            "Check container logs for error messages",
            "Verify the model format matches the serving runtime supported formats",
            "Ensure the model artifacts are not corrupted",
            "Check that required environment variables are set"
        ]')
    fi

    # OOMKilled
    has_oom=$(echo "$container_statuses" | jq '[.[] | select(.last_termination_reason == "OOMKilled")] | length')
    if [[ "$has_oom" -gt 0 ]]; then
        issues=$(echo "$issues" | jq '. + ["OOMKilled: Predictor container exceeded memory limits"]')
        fixes=$(echo "$fixes" | jq '. + [
            "Increase memory limits for the InferenceService",
            "Use a quantized version of the model (GPTQ, AWQ)",
            "Consider using a GPU with more memory",
            "For vLLM, adjust --max-model-len to reduce memory usage"
        ]')
    fi

    # FailedScheduling
    has_scheduling=$(echo "$all_events" | jq '[.[] | select(.reason == "FailedScheduling")] | length')
    if [[ "$has_scheduling" -gt 0 ]]; then
        scheduling_msg=$(echo "$all_events" | jq -r '[.[] | select(.reason == "FailedScheduling")][0].message // "unknown"')
        issues=$(echo "$issues" | jq --arg msg "$scheduling_msg" '. + ["FailedScheduling: " + $msg]')
        fixes=$(echo "$fixes" | jq '. + [
            "Check GPU availability with the explore-cluster skill",
            "Reduce the number of requested GPUs",
            "Verify the GPU resource name matches what the cluster provides (nvidia.com/gpu)",
            "Check node taints and tolerations for GPU nodes"
        ]')
    fi

    # Pending pod
    if [[ "$pod_phase" == "Pending" ]]; then
        has_known_issue=$(echo "$issues" | jq '[.[] | test("FailedScheduling|ImagePull")] | any')
        if [[ "$has_known_issue" != "true" ]]; then
            issues=$(echo "$issues" | jq '. + ["Pod is in Pending state"]')
            fixes=$(echo "$fixes" | jq '. + ["Check events for scheduling or resource errors", "Verify resource quotas in the namespace"]')
        fi
    fi
fi

# Check serving runtime
if [[ "$runtime_status" != "null" ]]; then
    runtime_found=$(echo "$runtime_status" | jq -r '.found')
    if [[ "$runtime_found" == "false" ]]; then
        issues=$(echo "$issues" | jq --arg name "$runtime_name" '. + ["Serving runtime not found: " + $name]')
        fixes=$(echo "$fixes" | jq '. + [
            "List available serving runtimes with the browse-models skill",
            "Create or instantiate the required serving runtime in the namespace",
            "Verify the runtime name in the InferenceService matches an existing runtime"
        ]')
    fi
fi

# Check storage
if [[ "$storage_status" != "null" ]]; then
    storage_accessible=$(echo "$storage_status" | jq -r '.accessible // "null"')
    if [[ "$storage_accessible" == "false" ]]; then
        storage_type=$(echo "$storage_status" | jq -r '.type')
        if [[ "$storage_type" == "pvc" ]]; then
            issues=$(echo "$issues" | jq '. + ["Storage PVC is not accessible"]')
            fixes=$(echo "$fixes" | jq '. + [
                "Verify the PVC exists and is in Bound state",
                "Check that model files exist at the specified path in the PVC"
            ]')
        elif [[ "$storage_type" == "s3" ]]; then
            issues=$(echo "$issues" | jq '. + ["No data connection secrets found for S3 storage"]')
            fixes=$(echo "$fixes" | jq '. + [
                "Create a data connection with valid S3 credentials in the namespace",
                "Verify the S3 endpoint is reachable from the cluster"
            ]')
        fi
    fi
fi

# Check for storage errors in logs
if [[ "$logs_snippet" != "null" ]]; then
    storage_error_in_logs=$(echo "$logs_snippet" | jq -r '.' | grep -ci "model not found\|access denied\|no such file\|storage error\|bucket.*not.*exist" || true)
    if [[ "$storage_error_in_logs" -gt 0 ]]; then
        issues=$(echo "$issues" | jq '. + ["Storage access errors detected in container logs"]')
        fixes=$(echo "$fixes" | jq '. + [
            "Verify the model path within the storage location is correct",
            "Check storage credentials and permissions",
            "Ensure the model artifacts exist at the specified location"
        ]')
    fi
fi

# Determine overall status
overall_status="unknown"
if [[ "$is_ready" == "true" ]]; then
    overall_status="healthy"
elif [[ "$pod_count" -eq 0 ]]; then
    overall_status="no_pods"
elif [[ "$pod_phase" == "Pending" ]]; then
    overall_status="pending"
elif [[ "$pod_phase" == "Running" ]]; then
    overall_status="degraded"
else
    overall_status="error"
fi

# ---- Build Output ----
jq -n \
    --arg status "$overall_status" \
    --argjson isvc_info "$isvc_status" \
    --arg pod_phase "$pod_phase" \
    --argjson pod_count "$pod_count" \
    --argjson container_statuses "$container_statuses" \
    --argjson init_container_statuses "$init_container_statuses" \
    --argjson restart_count "$restart_count" \
    --argjson issues "$issues" \
    --argjson fixes "$fixes" \
    --argjson events "$all_events" \
    --argjson logs_snippet "$logs_snippet" \
    --argjson previous_logs "$previous_logs_snippet" \
    --argjson runtime "$runtime_status" \
    --argjson storage "$storage_status" \
    '{
        status: $status,
        inference_service: $isvc_info,
        pod: {
            count: $pod_count,
            phase: $pod_phase,
            container_statuses: $container_statuses,
            init_container_statuses: $init_container_statuses,
            total_restarts: $restart_count
        },
        issues_detected: $issues,
        suggested_fixes: $fixes,
        events: $events,
        logs_snippet: $logs_snippet,
        previous_logs: $previous_logs,
        related_resources: {
            serving_runtime: $runtime,
            storage: $storage
        }
    }'
