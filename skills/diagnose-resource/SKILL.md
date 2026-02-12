---
name: diagnose-resource
description: Comprehensive resource diagnostics for workbenches, models, training jobs, and pipelines
user-invocable: false
allowed-tools:
  - mcp__rhoai__get_workbench
  - mcp__rhoai__get_inference_service
  - mcp__rhoai__get_training_job
  - mcp__rhoai__get_pipeline_server
  - mcp__rhoai__resource_status
  - mcp__rhoai__get_training_logs
  - mcp__rhoai__get_job_events
  - mcp__rhoai__analyze_training_failure
  - mcp__rhoai__list_storage
  - mcp__rhoai__list_serving_runtimes
---

# Diagnose a Resource

Comprehensive diagnostics for any RHOAI resource.
This skill is auto-discovered when Claude detects a user wants to debug or diagnose a resource.

## Diagnostic Process

### 1. Identify Resource Type
Determine the type of resource being diagnosed:
- **workbench** / **notebook**
- **model** / **inference** / **inferenceservice**
- **training_job** / **trainjob**
- **pipeline** / **dspa**

### 2. Get Resource Details
Based on type, use the appropriate tool:
- Workbench: `mcp__rhoai__get_workbench`
- Model: `mcp__rhoai__get_inference_service`
- Training: `mcp__rhoai__get_training_job`
- Pipeline: `mcp__rhoai__get_pipeline_server`

### 3. Check Status
- Use `mcp__rhoai__resource_status` for a quick health check

### 4. Gather Diagnostic Data

**For Training Jobs:**
- Use `mcp__rhoai__get_job_events` for Kubernetes events
- Use `mcp__rhoai__get_training_logs` for container logs
- Use `mcp__rhoai__analyze_training_failure` if job failed

**For Workbenches:**
- Check for ImagePullBackOff, CrashLoopBackOff, FailedScheduling
- Check volume mounts with `mcp__rhoai__list_storage`

**For Models:**
- Check serving runtime with `mcp__rhoai__list_serving_runtimes`
- Verify storage URI accessibility

### 5. Identify Issues
Look for common failure patterns:
- **OOMKilled**: Out of memory - need more resources
- **ImagePullBackOff**: Image pull failure - check registry access
- **FailedScheduling**: Insufficient resources - check GPU availability
- **CrashLoopBackOff**: Container crash loop - check logs
- **FailedMount**: Volume mount failure - check PVC status

### 6. Suggest Fixes
Provide actionable remediation steps based on the issues detected.
