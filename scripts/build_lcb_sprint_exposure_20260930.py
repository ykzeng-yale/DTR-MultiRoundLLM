#!/usr/bin/env python3
"""Refresh historical identities only; nonfinite scores cannot select the roster.

No model outputs, task programs, private tests, labels or numeric scores are
traversed. Nonfinite scalar tokens in old JSON are inert placeholders. Their
existence is counted without giving them numerical meaning. Test-source parsing
remains strict and is never patched by this process.
"""
import argparse
import json
from pathlib import Path
import resource
import signal
import sys
import time
try:
    import build_lcb_sprint_bundle_20260930 as bundle
except ModuleNotFoundError:
    from scripts import build_lcb_sprint_bundle_20260930 as bundle

NONFINITE = {'__historical_nonfinite_metadata_scalar__': True}


def historical_json(text, audit):
    def constant(_):
        audit['nonfinite_scalar_tokens_ignored'] += 1
        return dict(NONFINITE)
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:
                raise bundle.inquiry.InstrumentError('duplicate-historical-key')
            result[key]=value
        return result
    return json.loads(text,object_pairs_hook=pairs,parse_constant=constant)


def identity_shape_audit(value, totals):
    identities={'root','task_id','question_id','problem_id','uid','task'}
    forbidden={'code','stdout','stderr','response','responses','completion','completions',
        'output','outputs','grade','grades','outcome','outcomes','score','scores','label','labels',
        'private','private_test_cases','public_test_cases','test_cases','expected','expected_stdout',
        'hidden_tests','terminal_label','reward','rewards'}
    if isinstance(value,dict):
        for key,item in value.items():
            if key in forbidden or key.startswith(('private_','hidden_')): continue
            if key in identities:
                if item==NONFINITE:
                    totals['malformed_nonfinite_identity_fields'] += 1
                elif type(item) in (str,int):
                    totals['valid_scalar_identity_fields'] += 1
            if isinstance(item,(dict,list)): identity_shape_audit(item,totals)
    elif isinstance(value,list):
        for item in value:
            if isinstance(item,(dict,list)): identity_shape_audit(item,totals)


def run(plan_path, out):
    start=time.monotonic(); plan=bundle.inquiry.strict_json(Path(plan_path).read_text())
    signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(bundle.BundleError('exposure-wall-cap')))
    signal.alarm(plan['wall_seconds'])
    soft,hard=resource.getrlimit(resource.RLIMIT_CPU)
    bound=plan['cpu_seconds']
    resource.setrlimit(resource.RLIMIT_CPU,(bound,bound+1))
    if bundle.file_hash(__file__)!=plan['runner_sha256']:
        raise bundle.BundleError('runner-pin')
    old_plan_path=bundle.ROOT/plan['source_plan_path']
    if bundle.file_hash(old_plan_path)!=plan['source_plan_sha256']:
        raise bundle.BundleError('source-plan-pin')
    old_plan=bundle.inquiry.strict_json(old_plan_path.read_text())
    if bundle.file_hash(bundle.__file__)!=old_plan['runner_sha256']:
        raise bundle.BundleError('original-identity-walker-pin')
    public=list(bundle.jsonl(bundle.ROOT/old_plan['public_rows_path']))
    audit={'nonfinite_scalar_tokens_ignored':0,'malformed_nonfinite_identity_fields':0,
           'valid_scalar_identity_fields':0}
    strict=bundle.inquiry.strict_json
    def inert_parse(text):
        value=historical_json(text,audit); identity_shape_audit(value,audit); return value
    bundle.inquiry.strict_json=inert_parse
    try:
        links,scanned=bundle.exposure_inventory(public,old_plan)
    finally:
        bundle.inquiry.strict_json=strict
    out=Path(out).resolve()
    if out.exists() or not out.is_relative_to(bundle.ROOT/'work'):
        raise bundle.BundleError('fresh-ignored-output')
    out.mkdir(parents=True,mode=0o700)
    raw={'schema':'lcb-sprint-historical-identity-refresh-v1','paths':scanned,'exact_links':links,
         'audit':audit,'source_plan_sha256':plan['source_plan_sha256'],
         'source_public_sha256':bundle.file_hash(bundle.ROOT/old_plan['public_rows_path']),
         'limitations':['Frozen repository identity metadata only; external logs and pretraining are not certified.',
             'Output/label/test payload fields were excluded from identity traversal.',
             'Nonfinite scalar score tokens are inert and cannot change task inclusion.',
             'No model/task/reference execution, private decoding or network request.']}
    raw_bytes=bundle.canonical(raw)+b'\n'
    usage=resource.getrusage(resource.RUSAGE_SELF)
    rss=usage.ru_maxrss*(1 if sys.platform=='darwin' else 1024)
    if rss>plan['rss_bytes'] or len(raw_bytes)>plan['retained_bytes']:
        raise bundle.BundleError('exposure-rss-or-prewrite-cap')
    path=out/'exposure-inventory.json';path.write_bytes(raw_bytes)
    status_counts={}
    for record in scanned: status_counts[record['status']]=status_counts.get(record['status'],0)+1
    summary={'schema':'lcb-sprint-historical-identity-refresh-summary-v1',
        'status':'COMPLETE_IDENTITY_METADATA_REFRESH','inventory_files':len(scanned),
        'status_counts':status_counts,'exact_link_roots':len(links),'audit':audit,
        'elapsed_seconds':time.monotonic()-start,'plan_sha256':bundle.file_hash(plan_path),
        'cpu_seconds':usage.ru_utime+usage.ru_stime,'maximum_rss_bytes':rss,
        'raw':{'path':str(path.relative_to(bundle.ROOT)),'bytes':path.stat().st_size,'sha256':bundle.file_hash(path)},
        'no_roster_change':True,'model_calls':0,'task_code_executions':0,'private_decodes':0,'network_calls':0}
    (out/'summary.json').write_bytes(bundle.canonical(summary)+b'\n')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();print(json.dumps(run(a.plan,a.out),sort_keys=True))
