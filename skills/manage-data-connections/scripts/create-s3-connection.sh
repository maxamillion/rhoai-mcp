#!/usr/bin/env bash
# Create an S3 data connection secret in an RHOAI Data Science Project.
#
# Usage: ./create-s3-connection.sh NAMESPACE NAME ENDPOINT BUCKET ACCESS_KEY SECRET_KEY \
#            [--region REGION] [--display-name DISPLAY]
#
# Creates a Kubernetes secret with RHOAI labels and annotations for S3 storage.
# Output: JSON confirmation of the created data connection.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

CLI=$(detect_cli)

# ---- Parse arguments ----
NAMESPACE=""
NAME=""
ENDPOINT=""
BUCKET=""
ACCESS_KEY=""
SECRET_KEY=""
REGION="us-east-1"
DISPLAY_NAME=""

# Parse positional arguments first, then options
POSITIONAL=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --region)
            REGION="${2:-}"
            shift 2
            ;;
        --display-name)
            DISPLAY_NAME="${2:-}"
            shift 2
            ;;
        -*)
            die "Unknown option: $1"
            ;;
        *)
            POSITIONAL+=("$1")
            shift
            ;;
    esac
done

# Assign positional arguments
if [[ ${#POSITIONAL[@]} -lt 6 ]]; then
    die "Usage: $0 NAMESPACE NAME ENDPOINT BUCKET ACCESS_KEY SECRET_KEY [--region REGION] [--display-name DISPLAY]"
fi

NAMESPACE="${POSITIONAL[0]}"
NAME="${POSITIONAL[1]}"
ENDPOINT="${POSITIONAL[2]}"
BUCKET="${POSITIONAL[3]}"
ACCESS_KEY="${POSITIONAL[4]}"
SECRET_KEY="${POSITIONAL[5]}"

# Default display name to secret name if not provided
if [[ -z "$DISPLAY_NAME" ]]; then
    DISPLAY_NAME="$NAME"
fi

# ---- Validate inputs ----
require_namespace "$NAMESPACE"

# Check if secret already exists
if "$CLI" get secret "$NAME" -n "$NAMESPACE" &>/dev/null 2>&1; then
    die "Secret '$NAME' already exists in namespace '$NAMESPACE'."
fi

# ---- Create the secret ----
"$CLI" create secret generic "$NAME" -n "$NAMESPACE" \
    --from-literal="AWS_ACCESS_KEY_ID=$ACCESS_KEY" \
    --from-literal="AWS_SECRET_ACCESS_KEY=$SECRET_KEY" \
    --from-literal="AWS_S3_ENDPOINT=$ENDPOINT" \
    --from-literal="AWS_S3_BUCKET=$BUCKET" \
    --from-literal="AWS_DEFAULT_REGION=$REGION" \
    &>/dev/null

# ---- Apply RHOAI labels ----
"$CLI" label secret "$NAME" -n "$NAMESPACE" \
    "opendatahub.io/dashboard=true" \
    "opendatahub.io/managed=true" \
    --overwrite &>/dev/null

# ---- Apply RHOAI annotations ----
"$CLI" annotate secret "$NAME" -n "$NAMESPACE" \
    "opendatahub.io/connection-type=s3" \
    "openshift.io/display-name=$DISPLAY_NAME" \
    --overwrite &>/dev/null

# ---- Output confirmation ----
cat <<EOF
{
  "status": "created",
  "namespace": "$NAMESPACE",
  "name": "$NAME",
  "display_name": "$DISPLAY_NAME",
  "connection_type": "s3",
  "endpoint": "$ENDPOINT",
  "bucket": "$BUCKET",
  "region": "$REGION",
  "access_key_id": "$ACCESS_KEY",
  "secret_access_key": "********",
  "labels": {
    "opendatahub.io/dashboard": "true",
    "opendatahub.io/managed": "true"
  },
  "annotations": {
    "opendatahub.io/connection-type": "s3",
    "openshift.io/display-name": "$DISPLAY_NAME"
  }
}
EOF
