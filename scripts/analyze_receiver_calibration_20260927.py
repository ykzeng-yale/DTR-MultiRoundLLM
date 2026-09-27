#!/usr/bin/env python3
"""Descriptive accounting only; no throughput extrapolation or efficacy inference."""
import argparse
import json
from pathlib import Path
import statistics


def summarize(record):
    groups={}
    for row in record['calls']:
        label=row['length_label'];group=groups.setdefault(label,{'assigned':0,'returned':0,'failed':0,'seconds':[],'prompt_tokens':[],'completion_tokens':[]})
        group['assigned']+=1
        if row['status']=='returned':
            group['returned']+=1;group['seconds'].append(row['seconds']);group['prompt_tokens'].append(row['prompt_tokens']);group['completion_tokens'].append(row['completion_tokens'])
        else:group['failed']+=1
    for group in groups.values():
        for field in ['seconds','prompt_tokens','completion_tokens']:
            values=group.pop(field)
            group[field]={'min':min(values),'median':statistics.median(values),'max':max(values)} if values else None
    return {'classification':'descriptive synthetic calibration; no benchmark efficacy, power or reliable multi-slot capacity estimate',
            'planned':record['planned_calls'],'assigned':len(record['calls']),
            'unassigned':record['planned_calls']-len(record['calls']),
            'groups':groups,'guard_failure':record['guard_failure'],'error':record['error'],
            'receiver_exit_observed':record.get('receiver_exit_observed',False),
            'energy_measured':False,'paid_usd':0}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('summary',type=Path);a=p.parse_args()
    print(json.dumps(summarize(json.loads(a.summary.read_bytes())),indent=2))
