"""Prospective large-battery operational grade, separate from historical v1.

Operational success means every fixed case completes within its pinned limits
and its UTF8 stdout matches the declared source-backed comparator. Syntax,
runtime, resource, encoding and output-limit failures after a verified strict
bootstrap are observed zeros. Namespace/bootstrap/observer unavailability is
unknown, never automatically STOP or zero. This is not all-input correctness.
"""
import itertools
import re

from experiments.measurement_sprint_v3 import execution_v3 as execution
from experiments.measurement_sprint_v3 import runtime_v3 as runtime

VERSION = 'stdio-sprint-finite-operational-grade-v3'
NORMALIZATIONS = ('exact', 'crlf-to-lf', 'ascii-whitespace-tokens-v1',
                  'line-ascii-tokens-v1', 'ascii_whitespace_tokens_v1',
                  'single_line_exact_optional_final_newline_v1')
TEXT = {'PASS': 'Public check status: PASS.', 'FAIL': 'Public check status: FAIL.',
        'INCOMPLETE': 'Public check status: INCOMPLETE.'}


def source_bindings():
    return dict(execution.source_bindings(), observer=runtime.file_hash(__file__))


def utf8(value, cap):
    if type(value) is not str:
        raise ValueError('UTF8 source text required')
    raw = value.encode('utf-8', 'strict')
    if len(raw) > cap:
        raise ValueError('source instrument exceeds prospective resource cap')
    return raw


def _token_equal(a, b):
    sentinel = object()
    aa = (match.group() for match in re.finditer(rb'[^ \t\r\n\f\v]+', a))
    bb = (match.group() for match in re.finditer(rb'[^ \t\r\n\f\v]+', b))
    return all(x == y for x, y in itertools.zip_longest(aa, bb, fillvalue=sentinel))


def _lines(raw):
    """CRLF framing; preserve blank rows, permit one terminal LF.

    Empty bytes represent zero rows. A single LF represents one blank row;
    therefore an omitted blank row cannot collapse to a missing final newline.
    This prospective convention is only allowed by source-backed line contracts.
    """
    value = raw.replace(b'\r\n', b'\n')
    if not value:
        return []
    if value.endswith(b'\n'):
        value = value[:-1]
    return value.split(b'\n')


def caps_from_source_contract(contract):
    """Explicit sealed-source schema translation, without changing its caps."""
    fields = {'address_space_bytes', 'program_bytes', 'stdin_bytes', 'stdout_bytes',
              'stderr_bytes', 'cpu_soft_seconds', 'cpu_hard_seconds', 'wall_seconds'}
    if type(contract) is not dict or set(contract) != fields:
        raise ValueError('exact sealed source resource contract required')
    caps = dict(execution.DEFAULT_CAPS)
    for key in fields - {'address_space_bytes', 'program_bytes'}:
        caps[key] = contract[key]
    caps['memory_bytes'] = contract['address_space_bytes']
    caps['source_bytes'] = contract['program_bytes']
    return execution.validate_caps(caps)


def _single_line(raw):
    value = raw.replace(b'\r\n', b'\n')
    if value.endswith(b'\n'):
        value = value[:-1]
    if b'\n' in value or b'\r' in value:
        raise ValueError('single-line source contract excludes internal LF/bare CR')
    return value


def compare_stdout(actual, expected, normalization):
    if type(actual) is not bytes or type(expected) is not bytes:
        raise ValueError('raw stdout bytes required')
    actual.decode('utf-8', 'strict')
    expected.decode('utf-8', 'strict')
    if normalization not in NORMALIZATIONS:
        raise ValueError('explicit source-backed comparison required')
    if normalization in ('ascii-whitespace-tokens-v1', 'ascii_whitespace_tokens_v1'):
        return _token_equal(actual, expected)
    if normalization == 'single_line_exact_optional_final_newline_v1':
        try:
            return _single_line(actual) == _single_line(expected)
        except ValueError:
            return False
    if normalization == 'line-ascii-tokens-v1':
        a, b = _lines(actual), _lines(expected)
        return len(a) == len(b) and all(_token_equal(x, y) for x, y in zip(a, b))
    if normalization == 'crlf-to-lf':
        actual, expected = actual.replace(b'\r\n', b'\n'), expected.replace(b'\r\n', b'\n')
    return actual == expected


