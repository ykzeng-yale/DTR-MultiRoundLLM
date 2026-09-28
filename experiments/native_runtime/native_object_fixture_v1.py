"""Trusted fixed objects only; no benchmark/reference/generated source."""
import json,sys
sys.path.insert(0,'/runtime')
import numpy as np
import scipy
import pandas as pd
import matplotlib
matplotlib.use('Agg')
from matplotlib.figure import Figure
import nltk,sklearn
# Emit observations, not correctness flags. Expected values stay in host plan.
frame=pd.DataFrame({'group':['b','a','b'],'value':[2.,3.,4.]})
grouped=frame.groupby('group')['value'].sum().sort_index()
fig=Figure();ax=fig.subplots();ax.plot([0.,1.,2.],[1.,4.,9.])
line=ax.lines[0]
observed={'array_product':(np.array([[1.,2.],[3.,4.]]) @ np.array([2.,1.])).tolist(),
 'group_labels':grouped.index.tolist(),'group_values':grouped.tolist(),
 'line_x':line.get_xdata().tolist(),'line_y':line.get_ydata().tolist(),
 'versions':{m.__name__:m.__version__ for m in [np,scipy,pd,matplotlib,nltk,sklearn]}}
print(json.dumps(observed,sort_keys=True,allow_nan=False))
