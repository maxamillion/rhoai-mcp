#!/usr/bin/env bash
# Create a PersistentVolumeClaim in a namespace.
#
# Generates and applies a PVC manifest with the RHOAI dashboard label.
# Supports configurable access mode and storage class.
#
# Usage: ./create-pvc.sh NAMESPACE NAME SIZE [--access-mode MODE] [--storage-class CLASS] [--dry-run]
# Output: JSON result of the created PVC or the dry-run manifest.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

CLI=$(detect_cli)

# ---- Parse arguments ----

NAMESPACE="${1:?Usage: create-pvc.sh NAMESPACE NAME SIZE [--access-mode MODE] [--storage-class CLASS] [--dry-run]}"
NAME="${2:?Usage: create-pvc.sh NAMESPACE NAME SIZE [--access-mode MODE] [--storage-class CLASS] [--dry-run]}"
SIZE="${3:?Usage: create-pvc.sh NAMESPACE NAME SIZE [--access-mode MODE] [--storage-class CLASS] [--dry-run]}"
shift 3

ACCESS_MODE="ReadWriteOnce"
STORAGE_CLASS=""
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --access-mode)
            ACCESS_MODE="${2:?--access-mode requires a value}"
            shift 2
            ;;
        --storage-class)
            STORAGE_CLASS="${2:?--storage-class requires a value}"
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

# Validate access mode
case "$ACCESS_MODE" in
    ReadWriteOnce|ReadWriteMany|ReadOnlyMany) ;;
    *) die "Invalid access mode '$ACCESS_MODE'. Must be ReadWriteOnce, ReadWriteMany, or ReadOnlyMany." ;;
esac

# Validate size format (e.g., 10Gi, 100Mi, 1Ti)
if ! echo "$SIZE" | grep -qE '^[0-9]+(Ki|Mi|Gi|Ti|Pi|Ei)$'; then
    die "Invalid size '$SIZE'. Must be a quantity like 10Gi, 100Mi, or 1Ti."
fi

require_namespace "$NAMESPACE"

# ---- Build manifest ----

MANIFEST=$(mktemp)
trap 'rm -f "$MANIFEST"' EXIT

if [[ -n "$STORAGE_CLASS" ]]; then
    cat > "$MANIFEST" <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ${NAME}
  namespace: ${NAMESPACE}
  labels:
    opendatahub.io/dashboard: "true"
spec:
  accessModes:
    - ${ACCESS_MODE}
  resources:
    requests:
      storage: ${SIZE}
  storageClassName: ${STORAGE_CLASS}
EOF
else
    cat > "$MANIFEST" <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ${NAME}
  namespace: ${NAMESPACE}
  labels:
    opendatahub.io/dashboard: "true"
spec:
  accessModes:
    - ${ACCESS_MODE}
  resources:
    requests:
      storage: ${SIZE}
EOF
fi

# ---- Apply or dry-run ----

if $DRY_RUN; then
    info "Dry run - manifest not applied"
    cat "$MANIFEST"
    exit 0
fi

apply_manifest "$MANIFEST" "$NAMESPACE"

# Return the created PVC as JSON
"$CLI" get pvc "$NAME" -n "$NAMESPACE" -o json | jq '{
  name: .metadata.name,
  namespace: .metadata.namespace,
  status: .status.phase,
  capacity: (.status.capacity.storage // "pending"),
  access_modes: .spec.accessModes,
  storage_class: .spec.storageClassName,
  created: .metadata.creationTimestamp
}'
