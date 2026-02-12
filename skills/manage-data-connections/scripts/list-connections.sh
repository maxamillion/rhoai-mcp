#!/usr/bin/env bash
# List S3 data connections in an RHOAI Data Science Project.
#
# Usage: ./list-connections.sh NAMESPACE
#
# Lists all secrets labeled as RHOAI data connections and extracts
# connection details. Secret access keys are masked in the output.
#
# Output: JSON array of data connection details.

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

# ---- Fetch data connection secrets ----
# Data connections have label opendatahub.io/dashboard=true
# and annotation opendatahub.io/connection-type
SECRETS_JSON=$("$CLI" get secrets -n "$NAMESPACE" \
    -l "opendatahub.io/dashboard=true" \
    -o json 2>/dev/null || echo '{"items":[]}')

# Filter to only secrets with the connection-type annotation and extract fields
echo "$SECRETS_JSON" | jq '[
    .items[]
    | select(.metadata.annotations["opendatahub.io/connection-type"] != null)
    | {
        name: .metadata.name,
        display_name: (.metadata.annotations["openshift.io/display-name"] // .metadata.name),
        type: .metadata.annotations["opendatahub.io/connection-type"],
        endpoint: (.data["AWS_S3_ENDPOINT"] // "" | @base64d),
        bucket: (.data["AWS_S3_BUCKET"] // "" | @base64d),
        region: (.data["AWS_DEFAULT_REGION"] // "" | @base64d),
        access_key_id: (.data["AWS_ACCESS_KEY_ID"] // "" | @base64d),
        secret_access_key: "********"
    }
]'
