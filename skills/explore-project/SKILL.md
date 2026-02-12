---
name: explore-project
description: Explore resources within a specific Data Science Project
user-invocable: true
allowed-tools:
  - mcp__rhoai__project_summary
  - mcp__rhoai__list_workbenches
  - mcp__rhoai__get_workbench_url
  - mcp__rhoai__list_inference_services
  - mcp__rhoai__get_model_endpoint
  - mcp__rhoai__list_training_jobs
  - mcp__rhoai__get_training_progress
  - mcp__rhoai__list_data_connections
  - mcp__rhoai__list_storage
  - mcp__rhoai__get_pipeline_server
---

# Explore a Data Science Project

Explore the resources within a specific Data Science Project on Red Hat OpenShift AI.

Ask the user for:
- **Namespace**: The project namespace to explore

## Steps

### 1. Project Overview
- Use `mcp__rhoai__project_summary` to get a compact summary
- This shows workbench, model, pipeline, and storage counts

### 2. Workbenches
- Use `mcp__rhoai__list_workbenches` to see all notebook environments
- For running workbenches, use `mcp__rhoai__get_workbench_url` to get access URLs

### 3. Deployed Models
- Use `mcp__rhoai__list_inference_services` to see deployed models
- Use `mcp__rhoai__get_model_endpoint` to get inference URLs for each model

### 4. Training Jobs
- Use `mcp__rhoai__list_training_jobs` to see current and past training jobs
- Use `mcp__rhoai__get_training_progress` for any active jobs

### 5. Data Connections
- Use `mcp__rhoai__list_data_connections` to see configured S3 connections
- These provide access to external data sources

### 6. Storage
- Use `mcp__rhoai__list_storage` to see PersistentVolumeClaims
- Check storage capacity and what's available

### 7. Pipeline Server
- Use `mcp__rhoai__get_pipeline_server` to check if pipelines are configured

Start with the project summary to get an overview.
