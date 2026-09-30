"""Independent bounded reconciliation of saved sprint generation, no execution.

Only explicitly supplied public configuration/state, frozen requests, terminal
summary and immutable start/completion journals are opened. No sealed battery,
private label, model, receiver or generated program is executed or opened.
Integrity is distinct from task quality, actual freshness and statistical
independence. This supporting auditor does not modify or release frozen stages.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import resource
import signal
import sys
import time

VERSION = 'sprint-independent-generation-audit-v1'
RECEIVER_VERSION = 'sprint-cuda-four-slot-receiver-v1'
MODEL_SHA256 = '626b4a6678b86442240e33df819e00132d3ba7dddfe1cdc4fbb18e0a9615c62d'
RECEIVER_SHA256 = '411ebaa409af6e3968161cfba76ddb1e52a04f43a1692d8f3499384d48f36795'
REQUEST_KEYS = {'slot','execution_id','grading_unit_id','root','artifact','arm','replicate','phase','payload'}
PAYLOAD_KEYS = {'messages','stream','cache_prompt','temperature','top_p','top_k','min_p','max_tokens','seed'}
IDENTITY_KEYS = REQUEST_KEYS - {'payload'}
START_KEYS = IDENTITY_KEYS | {'status','payload_sha256','server_index'}
FAILURE_KINDS = {'isolated_service_failure','receiver_lost','administrative_deadline',
                 'receiver_contract_violation','interrupted_inflight_service'}
STAGES = {prefix+str(phase) for prefix in ('dev','tune','eval') for phase in range(3)}
MAX_FILE_BYTES = 1 << 30
MAX_TOTAL_INPUT_BYTES = 2 << 30
MAX_JOURNAL_LINE_BYTES = 512 << 10
MAX_ROWS = 82428
MAX_WALL_SECONDS = 300


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')


def sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def raw_sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None


def integer(value, low=0, high=None):
    return type(value) is int and low <= value and (high is None or value <= high)


def finite_seconds(value):
    return type(value) in (int,float) and math.isfinite(value) and value >= 0


def unique(rows, key, label):
    require(type(rows) is list and len(rows)<=MAX_ROWS,label+' bounded list')
    out={}
    for row in rows:
        require(type(row) is dict and type(row.get(key)) is str and row[key] and row[key] not in out,
                label+' duplicate/missing identity')
        out[row[key]]=row
    return out


def _seed(nonce, root, strategy, phase):
    return int(sha([nonce,root,strategy,phase])[:8],16)


def audit_objects(plan, requests, state, config, summary, journal, started, *,
                  hashes, expected_job_id):
    """Pure metadata/data audit; inputs are parsed saved JSON, never code.

    `hashes` contains raw file hashes, not canonical JSON substitutes. Missing
    terminal tokenizer evidence is disclosed as unauditable, never fabricated.
    All frozen requests receive a sanitized disposition row, including unknown
    attempted costs and unattempted assignments. No action is released here.
    """
    begin=time.monotonic()
    require(set(hashes)=={'stage_plan','requests','state','config','summary','journal','started'},'exact file-hash inputs')
    require(all(digest(v) for k,v in hashes.items() if k not in ('journal','started')),'file SHA256 inputs')
    require(all(v is None or digest(v) for k,v in hashes.items() if k in ('journal','started')),'optional journal file hashes')
    require(type(expected_job_id) is str and re.fullmatch('[0-9]+',expected_job_id),'actual expected job ID')
    stage=plan['stage_id'];require(stage in STAGES,'frozen stage identity')
    phase=int(stage[-1]);mode={'dev':'development','tune':'tuning','eval':'evaluation'}[stage[:-1]]
    require(config['mode']==mode and state['phase']==phase,'stage state/mode order')
    require(sha({k:v for k,v in config.items() if k!='config_sha256'})==config['config_sha256'],'config canonical hash')
    require(config['config_sha256']==state['config_sha256']==plan['study_config_sha256']==summary['study_config_sha256'],'config identity binding')
    require(hashes['config']==plan['study_config_file_sha256'] and hashes['state']==plan['state_sha256']==summary['state_sha256'], 'config/state raw file binding')
    require(hashes['requests']==plan['requests_file_sha256'] and requests==state['requests'] and sha(requests)==plan['requests_canonical_sha256']==summary['requests_sha256'],'exact state/request file/canonical binding')
    require(summary['version']==RECEIVER_VERSION and summary['stage_id']==stage and summary['job_id']==expected_job_id,'actual terminal receiver/stage/job binding')
    require(summary['config_sha256']==hashes['stage_plan'] and summary['freeze']==plan['freeze_commit'],'exact stage-plan/freeze binding')
    require(type(plan['freeze_commit']) is str and re.fullmatch('[0-9a-f]{40}',plan['freeze_commit']),'immutable freeze witness')
    require(plan['model_sha256']==MODEL_SHA256 and plan['receiver_state_sha256']==RECEIVER_SHA256 and config['pins']['receiver']==RECEIVER_SHA256,'receiver/model pinned law')
    require(summary.get('model_lock')==plan.get('model_lock'),'model lock receipt equality')
    require(plan['server_count'] in (1,2) and plan['workers']==4*plan['server_count'],'exact receiver-instance/slot law')
    require(integer(plan['max_calls'],0,MAX_ROWS) and len(requests)==plan['max_calls']<=plan['assignment_cap'],'all finite assigned requests')
    require(plan['max_completion_tokens']==1024*len(requests),'entire completion reservation')
    require(type(summary.get('state_unchanged')) is bool and summary.get('paid_usd')==0 and summary.get('energy_measured') is False,'terminal law/cost accounting fields')
    require(summary.get('error') is None or type(summary['error']) is str,'terminal error preserved')
    require(finite_seconds(summary['elapsed_seconds']),'terminal elapsed time')

    ledger=unique(config['ledger'],'assignment_id','config ledger')
    rows=unique(state['rows'],'assignment_id','all assigned state rows')
    require(set(rows)==set(ledger),'no assigned state row loss')
    initials=unique(config['initials'],'initial_execution_id','frozen initial executions')
    nonce_rows=config['randomization']['component_replicate_nonces']
    require(config['randomization_sha256']==sha(config['randomization']),'randomization table binding')
    nonces={}
    for n in nonce_rows:
        require(set(n)=={'family_id','replicate','nonce_hex'} and re.fullmatch('[0-9a-f]{32}',n['nonce_hex']) and integer(n['replicate']),'nonce schema')
        unit=(n['family_id'],n['replicate']);require(unit not in nonces,'duplicate family/repetition nonce');nonces[unit]=n['nonce_hex']
    for initial in initials.values():
        require(initial['initial_execution_id']=='initial-'+sha([mode,initial['root'],initial['replicate'],config['seed']]),'initial execution identity')
        require(initial['seed']==_seed(nonces[(initial['family_id'],initial['replicate'])],initial['root'],'INITIAL',0),'actual initial seeded assignment')
    for aid,entry in ledger.items():
        row=rows[aid]
        require(all(row.get(k)==v for k,v in entry.items()),'frozen branch assignment drift')
        require(aid=='assignment-'+sha([mode,entry['root'],entry['replicate'],config['seed'],entry['strategy']]),'branch execution identity')
        require(entry['seeds']==[_seed(nonces[(entry['family_id'],entry['replicate'])],entry['root'],entry['strategy'],p) for p in (1,2)],'actual continuation seeded assignment')
        initial=initials[entry['initial_execution_id']]
        require(all(entry[k]==initial[k] for k in ('root','family_id','replicate')),'initial/branch vector membership')
        require(sha(row['base_messages'])==config['public_prefix_sha256'][entry['root']],'unchanged original public prefix')
    for sid,expected in config['model_sha256s'].items():
        model=state['models'][sid];require(sha(model)==expected,'locked fitted artifact hash')
        require(not set(model['training_families']) & {r['family_id'] for r in ledger.values()},'training/stage family overlap')
    if mode=='evaluation':
        lock=plan.get('model_lock');require(type(lock) is dict and set(lock)=={'model_sha256s','selected_b1','choice_lock_sha256','freeze_commit'},'frozen eval model/comparator schema')
        require(lock['model_sha256s']==config['model_sha256s'] and lock['selected_b1']==config['selected_b1'] and lock['choice_lock_sha256']==config['choice_lock_sha256'],'frozen evaluation comparator/learner drift')
        require(re.fullmatch('[0-9a-f]{40}',lock['freeze_commit']) is not None,'earlier model/comparator freeze witness')
    else:require(plan.get('model_lock') is None,'premature evaluation lock')

    assigned=unique(requests,'execution_id','requests');slots=set()
    for q in requests:
        require(set(q)==REQUEST_KEYS and integer(q['slot']) and q['slot'] not in slots and q['phase']==phase,'request identity/slot/phase schema');slots.add(q['slot'])
        require(q['artifact']=='sprint-stdio-v1' and integer(q['replicate']),'supported stdio request identity')
        p=q['payload'];require(type(p) is dict and set(p)==PAYLOAD_KEYS,'exact public payload schema')
        require(p['stream'] is False and p['cache_prompt'] is False and all(p[k]==v for k,v in {'temperature':.7,'top_p':.95,'top_k':40,'min_p':.05,'max_tokens':1024}.items()) and integer(p['seed'],0,2**32-1),'pinned no-cache decoding/seed')
        require(type(p['messages']) is list and bool(p['messages']) and all(type(m) is dict and set(m)=={'role','content'} and m['role'] in ('system','user','assistant') and type(m['content']) is str for m in p['messages']),'public message schema')
        require(len(canonical(p))<=plan['max_payload_bytes'],'frozen payload byte cap')
        if phase==0:
            require(q['execution_id'] in initials,'phase0 initial request identity');i=initials[q['execution_id']]
            require(q['arm']=='INITIAL' and q['grading_unit_id']==q['execution_id'] and all(q[k]==i[k] for k in ('root','replicate')) and p['seed']==i['seed'],'phase0 vector/request binding')
            require(sha(p['messages'])==config['public_prefix_sha256'][q['root']],'phase0 public prefix')
        else:
            aid=q['execution_id'].removesuffix(':'+str(phase));require(q['execution_id']==aid+':'+str(phase) and aid in rows,'continuation branch identity');row=rows[aid]
            require(row['disposition']=='active' and all(q[k]==row[v] for k,v in [('root','root'),('arm','strategy'),('replicate','replicate'),('grading_unit_id','initial_execution_id')]) and p['seed']==row['seeds'][phase-1] and p['messages']==row['pending_messages'],'exact pending continuation request')
    require(slots==set(range(len(requests))),'complete contiguous assigned slots')
    expected_request_ids=(set(initials) if phase==0 else {r['assignment_id']+':'+str(phase) for r in rows.values() if r['disposition']=='active'})
    require(set(assigned)==expected_request_ids,'omitted scheduled initial/continuation request')

    completed=unique(journal,'execution_id','immutable completion journal')
    starts=unique(started,'execution_id','immutable start journal')
    calls=unique(summary['calls'],'execution_id','terminal calls')
    require(set(completed)<=set(starts)<=set(assigned),'completion/start/request identity nesting')
    require(set(calls)==set(starts),'all actual starts accounted at terminal')
    require([c['execution_id'] for c in summary['calls']]==[q['execution_id'] for q in requests if q['execution_id'] in starts],'terminal call ordering')
    require(summary['journal_sha256']==hashes['journal'] and summary['started_sha256']==hashes['started'],'immutable journal hash binding')
    missing=[q['execution_id'] for q in requests if q['execution_id'] not in calls]
    require(summary['unattempted']==len(missing) and summary['unattempted_execution_ids']==missing,'all unattempted assignments preserved')
    checks=unique(summary.get('tokenizer_preflight',[]),'execution_id','tokenizer checks')
    require(set(checks)<=set(assigned),'unassigned tokenizer check')
    if checks:require(set(checks)==set(assigned),'partial tokenizer evidence cannot represent completed global preflight')
    for eid,check in checks.items():
        require(set(check)=={'execution_id','payload_sha256','template_prompt_sha256','tokens','context_tokens','completion_reserved','tokenizer_reserve'},'tokenizer evidence schema')
        require(check['payload_sha256']==sha(assigned[eid]['payload']) and digest(check['template_prompt_sha256']) and integer(check['tokens'],0,7152) and check['context_tokens']==8192 and check['completion_reserved']==1024 and check['tokenizer_reserve']==16,'tokenizer payload/context/reserve fields')
    audit_rows=[];prompt_tokens=completion_tokens=0;unknown_token_calls=unknown_latency_calls=0;failures=Counter();unverified_tokenizer=[];call_seconds=0.0;nonzero_cache=[]
    for q in requests:
        require(time.monotonic()-begin<MAX_WALL_SECONDS,'pure audit global wall cap')
        eid=q['execution_id'];call=calls.get(eid)
        row={k:q[k] for k in IDENTITY_KEYS};row.update(payload_sha256=sha(q['payload']),seed=q['payload']['seed'],server_index=q['payload']['seed']%plan['server_count'],status='unattempted',response_sha256=None,prompt_tokens=None,completion_tokens=None,seconds=None,failure_kind=None)
        if call is None:audit_rows.append(row);continue
        start=starts[eid]
        require(set(start)==START_KEYS and start['status']=='assigned','actual start schema/status')
        require(all(start[k]==q[k] for k in IDENTITY_KEYS) and start['payload_sha256']==sha(q['payload']) and start['server_index']==row['server_index'],'actual seeded route/start identity')
        require(all(call[k]==q[k] for k in IDENTITY_KEYS) and call['payload_sha256']==sha(q['payload']) and call['server_index']==row['server_index'],'actual seeded route/call identity')
        if eid in completed:
            require(call==completed[eid],'terminal record differs from immutable completion journal')
            require(finite_seconds(call.get('seconds')),'completed journal requires actual measured latency')
        else:
            recovered=dict(start,status='failed',seconds=None,error='interrupted started request without completed journal',failure_kind='interrupted_inflight_service')
            require(call==recovered,'interrupted inflight row not exactly recovered from saved start')
        require(call['status'] in ('returned','failed'),'terminal assigned-only status prohibited')
        require(call.get('seconds') is None and call['status']=='failed' or finite_seconds(call.get('seconds')),'actual latency field')
        if call['seconds'] is None:unknown_latency_calls+=1
        else:call_seconds+=call['seconds']
        row.update(status=call['status'],seconds=call['seconds'])
        if call['status']=='returned':
            response=call['response'];choices=response['choices'];usage=response['usage']
            require(type(choices) is list and len(choices)==1 and choices[0].get('finish_reason') in ('stop','length') and type(choices[0].get('message',{}).get('content')) is str,'returned response choice/content')
            content=choices[0]['message']['content'];require(raw_sha(content.encode('utf-8',errors='strict'))==call['raw_response_sha256'],'raw returned response hash')
            require(integer(usage.get('prompt_tokens'),0,7168) and integer(usage.get('completion_tokens'),0,1024),'actual prompt/completion usage bounds')
            require(call['prompt_tokens']==usage['prompt_tokens'] and call['completion_tokens']==usage['completion_tokens'],'receipt/token usage equality')
            require(integer(call['tokenizer_difference'],-16,16),'prospective tokenizer discrepancy bound')
            if eid in checks:require(call['tokenizer_difference']==call['prompt_tokens']-checks[eid]['tokens'],'actual versus tokenizer token equality')
            else:unverified_tokenizer.append(eid)
            if 'total_tokens' in usage:require(usage['total_tokens']==call['prompt_tokens']+call['completion_tokens'],'total token arithmetic')
            cached=usage.get('prompt_tokens_details',{}).get('cached_tokens',0)
            if cached!=0:nonzero_cache.append(eid)
            row.update(response_sha256=call['raw_response_sha256'],prompt_tokens=call['prompt_tokens'],completion_tokens=call['completion_tokens'])
            prompt_tokens+=call['prompt_tokens'];completion_tokens+=call['completion_tokens']
        else:
            require(type(call.get('error')) is str and call.get('failure_kind') in FAILURE_KINDS,'failed assignment reason preserved')
            require(not any(k in call for k in ('raw_response_sha256','prompt_tokens','completion_tokens','tokenizer_difference')),'failed calls must not invent validated token metadata')
            row['failure_kind']=call['failure_kind'];failures[call['failure_kind']]+=1;unknown_token_calls+=1
        audit_rows.append(row)
    require(completion_tokens<=plan['max_completion_tokens'],'returned completion reservation exceeded')
    if any(c['status']=='returned' for c in calls.values()) and summary['state_unchanged'] is not True:
        stable=False
    else:stable=summary['state_unchanged'] is True
    return {'version':VERSION,'classification':'saved generation integrity; not outcome/efficacy or release',
            'stage_id':stage,'job_id':expected_job_id,'freeze':plan['freeze_commit'],'file_sha256s':dict(hashes),
            'study_config_sha256':config['config_sha256'],'state_file_sha256':hashes['state'],
            'assigned':len(requests),'returned':sum(c['status']=='returned' for c in calls.values()),
            'failed':sum(c['status']=='failed' for c in calls.values()),'unattempted':len(missing),
            'completed_journal_rows':len(completed),'started_rows':len(starts),'recovered_interrupted_rows':len(starts)-len(completed),
            'failure_kind_counts':dict(failures),'global_cap_reason':summary.get('global_cap_reason'),
            'terminal_error':summary.get('error'),'receiver_state_unchanged':summary['state_unchanged'],
            'tokenizer_checked':len(checks),'returned_without_saved_tokenizer_evidence':unverified_tokenizer,
            'all_returned_tokenizer_reconciled':not unverified_tokenizer,
            'nonzero_cached_token_execution_ids':nonzero_cache,
            'reported_prompt_tokens_known':prompt_tokens,'reported_completion_tokens_known':completion_tokens,
            'attempted_calls_with_unknown_token_cost':unknown_token_calls,
            'reported_call_wall_seconds_sum':call_seconds,'attempted_calls_with_unknown_latency':unknown_latency_calls,
            'stage_elapsed_seconds':summary['elapsed_seconds'],'paid_usd':0,'energy_measured':False,
            'complete_generation_integrity':not missing and not failures and not summary.get('error') and stable and not unverified_tokenizer and not nonzero_cache,
            'assignment_dispositions':audit_rows,'private_files_read':0,'candidate_executions':0,'model_calls':0,
            'limits':['Recorded route/seed hashes do not prove independent draws or actual noninterference.',
                      'Template prompt/tokenizer tokens are hash-bound metadata; token IDs and rendered template bytes are not retained by the collector.',
                      'Receiver state_unchanged is the frozen worker reported check; no per-stage after-props bytes are retained for independent recomputation.',
                      'Failed/inflight calls retain unknown token costs rather than being charged zero.',
                      'No private grading, task success, policy efficacy, cost benefit or stage release is established.']}


class BoundedReader:
    def __init__(self):self.total=0;self.start=time.monotonic()
    def raw(self,path,cap=MAX_FILE_BYTES):
        path=Path(path);require(path.is_file() and not path.is_symlink(),'explicit regular saved input required')
        require(path.stat().st_size<=cap and self.total+path.stat().st_size<=MAX_TOTAL_INPUT_BYTES,'saved audit input byte envelope')
        with path.open('rb') as stream:raw=stream.read(cap+1)
        self.total+=len(raw);require(len(raw)<=cap and self.total<=MAX_TOTAL_INPUT_BYTES and time.monotonic()-self.start<MAX_WALL_SECONDS,'saved audit byte/wall cap')
        return raw
    def json(self,path):
        raw=self.raw(path);return strict_json(raw),raw_sha(raw)
    def journal(self,path):
        if path is None or not Path(path).exists():return [],None
        raw=self.raw(path);require(raw==b'' or raw.endswith(b'\n'),'immutable journal has incomplete trailing row')
        lines=raw.splitlines();require(len(lines)<=MAX_ROWS and all(len(line)<=MAX_JOURNAL_LINE_BYTES for line in lines),'bounded immutable journal rows')
        return [strict_json(line) for line in lines],raw_sha(raw)


def strict_json(raw):
    def object_pairs(pairs):
        value={}
        for k,v in pairs:
            require(k not in value,'duplicate saved JSON key');value[k]=v
        return value
    def bad_constant(value):raise ValueError('nonfinite saved JSON number '+value)
    return json.loads(raw,object_pairs_hook=object_pairs,parse_constant=bad_constant)


def audit_files(*,stage_plan,requests,state,config,summary,journal,started,job_id,repo_root=None):
    reader=BoundedReader();values={};hashes={}
    for name,path in [('stage_plan',stage_plan),('requests',requests),('state',state),('config',config),('summary',summary)]:
        values[name],hashes[name]=reader.json(path)
    values['journal'],hashes['journal']=reader.journal(journal);values['started'],hashes['started']=reader.journal(started)
    result=audit_objects(values['stage_plan'],values['requests'],values['state'],values['config'],values['summary'],values['journal'],values['started'],hashes=hashes,expected_job_id=job_id)
    source_checked=[]
    if repo_root is not None:
        root=Path(repo_root).resolve()
        for name,want in values['stage_plan']['files'].items():
            relative=Path(name);require(not relative.is_absolute() and '..' not in relative.parts and relative.parts[0] in ('experiments','scripts','results'),'source-only pin path')
            path=root/relative;require(path.resolve().is_relative_to(root),'source pin stays in declared checkout')
            raw=reader.raw(path);require(raw_sha(raw)==want,'frozen source pin drift: '+name);source_checked.append(name)
    result.update(source_pins_verified=len(source_checked),source_pins_checked=source_checked,total_saved_bytes_read=reader.total)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('stage-plan','requests','state','config','summary','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--journal',type=Path);parser.add_argument('--started',type=Path)
    parser.add_argument('--job-id',required=True);parser.add_argument('--repo-root',type=Path)
    args=parser.parse_args()
    def timeout(signum,frame):raise TimeoutError('independent audit global wall cap')
    signal.signal(signal.SIGALRM,timeout);signal.alarm(MAX_WALL_SECONDS)
    resource.setrlimit(resource.RLIMIT_CPU,(240,245))
    resource.setrlimit(resource.RLIMIT_AS,(8<<30,8<<30))
    result=audit_files(stage_plan=args.stage_plan,requests=args.requests,state=args.state,config=args.config,
        summary=args.summary,journal=args.journal,started=args.started,job_id=args.job_id,repo_root=args.repo_root)
    args.out.mkdir(mode=0o700,exist_ok=False)
    (args.out/'reconciliation.json').write_bytes(canonical(result)+b'\n')
    print(json.dumps({k:result[k] for k in ('version','stage_id','job_id','assigned','returned','failed','unattempted','complete_generation_integrity')}))


if __name__=='__main__':main()
