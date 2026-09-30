"""Prepare/reconcile frozen sprint data, never execute candidate code.

Public/private observation receipts are produced by a separately qualified
isolated grader. This command cannot release collection or certify admission.
All outputs use a fresh directory; sealed private bytes are read only after a
terminal-state gate. Exact receiver/config/file hashes are caller freeze gates.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from experiments.sprint import pipeline_v1 as pipeline


def read(path):
    return json.loads(path.read_bytes())


def tasks(path):
    text=path.read_text()
    return json.loads(text) if text.lstrip().startswith('[') else [json.loads(line) for line in text.splitlines() if line.strip()]


def observer(receipts, expected_scope, expected_pin):
    if not isinstance(receipts,list): raise ValueError('observation receipt list')
    mapped = {}
    for receipt in receipts:
        if set(receipt) != {'grading_unit_id','root','program_sha256','scope','observer_sha256','observation'} or receipt['scope'] != expected_scope or receipt['observer_sha256'] != expected_pin:
            raise ValueError('source/scope-bound qualified observation receipt')
        key = (receipt['grading_unit_id'],receipt['root'],receipt['program_sha256'])
        if key in mapped: raise ValueError('duplicate observation receipt')
        mapped[key] = receipt['observation']
    def get(unit_id,root,program):
        key = (unit_id,root,pipeline.text_sha(program))
        if key not in mapped: raise ValueError('missing exact artifact observation')
        return mapped[key]
    return get


def main():
    p = argparse.ArgumentParser()
    p.add_argument('operation',choices=('initialize','public-assignments','advance','private-assignments','join','fit','select-b1','accounting','analyze'))
    p.add_argument('--config',type=Path,required=True)
    p.add_argument('--tasks',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--state',type=Path)
    p.add_argument('--receipt',type=Path)
    p.add_argument('--observations',type=Path)
    p.add_argument('--joined',type=Path)
    p.add_argument('--models',type=Path)
    a = p.parse_args()
    config, public = read(a.config), tasks(a.tasks)
    pipeline.validate_config(config,public)
    state = read(a.state) if a.state else None
    if a.operation == 'initialize':
        result = pipeline.initialize(config,public,models=read(a.models)['models'] if a.models else None)
    elif a.operation == 'public-assignments':
        result = pipeline.public_assignments(state,read(a.receipt))
    elif a.operation == 'advance':
        observe = observer(read(a.observations),'public',config['pins']['public_observer'])
        result = pipeline.advance(state,read(a.receipt),config,public,observe)
    elif a.operation == 'private-assignments':
        result = pipeline.private_assignments(state)
    elif a.operation == 'join':
        # Gate is intentionally before opening the supplied private receipt.
        pipeline.private_assignments(state)
        grade = observer(read(a.observations),'private',config['pins']['private_observer'])
        result = pipeline.terminal_label_join(state,config,public,grade)
    elif a.operation == 'fit':
        result = pipeline.fit_models(state,read(a.joined),config,public)
    elif a.operation == 'select-b1':
        result = pipeline.select_b1(state,read(a.joined),config)
    elif a.operation == 'analyze':
        result = pipeline.analyze(state,read(a.joined),config)
    else:
        result = pipeline.accounting(state)
    a.out.mkdir(exist_ok=False)
    (a.out/'result.json').write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    if isinstance(result,dict) and 'requests' in result:
        (a.out/'requests.json').write_text(json.dumps(result['requests'],indent=2,ensure_ascii=False)+'\n')
    (a.out/'operation.json').write_text(json.dumps({'operation':a.operation,
        'config_sha256':config['config_sha256'],'output_sha256':pipeline.sha(result),
        'candidate_code_executed':False,'model_calls':0})+'\n')


if __name__ == '__main__': main()
