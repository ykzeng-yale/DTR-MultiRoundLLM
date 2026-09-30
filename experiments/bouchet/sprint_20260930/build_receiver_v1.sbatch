#!/bin/bash
#SBATCH --job-name=dtr-sprint-build-v1
#SBATCH --account=pi_fl426
#SBATCH --partition=devel
#SBATCH --qos=normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=logs/build-%j.out
#SBATCH --error=logs/build-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
timeout --signal=TERM --kill-after=15s 3500s bash experiments/bouchet/sprint_20260930/build_receiver_v1.sh
