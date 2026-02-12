---
name: monitor-training
description: Monitor an active training job and diagnose issues
user-invocable: true
allowed-tools:
  - mcp__rhoai__get_training_job
  - mcp__rhoai__get_training_progress
  - mcp__rhoai__get_training_logs
  - mcp__rhoai__get_job_events
  - mcp__rhoai__manage_checkpoints
  - mcp__rhoai__analyze_training_failure
  - mcp__rhoai__suspend_training_job
---

# Monitor a Training Job

Monitor an active training job on Red Hat OpenShift AI and diagnose any issues.

Ask the user for:
- **Namespace**: Namespace containing the training job
- **Job Name**: Name of the training job to monitor

## Steps

### 1. Check Job Status
- Use `mcp__rhoai__get_training_job` to get the current job status and configuration
- Use `mcp__rhoai__get_training_progress` to see real-time training metrics (epoch, loss, learning rate)

### 2. Review Logs
- Use `mcp__rhoai__get_training_logs` to check the trainer container logs
- Look for warnings or errors in the output

### 3. Check Events
- Use `mcp__rhoai__get_job_events` to see Kubernetes events for the job
- This helps identify scheduling issues, OOM conditions, or resource problems

### 4. Check Checkpoints
- Use `mcp__rhoai__manage_checkpoints` to see saved checkpoint information
- Verify checkpoints are being saved as expected

### 5. If Issues Found
- If the job is stuck or failing, use `mcp__rhoai__analyze_training_failure` for diagnosis
- Consider using `mcp__rhoai__suspend_training_job` if you need to pause and investigate

Start by getting the current job status and training progress.
