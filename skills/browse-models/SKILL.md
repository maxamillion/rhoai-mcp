---
name: browse-models
description: Browse and discover models in the RHOAI Model Registry and Model Catalog. Use when the user wants to find available models for deployment or fine-tuning.
license: Apache-2.0
compatibility: Requires oc or kubectl, jq, and an OpenShift cluster with RHOAI installed.
metadata:
  author: Red Hat
  version: "1.0"
  category: exploration
---

# Browse Models

Discover models available in the RHOAI Model Registry and Model Catalog. This skill helps users find models that are registered, understand their versions and formats, and identify which serving runtimes are available to serve them.

## Workflow

### Step 1: List Registered Models from the Model Registry

Run the `list-registered-models.sh` script to query the Model Registry for all registered models.

```bash
bash scripts/list-registered-models.sh [NAMESPACE]
```

If `NAMESPACE` is omitted, the script searches for Model Registry instances across the cluster. The script will:

1. Check if the Model Registry CRD (`modelregistries.modelregistry.opendatahub.io`) exists on the cluster.
2. If the CRD exists, list all `ModelRegistry` instances and query the registry REST API for registered models and their versions.
3. If the CRD is not found, look for services with `modelregistry` in the name in the `redhat-ods-applications` namespace.
4. If no Model Registry is found at all, fall back to listing `InferenceServices` across namespaces as a view of currently deployed models.

The output is JSON containing model names, descriptions, and available versions.

### Step 2: List Model Versions

The `list-registered-models.sh` script includes version information for each model. Review the `versions` array in the output to see which versions are available, along with their state (e.g., `LIVE`, `ARCHIVED`) and any associated artifact URIs.

### Step 3: Check Serving Runtimes

Run the `list-serving-runtimes.sh` script to understand what model formats are supported on the cluster.

```bash
bash scripts/list-serving-runtimes.sh [NAMESPACE]
```

If `NAMESPACE` is omitted, the current namespace is used. The script will:

1. List `ServingRuntime` resources (`servingruntimes.serving.kserve.io`) in the target namespace.
2. List serving runtime templates from the `redhat-ods-applications` platform namespace (`templates.template.openshift.io`).
3. Extract supported model formats from each runtime.

The output is JSON with runtime names, display names, supported formats, and whether the runtime is already deployed in the namespace or available as a template.

## Notes

### Model Registry vs Model Catalog

- **Model Registry** is a cluster-local service (part of RHOAI) that tracks models registered by users. It stores model metadata, versions, and artifact locations. Models in the registry have been explicitly registered and are typically ready for deployment or already deployed.

- **Model Catalog** is an external catalog of pre-trained models (e.g., from Hugging Face, or a curated Red Hat catalog). These models may need to be downloaded and registered before they can be deployed. The Model Catalog is typically accessed through the RHOAI dashboard UI rather than a cluster API.

This skill focuses on the Model Registry and deployed models since those are queryable via cluster APIs. For Model Catalog browsing, use the RHOAI dashboard.

### Cross-referencing Results

After listing models and serving runtimes, cross-reference the model formats with the supported formats from the serving runtimes to determine which runtimes can serve each model. For example, if a model is stored in `pytorch` format, look for runtimes that list `pytorch` in their supported formats (e.g., vLLM, TGIS).
