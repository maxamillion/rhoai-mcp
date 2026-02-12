#!/usr/bin/env bash
# Pre-flight checks before deploying an LLM as an InferenceService.
#
# Validates cluster authentication, namespace existence, GPU node availability,
# and presence of vLLM or TGIS serving runtimes.
#
# Usage: ./check-llm-prereqs.sh <NAMESPACE> <MODEL_ID>
# Output: JSON with checks array and overall pass/fail.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

# ---- Argument validation ----
NAMESPACE="${1:-}"
MODEL_ID="${2:-}"

if [[ -z "$NAMESPACE" || -z "$MODEL_ID" ]]; then
    die "Usage: $0 <NAMESPACE> <MODEL_ID>"
fi

CLI=$(detect_cli)

CHECKS="[]"
ALL_PASSED=true

add_check() {
    local name="$1"
    local passed="$2"
    local details="$3"
    CHECKS=$(echo "$CHECKS" | jq \
        --arg name "$name" \
        --argjson passed "$passed" \
        --arg details "$details" \
        '. + [{"name": $name, "passed": $passed, "details": $details}]')
    if [[ "$passed" == "false" ]]; then
        ALL_PASSED=false
    fi
}

# ---- Check 1: Cluster authentication ----
if check_auth 2>/dev/null; then
    add_check "auth" "true" "Authenticated to the cluster"
else
    add_check "auth" "false" "Not authenticated. Run '$CLI login' or configure KUBECONFIG."
fi

# ---- Check 2: Namespace exists ----
if "$CLI" get namespace "$NAMESPACE" &>/dev/null 2>&1; then
    add_check "namespace" "true" "Namespace '$NAMESPACE' exists"
else
    add_check "namespace" "false" "Namespace '$NAMESPACE' not found. Create it before deploying."
fi

# ---- Check 3: GPU availability ----
GPU_NODES=$("$CLI" get nodes -o json 2>/dev/null | jq \
    '[.items[] | select(.status.allocatable["nvidia.com/gpu"] // "0" | tonumber > 0)]' 2>/dev/null || echo "[]")

GPU_NODE_COUNT=$(echo "$GPU_NODES" | jq 'length' 2>/dev/null || echo 0)
GPU_TOTAL=$(echo "$GPU_NODES" | jq '[.[].status.allocatable["nvidia.com/gpu"] | tonumber] | add // 0' 2>/dev/null || echo 0)

if [[ "$GPU_NODE_COUNT" -gt 0 ]]; then
    add_check "gpu_nodes" "true" "$GPU_NODE_COUNT GPU node(s) with $GPU_TOTAL total GPU(s) available"
else
    add_check "gpu_nodes" "false" "No GPU nodes detected. LLMs require at least 1 GPU node with nvidia.com/gpu resources."
fi

# ---- Check 4: vLLM or TGIS serving runtime available ----
HAS_SERVING_RUNTIME=false
if "$CLI" api-resources --api-group="$SERVING_RUNTIME_GROUP" 2>/dev/null | grep -q "$SERVING_RUNTIME_PLURAL"; then
    HAS_SERVING_RUNTIME=true
fi

if $HAS_SERVING_RUNTIME; then
    # Check namespace-scoped runtimes for vLLM or TGIS
    RUNTIMES_JSON=$("$CLI" get "${SERVING_RUNTIME_PLURAL}.${SERVING_RUNTIME_GROUP}" \
        -n "$NAMESPACE" -o json 2>/dev/null || echo '{"items":[]}')

    VLLM_COUNT=$(echo "$RUNTIMES_JSON" | jq \
        '[.items[] | select(.metadata.name | ascii_downcase | test("vllm"))] | length' 2>/dev/null || echo 0)

    TGIS_COUNT=$(echo "$RUNTIMES_JSON" | jq \
        '[.items[] | select(.metadata.name | ascii_downcase | test("tgis"))] | length' 2>/dev/null || echo 0)

    # Also check platform namespace templates
    PLATFORM_RUNTIMES=$("$CLI" get "${SERVING_RUNTIME_PLURAL}.${SERVING_RUNTIME_GROUP}" \
        -n "$PLATFORM_NAMESPACE" -o json 2>/dev/null || echo '{"items":[]}')

    PLATFORM_VLLM=$(echo "$PLATFORM_RUNTIMES" | jq \
        '[.items[] | select(.metadata.name | ascii_downcase | test("vllm"))] | length' 2>/dev/null || echo 0)

    PLATFORM_TGIS=$(echo "$PLATFORM_RUNTIMES" | jq \
        '[.items[] | select(.metadata.name | ascii_downcase | test("tgis"))] | length' 2>/dev/null || echo 0)

    TOTAL_VLLM=$((VLLM_COUNT + PLATFORM_VLLM))
    TOTAL_TGIS=$((TGIS_COUNT + PLATFORM_TGIS))
    TOTAL_LLM_RUNTIMES=$((TOTAL_VLLM + TOTAL_TGIS))

    if [[ "$TOTAL_LLM_RUNTIMES" -gt 0 ]]; then
        RUNTIME_DETAILS=""
        if [[ "$TOTAL_VLLM" -gt 0 ]]; then
            RUNTIME_DETAILS="vLLM($TOTAL_VLLM)"
        fi
        if [[ "$TOTAL_TGIS" -gt 0 ]]; then
            if [[ -n "$RUNTIME_DETAILS" ]]; then
                RUNTIME_DETAILS="$RUNTIME_DETAILS, "
            fi
            RUNTIME_DETAILS="${RUNTIME_DETAILS}TGIS($TOTAL_TGIS)"
        fi
        add_check "llm_runtime" "true" "LLM serving runtime(s) available: $RUNTIME_DETAILS"
    else
        add_check "llm_runtime" "false" "No vLLM or TGIS serving runtime found in namespace '$NAMESPACE' or platform namespace '$PLATFORM_NAMESPACE'"
    fi
else
    add_check "llm_runtime" "false" "ServingRuntime CRD not found. KServe may not be installed."
fi

# ---- Output ----
jq -n \
    --arg model_id "$MODEL_ID" \
    --arg namespace "$NAMESPACE" \
    --argjson checks "$CHECKS" \
    --argjson all_passed "$ALL_PASSED" \
    '{
        "model_id": $model_id,
        "namespace": $namespace,
        "all_passed": $all_passed,
        "checks": $checks,
        "ready_to_deploy": $all_passed
    }'
