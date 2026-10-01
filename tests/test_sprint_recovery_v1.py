import copy
import pytest
from experiments.sprint.recovery_v1 import PREFIX,GRADES,LIMITS,validate_prefix,verify_manifest

def inputs():
    sizes=[5472,3668,2478,444,1692,1679,3648]
    stages=[dict(stage_id=k,returned=n,error=None,failed=0,unattempted=0) for k,n in zip(PREFIX,sizes)]
    summary={'stages':stages,'grading':[{'grading_id':g} for g in GRADES],'error':"RuntimeError('finite wait expired before eval1')",'assigned_calls_reserved':19081,'completion_tokens_reserved':19538944}
    reports=[dict(complete_generation_integrity=True,assigned=n,returned=n) for n in sizes]
    limits={k:k for k in LIMITS};return summary,reports,limits,copy.deepcopy(limits)

def test_exact_prefix_cannot_replay_or_relax_budget():
    assert validate_prefix(*inputs())==19081
    for mutate in ('partial','reorder','budget','unknown','grade'):
        s,r,o,n=inputs()
        if mutate=='partial':s['stages'][-1]['unattempted']=1
        elif mutate=='reorder':s['stages'].reverse()
        elif mutate=='budget':n['max_calls']='expanded'
        elif mutate=='unknown':r[-1]['complete_generation_integrity']=False
        else:s['grading'].pop()
        with pytest.raises(ValueError):validate_prefix(s,r,o,n)

def test_manifest_requires_all_owned_files_and_refuses_mutation(tmp_path):
    import hashlib
    roots=[tmp_path/'a',tmp_path/'b']
    for r in roots:r.mkdir()
    f=roots[0]/'evidence';f.write_bytes(b'abc')
    x={'roots':[str(r) for r in roots],'files':[{'path':str(f),'bytes':3,'sha256':hashlib.sha256(b'abc').hexdigest()}]}
    assert verify_manifest(x)==3
    (roots[1]/'omitted').write_bytes(b'z')
    with pytest.raises(ValueError,match='omissions'):verify_manifest(x)
    (roots[1]/'omitted').unlink();f.write_bytes(b'xyz')
    with pytest.raises(ValueError,match='immutable'):verify_manifest(x)

def test_checkpoint_rebinding_retains_policy_and_eval_generation_and_requalifies():
    from scripts.drive_sprint_study_v2 import rebind_checkpoint
    done={k:{'frozen':k} for k in ('qualified','development_join','fit','tuning_join','select_b1','evaluation_freeze','eval0_generation')}
    old={'job_id':'27989272','done':done,'grading':[{'g':i} for i in range(6)]}
    plan={'spec':{'job_id':'999'},'plan_sha256':'new'}
    new=rebind_checkpoint(old,plan)
    assert 'qualified' not in new['done'] and 'qualified' in old['done']
    assert new['done']['fit']==old['done']['fit'] and new['grading']==old['grading']
    old['done']['eval1_generation']={}
    with pytest.raises(ValueError):rebind_checkpoint(old,plan)

def test_saved_batch_result_pin_is_summary_not_observation_array():
    from experiments.sprint import receiver_v1 as r
    observations=[{'grade':0}]
    summary={'observations_sha256':r.sha(observations),'accounted_units':1}
    record={'result_sha256':r.sha(summary)}
    assert record['result_sha256']==r.sha(summary)
    assert record['result_sha256']!=r.sha(observations)