def case_binding(case, scope, caps):
    if (type(case) is not dict or set(case) != {'case_id', 'scope', 'stdin', 'expected_stdout'}
            or scope not in ('public', 'private') or case['scope'] != scope
            or type(case['case_id']) is not str or not case['case_id']):
        raise ValueError('exact separately scoped source case required')
    stdin = utf8(case['stdin'], caps['stdin_bytes'])
    expected = utf8(case['expected_stdout'], caps['stdout_bytes'])
    return {'case_id': case['case_id'], 'scope': scope,
            'case_sha256': runtime.sha256(runtime.canonical(case)),
            'stdin_sha256': runtime.sha256(stdin), 'stdin_bytes': len(stdin),
            'expected_stdout_sha256': runtime.sha256(expected),
            'expected_stdout_bytes': len(expected)}


def freeze_instrument(cases, *, scope, normalization, runtime_manifest_sha256,
                      source_contract_sha256, caps=None):
    caps = dict(execution.DEFAULT_CAPS if caps is None else caps)
    execution.validate_caps(caps)
    if type(cases) is not list or not cases or normalization not in NORMALIZATIONS:
        raise ValueError('complete nonempty source battery and comparator required')
    for value in (runtime_manifest_sha256, source_contract_sha256):
        if type(value) is not str or not re.fullmatch('[0-9a-f]{64}', value):
            raise ValueError('independently pinned runtime/source contract hashes required')
    bindings = [case_binding(case, scope, caps) for case in cases]
    if normalization == 'single_line_exact_optional_final_newline_v1':
        for case in cases:
            _single_line(case['expected_stdout'].encode('utf-8', 'strict'))
    if len({row['case_id'] for row in bindings}) != len(bindings):
        raise ValueError('duplicate case assignment ID')
    return {'version': VERSION, 'scope': scope, 'cases': bindings,
            'normalization': normalization, 'caps': caps,
            'runtime_manifest_sha256': runtime_manifest_sha256,
            'source_contract_sha256': source_contract_sha256,
            'source_sha256s': source_bindings(),
            'endpoint': 'all fixed cases pass within limits; completed operational failures zero; observer unavailable unknown'}


def instrument_sha256(instrument):
    return runtime.sha256(runtime.canonical(instrument))


def _member(case, instrument, expected_instrument_sha256, scope):
    if (type(instrument) is not dict or set(instrument) != {
            'version', 'scope', 'cases', 'normalization', 'caps',
            'runtime_manifest_sha256', 'source_contract_sha256', 'source_sha256s', 'endpoint'}
            or instrument['version'] != VERSION or instrument['scope'] != scope
            or instrument['source_sha256s'] != source_bindings()
            or instrument['normalization'] not in NORMALIZATIONS
            or instrument_sha256(instrument) != expected_instrument_sha256):
        raise ValueError('independently pinned instrument source/scope/comparator drift')
    execution.validate_caps(instrument['caps'])
    binding = case_binding(case, scope, instrument['caps'])
    matches = [row for row in instrument['cases'] if row['case_id'] == case['case_id']]
    if len(matches) != 1 or matches[0] != binding:
        raise ValueError('case absent or changed from complete frozen battery')
    return binding


def evaluate_case(code, case, *, instrument, expected_instrument_sha256,
                  scope, runner):
    """Only source and stdin reach the qualified runner, never expectations."""
    binding = _member(case, instrument, expected_instrument_sha256, scope)
    code_bytes = utf8(code, instrument['caps']['source_bytes'])
    stdin = utf8(case['stdin'], instrument['caps']['stdin_bytes'])
    process = runner(code, stdin, caps=instrument['caps'])
    expected_identity = {
        'version': execution.VERSION,
        'source_sha256': runtime.sha256(code_bytes), 'stdin_sha256': runtime.sha256(stdin),
        'stdin_bytes': len(stdin), 'caps': instrument['caps'],
        'runtime_manifest_sha256': instrument['runtime_manifest_sha256'],
    }
    if any(process.get(key) != value for key, value in expected_identity.items()):
        raise ValueError('execution receipt identity/runtime/resource drift')
    disposition = process.get('disposition')
    receipt = {'version': VERSION, 'artifact_sha256': expected_identity['source_sha256'],
               **binding, 'instrument_sha256': expected_instrument_sha256,
               'normalization': instrument['normalization'],
               'execution': {key: value for key, value in process.items()
                             if key not in ('stdout', 'stderr')},
               'historical_grades_changed': False}
    if disposition == 'observer_unavailable' and process.get('outcome_available') is False:
        return dict(receipt, status='INCOMPLETE', outcome=None,
                    reason=process.get('failure', 'observer_unavailable'))
    if process.get('outcome_available') is not True or process.get('payload_started') is not True:
        raise ValueError('available operational observation requires strict bootstrap')
    if disposition == 'operational_failure':
        return dict(receipt, status='FAIL', outcome=0,
                    reason=process['failure'])
    if disposition != 'completed' or process.get('returncode') != 0 or process.get('cleanup') is not True:
        raise ValueError('invalid completed execution receipt')
    raw = process.get('stdout')
    if (type(raw) is not bytes or len(raw) != process.get('stdout_bytes')
            or runtime.sha256(raw) != process.get('stdout_sha256')
            or len(raw) > instrument['caps']['stdout_bytes']):
        raise ValueError('stdout observation hash/size drift')
    try:
        passed = compare_stdout(raw, utf8(case['expected_stdout'], instrument['caps']['stdout_bytes']),
                                instrument['normalization'])
    except UnicodeDecodeError:
        return dict(receipt, status='FAIL', outcome=0, reason='invalid_stdout_utf8')
    return dict(receipt, status='PASS' if passed else 'FAIL', outcome=int(passed),
                reason='external_frozen_stdout_comparison')


