#!/bin/bash
#SBATCH --job-name=dtr-cuda-build-v1
#SBATCH --account=pi_fl426
#SBATCH --partition=day
#SBATCH --qos=normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=00:30:00
#SBATCH --output=logs/build-%j.out
#SBATCH --error=logs/build-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
exec timeout --signal=TERM --kill-after=15s 1700s bash experiments/bouchet/build_h100_v1.sh
