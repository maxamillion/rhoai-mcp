---
name: explore-project
description: Deep-dive into a specific Data Science Project to see all its workbenches, models, training jobs, data connections, and storage. Use when the user wants to explore a particular RHOAI project.
license: Apache-2.0
compatibility: Requires oc or kubectl, jq, and an OpenShift cluster with RHOAI installed.
metadata:
  author: Red Hat
  version: "1.0"
  category: exploration
---

# Explore Project

Deep-dive into a specific Red Hat OpenShift AI (RHOAI) Data Science Project to understand all its resources and their current state.

## Workflow

### Step 1: Get project summary

Run the project summary script to collect resource counts and status information for the target namespace:

```bash
bash scripts/project-summary.sh NAMESPACE
```

Replace `NAMESPACE` with the name of the Data Science Project (Kubernetes namespace) to explore. The script outputs a JSON summary containing counts and status breakdowns for all RHOAI resource types in the project.

### Step 2: List workbenches, models, training jobs, connections, and storage

Based on the summary output, drill into specific resource types that are present in the project. The summary JSON includes:

- **Notebooks (Workbenches)**: Total count and how many are running vs stopped. Notebooks with the `kubeflow-resource-stopped` annotation are stopped.
- **InferenceServices (Models)**: Total count and how many have Ready=True status. These are models being served via KServe.
- **TrainJobs**: Total count and how many are actively running. Only present if the Kubeflow Training Operator is installed.
- **PersistentVolumeClaims (Storage)**: Total count of PVCs in the namespace.
- **Data Connections**: Total count of secrets labeled `opendatahub.io/dashboard=true` with the `opendatahub.io/connection-type` annotation.
- **Pipeline Server**: Whether a DataSciencePipelinesApplication exists in the namespace.

### Interpretation guidance

- A project with many stopped notebooks may indicate idle resources that could be cleaned up.
- InferenceServices that are not Ready may be in the process of deploying or may have configuration issues. Check their status conditions for details.
- TrainJobs with active/running status indicate ongoing training workloads. Monitor these for completion or errors.
- Data connections are S3-compatible storage credentials used by workbenches and pipelines. Verify they point to valid endpoints.
- The presence of a pipeline server (DSPA) indicates the project is configured for Data Science Pipelines.
- If TrainJobs are reported as "crd_not_installed", the Kubeflow Training Operator is not available on this cluster.
