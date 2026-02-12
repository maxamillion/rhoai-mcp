---
name: test-endpoint
description: Test a deployed model's inference endpoint on RHOAI. Use when the user wants to verify a deployed model is working and get the endpoint URL.
license: Apache-2.0
compatibility: Requires oc or kubectl and jq.
metadata:
  author: Red Hat
  version: "1.0"
  category: deployment
---

# Test Endpoint

Test a deployed model's inference endpoint on Red Hat OpenShift AI (RHOAI).
This skill retrieves endpoint URLs and checks the readiness status of deployed
InferenceService resources.

## Prerequisites

- `oc` or `kubectl` CLI installed and authenticated to the cluster
- `jq` installed for JSON processing
- An OpenShift cluster with a deployed InferenceService

## Workflow

### Step 1: Get endpoint info

Retrieve the external and internal URLs for a deployed model.

```bash
bash scripts/get-endpoint.sh <NAMESPACE> <MODEL_NAME>
```

For example:

```bash
bash scripts/get-endpoint.sh my-project llama-7b
```

The output JSON includes:

- `url` - The external route URL for sending inference requests
- `internal_url` - The cluster-internal URL (for in-cluster clients)
- `status` - Whether the endpoint is `Ready` or `NotReady`

If the status is `NotReady`, the model is still starting up or has an issue.
Proceed to Step 2 for more detail.

### Step 2: Check model status

Get detailed status information including conditions, replica counts, and
runtime details.

```bash
bash scripts/check-model-status.sh <NAMESPACE> <MODEL_NAME>
```

For example:

```bash
bash scripts/check-model-status.sh my-project llama-7b
```

Review the output JSON:

- `ready` - Boolean indicating if the model is serving
- `conditions` - Array of Kubernetes conditions with type, status, and reason
- `replicas` - Current replica information
- `runtime` - The serving runtime being used
- `model_format` - The model format
- `storage_uri` - Where the model is loaded from

If the model is not ready, check the conditions for error messages. Common
issues include insufficient resources, image pull errors, or storage access
problems.

## Example Request Formats

Once the endpoint is ready, you can send inference requests. The request format
depends on the serving runtime.

### KServe V1 Inference Protocol (standard models)

```bash
curl -X POST "${URL}/v1/models/${MODEL_NAME}:predict" \
    -H "Content-Type: application/json" \
    -d '{"instances": [{"input": [1.0, 2.0, 3.0]}]}'
```

### OpenAI-Compatible API (vLLM runtime)

```bash
curl -X POST "${URL}/v1/completions" \
    -H "Content-Type: application/json" \
    -d '{
        "model": "'"${MODEL_NAME}"'",
        "prompt": "Hello, how are you?",
        "max_tokens": 100
    }'
```

### OpenAI Chat Completions (vLLM runtime)

```bash
curl -X POST "${URL}/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d '{
        "model": "'"${MODEL_NAME}"'",
        "messages": [{"role": "user", "content": "Hello!"}],
        "max_tokens": 100
    }'
```

### TGIS gRPC (TGIS runtime)

TGIS typically uses gRPC. Use `grpcurl` or a compatible client to send
requests to the internal URL on the appropriate port.

## Notes

- **External vs Internal URLs**: The external URL is accessible from outside
  the cluster via an OpenShift Route. The internal URL is only accessible from
  within the cluster (useful for other pods or pipelines).
- **Authentication**: Depending on cluster configuration, the external endpoint
  may require a bearer token. Check if the route has TLS and auth configured.
- **Cold starts**: If the model has scale-to-zero enabled (`minReplicas: 0`),
  the first request after idle will take longer as the pod starts up.
