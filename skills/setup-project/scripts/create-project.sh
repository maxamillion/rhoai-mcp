#!/usr/bin/env bash
# Create a Data Science Project namespace with RHOAI labels and annotations.
#
# Usage: ./create-project.sh PROJECT_NAME [--display-name NAME] [--description DESC]
#
# Creates a Kubernetes namespace labeled for the RHOAI dashboard.
# Output: JSON confirmation of the created project.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

CLI=$(detect_cli)

# ---- Parse arguments ----
PROJECT_NAME=""
DISPLAY_NAME=""
DESCRIPTION=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --display-name)
            DISPLAY_NAME="${2:-}"
            shift 2
            ;;
        --description)
            DESCRIPTION="${2:-}"
            shift 2
            ;;
        -*)
            die "Unknown option: $1"
            ;;
        *)
            if [[ -z "$PROJECT_NAME" ]]; then
                PROJECT_NAME="$1"
            else
                die "Unexpected argument: $1"
            fi
            shift
            ;;
    esac
done

if [[ -z "$PROJECT_NAME" ]]; then
    die "Usage: $0 PROJECT_NAME [--display-name NAME] [--description DESC]"
fi

# Default display name to project name if not provided
if [[ -z "$DISPLAY_NAME" ]]; then
    DISPLAY_NAME="$PROJECT_NAME"
fi

# ---- Check if project already exists ----
if "$CLI" get namespace "$PROJECT_NAME" &>/dev/null 2>&1; then
    die "Namespace '$PROJECT_NAME' already exists."
fi

# ---- Create namespace ----
# Use 'oc new-project' if oc is available for OpenShift-native project creation,
# otherwise fall back to kubectl create namespace
if [[ "$CLI" == "oc" ]]; then
    "$CLI" new-project "$PROJECT_NAME" --display-name="$DISPLAY_NAME" --description="$DESCRIPTION" &>/dev/null 2>&1 || \
        "$CLI" create namespace "$PROJECT_NAME" &>/dev/null
else
    "$CLI" create namespace "$PROJECT_NAME" &>/dev/null
fi

# ---- Apply RHOAI labels and annotations ----
"$CLI" label namespace "$PROJECT_NAME" \
    "opendatahub.io/dashboard=true" \
    --overwrite &>/dev/null

if [[ -n "$DISPLAY_NAME" ]]; then
    "$CLI" annotate namespace "$PROJECT_NAME" \
        "openshift.io/display-name=$DISPLAY_NAME" \
        --overwrite &>/dev/null
fi

if [[ -n "$DESCRIPTION" ]]; then
    "$CLI" annotate namespace "$PROJECT_NAME" \
        "openshift.io/description=$DESCRIPTION" \
        --overwrite &>/dev/null
fi

# ---- Output confirmation ----
cat <<EOF
{
  "status": "created",
  "project": "$PROJECT_NAME",
  "display_name": "$DISPLAY_NAME",
  "description": "$DESCRIPTION",
  "labels": {
    "opendatahub.io/dashboard": "true"
  }
}
EOF
