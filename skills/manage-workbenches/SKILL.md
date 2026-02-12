---
name: manage-workbenches
description: Manage Jupyter workbench lifecycle on RHOAI - create, start, stop, and list workbenches. Use when the user wants to work with notebook environments.
license: Apache-2.0
compatibility: Requires oc or kubectl and jq. Needs RHOAI with Kubeflow Notebooks operator.
metadata:
  author: Red Hat
  version: "1.0"
  category: management
---

# Manage Workbenches

Manage the full lifecycle of Jupyter workbenches (Kubeflow Notebooks) on Red Hat
OpenShift AI (RHOAI). This skill supports listing, creating, starting, stopping,
and retrieving the URL for workbenches in a Data Science Project.

## Prerequisites

- `oc` or `kubectl` CLI installed and authenticated to the cluster
- `jq` installed for JSON processing
- An OpenShift cluster with Red Hat OpenShift AI (RHOAI) installed
- Kubeflow Notebooks operator enabled

## Workflow

### Step 1: List workbenches

List all workbenches in a namespace to see what currently exists and their status.

```bash
bash scripts/list-workbenches.sh NAMESPACE
```

Replace `NAMESPACE` with the Data Science Project namespace. The output is a JSON
array with each workbench's name, image, status, stopped state, and URL.

### Step 2: Create a workbench

Create a new workbench with the specified container image and resource settings.

```bash
bash scripts/create-workbench.sh NAMESPACE NAME IMAGE [OPTIONS]
```

Required arguments:
- `NAMESPACE` - The Data Science Project namespace
- `NAME` - Name for the workbench (must be a valid Kubernetes name)
- `IMAGE` - Container image for the notebook (e.g., a Jupyter notebook image)

Optional flags:
- `--cpu CPU` - CPU request and limit (default: 1)
- `--memory MEM` - Memory request and limit (default: 4Gi)
- `--gpu GPU` - Number of GPUs to request (default: 0)
- `--storage-size SIZE` - PVC storage size (default: 10Gi)
- `--display-name DISPLAY` - Human-readable display name
- `--dry-run` - Print the manifest without applying it

Example:

```bash
bash scripts/create-workbench.sh my-project my-workbench \
    image-registry.openshift-image-registry.svc:5000/redhat-ods-applications/jupyter-minimal-ubi9-python-3.11:2024.2 \
    --cpu 2 --memory 8Gi --storage-size 20Gi --display-name "My Workbench"
```

The script creates a PersistentVolumeClaim for the workbench storage and then
creates the Notebook custom resource.

### Step 3: Start or stop a workbench

Start a stopped workbench:

```bash
bash scripts/start-workbench.sh NAMESPACE NAME
```

Stop a running workbench:

```bash
bash scripts/stop-workbench.sh NAMESPACE NAME
```

Starting removes the `kubeflow-resource-stopped` annotation from the Notebook
resource, which causes the controller to create the workbench pod. Stopping adds
this annotation, which causes the controller to delete the pod.

### Step 4: Get workbench URL

After a workbench is running, its URL is included in the output from the list
command (Step 1). The URL is derived from the OpenShift Route that the Notebooks
controller creates for each workbench. Re-run the list command to see the URL
once the workbench is ready.

## Notes

- **Images**: Use notebook images from the RHOAI dashboard image list or from the
  `redhat-ods-applications` namespace. Common images include Jupyter minimal,
  standard data science, PyTorch, and TensorFlow variants.
- **Storage**: Each workbench gets a PVC mounted at `/opt/app-root/src`. This
  persists data across restarts but is deleted if the workbench is deleted.
- **OAuth**: The `notebooks.opendatahub.io/inject-oauth: "true"` annotation
  configures the workbench to use OpenShift OAuth for authentication, so only
  authenticated users can access it.
- **Stopping vs Deleting**: Stopping a workbench preserves the Notebook resource
  and its PVC but removes the pod. Data is preserved. Deleting the Notebook
  resource (not covered by this skill) removes everything.
- **GPU workbenches**: Use `--gpu` to request GPUs. Ensure the cluster has GPU
  nodes available (check with the explore-cluster skill).
