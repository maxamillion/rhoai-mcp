---
name: find-gpus
description: Discover GPU resources across the cluster, find available GPUs, identify current consumers, and calculate scheduling availability. Use when the user needs to know what GPUs are free.
license: Apache-2.0
compatibility: Requires oc or kubectl and jq. Needs an OpenShift cluster.
metadata:
  author: Red Hat
  version: "1.0"
  category: exploration
---

# Find GPUs

Discover GPU resources across a Red Hat OpenShift AI (RHOAI) cluster. This skill
identifies every node with NVIDIA GPUs, shows which pods are consuming them, and
calculates how many GPUs are available for scheduling right now.

## Prerequisites

- `oc` or `kubectl` CLI installed and authenticated to the cluster
- `jq` installed for JSON processing
- An OpenShift cluster with GPU-equipped nodes

## Workflow

### Step 1: Check cluster authentication

Verify that you are authenticated to the cluster.

```bash
bash skills/_shared/auth-check.sh
```

If authentication fails, run `oc login` with the appropriate cluster URL and
credentials before continuing.

### Step 2: Find GPU resources

Query all nodes and pods to build a complete picture of GPU availability and
consumption across the cluster.

```bash
bash scripts/find-gpus.sh
```

The output is a JSON object with three sections described below.

## Interpreting Results

### nodes

An array of objects, one per GPU-equipped node. Each entry contains:

- **name** -- the Kubernetes node name.
- **gpu_product** -- the NVIDIA GPU model label (e.g. `NVIDIA-A100-SXM4-40GB`),
  or `unknown` if the label is not set.
- **capacity** -- the total number of GPUs the node reports in `status.capacity`.
- **allocatable** -- the number of GPUs Kubernetes considers schedulable (may be
  less than capacity if some are reserved by the system).
- **used** -- the number of GPUs currently requested by running or pending pods
  on this node.
- **available** -- `allocatable - used`. This is the number of GPUs that can be
  claimed by new workloads right now.

### consumers

An array of objects listing every pod that has requested `nvidia.com/gpu`
resources. Each entry contains:

- **pod** -- the pod name.
- **namespace** -- the namespace the pod runs in.
- **gpus** -- the number of GPUs requested by the pod.

Use this list to understand who is consuming GPUs and whether any workloads
can be stopped or moved to free resources.

### summary

A top-level rollup of cluster GPU state:

- **total_gpus** -- sum of allocatable GPUs across all nodes.
- **used_gpus** -- sum of GPUs requested by running or pending pods.
- **available_gpus** -- `total_gpus - used_gpus`.

## Notes

- **No GPUs found** is a valid result. If the cluster has no GPU-equipped nodes,
  all arrays will be empty and all counts will be zero.
- **Pending pods** are included in the "used" count because their GPU requests
  block scheduling even if the pod has not started yet.
- **available_gpus** can be zero even when GPUs exist if every GPU is already
  claimed. Check the consumers list to decide whether any workloads can be
  preempted.
- **gpu_product** comes from the `nvidia.com/gpu.product` node label, which is
  set by the NVIDIA GPU Operator. If this label is missing the product will
  show as `unknown`.
