#!/usr/bin/env bash
# List RHOAI resources of a given type.
#
# Maps friendly type names to Kubernetes resource types and lists all
# resources, optionally scoped to a namespace.
#
# Usage: ./list-resources.sh TYPE [NAMESPACE]
# Output: JSON array of resources.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

CLI=$(detect_cli)

TYPE="${1:?Usage: list-resources.sh TYPE [NAMESPACE]}"
NAMESPACE="${2:-}"

# ---- Handle project listing (cluster-scoped) ----

if [[ "$TYPE" == "project" ]]; then
    "$CLI" get namespaces -l "opendatahub.io/dashboard=true" -o json 2>/dev/null | jq '[.items[] | {
      name: .metadata.name,
      status: .status.phase,
      created: .metadata.creationTimestamp,
      labels: (.metadata.labels // {})
    }]'
    exit 0
fi

# ---- Map type to Kubernetes resource ----

case "$TYPE" in
    workbench|notebook)
        RESOURCE="${NOTEBOOK_PLURAL}.${NOTEBOOK_GROUP}"
        JQ_FILTER='[.items[] | {
          name: .metadata.name,
          namespace: .metadata.namespace,
          status: (if .metadata.annotations["kubeflow-resource-stopped"] then "Stopped" else "Running" end),
          image: (.spec.template.spec.containers[0].image // "unknown"),
          created: .metadata.creationTimestamp
        }]'
        ;;
    model|inferenceservice)
        RESOURCE="${INFERENCE_SERVICE_PLURAL}.${INFERENCE_SERVICE_GROUP}"
        JQ_FILTER='[.items[] | {
          name: .metadata.name,
          namespace: .metadata.namespace,
          ready: (.status.conditions // [] | map(select(.type == "Ready")) | .[0].status // "Unknown"),
          url: (.status.url // "pending"),
          model_format: (.spec.predictor.model.modelFormat.name // "unknown"),
          created: .metadata.creationTimestamp
        }]'
        ;;
    training_job|trainjob)
        RESOURCE="${TRAINJOB_PLURAL}.${TRAINJOB_GROUP}"
        JQ_FILTER='[.items[] | {
          name: .metadata.name,
          namespace: .metadata.namespace,
          suspended: (.spec.suspend // false),
          conditions: (.status.conditions // []),
          runtime: (.spec.trainingRuntimeRef.name // "unknown"),
          created: .metadata.creationTimestamp
        }]'
        ;;
    connection)
        # Connections are secrets with the dashboard label
        if [[ -z "$NAMESPACE" ]]; then
            die "NAMESPACE is required for listing connections."
        fi
        require_namespace "$NAMESPACE"
        "$CLI" get secrets -n "$NAMESPACE" -l "opendatahub.io/dashboard=true" -o json 2>/dev/null | jq '[.items[] | {
          name: .metadata.name,
          namespace: .metadata.namespace,
          type: (.metadata.annotations["opendatahub.io/connection-type"] // "unknown"),
          created: .metadata.creationTimestamp
        }]'
        exit 0
        ;;
    storage|pvc)
        RESOURCE="pvc"
        JQ_FILTER='[.items[] | {
          name: .metadata.name,
          namespace: .metadata.namespace,
          status: .status.phase,
          capacity: (.status.capacity.storage // "pending"),
          access_modes: .spec.accessModes,
          storage_class: .spec.storageClassName,
          created: .metadata.creationTimestamp
        }]'
        ;;
    pipeline|dspa)
        RESOURCE="${DSPA_PLURAL}.${DSPA_GROUP}"
        JQ_FILTER='[.items[] | {
          name: .metadata.name,
          namespace: .metadata.namespace,
          ready: (.status.conditions // [] | map(select(.type == "Ready")) | .[0].status // "Unknown"),
          created: .metadata.creationTimestamp
        }]'
        ;;
    *)
        die "Unknown resource type '$TYPE'. Supported: project, workbench, notebook, model, inferenceservice, training_job, trainjob, connection, storage, pvc, pipeline, dspa."
        ;;
esac

# ---- List resources ----

if [[ -z "$NAMESPACE" ]]; then
    die "NAMESPACE is required for listing $TYPE resources."
fi

require_namespace "$NAMESPACE"

RESULT=$("$CLI" get "$RESOURCE" -n "$NAMESPACE" -o json 2>/dev/null) || \
    die "Failed to list $TYPE resources in namespace '$NAMESPACE'. Ensure the CRD is installed."

echo "$RESULT" | jq "$JQ_FILTER"
