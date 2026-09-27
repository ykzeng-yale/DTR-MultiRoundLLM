#!/usr/bin/env python3
"""Frozen random source-ID reference feasibility audit, never receiver grading."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from experiments.prompt_choice.dependency_sandbox_v1 import run

PLAN=Path('experiments/prompt_choice/native_reference_sample_plan_20260927.json')
MARKER='NATIVE_REFERENCE_REPORT '


def render(row):
    # No source rewriting or assertion selection. Prefix fixes execution RNGs;
    # appended reporting uses the publisher's named TestCases class.
    return ('import random\nimport numpy as _audit_numpy\nrandom.seed(2026092702)\n_audit_numpy.random.seed(2026092702)\n'+
            row['complete_prompt']+row['canonical_solution']+'\n'+row['test']+
            '\nimport unittest as _audit_unittest, json as _audit_json\n'+
            '_audit_suite=_audit_unittest.defaultTestLoader.loadTestsFromTestCase(TestCases)\n'+
            '_audit_result=_audit_unittest.TextTestRunner(verbosity=1).run(_audit_suite)\n'+
            'print('+repr(MARKER)+"+_audit_json.dumps({'tests_run':_audit_result.testsRun,'failures':len(_audit_result.failures),'errors':len(_audit_result.errors),'skips':len(_audit_result.skipped),'expected_failures':len(_audit_result.expectedFailures),'unexpected_successes':len(_audit_result.unexpectedSuccesses),'was_successful':_audit_result.wasSuccessful()}))\n")


def extract(raw):
    if raw['execution']['disposition']!='completed_ungraded':return None
    lines=[l[len(MARKER):] for l in raw['raw_process']['stdout'].splitlines() if l.startswith(MARKER)]
    if len(lines)!=1:return None
    try:obj=json.loads(lines[0])
    except ValueError:return None
    count_keys={'tests_run','failures','errors','skips','expected_failures','unexpected_successes'}
    if type(obj) is not dict or set(obj)!=count_keys|{'was_successful'}:return None
    if any(type(obj[k]) is not int or obj[k]<0 for k in count_keys) or type(obj['was_successful']) is not bool:return None
    return obj


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--plan',type=Path,default=PLAN);parser.add_argument('--freeze',required=True);parser.add_argument('--raw-out',type=Path,required=True);parser.add_argument('--summary-out',type=Path,required=True);args=parser.parse_args()
    freeze=subprocess.check_output(['git','rev-parse',args.freeze],text=True).strip()
    plan_path=args.plan
    plan=json.loads(plan_path.read_bytes())
    for path in [str(plan_path),*plan['committed_sources']]:
        if subprocess.check_output(['git','show',freeze+':'+path])!=Path(path).read_bytes():raise ValueError('freeze mismatch')
    for path,h in plan['input_sha256'].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=h:raise ValueError('input hash mismatch')
    rows=json.loads(Path(plan['source_sample_path']).read_bytes())
    if [r['task_id'] for r in rows]!=plan['task_ids']:raise ValueError('sample order mismatch')
    if args.raw_out.exists() or args.summary_out.exists():raise ValueError('refuse reused output')
    args.raw_out.mkdir(parents=True);start=time.monotonic()
    summary={'classification':'random source-ID reference feasibility under current contained environment; not semantic correctness, family eligibility or efficacy','freeze':freeze,'config_sha256':hashlib.sha256(plan_path.read_bytes()).hexdigest(),'task_slots_planned':len(rows),'task_slots_attempted':0,'rows':[],'error':None,'receiver_calls':0,'paid_usd':0}
    def execute(source):return run(source,bundle=plan['bundle'],tree_sha256=plan['tree_sha256'],timeout_s=10,cpu_seconds=5,output_cap=65536,mem_bytes=1<<30)
    try:
        smoke=execute('import numpy,pandas,scipy,sklearn\nprint("IMPORT_SMOKE_OK")\n')
        (args.raw_out/'smoke.json').write_text(json.dumps(smoke,indent=2)+'\n')
        summary['smoke_completed']=smoke['execution']['disposition']=='completed_ungraded' and 'IMPORT_SMOKE_OK' in smoke['raw_process']['stdout'].splitlines()
        if not summary['smoke_completed']:raise RuntimeError('dependency smoke failed; no benchmark start')
        for row in rows:
            if time.monotonic()-start>plan['total_wall_seconds']-15:raise RuntimeError('remaining wall cap insufficient')
            tid=row['task_id'];number=tid.split('/')[-1];source=render(row)
            entry={'task_id':tid,'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'status':'assigned','native_report':None}
            summary['rows'].append(entry);summary['task_slots_attempted']+=1
            record=execute(source)
            path=args.raw_out/(number+'.json');path.write_text(json.dumps(record,indent=2)+'\n')
            report=extract(record)
            entry.update(status=record['execution']['disposition'],native_report=report,raw_path=str(path),raw_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),seconds=record['raw_process']['seconds'])
            # Exception names only; raw tracebacks/reference snippets stay ignored.
            text=record['raw_process']['stderr']
            entry['stderr_exception_classes']=sorted({line.split(':',1)[0] for line in text.splitlines() if ':' in line and line.split(':',1)[0].isidentifier() and line.split(':',1)[0].endswith(('Error','Exception','Warning'))})
            args.summary_out.write_text(json.dumps(summary,indent=2)+'\n')
    except BaseException as exc:
        summary['error']=type(exc).__name__+': '+str(exc)
        raise
    finally:
        summary['elapsed_seconds']=time.monotonic()-start
        summary['task_slots_unattempted']=len(rows)-summary['task_slots_attempted']
        args.summary_out.write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({'attempted':summary['task_slots_attempted'],'native_reports':sum(x['native_report'] is not None for x in summary['rows']),'elapsed_seconds':summary['elapsed_seconds'],'error':summary['error']}))


if __name__=='__main__':main()
