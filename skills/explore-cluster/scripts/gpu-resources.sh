#!/usr/bin/env bash
# Find GPU resources across the cluster.
#
# Identifies nodes with NVIDIA GPUs, reports per-node GPU counts and product
# labels, and calculates total and available GPU capacity.
#
# Usage: ./gpu-resources.sh
# Output: JSON with per-node GPU info and cluster totals.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

CLI=$(detect_cli)

# Get all nodes with their allocatable GPU counts, requested GPU counts,
# and GPU product labels in one pass.
NODES_JSON=$("$CLI" get nodes -o json 2>/dev/null)

if [[ -z "$NODES_JSON" ]] || ! echo "$NODES_JSON" | jq empty 2>/dev/null; then
    cat <<'EOF'
{
  "nodes": [],
  "total_gpus": 0,
  "available_gpus": 0,
  "gpu_types": []
}
EOF
    exit 0
fi

# Get pods requesting GPUs to calculate usage
PODS_GPU_JSON=$("$CLI" get pods --all-namespaces -o json 2>/dev/null || echo '{"items":[]}')

# Use jq to extract GPU nodes and calculate availability
jq -n \
    --argjson nodes "$NODES_JSON" \
    --argjson pods "$PODS_GPU_JSON" \
'
# Build a map of GPU requests per node from running/pending pods
($pods.items // [] | map(
    select(.status.phase == "Running" or .status.phase == "Pending") |
    {
        node: (.spec.nodeName // "unscheduled"),
        gpus: ([.spec.containers[]?.resources.requests // {} | .["nvidia.com/gpu"] // "0" | tonumber] | add // 0)
    }
) | group_by(.node) | map({
    key: .[0].node,
    value: ([.[].gpus] | add // 0)
}) | from_entries) as $gpu_requests |

# Process each node
[
    $nodes.items[] |
    select(
        (.status.allocatable // {} | .["nvidia.com/gpu"] // "0" | tonumber) > 0
    ) |
    {
        name: .metadata.name,
        gpu_product: (.metadata.labels["nvidia.com/gpu.product"] // "unknown"),
        allocatable_gpus: (.status.allocatable["nvidia.com/gpu"] | tonumber),
        requested_gpus: ($gpu_requests[.metadata.name] // 0),
        available_gpus: (
            (.status.allocatable["nvidia.com/gpu"] | tonumber) -
            ($gpu_requests[.metadata.name] // 0)
        )
    }
] as $gpu_nodes |

# Collect unique GPU types
[$gpu_nodes[].gpu_product] | unique as $gpu_types |

{
    nodes: $gpu_nodes,
    total_gpus: ([$gpu_nodes[].allocatable_gpus] | add // 0),
    available_gpus: ([$gpu_nodes[].available_gpus] | add // 0),
    gpu_types: $gpu_types
}
'
