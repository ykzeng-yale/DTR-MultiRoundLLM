from pathlib import Path
import json,hashlib,collections,ast
p=Path('results/e11_dev_v2_20260922T010959Z')
read=lambda x:json.loads((p/x).read_text())
rows=lambda x:[json.loads(s) for s in (p/x).read_text().splitlines()]
m=read('ARTIFACT_SHA256SUMS.json');checks={f:hashlib.sha256((p/f).read_bytes()).hexdigest()==h for f,h in m['files'].items()};assert all(checks.values())
g=rows('D/grades.jsonl'); calls=rows('A/calls.jsonl')+rows('C/calls.jsonl'); roots=sorted({x['root_id'] for x in g});by={(x['root_id'],x['arm'],x['replicate']):x['outcome'] for x in g}
out={'files_checked':len(checks),'all_checksums_match':True,'calls':len(calls),'prompt_tokens':sum(x['prompt_tokens'] for x in calls),'completion_tokens':sum(x['completion_tokens'] for x in calls),'missing_outputs':sum(x['output'] is None for x in calls),'grades':len(g),'missing_grades':[dict(root=x['root_id'],arm=x['arm'],rep=x['replicate'],reason=x['missing_reason']) for x in g if x['outcome'] is None]}
out['arm_counts']={a:dict(collections.Counter(str(x['outcome']) for x in g if x['arm']==a)) for a in ['STOP','N0','S0','N1','S1','R1']}
out['primary_root_differences']={r:sum(by[r,'S1',i]-by[r,'N1',i] for i in range(2))/2 for r in roots}
out['context_removal_mean']=sum(sum(by[r,'R1',i]-by[r,'N1',i] for i in range(2))/2 for r in roots)/7
out['ledgers']={f:dict(collections.Counter(x['event'] for x in rows(f))) for f in ['B/attempts.jsonl','D/grading_attempts.jsonl']}
from experiments.landmark.grade import extract_code
errs=[]
for x in calls:
 try:code=extract_code(x['output'])
 except ValueError:
  errs.append({'root':x['root_id'],'arm':x.get('arm'),'rep':x.get('replicate'),'error':'ambiguous fences','ast_parse_accepts':False});continue
 try:compile(code,'<candidate>','exec')
 except SyntaxError as e:
  try:ast.parse(code); accepted=True
  except SyntaxError:accepted=False
  errs.append({'root':x['root_id'],'arm':x.get('arm'),'rep':x.get('replicate'),'error':e.msg,'line':e.lineno,'ast_parse_accepts':accepted})
out['static_compile_failures']=errs
out['receiver_status']={phase:read(phase+'/completion.json')['receiver_verification']['status'] for phase in ['A','C']}
out['evidence_class']='saved-record arithmetic and static compilation only; no candidate execution or model calls'
Path('results/e11_lead_reconciliation_20260922.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
