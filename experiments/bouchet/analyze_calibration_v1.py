"""Validate and summarize saved synthetic CUDA pilot receipts, never efficacy."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def analyze(plan,receipt):
    calls=receipt['calls'];requests=plan['requests']
    if len(calls)>len(requests):raise ValueError('extra calls')
    if receipt['unattempted']!=len(requests)-len(calls):raise ValueError('assignment accounting')
    groups={};returned=0;tokens=0;valid_lines=0
    for i,call in enumerate(calls):
        expected=requests[i]
        if call['slot']!=expected['slot'] or call['payload_sha256']!=digest(expected['payload']):raise ValueError('assignment mismatch')
        if call['status'] not in ('assigned','failed','returned'):raise ValueError('unknown status')
        if call['status']!='returned':continue
        response=call['response'];usage=response['usage'];n=usage['completion_tokens'];prompt=usage['prompt_tokens']
        if type(n) is not int or not 0<=n<=512 or type(prompt) is not int or prompt+512>8192:raise ValueError('token accounting')
        seconds=call['seconds']
        if type(seconds) not in (int,float) or not 0<seconds<=125:raise ValueError('latency accounting')
        text=response['choices'][0]['message']['content']
        # Explicit exact instruction compliance, not a task-quality endpoint.
        exact=text.strip().splitlines()==[f'{j}. ready' for j in range(1,201)]
        returned+=1;tokens+=n;valid_lines+=exact
        groups.setdefault(expected['length_label'],[]).append({'seconds':seconds,'completion_tokens':n,'prompt_tokens':prompt,'exact_200_numbered_ready_lines':exact})
    if tokens>4608:raise ValueError('total tokens')
    clean=(len(calls)==9 and returned==9 and receipt.get('error') is None and receipt.get('state_unchanged') is True and not receipt.get('guard_failures'))
    return {'classification':'synthetic operational calibration; no receiver-law equivalence, sustained-output throughput or policy efficacy established','assigned':len(calls),'returned':returned,'unattempted':receipt['unattempted'],'completion_tokens':tokens,'exact_instruction_compliance':valid_lines,'all_nine_returned_without_recorded_error':clean,'groups':{k:{'count':len(v),'median_seconds':statistics.median(x['seconds'] for x in v),'rows':v} for k,v in groups.items()},'error':receipt.get('error'),'elapsed_seconds':receipt['elapsed_seconds'],'gpu_hours_upper_from_job_limit':0.25,'actual_gpu_hours':'requires reconciled Slurm allocated elapsed time','money_usd':0,'energy':'not estimated from token counts'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('refuse overwrite')
    plan=json.loads(a.plan.read_bytes());receipt=json.loads(a.receipt.read_bytes())
    if hashlib.sha256(a.plan.read_bytes()).hexdigest()!=receipt['config_sha256']:raise ValueError('plan digest')
    if plan['build_manifest_sha256']!=receipt['build_manifest_sha256']:raise ValueError('build manifest')
    result=analyze(plan,receipt);result['receipt_sha256']=hashlib.sha256(a.receipt.read_bytes()).hexdigest()
    a.out.write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
