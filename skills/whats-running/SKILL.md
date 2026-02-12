---
name: whats-running
description: Quick status of active workloads across the cluster including running workbenches, training jobs, and deployed models. Use when the user wants a fast snapshot of what is currently active.
license: Apache-2.0
compatibility: Requires oc or kubectl and jq. Needs an OpenShift cluster with RHOAI installed.
metadata:
  author: Red Hat
  version: "1.0"
  category: exploration
---

# What's Running

Get a quick snapshot of all active workloads across the cluster. This skill
checks for running workbenches (Kubeflow Notebooks), active training jobs
(TrainJobs), and deployed models (InferenceServices) across all namespaces
and returns a concise summary.

## Prerequisites

- `oc` or `kubectl` CLI installed and authenticated to the cluster
- `jq` installed for JSON processing
- An OpenShift cluster with Red Hat OpenShift AI (RHOAI) installed

## Workflow

### Step 1: Check cluster authentication

Verify that you are authenticated to the cluster and that RHOAI is installed.

```bash
bash skills/_shared/auth-check.sh
```

If authentication fails, run `oc login` with the appropriate cluster URL and
credentials before continuing.

### Step 2: Get active workloads

Retrieve a snapshot of all running workbenches, training jobs, and deployed
models across the cluster.

```bash
bash scripts/whats-running.sh
```

This returns a JSON object with lists of active workbenches, training jobs,
and deployed models along with a summary of total counts.

### Step 3: Summarize active workloads

Review the JSON output and present the user with a clear summary of what is
currently active in the cluster. Highlight any notable status conditions such
as models that are not ready or training jobs in a non-running phase.
