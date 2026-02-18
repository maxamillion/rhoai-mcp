"""Training workflow prompts for RHOAI MCP.

Provides prompts that guide AI agents through model fine-tuning workflows
including training setup, monitoring, and resumption.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from rhoai_mcp.server import RHOAIServer


def register_prompts(mcp: FastMCP, server: RHOAIServer) -> None:  # noqa: ARG001
    """Register training workflow prompts.

    Args:
        mcp: The FastMCP server instance to register prompts with.
        server: The RHOAI server instance (unused but required for interface).
    """

    @mcp.prompt(
        name="train-model",
        description="Guide through fine-tuning a model with LoRA/QLoRA on RHOAI",
    )
    def train_model(
        model_id: str,
        dataset_id: str,
        namespace: str,
        method: str = "lora",
    ) -> str:
        """Generate guidance for fine-tuning a model.

        Args:
            model_id: HuggingFace model identifier (e.g., "meta-llama/Llama-2-7b-hf").
            dataset_id: HuggingFace dataset identifier (e.g., "tatsu-lab/alpaca").
            namespace: Target namespace/project for training.
            method: Fine-tuning method - lora, qlora, dora, or full.

        Returns:
            Workflow guidance as a string prompt.
        """
        return f"""I need to fine-tune a model on Red Hat OpenShift AI.

**Training Configuration:**
- Model: {model_id}
- Dataset: {dataset_id}
- Namespace: {namespace}
- Method: {method}

**Please help me complete these steps:**

1. **Check Prerequisites**
   - Use `training(action="prerequisites")` to verify the namespace, model access, and GPU availability
   - Use `training(action="estimate")` to determine GPU memory requirements for {model_id} with {method}

2. **Prepare Infrastructure**
   - Use `list_training_runtimes` to find an available training runtime
   - If no runtime exists, use `setup_training_runtime` to create one
   - Use `setup_training_storage` to create a PVC for checkpoints if needed

3. **Configure Credentials (if needed)**
   - If {model_id} is a gated model, use `setup_hf_credentials` with my HuggingFace token

4. **Validate Configuration**
   - Use `training(action="validate")` to verify all resources are ready

5. **Start Training**
   - Use `training(action="create")` with the configuration above
   - First call without confirmed=True to preview the job spec
   - Then call with confirmed=True to create the job

6. **Monitor Progress**
   - Use `training(action="progress")` to check training metrics
   - Use `training(action="logs")` if issues arise

Please start by checking the prerequisites and estimating resource requirements."""

    @mcp.prompt(
        name="monitor-training",
        description="Monitor an active training job and diagnose issues",
    )
    def monitor_training(namespace: str, job_name: str) -> str:
        """Generate guidance for monitoring a training job.

        Args:
            namespace: Namespace containing the training job.
            job_name: Name of the training job to monitor.

        Returns:
            Workflow guidance as a string prompt.
        """
        return f"""I need to monitor a training job on Red Hat OpenShift AI.

**Job Details:**
- Namespace: {namespace}
- Job Name: {job_name}

**Please help me with:**

1. **Check Job Status**
   - Use `training(action="get")` to get the current job status and configuration
   - Use `training(action="progress")` to see real-time training metrics (epoch, loss, learning rate)

2. **Review Logs**
   - Use `training(action="logs")` to check the trainer container logs
   - Look for warnings or errors in the output

3. **Check Events**
   - Use `training(action="events")` to see Kubernetes events for the job
   - This helps identify scheduling issues, OOM conditions, or resource problems

4. **Check Checkpoints**
   - Use `training(action="checkpoints")` to see saved checkpoint information
   - Verify checkpoints are being saved as expected

5. **If Issues Found**
   - If the job is stuck or failing, use `analyze_training_failure` for diagnosis
   - Consider using `training(action="suspend")` if you need to pause and investigate

Please start by getting the current job status and training progress."""

    @mcp.prompt(
        name="resume-training",
        description="Resume a suspended or failed training job from checkpoint",
    )
    def resume_training(namespace: str, job_name: str) -> str:
        """Generate guidance for resuming a training job.

        Args:
            namespace: Namespace containing the training job.
            job_name: Name of the training job to resume.

        Returns:
            Workflow guidance as a string prompt.
        """
        return f"""I need to resume a training job on Red Hat OpenShift AI.

**Job Details:**
- Namespace: {namespace}
- Job Name: {job_name}

**Please help me with:**

1. **Check Current State**
   - Use `training(action="get")` to see the current job status
   - Use `training(action="checkpoints")` to find the latest checkpoint

2. **If Job is Suspended**
   - Use `training(action="resume")` to restart the job
   - The job will continue from the last checkpoint automatically

3. **If Job Failed**
   - Use `analyze_training_failure` to understand why it failed
   - Use `training(action="events")` to check for infrastructure issues
   - Fix any issues (OOM, storage, etc.)
   - You may need to create a new job with `training(action="create")` using the checkpoint_dir parameter

4. **Verify Resumption**
   - Use `training(action="progress")` to confirm training has resumed
   - Check that the epoch/step numbers continue from where they left off
   - Use `training(action="logs")` to verify no errors on startup

Please start by checking the current job state and checkpoint availability."""
