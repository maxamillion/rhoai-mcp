#!/usr/bin/env bash
# Deploy a model as a KServe InferenceService.
#
# Generates and applies an InferenceService manifest with the specified
# runtime, model format, storage, and resource configuration.
#
# Usage: ./deploy-inferenceservice.sh <NAMESPACE> <NAME> <RUNTIME> <MODEL_FORMAT> <STORAGE_URI> [OPTIONS]
#
# Options:
#   --min-replicas N        Minimum replicas (default: 1)
#   --max-replicas N        Maximum replicas (default: 1)
#   --cpu-request VALUE     CPU request (default: 1)
#   --cpu-limit VALUE       CPU limit (default: 2)
#   --memory-request VALUE  Memory request (default: 4Gi)
#   --memory-limit VALUE    Memory limit (default: 8Gi)
#   --gpu-count N           GPU count per replica (default: 0)
#   --display-name TEXT     Human-readable display name
#   --dry-run               Print manifest without applying
#
# Output: JSON confirmation of the created InferenceService.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

# ---- Positional arguments ----
NAMESPACE="${1:-}"
NAME="${2:-}"
RUNTIME="${3:-}"
MODEL_FORMAT="${4:-}"
STORAGE_URI="${5:-}"

if [[ -z "$NAMESPACE" || -z "$NAME" || -z "$RUNTIME" || -z "$MODEL_FORMAT" || -z "$STORAGE_URI" ]]; then
    die "Usage: $0 <NAMESPACE> <NAME> <RUNTIME> <MODEL_FORMAT> <STORAGE_URI> [OPTIONS]"
fi

shift 5

# ---- Default options ----
MIN_REPLICAS=1
MAX_REPLICAS=1
CPU_REQUEST="1"
CPU_LIMIT="2"
MEMORY_REQUEST="4Gi"
MEMORY_LIMIT="8Gi"
GPU_COUNT=0
DISPLAY_NAME="$NAME"
DRY_RUN=false

# ---- Parse options ----
while [[ $# -gt 0 ]]; do
    case "$1" in
        --min-replicas)
            MIN_REPLICAS="$2"
            shift 2
            ;;
        --max-replicas)
            MAX_REPLICAS="$2"
            shift 2
            ;;
        --cpu-request)
            CPU_REQUEST="$2"
            shift 2
            ;;
        --cpu-limit)
            CPU_LIMIT="$2"
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
        --gpu-count)
            GPU_COUNT="$2"
            shift 2
            ;;
        --display-name)
            DISPLAY_NAME="$2"
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

# ---- Build GPU resources block ----
GPU_BLOCK=""
if [[ "$GPU_COUNT" -gt 0 ]]; then
    GPU_BLOCK="          nvidia.com/gpu: \"${GPU_COUNT}\""
fi

# ---- Generate manifest ----
MANIFEST=$(mktemp /tmp/isvc-XXXXXX.yaml)
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
        --arg model_format "$MODEL_FORMAT" \
        --arg storage_uri "$STORAGE_URI" \
        '{
            "dry_run": true,
            "name": $name,
            "namespace": $namespace,
            "runtime": $runtime,
            "model_format": $model_format,
            "storage_uri": $storage_uri,
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
        "message": "InferenceService created. It may take a few minutes to become ready."
    }'
