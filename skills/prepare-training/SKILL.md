---
name: prepare-training
description: Pre-flight checks and setup for training - validates resources, storage, and runtime
user-invocable: false
allowed-tools:
  - mcp__rhoai__estimate_resources
  - mcp__rhoai__check_training_prerequisites
  - mcp__rhoai__validate_training_config
  - mcp__rhoai__list_training_runtimes
  - mcp__rhoai__setup_training_storage
  - mcp__rhoai__setup_hf_credentials
  - mcp__rhoai__cluster_summary
---

# Prepare for Training

Perform pre-flight checks and setup before starting a training job.
This skill is auto-discovered when Claude detects a user wants to train a model.

## Pre-flight Checks

### 1. Estimate Resources
- Use `mcp__rhoai__estimate_resources` with the model_id and method to determine GPU requirements
- Note the recommended GPU type and count

### 2. Check Prerequisites
- Use `mcp__rhoai__check_training_prerequisites` to verify:
  - Cluster connectivity
  - GPU availability
  - Training runtime availability
  - Checkpoint storage (if specified)
  - Model/Dataset ID format

### 3. Select Runtime
- Use `mcp__rhoai__list_training_runtimes` to find available runtimes
- Auto-select the first available if none specified

### 4. Validate Configuration
- Use `mcp__rhoai__validate_training_config` to verify all referenced resources exist

### 5. Setup Storage (if needed)
- Use `mcp__rhoai__setup_training_storage` to create a PVC for checkpoints
- Default size: 100GB

### 6. Setup Credentials (if needed)
- For gated models, use `mcp__rhoai__setup_hf_credentials`

### 7. Report Readiness
- Summarize all checks, issues, and warnings
- Provide suggested parameters for the `train` tool call
- Indicate whether training can proceed or issues need fixing first
