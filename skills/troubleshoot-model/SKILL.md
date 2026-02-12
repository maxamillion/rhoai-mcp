---
name: troubleshoot-model
description: Diagnose and fix issues with model deployments on RHOAI. Use when a deployed model is not ready, failing, or returning errors.
license: Apache-2.0
compatibility: Requires oc or kubectl and jq. Needs RHOAI with KServe installed.
metadata:
  author: Red Hat
  version: "1.0"
  category: troubleshooting
---

# Troubleshoot Model

Diagnose and fix issues with model deployments (KServe InferenceServices) on Red
Hat OpenShift AI (RHOAI). This skill identifies common failure patterns including
model readiness issues, image pull errors, GPU scheduling failures, storage access
problems, and runtime errors, then suggests targeted fixes.

## Prerequisites

- `oc` or `kubectl` CLI installed and authenticated to the cluster
- `jq` installed for JSON processing
- KServe installed on the cluster (part of RHOAI)

## Workflow

### Step 1: Run diagnostics

Run the comprehensive diagnostic script to gather all relevant information about
the model deployment:

```bash
bash scripts/diagnose-model.sh NAMESPACE MODEL_NAME
```

Replace `NAMESPACE` with the Data Science Project namespace and `MODEL_NAME` with
the name of the InferenceService resource.

This script performs a thorough diagnosis:

1. Gets the InferenceService status and conditions
2. Gets the predictor pod status
3. Collects events for the InferenceService and its pods
4. Retrieves container logs from predictor pods
5. Checks that the serving runtime exists
6. Checks storage URI accessibility
7. Scans for common failure patterns and suggests fixes

The output is JSON containing the status, detected issues, suggested fixes,
relevant events, a log snippet, and related resource statuses.

### Step 2: Apply fixes based on diagnostics

Review the `issues_detected` and `suggested_fixes` arrays in the diagnostic
output and apply the appropriate fix. See the common issues section below for
detailed guidance.

## Common Issues and Solutions

### Model Not Ready

**Symptoms**: InferenceService shows `Ready=False` or `Ready=Unknown`, the model
endpoint is not accepting requests.

**Solutions**:
- Check the predictor pod status for crash loops or pending state
- Verify the serving runtime exists and supports the model format
- Check container logs for model loading errors
- Ensure the storage URI is accessible and contains valid model artifacts
- Wait for the model to finish loading (large models take time)

### ImagePullBackOff

**Symptoms**: Predictor pod stuck in `ImagePullBackOff` or `ErrImagePull` status.

**Solutions**:
- Verify the serving runtime container image exists and is accessible
- Check that image pull secrets are configured in the namespace
- Verify network access to the container registry
- For custom serving runtimes, ensure the image reference is correct

### FailedScheduling (GPU Issues)

**Symptoms**: Predictor pod stuck in `Pending` state, events show
`FailedScheduling` with messages about insufficient GPU resources.

**Solutions**:
- Check GPU availability with the explore-cluster skill
- Reduce the number of requested GPUs
- Verify the GPU resource name matches what the cluster provides
  (e.g., `nvidia.com/gpu`)
- Check node taints and tolerations for GPU nodes
- Wait for other GPU workloads to complete

### Storage Access Errors

**Symptoms**: Model fails to load, logs show storage-related errors such as
"model not found", "access denied", or S3 connection errors.

**Solutions**:
- For `pvc://` URIs: verify the PVC exists, is bound, and contains model files
  at the specified path
- For `s3://` URIs: verify the data connection secret exists in the namespace
  with valid credentials
- Check that the storage endpoint is reachable from the cluster
- Verify the model path within the storage location is correct

### OOMKilled

**Symptoms**: Predictor pod terminated with reason `OOMKilled`.

**Solutions**:
- Increase memory limits for the InferenceService
- Use a quantized version of the model (e.g., GPTQ, AWQ)
- Use a serving runtime that supports model quantization
- Consider using a GPU with more memory
- For vLLM, adjust `--max-model-len` to reduce memory usage

### CrashLoopBackOff

**Symptoms**: Predictor pod repeatedly restarting.

**Solutions**:
- Check container logs for error messages
- Verify the model format matches the serving runtime's supported formats
- Ensure the model artifacts are not corrupted
- Check that required environment variables are set
- Verify the serving runtime configuration is valid

### Serving Runtime Not Found

**Symptoms**: InferenceService conditions show errors about missing serving
runtime.

**Solutions**:
- List available serving runtimes with the browse-models skill
- Create or instantiate the required serving runtime in the namespace
- Verify the runtime name in the InferenceService matches an existing runtime
- Check if the runtime is a cluster-scoped or namespace-scoped resource
