---
name: setup-inference-project
description: Set up a new Data Science Project for model serving
user-invocable: true
allowed-tools:
  - mcp__rhoai__create_data_science_project
  - mcp__rhoai__create_s3_data_connection
  - mcp__rhoai__list_serving_runtimes
  - mcp__rhoai__create_storage
  - mcp__rhoai__project_summary
  - mcp__rhoai__deploy_model
---

# Set Up an Inference Project

Set up a new Data Science Project for model serving on Red Hat OpenShift AI.

Ask the user for:
- **Project Name**: Name for the new project (DNS-compatible)
- **Display Name**: Human-readable display name (optional)

## Steps

### 1. Create the Project
- Use `mcp__rhoai__create_data_science_project` with the project name
- Set `enable_modelmesh=False` for single-model serving (KServe)
- Or `enable_modelmesh=True` for multi-model serving (ModelMesh)

### 2. Add Model Storage Connection
- Use `mcp__rhoai__create_s3_data_connection` to configure S3 access
- This is where model files are stored
- Provide: endpoint, bucket, access_key, secret_key

### 3. Check Available Serving Runtimes
- Use `mcp__rhoai__list_serving_runtimes` to see what's available
- Common options: OpenVINO, vLLM, TGIS, sklearn

### 4. Optional: Create Additional Storage
- Use `mcp__rhoai__create_storage` for model caching if needed
- Useful for large models to cache model files and avoid repeated pulls from remote storage

### 5. Verify Setup
- Use `mcp__rhoai__project_summary` to confirm configuration
- The project is ready for model deployment

### 6. Next: Deploy a Model
- Use `mcp__rhoai__deploy_model` to deploy the first model
- Specify: runtime, model_format, storage_uri

Start by creating the project.
