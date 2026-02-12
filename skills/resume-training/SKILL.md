---
name: resume-training
description: Resume a suspended or failed training job from checkpoint
user-invocable: true
allowed-tools:
  - mcp__rhoai__get_training_job
  - mcp__rhoai__manage_checkpoints
  - mcp__rhoai__resume_training_job
  - mcp__rhoai__analyze_training_failure
  - mcp__rhoai__get_job_events
  - mcp__rhoai__train
  - mcp__rhoai__get_training_progress
  - mcp__rhoai__get_training_logs
---

# Resume a Training Job

Resume a suspended or failed training job on Red Hat OpenShift AI from a checkpoint.

Ask the user for:
- **Namespace**: Namespace containing the training job
- **Job Name**: Name of the training job to resume

## Steps

### 1. Check Current State
- Use `mcp__rhoai__get_training_job` to see the current job status
- Use `mcp__rhoai__manage_checkpoints` to find the latest checkpoint

### 2. If Job is Suspended
- Use `mcp__rhoai__resume_training_job` to restart the job
- The job will continue from the last checkpoint automatically

### 3. If Job Failed
- Use `mcp__rhoai__analyze_training_failure` to understand why it failed
- Use `mcp__rhoai__get_job_events` to check for infrastructure issues
- Fix any issues (OOM, storage, etc.)
- You may need to create a new job with `mcp__rhoai__train` using the `checkpoint_dir` parameter

### 4. Verify Resumption
- Use `mcp__rhoai__get_training_progress` to confirm training has resumed
- Check that the epoch/step numbers continue from where they left off
- Use `mcp__rhoai__get_training_logs` to verify no errors on startup

Start by checking the current job state and checkpoint availability.
