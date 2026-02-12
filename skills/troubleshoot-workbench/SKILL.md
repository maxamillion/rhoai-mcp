---
name: troubleshoot-workbench
description: Diagnose and fix issues with workbenches on RHOAI. Use when a workbench is failing to start, crashing, or inaccessible.
license: Apache-2.0
compatibility: Requires oc or kubectl and jq. Needs RHOAI with Kubeflow Notebooks operator.
metadata:
  author: Red Hat
  version: "1.0"
  category: troubleshooting
---

# Troubleshoot Workbench

Diagnose and fix issues with workbenches (Kubeflow Notebooks) on Red Hat OpenShift
AI (RHOAI). This skill identifies common failure patterns including image pull
errors, crash loops, scheduling failures, OOM kills, and volume mount issues,
then suggests targeted fixes.

## Prerequisites

- `oc` or `kubectl` CLI installed and authenticated to the cluster
- `jq` installed for JSON processing
- Kubeflow Notebooks operator installed on the cluster

## Workflow

### Step 1: Run diagnostics

Run the comprehensive diagnostic script to gather all relevant information about
the workbench:

```bash
bash scripts/diagnose-workbench.sh NAMESPACE WORKBENCH_NAME
```

Replace `NAMESPACE` with the Data Science Project namespace and `WORKBENCH_NAME`
with the name of the workbench (Notebook resource name).

This script performs a thorough diagnosis:

1. Gets the Notebook resource status and conditions
2. Gets the pod status for the workbench pod
3. Collects events for both the Notebook and the pod
4. Retrieves container logs (with `--tail=100`)
5. Gets previous container logs if the pod is in CrashLoopBackOff
6. Checks PVC status for mounted volumes
7. Scans for common failure patterns and suggests fixes

The output is JSON containing the status, detected issues, suggested fixes,
relevant events, a log snippet, and related resource statuses.

### Step 2: Apply fixes based on diagnostics

Review the `issues_detected` and `suggested_fixes` arrays in the diagnostic
output and apply the appropriate fix. See the common issues section below for
detailed guidance.

## Common Issues and Solutions

### ImagePullBackOff

**Symptoms**: Pod stuck in `ImagePullBackOff` or `ErrImagePull` status, events
show image pull errors.

**Solutions**:
- Verify the container image name and tag are correct
- Check that the image exists in the registry
- Ensure image pull secrets are configured in the namespace
- Verify network access to the container registry
- For private registries, ensure credentials are up to date

### CrashLoopBackOff

**Symptoms**: Pod repeatedly restarting, status shows `CrashLoopBackOff`.

**Solutions**:
- Check the previous container logs for error messages
- Verify that the notebook image is compatible with the RHOAI version
- Check that required environment variables are configured
- Ensure volume mounts are valid and accessible
- Verify that the OAuth proxy sidecar is configured correctly

### FailedScheduling

**Symptoms**: Pod stuck in `Pending` state, events show `FailedScheduling` with
messages about insufficient resources.

**Solutions**:
- Check cluster resource availability with the explore-cluster skill
- Reduce CPU or memory requests for the workbench
- If requesting GPUs, verify GPU availability on the cluster
- Check node taints and tolerations
- Wait for other workloads to complete and free resources

### OOMKilled

**Symptoms**: Pod terminated with reason `OOMKilled`, or container shows
`OOMKilled` in the last termination state.

**Solutions**:
- Increase the memory limit for the workbench
- Reduce memory usage in the notebook (close unused kernels, reduce dataset size)
- Use a workbench image with lower baseline memory requirements

### FailedMount / Volume Mount Errors

**Symptoms**: Pod stuck in `ContainerCreating` state, events show `FailedMount`
or volume-related errors.

**Solutions**:
- Verify the PVC exists and is in `Bound` state
- Check that the PVC is not already mounted by another pod (if using ReadWriteOnce)
- Ensure the storage class is available and can provision volumes
- Check for storage quota limits in the namespace

### Workbench Not Accessible

**Symptoms**: Workbench shows as running but the URL returns errors or is not
reachable.

**Solutions**:
- Check that the OpenShift Route exists for the workbench
- Verify OAuth proxy configuration
- Check the workbench pod logs for startup errors
- Ensure the notebook server process is running inside the container
