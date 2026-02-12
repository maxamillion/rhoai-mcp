---
name: explore-cluster
description: Discover what's available in the RHOAI cluster
user-invocable: true
allowed-tools:
  - mcp__rhoai__cluster_summary
  - mcp__rhoai__list_data_science_projects
  - mcp__rhoai__project_summary
  - mcp__rhoai__list_training_runtimes
  - mcp__rhoai__list_notebook_images
---

# Explore the RHOAI Cluster

Discover what's available in this Red Hat OpenShift AI cluster.

## Steps

### 1. Cluster Overview
- Use `mcp__rhoai__cluster_summary` to get a compact overview of the entire cluster
- This shows project count, workbench status, model deployments, and resources

### 2. Available Projects
- Use `mcp__rhoai__list_data_science_projects` to see all Data Science Projects
- For each interesting project, use `mcp__rhoai__project_summary` to get details

### 3. GPU and Accelerator Availability
- Check cluster summary for GPU resource information
- Note which GPU types are available and their current usage

### 4. Training Runtimes
- Use `mcp__rhoai__list_training_runtimes` to see available training configurations
- These define what frameworks and images are available for training

### 5. Notebook Images
- Use `mcp__rhoai__list_notebook_images` to see available workbench images
- These are the IDE environments users can launch

Start with the cluster summary to get an overview.
