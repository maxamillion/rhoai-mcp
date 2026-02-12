---
name: whats-running
description: Quick status check of all active workloads in the RHOAI cluster
user-invocable: true
allowed-tools:
  - mcp__rhoai__cluster_summary
  - mcp__rhoai__list_training_jobs
  - mcp__rhoai__get_training_progress
  - mcp__rhoai__list_workbenches
  - mcp__rhoai__list_inference_services
---

# What's Running

Quick status check of all active workloads in the Red Hat OpenShift AI cluster.

## Steps

### 1. Quick Overview
- Use `mcp__rhoai__cluster_summary` for a compact view of everything running
- This shows workbench count, training jobs, and deployed models

### 2. Active Training Jobs
- For each project with training, use `mcp__rhoai__list_training_jobs`
- Use `mcp__rhoai__get_training_progress` for jobs in "Running" status
- Check estimated time remaining

### 3. Running Workbenches
- Use `mcp__rhoai__list_workbenches` per project with `verbosity="minimal"`
- Look for workbenches with status "Running"

### 4. Deployed Models
- Use `mcp__rhoai__list_inference_services` per project
- Check which models are ready to serve traffic

### 5. Resource Consumption
- Review the cluster summary for current resource usage
- Identify any resource bottlenecks

Start with the cluster summary for a quick overview.
