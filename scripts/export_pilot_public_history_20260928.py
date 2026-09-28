"""Source-only adapter qualification: no execution, labels, fitting or calls."""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from experiments.sequential.pilot_public_export import export

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest()
contract=json.loads(Path('experiments/bouchet/full_history_contract_v1.json').read_text())
# Read only source files necessary for the renderer and public observer identity.
source=['experiments/bouchet/full_history_pilot_v1.py','experiments/bouchet/checkpoint_requests_v1.py','experiments/prompt_choice/status_feedback_v1.py','experiments/prompt_choice/literal_observation_v1.py']
for f in source:
 if sha(f)!=contract['files'][f]:raise ValueError('frozen source mismatch '+f)
ledger_path=contract['assignments_path']
if sha(ledger_path)!=contract['files'][ledger_path]:raise ValueError('ledger hash')
plan=json.loads(Path('experiments/bouchet/full_history_phase0_plan_v1.json').read_text())
state_path='work/full_history_phase3_20260928/state.json'
ledger=json.loads(Path(ledger_path).read_text())
rows=export(json.loads(Path(state_path).read_text()),ledger,digest({k:plan[k] for k in ['model_sha256','receiver_state_sha256','build_manifest_sha256']}),digest({f:contract['files'][f] for f in source[:3]}),contract['files'][source[3]])
out=Path(sys.argv[1]);out.mkdir(exist_ok=False)
p=out/'decisions.jsonl';p.write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in rows))
summary={'classification':'public-history adapter validation, no learning/efficacy','decisions':len(rows),'trajectories':len({r['metadata']['trajectory'] for r in rows}),'stops':sum(r['selection']['chosen_id']=='STOP' for r in rows),'state_sha256':sha(state_path),'ledger_sha256':sha(ledger_path),'export_sha256':sha(p),'source_sha256':{f:sha(f) for f in source+['experiments/sequential/pilot_public_export.py','experiments/sequential/public_history.py',__file__]},'private_labels_read':False,'policy_fitted':False}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
