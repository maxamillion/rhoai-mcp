---
name: deploy-llm
description: Deploy a large language model on RHOAI with vLLM or TGIS runtime, GPU validation, and LLM-specific defaults. Use when the user wants to deploy an LLM for text generation.
license: Apache-2.0
compatibility: Requires oc or kubectl, jq, and python3. Needs an OpenShift cluster with RHOAI, KServe, and GPU nodes.
metadata:
  author: Red Hat
  version: "1.0"
  category: deployment
---

# Deploy LLM

Deploy a large language model for text generation on Red Hat OpenShift AI (RHOAI)
using KServe InferenceService with the vLLM or TGIS serving runtime. This skill
handles GPU validation, LLM-specific resource defaults, and runtime auto-detection.

## Prerequisites

- `oc` or `kubectl` CLI installed and authenticated to the cluster
- `jq` installed for JSON processing
- `python3` installed for resource estimation
- An OpenShift cluster with Red Hat OpenShift AI (RHOAI), KServe, and GPU nodes
- A model available in a supported storage location (S3 bucket or PVC)

## Workflow

### Step 1: Auth check

Verify cluster authentication and connection before proceeding.

```bash
bash skills/_shared/auth-check.sh
```

Review the output JSON. The `authenticated` field must be `true` and `has_rhoai`
should be `true` before proceeding.

### Step 2: Check LLM prerequisites

Validate that the namespace, GPU nodes, and LLM serving runtimes (vLLM or TGIS)
are available for deployment.

```bash
bash scripts/check-llm-prereqs.sh <NAMESPACE> <MODEL_ID>
```

For example:

```bash
bash scripts/check-llm-prereqs.sh my-project meta-llama/Llama-2-7b-hf
```

Review the output JSON. Every check must show `"passed": true` before
proceeding. If a check fails, resolve the issue (install GPU operator, enable
a serving runtime, etc.) and re-run.

### Step 3: Deploy the LLM

Create the InferenceService to deploy the LLM for text generation serving.

```bash
bash scripts/deploy-llm.sh <NAMESPACE> <NAME> <MODEL_ID> <STORAGE_URI> [OPTIONS]
```

For example:

```bash
bash scripts/deploy-llm.sh my-project llama-7b meta-llama/Llama-2-7b-hf pvc://model-storage/llama-7b \
    --gpu-count 1 --memory-request 16Gi --memory-limit 32Gi
```

Available options:

- `--runtime NAME` - Serving runtime name (default: auto-detect, prefers vLLM)
- `--gpu-count N` - Number of GPUs per replica (default: 1)
- `--memory-request VALUE` - Memory request per replica (default: 16Gi)
- `--memory-limit VALUE` - Memory limit per replica (default: 32Gi)
- `--min-replicas N` - Minimum replica count (default: 1)
- `--max-replicas N` - Maximum replica count (default: 1)
- `--dry-run` - Print the manifest without applying it

Use `--dry-run` first to inspect the manifest before applying.

### Step 4: Wait and verify deployment

After deploying, monitor the InferenceService status until it is ready. Note
that LLMs typically take longer to start than smaller models due to model
loading time and GPU initialization.

```bash
CLI=$(command -v oc 2>/dev/null && echo oc || echo kubectl)
$CLI get inferenceservices.serving.kserve.io <NAME> -n <NAMESPACE> -w
```

The model is ready when the `READY` column shows `True`. For large models this
may take 10-20 minutes depending on model size, storage speed, and whether the
container image needs to be pulled.

Once ready, use the `test-endpoint` skill to verify the model is responding
to inference requests.

## Model Sizing Guide

| Model Size | GPU Memory | Recommended GPU | Example Models |
|-----------|-----------|----------------|---------------|
| 7B | 16 GB | 1x NVIDIA T4 | Llama-2-7b, Mistral-7B |
| 13B | 26 GB | 1x A10G/A100 | Llama-2-13b |
| 34B | 70 GB | 1x A100-80GB | CodeLlama-34b |
| 70B | 140 GB | 2x A100-80GB | Llama-2-70b |

## Runtime Reference

| Runtime | Best For | Features |
|---------|---------|----------|
| vLLM | High-throughput LLM serving | Continuous batching, paged attention, tensor parallelism |
| TGIS | IBM-optimized LLM serving | Token streaming, batch inference |

## Notes

- **GPU required**: LLMs require at least one GPU. The skill defaults to 1 GPU
  and 16Gi memory, which is suitable for 7B parameter models.
- **Multi-GPU**: For models larger than 40GB, multiple GPUs are required. Set
  `--gpu-count` accordingly (see sizing guide above).
- **Scale-to-zero**: Set `--min-replicas 0` to allow the model to scale down
  when idle. The first request after idle will have significantly higher latency
  due to model loading.
- **Storage schemes**: Use `pvc://pvc-name/path` for PersistentVolumeClaim
  storage or `s3://bucket/path` for S3-compatible object storage (requires a
  data connection secret in the namespace).
