"""Handwritten full-shape arrays and mocked adapter events; no draws or fits."""
import copy
import io
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'experiments/e0'))
import stop_anchor_journal as journal
from regularization_job import _fingerprint,_digest,_point_record

@pytest.fixture
def bundle(tmp_path):
    plan=json.loads((ROOT/'experiments/e0/stop_anchor_comparison_plan_v1.json').read_text())
    writer=journal.Recorder(tmp_path/'run',plan)
    identity=writer.identities[0]
    n=9200
    task=np.repeat(np.arange(230),40)
    data=dict(task=task,S=np.full((n,3),3,dtype=np.int64),A=np.zeros((n,3),dtype=np.int64),
              B=np.ones((n,3)),Y=np.ones(n),elig=np.zeros((n,3),dtype=bool))
    data['elig'][:,0]=True
    data['B'][:,0]=journal.adapter.sim.make_beh(2.5,.02,gz=0.)[0,3,0]
    folds=journal.adapter.anchored._fold_assignment(task,3,0,np.repeat(np.arange(230)%3,40))
    fold={k:v.tolist() for k,v in folds.items()}
    provenance=dict(source_sha256=writer.sources,dataset=_fingerprint(data),folds={**fold,'sha256':_digest(fold)})
    prepared=dict(event='prepared',identity=identity,provenance=provenance,
        arrays={k:dict(dtype=v.dtype.str,shape=list(v.shape),values=v.tolist()) for k,v in data.items()})
    return writer,identity,prepared,data


def start_prepared(bundle):
    w,i,p,d=bundle
    w.start(i['job']);w.retain(p)
    return w,i,p,d


def variant_events(identity,prepared,variant):
    names=[f'{variant}:{m}' for m in ('plugin','dr')]
    base=dict(identity=identity,variant=variant,dataset_sha256=prepared['provenance']['dataset']['sha256'],
              fold_sha256=prepared['provenance']['folds']['sha256'])
    means=np.ones(230)
    return ({**base,'event':'variant_started','estimator_ids':names},
            {**base,'event':'variant','records':[_point_record(identity,e,means) for e in names],
             'root_means':{m:means.tolist() for m in ('plugin','dr')},'root_labels':prepared['provenance']['folds']['task_labels'],'support':[],'resources':{}})


def test_empty_is_full_plan(bundle):
    w,*_=bundle
    r=journal.reconcile_recording(w.root)
    assert len(r['summary']['slots'])==2304
    assert all(s['status']=='unattempted' for s in r['summary']['slots'])


def test_archive_roundtrip_and_partial_preservation(bundle):
    w,i,p,d=start_prepared(bundle)
    first=list(journal.adapter.anchored.VARIANTS)[0]
    a,b=variant_events(i,p,first);w.retain(a);w.retain(b)
    second=list(journal.adapter.anchored.VARIANTS)[1]
    a,_=variant_events(i,p,second);w.retain(a)
    r=journal.reconcile_recording(w.root)
    states=[s['status'] for s in r['summary']['slots']]
    assert states.count('completed')==2
    assert states.count('attempted')==22
    assert states.count('unattempted')==2280
    with np.load(w.root/'dataset_000.npz',allow_pickle=False) as arrays:
        for key in d: assert np.array_equal(arrays[key],d[key])
    assert r['audit']['job_states'][0]['started']==[first,second]


def test_all_variants_and_complete_job(bundle):
    w,i,p,d=start_prepared(bundle)
    for v in journal.adapter.anchored.VARIANTS:
        for e in variant_events(i,p,v):w.retain(e)
    w.finish(i['job'],{'sampled_datasets':0})
    r=journal.reconcile_recording(w.root)
    assert r['audit']['job_states'][0]['complete']
    assert not r['audit']['recorded_jobs_complete']
    assert sum(s['status']=='completed' for s in r['summary']['slots'])==24


def test_preparation_failure_is_operational_attempt_not_fit(bundle):
    w,i,p,d=bundle;w.start(i['job'])
    rows=[{**i['planned_job'],'estimator':e,'status':'failed','reason':'bad supplied data'} for e in journal.reporting.ESTIMATORS]
    w.retain(dict(event='job_failed',identity=i,provenance={'source_sha256':w.sources},failure_phase='preparation',records=rows))
    w.finish(i['job'],{'backward_fit_attempts':0})
    r=journal.reconcile_recording(w.root)
    assert sum(s['status']=='failed' for s in r['summary']['slots'])==24
    assert r['audit']['job_states'][0]['started']==[]


