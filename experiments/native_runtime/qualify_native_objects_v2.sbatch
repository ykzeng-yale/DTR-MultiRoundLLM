#!/bin/bash
#SBATCH --job-name=dtr-mrl-native-objects-v2
#SBATCH --account=pi_fl426
#SBATCH --partition=devel
#SBATCH --qos=normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:10:00
#SBATCH --output=logs/native-%j.out
#SBATCH --error=logs/native-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
module purge
export PYTHONPATH=/apps/software/2024a/software/Python/3.12.3-GCCcore-13.3.0/lib/python3.12/site-packages
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
ulimit -f 2097152
timeout --signal=TERM --kill-after=5s 420s /usr/bin/python3 experiments/native_runtime/qualify_native_objects_v2.py
