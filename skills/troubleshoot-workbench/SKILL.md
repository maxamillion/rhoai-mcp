---
name: troubleshoot-workbench
description: Diagnose and fix issues with a workbench on OpenShift AI
user-invocable: true
allowed-tools:
  - mcp__rhoai__get_workbench
  - mcp__rhoai__resource_status
  - mcp__rhoai__list_storage
  - mcp__rhoai__get_workbench_url
  - mcp__rhoai__start_workbench
  - mcp__rhoai__stop_workbench
  - mcp__rhoai__delete_workbench
  - mcp__rhoai__create_workbench
---

# Troubleshoot a Workbench

Diagnose and fix issues with a workbench (notebook) on Red Hat OpenShift AI.

Ask the user for:
- **Namespace**: Namespace containing the workbench
- **Workbench Name**: Name of the problematic workbench

## Steps

### 1. Get Workbench Status
- Use `mcp__rhoai__get_workbench` to see the current status and configuration
- Check the pod phase and any error conditions

### 2. Check Resource Status
- Use `mcp__rhoai__resource_status` with `resource_type="workbench"` for a quick status check
- This shows if the workbench is Running, Pending, or Failed

### 3. Common Issues

**Stuck Starting:**
- Check if image is pulling: look for ImagePullBackOff in status
- Check storage: use `mcp__rhoai__list_storage` to verify PVC is Bound
- Check resources: GPU or memory may be unavailable

**Not Accessible:**
- Use `mcp__rhoai__get_workbench_url` to get the correct URL
- Verify the route exists and is properly configured

**Stopped Unexpectedly:**
- Check if manually stopped (kubeflow-resource-stopped annotation)
- Use `mcp__rhoai__start_workbench` to restart if stopped

### 4. Resolution
- If stuck, try `mcp__rhoai__stop_workbench` followed by `mcp__rhoai__start_workbench`
- If persistent issues, may need to recreate with `mcp__rhoai__delete_workbench` and `mcp__rhoai__create_workbench`

Start by getting the workbench status.
