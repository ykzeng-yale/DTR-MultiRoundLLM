"""Frozen batch grading CLI; submits no jobs and contacts no receiver."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from experiments.sprint_grading.batch_v1 import run_batch


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--plan',required=True)
    parser.add_argument('--out',required=True);parser.add_argument('--attestation')
    args=parser.parse_args()
    summary=run_batch(args.plan,args.out,attestation_path=args.attestation)
    print(json.dumps({k:summary[k] for k in ('status','assigned_units','accounted_units',
        'case_starts','cached_units','elapsed_seconds','stop_reason')},sort_keys=True))
