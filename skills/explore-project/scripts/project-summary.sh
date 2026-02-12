#!/usr/bin/env bash
# Collect a comprehensive summary of all RHOAI resources in a Data Science Project.
#
# Usage: ./project-summary.sh NAMESPACE
#
# Outputs JSON with resource counts and status breakdowns for:
#   - Notebooks (workbenches): total, running, stopped
#   - InferenceServices (models): total, ready, not ready
#   - TrainJobs: total, running, completed, failed (if CRD installed)
#   - PersistentVolumeClaims (storage): total, with capacity info
#   - Data connections: total count
#   - Pipeline server (DSPA): present or not

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

CLI=$(detect_cli)

# ---- Validate inputs ----
NAMESPACE="${1:-}"
if [[ -z "$NAMESPACE" ]]; then
    die "Usage: $0 NAMESPACE"
fi

require_namespace "$NAMESPACE"

# ---- Notebooks (Workbenches) ----
notebooks_total=0
notebooks_running=0
notebooks_stopped=0

if "$CLI" api-resources --api-group="$NOTEBOOK_GROUP" 2>/dev/null | grep -q "$NOTEBOOK_PLURAL"; then
    notebooks_json=$("$CLI" get "${NOTEBOOK_PLURAL}.${NOTEBOOK_GROUP}" -n "$NAMESPACE" -o json 2>/dev/null || echo '{"items":[]}')
    notebooks_total=$(echo "$notebooks_json" | jq '.items | length')

    # A notebook is stopped if it has the kubeflow-resource-stopped annotation
    notebooks_stopped=$(echo "$notebooks_json" | jq '[.items[] | select(.metadata.annotations["kubeflow-resource-stopped"] != null)] | length')
    notebooks_running=$(( notebooks_total - notebooks_stopped ))
fi

# ---- InferenceServices (Models) ----
isvc_total=0
isvc_ready=0
isvc_not_ready=0

if "$CLI" api-resources --api-group="$INFERENCE_SERVICE_GROUP" 2>/dev/null | grep -q "$INFERENCE_SERVICE_PLURAL"; then
    isvc_json=$("$CLI" get "${INFERENCE_SERVICE_PLURAL}.${INFERENCE_SERVICE_GROUP}" -n "$NAMESPACE" -o json 2>/dev/null || echo '{"items":[]}')
    isvc_total=$(echo "$isvc_json" | jq '.items | length')

    # An InferenceService is ready if it has a status condition with type=Ready and status=True
    isvc_ready=$(echo "$isvc_json" | jq '[.items[] | select(.status.conditions[]? | select(.type == "Ready" and .status == "True"))] | length')
    isvc_not_ready=$(( isvc_total - isvc_ready ))
fi

# ---- TrainJobs ----
trainjobs_total=0
trainjobs_running=0
trainjobs_completed=0
trainjobs_failed=0
trainjobs_available="true"

if ! "$CLI" api-resources --api-group="$TRAINJOB_GROUP" 2>/dev/null | grep -q "$TRAINJOB_PLURAL"; then
    trainjobs_available="false"
else
    trainjobs_json=$("$CLI" get "${TRAINJOB_PLURAL}.${TRAINJOB_GROUP}" -n "$NAMESPACE" -o json 2>/dev/null || echo '{"items":[]}')
    trainjobs_total=$(echo "$trainjobs_json" | jq '.items | length')

    # Check status conditions for each TrainJob
    trainjobs_completed=$(echo "$trainjobs_json" | jq '[.items[] | select(.status.conditions[]? | select(.type == "Complete" and .status == "True"))] | length')
    trainjobs_failed=$(echo "$trainjobs_json" | jq '[.items[] | select(.status.conditions[]? | select(.type == "Failed" and .status == "True"))] | length')
    trainjobs_running=$(( trainjobs_total - trainjobs_completed - trainjobs_failed ))
    # Guard against negative values if conditions overlap
    if (( trainjobs_running < 0 )); then
        trainjobs_running=0
    fi
fi

# ---- PersistentVolumeClaims (Storage) ----
pvcs_json=$("$CLI" get pvc -n "$NAMESPACE" -o json 2>/dev/null || echo '{"items":[]}')
pvcs_total=$(echo "$pvcs_json" | jq '.items | length')
pvcs_bound=$(echo "$pvcs_json" | jq '[.items[] | select(.status.phase == "Bound")] | length')
pvcs_total_capacity=$(echo "$pvcs_json" | jq -r '[.items[] | .spec.resources.requests.storage // "0"] | join(", ")')

# ---- Data Connections ----
connections_total=0

# Data connections are secrets with label opendatahub.io/dashboard=true
# and annotation opendatahub.io/connection-type
secrets_json=$("$CLI" get secrets -n "$NAMESPACE" -l "opendatahub.io/dashboard=true" -o json 2>/dev/null || echo '{"items":[]}')
connections_total=$(echo "$secrets_json" | jq '[.items[] | select(.metadata.annotations["opendatahub.io/connection-type"] != null)] | length')

# ---- Pipeline Server (DSPA) ----
dspa_present="false"
dspa_name=""

if "$CLI" api-resources --api-group="$DSPA_GROUP" 2>/dev/null | grep -q "$DSPA_PLURAL"; then
    dspa_json=$("$CLI" get "${DSPA_PLURAL}.${DSPA_GROUP}" -n "$NAMESPACE" -o json 2>/dev/null || echo '{"items":[]}')
    dspa_count=$(echo "$dspa_json" | jq '.items | length')
    if (( dspa_count > 0 )); then
        dspa_present="true"
        dspa_name=$(echo "$dspa_json" | jq -r '.items[0].metadata.name // ""')
    fi
fi

# ---- Output JSON Summary ----
cat <<EOF
{
  "namespace": "$NAMESPACE",
  "notebooks": {
    "total": $notebooks_total,
    "running": $notebooks_running,
    "stopped": $notebooks_stopped
  },
  "inference_services": {
    "total": $isvc_total,
    "ready": $isvc_ready,
    "not_ready": $isvc_not_ready
  },
  "trainjobs": {
    "crd_installed": $trainjobs_available,
    "total": $trainjobs_total,
    "running": $trainjobs_running,
    "completed": $trainjobs_completed,
    "failed": $trainjobs_failed
  },
  "pvcs": {
    "total": $pvcs_total,
    "bound": $pvcs_bound,
    "capacities": "$pvcs_total_capacity"
  },
  "data_connections": {
    "total": $connections_total
  },
  "pipeline_server": {
    "present": $dspa_present,
    "name": "$dspa_name"
  }
}
EOF
