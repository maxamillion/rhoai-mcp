---
name: resume-training
description: Resume a suspended training job or restart from a checkpoint on RHOAI. Use when the user wants to continue a paused or failed training job.
license: Apache-2.0
compatibility: Requires oc or kubectl and jq. Needs Kubeflow Training Operator installed.
metadata:
  author: Red Hat
  version: "1.0"
  category: training
---

# Resume Training

Resume a suspended training job or restart a failed training job from a
checkpoint on Red Hat OpenShift AI (RHOAI). This skill handles both simple
resume (unsuspending a paused job) and diagnosing failed jobs to determine
the best recovery approach.

## Prerequisites

- `oc` or `kubectl` CLI installed and authenticated to the cluster
- `jq` installed for JSON processing
- Kubeflow Training Operator installed on the cluster

## Workflow

### Step 1: Check current job state

First, determine the current state of the training job. Use the monitor-training
skill's status script to check:

```bash
bash ../monitor-training/scripts/training-status.sh NAMESPACE JOB_NAME
```

Replace `NAMESPACE` with the project namespace and `JOB_NAME` with the TrainJob
name. Review the status to determine whether the job is:

- **Suspended**: The job has `spec.suspend: true` and can be resumed directly.
- **Failed**: The job encountered an error and needs diagnosis before recovery.
- **Running**: The job is already active; no action needed.
- **Completed**: The job finished successfully; no action needed.

### Step 2: If suspended, resume the job

If the job is suspended, resume it by patching `spec.suspend` to `false`:

```bash
bash scripts/resume-job.sh NAMESPACE JOB_NAME
```

This patches the TrainJob to set `spec.suspend: false`, which causes the
Training Operator to recreate the training pods and continue training.

### Step 3: If failed, diagnose and create a new job from checkpoint

If the job has failed, first diagnose the failure using the troubleshoot-training
skill. Common failure causes include OOM errors, image pull issues, and
scheduling failures.

If checkpoints are available, a new TrainJob can be created that resumes from
the last checkpoint. The checkpoint location depends on the training
configuration -- check the job's volume mounts and output directory settings.

To suspend a running job (for example, to free GPU resources temporarily):

```bash
bash scripts/suspend-job.sh NAMESPACE JOB_NAME
```

### Step 4: Verify resumption

After resuming, verify the job is running again:

```bash
bash ../monitor-training/scripts/training-status.sh NAMESPACE JOB_NAME
```

Check that the status shows the job as active and that training metrics are
being updated. Use the monitor-training skill to track ongoing progress.

## Notes

- **Suspend vs Delete**: Suspending a job stops its pods but preserves the
  TrainJob resource and its configuration. This is useful for temporarily
  freeing GPU resources. Deleting a job removes it entirely.
- **Checkpoints**: Whether a job can resume from a checkpoint depends on the
  training script and configuration. Jobs that write checkpoints to a
  PersistentVolumeClaim can typically be restarted from the last checkpoint.
- **Resource availability**: Resuming a job requires the same GPU and memory
  resources to be available. If the cluster is fully utilized, the job may
  remain pending until resources are freed.
