#!/usr/bin/env bash
# List available training and serving runtimes.
#
# Discovers ClusterTrainingRuntimes from the Kubeflow Training Operator and
# ServingRuntime templates from the RHOAI platform namespace.
#
# Usage: ./list-runtimes.sh
# Output: JSON with training_runtimes and serving_runtimes arrays.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

CLI=$(detect_cli)

# ---- Training Runtimes ----

TRAINING_RUNTIMES="[]"

if "$CLI" api-resources --api-group="$CLUSTER_TRAINING_RUNTIME_GROUP" 2>/dev/null \
    | grep -q "$CLUSTER_TRAINING_RUNTIME_PLURAL"; then

    CTR_JSON=$("$CLI" get \
        "${CLUSTER_TRAINING_RUNTIME_PLURAL}.${CLUSTER_TRAINING_RUNTIME_GROUP}" \
        -o json 2>/dev/null || echo '{"items":[]}')

    TRAINING_RUNTIMES=$(echo "$CTR_JSON" | jq '
        [.items[] | {
            name: .metadata.name,
            type: "ClusterTrainingRuntime",
            ml_framework: (
                .spec.template.spec.replicatedJobs // [] |
                map(.template.spec.containers // [] | .[].env // [] |
                    map(select(.name == "ML_FRAMEWORK")) | .[0].value // null
                ) | map(select(. != null)) | .[0] // "unknown"
            ),
            created: .metadata.creationTimestamp
        }]
    ' 2>/dev/null || echo '[]')
fi

# ---- Serving Runtimes ----

SERVING_RUNTIMES="[]"

if "$CLI" api-resources --api-group="$SERVING_RUNTIME_GROUP" 2>/dev/null \
    | grep -q "$SERVING_RUNTIME_PLURAL"; then

    SR_JSON=$("$CLI" get \
        "${SERVING_RUNTIME_PLURAL}.${SERVING_RUNTIME_GROUP}" \
        -n "$PLATFORM_NAMESPACE" \
        -o json 2>/dev/null || echo '{"items":[]}')

    SERVING_RUNTIMES=$(echo "$SR_JSON" | jq '
        [.items[] | {
            name: .metadata.name,
            type: "ServingRuntime",
            display_name: (
                .metadata.annotations["openshift.io/display-name"] //
                .metadata.name
            ),
            supported_formats: [
                .spec.supportedModelFormats // [] | .[] | {
                    name: .name,
                    version: (.version // null),
                    auto_select: (.autoSelect // false)
                }
            ],
            multi_model: (.spec.multiModel // false),
            created: .metadata.creationTimestamp
        }]
    ' 2>/dev/null || echo '[]')
fi

# ---- Assemble output ----

jq -n \
    --argjson training "$TRAINING_RUNTIMES" \
    --argjson serving "$SERVING_RUNTIMES" \
    '{
        training_runtimes: $training,
        training_runtime_count: ($training | length),
        serving_runtimes: $serving,
        serving_runtime_count: ($serving | length)
    }'
