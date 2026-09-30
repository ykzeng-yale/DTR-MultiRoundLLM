#!/bin/bash
#SBATCH --job-name=dtr-scientific-sprint-v1
#SBATCH --account=pi_fl426
#SBATCH --partition=gpu_devel
#SBATCH --qos=normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gpus=2
#SBATCH --cpus-per-task=12
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=logs/sprint-%j.out
#SBATCH --error=logs/sprint-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
module purge
module load GCC/13.3.0 CUDA/12.8.0
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=4
umask 077
timeout --signal=TERM --kill-after=15s 14340s /usr/bin/python3 experiments/sprint/receiver_v1.py --plan worker-plan.json
