#!/usr/bin/env bash
# Create a new workbench (Kubeflow Notebook) in a namespace.
#
# Usage: ./create-workbench.sh NAMESPACE NAME IMAGE [OPTIONS]
#
# Options:
#   --cpu CPU            CPU request and limit (default: 1)
#   --memory MEM         Memory request and limit (default: 4Gi)
#   --gpu GPU            Number of GPUs (default: 0)
#   --storage-size SIZE  PVC storage size (default: 10Gi)
#   --display-name NAME  Human-readable display name
#   --dry-run            Print manifest without applying
#
# Creates a PVC and Notebook resource.
# Output: JSON with creation result.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

CLI=$(detect_cli)

# ---- Parse arguments ----
NAMESPACE="${1:-}"
NAME="${2:-}"
IMAGE="${3:-}"

if [[ -z "$NAMESPACE" || -z "$NAME" || -z "$IMAGE" ]]; then
    die "Usage: $0 NAMESPACE NAME IMAGE [--cpu CPU] [--memory MEM] [--gpu GPU] [--storage-size SIZE] [--display-name DISPLAY] [--dry-run]"
fi

shift 3

# Defaults
CPU="1"
MEMORY="4Gi"
GPU="0"
STORAGE_SIZE="10Gi"
DISPLAY_NAME="$NAME"
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --cpu)
            CPU="$2"
            shift 2
            ;;
        --memory)
            MEMORY="$2"
            shift 2
            ;;
        --gpu)
            GPU="$2"
            shift 2
            ;;
        --storage-size)
            STORAGE_SIZE="$2"
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

# ---- Validate inputs ----
require_namespace "$NAMESPACE"

if ! "$CLI" api-resources --api-group="$NOTEBOOK_GROUP" 2>/dev/null | grep -q "$NOTEBOOK_PLURAL"; then
    die "Notebook CRD not found. Ensure the Kubeflow Notebooks operator is installed."
fi

# Check if notebook already exists
if "$CLI" get "${NOTEBOOK_PLURAL}.${NOTEBOOK_GROUP}" "$NAME" -n "$NAMESPACE" &>/dev/null 2>&1; then
    die "Notebook '$NAME' already exists in namespace '$NAMESPACE'."
fi

# ---- Build GPU resources ----
GPU_RESOURCES=""
if [[ "$GPU" -gt 0 ]]; then
    GPU_RESOURCES=$(cat <<GPUEOF
              nvidia.com/gpu: "$GPU"
GPUEOF
)
fi

GPU_LIMITS=""
if [[ "$GPU" -gt 0 ]]; then
    GPU_LIMITS=$(cat <<GPULEOF
              nvidia.com/gpu: "$GPU"
GPULEOF
)
fi

# ---- Build PVC manifest ----
PVC_MANIFEST=$(cat <<PVCEOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ${NAME}-pvc
  namespace: ${NAMESPACE}
  labels:
    opendatahub.io/dashboard: "true"
    app: ${NAME}
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: ${STORAGE_SIZE}
PVCEOF
)

# ---- Build Notebook manifest ----
NOTEBOOK_MANIFEST=$(cat <<NBEOF
apiVersion: kubeflow.org/v1
kind: Notebook
metadata:
  name: ${NAME}
  namespace: ${NAMESPACE}
  labels:
    opendatahub.io/dashboard: "true"
    app: ${NAME}
  annotations:
    openshift.io/display-name: "${DISPLAY_NAME}"
    notebooks.opendatahub.io/inject-oauth: "true"
spec:
  template:
    spec:
      containers:
        - name: ${NAME}
          image: ${IMAGE}
          resources:
            requests:
              cpu: "${CPU}"
              memory: "${MEMORY}"
${GPU_RESOURCES:+${GPU_RESOURCES}
}            limits:
              cpu: "${CPU}"
              memory: "${MEMORY}"
${GPU_LIMITS:+${GPU_LIMITS}
}          volumeMounts:
            - name: ${NAME}-pvc
              mountPath: /opt/app-root/src
      volumes:
        - name: ${NAME}-pvc
          persistentVolumeClaim:
            claimName: ${NAME}-pvc
NBEOF
)

# ---- Dry run or apply ----
if $DRY_RUN; then
    cat <<EOF
{
  "dry_run": true,
  "pvc_manifest": $(echo "$PVC_MANIFEST" | jq -Rs .),
  "notebook_manifest": $(echo "$NOTEBOOK_MANIFEST" | jq -Rs .)
}
EOF
    exit 0
fi

# Create PVC if it does not already exist
pvc_status="created"
if "$CLI" get pvc "${NAME}-pvc" -n "$NAMESPACE" &>/dev/null 2>&1; then
    pvc_status="already_exists"
    info "PVC '${NAME}-pvc' already exists, skipping creation."
else
    echo "$PVC_MANIFEST" | "$CLI" apply -f - -n "$NAMESPACE" >/dev/null 2>&1
    info "PVC '${NAME}-pvc' created."
fi

# Create Notebook
echo "$NOTEBOOK_MANIFEST" | "$CLI" apply -f - -n "$NAMESPACE" >/dev/null 2>&1

cat <<EOF
{
  "success": true,
  "name": "${NAME}",
  "namespace": "${NAMESPACE}",
  "image": "${IMAGE}",
  "display_name": "${DISPLAY_NAME}",
  "cpu": "${CPU}",
  "memory": "${MEMORY}",
  "gpu": "${GPU}",
  "storage_size": "${STORAGE_SIZE}",
  "pvc_name": "${NAME}-pvc",
  "pvc_status": "${pvc_status}",
  "message": "Workbench '${NAME}' created. It may take a few minutes to start."
}
EOF
