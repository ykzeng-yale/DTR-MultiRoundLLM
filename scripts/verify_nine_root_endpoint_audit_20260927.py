import json,hashlib,os,collections,datetime
from pathlib import Path
root=Path.cwd(); load=lambda p:json.loads(Path(p).read_text()); sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
plan=load('results/nine_root_endpoint_plan_20260926T2359Z.json'); obs_path=Path('results/nine_root_endpoint_observer_20260926T2359Z.json'); obs=load(obs_path)
pred=load('results/nine_root_measurement_predictions_20260926.json'); projection=load('results/nine_root_endpoint_projection_20260926T2359Z.json')
files=obs['files']; actual=set()
for d in [plan['output_directory'],'work/nine_root_endpoint_observer_20260926T2359Z',*obs['new_supervisor_directories']]: actual.update(str(p) for p in Path(d).rglob('*') if p.is_file())
actual.add('results/nine_root_endpoint_projection_20260926T2359Z.json'); assert actual==set(files)
for p,v in files.items(): assert Path(p).stat().st_size==v['bytes'] and sha(p)==v['sha256']
assert sum(v['bytes'] for v in files.values())+obs_path.stat().st_size==obs['all_operational_evidence_bytes']==658962
rows=[json.loads(x) for x in Path(plan['output_directory'],'slots_private.jsonl').read_text().splitlines()]; assert len(rows)==486
predmap={(r['task_id'],r['artifact_kind']):r for r in pred['records']}; counts=collections.Counter(); pids=[]
for i,s in enumerate(plan['slots']):
 a,b,r=rows[3*i:3*i+3]; assert [a['event'],b['event'],r['event']]==['launch_attempt','launch_return','slot']
 assert a['slot_id']==s['slot_id'] and a['launch_number']==b['launch_number']==i+1 and b['returned']=='normal'
 for k,v in s.items(): assert r[k]==v,(i,k)
 assert r['raw_retained'] and r['launched'] and r['outcome'] in [0,1]
 calls=r['private_runner_calls']; assert len(calls)==1; call=calls[0]; raw=call['result']
 assert call['program_sha256']==a['program_sha256'] and raw['pid']==b['payload_pid'] and raw['executed'] and not raw['timed_out']
 assert raw['returncode'] in (0,1) and raw['sandbox_kind']=='seatbelt'
 if s['check']=='public':
  parsed=[json.loads(x) for x in raw['stdout'].splitlines() if x.startswith('{')]; assert len(parsed)==1
  assert parsed[0]['n']==r['public_nonce'] and parsed[0]['status'] in ('pass','wrong_value')
  outcome=int(parsed[0]['status']=='pass')
 else:
  assert '__LANDMARK_GRADER_STARTED__' in raw['stdout']; outcome=int(raw['returncode']==0)
  if outcome: assert '__LANDMARK_PRIVATE_OK__' in raw['stdout']
 assert outcome==r['outcome']==projection['slots'][i]['outcome']
 pr=predmap[(s['task_id'],s['artifact_kind'])]; assert pr['code_sha256']==s['code_sha256']; assert outcome==int(pr['predicted'][s['check']])
 counts[s['check']+'_pass' if outcome else s['check']+'_fail']+=1
 try: os.kill(raw['pid'],0)
 except ProcessLookupError: pids.append(raw['pid'])
 else: raise AssertionError('PID alive or ambiguous')
assert len(set(pids))==162
out={'reviewer':'Codex scientific lead','reviewed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'plan_commit':obs['plan_commit'],'observer_sha256':sha(obs_path),'projection_sha256':sha('results/nine_root_endpoint_projection_20260926T2359Z.json'),'raw_event_counts':dict(collections.Counter(r['event'] for r in rows)),'all_file_hashes_and_inventory_verified':True,'all_slot_identities_and_raw_outcomes_verified':True,'all_162_predictions_confirmed':True,'reported_payload_pids_absent':len(pids),'counts':dict(counts),'external_final_seconds_observed_from_driver_stdout':4.779389750212431,'all_operational_evidence_bytes':658962,'model_calls':0,'scope':'finite reference/control measurement audit; no policy efficacy or eligible family claim'}
p=Path('results/nine_root_endpoint_independent_review_20260927.json');p.open('x').write(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
