---
name: find-gpus
description: Find available GPU resources for training or inference
user-invocable: true
allowed-tools:
  - mcp__rhoai__cluster_summary
  - mcp__rhoai__list_data_science_projects
  - mcp__rhoai__list_workbenches
  - mcp__rhoai__estimate_resources
---

# Find GPU Resources

Find available GPU resources for training or inference on Red Hat OpenShift AI.

## Steps

### 1. Cluster GPU Resources
- Use `mcp__rhoai__cluster_summary` to get an overview including GPU capacity
- Check GPU counts and availability

### 2. Current GPU Usage
- Use `mcp__rhoai__cluster_summary` to see what's running across the cluster
- Check training jobs and inference services that are using GPUs

### 3. GPU-capable Projects
- Use `mcp__rhoai__list_data_science_projects` to find projects
- Use `mcp__rhoai__list_workbenches` per project to see GPU allocations

### 4. For Training
- Use `mcp__rhoai__estimate_resources` with your model to see GPU requirements
- Compare requirements against available resources

### 5. Recommendations
- If GPUs are scarce, consider using `qlora` method (lower memory requirement)
- Check if any suspended training jobs can be cleaned up
- Consider scheduling jobs during off-peak hours

Start by checking the cluster GPU resources.
