#!/usr/bin/env bash
# Manage the lifecycle of RHOAI resources.
#
# Supports start, stop, suspend, resume, and delete actions across
# different resource types.
#
# Usage: ./manage-lifecycle.sh ACTION TYPE NAME NAMESPACE
# Output: JSON result of the operation.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

CLI=$(detect_cli)

ACTION="${1:?Usage: manage-lifecycle.sh ACTION TYPE NAME NAMESPACE}"
NAME="${3:?Usage: manage-lifecycle.sh ACTION TYPE NAME NAMESPACE}"
NAMESPACE="${4:?Usage: manage-lifecycle.sh ACTION TYPE NAME NAMESPACE}"
TYPE="${2:?Usage: manage-lifecycle.sh ACTION TYPE NAME NAMESPACE}"

require_namespace "$NAMESPACE"

# ---- Dispatch by action and type ----

case "$TYPE" in
    workbench|notebook)
        RESOURCE="${NOTEBOOK_PLURAL}.${NOTEBOOK_GROUP}"
        case "$ACTION" in
            start)
                # Remove the kubeflow-resource-stopped annotation to start the workbench
                "$CLI" annotate "$RESOURCE" "$NAME" -n "$NAMESPACE" \
                    "kubeflow-resource-stopped-" \
                    --overwrite 2>/dev/null || \
                    die "Failed to start workbench '$NAME' in namespace '$NAMESPACE'."
                jq -n --arg name "$NAME" --arg namespace "$NAMESPACE" --arg action "start" '{
                    result: "success",
                    action: $action,
                    type: "workbench",
                    name: $name,
                    namespace: $namespace,
                    message: "Workbench started. The pod will be created shortly."
                }'
                ;;
            stop)
                # Add the kubeflow-resource-stopped annotation with current timestamp
                TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
                "$CLI" annotate "$RESOURCE" "$NAME" -n "$NAMESPACE" \
                    "kubeflow-resource-stopped=$TIMESTAMP" \
                    --overwrite 2>/dev/null || \
                    die "Failed to stop workbench '$NAME' in namespace '$NAMESPACE'."
                jq -n --arg name "$NAME" --arg namespace "$NAMESPACE" --arg action "stop" '{
                    result: "success",
                    action: $action,
                    type: "workbench",
                    name: $name,
                    namespace: $namespace,
                    message: "Workbench stopped. The pod will be terminated shortly."
                }'
                ;;
            delete)
                # Delete handled below in common delete section
                ;;
            *)
                die "Unsupported action '$ACTION' for workbench. Supported: start, stop, delete."
                ;;
        esac
        ;;
    training_job|trainjob)
        RESOURCE="${TRAINJOB_PLURAL}.${TRAINJOB_GROUP}"
        case "$ACTION" in
            suspend)
                "$CLI" patch "$RESOURCE" "$NAME" -n "$NAMESPACE" \
                    --type merge -p '{"spec":{"suspend":true}}' 2>/dev/null || \
                    die "Failed to suspend training job '$NAME' in namespace '$NAMESPACE'."
                jq -n --arg name "$NAME" --arg namespace "$NAMESPACE" --arg action "suspend" '{
                    result: "success",
                    action: $action,
                    type: "training_job",
                    name: $name,
                    namespace: $namespace,
                    message: "Training job suspended. GPU resources will be released."
                }'
                ;;
            resume)
                "$CLI" patch "$RESOURCE" "$NAME" -n "$NAMESPACE" \
                    --type merge -p '{"spec":{"suspend":false}}' 2>/dev/null || \
                    die "Failed to resume training job '$NAME' in namespace '$NAMESPACE'."
                jq -n --arg name "$NAME" --arg namespace "$NAMESPACE" --arg action "resume" '{
                    result: "success",
                    action: $action,
                    type: "training_job",
                    name: $name,
                    namespace: $namespace,
                    message: "Training job resumed. Pods will be recreated."
                }'
                ;;
            delete)
                # Delete handled below in common delete section
                ;;
            *)
                die "Unsupported action '$ACTION' for training_job. Supported: suspend, resume, delete."
                ;;
        esac
        ;;
    model|inferenceservice)
        RESOURCE="${INFERENCE_SERVICE_PLURAL}.${INFERENCE_SERVICE_GROUP}"
        if [[ "$ACTION" != "delete" ]]; then
            die "Unsupported action '$ACTION' for model. Supported: delete."
        fi
        ;;
    connection)
        RESOURCE="secret"
        if [[ "$ACTION" != "delete" ]]; then
            die "Unsupported action '$ACTION' for connection. Supported: delete."
        fi
        ;;
    storage|pvc)
        RESOURCE="pvc"
        if [[ "$ACTION" != "delete" ]]; then
            die "Unsupported action '$ACTION' for storage. Supported: delete."
        fi
        ;;
    pipeline|dspa)
        RESOURCE="${DSPA_PLURAL}.${DSPA_GROUP}"
        if [[ "$ACTION" != "delete" ]]; then
            die "Unsupported action '$ACTION' for pipeline. Supported: delete."
        fi
        ;;
    *)
        die "Unknown resource type '$TYPE'. Supported: workbench, notebook, model, inferenceservice, training_job, trainjob, connection, storage, pvc, pipeline, dspa."
        ;;
esac

# ---- Common delete handling ----

if [[ "$ACTION" == "delete" ]]; then
    # For connections, verify the secret has the dashboard label before deleting
    if [[ "$TYPE" == "connection" ]]; then
        HAS_LABEL=$("$CLI" get secret "$NAME" -n "$NAMESPACE" -o jsonpath='{.metadata.labels.opendatahub\.io/dashboard}' 2>/dev/null || echo "")
        if [[ "$HAS_LABEL" != "true" ]]; then
            die "Secret '$NAME' is not an RHOAI data connection. Refusing to delete."
        fi
    fi

    # Prompt for confirmation via stderr
    echo "WARNING: About to delete $TYPE '$NAME' in namespace '$NAMESPACE'. This action is irreversible." >&2
    echo "Proceeding with deletion..." >&2

    "$CLI" delete "$RESOURCE" "$NAME" -n "$NAMESPACE" 2>/dev/null || \
        die "Failed to delete $TYPE '$NAME' in namespace '$NAMESPACE'."

    jq -n --arg name "$NAME" --arg namespace "$NAMESPACE" --arg type "$TYPE" --arg action "delete" '{
        result: "success",
        action: $action,
        type: $type,
        name: $name,
        namespace: $namespace,
        message: "\($type) \($name) deleted from namespace \($namespace)."
    }'
fi
