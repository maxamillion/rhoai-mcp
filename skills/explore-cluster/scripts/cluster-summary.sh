#!/usr/bin/env bash
# Get a compact overview of all Data Science Projects and their resources.
#
# Lists all namespaces labeled as Data Science Projects and counts
# workbenches (Notebooks), InferenceServices, and TrainJobs in each.
#
# Usage: ./cluster-summary.sh
# Output: JSON summary of projects and resource counts.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

CLI=$(detect_cli)

# Discover Data Science Projects (namespaces with the dashboard label)
PROJECTS=$("$CLI" get namespaces \
    -l "opendatahub.io/dashboard=true" \
    -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || true)

if [[ -z "$PROJECTS" ]]; then
    cat <<'EOF'
{
  "projects": [],
  "total_projects": 0,
  "total_workbenches": 0,
  "total_inference_services": 0,
  "total_train_jobs": 0
}
EOF
    exit 0
fi

# Check which CRDs are available so we can skip gracefully
HAS_NOTEBOOKS=false
if "$CLI" api-resources --api-group="$NOTEBOOK_GROUP" 2>/dev/null | grep -q "$NOTEBOOK_PLURAL"; then
    HAS_NOTEBOOKS=true
fi

HAS_ISVC=false
if "$CLI" api-resources --api-group="$INFERENCE_SERVICE_GROUP" 2>/dev/null | grep -q "$INFERENCE_SERVICE_PLURAL"; then
    HAS_ISVC=true
fi

HAS_TRAINJOBS=false
if "$CLI" api-resources --api-group="$TRAINJOB_GROUP" 2>/dev/null | grep -q "$TRAINJOB_PLURAL"; then
    HAS_TRAINJOBS=true
fi

# Build per-project JSON array
TOTAL_WB=0
TOTAL_ISVC=0
TOTAL_TJ=0
PROJECT_JSON="["
FIRST=true

for PROJECT in $PROJECTS; do
    WB_COUNT=0
    ISVC_COUNT=0
    TJ_COUNT=0

    if $HAS_NOTEBOOKS; then
        WB_COUNT=$("$CLI" get "${NOTEBOOK_PLURAL}.${NOTEBOOK_GROUP}" \
            -n "$PROJECT" -o json 2>/dev/null \
            | jq '.items | length' 2>/dev/null || echo 0)
    fi

    if $HAS_ISVC; then
        ISVC_COUNT=$("$CLI" get "${INFERENCE_SERVICE_PLURAL}.${INFERENCE_SERVICE_GROUP}" \
            -n "$PROJECT" -o json 2>/dev/null \
            | jq '.items | length' 2>/dev/null || echo 0)
    fi

    if $HAS_TRAINJOBS; then
        TJ_COUNT=$("$CLI" get "${TRAINJOB_PLURAL}.${TRAINJOB_GROUP}" \
            -n "$PROJECT" -o json 2>/dev/null \
            | jq '.items | length' 2>/dev/null || echo 0)
    fi

    TOTAL_WB=$((TOTAL_WB + WB_COUNT))
    TOTAL_ISVC=$((TOTAL_ISVC + ISVC_COUNT))
    TOTAL_TJ=$((TOTAL_TJ + TJ_COUNT))

    if $FIRST; then
        FIRST=false
    else
        PROJECT_JSON+=","
    fi

    PROJECT_JSON+=$(cat <<ENTRY
{
    "name": "$PROJECT",
    "workbenches": $WB_COUNT,
    "inference_services": $ISVC_COUNT,
    "train_jobs": $TJ_COUNT
  }
ENTRY
)
done

PROJECT_JSON+="]"

# Assemble final output
jq -n \
    --argjson projects "$PROJECT_JSON" \
    --arg total_projects "$(echo "$PROJECTS" | wc -w | tr -d ' ')" \
    --arg total_wb "$TOTAL_WB" \
    --arg total_isvc "$TOTAL_ISVC" \
    --arg total_tj "$TOTAL_TJ" \
    '{
        projects: $projects,
        total_projects: ($total_projects | tonumber),
        total_workbenches: ($total_wb | tonumber),
        total_inference_services: ($total_isvc | tonumber),
        total_train_jobs: ($total_tj | tonumber)
    }'
