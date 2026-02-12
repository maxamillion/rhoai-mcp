---
name: analyze-oom
description: Analyze and resolve Out-of-Memory issues in training jobs
user-invocable: true
allowed-tools:
  - mcp__rhoai__get_job_events
  - mcp__rhoai__get_training_logs
  - mcp__rhoai__get_training_job
  - mcp__rhoai__estimate_resources
  - mcp__rhoai__delete_training_job
  - mcp__rhoai__train
  - mcp__rhoai__get_training_progress
---

# Analyze Out-of-Memory Issues

Analyze and resolve Out-of-Memory (OOM) issues in training jobs on Red Hat OpenShift AI.

Ask the user for:
- **Namespace**: Namespace containing the training job
- **Job Name**: Name of the training job with OOM issues

## Steps

### 1. Confirm OOM Issue
- Use `mcp__rhoai__get_job_events` to look for OOMKilled events
- Use `mcp__rhoai__get_training_logs` with `previous=True` to see last output before crash

### 2. Analyze Current Configuration
- Use `mcp__rhoai__get_training_job` to see current batch_size, method, and resources

### 3. Estimate Required Resources
- Use `mcp__rhoai__estimate_resources` with the same model_id and method
- Compare estimated GPU memory vs. what was allocated

### 4. Mitigation Strategies (in order of preference)

**A. Reduce Memory Usage:**
- Switch from `lora` to `qlora` (4-bit quantization)
- Reduce `batch_size` (most impactful)
- Reduce `sequence_length` if applicable

**B. Increase Resources:**
- Request more GPUs per node
- Use multi-node training for larger models

**C. Gradient Checkpointing:**
- Enable in training config (trades compute for memory)

### 5. Create New Job
- Use `mcp__rhoai__delete_training_job` to clean up the failed job
- Use `mcp__rhoai__train` with adjusted parameters
- Preview first, then confirm

### 6. Monitor New Job
- Use `mcp__rhoai__get_training_progress` to verify training starts
- Watch memory usage in early epochs

Start by confirming the OOM issue in events and logs.