@pytest.mark.parametrize('fault',['identity','source','fingerprint','folds','object','logger'])
def test_prepared_rejects_fault_before_archive(bundle,fault):
    w,i,p,d=bundle;w.start(i['job']);p=copy.deepcopy(p)
    if fault=='identity':p['identity']['job']['data_seed']='7'
    if fault=='source':p['provenance']['source_sha256']={}
    if fault=='fingerprint':p['arrays']['Y']['values'][0]=0
    if fault=='folds':p['provenance']['folds']['episode_fold_ids'][0]=2
    if fault=='object':p['arrays']['task']['dtype']='O'
    if fault=='logger':
        p['arrays']['B']['values'][0][0]=.9
        x={k:np.asarray(v['values'],dtype=v['dtype']) for k,v in p['arrays'].items()}
        p['provenance']['dataset']=_fingerprint(x)
    with pytest.raises((ValueError,KeyError)):w.retain(p)
    assert not list(w.root.glob('*.npz'))


@pytest.mark.parametrize('fault',['missing_start','duplicate','wrong_pairing','wrong_data','wrong_variant','wrong_mean','wrong_interval'])
def test_terminal_rejects_fault(bundle,fault):
    w,i,p,d=start_prepared(bundle)
    first=list(journal.adapter.anchored.VARIANTS)[0]
    a,b=variant_events(i,p,first)
    if fault!='missing_start':w.retain(a)
    if fault=='duplicate':w.retain(b)
    if fault=='wrong_pairing':b['records'][0]['pairing_id']='bad'
    if fault=='wrong_data':b['dataset_sha256']='bad'
    if fault=='wrong_variant':b['variant']='history_lambda5_recursive'
    if fault=='wrong_mean':b['root_means']['plugin'][0]=0
    if fault=='wrong_interval':b['records'][1]['interval']['se']=.1
    with pytest.raises(ValueError):w.retain(b)


def test_later_failure_and_mutation_cannot_erase_earlier_record(bundle):
    w,i,p,d=start_prepared(bundle)
    a,b=variant_events(i,p,list(journal.adapter.anchored.VARIANTS)[0]);w.retain(a);w.retain(b)
    b['records'][0]['estimate']=99
    r=journal.reconcile_recording(w.root)
    assert r['summary']['slots'][0]['estimate']==1
    with pytest.raises(ValueError):w.finish(i['job'],{})


def test_truncated_final_line_is_retained_and_flagged(bundle):
    w,i,p,d=start_prepared(bundle)
    with (w.root/'events.jsonl').open('ab') as f:f.write(b'{"event":')
    r=journal.reconcile_recording(w.root)
    assert r['audit']['ignored_trailing_bytes']==9
    assert r['summary']['truncated']


def test_archive_byte_corruption_detected(bundle):
    w,i,p,d=start_prepared(bundle)
    with (w.root/'dataset_000.npz').open('ab') as f:f.write(b'x')
    with pytest.raises(ValueError,match='archive bytes'):journal.reconcile_recording(w.root)


def test_output_cap_retains_start_without_claiming_prepared(bundle):
    w,i,p,d=bundle;w.start(i['job']);w.limit=sum(f.stat().st_size for f in w.root.iterdir())+5
    with pytest.raises(journal.OutputCap):w.retain(p)
    assert not list(w.root.glob('*.npz'))
    assert [e['event'] for e in w.events]==['job_started']


def test_connected_fixture_uses_real_callback_and_refuses_sampling(bundle,monkeypatch):
    w,i,p,d=bundle
    def fake(plan,job,*,data,on_event):
        assert data is d
        on_event(p)
        for variant in journal.adapter.anchored.VARIANTS:
            for e in variant_events(i,p,variant):on_event(e)
        return {'resources':{'sampled_datasets':0}}
    monkeypatch.setattr(journal.adapter,'evaluate_job',fake)
    with pytest.raises(ValueError):journal.record_job(w,i['job'],data=None)
    journal.record_job(w,i['job'],data=d)
    assert journal.reconcile_recording(w.root)['audit']['job_states'][0]['complete']


def test_exclusive_no_resume_and_order(bundle):
    w,i,p,d=bundle
    with pytest.raises(FileExistsError):journal.Recorder(w.root,journal.recorder_plan(w))
    with pytest.raises(ValueError):w.start(w.identities[1]['job'])


def test_fixed_byte_ceiling_cannot_be_increased(tmp_path):
    plan=json.loads((ROOT/'experiments/e0/stop_anchor_comparison_plan_v1.json').read_text())
    with pytest.raises(ValueError):journal.Recorder(tmp_path/'run',plan,output_bytes=268435457)


