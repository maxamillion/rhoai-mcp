---
name: scale-model
description: Scale a model deployment up or down on OpenShift AI
user-invocable: true
allowed-tools:
  - mcp__rhoai__get_inference_service
  - mcp__rhoai__delete_inference_service
  - mcp__rhoai__deploy_model
  - mcp__rhoai__cluster_summary
---

# Scale a Model Deployment

Scale a model deployment up or down on Red Hat OpenShift AI.

Ask the user for:
- **Namespace**: Namespace containing the model
- **Model Name**: Name of the deployed model

## Steps

### 1. Check Current Configuration
- Use `mcp__rhoai__get_inference_service` to see current replica settings
- Note current `min_replicas` and `max_replicas`

### 2. Scaling Options

**Scale Up (More Capacity):**
- Increase `min_replicas` for guaranteed capacity
- Increase `max_replicas` for burst handling
- Ensure sufficient GPU/memory resources exist

**Scale Down (Save Resources):**
- Reduce `min_replicas` (minimum 0 for scale-to-zero)
- Scale-to-zero saves resources but has cold start latency

**Scale to Zero:**
- Set `min_replicas=0`
- Model pods terminate when idle
- First request triggers scale-up (may take 30s-2min)

### 3. Apply Scaling
- Currently requires redeploying with new settings
- Use `mcp__rhoai__delete_inference_service` then `mcp__rhoai__deploy_model`

### 4. Verify Scaling
- Use `mcp__rhoai__get_inference_service` to confirm replica changes
- Check that pods are running with expected count

### 5. Resource Considerations
- Check `mcp__rhoai__cluster_summary` for available capacity
- Each replica needs its own GPU allocation
- Consider cost vs. latency tradeoffs

Start by checking the current configuration.
