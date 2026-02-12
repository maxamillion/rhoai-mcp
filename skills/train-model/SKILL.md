---
name: train-model
description: Guide through fine-tuning a model with LoRA/QLoRA on Red Hat OpenShift AI
user-invocable: true
allowed-tools:
  - mcp__rhoai__check_training_prerequisites
  - mcp__rhoai__estimate_resources
  - mcp__rhoai__list_training_runtimes
  - mcp__rhoai__setup_training_runtime
  - mcp__rhoai__setup_training_storage
  - mcp__rhoai__setup_hf_credentials
  - mcp__rhoai__validate_training_config
  - mcp__rhoai__train
  - mcp__rhoai__get_training_progress
  - mcp__rhoai__get_training_logs
---

# Train a Model on OpenShift AI

Guide the user through fine-tuning a model with LoRA/QLoRA on Red Hat OpenShift AI.

Ask the user for:
- **Model ID**: HuggingFace model identifier (e.g., `meta-llama/Llama-2-7b-hf`)
- **Dataset ID**: HuggingFace dataset identifier (e.g., `tatsu-lab/alpaca`)
- **Namespace**: Target project/namespace for training
- **Method**: Fine-tuning method (`lora`, `qlora`, `dora`, or `full`; default: `lora`)

## Steps

### 1. Check Prerequisites
- Use `mcp__rhoai__check_training_prerequisites` to verify the namespace, model access, and GPU availability
- Use `mcp__rhoai__estimate_resources` to determine GPU memory requirements for the model and method

### 2. Prepare Infrastructure
- Use `mcp__rhoai__list_training_runtimes` to find an available training runtime
- If no runtime exists, use `mcp__rhoai__setup_training_runtime` to create one
- Use `mcp__rhoai__setup_training_storage` to create a PVC for checkpoints if needed

### 3. Configure Credentials (if needed)
- If the model is a gated model (e.g., Llama), use `mcp__rhoai__setup_hf_credentials` with the user's HuggingFace token

### 4. Validate Configuration
- Use `mcp__rhoai__validate_training_config` to verify all resources are ready

### 5. Start Training
- Use `mcp__rhoai__train` with the configuration
- First call without `confirmed=True` to preview the job spec
- Then call with `confirmed=True` to create the job

### 6. Monitor Progress
- Use `mcp__rhoai__get_training_progress` to check training metrics
- Use `mcp__rhoai__get_training_logs` if issues arise

Start by checking the prerequisites and estimating resource requirements.
