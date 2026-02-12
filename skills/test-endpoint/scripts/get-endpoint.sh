#!/usr/bin/env bash
# Get the inference endpoint URL and status for a deployed model.
#
# Retrieves the external and internal URLs from the InferenceService status,
# along with readiness information.
#
# Usage: ./get-endpoint.sh <NAMESPACE> <MODEL_NAME>
# Output: JSON with endpoint URLs and status.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

# ---- Argument validation ----
NAMESPACE="${1:-}"
MODEL_NAME="${2:-}"

if [[ -z "$NAMESPACE" || -z "$MODEL_NAME" ]]; then
    die "Usage: $0 <NAMESPACE> <MODEL_NAME>"
fi

CLI=$(detect_cli)

# ---- Get InferenceService ----
ISVC_JSON=$("$CLI" get inferenceservices.serving.kserve.io "$MODEL_NAME" \
    -n "$NAMESPACE" -o json 2>/dev/null)

if [[ -z "$ISVC_JSON" ]]; then
    jq -n \
        --arg name "$MODEL_NAME" \
        --arg namespace "$NAMESPACE" \
        '{
            "name": $name,
            "namespace": $namespace,
            "url": null,
            "internal_url": null,
            "status": "NotFound",
            "error": "InferenceService not found"
        }'
    exit 1
fi

# ---- Extract endpoint information ----
URL=$(echo "$ISVC_JSON" | jq -r '.status.url // empty' 2>/dev/null || echo "")
INTERNAL_URL=$(echo "$ISVC_JSON" | jq -r '.status.address.url // empty' 2>/dev/null || echo "")

# Determine status from conditions
STATUS=$(echo "$ISVC_JSON" | jq -r '
    .status.conditions // [] |
    map(select(.type == "Ready")) |
    if length > 0 then
        if .[0].status == "True" then "Ready"
        else "NotReady"
        end
    else "Unknown"
    end
' 2>/dev/null || echo "Unknown")

jq -n \
    --arg name "$MODEL_NAME" \
    --arg namespace "$NAMESPACE" \
    --arg url "$URL" \
    --arg internal_url "$INTERNAL_URL" \
    --arg status "$STATUS" \
    '{
        "name": $name,
        "namespace": $namespace,
        "url": (if $url == "" then null else $url end),
        "internal_url": (if $internal_url == "" then null else $internal_url end),
        "status": $status
    }'
