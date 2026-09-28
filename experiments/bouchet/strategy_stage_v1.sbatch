#!/bin/bash
#SBATCH --job-name=dtr-strategy-v1
#SBATCH --account=pi_fl426
#SBATCH --partition=gpu_h100
#SBATCH --qos=normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gpus-per-node=h100:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=logs/strategy-%j.out
#SBATCH --error=logs/strategy-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
module purge
module load GCC/13.3.0 CUDA/12.8.0 Python/3.12.3-GCCcore-13.3.0
nvidia-smi > gpu-before.txt
nvidia-smi --query-gpu=timestamp,name,memory.used,utilization.gpu,power.draw --format=csv -l 1 > gpu-samples.csv &
monitor=$!
trap 'kill "$monitor" 2>/dev/null || true' EXIT
 timeout --signal=TERM --kill-after=15s 1750s python experiments/bouchet/run_strategy_stage_v1.py --plan stage-plan.json
nvidia-smi > gpu-after.txt
