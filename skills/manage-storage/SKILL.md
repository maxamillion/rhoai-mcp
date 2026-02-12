---
name: manage-storage
description: Manage PersistentVolumeClaims (storage) in RHOAI projects. Use when the user needs to create, list, or manage storage for workbenches, training, or model serving.
license: Apache-2.0
compatibility: Requires oc or kubectl and jq.
metadata:
  author: Red Hat
  version: "1.0"
  category: management
---

# Manage Storage

Create and manage PersistentVolumeClaims (PVCs) for storage in Red Hat OpenShift AI
Data Science Projects. Storage is used by workbenches for persisting notebooks and
data, by training jobs for datasets and checkpoints, and by model serving for model
artifacts.

## Prerequisites

- `oc` or `kubectl` CLI installed and authenticated to the cluster
- `jq` installed for JSON processing
- An OpenShift cluster with Red Hat OpenShift AI (RHOAI) installed
- A Data Science Project (namespace) already created

## Workflow

### Step 1: Check cluster authentication

Verify that you are authenticated to the cluster.

```bash
bash ../_shared/auth-check.sh
```

If authentication fails, run `oc login` with the appropriate cluster URL and
credentials before continuing.

### Step 2: List existing storage

Review what PVCs already exist in the target namespace before creating new ones.

```bash
bash scripts/list-storage.sh NAMESPACE
```

This returns a JSON array of PVCs with their name, status (Bound, Pending, Lost),
capacity, access modes, and storage class. Check for Pending PVCs which may indicate
storage class issues.

### Step 3: Create a PVC

Create a new PersistentVolumeClaim in the target namespace.

```bash
bash scripts/create-pvc.sh NAMESPACE NAME SIZE [--access-mode MODE] [--storage-class CLASS] [--dry-run]
```

Parameters:
- `NAMESPACE` - The Data Science Project namespace
- `NAME` - Name for the PVC (must be DNS-compatible)
- `SIZE` - Storage size (e.g., `10Gi`, `50Gi`, `100Gi`)
- `--access-mode MODE` - Access mode (default: `ReadWriteOnce`)
- `--storage-class CLASS` - Storage class name (omit to use cluster default)
- `--dry-run` - Print the manifest without applying it

Use `--dry-run` first to review the manifest before applying.

## Access Mode Guidance

- **ReadWriteOnce (RWO)** - Default. Use for workbench storage where only one pod
  needs access at a time. Suitable for most single-user workloads.
- **ReadWriteMany (RWX)** - Use for training checkpoints that need to be shared
  across multiple worker pods. Required for distributed training with checkpoint
  sharing. Requires a storage class that supports RWX (e.g., CephFS, NFS).
- **ReadOnlyMany (ROX)** - Use for read-only shared datasets that multiple pods
  need to access simultaneously.

## Notes

- **Storage class** defaults to the cluster default if not specified. Run
  `oc get storageclasses` to see available options.
- **Size cannot be reduced** after creation on most storage backends. Plan capacity
  accordingly; it is easier to expand than to shrink.
- **PVC labels** include `opendatahub.io/dashboard: "true"` so that the RHOAI
  dashboard recognizes and displays the PVC.
- **Pending PVCs** usually indicate that the requested storage class is not available
  or the requested size exceeds available capacity.
