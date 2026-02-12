---
name: troubleshoot-training
description: Diagnose and fix issues with a training job on OpenShift AI
user-invocable: true
allowed-tools:
  - mcp__rhoai__get_training_job
  - mcp__rhoai__analyze_training_failure
  - mcp__rhoai__get_job_events
  - mcp__rhoai__get_training_logs
  - mcp__rhoai__list_storage
  - mcp__rhoai__suspend_training_job
  - mcp__rhoai__resume_training_job
  - mcp__rhoai__delete_training_job
  - mcp__rhoai__train
---

# Troubleshoot a Training Job

Diagnose and fix issues with a training job on Red Hat OpenShift AI.

Ask the user for:
- **Namespace**: Namespace containing the training job
- **Job Name**: Name of the failing training job

## Steps

### 1. Get Job Status
- Use `mcp__rhoai__get_training_job` to see the current status and conditions
- Check if the job is Failed, Suspended, or stuck in Pending

### 2. Analyze Failure
- Use `mcp__rhoai__analyze_training_failure` for automated diagnosis
- This checks logs, events, and provides suggestions

### 3. Check Events
- Use `mcp__rhoai__get_job_events` to see Kubernetes events
- Look for: ImagePullBackOff, OOMKilled, FailedScheduling, etc.

### 4. Check Logs
- Use `mcp__rhoai__get_training_logs` to see trainer container output
- If container crashed, use `mcp__rhoai__get_training_logs` with `previous=True`

### 5. Common Issues

| Issue | Symptom | Fix |
|-------|---------|-----|
| **OOM** | OOMKilled events | Reduce `batch_size` or use `qlora` method |
| **ImagePull** | ImagePullBackOff | Check container registry access |
| **Pending** | FailedScheduling | Check GPU availability |
| **Storage** | Volume mount errors | Verify PVC with `mcp__rhoai__list_storage` |

### 6. Resolution
- If fixable, use `mcp__rhoai__suspend_training_job` then `mcp__rhoai__resume_training_job`
- If job is corrupted, use `mcp__rhoai__delete_training_job` and recreate with `mcp__rhoai__train`

Start with the job status and failure analysis.
