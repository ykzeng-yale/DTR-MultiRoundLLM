"""Frozen standard-input/output instrument with external exact comparison.

Only source and UTF-8 invocation input enter the strict child boundary. Private
expectations and comparison code stay in the supervisor. Candidate stdout is
the scored endpoint, not proof of an internal object, algorithm or all-input
semantics. Exact/CRLF or ASCII-whitespace token contracts require separate
source-task unique-output adjudication. Token comparison is valid only where
that source supports token-exact unique output; it is not generic semantic
equivalence. This module admits no task and releases no collection.
"""
import hashlib
import json
from pathlib import Path
import re
import sys

from experiments.prompt_choice import native_execution_v1 as classification
from experiments.prompt_choice import native_execution_v2 as execution
from experiments.prompt_choice import strict_sandbox_v2 as sandbox
from experiments.prompt_choice import status_feedback_v1 as feedback
from scripts import check_landmark_sandbox as checker

VERSION = 'frozen-utf8-stdio-observation-v1'
NORMALIZATIONS = ('exact', 'crlf-to-lf', 'ascii-whitespace-tokens-v1')
MAX_BYTES = 65536


def _bytes(text, *, output=False):
    if type(text) is not str:
        raise ValueError('bounded UTF-8 text required')
    try:
        raw = text.encode('utf-8', errors='strict')
    except UnicodeEncodeError as exc:
        raise ValueError('bounded UTF-8 text required') from exc
    if len(raw) > MAX_BYTES or (output and len(raw) == MAX_BYTES):
        raise ValueError('bounded UTF-8 text required')
    return raw


def canonical_stdout(text, normalization):
    """Apply only the independently frozen formatting contract.

    The token option splits ASCII space/tab/CR/LF/formfeed/vertical-tab only,
    preserving every token's text and order. It does not interpret numbers,
    case, Unicode whitespace, permutations or multiple acceptable answers.
    """
    _bytes(text, output=True)
    if normalization not in NORMALIZATIONS:
        raise ValueError('predeclared stdout normalization required')
    if normalization == 'ascii-whitespace-tokens-v1':
        return tuple(token for token in re.split(r'[ \t\r\n\f\v]+', text) if token)
    return text if normalization == 'exact' else text.replace('\r\n', '\n')


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def _serialize(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode()


def source_bindings():
    modules = {'scorer': sys.modules[__name__], 'execution': execution,
               'classification': classification, 'sandbox': sandbox,
               'containment_checker': checker, 'feedback': feedback}
    return {name: _hash(Path(module.__file__).read_bytes())
            for name, module in modules.items()}


def case_binding(case, scope):
    if (type(case) is not dict or set(case) != {'scope', 'stdin', 'expected_stdout'}
            or scope not in ('public', 'private') or case['scope'] != scope):
        raise ValueError('separately scoped stdio case required')
    _bytes(case['stdin'])
    _bytes(case['expected_stdout'], output=True)
    return _hash(_serialize(case))


def freeze_instrument(cases, *, scope, normalization='exact'):
    if (scope not in ('public', 'private') or type(cases) is not list or not cases
            or normalization not in NORMALIZATIONS):
        raise ValueError('separate nonempty instrument and explicit normalization required')
    hashes = [case_binding(case, scope) for case in cases]
    if len(set(hashes)) != len(hashes):
        raise ValueError('duplicate frozen stdio case')
    return {'version': VERSION, 'scope': scope, 'case_sha256s': sorted(hashes),
            'normalization': normalization, 'source_sha256s': source_bindings()}


def instrument_sha256(instrument):
    return _hash(_serialize(instrument))


def _member(case, instrument, expected_instrument_sha256, scope):
    if (type(instrument) is not dict
            or set(instrument) != {'version', 'scope', 'case_sha256s', 'normalization', 'source_sha256s'}
            or instrument['version'] != VERSION or instrument['scope'] != scope
            or instrument['normalization'] not in NORMALIZATIONS
            or instrument['source_sha256s'] != source_bindings()):
        raise ValueError('stdio instrument scope/source/normalization drift')
    hashes = instrument['case_sha256s']
    if (type(hashes) is not list or not hashes
            or any(type(value) is not str or len(value) != 64
                   or any(c not in '0123456789abcdef' for c in value) for value in hashes)
            or hashes != sorted(set(hashes))):
        raise ValueError('frozen stdio membership hashes required')
    if instrument_sha256(instrument) != expected_instrument_sha256:
        raise ValueError('stdio instrument differs from independently pinned digest')
    binding = case_binding(case, scope)
    if binding not in hashes:
        raise ValueError('stdio case absent from frozen instrument')
    return binding


def _evaluate(code, case, *, instrument, expected_instrument_sha256,
              containment_attestation, scope, runner):
    case_hash = _member(case, instrument, expected_instrument_sha256, scope)
    if type(code) is not str or len(code.encode('utf-8')) > 1048576:
        raise ValueError('bounded candidate source required')
    stdin_bytes = _bytes(case['stdin'])
    artifact = _hash(code.encode('utf-8'))
    execution.verify_attestation(containment_attestation)
    if runner is None:
        runner = execution.run_stdin
    # Only these source/input arguments are staged by the isolated runner.
    process = runner(code, stdin_bytes, attestation_path=containment_attestation,
        timeout_s=2.0, cpu_seconds=1, output_cap=MAX_BYTES, mem_bytes=256 << 20)
    disposition = process['execution']['disposition']
    receipt = {'version': VERSION, 'artifact_sha256': artifact,
               'case_sha256': case_hash, 'stdin_sha256': _hash(stdin_bytes),
               'expected_stdout_sha256': _hash(_bytes(case['expected_stdout'], output=True)),
               'instrument_sha256': expected_instrument_sha256,
               'normalization': instrument['normalization'], 'process': process}
    if disposition != 'completed_ungraded':
        return dict(receipt, status='INCOMPLETE', outcome=None, reason=disposition)
    raw = process['raw_process']
    if raw.get('stdout_utf8_valid') is not True:
        return dict(receipt, status='INCOMPLETE', outcome=None, reason='invalid_stdout_utf8')
    try:
        actual = canonical_stdout(raw['stdout'], instrument['normalization'])
    except ValueError:
        return dict(receipt, status='INCOMPLETE', outcome=None, reason='invalid_or_saturated_stdout')
    expected = canonical_stdout(case['expected_stdout'], instrument['normalization'])
    passed = actual == expected
    return dict(receipt, status='PASS' if passed else 'FAIL', outcome=int(passed),
                reason='external_frozen_stdout_comparison')


def public_check(code, case, *, instrument, expected_instrument_sha256,
                 containment_attestation, runner=None):
    receipt = _evaluate(code, case, instrument=instrument,
        expected_instrument_sha256=expected_instrument_sha256,
        containment_attestation=containment_attestation, scope='public', runner=runner)
    record = {'version': feedback.VERSION, 'artifact_sha256': receipt['artifact_sha256'],
              'public_test_sha256': receipt['case_sha256'], 'status': receipt['status']}
    text = feedback.render(record, expected_artifact_sha256=receipt['artifact_sha256'],
                           expected_public_test_sha256=receipt['case_sha256'])
    return {'feedback_text': text, 'audit': {'receipt': receipt, 'feedback_record': record}}


def private_check(code, case, *, instrument, expected_instrument_sha256,
                  containment_attestation, runner=None):
    return _evaluate(code, case, instrument=instrument,
        expected_instrument_sha256=expected_instrument_sha256,
        containment_attestation=containment_attestation, scope='private', runner=runner)
