#!/bin/bash
#SBATCH --job-name=dtr-stdio-sprint-qualification
#SBATCH --account=pi_fl426
#SBATCH --partition=devel
#SBATCH --qos=normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:05:00
#SBATCH --output=logs/stdio-qualification-%j.out
#SBATCH --error=logs/stdio-qualification-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
timeout --signal=TERM --kill-after=5s 240s /usr/bin/python3 scripts/qualify_stdio_sprint_v4.py --plan stdio-sprint-plan.json --out stdio-sprint-results
