"""Static examples audit: literal parsing and independent arithmetic, no code execution.

Never executes candidate, reference, control or assertion text.  Private
assertions are only ``ast.parse``d and their call arguments ``ast.literal_eval``d;
public cases are ``ast.literal_eval``d and checked against an independent
arithmetic oracle written here.  No subprocess, sandbox, model or network.

Usage (MRL-10, parameterized; all three arguments required, --out must not exist):

    uv run python scripts/check_public_diagnostic_examples_20260921.py \
        --examples docs/public_diagnostic_examples_v1.json \
        --private-specs work/<build>/private_specs.jsonl \
        --out work/<run>/public_diagnostic_examples_audit.json \
        --expected-case-count 21

Historical mode: with NO arguments the script reproduces the original
2026-09-21 behaviour exactly (hardcoded v1c private specs, writes
results/public_diagnostic_examples_review_20260921.json).  It is kept only for
reproducibility of that historical result and must not be used to audit the
rebound v2 specs.
"""
import argparse
import ast
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
LEGACY_EXAMPLES = Path('docs/public_diagnostic_examples_v1.json')
LEGACY_PRIVATE_SPECS = Path('experiments/landmark/dev_release_v1c/private_specs.jsonl')
LEGACY_OUT = Path('results/public_diagnostic_examples_review_20260921.json')
LEGACY_CASE_COUNT = 21
EVIDENCE_TYPE = 'static literal/input and arithmetic audit; no stored code execution'
LIMITS = 'No semantic holdout, grader validity, informative diagnostic or empirical efficacy certification.'


class AuditError(Exception):
    pass


def _oracle(root, args):
    """Independent arithmetic oracle; never evaluates stored program text."""
    if root == 'mbpp/52': return sum(args[0] for _ in range(args[1]))
    if root == 'mbpp/357': return sorted(y for tup in args[0] for y in tup)[-1]
    if root == 'mbpp/373': return args[0]*args[1]*args[2]
    if root == 'mbpp/378': return [args[0][(i-1) % len(args[0])] for i in range(len(args[0]))]
    if root == 'mbpp/402':
        n, r, p = args
        return (math.factorial(n)//(math.factorial(r)*math.factorial(n-r))) % p
    if root == 'mbpp/489': return sum(x == sorted(args[1])[-1] for x in args[1])
    if root == 'mbpp/509': return (args[0]+1)//2
    raise AuditError(f'no independent oracle for root {root!r}')


def _private_inputs(spec, entry_point):
    inputs = []
    for assertion in spec['private_assertions']:
        tree = ast.parse(assertion)  # parse only; never compiled or executed
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id == entry_point]
        if len(calls) != 1 or calls[0].keywords:
            raise AuditError(f'{entry_point}: expected exactly one positional call in {assertion!r}')
        inputs.append([ast.literal_eval(n) for n in calls[0].args])
    return inputs


def audit(public, private, expected_case_count=None):
    checks = []
    for task in public['cases']:
        root = task['root_id']
        if root not in private:
            raise AuditError(f'public root {root!r} missing from private specs')
        spec = private[root]
        if spec.get('entry_point', task['entry_point']) != task['entry_point']:
            raise AuditError(f'{root}: entry_point mismatch')
        inputs = _private_inputs(spec, task['entry_point'])
        for case in task['cases']:
            args = ast.literal_eval(case['args_literal'])
            expected = ast.literal_eval(case['expected_literal'])
            if _oracle(root, args) != expected:
                raise AuditError(f'{root}/{case["case_id"]}: oracle disagrees with expected_literal')
            checks.append({'root_id': root, 'case_id': case['case_id'], 'oracle_agrees': True,
                           'literal_private_input_overlap': _norm(args) in [_norm(i) for i in inputs]})
    if expected_case_count is not None and len(checks) != expected_case_count:
        raise AuditError(f'case count {len(checks)} != expected {expected_case_count}')
    return checks


