---
name: manage-resources
description: Generic resource operations for RHOAI - get, list, and manage lifecycle of any RHOAI resource type. Use for general-purpose resource queries and management.
license: Apache-2.0
compatibility: Requires oc or kubectl and jq.
metadata:
  author: Red Hat
  version: "1.0"
  category: management
---

# Manage Resources

Get, list, and manage the lifecycle of any RHOAI resource type. This skill provides
a unified interface for working with workbenches, models, training jobs, data
connections, storage, and pipelines without needing to know the underlying Kubernetes
resource types and API groups.

## Prerequisites

- `oc` or `kubectl` CLI installed and authenticated to the cluster
- `jq` installed for JSON processing
- An OpenShift cluster with Red Hat OpenShift AI (RHOAI) installed

## Supported Resource Types

| Type Alias             | Kubernetes Resource                          |
|------------------------|----------------------------------------------|
| `workbench`, `notebook`| `notebooks.kubeflow.org`                     |
| `model`, `inferenceservice` | `inferenceservices.serving.kserve.io`   |
| `training_job`, `trainjob`  | `trainjobs.trainer.kubeflow.org`        |
| `connection`           | Secrets with `opendatahub.io/dashboard` label|
| `storage`, `pvc`       | `persistentvolumeclaim`                      |
| `pipeline`, `dspa`     | `datasciencepipelinesapplications.datasciencepipelinesapplications.opendatahub.io` |

## Workflow

### Step 1: Check cluster authentication

Verify that you are authenticated to the cluster.

```bash
bash ../_shared/auth-check.sh
```

If authentication fails, run `oc login` with the appropriate cluster URL and
credentials before continuing.

### Step 2: Get a specific resource

Retrieve the full details of a single resource by type, name, and namespace.

```bash
bash scripts/get-resource.sh TYPE NAME NAMESPACE
```

Returns the complete JSON representation of the resource. Useful for inspecting
status, spec, and metadata of a specific workbench, model, or training job.

### Step 3: List resources

List all resources of a given type, optionally within a specific namespace.

```bash
bash scripts/list-resources.sh TYPE [NAMESPACE]
```

For most types, `NAMESPACE` is required. For `project` type, namespace is not
needed as it lists all Data Science Projects across the cluster.

### Step 4: Manage resource lifecycle

Start, stop, suspend, resume, or delete resources.

```bash
bash scripts/manage-lifecycle.sh ACTION TYPE NAME NAMESPACE
```

Supported actions by type:
- **workbench**: `start`, `stop`, `delete`
- **training_job**: `suspend`, `resume`, `delete`
- **model**, **connection**, **storage**, **pipeline**: `delete`

## Notes

- **Type aliases** are case-sensitive. Use lowercase names as shown in the table above.
- **Workbench start/stop** works by toggling the `kubeflow-resource-stopped`
  annotation on the Notebook resource. This is the same mechanism used by the
  RHOAI dashboard.
- **Training job suspend/resume** patches `spec.suspend` on the TrainJob resource.
  A suspended job releases its GPU resources but preserves its state for later
  resumption.
- **Delete** operations are irreversible. The script will prompt for confirmation
  before deleting.
- **Projects** are namespaces labeled with `opendatahub.io/dashboard=true`. The
  list-resources script filters for this label when listing projects.
