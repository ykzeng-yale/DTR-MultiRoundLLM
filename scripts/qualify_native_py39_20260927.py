#!/usr/bin/env python3
"""Frozen harmless qualification of a pinned Python3.9 dependency sandbox."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from experiments.prompt_choice.dependency_sandbox_v1 import run

PLAN=Path('experiments/prompt_choice/native_py39_qualification_plan_20260927.json')


def sources(bundle):
    repo=str(Path('COORDINATION.md').resolve());b=str(Path(bundle).resolve()/'__qualification_write__')
    return [(f'import_{name}',f'import {name}\nprint("QUALIFIED")\n') for name in ('numpy','pandas','scipy','sklearn','matplotlib','psutil','cryptography','seaborn','pytz','nltk','openpyxl','cv2','faker')] + [
        ('own_directory','open("own.txt","w").write("ok")\nassert open("own.txt").read()=="ok"\nprint("QUALIFIED")\n'),
        ('repository_read',f'try:\n    open({repo!r}).read()\nexcept PermissionError:\n    print("QUALIFIED")\n'),
        ('bundle_write',f'try:\n    open({b!r},"x").write("probe")\nexcept PermissionError:\n    print("QUALIFIED")\n'),
        ('network_connect','import socket\ns=socket.socket()\ns.settimeout(1)\ntry:\n    s.connect(("127.0.0.1",9))\nexcept PermissionError:\n    print("QUALIFIED")\nfinally:\n    s.close()\n'),
        ('fork','import os,errno\ntry:\n    pid=os.fork()\nexcept OSError as exc:\n    assert exc.errno in (errno.EPERM,errno.EAGAIN)\n    print("QUALIFIED")\nelse:\n    if pid==0: os._exit(0)\n    os.waitpid(pid,0)\n'),
        ('system_exec','import subprocess,errno\ntry:\n    subprocess.run(["/usr/bin/true"],timeout=1)\nexcept OSError as exc:\n    assert exc.errno in (errno.EPERM,errno.EAGAIN)\n    print("QUALIFIED")\n'),
    ]


def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,default=PLAN);p.add_argument('--freeze',required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    freeze=subprocess.check_output(['git','rev-parse',args.freeze],text=True).strip();plan_path=args.plan;plan=json.loads(plan_path.read_bytes())
    for path in [str(plan_path),*plan['committed_sources']]:
        if subprocess.check_output(['git','show',freeze+':'+path])!=Path(path).read_bytes():raise ValueError('freeze mismatch')
    for path,h in plan['input_sha256'].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=h:raise ValueError('pin mismatch')
    if args.out.exists():raise ValueError('refuse overwrite')
    args.out.mkdir(parents=True);start=time.monotonic();rows=[]
    summary={'classification':'known harmless containment/import qualification; no benchmark/model calls','freeze':freeze,'python':plan['python'],'python_sha256':plan['python_sha256'],'bundle_sha256':plan['tree_sha256'],'rows':rows,'error':None}
    try:
        for name,source in sources(plan['bundle']):
            if time.monotonic()-start>plan['total_wall_seconds']-12:raise RuntimeError('total cap')
            rec=run(source,bundle=plan['bundle'],tree_sha256=plan['tree_sha256'],python=plan['python'],runtime_read_root=plan.get('runtime_read_root'),timeout_s=10,cpu_seconds=5,output_cap=65536,mem_bytes=1<<30)
            path=args.out/(name+'.json');path.write_text(json.dumps(rec,indent=2)+'\n')
            passed=rec['execution']['disposition']=='completed_ungraded' and rec['raw_process']['stdout'].splitlines()==['QUALIFIED']
            rows.append({'name':name,'passed':passed,'receipt_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'seconds':rec['raw_process']['seconds']})
    except BaseException as exc:
        summary['error']=type(exc).__name__+': '+str(exc);raise
    finally:
        summary['elapsed_seconds']=time.monotonic()-start;summary['passed']=len(rows)==plan['slots'] and all(r['passed'] for r in rows)
        (args.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary))


if __name__=='__main__':main()
