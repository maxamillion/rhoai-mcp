---
name: setup-training-project
description: Set up a new Data Science Project for model training
user-invocable: true
allowed-tools:
  - mcp__rhoai__create_data_science_project
  - mcp__rhoai__list_training_runtimes
  - mcp__rhoai__setup_training_runtime
  - mcp__rhoai__setup_training_storage
  - mcp__rhoai__setup_hf_credentials
  - mcp__rhoai__create_s3_data_connection
  - mcp__rhoai__project_summary
  - mcp__rhoai__check_training_prerequisites
---

# Set Up a Training Project

Set up a new Data Science Project for model training on Red Hat OpenShift AI.

Ask the user for:
- **Project Name**: Name for the new project (DNS-compatible)
- **Display Name**: Human-readable display name (optional)

## Steps

### 1. Create the Project
- Use `mcp__rhoai__create_data_science_project` with the project name
- Set display_name and add a description explaining the project purpose

### 2. Set Up Training Runtime
- Use `mcp__rhoai__list_training_runtimes` to check if a runtime exists
- If not, use `mcp__rhoai__setup_training_runtime` to create one
- The runtime defines container images and frameworks

### 3. Create Storage for Checkpoints
- Use `mcp__rhoai__setup_training_storage` to create a PVC
- Recommended size: 100GB for model checkpoints
- Use ReadWriteMany access mode for distributed training

### 4. Configure Model Access (if needed)
- For gated HuggingFace models, use `mcp__rhoai__setup_hf_credentials`
- This creates a secret with the user's HF token

### 5. Optional: Add Data Connection
- Use `mcp__rhoai__create_s3_data_connection` if S3 access is needed
- Useful for storing datasets or final model artifacts

### 6. Verify Setup
- Use `mcp__rhoai__project_summary` to confirm all resources are created
- Use `mcp__rhoai__check_training_prerequisites` with the target model

Start by creating the project.
