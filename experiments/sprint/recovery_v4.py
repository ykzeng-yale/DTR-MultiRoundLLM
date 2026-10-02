"""Immutable successful-prefix recovery; never replay a completed assignment.

The prior worker may have failed administratively after the successful prefix.
That failure is retained, not reclassified as study completion. Fresh node
qualification remains mandatory. No policy fitting or selection occurs here.
"""
import json
from pathlib import Path
from experiments.sprint import receiver_v1 as receiver
from scripts import audit_sprint_generation_v1 as audit

PREFIX=('dev0','dev1','dev2','tune0','tune1','tune2','eval0')
GRADES=('dev0_public','dev1_public','dev2_private','tune0_public','tune1_public','tune2_private','eval0_public')
LIMITS=('contract_sha256','model_sha256','receiver_state_sha256','build_manifest_sha256','max_calls','max_completion_tokens','max_case_starts','max_grading_cpu_seconds','max_retained_bytes','server_count','workers','owner_deadline_iso')


def require(value,message):
    if not value:raise ValueError(message)


def validate_prefix(summary, reports, old, new):
    require(all(old[k]==new[k] for k in LIMITS),'unchanged scientific/global limits')
    require(summary['error']=="RuntimeError('finite wait expired before eval1')",'specific preserved administrative failure only')
    require(tuple(s['stage_id'] for s in summary['stages'])==PREFIX,'exact successful prefix; no partial/reordered extension')
    require(tuple(s['grading_id'] for s in summary['grading'])==GRADES,'exact completed grading prefix')
    require(len(reports)==len(PREFIX),'all prefix stages independently recounted')
    for stage,report in zip(summary['stages'],reports):
        require(stage['error'] is None and stage['failed']==0 and stage['unattempted']==0,'partial/failed generation cannot resume')
        require(report['complete_generation_integrity'] and report['assigned']==report['returned']==stage['returned'],'complete assigned prefix')
    calls=sum(s['returned'] for s in summary['stages'])
    require(calls==summary['assigned_calls_reserved']==19081,'exact cumulative calls')
    require(summary['completion_tokens_reserved']==1024*calls,'cumulative token reservations')
    return calls


def verify_manifest(manifest):
    roots=[Path(p).resolve() for p in manifest['roots']]
    require(len(roots)==len(set(roots)) and len(roots)==5,'five owned prior artifact roots')
    listed=set();total=0
    for item in manifest['files']:
        path=Path(item['path']);resolved=path.resolve()
        require(not path.is_symlink() and path.is_file() and any(resolved.is_relative_to(r) for r in roots),'owned regular prior evidence')
        require(resolved not in listed and path.stat().st_size==item['bytes'] and receiver.file_sha(path)==item['sha256'],'immutable prior hash/bytes')
        listed.add(resolved);total+=item['bytes']
    actual=set()
    for root in roots:
        for p in root.rglob('*'):
            require(not p.is_symlink(),'prior evidence symlink')
            if p.is_file():actual.add(p.resolve())
    require(actual==listed,'complete prior inventory; no omissions')
    return total


