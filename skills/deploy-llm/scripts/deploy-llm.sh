#!/usr/bin/env bash
# Deploy a large language model as a KServe InferenceService.
#
# Generates and applies an InferenceService manifest configured for LLM
# serving with vLLM or TGIS runtime, GPU resources, and PyTorch model format.
#
# Usage: ./deploy-llm.sh <NAMESPACE> <NAME> <MODEL_ID> <STORAGE_URI> [OPTIONS]
#
# Options:
#   --runtime NAME          Serving runtime (default: auto-detect, prefers vLLM)
#   --gpu-count N           GPU count per replica (default: 1)
#   --memory-request VALUE  Memory request (default: 16Gi)
#   --memory-limit VALUE    Memory limit (default: 32Gi)
#   --min-replicas N        Minimum replicas (default: 1)
#   --max-replicas N        Maximum replicas (default: 1)
#   --dry-run               Print manifest without applying
#
# Output: JSON confirmation of the created InferenceService.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

# ---- Positional arguments ----
NAMESPACE="${1:-}"
NAME="${2:-}"
MODEL_ID="${3:-}"
STORAGE_URI="${4:-}"

if [[ -z "$NAMESPACE" || -z "$NAME" || -z "$MODEL_ID" || -z "$STORAGE_URI" ]]; then
    die "Usage: $0 <NAMESPACE> <NAME> <MODEL_ID> <STORAGE_URI> [OPTIONS]"
fi

shift 4

# ---- LLM-specific default options ----
RUNTIME=""
GPU_COUNT=1
MEMORY_REQUEST="16Gi"
MEMORY_LIMIT="32Gi"
MIN_REPLICAS=1
MAX_REPLICAS=1
DRY_RUN=false

# ---- Parse options ----
while [[ $# -gt 0 ]]; do
    case "$1" in
        --runtime)
            RUNTIME="$2"
            shift 2
            ;;
        --gpu-count)
            GPU_COUNT="$2"
            shift 2
            ;;
        --memory-request)
            MEMORY_REQUEST="$2"
            shift 2
            ;;
        --memory-limit)
            MEMORY_LIMIT="$2"
            shift 2
            ;;
        --min-replicas)
            MIN_REPLICAS="$2"
            shift 2
            ;;
        --max-replicas)
            MAX_REPLICAS="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            die "Unknown option: $1"
            ;;
    esac
done

CLI=$(detect_cli)

# ---- Auto-detect runtime if not specified ----
if [[ -z "$RUNTIME" ]]; then
    info "Auto-detecting LLM serving runtime..."

    # Check namespace-scoped runtimes first
    RUNTIMES_JSON=$("$CLI" get "${SERVING_RUNTIME_PLURAL}.${SERVING_RUNTIME_GROUP}" \
        -n "$NAMESPACE" -o json 2>/dev/null || echo '{"items":[]}')

    # Prefer vLLM over TGIS
    VLLM_RUNTIME=$(echo "$RUNTIMES_JSON" | jq -r \
        '[.items[] | select(.metadata.name | ascii_downcase | test("vllm"))] | .[0].metadata.name // empty' 2>/dev/null || echo "")

    if [[ -n "$VLLM_RUNTIME" ]]; then
        RUNTIME="$VLLM_RUNTIME"
        info "Found vLLM runtime in namespace: $RUNTIME"
    else
        TGIS_RUNTIME=$(echo "$RUNTIMES_JSON" | jq -r \
            '[.items[] | select(.metadata.name | ascii_downcase | test("tgis"))] | .[0].metadata.name // empty' 2>/dev/null || echo "")

        if [[ -n "$TGIS_RUNTIME" ]]; then
            RUNTIME="$TGIS_RUNTIME"
            info "Found TGIS runtime in namespace: $RUNTIME"
        else
            # Fall back to platform namespace
            PLATFORM_RUNTIMES=$("$CLI" get "${SERVING_RUNTIME_PLURAL}.${SERVING_RUNTIME_GROUP}" \
                -n "$PLATFORM_NAMESPACE" -o json 2>/dev/null || echo '{"items":[]}')

            VLLM_RUNTIME=$(echo "$PLATFORM_RUNTIMES" | jq -r \
                '[.items[] | select(.metadata.name | ascii_downcase | test("vllm"))] | .[0].metadata.name // empty' 2>/dev/null || echo "")

            if [[ -n "$VLLM_RUNTIME" ]]; then
                RUNTIME="$VLLM_RUNTIME"
                info "Found vLLM runtime in platform namespace: $RUNTIME"
            else
                TGIS_RUNTIME=$(echo "$PLATFORM_RUNTIMES" | jq -r \
                    '[.items[] | select(.metadata.name | ascii_downcase | test("tgis"))] | .[0].metadata.name // empty' 2>/dev/null || echo "")

                if [[ -n "$TGIS_RUNTIME" ]]; then
                    RUNTIME="$TGIS_RUNTIME"
                    info "Found TGIS runtime in platform namespace: $RUNTIME"
                else
                    die "No vLLM or TGIS serving runtime found. Install a runtime or specify one with --runtime."
                fi
            fi
        fi
    fi
