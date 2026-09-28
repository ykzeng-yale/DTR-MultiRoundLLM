#!/bin/bash
#SBATCH --job-name=dtr-mrl-core-wheels
#SBATCH --account=pi_fl426
#SBATCH --partition=devel
#SBATCH --qos=normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:12:00
#SBATCH --output=logs/wheels-%j.out
#SBATCH --error=logs/wheels-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
module purge
module load Python/3.12.3-GCCcore-13.3.0
timeout --signal=TERM --kill-after=5s 660s python experiments/native_runtime/acquire_wheels_v1.py
