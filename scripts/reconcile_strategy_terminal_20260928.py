import json,hashlib,collections
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.audit_literal_panel_20260928 import aggregate
from scripts.grade_strategy_comparison_20260928 import describe
from experiments.bouchet.full_history_pilot_v1 import source
b=Path('work/strategy_terminal_grading_20260928');r=json.loads((b/'summary.json').read_bytes());s=json.loads(Path('work/strategy_phase2_20260928/state.json').read_bytes());assert r['error'] is None and len(r['rows'])==162
files=list(b.glob('*.json'));n=0
for row,state in zip(r['rows'],s['rows']):
 assert all(row[k]==state[k] for k in ('slot','trajectory','policy','root','replicate','disposition'))
 try:
  source(state['final_raw']);extractable=True
 except (ValueError,SyntaxError,TypeError):extractable=False
 private=json.loads((Path('work/nine_root_measurement_v1_20260926/private')/(row['root'].replace('/','_')+'.json')).read_bytes())
 for battery,status in row['batteries'].items():
  fs=list(b.glob(f"{row['slot']}-{battery}-*.json"));n+=len(fs)
  expected={f"{row['slot']}-{battery}-{j}.json" for j in range(len(private['batteries'][battery]['cases']))} if extractable and state['disposition']!='generation_unavailable' else set()
  assert {f.name for f in fs}==expected
  if fs:assert aggregate([json.loads(f.read_bytes())['status'] for f in fs])==status
  else:assert status=='INCOMPLETE'
assert n==r['case_starts'];assert describe(r['rows'])==r['descriptive'];assert sum(x['continuation_calls'] for x in r['rows'])==203
cost={}
for policy in r['descriptive']['counts']:
 rows=[x for x in r['rows'] if x['policy']==policy]
 cost[policy]={k:sum(x[k] for x in rows) for k in ('continuation_calls','continuation_prompt_tokens','continuation_completion_tokens','continuation_seconds','public_checks_including_initial')}
 cost[policy]['initial_prompt_tokens']=sum(x['initial_usage']['prompt_tokens'] for x in rows)
 cost[policy]['initial_completion_tokens']=sum(x['initial_usage']['completion_tokens'] for x in rows)
summary={'classification':'lead raw-case reconciliation, reused development roots only','assigned':162,'raw_cases_reconciled':n,'seconds':r['seconds'],'all_rows_and_batteries_reconciled':True,'descriptive':r['descriptive'],'cost_by_policy':cost,'sha256':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}}
Path('results/strategy_terminal_reconciliation_20260928.json').write_text(json.dumps(summary,indent=2)+'\n');Path('results/strategy_terminal_grading_20260928.json').write_bytes((b/'summary.json').read_bytes());print(json.dumps({k:v for k,v in summary.items() if k!='sha256'},indent=2))
