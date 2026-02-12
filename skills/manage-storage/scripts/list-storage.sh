#!/usr/bin/env bash
# List PersistentVolumeClaims in a namespace.
#
# Shows each PVC's name, status, capacity, access modes, storage class,
# and creation timestamp.
#
# Usage: ./list-storage.sh NAMESPACE
# Output: JSON array of PVC details.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

CLI=$(detect_cli)
NAMESPACE="${1:?Usage: list-storage.sh NAMESPACE}"

require_namespace "$NAMESPACE"

"$CLI" get pvc -n "$NAMESPACE" -o json | jq '[.items[] | {
  name: .metadata.name,
  status: .status.phase,
  capacity: (.status.capacity.storage // "pending"),
  access_modes: .spec.accessModes,
  storage_class: .spec.storageClassName,
  created: .metadata.creationTimestamp
}]'
