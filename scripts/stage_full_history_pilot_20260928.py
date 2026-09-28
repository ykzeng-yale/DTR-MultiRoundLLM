"""Prepare deterministic stages locally; private files are never opened here."""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiments.bouchet.full_history_pilot_v1 import initialize, advance
from experiments.prompt_choice.literal_observation_v1 import evaluate


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--contract', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--state', type=Path)
    p.add_argument('--receipt', type=Path)
    p.add_argument('--stage-plan', type=Path)
    a = p.parse_args()
    contract = json.loads(a.contract.read_bytes())
    for f, h in contract['files'].items():
        if f.startswith(contract['package']+'/private/'):
            continue  # Private bytes are verified only by terminal grading.
        if hashlib.sha256(Path(f).read_bytes()).hexdigest() != h:
            raise ValueError('contract input mismatch: '+f)
    public = [json.loads(Path(f).read_bytes()) for f in contract['public_paths']]
    if bool(a.state) != bool(a.receipt) or bool(a.receipt) != bool(a.stage_plan):
        raise ValueError('state, receipt and stage plan required together')
    a.out.mkdir(exist_ok=False)
    start = time.monotonic()
    count = 0
    def observed(*args):
        nonlocal count
        if count >= 18 or time.monotonic()-start > 110:
            raise RuntimeError('public observation cap')
        r = evaluate(*args)
        (a.out/f'public-{count}.json').write_text(json.dumps(r)+'\n')
        count += 1
        return r
    if a.state:
        state = json.loads(a.state.read_bytes())
        receipt = json.loads(a.receipt.read_bytes())
        stage_plan = json.loads(a.stage_plan.read_bytes())
        if receipt['config_sha256'] != hashlib.sha256(a.stage_plan.read_bytes()).hexdigest():
            raise ValueError('stage receipt plan mismatch')
        if stage_plan['state_sha256'] != hashlib.sha256(a.state.read_bytes()).hexdigest():
            raise ValueError('stage state mismatch')
        if receipt['error'] or not receipt.get('state_unchanged'):
            raise ValueError('failed receiver stage: preserve and reconcile, no continuation')
        state = advance(state, receipt, public, observed)
    else:
        ledger = json.loads(Path(contract['assignments_path']).read_bytes())
        state = initialize(public, ledger)
    (a.out/'state.json').write_text(json.dumps(state, indent=2)+'\n')
    (a.out/'requests.json').write_text(json.dumps(state['requests'], indent=2)+'\n')
    (a.out/'preparation.json').write_text(json.dumps({
        'phase': state['phase'], 'public_case_starts': count,
        'elapsed_seconds': time.monotonic()-start,
        'contract_sha256': hashlib.sha256(a.contract.read_bytes()).hexdigest(),
        'prior_receipt_sha256': hashlib.sha256(a.receipt.read_bytes()).hexdigest() if a.receipt else None,
        'requests': len(state['requests']), 'private_files_opened': False}, indent=2)+'\n')


if __name__ == '__main__':
    main()
