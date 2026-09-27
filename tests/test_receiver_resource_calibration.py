from copy import deepcopy
from scripts.calibrate_receiver_resources_20260927 import build_requests, resource_violation


def test_assignments_remain_separate_with_fixed_sampler_and_no_cache():
    p={'instruction':'count','context_line':'data\n','assignments':[{'length_label':'short','repeats':2,'seed':4},{'length_label':'long','repeats':3,'seed':5}]}
    r=build_requests(p)
    assert [x['payload']['seed'] for x in r]==[4,5]
    assert [x['payload']['messages'][1]['content'] for x in r]==['count\ndata\ndata\n','count\ndata\ndata\ndata\n']
    assert all(x['payload']['cache_prompt'] is False and x['payload']['max_tokens']==512 for x in r)


def test_resource_trips_and_none_rss():
    p={'min_pressure_free_percent':15,'max_swap_growth_mib':2048,'max_receiver_rss_bytes':100,'min_disk_available_bytes':1000}
    b={'memory_pressure_free_percent':50,'swap_used_mib':100,'rss_bytes':None,'disk_available_bytes':2000}
    assert resource_violation(b,b,p) is None
    for key,value,reason in [('memory_pressure_free_percent',14,'memory_pressure'),('swap_used_mib',2149,'swap_growth'),('rss_bytes',101,'receiver_rss'),('disk_available_bytes',999,'disk_available')]:
        q=deepcopy(b);q[key]=value
        assert resource_violation(q,b,p)==reason


def test_analysis_keeps_failed_and_unassigned_calls():
    from scripts.analyze_receiver_calibration_20260927 import summarize
    r=summarize({'planned_calls':9,'calls':[{'length_label':'short','status':'failed'}], 'guard_failure':['wall'],'error':'timeout'})
    assert r['assigned']==1 and r['unassigned']==8
    assert r['groups']['short']['failed']==1 and r['groups']['short']['seconds'] is None
