---
name: test-endpoint
description: Test a deployed model inference endpoint on OpenShift AI
user-invocable: true
allowed-tools:
  - mcp__rhoai__get_inference_service
  - mcp__rhoai__get_model_endpoint
  - mcp__rhoai__list_serving_runtimes
  - mcp__rhoai__test_model_endpoint
---

# Test a Model Endpoint

Test a deployed model's inference endpoint on Red Hat OpenShift AI.

Ask the user for:
- **Namespace**: Namespace containing the model
- **Model Name**: Name of the deployed model

## Steps

### 1. Get Endpoint Information
- Use `mcp__rhoai__get_inference_service` to check the model status
- Verify the model shows `Ready=True`
- Use `mcp__rhoai__get_model_endpoint` to get the inference URL

### 2. Understand the Endpoint
- The URL format depends on the serving runtime:
  - **KServe v1**: `/v1/models/<model_name>:predict`
  - **KServe v2**: `/v2/models/<model_name>/infer`
  - **OpenAI-compatible (vLLM)**: `/v1/completions`

### 3. Check Serving Runtime
- Use `mcp__rhoai__list_serving_runtimes` to understand the API format
- Each runtime has different request/response schemas

### 4. Test Request Examples

**For ONNX/sklearn (KServe v1):**
```json
{"instances": [[1.0, 2.0, 3.0, 4.0]]}
```

**For vLLM (OpenAI-compatible):**
```json
{
  "model": "<model_name>",
  "prompt": "Hello, how are you?",
  "max_tokens": 100
}
```

### 5. Troubleshooting
- If endpoint not responding, check replica count
- If `min_replicas=0`, first request triggers scale-up
- Use `mcp__rhoai__get_inference_service` to see current replicas
- Use `mcp__rhoai__test_model_endpoint` for automated endpoint testing

Start by getting the endpoint information.
