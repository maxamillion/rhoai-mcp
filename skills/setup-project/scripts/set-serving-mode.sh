#!/usr/bin/env bash
# Set the model serving mode for a Data Science Project namespace.
#
# Usage: ./set-serving-mode.sh NAMESPACE MODE
#
# MODE:
#   single  - KServe single-model serving (modelmesh-enabled=false)
#   multi   - ModelMesh multi-model serving (modelmesh-enabled=true)
#
# Output: JSON confirmation of the serving mode change.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

CLI=$(detect_cli)

# ---- Validate inputs ----
NAMESPACE="${1:-}"
MODE="${2:-}"

if [[ -z "$NAMESPACE" || -z "$MODE" ]]; then
    die "Usage: $0 NAMESPACE MODE (single|multi)"
fi

require_namespace "$NAMESPACE"

# ---- Determine label value ----
case "$MODE" in
    single)
        MODELMESH_ENABLED="false"
        MODE_DESCRIPTION="KServe single-model serving"
        ;;
    multi)
        MODELMESH_ENABLED="true"
        MODE_DESCRIPTION="ModelMesh multi-model serving"
        ;;
    *)
        die "Invalid mode '$MODE'. Must be 'single' (KServe) or 'multi' (ModelMesh)."
        ;;
esac

# ---- Apply label ----
"$CLI" label namespace "$NAMESPACE" \
    "modelmesh-enabled=$MODELMESH_ENABLED" \
    --overwrite &>/dev/null

# ---- Output confirmation ----
cat <<EOF
{
  "status": "configured",
  "namespace": "$NAMESPACE",
  "serving_mode": "$MODE",
  "description": "$MODE_DESCRIPTION",
  "labels": {
    "modelmesh-enabled": "$MODELMESH_ENABLED"
  }
}
EOF
