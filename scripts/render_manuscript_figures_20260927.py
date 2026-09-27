#!/usr/bin/env python3
"""Render saved, reconciled evidence; no model calls, grading or fitted analyses."""
import argparse
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

SOURCE = Path('results/manuscript_clean_checkout_20260927/saved_diagnostics.json')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out-dir', type=Path, required=True)
    a = p.parse_args()
    a.out_dir.mkdir(parents=True, exist_ok=False)
    data = json.loads(SOURCE.read_bytes())
    plt.rcParams.update({'font.size': 10, 'svg.fonttype': 'none', 'axes.spines.top': False,
                         'axes.spines.right': False, 'pdf.fonttype': 42})
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.5), layout='constrained')
    models=['qwen2.5-3b-instruct','qwen2.5-7b-instruct']
    x=np.arange(2)
    for j,(key,label,color) in enumerate([('net_repair_gain','Repair','#466c9a'),('bon3_net_gain','Adaptive resampling','#c38330')]):
        vals=[100*data['repair'][m][key] for m in models]
        bars=axes[0].bar(x+(j-.5)*.32,vals,.32,label=label,color=color)
        axes[0].bar_label(bars,fmt='%.2f',padding=3)
    axes[0].set_xticks(x,['3B receiver','7B receiver']);axes[0].set_ylim(0,10)
    axes[0].set_ylabel('Gain over initial answer (percentage points)')
    axes[0].set_title('A. Reused trajectories: 561 tasks')
    axes[0].legend(frameon=False)
    conditions=['base','kappa0','FAIL_latent','FAIL_coarsening','FAIL_positivity']
    x=np.arange(len(conditions))
    for j,(key,label,color) in enumerate([('plugin','Plug-in','#466c9a'),('dr','DR','#c38330')]):
        vals=[data['matched_estimators'][c][key]['rmse'] for c in conditions]
        axes[1].bar(x+(j-.5)*.36, vals,.36,label=label,color=color)
    axes[1].set_xticks(x,['Base','κ = 0','Latent\nconfounding','Coarsened\nhistory','Weak\noverlap'])
    axes[1].set_ylabel('Monte Carlo RMSE (value units)')
    axes[1].set_title('B. Synthetic matched fits: 80 pairs per condition')
    axes[1].legend(frameon=False)
    paths=[]
    for suffix in ['pdf','svg','png']:
        path=a.out_dir/('audited_evidence.'+suffix)
        fig.savefig(path,dpi=180,metadata={'Creator':'DTR-MultiRoundLLM saved-evidence renderer'})
        paths.append(path)
    plt.close(fig)
    receipt={'source':str(SOURCE),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
             'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             'matplotlib':matplotlib.__version__, 'numpy':np.__version__,
             'outputs':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
             'scope':'Saved-record visualization only; no new fits or model outcomes. Panel A is not exactly cost matched; panel B is synthetic, not receiver efficacy.'}
    (a.out_dir/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__=='__main__':main()
