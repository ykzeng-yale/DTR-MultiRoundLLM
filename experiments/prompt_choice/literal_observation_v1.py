"""Versioned literal-input, JSON-output comparator for the audited nine-root panel.

Input literals preserve integer dictionary keys that JSON would stringify. This
new input contract does not expand supported output types or certify native objects.

The candidate receives its invocation inputs, never expected values or comparison
code. Candidate stdout is an untrusted observation, not an authoritative verdict.
Only bounded JSON values are supported; no pickle, eval, imports or candidate code
run in this supervising process. This does not certify arbitrary object behavior.
"""
import ast
import hashlib
import json
import keyword
import math
from experiments.prompt_choice.native_execution_v1 import run

VERSION = 'external-literal-input-json-observation-v1'
MAX_BYTES = 65536


def validate_value(value, depth=0, budget=None):
    if budget is None:
        budget = [16384]
    budget[0] -= 1
    if depth > 32 or budget[0] < 0:
        raise ValueError('observation complexity')
    t = type(value)
    if value is None or t in (bool, str):
        return
    if t is int:
        if value.bit_length() > 1024:
            raise ValueError('integer size')
        return
    if t is float and math.isfinite(value):
        return
    if t is list:
        for x in value:
            validate_value(x, depth+1, budget)
        return
    if t is dict and all(type(k) is str for k in value):
        for x in value.values():
            validate_value(x, depth+1, budget)
        return
    raise ValueError('unsupported observation')


def encoded(value):
    validate_value(value)
    raw = json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(',', ':'))
    if len(raw.encode()) > MAX_BYTES:
        raise ValueError('observation size')
    return raw


def no_duplicates(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError('duplicate key')
        out[k] = v
    return out


def parse_observation(text):
    if type(text) is not str or len(text.encode()) >= MAX_BYTES:
        raise ValueError('observation size')
    def reject_constant(_):
        raise ValueError('nonfinite JSON')
    try:
        obj = json.loads(text, object_pairs_hook=no_duplicates, parse_constant=reject_constant)
    except (ValueError, RecursionError) as exc:
        raise ValueError('malformed observation') from exc
    if type(obj) is not dict or set(obj) != {'observation_version', 'value'} or obj['observation_version'] != VERSION:
        raise ValueError('observation schema')
    validate_value(obj['value'])
    return obj['value']


def equal(left, right):
    # Exact type equality: bool is not int; 1.0 is not silently the integer1.
    if type(left) is not type(right):
        return False
    if type(left) is list:
        return len(left) == len(right) and all(equal(a,b) for a,b in zip(left,right))
    if type(left) is dict:
        return left.keys() == right.keys() and all(equal(left[k],right[k]) for k in left)
    return left == right


def program(code, entry_point, args):
    if type(code) is not str or len(code.encode()) > 1 << 20:
        raise ValueError('source size')
    if type(entry_point) is not str or not entry_point.isidentifier() or keyword.iskeyword(entry_point):
        raise ValueError('entry point')
    if type(args) is not str or len(args.encode()) > MAX_BYTES:
        raise ValueError('literal input size/type')
    try:
        parsed = ast.literal_eval(args)
    except (ValueError, SyntaxError, RecursionError) as exc:
        raise ValueError('literal inputs required') from exc
    if type(parsed) is not list:
        raise ValueError('positional inputs required')
    # ast.literal_eval never executes calls; preserve integer mapping keys/tuples.
    return (code + '\nimport json as _observation_json, ast as _observation_ast\n' +
            f'_observation_args = _observation_ast.literal_eval({args!r})\n' +
            f'_observation_value = {entry_point}(*_observation_args)\n' +
            "print(_observation_json.dumps({'observation_version':" + repr(VERSION) +
            ",'value':_observation_value},allow_nan=False,separators=(',',':')))\n")


def evaluate(code, entry_point, args, expected, *, runner=run):
    expected_json = encoded(expected)  # Validate before any start.
    source = program(code, entry_point, args)
    binding = {'artifact_sha256': hashlib.sha256(code.encode()).hexdigest(),
               'invocation_sha256': hashlib.sha256(encoded([entry_point,args]).encode()).hexdigest(),
               'expected_sha256': hashlib.sha256(expected_json.encode()).hexdigest()}
    result = runner(source, timeout_s=2, cpu_seconds=1, output_cap=MAX_BYTES, mem_bytes=256 << 20)
    disposition = result['execution']['disposition']
    if disposition != 'completed_ungraded':
        return dict(version=VERSION, **binding, status='INCOMPLETE', outcome=None,
                    reason=disposition, process=result)
    try:
        observation = parse_observation(result['raw_process']['stdout'])
    except ValueError:
        return dict(version=VERSION, **binding, status='INCOMPLETE', outcome=None,
                    reason='invalid_observation', process=result)
    passed = equal(observation, expected)
    return dict(version=VERSION, **binding, status='PASS' if passed else 'FAIL',
                outcome=int(passed), reason='external_comparison', process=result)
