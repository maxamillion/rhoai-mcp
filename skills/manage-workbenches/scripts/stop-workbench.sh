#!/usr/bin/env bash
# Stop a running workbench by adding the stopped annotation.
#
# Usage: ./stop-workbench.sh NAMESPACE NAME
#
# Adds the kubeflow-resource-stopped annotation to the Notebook resource,
# which causes the Kubeflow Notebooks controller to delete the workbench pod.
# The Notebook resource and PVC are preserved.
#
# Output: JSON with stop result.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

CLI=$(detect_cli)

# ---- Validate inputs ----
NAMESPACE="${1:-}"
NAME="${2:-}"

if [[ -z "$NAMESPACE" || -z "$NAME" ]]; then
    die "Usage: $0 NAMESPACE NAME"
fi

require_namespace "$NAMESPACE"

# Check if notebook exists
if ! "$CLI" get "${NOTEBOOK_PLURAL}.${NOTEBOOK_GROUP}" "$NAME" -n "$NAMESPACE" &>/dev/null 2>&1; then
    die "Notebook '$NAME' not found in namespace '$NAMESPACE'."
fi

# Check if already stopped
stopped_annotation=$("$CLI" get "${NOTEBOOK_PLURAL}.${NOTEBOOK_GROUP}" "$NAME" \
    -n "$NAMESPACE" -o jsonpath='{.metadata.annotations.kubeflow-resource-stopped}' 2>/dev/null || true)

if [[ -n "$stopped_annotation" ]]; then
    cat <<EOF
{
  "success": true,
  "name": "$NAME",
  "namespace": "$NAMESPACE",
  "action": "none",
  "message": "Workbench '$NAME' is already stopped."
}
EOF
    exit 0
fi

# Add the stopped annotation
"$CLI" annotate "${NOTEBOOK_PLURAL}.${NOTEBOOK_GROUP}" "$NAME" \
    -n "$NAMESPACE" kubeflow-resource-stopped="true" --overwrite >/dev/null 2>&1

cat <<EOF
{
  "success": true,
  "name": "$NAME",
  "namespace": "$NAMESPACE",
  "action": "stopped",
  "message": "Workbench '$NAME' has been stopped. The pod will be terminated but the Notebook resource and PVC are preserved."
}
EOF
