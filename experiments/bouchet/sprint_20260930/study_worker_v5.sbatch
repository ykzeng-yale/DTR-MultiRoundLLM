#!/bin/bash
#SBATCH --job-name=dtr-scientific-sprint-h100-v3
#SBATCH --account=pi_gt353
#SBATCH --partition=gpu_h100
#SBATCH --qos=normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gpus=h100:2
#SBATCH --cpus-per-task=12
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=logs/sprint-h100-%j.out
#SBATCH --error=logs/sprint-h100-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
module purge
module load GCC/13.3.0 CUDA/12.8.0
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=4
umask 077
timeout --signal=TERM --kill-after=15s 14340s /usr/bin/python3 -m experiments.sprint.worker_v3 --plan worker-plan.json
