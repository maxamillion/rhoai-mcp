#!/usr/bin/env bash
# Shared utility functions for RHOAI Agent Skills
# Provides common helpers for kubectl/oc operations, auth checking,
# output formatting, and CRD validation.
#
# Usage: source "${SCRIPT_DIR}/../../_shared/lib.sh"

set -euo pipefail

# ---- CLI Detection ----

detect_cli() {
    # Prefer oc if available (OpenShift-native), fall back to kubectl
    if command -v oc &>/dev/null; then
        echo "oc"
    elif command -v kubectl &>/dev/null; then
        echo "kubectl"
    else
        echo "ERROR: Neither 'oc' nor 'kubectl' found in PATH." >&2
        exit 1
    fi
}

# ---- Authentication ----

check_auth() {
    local cli
    cli=$(detect_cli)

    if ! "$cli" auth can-i get namespaces &>/dev/null 2>&1; then
        echo "ERROR: Not authenticated to the cluster. Run '$cli login' or configure KUBECONFIG." >&2
        return 1
    fi
}

# ---- Namespace Helpers ----

require_namespace() {
    local namespace="${1:-}"
    if [[ -z "$namespace" ]]; then
        echo "ERROR: namespace is required." >&2
        return 1
    fi

    local cli
    cli=$(detect_cli)

    if ! "$cli" get namespace "$namespace" &>/dev/null 2>&1; then
        echo "ERROR: Namespace '$namespace' not found." >&2
        return 1
    fi
}

current_namespace() {
    local cli
    cli=$(detect_cli)
    "$cli" config view --minify -o jsonpath='{.contexts[0].context.namespace}' 2>/dev/null || echo "default"
}

# ---- CRD Checking ----

check_crd() {
    local group="$1"
    local plural="$2"
    local cli
    cli=$(detect_cli)

    if ! "$cli" api-resources --api-group="$group" 2>/dev/null | grep -q "$plural"; then
        echo "ERROR: CRD '$plural.$group' not found. Ensure the operator is installed." >&2
        return 1
    fi
}

# ---- Output Formatting ----

format_output() {
    # Formats JSON output for readability. Passes through if jq is available,
    # otherwise outputs raw JSON.
    if command -v jq &>/dev/null; then
        jq '.'
    else
        cat
    fi
}

format_table() {
    # Formats JSON array as a table using jq. Falls back to raw JSON.
    local fields="$1"  # jq expression for table columns, e.g. '.name, .status'
    if command -v jq &>/dev/null; then
        jq -r ".[] | [$fields] | @tsv"
    else
        cat
    fi
}

json_array_to_text() {
    # Converts a JSON array to newline-separated text
    if command -v jq &>/dev/null; then
        jq -r '.[]'
    else
        cat
    fi
}

# ---- Resource Helpers ----

get_custom_resource() {
    local cli group version plural name namespace
    cli=$(detect_cli)
    group="$1"
    version="$2"
    plural="$3"
    name="$4"
    namespace="${5:-}"

    if [[ -n "$namespace" ]]; then
        "$cli" get "$plural.$group" "$name" -n "$namespace" -o json 2>/dev/null
    else
        "$cli" get "$plural.$group" "$name" -o json 2>/dev/null
    fi
}

list_custom_resources() {
    local cli group version plural namespace
    cli=$(detect_cli)
    group="$1"
    version="$2"
    plural="$3"
    namespace="${4:-}"

    if [[ -n "$namespace" ]]; then
        "$cli" get "$plural.$group" -n "$namespace" -o json 2>/dev/null
    else
        "$cli" get "$plural.$group" -o json 2>/dev/null
    fi
}

apply_manifest() {
    local cli manifest_file namespace
    cli=$(detect_cli)
    manifest_file="$1"
    namespace="${2:-}"

    if [[ -n "$namespace" ]]; then
        "$cli" apply -f "$manifest_file" -n "$namespace"
    else
        "$cli" apply -f "$manifest_file"
    fi
}

# ---- RHOAI CRD API Paths ----
# These constants match the CRD definitions from the MCP server's domains/*/crds.py

# Training Operator
TRAINJOB_GROUP="trainer.kubeflow.org"
TRAINJOB_VERSION="v1"
TRAINJOB_PLURAL="trainjobs"

CLUSTER_TRAINING_RUNTIME_GROUP="trainer.kubeflow.org"
CLUSTER_TRAINING_RUNTIME_VERSION="v1"
CLUSTER_TRAINING_RUNTIME_PLURAL="clustertrainingruntimes"

TRAINING_RUNTIME_GROUP="trainer.kubeflow.org"
TRAINING_RUNTIME_VERSION="v1"
TRAINING_RUNTIME_PLURAL="trainingruntimes"

# KServe Inference
INFERENCE_SERVICE_GROUP="serving.kserve.io"
INFERENCE_SERVICE_VERSION="v1beta1"
INFERENCE_SERVICE_PLURAL="inferenceservices"

SERVING_RUNTIME_GROUP="serving.kserve.io"
SERVING_RUNTIME_VERSION="v1alpha1"
SERVING_RUNTIME_PLURAL="servingruntimes"

# Kubeflow Notebooks
NOTEBOOK_GROUP="kubeflow.org"
NOTEBOOK_VERSION="v1"
NOTEBOOK_PLURAL="notebooks"

# Data Science Pipelines
DSPA_GROUP="datasciencepipelinesapplications.opendatahub.io"
DSPA_VERSION="v1alpha1"
DSPA_PLURAL="datasciencepipelinesapplications"

# Platform namespace for RHOAI templates
PLATFORM_NAMESPACE="redhat-ods-applications"

# ---- Error Handling ----

die() {
    echo "ERROR: $*" >&2
    exit 1
}

warn() {
    echo "WARNING: $*" >&2
}

info() {
    echo "INFO: $*" >&2
}
