#!/usr/bin/env bash
# Find GPU resources across the cluster, identify consumers, and calculate
# scheduling availability.
#
# Usage: ./find-gpus.sh
# Output: JSON with per-node GPU info, consumer pods, and cluster totals.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

CLI=$(detect_cli)
check_auth

# ---- Gather node data ----

NODES_JSON=$("$CLI" get nodes -o json 2>/dev/null || echo '{}')

if [[ -z "$NODES_JSON" ]] || ! echo "$NODES_JSON" | jq empty 2>/dev/null; then
    NODES_JSON='{"items":[]}'
fi

# ---- Gather pod data ----

PODS_JSON=$("$CLI" get pods --all-namespaces -o json 2>/dev/null || echo '{"items":[]}')

if [[ -z "$PODS_JSON" ]] || ! echo "$PODS_JSON" | jq empty 2>/dev/null; then
    PODS_JSON='{"items":[]}'
fi

# ---- Process everything in a single jq invocation ----

jq -n \
    --argjson nodes "$NODES_JSON" \
    --argjson pods "$PODS_JSON" \
'
# Build list of pods requesting GPUs (running or pending)
[
    ($pods.items // [])[] |
    select(.status.phase == "Running" or .status.phase == "Pending") |
    {
        pod: .metadata.name,
        namespace: .metadata.namespace,
        node: (.spec.nodeName // "unscheduled"),
        gpus: (
            [.spec.containers[]?.resources.requests // {} |
             .["nvidia.com/gpu"] // "0" | tonumber] | add // 0
        )
    } |
    select(.gpus > 0)
] as $gpu_pods |

# Sum GPU requests per node
(
    $gpu_pods |
    group_by(.node) |
    map({ key: .[0].node, value: ([.[].gpus] | add // 0) }) |
    from_entries
) as $gpu_by_node |

# Build per-node GPU info
[
    ($nodes.items // [])[] |
    select(
        (.status.capacity // {} | .["nvidia.com/gpu"] // "0" | tonumber) > 0 or
        (.status.allocatable // {} | .["nvidia.com/gpu"] // "0" | tonumber) > 0
    ) |
    {
        name: .metadata.name,
        gpu_product: (.metadata.labels["nvidia.com/gpu.product"] // "unknown"),
        capacity: (.status.capacity["nvidia.com/gpu"] // "0" | tonumber),
        allocatable: (.status.allocatable["nvidia.com/gpu"] // "0" | tonumber),
        used: ($gpu_by_node[.metadata.name] // 0),
        available: (
            (.status.allocatable["nvidia.com/gpu"] // "0" | tonumber) -
            ($gpu_by_node[.metadata.name] // 0)
        )
    }
] as $gpu_nodes |

# Build consumer list (drop the internal node field)
[
    $gpu_pods[] | { pod, namespace, gpus }
] as $consumers |

# Summary
{
    nodes: $gpu_nodes,
    consumers: $consumers,
    summary: {
        total_gpus: ([$gpu_nodes[].allocatable] | add // 0),
        used_gpus: ([$gpu_nodes[].used] | add // 0),
        available_gpus: ([$gpu_nodes[].available] | add // 0)
    }
}
'
