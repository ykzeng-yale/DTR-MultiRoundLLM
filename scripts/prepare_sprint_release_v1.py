"""Prepare exact finite stage/grading plans; no calls, execution or submission.

The lead must commit the emitted artifact hashes and source before publishing a
release. All data paths are relative to the exact owned study checkout. A ready
receipt binds this worker's independently recounted qualification, not a prior
host's capability check.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiments.sprint import receiver_v1 as receiver


def read(path):
    return json.loads(Path(path).read_bytes())


def digest(path):
    return receiver.file_sha(path)


def binding(worker, ready):
    if (ready['worker_plan_sha256'] != worker['_file_sha256'] or
        ready['model_sha256'] != worker['model_sha256'] or
        ready['build_manifest_sha256'] != worker['build_manifest_sha256'] or
        ready['receiver_state_sha256'] != worker['receiver_state_sha256'] or
        ready['server_count'] != worker['server_count'] or
        ready['owner_deadline_iso'] != worker['owner_deadline_iso']):
        raise ValueError('actual qualified worker/model/law binding')
    for key in ('runtime_manifest_sha256', 'attestation_file_sha256', 'receiver_qualification_sha256'):
        value = ready[key]
        if len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('complete qualified runtime/receiver evidence required')


def stage_plan(worker, ready, stage, config_path, state_path, requests_path, freeze, model_lock=None):
    binding(worker, ready)
    if stage not in worker['stage_ids'] or len(freeze) != 40 or any(c not in '0123456789abcdef' for c in freeze):
        raise ValueError('frozen ordered stage identity')
    config, state, requests = read(config_path), read(state_path), read(requests_path)
    expected_mode = {'dev':'development','tune':'tuning','eval':'evaluation'}[stage[:-1]]
    if (config['mode'] != expected_mode or state['phase'] != int(stage[-1]) or
        state['config_sha256'] != config['config_sha256'] or requests != state['requests'] or
        receiver.sha({k:v for k,v in config.items() if k != 'config_sha256'}) != config['config_sha256']):
        raise ValueError('exact state/config/ordered request binding')
    if config['pins']['receiver'] != worker['receiver_state_sha256']:
        raise ValueError('study receiver differs from qualified worker')
    if stage.startswith('eval'):
        if model_lock is None or (model_lock['model_sha256s'],model_lock['selected_b1'],model_lock['choice_lock_sha256']) != (config['model_sha256s'],config['selected_b1'],config['choice_lock_sha256']):
            raise ValueError('actually frozen policy/comparator lock')
    elif model_lock is not None:
        raise ValueError('premature model lock')
    plan = dict(stage_id=stage, contract_sha256=worker['contract_sha256'],
        freeze_commit=freeze, files=worker['files'], workers=worker['workers'],
        server_count=worker['server_count'], receiver_state_sha256=worker['receiver_state_sha256'],
        model_sha256=worker['model_sha256'], build_manifest_sha256=worker['build_manifest_sha256'],
        attestation_file_sha256=ready['attestation_file_sha256'],
        runtime_manifest_sha256=ready['runtime_manifest_sha256'],
        study_config_path=str(config_path),study_config_file_sha256=digest(config_path),
        study_config_sha256=config['config_sha256'],state_path=str(state_path),state_sha256=digest(state_path),
        requests_path=str(requests_path),requests_file_sha256=digest(requests_path),
        requests_canonical_sha256=receiver.sha(requests),max_calls=len(requests),
        max_completion_tokens=1024*len(requests),assignment_cap=62016,
        max_payload_bytes=262144,max_requests_bytes=512<<20,
        request_timeout_seconds=120,model_lock=model_lock)
    if requests:
        receiver.validate_requests(requests,plan)
    return plan


def grading_plan(worker, ready, grading_id, config_path, state_path, assignments_path,
                 source_manifest, bundle_dir, *, max_wall_seconds=3600,
                 max_cpu_seconds=14000, max_case_starts=4000000):
    binding(worker,ready)
    scope=grading_id.rsplit('_',1)[1]
    if grading_id not in worker['grading_ids'] or scope not in ('public','private'):
        raise ValueError('frozen finite grading identity')
    config,state,assignments=read(config_path),read(state_path),read(assignments_path)
    if (config['config_sha256'] != state['config_sha256'] or
        receiver.sha({k:v for k,v in config.items() if k != 'config_sha256'}) != config['config_sha256'] or
        config['pins']['receiver'] != worker['receiver_state_sha256'] or
        any(a['scope']!=scope for a in assignments)):
        raise ValueError('source-separated exact grade assignments')
    if scope=='private' and (state['phase']!=3 or state['requests'] or any(r['disposition']=='active' for r in state['rows'])):
        raise ValueError('all-assigned terminal private gate')
    return dict(version='sprint-qualified-batch-grading-v1',grading_id=grading_id,
        scope=scope,contract_sha256=worker['contract_sha256'],files=worker['files'],workers=4,
        study_config_path=str(config_path),study_config_file_sha256=digest(config_path),
        study_config_sha256=config['config_sha256'],state_path=str(state_path),
        state_file_sha256=digest(state_path),state_sha256=receiver.sha(state),
        assignments_path=str(assignments_path),assignments_file_sha256=digest(assignments_path),
        assignments_sha256=receiver.sha(assignments),observer_sha256=config['pins'][scope+'_observer'],
        attestation_path=worker['output_dir']+'/qualification/attestation.json',
        attestation_sha256=ready['attestation_file_sha256'],
        qualification_plan_path=worker['qualification_plan_path'],
        qualification_plan_sha256=worker['qualification_plan_sha256'],
        source_manifest_path=str(source_manifest),source_manifest_sha256=digest(source_manifest),
        bundle_dir=str(bundle_dir),cache_dir=worker['output_dir']+'/grading-cache',
        owner_deadline_iso=worker['owner_deadline_iso'],max_wall_seconds=max_wall_seconds,
        max_cpu_seconds=max_cpu_seconds,max_case_starts=max_case_starts,
        max_retained_bytes=20<<30,max_rss_bytes=8<<30,
        max_input_file_bytes=2<<30,max_output_file_bytes=512<<20)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('kind',choices=('stage','grading'))
    for flag in ('worker','ready','config','state','out'):
        parser.add_argument('--'+flag,type=Path,required=True)
    parser.add_argument('--id',required=True)
    parser.add_argument('--requests',type=Path)
    parser.add_argument('--assignments',type=Path)
    parser.add_argument('--freeze')
    parser.add_argument('--model-lock',type=Path)
    parser.add_argument('--source-manifest',type=Path)
    parser.add_argument('--bundle-dir',type=Path)
    parser.add_argument('--wall',type=int,default=3600)
    parser.add_argument('--cpu',type=int,default=14000)
    parser.add_argument('--cases',type=int,default=4000000)
    args=parser.parse_args()
    worker=read(args.worker);worker['_file_sha256']=digest(args.worker)
    ready=read(args.ready)
    if args.kind=='stage':
        value=stage_plan(worker,ready,args.id,args.config,args.state,args.requests,args.freeze,
            read(args.model_lock) if args.model_lock else None)
    else:
        value=grading_plan(worker,ready,args.id,args.config,args.state,args.assignments,
            args.source_manifest,args.bundle_dir,max_wall_seconds=args.wall,
            max_cpu_seconds=args.cpu,max_case_starts=args.cases)
    with args.out.open('xb') as stream:
        stream.write(receiver.canonical(value)+b'\n')


if __name__=='__main__':
    main()
