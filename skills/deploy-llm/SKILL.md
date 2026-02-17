---
name: deploy-llm
description: Deploy a Large Language Model with vLLM or TGIS on OpenShift AI
user-invocable: true
allowed-tools:
  - mcp__rhoai__cluster_summary
  - mcp__rhoai__list_serving_runtimes
  - mcp__rhoai__create_serving_runtime
  - mcp__rhoai__create_s3_data_connection
  - mcp__rhoai__deploy_model
  - mcp__rhoai__get_inference_service
  - mcp__rhoai__get_model_endpoint
  - mcp__rhoai__estimate_serving_resources
---

# Deploy a Large Language Model

Deploy a Large Language Model for inference using vLLM or TGIS on Red Hat OpenShift AI.

Ask the user for:
- **Namespace**: Target project for deployment
- **Model Name**: Name for the deployed model
- **Model ID**: HuggingFace model ID or storage path

## Steps

### 1. Check GPU Availability
- Use `mcp__rhoai__cluster_summary` to verify GPU availability
- LLMs typically require significant GPU memory (16GB+)
- Use `mcp__rhoai__estimate_serving_resources` to estimate requirements

### 2. Check Serving Runtimes
- Use `mcp__rhoai__list_serving_runtimes` to find LLM-capable runtimes
- Look for: vLLM, TGIS (Text Generation Inference Server)
- If needed, use `mcp__rhoai__create_serving_runtime` to instantiate from template

### 3. Prepare Model Storage
- If model is on HuggingFace, the serving runtime will pull it at deploy time, or pre-stage it in S3/PVC storage
- Create an S3 data connection with `mcp__rhoai__create_s3_data_connection` for model storage
- Or use a PVC with the model files

### 4. Configure GPU Resources
- LLMs need GPU allocation via the `gpu_count` parameter
- Adjust `memory_limit` based on model size

### 5. Deploy the Model
- Use `mcp__rhoai__deploy_model` with:
  - runtime: vLLM or TGIS
  - model_format: `pytorch` (typical for LLMs)
  - storage_uri pointing to model files
  - gpu_count: 1 or more based on model size

### 6. Model Sizing Guide
| Model Size | GPU Requirements |
|-----------|-----------------|
| 7B | 1x 24GB GPU or 2x 16GB GPUs |
| 13B | 2x 24GB GPUs |
| 70B | 4+ 80GB GPUs or quantized version |

### 7. Verify Deployment
- Use `mcp__rhoai__get_inference_service` to monitor startup (LLMs may take several minutes)
- Use `mcp__rhoai__get_model_endpoint` once ready

### 8. Optimize (Optional)
- Set `min_replicas=0` for scale-to-zero (cost saving, but first request has cold start latency)

Start by checking GPU availability.
