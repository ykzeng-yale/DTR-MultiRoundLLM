#!/usr/bin/env python3
"""Compare plug-in and DR with identical Q fits, folds and target law."""
import argparse,hashlib,json,sys,time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'experiments/e0'))
from simulator import kernel,make_beh,simulate,template_kernel,true_value,UNIF5
from estimators import fit_q,dr_scores,task_clustered
from run_grid import CELLS
NAMES=['base','kappa0','FAIL_latent','FAIL_coarsening','FAIL_positivity']


def matched(d,T,rng):
    n_tasks=len(np.unique(d['task']))
    fold=rng.permutation(np.arange(n_tasks)%3)[d['task']]
    plugin=np.zeros(len(d['Y']));dr=np.zeros(len(d['Y']))
    for k in range(3):
        train=np.flatnonzero(fold!=k);test=fold==k
        Q,fb,V=fit_q(d,T,UNIF5,idx=train)
        plugin[test]=V[test]
        dr[test]=dr_scores(d,T,UNIF5,Q,fb)[test]
    return float(plugin.mean()),task_clustered(d['task'],dr)


def one(args):
    name,seed=args;cfg=CELLS[name];rng=np.random.default_rng(seed)
    d=simulate(cfg['n_tasks'],cfg['runs'],cfg['T'],kernel(cfg['cmult']),make_beh(cfg['kappa'],cfg['floor'],cfg['gz']),rng,
               mislabel=cfg['mislabel'],template_sd=cfg['template_sd'],cmult=cfg['cmult'])
    truth=true_value(template_kernel(cfg['cmult'],d['template_offsets']),UNIF5,cfg['T'])
    plugin,dr=matched(d,cfg['T'],rng)
    return dict(cell=name,seed=seed,truth=truth,plugin=plugin,dr=dr[0],dr_interval=list(dr[2:]),template_offsets=d['template_offsets'])


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    paths=[Path(__file__),ROOT/'experiments/e0/simulator.py',ROOT/'experiments/e0/estimators.py',ROOT/'experiments/e0/run_grid.py']
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    (a.out/'manifest.json').write_text(json.dumps(dict(cells=NAMES,replications_per_cell=80,seed_base=20260921,workers=4,source_hashes=hashes,
        plan='docs/scientific_diagnostic_plan_20260920.md',target='uniform continuation actual replicate template mixture',note='same Q fits and task folds; known behavior; no model calls'),indent=2))
    start=time.perf_counter();args=[(name,20260921+100000*i+j) for i,name in enumerate(NAMES) for j in range(80)]
    with ProcessPoolExecutor(max_workers=4) as ex: rows=list(ex.map(one,args))
    (a.out/'replicates.json').write_text(json.dumps(rows,indent=2));out={}
    for name in NAMES:
        rr=[r for r in rows if r['cell']==name];truth=np.array([r['truth'] for r in rr]);entry={}
        errors={m:np.array([r[m] for r in rr])-truth for m in ['plugin','dr']}
        for m,e in errors.items():entry[m]=dict(bias=float(e.mean()),bias_mcse=float(e.std(ddof=1)/np.sqrt(len(e))),rmse=float(np.sqrt((e**2).mean())))
        diff=errors['dr']**2-errors['plugin']**2;se=float(diff.std(ddof=1)/np.sqrt(len(diff)))
        entry['paired_mse_dr_minus_plugin']=dict(mean=float(diff.mean()),mcse=se,mc_interval95=[float(diff.mean()-1.96*se),float(diff.mean()+1.96*se)])
        entry['dr_coverage']=float(np.mean([r['dr_interval'][0]<=r['truth']<=r['dr_interval'][1] for r in rr]));out[name]=entry
    report=dict(results=out,elapsed_seconds=time.perf_counter()-start,n_replications=len(rows),caveat='Diagnostic comparison of estimators, not evidence of prompt efficacy or universal DR superiority; MC intervals approximate.')
    (a.out/'summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
