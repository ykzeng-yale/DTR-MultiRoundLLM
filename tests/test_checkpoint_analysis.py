from scripts.grade_checkpoint_challenge_20260928 import describe

def test_missing_arm_keeps_full_denominator_and_bounds():
    base=[{'root':r,'artifact':'reference','batteries':{'supplement_v1':'PASS'}} for r in ['a','b']]
    rows=[{'root':'a','artifact':'reference','arm':'PATCH','batteries':{'supplement_v1':'FAIL'}}]
    x=describe(rows,base)
    assert x['mean_bounds']['PATCH']==[0,.5]
    assert x['mean_bounds']['STOP']==[1,1]
    assert x['contrast_bounds']['PATCH-STOP']==[-1,-.5]
    assert x['by_initial_artifact_kind']['reference']['PATCH']=={'PASS':0,'FAIL':1,'INCOMPLETE':1}
