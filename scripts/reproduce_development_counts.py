"""Recount E11/E13a and endpoint projections from Git blobs, without executing payloads."""
import argparse
import collections
import hashlib
import json
import subprocess
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def grade_index(rows, expected):
    indexed = {}
    for row in rows:
        key = (row['root_id'], row['arm'], row['replicate'])
        if key in indexed:
            raise ValueError('duplicate grade key')
        value = row['outcome']
        if value is not None and (type(value) is not int or value not in (0, 1)):
            raise ValueError('nonbinary grade')
        indexed[key] = value
    if set(indexed) != expected:
        raise ValueError('assignment/grade mismatch')
    return indexed


def reproduce(revision):
    commit = subprocess.check_output(
        ['git', 'rev-parse', '--verify', revision + '^{commit}'], cwd=ROOT, text=True
    ).strip()
    hashes = {}

    def read(name, lines=False):
        raw = subprocess.check_output(['git', 'show', commit + ':' + name], cwd=ROOT)
        hashes[name] = hashlib.sha256(raw).hexdigest()
        return [json.loads(line) for line in raw.splitlines()] if lines else json.loads(raw)

    roots = [f'mbpp/{i}' for i in (52, 357, 373, 378, 402, 489, 509)]
    arms = ('STOP', 'N0', 'S0', 'N1', 'S1', 'R1')
    expected = {(r, a, j) for r in roots for a in arms
                for j in range(1 if a == 'STOP' else 2)}
    e11 = grade_index(read('results/e11_dev_v2_20260922T010959Z/D/grades.jsonl', True), expected)
    e11_counts = {a: dict(collections.Counter(str(v) for (r, arm, j), v in e11.items()
                                            if arm == a)) for a in arms}
    e11_delta = {r: str(sum(Fraction(e11[r, 'S1', j] - e11[r, 'N1', j], 2)
                           for j in range(2))) for r in roots}
    context_delta = sum(Fraction(e11[r, 'R1', j] - e11[r, 'N1', j], 14)
                        for r in roots for j in range(2))

    plan = read('results/e13a_request_plan_20260922.json')
    keys = [(r['root_id'], x['arm'], x['replicate']) for r in plan['roots']
            for x in r['requests']]
    if len(keys) != len(set(keys)):
        raise ValueError('duplicate planned E13a key')
    e13 = grade_index(read('results/e13a_two_arm_20260923T061500Z/grade/grades.jsonl', True), set(keys))
    if any(v is None for v in e13.values()):
        raise ValueError('E13a missing grade; do not silently drop')
    e13_counts = {a: {'passes': sum(v for (r, arm, j), v in e13.items() if arm == a),
                      'assigned': sum(arm == a for r, arm, j in e13)}
                  for a in ('R1', 'FRESH')}
    root_deltas = []
    for root in sorted({r for r, a, j in e13}):
        values = {a: [v for (r, arm, j), v in e13.items() if r == root and arm == a]
                  for a in ('R1', 'FRESH')}
        root_deltas.append(Fraction(sum(values['R1']), len(values['R1']))
                           - Fraction(sum(values['FRESH']), len(values['FRESH'])))

    audits = {}
    for name, size in [('results/policy_endpoint_audit_projection_20260926T2303Z.json', 36),
                       ('results/nine_root_endpoint_projection_20260926T2359Z.json', 162)]:
        slots = read(name)['slots']
        if len(slots) != size or len({s['slot_id'] for s in slots}) != size:
            raise ValueError('endpoint slot inventory mismatch')
        if any(type(s['outcome']) is not int or s['outcome'] not in (0, 1) for s in slots):
            raise ValueError('endpoint missing or nonbinary outcome')
        audits[name] = dict(collections.Counter(f"{s['check']}:{s['outcome']}" for s in slots))
    return {'commit': commit, 'input_sha256': hashes,
            'E11': {'arm_counts': e11_counts, 'primary_root_differences': e11_delta,
                    'context_removal_mean': str(context_delta)},
            'E13a': {'arm_counts': e13_counts,
                     'equal_root_mean_difference': str(sum(root_deltas) / len(root_deltas))},
            'endpoint_projection_counts': audits,
            'scope': 'Git-blob arithmetic only; no execution, regrading, simulation, fit, raw-private-log replay, independence or policy-efficacy validation.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', default='HEAD')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    result = reproduce(args.revision)
    result['executed_script_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'output': str(args.output), 'commit': result['commit']}))
