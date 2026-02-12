#!/usr/bin/env bash
# List available serving runtimes for model deployment.
#
# Usage: ./list-serving-runtimes.sh [NAMESPACE]
#
# If NAMESPACE is omitted, uses the current namespace.
#
# Lists:
#   - ServingRuntimes deployed in the target namespace
#   - Serving runtime templates from the redhat-ods-applications namespace
#
# Output: JSON with runtime name, display name, supported formats, and source.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

CLI=$(detect_cli)
NAMESPACE="${1:-$(current_namespace)}"

# ---- Helper Functions ----

list_namespace_runtimes() {
    # List ServingRuntime resources in the given namespace.
    local ns="$1"
    local runtimes_json

    runtimes_json=$("$CLI" get servingruntimes.serving.kserve.io \
        -n "$ns" -o json 2>/dev/null) || true

    if [[ -z "$runtimes_json" ]] || ! echo "$runtimes_json" | jq -e '.items' &>/dev/null; then
        echo "[]"
        return
    fi

    echo "$runtimes_json" | jq --arg ns "$ns" '[.items[]? | {
        name: .metadata.name,
        display_name: (
            .metadata.annotations["openshift.io/display-name"] //
            .metadata.annotations["opendatahub.io/display-name"] //
            .metadata.name
        ),
        namespace: .metadata.namespace,
        supported_formats: [
            .spec.supportedModelFormats[]? | {
                name: .name,
                version: (.version // null),
                auto_select: (.autoSelect // false),
                priority: (.priority // null)
            }
        ],
        format_names: [.spec.supportedModelFormats[]?.name] | unique,
        containers: [.spec.containers[]?.name] | unique,
        multi_model: (.spec.multiModel // false),
        disabled: (
            .metadata.annotations["modelmesh-enabled"] == "false" or
            .metadata.labels["opendatahub.io/dashboard"] == "false"
        ),
        source: "namespace"
    }]'
}

list_template_runtimes() {
    # List serving runtime templates from the platform namespace.
    local templates_json

    # Check if template.openshift.io API group exists (OpenShift only)
    if ! "$CLI" api-resources --api-group="template.openshift.io" 2>/dev/null | grep -q "templates"; then
        echo "[]"
        return
    fi

    templates_json=$("$CLI" get templates.template.openshift.io \
        -n "$PLATFORM_NAMESPACE" -o json 2>/dev/null) || true

    if [[ -z "$templates_json" ]] || ! echo "$templates_json" | jq -e '.items' &>/dev/null; then
        echo "[]"
        return
    fi

    # Filter for serving runtime templates and extract model format info
    echo "$templates_json" | jq '[.items[]? |
        select(
            (.metadata.annotations["opendatahub.io/template-enabled"] == "true") and
            (
                (.metadata.labels["opendatahub.io/dashboard"] == "true") or
                (.metadata.annotations["tags"] // "" | test("serving"; "i")) or
                (.objects[]?.kind == "ServingRuntime")
            )
        ) | {
            name: .metadata.name,
            display_name: (
                .metadata.annotations["openshift.io/display-name"] //
                .metadata.annotations["opendatahub.io/display-name"] //
                .metadata.name
            ),
            description: (.metadata.annotations["description"] // ""),
            namespace: "'"$PLATFORM_NAMESPACE"'",
            supported_formats: [
                .objects[]? | select(.kind == "ServingRuntime") |
                .spec.supportedModelFormats[]? | {
                    name: .name,
                    version: (.version // null),
                    auto_select: (.autoSelect // false)
                }
            ],
            format_names: [
                .objects[]? | select(.kind == "ServingRuntime") |
                .spec.supportedModelFormats[]?.name
            ] | unique,
            template_name: .metadata.name,
            requires_instantiation: true,
            source: "template"
        }
    ]'
}

list_cluster_serving_runtimes() {
    # List ClusterServingRuntime resources (cluster-scoped runtimes).
    local runtimes_json

    # Check if ClusterServingRuntime CRD exists
    if ! "$CLI" api-resources --api-group="serving.kserve.io" 2>/dev/null | grep -q "clusterservingruntimes"; then
        echo "[]"
        return
    fi

    runtimes_json=$("$CLI" get clusterservingruntimes.serving.kserve.io \
        -o json 2>/dev/null) || true

    if [[ -z "$runtimes_json" ]] || ! echo "$runtimes_json" | jq -e '.items' &>/dev/null; then
        echo "[]"
        return
    fi

    echo "$runtimes_json" | jq '[.items[]? | {
        name: .metadata.name,
        display_name: (
            .metadata.annotations["openshift.io/display-name"] //
            .metadata.annotations["opendatahub.io/display-name"] //
            .metadata.name
        ),
        supported_formats: [
            .spec.supportedModelFormats[]? | {
                name: .name,
                version: (.version // null),
                auto_select: (.autoSelect // false)
            }
        ],
        format_names: [.spec.supportedModelFormats[]?.name] | unique,
        multi_model: (.spec.multiModel // false),
        source: "cluster"
    }]'
}

# ---- Main Logic ----

check_auth

# Check if ServingRuntime CRD exists
has_serving_runtimes=true
if ! "$CLI" api-resources --api-group="serving.kserve.io" 2>/dev/null | grep -q "servingruntimes"; then
    has_serving_runtimes=false
    warn "ServingRuntime CRD not found. KServe may not be installed."
fi

# Collect runtimes from all sources
namespace_runtimes="[]"
cluster_runtimes="[]"
template_runtimes="[]"

if [[ "$has_serving_runtimes" == "true" ]]; then
    info "Listing ServingRuntimes in namespace '${NAMESPACE}'..."
    namespace_runtimes=$(list_namespace_runtimes "$NAMESPACE")

    info "Checking for ClusterServingRuntimes..."
    cluster_runtimes=$(list_cluster_serving_runtimes)
fi

info "Checking for serving runtime templates in '${PLATFORM_NAMESPACE}'..."
template_runtimes=$(list_template_runtimes)

# Count results
ns_count=$(echo "$namespace_runtimes" | jq 'length')
cluster_count=$(echo "$cluster_runtimes" | jq 'length')
template_count=$(echo "$template_runtimes" | jq 'length')
total_count=$((ns_count + cluster_count + template_count))

# Collect all unique supported formats across all runtimes
all_formats=$(jq -n \
    --argjson ns "$namespace_runtimes" \
    --argjson cl "$cluster_runtimes" \
    --argjson tmpl "$template_runtimes" \
    '[$ns[]?.format_names[]?, $cl[]?.format_names[]?, $tmpl[]?.format_names[]?] | unique')

# Build final output
jq -n \
    --argjson namespace_runtimes "$namespace_runtimes" \
    --argjson cluster_runtimes "$cluster_runtimes" \
    --argjson template_runtimes "$template_runtimes" \
    --argjson all_formats "$all_formats" \
    --arg namespace "$NAMESPACE" \
    --argjson ns_count "$ns_count" \
    --argjson cluster_count "$cluster_count" \
    --argjson template_count "$template_count" \
    --argjson total_count "$total_count" \
    '{
        namespace: $namespace,
        total_runtimes: $total_count,
        namespace_runtime_count: $ns_count,
        cluster_runtime_count: $cluster_count,
        template_count: $template_count,
        all_supported_formats: $all_formats,
        namespace_runtimes: $namespace_runtimes,
        cluster_runtimes: $cluster_runtimes,
        template_runtimes: $template_runtimes,
        notes: (
            if $total_count == 0 then
                "No serving runtimes found. Ensure RHOAI is installed and KServe is enabled."
            elif $template_count > 0 then
                "Template runtimes require instantiation before use. Use the template_name with create_serving_runtime or oc process to create them in your namespace."
            else
                null
            end
        )
    }' | format_output
