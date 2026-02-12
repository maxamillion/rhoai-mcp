#!/usr/bin/env bash
# List registered models from the RHOAI Model Registry.
#
# Usage: ./list-registered-models.sh [NAMESPACE]
#
# If NAMESPACE is provided, look for Model Registry in that namespace.
# Otherwise, search cluster-wide for Model Registry instances.
#
# Falls back to listing InferenceServices as deployed models if no
# Model Registry is found.
#
# Output: JSON with model names, versions, and formats.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

CLI=$(detect_cli)
NAMESPACE="${1:-}"

# ---- Helper Functions ----

query_registry_api() {
    # Query the Model Registry REST API for registered models.
    # Args: $1 = registry host (host:port or URL)
    local registry_url="$1"

    # Fetch registered models from the API
    local models_json
    models_json=$(curl -s --max-time 10 \
        "${registry_url}/api/model_registry/v1alpha3/registered_models" 2>/dev/null) || true

    if [[ -z "$models_json" ]] || ! echo "$models_json" | jq -e '.items' &>/dev/null; then
        return 1
    fi

    # For each model, also fetch versions
    local result="[]"
    local model_ids
    model_ids=$(echo "$models_json" | jq -r '.items[]?.id // empty')

    for model_id in $model_ids; do
        local model_name model_desc model_state
        model_name=$(echo "$models_json" | jq -r --arg id "$model_id" '.items[] | select(.id == $id) | .name // "unknown"')
        model_desc=$(echo "$models_json" | jq -r --arg id "$model_id" '.items[] | select(.id == $id) | .description // ""')
        model_state=$(echo "$models_json" | jq -r --arg id "$model_id" '.items[] | select(.id == $id) | .state // "UNKNOWN"')

        # Fetch versions for this model
        local versions_json
        versions_json=$(curl -s --max-time 10 \
            "${registry_url}/api/model_registry/v1alpha3/registered_models/${model_id}/versions" 2>/dev/null) || true

        local versions="[]"
        if [[ -n "$versions_json" ]] && echo "$versions_json" | jq -e '.items' &>/dev/null; then
            versions=$(echo "$versions_json" | jq '[.items[]? | {
                name: (.name // "unknown"),
                state: (.state // "UNKNOWN"),
                description: (.description // ""),
                id: (.id // "")
            }]')
        fi

        result=$(echo "$result" | jq --arg name "$model_name" \
            --arg desc "$model_desc" \
            --arg state "$model_state" \
            --argjson versions "$versions" \
            '. + [{
                name: $name,
                description: $desc,
                state: $state,
                versions: $versions,
                source: "model_registry"
            }]')
    done

    echo "$result"
}

find_registry_via_crd() {
    # Find Model Registry instances using the ModelRegistry CRD.
    # Returns the registry service URL if found.
    local search_ns="${1:-}"

    local registries_json
    if [[ -n "$search_ns" ]]; then
        registries_json=$("$CLI" get modelregistries.modelregistry.opendatahub.io \
            -n "$search_ns" -o json 2>/dev/null) || return 1
    else
        registries_json=$("$CLI" get modelregistries.modelregistry.opendatahub.io \
            --all-namespaces -o json 2>/dev/null) || return 1
    fi

    local count
    count=$(echo "$registries_json" | jq '.items | length')
    if [[ "$count" -eq 0 ]]; then
        return 1
    fi

    # Get the first registry's namespace and name
    local reg_name reg_ns
    reg_name=$(echo "$registries_json" | jq -r '.items[0].metadata.name')
    reg_ns=$(echo "$registries_json" | jq -r '.items[0].metadata.namespace')

    # Find the service for this registry
    local svc_json
    svc_json=$("$CLI" get svc -n "$reg_ns" -l "component=${reg_name}" -o json 2>/dev/null) || \
    svc_json=$("$CLI" get svc -n "$reg_ns" -o json 2>/dev/null) || return 1

    # Look for a service matching the registry name
    local svc_name svc_port
    svc_name=$(echo "$svc_json" | jq -r --arg name "$reg_name" \
        '.items[] | select(.metadata.name | contains($name)) | .metadata.name' | head -1)

    if [[ -z "$svc_name" ]]; then
        # Try to find any modelregistry service
        svc_name=$(echo "$svc_json" | jq -r \
            '.items[] | select(.metadata.name | contains("modelregistry") or contains("model-registry")) | .metadata.name' | head -1)
    fi

    if [[ -z "$svc_name" ]]; then
        return 1
    fi

    # Get the REST port (typically 8080 or named http or rest-api)
    svc_port=$(echo "$svc_json" | jq -r --arg svc "$svc_name" \
        '.items[] | select(.metadata.name == $svc) | .spec.ports[] | select(.name == "http-api" or .name == "rest-api" or .name == "http" or .port == 8080) | .port' | head -1)

    if [[ -z "$svc_port" ]]; then
        # Fall back to first port
        svc_port=$(echo "$svc_json" | jq -r --arg svc "$svc_name" \
            '.items[] | select(.metadata.name == $svc) | .spec.ports[0].port')
    fi

    echo "http://${svc_name}.${reg_ns}.svc.cluster.local:${svc_port}"
}

find_registry_via_service() {
    # Find Model Registry by looking for services with modelregistry in the name.
    local search_ns="${1:-$PLATFORM_NAMESPACE}"

    local svc_json
    svc_json=$("$CLI" get svc -n "$search_ns" -o json 2>/dev/null) || return 1

    local svc_name
    svc_name=$(echo "$svc_json" | jq -r \
        '.items[] | select(.metadata.name | test("modelregistry|model-registry"; "i")) | .metadata.name' | head -1)

    if [[ -z "$svc_name" ]]; then
        return 1
    fi

    local svc_port
    svc_port=$(echo "$svc_json" | jq -r --arg svc "$svc_name" \
        '.items[] | select(.metadata.name == $svc) | .spec.ports[] | select(.name == "http-api" or .name == "rest-api" or .name == "http" or .port == 8080) | .port' | head -1)

    if [[ -z "$svc_port" ]]; then
        svc_port=$(echo "$svc_json" | jq -r --arg svc "$svc_name" \
            '.items[] | select(.metadata.name == $svc) | .spec.ports[0].port')
    fi

    echo "http://${svc_name}.${search_ns}.svc.cluster.local:${svc_port}"
}

list_deployed_models() {
    # Fallback: list InferenceServices across namespaces as deployed models.
    local isvc_json

    if [[ -n "$NAMESPACE" ]]; then
        isvc_json=$("$CLI" get inferenceservices.serving.kserve.io \
            -n "$NAMESPACE" -o json 2>/dev/null) || true
    else
        isvc_json=$("$CLI" get inferenceservices.serving.kserve.io \
            --all-namespaces -o json 2>/dev/null) || true
    fi

    if [[ -z "$isvc_json" ]] || ! echo "$isvc_json" | jq -e '.items' &>/dev/null; then
        echo "[]"
        return
    fi

    echo "$isvc_json" | jq '[.items[]? | {
        name: .metadata.name,
        namespace: .metadata.namespace,
        model_format: (.spec.predictor.model.modelFormat.name // "unknown"),
        runtime: (.spec.predictor.model.runtime // "unknown"),
        storage_uri: (.spec.predictor.model.storageUri // ""),
        status: (
            if .status.conditions then
                (.status.conditions[] | select(.type == "Ready") | .status // "Unknown")
            else
                "Unknown"
            end
        ),
        url: (.status.url // ""),
        source: "inference_service"
    }]'
}

# ---- Main Logic ----

check_auth

# Try to find the Model Registry
registry_url=""
registry_method=""

# Method 1: Check if ModelRegistry CRD exists
if "$CLI" api-resources --api-group="modelregistry.opendatahub.io" 2>/dev/null | grep -q "modelregistries"; then
    info "Found ModelRegistry CRD, searching for instances..."
    registry_url=$(find_registry_via_crd "$NAMESPACE") || true
    if [[ -n "$registry_url" ]]; then
        registry_method="crd"
    fi
fi

# Method 2: Look for Model Registry services directly
if [[ -z "$registry_url" ]]; then
    info "Looking for Model Registry services..."
    registry_url=$(find_registry_via_service "$NAMESPACE") || true
    if [[ -z "$registry_url" ]] && [[ -n "$NAMESPACE" ]] && [[ "$NAMESPACE" != "$PLATFORM_NAMESPACE" ]]; then
        # Also check the platform namespace
        registry_url=$(find_registry_via_service "$PLATFORM_NAMESPACE") || true
    fi
    if [[ -n "$registry_url" ]]; then
        registry_method="service"
    fi
fi

# Query the registry or fall back to deployed models
if [[ -n "$registry_url" ]]; then
    info "Querying Model Registry at ${registry_url}..."
    models=$(query_registry_api "$registry_url") || true

    if [[ -n "$models" ]] && [[ "$models" != "[]" ]]; then
        jq -n \
            --argjson models "$models" \
            --arg registry_url "$registry_url" \
            --arg method "$registry_method" \
            '{
                source: "model_registry",
                registry_url: $registry_url,
                discovery_method: $method,
                model_count: ($models | length),
                models: $models
            }' | format_output
        exit 0
    else
        warn "Model Registry found but returned no models or API is not accessible."
    fi
fi

# Fallback: list deployed InferenceServices
info "No Model Registry found. Listing deployed models (InferenceServices) as fallback..."

# Check if InferenceService CRD exists
if ! "$CLI" api-resources --api-group="serving.kserve.io" 2>/dev/null | grep -q "inferenceservices"; then
    jq -n '{
        source: "none",
        error: "No Model Registry or InferenceService CRD found on this cluster.",
        suggestion: "Ensure RHOAI is installed and the Model Registry component is enabled.",
        models: []
    }' | format_output
    exit 0
fi

deployed=$(list_deployed_models)
model_count=$(echo "$deployed" | jq 'length')

jq -n \
    --argjson models "$deployed" \
    --argjson count "$model_count" \
    '{
        source: "inference_services",
        note: "No Model Registry found. Showing deployed InferenceServices instead.",
        suggestion: "Enable the Model Registry component in RHOAI to track and version models.",
        model_count: $count,
        models: $models
    }' | format_output
