#!/usr/bin/env bash
# List all workbenches (Kubeflow Notebooks) in a namespace.
#
# Usage: ./list-workbenches.sh NAMESPACE
#
# For each workbench, extracts:
#   - name, image, status, stopped state, URL (from Route)
#
# Output: JSON array of workbench objects.

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

# ---- Check CRD ----
if ! "$CLI" api-resources --api-group="$NOTEBOOK_GROUP" 2>/dev/null | grep -q "$NOTEBOOK_PLURAL"; then
    die "Notebook CRD not found. Ensure the Kubeflow Notebooks operator is installed."
fi

# ---- List Notebooks ----
notebooks_json=$("$CLI" get "${NOTEBOOK_PLURAL}.${NOTEBOOK_GROUP}" \
    -n "$NAMESPACE" -o json 2>/dev/null || echo '{"items":[]}')

notebook_count=$(echo "$notebooks_json" | jq '.items | length')

if [[ "$notebook_count" -eq 0 ]]; then
    echo "[]"
    exit 0
fi

# ---- Build output ----
# For each notebook, extract name, image, status, stopped state, and URL
echo "$notebooks_json" | jq --arg ns "$NAMESPACE" '[.items[] | {
    name: .metadata.name,
    namespace: .metadata.namespace,
    display_name: (
        .metadata.annotations["openshift.io/display-name"] //
        .metadata.annotations["opendatahub.io/display-name"] //
        .metadata.name
    ),
    image: (
        .spec.template.spec.containers[0].image // "unknown"
    ),
    status: (
        if .metadata.annotations["kubeflow-resource-stopped"] != null then
            "Stopped"
        elif (.status.conditions // []) | map(select(.type == "Ready" and .status == "True")) | length > 0 then
            "Running"
        elif (.status.conditions // []) | length > 0 then
            (.status.conditions | sort_by(.lastTransitionTime) | last | .type + "=" + .status)
        else
            "Unknown"
        end
    ),
    stopped: (
        .metadata.annotations["kubeflow-resource-stopped"] != null
    ),
    cpu: (
        .spec.template.spec.containers[0].resources.requests.cpu // "not set"
    ),
    memory: (
        .spec.template.spec.containers[0].resources.requests.memory // "not set"
    ),
    created: .metadata.creationTimestamp
}]' | while IFS= read -r line; do
    # Enrich with route URLs
    echo "$line" | jq --arg ns "$NAMESPACE" '[.[] | . + {
        url: null
    }]'
done | head -1 > /tmp/workbenches_$$.json

# Try to get routes for each workbench
result=$(cat /tmp/workbenches_$$.json)
enriched="["
first=true

for name in $(echo "$result" | jq -r '.[].name'); do
    route_url=""
    route_json=$("$CLI" get route "$name" -n "$NAMESPACE" -o json 2>/dev/null || true)
    if [[ -n "$route_json" ]]; then
        route_host=$(echo "$route_json" | jq -r '.spec.host // empty')
        route_tls=$(echo "$route_json" | jq -r '.spec.tls // empty')
        if [[ -n "$route_host" ]]; then
            if [[ -n "$route_tls" ]]; then
                route_url="https://${route_host}"
            else
                route_url="http://${route_host}"
            fi
        fi
    fi

    wb_json=$(echo "$result" | jq --arg name "$name" --arg url "$route_url" \
        '[.[] | select(.name == $name)][0] | .url = (if $url == "" then null else $url end)')

    if $first; then
        first=false
    else
        enriched+=","
    fi
    enriched+="$wb_json"
done

enriched+="]"

echo "$enriched" | jq '.'

# Clean up
rm -f /tmp/workbenches_$$.json