fi

# ---- LLM-specific settings ----
MODEL_FORMAT="pytorch"
CPU_REQUEST="2"
CPU_LIMIT="4"
DISPLAY_NAME="$NAME"

# ---- Build GPU resources block ----
GPU_BLOCK=""
if [[ "$GPU_COUNT" -gt 0 ]]; then
    GPU_BLOCK="          nvidia.com/gpu: \"${GPU_COUNT}\""
fi

# ---- Generate manifest ----
MANIFEST=$(mktemp /tmp/isvc-llm-XXXXXX.yaml)
trap 'rm -f "$MANIFEST"' EXIT

cat > "$MANIFEST" <<EOF
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: ${NAME}
  namespace: ${NAMESPACE}
  labels:
    opendatahub.io/dashboard: "true"
  annotations:
    openshift.io/display-name: "${DISPLAY_NAME}"
spec:
  predictor:
    model:
      modelFormat:
        name: ${MODEL_FORMAT}
      runtime: ${RUNTIME}
      storageUri: ${STORAGE_URI}
      resources:
        requests:
          cpu: "${CPU_REQUEST}"
          memory: "${MEMORY_REQUEST}"
        limits:
          cpu: "${CPU_LIMIT}"
          memory: "${MEMORY_LIMIT}"
${GPU_BLOCK:+$GPU_BLOCK
}    minReplicas: ${MIN_REPLICAS}
    maxReplicas: ${MAX_REPLICAS}
EOF

# ---- Dry run or apply ----
if $DRY_RUN; then
    info "Dry run mode - manifest not applied"
    echo "---"
    cat "$MANIFEST"
    echo "---"
    jq -n \
        --arg name "$NAME" \
        --arg namespace "$NAMESPACE" \
        --arg runtime "$RUNTIME" \
        --arg model_id "$MODEL_ID" \
        --arg model_format "$MODEL_FORMAT" \
        --arg storage_uri "$STORAGE_URI" \
        --argjson gpu_count "$GPU_COUNT" \
        '{
            "dry_run": true,
            "name": $name,
            "namespace": $namespace,
            "runtime": $runtime,
            "model_id": $model_id,
            "model_format": $model_format,
            "storage_uri": $storage_uri,
            "gpu_count": $gpu_count,
            "message": "Manifest printed above. Remove --dry-run to apply."
        }'
    exit 0
fi

# ---- Apply manifest ----
if ! "$CLI" apply -f "$MANIFEST" 2>&1; then
    die "Failed to apply InferenceService manifest"
fi

# ---- Verify creation ----
ISVC_JSON=$("$CLI" get inferenceservices.serving.kserve.io "$NAME" \
    -n "$NAMESPACE" -o json 2>/dev/null || echo "{}")

READY=$(echo "$ISVC_JSON" | jq -r '
    .status.conditions // [] |
    map(select(.type == "Ready")) |
    if length > 0 then .[0].status else "Unknown" end
' 2>/dev/null || echo "Unknown")

jq -n \
    --arg name "$NAME" \
    --arg namespace "$NAMESPACE" \
    --arg runtime "$RUNTIME" \
    --arg model_id "$MODEL_ID" \
    --arg model_format "$MODEL_FORMAT" \
    --arg storage_uri "$STORAGE_URI" \
    --arg display_name "$DISPLAY_NAME" \
    --argjson min_replicas "$MIN_REPLICAS" \
    --argjson max_replicas "$MAX_REPLICAS" \
    --arg cpu_request "$CPU_REQUEST" \
    --arg cpu_limit "$CPU_LIMIT" \
    --arg memory_request "$MEMORY_REQUEST" \
    --arg memory_limit "$MEMORY_LIMIT" \
    --argjson gpu_count "$GPU_COUNT" \
    --arg ready "$READY" \
    '{
        "created": true,
        "name": $name,
        "namespace": $namespace,
        "runtime": $runtime,
        "model_id": $model_id,
        "model_format": $model_format,
        "storage_uri": $storage_uri,
        "display_name": $display_name,
        "min_replicas": $min_replicas,
        "max_replicas": $max_replicas,
        "resources": {
            "cpu_request": $cpu_request,
            "cpu_limit": $cpu_limit,
            "memory_request": $memory_request,
            "memory_limit": $memory_limit,
            "gpu_count": $gpu_count
        },
        "ready": $ready,
        "message": "InferenceService created for LLM. It may take 10-20 minutes to become ready depending on model size."
    }'
