---
name: troubleshoot-model
description: Diagnose and fix issues with a deployed model on OpenShift AI
user-invocable: true
allowed-tools:
  - mcp__rhoai__get_inference_service
  - mcp__rhoai__get_model_endpoint
  - mcp__rhoai__list_serving_runtimes
  - mcp__rhoai__deploy_model
  - mcp__rhoai__delete_inference_service
  - mcp__rhoai__test_model_endpoint
---

# Troubleshoot a Deployed Model

Diagnose and fix issues with a deployed model on Red Hat OpenShift AI.

Ask the user for:
- **Namespace**: Namespace containing the model
- **Model Name**: Name of the InferenceService

## Steps

### 1. Get Model Status
- Use `mcp__rhoai__get_inference_service` to see the current status
- Check the Ready condition and any failure messages

### 2. Check Endpoint
- Use `mcp__rhoai__get_model_endpoint` to see if the endpoint is available
- An empty or error URL indicates deployment issues

### 3. Common Issues

**Model Not Ready:**
- Container may be pulling or starting
- Check if model files are accessible at storage_uri
- Verify the serving runtime supports this model format

**Prediction Errors:**
- Model format may not match runtime expectations
- Input data format may be incorrect
- Memory/GPU resources may be insufficient

**Scale Issues:**
- If `min_replicas=0`, first request triggers cold start
- Check resource limits for the serving runtime

### 4. Check Related Resources
- Use `mcp__rhoai__list_serving_runtimes` to verify runtime availability
- Check data connections if model is from S3

### 5. Resolution
- Redeploy with correct configuration using `mcp__rhoai__deploy_model`
- If persistent issues, use `mcp__rhoai__delete_inference_service` and redeploy
- Use `mcp__rhoai__test_model_endpoint` to verify fix

Start by getting the inference service status.
