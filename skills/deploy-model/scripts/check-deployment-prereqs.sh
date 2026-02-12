#!/usr/bin/env bash
# Pre-flight checks before deploying a model as an InferenceService.
#
# Validates namespace existence, serving runtime compatibility, storage
# accessibility, and GPU availability.
#
# Usage: ./check-deployment-prereqs.sh <NAMESPACE> <MODEL_FORMAT> <STORAGE_URI>
# Output: JSON with checks array and overall pass/fail.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

# ---- Argument validation ----
NAMESPACE="${1:-}"
MODEL_FORMAT="${2:-}"
STORAGE_URI="${3:-}"

if [[ -z "$NAMESPACE" || -z "$MODEL_FORMAT" || -z "$STORAGE_URI" ]]; then
    die "Usage: $0 <NAMESPACE> <MODEL_FORMAT> <STORAGE_URI>"
fi

CLI=$(detect_cli)

CHECKS="[]"
ALL_PASSED=true

add_check() {
    local name="$1"
    local passed="$2"
    local message="$3"
    CHECKS=$(echo "$CHECKS" | jq \
        --arg name "$name" \
        --argjson passed "$passed" \
        --arg message "$message" \
        '. + [{"name": $name, "passed": $passed, "message": $message}]')
    if [[ "$passed" == "false" ]]; then
        ALL_PASSED=false
    fi
}

# ---- Check 1: Namespace exists ----
if "$CLI" get namespace "$NAMESPACE" &>/dev/null 2>&1; then
    add_check "namespace" "true" "Namespace '$NAMESPACE' exists"
else
    add_check "namespace" "false" "Namespace '$NAMESPACE' not found"
fi

# ---- Check 2: Serving runtime supports model format ----
HAS_SERVING_RUNTIME=false
if "$CLI" api-resources --api-group="$SERVING_RUNTIME_GROUP" 2>/dev/null | grep -q "$SERVING_RUNTIME_PLURAL"; then
    HAS_SERVING_RUNTIME=true
fi

if $HAS_SERVING_RUNTIME; then
    # Check namespace-scoped runtimes
    COMPATIBLE_COUNT=0
    RUNTIMES_JSON=$("$CLI" get "${SERVING_RUNTIME_PLURAL}.${SERVING_RUNTIME_GROUP}" \
        -n "$NAMESPACE" -o json 2>/dev/null || echo '{"items":[]}')

    COMPATIBLE_COUNT=$(echo "$RUNTIMES_JSON" | jq --arg fmt "$MODEL_FORMAT" \
        '[.items[] | select(.spec.supportedModelFormats[]? | .name | ascii_downcase == ($fmt | ascii_downcase))] | length' 2>/dev/null || echo 0)

    # Also check platform namespace templates
    TEMPLATE_COUNT=0
    PLATFORM_RUNTIMES=$("$CLI" get "${SERVING_RUNTIME_PLURAL}.${SERVING_RUNTIME_GROUP}" \
        -n "$PLATFORM_NAMESPACE" -o json 2>/dev/null || echo '{"items":[]}')

    TEMPLATE_COUNT=$(echo "$PLATFORM_RUNTIMES" | jq --arg fmt "$MODEL_FORMAT" \
        '[.items[] | select(.spec.supportedModelFormats[]? | .name | ascii_downcase == ($fmt | ascii_downcase))] | length' 2>/dev/null || echo 0)

    TOTAL_COMPATIBLE=$((COMPATIBLE_COUNT + TEMPLATE_COUNT))

    if [[ "$TOTAL_COMPATIBLE" -gt 0 ]]; then
        add_check "serving_runtime" "true" "$TOTAL_COMPATIBLE runtime(s) support format '$MODEL_FORMAT'"
    else
        add_check "serving_runtime" "false" "No serving runtime supports format '$MODEL_FORMAT'"
    fi
else
    add_check "serving_runtime" "false" "ServingRuntime CRD not found. KServe may not be installed."
fi

# ---- Check 3: Storage accessibility ----
if [[ "$STORAGE_URI" == pvc://* ]]; then
    PVC_NAME=$(echo "$STORAGE_URI" | sed 's|^pvc://||' | cut -d'/' -f1)
    PVC_JSON=$("$CLI" get pvc "$PVC_NAME" -n "$NAMESPACE" -o json 2>/dev/null || echo "")

    if [[ -n "$PVC_JSON" ]]; then
        PVC_PHASE=$(echo "$PVC_JSON" | jq -r '.status.phase // "Unknown"')
        if [[ "$PVC_PHASE" == "Bound" ]]; then
            add_check "storage" "true" "PVC '$PVC_NAME' is bound"
        else
            add_check "storage" "false" "PVC '$PVC_NAME' is not bound (status: $PVC_PHASE)"
        fi
    else
        add_check "storage" "false" "PVC '$PVC_NAME' not found in namespace '$NAMESPACE'"
    fi
elif [[ "$STORAGE_URI" == s3://* ]]; then
    # Check if any data connection secrets exist in the namespace
    DC_COUNT=$("$CLI" get secrets -n "$NAMESPACE" \
        -l "opendatahub.io/dashboard=true,opendatahub.io/managed=true" \
        -o json 2>/dev/null | jq '.items | length' 2>/dev/null || echo 0)

    if [[ "$DC_COUNT" -gt 0 ]]; then
        add_check "storage" "true" "S3 storage URI with $DC_COUNT data connection(s) available"
    else
        add_check "storage" "false" "S3 storage URI but no data connections found in namespace '$NAMESPACE'"
    fi
else
    add_check "storage" "false" "Unknown storage scheme in URI: $STORAGE_URI (expected pvc:// or s3://)"
fi

# ---- Check 4: GPU availability (informational) ----
GPU_NODES=$("$CLI" get nodes -o json 2>/dev/null | jq \
    '[.items[] | select(.status.allocatable["nvidia.com/gpu"] // "0" | tonumber > 0)]' 2>/dev/null || echo "[]")

GPU_TOTAL=$(echo "$GPU_NODES" | jq '[.[].status.allocatable["nvidia.com/gpu"] | tonumber] | add // 0')

if [[ "$GPU_TOTAL" -gt 0 ]]; then
    add_check "gpu" "true" "$GPU_TOTAL GPU(s) available across cluster nodes"
else
    add_check "gpu" "true" "No GPUs detected (OK if model does not require GPU)"
fi

# ---- Output ----
jq -n \
    --argjson checks "$CHECKS" \
    --argjson all_passed "$ALL_PASSED" \
    '{
        "all_passed": $all_passed,
        "checks": $checks,
        "ready_to_deploy": $all_passed
    }'
