#!/bin/bash
#SBATCH --job-name=dtr-mrl-isolation-stress
#SBATCH --account=pi_fl426
#SBATCH --partition=devel
#SBATCH --qos=normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:10:00
#SBATCH --output=logs/stress-%j.out
#SBATCH --error=logs/stress-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
timeout --signal=TERM --kill-after=5s 560s /usr/bin/python3 experiments/containment/stress_v1.py
