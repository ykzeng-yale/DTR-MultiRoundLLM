"""Prospective status-only native-test feedback; no grader, execution or collection.

The trusted collector must authenticate the artifact/test binding. This pure serializer
cannot certify truth of a reported check. Private audit logs never enter this API.
"""
from __future__ import annotations
import hashlib
import json
import re

VERSION = 'native-status-feedback-v1'
STATUSES = ('PASS', 'FAIL', 'INCOMPLETE')
TEXT = {
    'PASS': 'Public check: PASS. This does not establish correctness on other inputs.',
    'FAIL': 'Public check: FAIL. The observed check did not pass; no expected or actual value is disclosed.',
    'INCOMPLETE': 'Public check: INCOMPLETE. Its outcome was not observed; this is neither a pass nor a demonstrated failure.',
}
FIELDS = frozenset({'version', 'artifact_sha256', 'public_test_sha256', 'status'})
SHA = re.compile(r'[0-9a-f]{64}\Z')


def _hash(value):
    if type(value) is not str or SHA.fullmatch(value) is None:
        raise ValueError('invalid binding hash')


def render(record, *, expected_artifact_sha256, expected_public_test_sha256):
    """Return only one fixed string. Bindings are checked but never rendered.

Extra keys fail closed, with constant errors rather than reflecting their contents.
Calls on invalid bindings must stop before receiver dispatch, not become a fourth
feedback category or automatically trigger a retry.
"""
    if type(record) is not dict or set(record) != FIELDS:
        raise ValueError('invalid feedback schema')
    if type(record['version']) is not str or record['version'] != VERSION:
        raise ValueError('unsupported feedback version')
    for value in (record['artifact_sha256'],record['public_test_sha256'],expected_artifact_sha256,expected_public_test_sha256):
        _hash(value)
    if record['artifact_sha256'] != expected_artifact_sha256 or record['public_test_sha256'] != expected_public_test_sha256:
        raise ValueError('feedback binding mismatch')
    status=record['status']
    if type(status) is not str or status not in STATUSES:
        raise ValueError('unknown feedback status')
    return TEXT[status]


def contract():
    payload={'version':VERSION,'statuses':list(STATUSES),'text':TEXT,'fields':sorted(FIELDS)}
    encoded=json.dumps(payload,sort_keys=True,separators=(',',':')).encode()
    return {**payload,'contract_sha256':hashlib.sha256(encoded).hexdigest()}