def test_root_mean_label_order_is_bound(bundle):
    w,i,p,d=start_prepared(bundle)
    a,b=variant_events(i,p,list(journal.adapter.anchored.VARIANTS)[0]);w.retain(a)
    b['root_labels']=list(reversed(b['root_labels']))
    with pytest.raises(ValueError,match='root-label'):w.retain(b)


def test_real_adapter_connects_archive_and24_terminal_scores(bundle,monkeypatch):
    w,i,p,d=bundle
    def forbidden(*args,**kwargs):
        raise AssertionError('No synthetic dataset sampling in connected fixture')
    monkeypatch.setattr(journal.adapter.sim,'simulate',forbidden)
    result=journal.record_job(w,i['job'],data=d)
    assert result['resources']['sampler_attempts']==0
    assert result['resources']['backward_fit_attempts']==24
    assert result['resources']['backward_fits_completed']==24
    summary=journal.reconcile_recording(w.root)['summary']
    rows=[s for s in summary['slots'] if s['replicate']==0]
    assert len(rows)==24 and all(s['status']=='completed' for s in rows)
    assert all(s['estimate']==pytest.approx(1.) for s in rows)


def test96_preparation_failures_keep_all2304terminal_slots(bundle):
    w,*_=bundle
    for i in w.identities:
        w.start(i['job'])
        rows=[{**i['planned_job'],'estimator':e,'status':'failed','reason':'handwritten preparation failure'} for e in journal.reporting.ESTIMATORS]
        w.retain(dict(event='job_failed',identity=i,provenance={'source_sha256':w.sources},failure_phase='preparation',records=rows))
        w.finish(i['job'],{'backward_fit_attempts':0})
    r=journal.reconcile_recording(w.root)
    assert r['audit']['recorded_jobs_complete']
    assert not r['audit']['writer_exit_verified']
    assert len(r['summary']['slots'])==2304
    assert all(s['status']=='failed' for s in r['summary']['slots'])
    assert r['summary']['incomplete']


def test_start_rejects_boolean_replicate_before_journal(bundle):
    w,i,p,d=bundle
    invalid={**i['job'],'replicate':False}
    with pytest.raises(ValueError):w.start(invalid)
    assert not (w.root/'events.jsonl').exists()


def test_incremental_state_matches_full_replay_without_rechecking_history(bundle, monkeypatch):
    w,i,p,d=start_prepared(bundle)
    calls=[]
    original=journal._point_record
    def counted(*args,**kwargs):
        calls.append(args[1]);return original(*args,**kwargs)
    monkeypatch.setattr(journal,'_point_record',counted)
    for variant in journal.adapter.anchored.VARIANTS:
        for event in variant_events(i,p,variant):w.retain(event)
    w.finish(i['job'],{})
    assert len(calls)==24  # every point checked once by the writer
    events=[json.loads(line) for line in (w.root/'events.jsonl').read_text().splitlines()]
    records,states=journal._reconcile(events,w.identities,w.sources)
    assert len(calls)==48  # independent full replay still checks every point
    assert w.snapshot_records()==records and w._state[1]==states
    assert w.completed_jobs==1
    assert all(set(e)=={'event','utc','replicate'} for e in w.events)
    detached=w.snapshot_records();detached[0]['estimate']=99
    assert w.snapshot_records()[0]['estimate']==1


def test_invalid_second_row_rolls_back_all_incremental_state(bundle):
    w,i,p,d=start_prepared(bundle)
    a,b=variant_events(i,p,list(journal.adapter.anchored.VARIANTS)[0]);w.retain(a)
    before=copy.deepcopy(w._state)
    raw=(w.root/'events.jsonl').read_bytes()
    bad=copy.deepcopy(b);bad['root_means']['dr'][0]=2
    with pytest.raises(ValueError,match='root means'):w.retain(bad)
    assert w._state==before and (w.root/'events.jsonl').read_bytes()==raw
    w.retain(b)
    assert sum(r['status']=='completed' for r in w.snapshot_records())==2


def test_failed_fsync_does_not_promote_memory_state(bundle,monkeypatch):
    w,i,p,d=bundle
    before=copy.deepcopy(w._state)
    def fail(fd):raise OSError('injected durability failure')
    monkeypatch.setattr(journal.os,'fsync',fail)
    with pytest.raises(OSError,match='durability'):w.start(i['job'])
    assert w._state==before and w.events==[]
    # Bytes may already have reached the file; the writer must not resume/retry.


def test_exclusive_link_transient_bytes_are_reserved(bundle):
    w,*_=bundle
    used=sum(p.stat().st_size for p in w.root.iterdir())
    w.limit=used+15
    with pytest.raises(journal.OutputCap):w._write('probe.bin',b'0123456789')
    assert not (w.root/'probe.bin').exists() and not (w.root/'probe.bin.tmp').exists()
