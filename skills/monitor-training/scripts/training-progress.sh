#!/usr/bin/env bash
# Get training progress metrics from the trainer status annotation.
#
# Extracts the trainer.opendatahub.io/trainerStatus annotation which contains
# live training metrics including epoch, step, loss, and throughput.
#
# Usage: ./training-progress.sh NAMESPACE JOB_NAME
# Output: JSON with training progress metrics.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../_shared/lib.sh"

NAMESPACE="${1:-}"
JOB_NAME="${2:-}"

if [[ -z "$NAMESPACE" || -z "$JOB_NAME" ]]; then
    die "Usage: $0 NAMESPACE JOB_NAME"
fi

CLI=$(detect_cli)

# Get the TrainJob resource
TRAINJOB_JSON=$("$CLI" get "${TRAINJOB_PLURAL}.${TRAINJOB_GROUP}" "$JOB_NAME" \
    -n "$NAMESPACE" -o json 2>/dev/null) || die "TrainJob '$JOB_NAME' not found in namespace '$NAMESPACE'."

# Extract the trainer status annotation
TRAINER_STATUS=$(echo "$TRAINJOB_JSON" | jq -r '.metadata.annotations["trainer.opendatahub.io/trainerStatus"] // empty' 2>/dev/null)

if [[ -z "$TRAINER_STATUS" ]]; then
    # No progress annotation found; return basic status
    echo "$TRAINJOB_JSON" | jq '{
        job_name: .metadata.name,
        namespace: .metadata.namespace,
        progress_available: false,
        message: "No trainer status annotation found. The job may not have started training yet or may not report progress via annotations.",
        status: (
            if .status.conditions then
                (.status.conditions | sort_by(.lastTransitionTime) | last | .type + "=" + .status)
            else
                "Unknown"
            end
        )
    }'
    exit 0
fi

# Parse and format the trainer status annotation
echo "$TRAINER_STATUS" | jq --arg name "$JOB_NAME" --arg ns "$NAMESPACE" '{
    job_name: $name,
    namespace: $ns,
    progress_available: true,
    trainingState: .trainingState,
    currentEpoch: .currentEpoch,
    totalEpochs: .totalEpochs,
    currentStep: .currentStep,
    totalSteps: .totalSteps,
    loss: .loss,
    learningRate: .learningRate,
    throughput: .throughput,
    gradientNorm: .gradientNorm,
    estimatedTimeRemaining: .estimatedTimeRemaining,
    epoch_progress: (
        if .totalEpochs and .totalEpochs > 0 and .currentEpoch then
            ((.currentEpoch / .totalEpochs * 100 * 10 | floor) / 10 | tostring) + "%"
        else
            null
        end
    ),
    step_progress: (
        if .totalSteps and .totalSteps > 0 and .currentStep then
            ((.currentStep / .totalSteps * 100 * 10 | floor) / 10 | tostring) + "%"
        else
            null
        end
    )
}'
