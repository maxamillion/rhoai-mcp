#!/usr/bin/env bash
# Get a specific RHOAI resource by type, name, and namespace.
#
# Maps friendly type names to the underlying Kubernetes resource types
# and retrieves the full JSON representation.
#
# Usage: ./get-resource.sh TYPE NAME NAMESPACE
# Output: JSON of the resource.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

CLI=$(detect_cli)

TYPE="${1:?Usage: get-resource.sh TYPE NAME NAMESPACE}"
NAME="${2:?Usage: get-resource.sh TYPE NAME NAMESPACE}"
NAMESPACE="${3:?Usage: get-resource.sh TYPE NAME NAMESPACE}"

require_namespace "$NAMESPACE"

# ---- Map type to Kubernetes resource ----

case "$TYPE" in
    workbench|notebook)
        RESOURCE="${NOTEBOOK_PLURAL}.${NOTEBOOK_GROUP}"
        ;;
    model|inferenceservice)
        RESOURCE="${INFERENCE_SERVICE_PLURAL}.${INFERENCE_SERVICE_GROUP}"
        ;;
    training_job|trainjob)
        RESOURCE="${TRAINJOB_PLURAL}.${TRAINJOB_GROUP}"
        ;;
    connection)
        # Connections are secrets with the dashboard label
        RESULT=$("$CLI" get secret "$NAME" -n "$NAMESPACE" -o json 2>/dev/null) || \
            die "Connection '$NAME' not found in namespace '$NAMESPACE'."
        # Verify it has the dashboard label
        HAS_LABEL=$(echo "$RESULT" | jq -r '.metadata.labels["opendatahub.io/dashboard"] // "false"')
        if [[ "$HAS_LABEL" != "true" ]]; then
            die "Secret '$NAME' exists but is not an RHOAI data connection (missing opendatahub.io/dashboard label)."
        fi
        echo "$RESULT" | jq '.'
        exit 0
        ;;
    storage|pvc)
        RESOURCE="pvc"
        ;;
    pipeline|dspa)
        RESOURCE="${DSPA_PLURAL}.${DSPA_GROUP}"
        ;;
    *)
        die "Unknown resource type '$TYPE'. Supported: workbench, notebook, model, inferenceservice, training_job, trainjob, connection, storage, pvc, pipeline, dspa."
        ;;
esac

# ---- Get the resource ----

RESULT=$("$CLI" get "$RESOURCE" "$NAME" -n "$NAMESPACE" -o json 2>/dev/null) || \
    die "$TYPE '$NAME' not found in namespace '$NAMESPACE'."

echo "$RESULT" | jq '.'
