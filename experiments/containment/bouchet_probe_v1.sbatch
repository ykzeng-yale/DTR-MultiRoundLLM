#!/bin/bash
#SBATCH --job-name=dtr-mrl-isolation-probe
#SBATCH --account=pi_fl426
#SBATCH --partition=day
#SBATCH --qos=normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:05:00
#SBATCH --output=logs/probe-%j.out
#SBATCH --error=logs/probe-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
timeout --signal=TERM --kill-after=5s 60s /usr/bin/python3 -I experiments/containment/bouchet_probe_v1.py
