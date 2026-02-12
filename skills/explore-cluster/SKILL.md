---
name: explore-cluster
description: Discover and explore resources in a Red Hat OpenShift AI cluster including projects, GPUs, runtimes, and workloads. Use when the user wants to know what's available in their RHOAI cluster.
license: Apache-2.0
compatibility: Requires oc or kubectl, jq, and an OpenShift cluster with RHOAI installed.
metadata:
  author: Red Hat
  version: "1.0"
  category: exploration
---

# Explore Cluster

Discover what is available in a Red Hat OpenShift AI (RHOAI) cluster. This skill
gathers information about Data Science Projects, GPU resources, training and serving
runtimes, and active workloads to give you a complete picture of the cluster.

## Prerequisites

- `oc` or `kubectl` CLI installed and authenticated to the cluster
- `jq` installed for JSON processing
- An OpenShift cluster with Red Hat OpenShift AI (RHOAI) installed

## Workflow

### Step 1: Check cluster authentication

Verify that you are authenticated to the cluster and that RHOAI is installed.

```bash
bash ../_shared/auth-check.sh
```

If authentication fails, run `oc login` with the appropriate cluster URL and
credentials before continuing.

### Step 2: Get cluster summary

Retrieve a compact overview of all Data Science Projects and the resources
running in each one.

```bash
bash scripts/cluster-summary.sh
```

This lists every Data Science Project along with counts of workbenches,
InferenceServices, and TrainJobs in each project.

### Step 3: Find GPU resources

Discover what GPU hardware is available across the cluster nodes.

```bash
bash scripts/gpu-resources.sh
```

This shows each node that has NVIDIA GPUs, the GPU product type, the total GPU
count, and how many are currently available for scheduling.

### Step 4: List training and serving runtimes

See which runtimes are available for training jobs and model serving.

```bash
bash scripts/list-runtimes.sh
```

This lists ClusterTrainingRuntimes from the Kubeflow Training Operator and
ServingRuntime templates from the RHOAI platform namespace.

### Step 5: Check what is running

Review the cluster summary output from Step 2 to identify active workloads.
Look for projects with running workbenches, deployed models, or active training
jobs. Use the explore-project skill to drill into a specific project for more
detail.

## Notes

- **Empty results are normal** on a newly installed cluster. If no Data Science
  Projects exist, create one through the RHOAI dashboard or using `oc`.
- **Missing CRDs** indicate that a particular operator component is not installed.
  For example, if TrainJobs are not found, the Kubeflow Training Operator may not
  be enabled.
- **GPU counts** show allocatable GPUs at the node level. The "available" count
  subtracts GPUs that are currently requested by running pods, so it reflects
  what can be scheduled right now.
- **ServingRuntimes** in the `redhat-ods-applications` namespace are platform
  templates. Individual projects may have additional namespace-scoped runtimes.