def _norm(v):
    """Type-sensitive canonical key: tuples compare as lists (recursively), bool stays distinct from int."""
    if isinstance(v, (list, tuple)):
        return ['seq', [_norm(x) for x in v]]
    if isinstance(v, dict):
        return ['map', sorted((repr(_norm(k)), _norm(x)) for k, x in v.items())]
    return [type(v).__name__, v]


def _strict(data):
    def pairs(items):
        keys = [k for k, _ in items]
        if len(keys) != len(set(keys)):
            raise AuditError('duplicate JSON key')
        return dict(items)
    return json.loads(data, object_pairs_hook=pairs)


def _load(ex_bytes, sp_bytes):
    """Parse exactly the bytes that were hashed (never re-read from disk); duplicate keys are refused."""
    public = _strict(ex_bytes)
    private = {}
    for line in sp_bytes.decode('utf-8').splitlines():
        if not line.strip():
            continue
        row = _strict(line)
        if row['root_id'] in private:
            raise AuditError(f'duplicate root_id {row["root_id"]!r} in private specs')
        private[row['root_id']] = row
    return public, private


def build_result(examples_path, specs_path, expected_case_count=None, legacy=False):
    start = time.perf_counter()
    examples_path, specs_path = Path(examples_path), Path(specs_path)
    # Hash exactly the bytes that are audited.
    ex_bytes, sp_bytes = examples_path.read_bytes(), specs_path.read_bytes()
    public, private = _load(ex_bytes, sp_bytes)
    checks = audit(public, private, expected_case_count)
    result = {'evidence_type': EVIDENCE_TYPE, 'cases': checks, 'case_count': len(checks),
              'overlap_gate': 'HOLD' if any(x['literal_private_input_overlap'] for x in checks) else 'PASS',
              'input_sha256': {str(examples_path): hashlib.sha256(ex_bytes).hexdigest(),
                               str(specs_path): hashlib.sha256(sp_bytes).hexdigest()},
              'seconds': time.perf_counter()-start, 'model_calls': 0,
              'candidate_reference_executions': 0, 'paid_usd': 0, 'limits': LIMITS}
    if not legacy:
        result.update({'mode': 'parameterized',
                       'examples_path': str(examples_path), 'examples_sha256': hashlib.sha256(ex_bytes).hexdigest(),
                       'private_specs_path': str(specs_path), 'private_specs_sha256': hashlib.sha256(sp_bytes).hexdigest(),
                       'expected_case_count': expected_case_count, 'network_requests': 0, 'subprocesses': 0})
    return result


def write_new(out, result):
    out = Path(out)
    data = (json.dumps(result, indent=2)+'\n').encode()
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)  # refuses an existing path
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)


def _summary(result):
    print(json.dumps({k: v for k, v in result.items() if k not in ['cases', 'input_sha256']}, indent=2))


def legacy_main():
    """Historical 2026-09-21 behaviour, kept byte-for-byte in semantics for reproducibility."""
    os.chdir(ROOT)  # the historical relative paths resolve against the repository, never the caller's directory
    result = build_result(LEGACY_EXAMPLES, LEGACY_PRIVATE_SPECS, LEGACY_CASE_COUNT, legacy=True)
    fd = os.open(LEGACY_OUT, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)  # refuse overwrite (MRL-10 review)
    with os.fdopen(fd, 'w') as fh:
        fh.write(json.dumps(result, indent=2)+'\n')
    _summary(result)
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if not argv:
        return legacy_main()
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--examples', required=True)
    p.add_argument('--private-specs', required=True, help='private specs JSONL (e.g. rebound v2 build)')
    p.add_argument('--out', required=True, help='output JSON path; must not already exist')
    p.add_argument('--expected-case-count', type=int, required=True)
    a = p.parse_args(argv)
    out = Path(a.out)
    if out.exists():
        print(f'refusing to overwrite existing {out}', file=sys.stderr)
        return 2
    try:
        result = build_result(a.examples, a.private_specs, a.expected_case_count)
    except AuditError as e:
        print(f'audit error: {e}', file=sys.stderr)
        return 3
    write_new(out, result)
    _summary(result)
    return 0 if result['overlap_gate'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
