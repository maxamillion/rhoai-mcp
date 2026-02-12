#!/usr/bin/env bash
# List available training runtimes for TrainJob creation.
#
# Lists ClusterTrainingRuntimes (cluster-scoped) and optionally
# TrainingRuntimes within a namespace. Extracts name, framework,
# and initializer types from each runtime.
#
# Usage: ./list-training-runtimes.sh [NAMESPACE]
# Output: JSON with cluster_runtimes and (optionally) namespace_runtimes arrays.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

NAMESPACE="${1:-}"

CLI=$(detect_cli)

# ---- Cluster-scoped runtimes ----

CLUSTER_RUNTIMES="[]"

if "$CLI" api-resources --api-group="$CLUSTER_TRAINING_RUNTIME_GROUP" 2>/dev/null \
    | grep -q "$CLUSTER_TRAINING_RUNTIME_PLURAL"; then

    CTR_JSON=$("$CLI" get \
        "${CLUSTER_TRAINING_RUNTIME_PLURAL}.${CLUSTER_TRAINING_RUNTIME_GROUP}" \
        -o json 2>/dev/null || echo '{"items":[]}')

    CLUSTER_RUNTIMES=$(echo "$CTR_JSON" | jq '
        [.items[] | {
            name: .metadata.name,
            scope: "cluster",
            framework: (.metadata.labels["training.kubeflow.org/framework"] // null),
            has_model_initializer: (
                [(.spec.template.spec.initializers // [])[] |
                    select(.type == "model")] | length > 0
            ),
            has_dataset_initializer: (
                [(.spec.template.spec.initializers // [])[] |
                    select(.type == "dataset")] | length > 0
            ),
            initializer_types: [
                (.spec.template.spec.initializers // [])[] | .type
            ],
            created: .metadata.creationTimestamp
        }]
    ' 2>/dev/null || echo '[]')
fi

# ---- Namespace-scoped runtimes ----

NAMESPACE_RUNTIMES="[]"

if [[ -n "$NAMESPACE" ]]; then
    if "$CLI" api-resources --api-group="$TRAINING_RUNTIME_GROUP" 2>/dev/null \
        | grep -q "$TRAINING_RUNTIME_PLURAL"; then

        TR_JSON=$("$CLI" get \
            "${TRAINING_RUNTIME_PLURAL}.${TRAINING_RUNTIME_GROUP}" \
            -n "$NAMESPACE" \
            -o json 2>/dev/null || echo '{"items":[]}')

        NAMESPACE_RUNTIMES=$(echo "$TR_JSON" | jq '
            [.items[] | {
                name: .metadata.name,
                scope: "namespace",
                namespace: .metadata.namespace,
                framework: (.metadata.labels["training.kubeflow.org/framework"] // null),
                has_model_initializer: (
                    [(.spec.template.spec.initializers // [])[] |
                        select(.type == "model")] | length > 0
                ),
                has_dataset_initializer: (
                    [(.spec.template.spec.initializers // [])[] |
                        select(.type == "dataset")] | length > 0
                ),
                initializer_types: [
                    (.spec.template.spec.initializers // [])[] | .type
                ],
                created: .metadata.creationTimestamp
            }]
        ' 2>/dev/null || echo '[]')
    fi
fi

# ---- Assemble output ----

if [[ -n "$NAMESPACE" ]]; then
    jq -n \
        --argjson cluster "$CLUSTER_RUNTIMES" \
        --argjson ns "$NAMESPACE_RUNTIMES" \
        --arg namespace "$NAMESPACE" \
        '{
            cluster_runtimes: $cluster,
            cluster_runtime_count: ($cluster | length),
            namespace_runtimes: $ns,
            namespace_runtime_count: ($ns | length),
            namespace: $namespace,
            total_count: (($cluster | length) + ($ns | length))
        }'
else
    jq -n \
        --argjson cluster "$CLUSTER_RUNTIMES" \
        '{
            cluster_runtimes: $cluster,
            cluster_runtime_count: ($cluster | length),
            total_count: ($cluster | length)
        }'
fi
