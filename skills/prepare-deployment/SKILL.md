---
name: prepare-deployment
description: Pre-flight checks for model deployment - validates runtime, storage, and resources
user-invocable: false
allowed-tools:
  - mcp__rhoai__list_serving_runtimes
  - mcp__rhoai__create_serving_runtime
  - mcp__rhoai__check_deployment_prerequisites
  - mcp__rhoai__estimate_serving_resources
  - mcp__rhoai__recommend_serving_runtime
  - mcp__rhoai__list_storage
  - mcp__rhoai__list_data_connections
  - mcp__rhoai__cluster_summary
---

# Prepare for Model Deployment

Perform pre-flight checks before deploying a model for inference.
This skill is auto-discovered when Claude detects a user wants to deploy a model.

## Pre-flight Checks

### 1. Estimate Model Resources
- Determine model size and format from the model_id
- Use `mcp__rhoai__estimate_serving_resources` to calculate GPU/memory requirements

### 2. Find Compatible Runtime
- Use `mcp__rhoai__list_serving_runtimes` to find runtimes that support the model format
- Use `mcp__rhoai__recommend_serving_runtime` for automated recommendation
- If the recommended runtime needs instantiation from a template, use `mcp__rhoai__create_serving_runtime`

### 3. Check GPU Availability
- Use `mcp__rhoai__cluster_summary` to verify sufficient GPUs are available
- Compare available GPUs against estimated requirements

### 4. Validate Storage
- If using PVC storage, use `mcp__rhoai__list_storage` to verify the PVC exists and is Bound
- If using S3, use `mcp__rhoai__list_data_connections` to verify credentials exist

### 5. Run Pre-flight Checks
- Use `mcp__rhoai__check_deployment_prerequisites` for comprehensive validation

### 6. Report Readiness
- Summarize all checks, issues, and warnings
- Provide suggested parameters for the `deploy_model` tool call
- Indicate next action: deploy_model, create_serving_runtime, or fix_issues
