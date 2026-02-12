---
name: setup-project
description: Create and configure Data Science Projects on RHOAI for training or inference workloads. Use when the user wants to create a new project or set up a project for ML workflows.
license: Apache-2.0
compatibility: Requires oc or kubectl and jq. Needs an OpenShift cluster with RHOAI installed.
metadata:
  author: Red Hat
  version: "1.0"
  category: management
---

# Setup Project

Create and configure a Red Hat OpenShift AI (RHOAI) Data Science Project for
training or inference workloads. A Data Science Project is a Kubernetes namespace
with RHOAI labels and annotations that make it visible in the RHOAI dashboard.

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

### Step 2: Create the project

Create a new Data Science Project namespace with RHOAI labels and annotations.

```bash
bash scripts/create-project.sh PROJECT_NAME [--display-name "Display Name"] [--description "Description"]
```

Replace `PROJECT_NAME` with the desired namespace name. Use `--display-name` to
set a human-readable name shown in the RHOAI dashboard and `--description` for
an optional project description.

### Step 3: Set serving mode (inference projects)

If this project will be used to deploy models, configure the serving mode. Skip
this step for training-only projects.

```bash
bash scripts/set-serving-mode.sh NAMESPACE MODE
```

Replace `NAMESPACE` with the project name and `MODE` with one of:
- `single` -- KServe single-model serving (sets `modelmesh-enabled: "false"`)
- `multi` -- ModelMesh multi-model serving (sets `modelmesh-enabled: "true"`)

### Step 4: Set up training runtime (training projects)

If this project will be used for training jobs, verify that a
ClusterTrainingRuntime or TrainingRuntime is available. Use the explore-cluster
skill to list available runtimes.

### Step 5: Create storage (if needed)

If the project requires persistent storage for datasets, checkpoints, or model
artifacts, use the manage-storage skill to create PersistentVolumeClaims in the
project namespace.

## Project types

- **Training project**: Create the project (Step 2), verify training runtimes
  (Step 4), and optionally create storage (Step 5). Data connections for model
  and dataset storage can be added with the manage-data-connections skill.
- **Inference project**: Create the project (Step 2), set the serving mode
  (Step 3), and then deploy models using the deploy-model skill.

## Notes

- The project name must be a valid Kubernetes namespace name: lowercase
  alphanumeric characters or hyphens, starting with a letter.
- The `opendatahub.io/dashboard: "true"` label is required for the project to
  appear in the RHOAI dashboard.
- Setting the serving mode can be changed later by re-running the
  set-serving-mode script with a different mode.
