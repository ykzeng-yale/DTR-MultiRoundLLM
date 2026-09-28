"""Frozen strategy stage preparation; never opens private outcome files."""
import argparse,ast,hashlib,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from experiments.bouchet.strategy_comparison_v1 import initialize,advance
from experiments.bouchet.full_history_pilot_v1 import source
from experiments.prompt_choice.literal_observation_v1 import evaluate

def main():
    p=argparse.ArgumentParser();p.add_argument('--contract',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--state',type=Path);p.add_argument('--receipt',type=Path);p.add_argument('--stage-plan',type=Path);a=p.parse_args()
    c=json.loads(a.contract.read_bytes())
    for f,h in c['files'].items():
        if f.startswith(c['package']+'/private/'):continue
        if hashlib.sha256(Path(f).read_bytes()).hexdigest()!=h:raise ValueError('contract mismatch '+f)
    if len({bool(a.state),bool(a.receipt),bool(a.stage_plan)})!=1:raise ValueError('stage inputs incomplete')
    a.out.mkdir(exist_ok=False);start=time.monotonic();count=0
    public={r['task_id']:r for r in [json.loads(Path(f).read_bytes()) for f in c['public_paths']]}
    def observe(root,raw):
        nonlocal count
        if count>=144 or time.monotonic()-start>350:raise RuntimeError('public cap')
        try:code=source(raw)
        except (ValueError,SyntaxError,TypeError):return 'INCOMPLETE',{'reason':'extraction_or_syntax_unavailable'}
        task=public[root];case=task['public_case'];audit=evaluate(code,task['entry_point'],case['args_literal'],ast.literal_eval(case['expected_literal']))
        (a.out/f'public-{count}.json').write_text(json.dumps(audit)+'\n');count+=1
        return audit['status'],audit
    if a.state:
        plan=json.loads(a.stage_plan.read_bytes());receipt=json.loads(a.receipt.read_bytes())
        if receipt['config_sha256']!=hashlib.sha256(a.stage_plan.read_bytes()).hexdigest() or plan['state_sha256']!=hashlib.sha256(a.state.read_bytes()).hexdigest():raise ValueError('stage binding')
        if receipt['error'] or not receipt.get('state_unchanged'):raise ValueError('receiver failure: reconcile before continuing')
        state=advance(json.loads(a.state.read_bytes()),receipt,observe)
    else:
        state=initialize(json.loads(Path(c['initial_path']).read_bytes()),json.loads(Path(c['assignments_path']).read_bytes()))
    (a.out/'state.json').write_text(json.dumps(state,indent=2)+'\n');(a.out/'requests.json').write_text(json.dumps(state['requests'],indent=2)+'\n')
    (a.out/'preparation.json').write_text(json.dumps({'phase':state['phase'],'public_case_starts':count,'seconds':time.monotonic()-start,'requests':len(state['requests']),'contract_sha256':hashlib.sha256(a.contract.read_bytes()).hexdigest(),'private_files_opened':False},indent=2)+'\n')
if __name__=='__main__':main()
