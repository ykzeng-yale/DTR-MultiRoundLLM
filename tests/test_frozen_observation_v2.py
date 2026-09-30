"""Instrument/transport checks; mock processes only, no candidate execution."""
import copy
import json

import pytest

from experiments.prompt_choice import frozen_observation_v2 as frozen
from experiments.prompt_choice import observation_boundary_v1 as ob
from experiments.prompt_choice.status_feedback_v1 import TEXT


def case(scope='public', expected=8):
    return {'scope': scope, 'entry_point': 'task_func', 'args': [7], 'expected': expected}


def runner(source, **kwargs):
    return {'execution': {'disposition': 'completed_ungraded'},
            'raw_process': {'stdout': json.dumps({'observation_version': ob.VERSION, 'value': 8})}}


def check(c, instrument, digest, run=runner):
    return frozen.public_check('def task_func(x): return x+1', c,
        instrument=instrument, expected_instrument_sha256=digest,
        containment_attestation='trusted-mock-attestation', runner=run)


def test_frozen_membership_and_host_verification_precede_execution(monkeypatch):
    instrument = frozen.freeze_instrument([case()], scope='public')
    digest = frozen.instrument_sha256(instrument)
    events = []
    monkeypatch.setattr(frozen.execution, 'verify_attestation', lambda p: events.append('verified'))
    def traced(source, **kwargs):
        assert events == ['verified']
        events.append('observed')
        return runner(source, **kwargs)
    out = check(case(), instrument, digest, traced)
    assert out['feedback_text'] == TEXT['PASS']
    assert out['audit']['instrument_sha256'] == digest
    assert events == ['verified', 'observed']


@pytest.mark.parametrize('change', ['expected', 'scope', 'digest', 'source'])
def test_wrong_case_or_freeze_refused_before_launch(change, monkeypatch):
    instrument = frozen.freeze_instrument([case()], scope='public')
    digest = frozen.instrument_sha256(instrument)
    c = case()
    if change == 'expected': c['expected'] = 9
    if change == 'scope': c['scope'] = 'private'
    if change == 'digest': digest = '0'*64
    if change == 'source': instrument['source_sha256s']['sandbox'] = '0'*64
    def never(*args, **kwargs): raise AssertionError('reached execution/attestation')
    monkeypatch.setattr(frozen.execution, 'verify_attestation', never)
    with pytest.raises(ValueError): check(c, instrument, digest, never)


def test_relabeling_private_case_public_does_not_grant_membership(monkeypatch):
    instrument = frozen.freeze_instrument([case()], scope='public')
    relabeled = case('private', 999)
    relabeled['scope'] = 'public'
    def never(*args, **kwargs): raise AssertionError('reached execution')
    monkeypatch.setattr(frozen.execution, 'verify_attestation', never)
    with pytest.raises(ValueError, match='absent'): check(relabeled, instrument, frozen.instrument_sha256(instrument), never)


def test_failed_attestation_prevents_process_start(monkeypatch):
    instrument = frozen.freeze_instrument([case()], scope='public')
    def refuse(path): raise ValueError('stale containment')
    def never(*args, **kwargs): raise AssertionError('executed')
    monkeypatch.setattr(frozen.execution, 'verify_attestation', refuse)
    with pytest.raises(ValueError, match='stale'):
        check(case(), instrument, frozen.instrument_sha256(instrument), never)


def test_private_instrument_never_produces_feedback(monkeypatch):
    instrument = frozen.freeze_instrument([case('private', 999)], scope='private')
    monkeypatch.setattr(frozen.execution, 'verify_attestation', lambda p: {})
    out = frozen.private_check('pass', case('private', 999), instrument=instrument,
        expected_instrument_sha256=frozen.instrument_sha256(instrument),
        containment_attestation='trusted-mock', runner=runner)
    assert 'feedback_text' not in out and out['receipt']['status'] == 'FAIL'


def test_duplicate_or_unsupported_instruments_refused():
    with pytest.raises(ValueError, match='duplicate'):
        frozen.freeze_instrument([case(), case()], scope='public')
    with pytest.raises(ValueError): frozen.freeze_instrument([], scope='public')
    with pytest.raises(ValueError): frozen.freeze_instrument([case()], scope='private')
    c = case(); c['expected'] = (8,)
    with pytest.raises(ValueError, match='unsupported'):
        frozen.freeze_instrument([c], scope='public')
