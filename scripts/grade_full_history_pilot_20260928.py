"""Terminal descriptive grading; no further receiver requests or policy fitting."""
import argparse
import ast
from collections import Counter
import hashlib
import json
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiments.bouchet.full_history_pilot_v1 import source
from experiments.prompt_choice.literal_observation_v1 import evaluate
from scripts.audit_literal_panel_20260928 import aggregate


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--contract', type=Path, required=True)
    p.add_argument('--state', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    c = json.loads(a.contract.read_bytes())
    for f, h in c['files'].items():
        if hashlib.sha256(Path(f).read_bytes()).hexdigest() != h:
            raise ValueError('contract mismatch: '+f)
    state = json.loads(a.state.read_bytes())
    if state['requests'] or any(r['disposition']=='active' for r in state['rows']):
        raise ValueError('nonterminal state')
    ledger = json.loads(Path(c['assignments_path']).read_bytes())
    if len(state['rows']) != 18 or any(any(r[k]!=l[k] for k in l) for r,l in zip(state['rows'],ledger)):
        raise ValueError('assigned trajectory mismatch')
    a.out.mkdir(exist_ok=False)
    start = time.monotonic()
    result = {'classification': 'reused-nine-root sequential operational pilot; no efficacy or policy-selection inference',
              'state_sha256': hashlib.sha256(a.state.read_bytes()).hexdigest(),
              'assigned': 18, 'rows': [], 'case_starts': 0, 'error': None}
    try:
        for row in state['rows']:
            r = {k: row[k] for k in ('trajectory','root','replicate','disposition')}
            r['batteries'] = {k:'INCOMPLETE' for k in ('original_private','supplement_v1')}
            r['actions'] = [d['action'] for d in row['decisions']]
            r['public_statuses'] = [d['public_status'] for d in row['decisions']]
            result['rows'].append(r)
            if row['disposition'] == 'generation_unavailable':
                continue
            try:
                code = source(row['final_raw'])
            except (ValueError, SyntaxError, TypeError):
                continue
            name = row['root'].replace('/','_')+'.json'
            pub = json.loads((Path(c['package'])/'public'/name).read_bytes())
            pri = json.loads((Path(c['package'])/'private'/name).read_bytes())
            for battery, data in pri['batteries'].items():
                statuses = []
                for j, case in enumerate(data['cases']):
                    if result['case_starts'] >= 500 or time.monotonic()-start > 1100:
                        raise RuntimeError('terminal grading cap')
                    value = evaluate(code,pub['entry_point'],case['args_literal'],ast.literal_eval(case['expected_literal']))
                    (a.out/f"{row['trajectory']}-{battery}-{j}.json").write_text(json.dumps(value)+'\n')
                    result['case_starts'] += 1
                    if sum(f.stat().st_size for f in a.out.glob('*.json')) > 256<<20:
                        raise RuntimeError('terminal output cap')
                    statuses.append(value['status'])
                r['batteries'][battery] = aggregate(statuses)
    except BaseException as e:
        result['error'] = repr(e)
        raise
    finally:
        statuses = [r['batteries']['supplement_v1'] for r in result['rows']]
        statuses += ['INCOMPLETE']*(18-len(statuses))
        result.update(elapsed_seconds=time.monotonic()-start,
                      supplemental_counts=dict(Counter(statuses)),
                      descriptive_bounds=[statuses.count('PASS')/18,
                                          (statuses.count('PASS')+statuses.count('INCOMPLETE'))/18])
        (a.out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__ == '__main__':
    main()
