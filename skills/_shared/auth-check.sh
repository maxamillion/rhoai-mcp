#!/usr/bin/env bash
# Verify cluster authentication and print connection info.
# Usage: ./auth-check.sh
#
# Returns JSON with cluster info and auth status.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/lib.sh"

CLI=$(detect_cli)

# Check basic auth
if ! check_auth 2>/dev/null; then
    cat <<EOF
{
  "authenticated": false,
  "cli": "$CLI",
  "error": "Not authenticated. Run '$CLI login' or configure KUBECONFIG."
}
EOF
    exit 1
fi

# Get cluster info
CLUSTER_URL=$("$CLI" cluster-info 2>/dev/null | head -1 | grep -oP 'https?://[^ ]+' || echo "unknown")
CURRENT_NS=$(current_namespace)
USER=$("$CLI" whoami 2>/dev/null || echo "unknown")

# Check if this is an OpenShift cluster
IS_OPENSHIFT="false"
if "$CLI" api-resources --api-group=route.openshift.io &>/dev/null 2>&1; then
    IS_OPENSHIFT="true"
fi

# Check for RHOAI components
HAS_RHOAI="false"
if "$CLI" get crd datascienceclusters.datasciencecluster.opendatahub.io &>/dev/null 2>&1; then
    HAS_RHOAI="true"
fi

cat <<EOF
{
  "authenticated": true,
  "cli": "$CLI",
  "cluster_url": "$CLUSTER_URL",
  "current_namespace": "$CURRENT_NS",
  "user": "$USER",
  "is_openshift": $IS_OPENSHIFT,
  "has_rhoai": $HAS_RHOAI
}
EOF
