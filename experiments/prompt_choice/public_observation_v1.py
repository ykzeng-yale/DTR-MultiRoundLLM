"""Trusted public-status producer for the restricted JSON observation endpoint.

Private case objects are never accepted by the public API. This boundary prevents
accidental private-result routing, not a malicious trusted host or arbitrary native
object grading. Each evaluate invocation creates a fresh isolated process.
"""
import hashlib
from experiments.prompt_choice import observation_boundary_v1 as ob
from experiments.prompt_choice import status_feedback_v1 as feedback


def sha(text):return hashlib.sha256(text.encode()).hexdigest()


def case_binding(case,scope):
    if type(case) is not dict or set(case)!={'scope','entry_point','args','expected'} or case['scope']!=scope:
        raise ValueError('case scope/schema')
    ob.program('',case['entry_point'],case['args'])
    ob.encoded(case['expected'])
    return sha(ob.encoded([scope,case['entry_point'],case['args'],case['expected']]))


def public_check(code,case,*,runner=ob.run):
    binding=case_binding(case,'public')
    receipt=ob.evaluate(code,case['entry_point'],case['args'],case['expected'],runner=runner)
    artifact=sha(code)
    if receipt['artifact_sha256']!=artifact:raise ValueError('artifact binding')
    record={'version':feedback.VERSION,'artifact_sha256':artifact,'public_test_sha256':binding,'status':receipt['status']}
    text=feedback.render(record,expected_artifact_sha256=artifact,expected_public_test_sha256=binding)
    # Only text belongs in receiver-visible history. Receipt remains trusted storage.
    return {'feedback_text':text,'audit':{'case_sha256':binding,'receipt':receipt,'feedback_record':record}}


def private_check(code,case,*,runner=ob.run):
    binding=case_binding(case,'private')
    receipt=ob.evaluate(code,case['entry_point'],case['args'],case['expected'],runner=runner)
    return {'case_sha256':binding,'receipt':receipt}
