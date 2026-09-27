import pytest
from experiments.prompt_choice import status_feedback_v1 as s


def record(status='PASS',**kw):
    return {'version':s.VERSION,'artifact_sha256':'a'*64,'public_test_sha256':'b'*64,'status':status,**kw}


def render(r):
    return s.render(r,expected_artifact_sha256='a'*64,expected_public_test_sha256='b'*64)


@pytest.mark.parametrize('status',s.STATUSES)
def test_exact_fixed_text_and_no_bindings(status):
    text=render(record(status))
    assert text==s.TEXT[status]
    assert 'a'*64 not in text and 'b'*64 not in text


@pytest.mark.parametrize('key',['expected','actual','stdout','stderr','exception','traceback','private_grade','test_name','test_source','duration'])
def test_forbidden_fields_never_reflected(key):
    secret='PRIVATE_SENTINEL_42'
    with pytest.raises(ValueError) as error:render(record(**{key:secret}))
    assert secret not in str(error.value)


@pytest.mark.parametrize('bad',[None,True,0,[],{},'pass','FAIL\nanswer=42','PASS '])
def test_nonstatus_rejected_without_echo(bad):
    r=record();r['status']=bad
    with pytest.raises(ValueError,match='unknown feedback status'):render(r)


def test_binding_mismatch_is_not_incomplete():
    r=record('INCOMPLETE');r['artifact_sha256']='c'*64
    with pytest.raises(ValueError,match='binding mismatch'):render(r)


@pytest.mark.parametrize('key',['artifact_sha256','public_test_sha256'])
def test_hashes_malformed(key):
    r=record();r[key]='secret'
    with pytest.raises(ValueError,match='invalid binding hash'):render(r)


def test_exact_three_string_alphabet_for_all_valid_bindings():
    observed=set()
    for a in ('0','1','c'):
        for b in ('2','3','d'):
            for status in s.STATUSES:
                r=record(status);r.update(artifact_sha256=a*64,public_test_sha256=b*64)
                observed.add(s.render(r,expected_artifact_sha256=a*64,expected_public_test_sha256=b*64))
    assert observed==set(s.TEXT.values()) and len(observed)==3


def test_missing_version_and_extra_schema_refused():
    r=record();del r['version']
    with pytest.raises(ValueError,match='schema'):render(r)
    r=record();r['version']='legacy'
    with pytest.raises(ValueError,match='version'):render(r)
