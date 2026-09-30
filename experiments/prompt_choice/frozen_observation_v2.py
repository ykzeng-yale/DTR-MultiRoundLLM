"""Frozen-instrument public/private JSON observation with containment gating.

Expected values remain host-side. Membership hashes bind a prospectively frozen
instrument; neither scope tags nor this API prove that its tests are valid or
secret. The endpoint concerns serialized output, not internal Python objects.
"""
import hashlib
import json
from pathlib import Path
from functools import partial
import sys

from experiments.prompt_choice import strict_sandbox_v2 as sandbox
from experiments.prompt_choice import observation_boundary_v1 as observation
from experiments.prompt_choice import native_execution_v1 as legacy_execution
from experiments.prompt_choice import native_execution_v2 as execution
from experiments.prompt_choice import public_observation_v1 as producer
from experiments.prompt_choice import status_feedback_v1 as feedback
from scripts import check_landmark_sandbox as checker

VERSION = 'frozen-json-observation-v2'


def _hash(text):
    return hashlib.sha256(text.encode()).hexdigest()


def _serialize(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def source_bindings():
    modules = {'enforcement': sys.modules[__name__], 'producer': producer,
               'observation': observation, 'execution': execution,
               'legacy_classification': legacy_execution, 'sandbox': sandbox,
               'feedback': feedback, 'containment_checker': checker}
    return {name: hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
            for name, module in modules.items()}


def freeze_instrument(cases, *, scope):
    if scope not in ('public', 'private') or type(cases) is not list or not cases:
        raise ValueError('nonempty separately scoped instrument required')
    bindings = [producer.case_binding(case, scope) for case in cases]
    if len(set(bindings)) != len(bindings):
        raise ValueError('duplicate frozen case')
    return {'version': VERSION, 'scope': scope, 'case_sha256s': sorted(bindings),
            'codec': observation.VERSION, 'source_sha256s': source_bindings()}


def instrument_sha256(instrument):
    return _hash(_serialize(instrument))


def _member(case, instrument, expected_instrument_sha256, scope):
    if (type(instrument) is not dict
            or set(instrument) != {'version', 'scope', 'case_sha256s', 'codec', 'source_sha256s'}
            or instrument.get('version') != VERSION or instrument.get('scope') != scope
            or instrument.get('codec') != observation.VERSION
            or instrument.get('source_sha256s') != source_bindings()):
        raise ValueError('instrument scope/source/codec drift')
    hashes = instrument['case_sha256s']
    if (type(hashes) is not list or not hashes
            or any(type(h) is not str or len(h) != 64
                   or any(c not in '0123456789abcdef' for c in h) for h in hashes)
            or hashes != sorted(set(hashes))):
        raise ValueError('frozen membership hashes')
    if instrument_sha256(instrument) != expected_instrument_sha256:
        raise ValueError('instrument differs from independently pinned digest')
    case_hash = producer.case_binding(case, scope)
    if case_hash not in hashes:
        raise ValueError('case is absent from frozen instrument')
    return case_hash


def public_check(code, case, *, instrument, expected_instrument_sha256,
                 containment_attestation, runner=None):
    _member(case, instrument, expected_instrument_sha256, 'public')
    execution.verify_attestation(containment_attestation)
    if runner is None:
        runner = partial(execution.run, attestation_path=containment_attestation)
    result = producer.public_check(code, case, runner=runner)
    result['audit']['instrument_sha256'] = expected_instrument_sha256
    result['audit']['instrument_version'] = VERSION
    return result


def private_check(code, case, *, instrument, expected_instrument_sha256,
                  containment_attestation, runner=None):
    _member(case, instrument, expected_instrument_sha256, 'private')
    execution.verify_attestation(containment_attestation)
    if runner is None:
        runner = partial(execution.run, attestation_path=containment_attestation)
    result = producer.private_check(code, case, runner=runner)
    result['instrument_sha256'] = expected_instrument_sha256
    result['instrument_version'] = VERSION
    return result
