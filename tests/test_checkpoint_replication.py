from scripts.grade_checkpoint_replication_20260928 import describe

def test_replicates_not_overwritten_or_dropped():
    base=[{'root':'a','artifact':'reference','replicate':j,'batteries':{'supplement_v1':'PASS'}} for j in range(3)]
    rows=[{'root':'a','artifact':'reference','replicate':j,'arm':'PATCH','batteries':{'supplement_v1':s}} for j,s in enumerate(['PASS','FAIL'])]
    a=describe(rows,base)
    assert a['mean_bounds']['PATCH']==[1/3,2/3]
    assert a['by_initial_artifact_kind']['reference']['PATCH']=={'PASS':1,'FAIL':1,'INCOMPLETE':1}
