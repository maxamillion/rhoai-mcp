#!/usr/bin/env bash
# Start a stopped workbench by removing the stopped annotation.
#
# Usage: ./start-workbench.sh NAMESPACE NAME
#
# Removes the kubeflow-resource-stopped annotation from the Notebook resource,
# which causes the Kubeflow Notebooks controller to create the workbench pod.
#
# Output: JSON with start result.

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

# Check if already running (no stopped annotation)
stopped_annotation=$("$CLI" get "${NOTEBOOK_PLURAL}.${NOTEBOOK_GROUP}" "$NAME" \
    -n "$NAMESPACE" -o jsonpath='{.metadata.annotations.kubeflow-resource-stopped}' 2>/dev/null || true)

if [[ -z "$stopped_annotation" ]]; then
    cat <<EOF
{
  "success": true,
  "name": "$NAME",
  "namespace": "$NAMESPACE",
  "action": "none",
  "message": "Workbench '$NAME' is already running."
}
EOF
    exit 0
fi

# Remove the stopped annotation
"$CLI" annotate "${NOTEBOOK_PLURAL}.${NOTEBOOK_GROUP}" "$NAME" \
    -n "$NAMESPACE" kubeflow-resource-stopped- --overwrite >/dev/null 2>&1

cat <<EOF
{
  "success": true,
  "name": "$NAME",
  "namespace": "$NAMESPACE",
  "action": "started",
  "message": "Workbench '$NAME' is starting. It may take a few minutes for the pod to be ready."
}
EOF
