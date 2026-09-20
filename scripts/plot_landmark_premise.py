#!/usr/bin/env python3
"""Plot saved premise summaries; no estimation or model calls."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
s=json.loads(Path('results/landmark_premise_20260920/summary.json').read_text())
cells=['homogeneous_null','qualitative_interaction','weak_interaction','unavailable_signal']
lookup={(v['cell'],v['branch_repetitions']):v for v in s}
values=[[],[],[],[]]
for c in cells:
 r=lookup[c,1];q=lookup[c,4]
 values[0].append(100*r['public_oracle_gain']['mean'])
 values[1].append(100*r['true_policy_gain']['mean'])
 values[2].append(100*(r['public_oracle_gain']['mean']+r['sample_max_excess_over_public_oracle']['mean']))
 values[3].append(100*(q['public_oracle_gain']['mean']+q['sample_max_excess_over_public_oracle']['mean']))
fig,ax=plt.subplots(figsize=(10,5.2),layout='constrained')
x=np.arange(4);width=.19
colors=['#245b78','#58a18b','#cf8553','#dfb59a']
labels=['Public-feature oracle','Learned policy: true value','Best observed branch: 1 draw','Best observed branch: 4 draws']
for j,(v,l,c) in enumerate(zip(values,labels,colors)):
 bars=ax.bar(x+(j-1.5)*width,v,width,color=c,label=l)
 if j>=2:
  for b in bars:b.set_hatch('///');b.set_edgecolor('#fff7ef');b.set_linewidth(.3)
ax.set_xticks(x,['Homogeneous null','Predictable interaction','Weak interaction','Unavailable signal'])
ax.set_ylabel('Gain over training-selected fixed arm (percentage points)')
ax.set_ylim(0,33);ax.spines[['top','right']].set_visible(False)
ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
ax.set_title('Zero average arm effects can hide useful personalization',loc='left',fontweight='bold',pad=18)
ax.legend(loc='upper left',bbox_to_anchor=(0,-.15),ncol=2,frameon=False)
fig.supxlabel('Known-truth simulation. Hatched bars use outcomes to choose an arm and are not deployable policies.',fontsize=9)
fig.savefig('results/landmark_premise_20260920/diagnostic_figure.png',dpi=170)
