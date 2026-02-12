---
name: scale-model
description: Scale a model deployment's replicas on RHOAI. Use when the user wants to scale up, scale down, or enable scale-to-zero for a deployed model.
license: Apache-2.0
compatibility: Requires oc or kubectl and jq.
metadata:
  author: Red Hat
  version: "1.0"
  category: deployment
---

# Scale Model

Scale a model deployment's replicas on Red Hat OpenShift AI (RHOAI). This skill
adjusts the `minReplicas` and `maxReplicas` on a KServe InferenceService to
scale the model up, down, or enable scale-to-zero.

## Prerequisites

- `oc` or `kubectl` CLI installed and authenticated to the cluster
- `jq` installed for JSON processing
- An existing InferenceService deployment in the target namespace

## Workflow

### Step 1: Check current replicas

Before scaling, check the current replica configuration and status.

```bash
CLI=$(command -v oc 2>/dev/null && echo oc || echo kubectl)
$CLI get inferenceservices.serving.kserve.io <MODEL_NAME> -n <NAMESPACE> \
    -o jsonpath='{.spec.predictor.minReplicas}{"\t"}{.spec.predictor.maxReplicas}{"\t"}{.status.conditions}' 2>/dev/null
```

Or use the `test-endpoint` skill's `check-model-status.sh` script for a
complete status view.

### Step 2: Patch replicas

Update the replica count on the InferenceService.

```bash
bash scripts/patch-replicas.sh <NAMESPACE> <MODEL_NAME> <MIN_REPLICAS> [MAX_REPLICAS]
```

For example, to scale to 3 replicas:

```bash
bash scripts/patch-replicas.sh my-project llama-7b 3 3
```

To enable scale-to-zero:

```bash
bash scripts/patch-replicas.sh my-project llama-7b 0 1
```

To scale down to a single replica:

```bash
bash scripts/patch-replicas.sh my-project llama-7b 1 1
```

If `MAX_REPLICAS` is omitted, it defaults to the value of `MIN_REPLICAS`.

The script outputs a JSON confirmation with the previous and new replica
settings.

## Scaling Guidance

### Scale-to-Zero

Setting `minReplicas` to `0` enables Knative scale-to-zero. The model pods
will be terminated after an idle period and automatically restarted when a new
inference request arrives.

- **Pros**: Saves GPU and compute resources when the model is not in use.
- **Cons**: First request after idle incurs cold start latency (typically
  30 seconds to several minutes depending on model size and image pull time).

Scale-to-zero is recommended for development and testing environments or for
models with infrequent usage patterns.

### Scaling Up

Increase `minReplicas` and `maxReplicas` to handle higher traffic. Each
replica runs an independent copy of the model server.

- For GPU models, each replica requires its own GPU allocation. Ensure
  sufficient GPU capacity in the cluster before scaling up.
- Memory and CPU requests are per-replica. Total resource consumption scales
  linearly with replica count.

### Autoscaling

When `minReplicas` < `maxReplicas`, KServe enables autoscaling via Knative.
The system will automatically add replicas based on traffic (concurrency or
RPS targets) and remove them when traffic decreases.

- **Example**: `minReplicas=1, maxReplicas=5` keeps at least one replica warm
  and can burst to five under load.
- Autoscaling behavior can be further tuned via Knative annotations on the
  InferenceService, but the replica range set here defines the bounds.

## Notes

- **Scaling takes time**: After patching, it may take a minute or more for
  new replicas to become ready, especially for GPU models that need to load
  weights.
- **Resource limits**: Scaling is constrained by available cluster resources.
  If the cluster lacks GPUs or memory, new replicas will remain in `Pending`
  state.
- **Monitoring**: After scaling, use `oc get pods -n <NAMESPACE>` to verify
  that the expected number of predictor pods are running.
