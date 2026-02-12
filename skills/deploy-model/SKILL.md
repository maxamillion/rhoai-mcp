---
name: deploy-model
description: Deploy a model for inference on RHOAI using KServe InferenceService. Use when the user wants to deploy, serve, or host a model for predictions.
license: Apache-2.0
compatibility: Requires oc or kubectl, jq, and python3. Needs an OpenShift cluster with RHOAI and KServe installed.
metadata:
  author: Red Hat
  version: "1.0"
  category: deployment
---

# Deploy Model

Deploy a model for inference on Red Hat OpenShift AI (RHOAI) using KServe
InferenceService. This skill walks through resource estimation, prerequisite
validation, and the actual deployment of a model serving endpoint.

## Prerequisites

- `oc` or `kubectl` CLI installed and authenticated to the cluster
- `jq` installed for JSON processing
- `python3` installed for resource estimation
- An OpenShift cluster with Red Hat OpenShift AI (RHOAI) and KServe installed
- A model available in a supported storage location (S3 bucket or PVC)

## Workflow

### Step 1: Estimate serving resources

Use the resource estimation script to determine recommended GPU, memory, and CPU
settings based on the model identifier. This uses parameter count heuristics to
suggest appropriate resource requests.

```bash
python3 scripts/estimate-serving-resources.py --model-id "meta-llama/Llama-2-7b-hf"
```

Optional flags for performance-aware sizing:

```bash
python3 scripts/estimate-serving-resources.py \
    --model-id "meta-llama/Llama-2-7b-hf" \
    --target-throughput 20 \
    --target-latency-ms 50
```

Review the output JSON for `gpu_count`, `memory`, `cpu`, and
`recommended_gpu_type`. These values feed into the deployment step.

### Step 2: Check prerequisites

Validate that the namespace, serving runtimes, and storage are ready for
deployment.

```bash
bash scripts/check-deployment-prereqs.sh <NAMESPACE> <MODEL_FORMAT> <STORAGE_URI>
```

For example:

```bash
bash scripts/check-deployment-prereqs.sh my-project pytorch pvc://model-storage/llama-7b
```

Review the output JSON. Every check must show `"passed": true` before
proceeding. If a check fails, resolve the issue (create the namespace, install
a runtime, bind the PVC, etc.) and re-run.

### Step 3: Deploy the model

Create the InferenceService to deploy the model for serving.

```bash
bash scripts/deploy-inferenceservice.sh <NAMESPACE> <NAME> <RUNTIME> <MODEL_FORMAT> <STORAGE_URI> [OPTIONS]
```

For example:

```bash
bash scripts/deploy-inferenceservice.sh my-project llama-7b vllm-runtime pytorch pvc://model-storage/llama-7b \
    --memory-request 16Gi --memory-limit 32Gi --gpu-count 1 --display-name "Llama 2 7B"
```

Available options:

- `--min-replicas N` - Minimum replica count (default: 1, use 0 for scale-to-zero)
- `--max-replicas N` - Maximum replica count (default: 1)
- `--cpu-request VALUE` - CPU request per replica (default: 1)
- `--cpu-limit VALUE` - CPU limit per replica (default: 2)
- `--memory-request VALUE` - Memory request per replica (default: 4Gi)
- `--memory-limit VALUE` - Memory limit per replica (default: 8Gi)
- `--gpu-count N` - Number of GPUs per replica (default: 0)
- `--display-name TEXT` - Human-readable display name
- `--dry-run` - Print the manifest without applying it

Use `--dry-run` first to inspect the manifest before applying.

### Step 4: Wait and verify deployment

After deploying, monitor the InferenceService status until it is ready.

```bash
CLI=$(command -v oc 2>/dev/null && echo oc || echo kubectl)
$CLI get inferenceservices.serving.kserve.io <NAME> -n <NAMESPACE> -w
```

The model is ready when the `READY` column shows `True`. This may take several
minutes depending on model size and whether the container image needs to be
pulled.

Once ready, use the `test-endpoint` skill to verify the model is responding
to inference requests.

## Model Format Reference

| Format       | Value        | Typical Runtimes               |
|-------------|-------------|-------------------------------|
| ONNX        | `onnx`       | OpenVINO, Triton              |
| PyTorch     | `pytorch`    | vLLM, TGIS, Triton            |
| TensorFlow  | `tensorflow` | TensorFlow Serving, Triton    |
| scikit-learn| `sklearn`    | MLServer                      |

## LLM-Specific Guidance

For large language models, prefer the **vLLM** or **TGIS** serving runtimes.
These runtimes are optimized for autoregressive text generation and support
features like continuous batching and paged attention.

- **vLLM**: Best for high-throughput LLM serving. Supports PyTorch models.
  Requires a GPU. Use the `vllm-cuda-runtime` or equivalent serving runtime.
- **TGIS**: Text Generation Inference Server from IBM. Supports PyTorch models.
  Use the `tgis-runtime` or equivalent serving runtime.

For LLMs, always set `--gpu-count` to at least 1 and size memory according to
the resource estimation output from Step 1.

## Notes

- **Scale-to-zero**: Set `--min-replicas 0` to allow the model to scale down
  when idle. The first request after idle will have higher latency (cold start).
- **Multi-GPU**: For models larger than 40GB, multiple GPUs may be required.
  The resource estimator will recommend the appropriate count.
- **Storage schemes**: Use `pvc://pvc-name/path` for PersistentVolumeClaim
  storage or `s3://bucket/path` for S3-compatible object storage (requires a
  data connection secret in the namespace).