def public_check(code, case, *, instrument, expected_instrument_sha256, runner):
    receipt = evaluate_case(code, case, instrument=instrument,
        expected_instrument_sha256=expected_instrument_sha256, scope='public', runner=runner)
    # No raw stderr/stdout, input, expected value, case identity or private score.
    return {'feedback_text': TEXT[receipt['status']], 'audit': receipt}


def evaluate_battery(code, cases, *, instrument, expected_instrument_sha256,
                     scope, runner):
    """Retain every fixed case. Do not early-stop or delete unavailable cases."""
    if type(cases) is not list or [case_binding(c, scope, instrument['caps']) for c in cases] != instrument['cases']:
        raise ValueError('whole ordered frozen battery required')
    rows = [evaluate_case(code, case, instrument=instrument,
        expected_instrument_sha256=expected_instrument_sha256, scope=scope, runner=runner)
        for case in cases]
    # A known failed conjunct proves battery failure even if another observation
    # is unavailable. Otherwise an unknown conjunct retains [0,1]. All raw
    # missingness remains reported separately; no successful-case selection.
    if any(row['outcome'] == 0 for row in rows):
        outcome, bounds, status = 0, [0, 0], 'FAIL'
    elif any(row['outcome'] is None for row in rows):
        outcome, bounds, status = None, [0, 1], 'INCOMPLETE'
    else:
        outcome, bounds, status = 1, [1, 1], 'PASS'
    return {'version': VERSION, 'instrument_sha256': expected_instrument_sha256,
            'artifact_sha256': runtime.sha256(code.encode('utf-8', 'strict')),
            'assigned': len(cases), 'accounted': len(rows), 'rows': rows,
            'status': status, 'outcome': outcome, 'bounds': bounds,
            'unavailable_cases': sum(row['outcome'] is None for row in rows)}


def fallback_artifact(event, *, last_valid_artifact, returned_artifact=None,
                      policy='retain-last-valid-on-receiver-failure-v1'):
    """Prospective receiver failure handling, separate from private grading.

    'Valid' means an existing hash-bound received UTF8 artifact, not privately
    correct. A returned syntax/runtime-failing program is still a returned
    artifact; do not choose its predecessor using private scores. No fallback
    can invent an absent initial answer or turn unavailable logs into STOP.
    """
    if policy != 'retain-last-valid-on-receiver-failure-v1':
        raise ValueError('explicit prospective fallback identity required')
    if event == 'returned':
        if type(returned_artifact) is not str:
            raise ValueError('returned UTF8 artifact required')
        returned_artifact.encode('utf-8', 'strict')
        artifact, disposition = returned_artifact, 'returned'
    elif event in ('receiver_failure', 'receiver_timeout', 'unattempted_after_cap'):
        if type(last_valid_artifact) is not str:
            return {'artifact': None, 'artifact_sha256': None,
                    'disposition': 'no-observed-initial-artifact', 'STOP': False}
        last_valid_artifact.encode('utf-8', 'strict')
        artifact, disposition = last_valid_artifact, 'prospective-last-valid-fallback'
    else:
        raise ValueError('missing logs/integrity failure are not receiver fallback events')
    return {'artifact': artifact, 'artifact_sha256': runtime.sha256(artifact.encode('utf-8')),
            'disposition': disposition, 'STOP': False}
