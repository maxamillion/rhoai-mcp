---
name: deploy-model
description: Deploy a model for inference serving on Red Hat OpenShift AI
user-invocable: true
allowed-tools:
  - mcp__rhoai__project_summary
  - mcp__rhoai__list_serving_runtimes
  - mcp__rhoai__list_data_connections
  - mcp__rhoai__list_storage
  - mcp__rhoai__deploy_model
  - mcp__rhoai__get_inference_service
  - mcp__rhoai__get_model_endpoint
  - mcp__rhoai__check_deployment_prerequisites
  - mcp__rhoai__estimate_serving_resources
  - mcp__rhoai__recommend_serving_runtime
---

# Deploy a Model for Inference

Deploy a model for inference serving on Red Hat OpenShift AI.

Ask the user for:
- **Namespace**: Target project for deployment
- **Model Name**: Name for the deployed model
- **Storage URI**: Model location (`s3://` or `pvc://`)
- **Model Format**: Model format (`onnx`, `pytorch`, `tensorflow`, etc.; default: `onnx`)

## Steps

### 1. Check Prerequisites
- Use `mcp__rhoai__project_summary` to verify the project exists
- Use `mcp__rhoai__list_serving_runtimes` to find a runtime that supports the model format

### 2. Verify Model Access
- If using S3 (`s3://`), ensure a data connection exists with `mcp__rhoai__list_data_connections`
- If using PVC (`pvc://`), verify the PVC exists with `mcp__rhoai__list_storage`

### 3. Select Runtime
- Choose a runtime that supports the model format:
  - **OpenVINO**: onnx, tensorflow, pytorch
  - **vLLM**: pytorch (LLMs)
  - **sklearn**: sklearn, xgboost
- Use `mcp__rhoai__recommend_serving_runtime` for automated recommendation

### 4. Deploy the Model
- Use `mcp__rhoai__deploy_model` with the configuration
- Configure `min_replicas=1` to avoid cold starts

### 5. Verify Deployment
- Use `mcp__rhoai__get_inference_service` to check the Ready status
- Use `mcp__rhoai__get_model_endpoint` to get the inference URL

### 6. Test the Endpoint
- The endpoint URL can be used for prediction requests
- Format depends on the serving runtime

Start by checking the available serving runtimes.