def verify(plan, original):
    recovery=plan['successful_prefix_recovery']
    manifest=json.loads(Path(recovery['manifest_path']).read_bytes())
    require(receiver.file_sha(recovery['manifest_path'])==recovery['manifest_sha256'],'bound recovery manifest')
    prior_bytes=verify_manifest(manifest)
    require(prior_bytes==plan['prior_artifact_bytes'],'exact cumulative prior retained bytes')
    old=json.loads(Path(recovery['prior_plan_path']).read_bytes())
    require(receiver.file_sha(recovery['prior_plan_path'])==recovery['prior_plan_sha256'],'original worker plan')
    summary=json.loads(Path(recovery['summary_path']).read_bytes())
    require(receiver.file_sha(recovery['summary_path'])==recovery['summary_sha256'],'terminal failure evidence')
    require(summary['job_id']==recovery['prior_job_id']=='28091783','exact old owned job')
    reports=[];contracts={};lock=None
    require(tuple(e['stage_id'] for e in recovery['stages'])==PREFIX,'exact recovery stage entries')
    for entry in recovery['stages']:
        report=audit.audit_files(**{k:Path(entry[k]) for k in ('stage_plan','requests','state','config','summary','journal','started')},job_id=entry['job_id'],repo_root=Path(entry['repo_root']))
        reports.append(report)
        stage=json.loads(Path(entry['stage_plan']).read_bytes());prefix=entry['stage_id'][:-1]
        require(prefix not in contracts or contracts[prefix]==stage['study_config_sha256'],'no within-study config mutation')
        contracts[prefix]=stage['study_config_sha256']
        if prefix=='eval':lock=stage['model_lock']
    auxiliary=plan['extra_failed_allocation']
    ap=Path(auxiliary['summary_path'])
    require(receiver.file_sha(ap)==auxiliary['summary_sha256'],'latest failed allocation summary hash')
    extra=json.loads(ap.read_bytes())
    require(extra['job_id']==auxiliary['job_id']=='28048309' and extra['error']==summary['error'] and
            extra['stages']==summary['stages'] and extra['grading']==summary['grading'][:6] and
            extra['assigned_calls_reserved']==summary['assigned_calls_reserved'] and
            extra['unentered_stage_ids']==['eval1','eval2'],'latest allocation generated/graded no new task assignments')
    q=plan['qualification_staging_failure']
    qp=Path(q['summary_path']);require(receiver.file_sha(qp)==q['summary_sha256'],'qualification staging failure bound')
    qs=json.loads(qp.read_bytes())
    require(qs['job_id']=='28066929' and qs['stages']==summary['stages'] and qs['grading']==summary['grading'][:6] and qs['assigned_calls_reserved']==19081 and qs['unentered_stage_ids']==['eval1','eval2'] and 'qualify_stdio_sprint_v4.py' in qs['error'],'no task replay during failed qualification')
    calls=validate_prefix(summary,reports,old,plan)
    # Prior grading is not rerun. Reconciliation and primitive cache bytes are
    # bound by complete inventory, and fresh attestation is separately required.
    for record in summary['grading']:
        root=Path(plan['preserved_grading_roots'][record['grading_id']])
        rp=root/'grading-reconciliation'/(record['grading_id']+'.json')
        report=json.loads(rp.read_bytes())
        require(receiver.file_sha(rp)==record['reconciliation_file_sha256'] and receiver.sha(report)==record['reconciliation_sha256'],'prior grade reconciliation hash')
        require(report['safe_to_advance'] and report['status']=='RECONCILED_COMPLETE','prior grading refused')
        batch=root/'grading'/record['grading_id']
        result=json.loads((batch/'summary.json').read_bytes())
        require(receiver.sha(result)==record['result_sha256'],'prior batch summary canonical hash')
        require(receiver.file_sha(batch/'observations.json')==result['observations_file_sha256'] and receiver.sha(json.loads((batch/'observations.json').read_bytes()))==result['observations_sha256'],'prior observations raw/canonical hashes')
    require(prior_bytes+2*(128<<20)+(32<<20)<plan['max_retained_bytes'],'prior+new retained envelope')
    witness={'version':'sprint-successful-prefix-recovery-v1','prior_job_id':recovery['prior_job_id'],'manifest_sha256':recovery['manifest_sha256'],'retained_bytes':prior_bytes,'returned_calls':calls,'owner_extension_receipt_sha256':original['receipt']['owner_extension_receipt_sha256']}
    return {'reserved_calls':calls,'retained_bytes':prior_bytes,'receipt':witness,'stage_contracts':contracts,'stages':summary['stages'],'grading':summary['grading'],'eval_lock':lock,'cache_dir':str(Path(recovery['prior_output_dir'])/'grading-cache')}
