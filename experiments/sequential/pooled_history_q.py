"""Regularized public-history regression for synthetic learner qualification.

Function approximation replaces exact cell lookup; it does NOT establish overlap
or causal sufficiency of this representation, and is not a text critic. STOP is
fitted using training labels like any other action. Full assigned histories are
retained by the input contract; this fixed feature map is explicitly lossy.
"""
import hashlib
import numpy as np
from experiments.sequential.finite_history_q import validate,key

DIM=128
PENALTY=1.0


def features(history,representation):
    h=key(history)
    if representation not in ('history','last'):raise ValueError('representation')
    symbols=h if representation=='history' else (h[-1],)
    # Position and adjacent-pair tokens preserve more chronology than bag of
    # observations. Collisions/generalization are part of this declared model.
    tokens=[f'position:{i}:symbol:{v}' for i,v in enumerate(symbols)]
    tokens += [f'pair:{i}:{symbols[i]}:{symbols[i+1]}' for i in range(len(symbols)-1)]
    tokens += ['whole:'+','.join(map(str,symbols))]
    x=np.zeros(DIM);x[0]=1
    for token in tokens:
        hsh=hashlib.sha256(token.encode()).digest();j=1+int.from_bytes(hsh[:8],'big')%(DIM-1)
        x[j]+=1 if hsh[8]&1 else -1
    return x


def predict(model,history,turn):
    if type(turn) is not int or not 0<=turn<model['horizon'] or len(history)!=2*turn+1:raise ValueError('turn')
    x=features(history,model['representation'])
    q=np.clip(model['coef'][turn]@x,0.,1.)
    k=history if model['representation']=='history' else (history[-1],)
    return int(np.argmax(q)),k not in model['seen'][turn],{a:float(q[a]) for a in range(3)}


def fit(episodes,horizon,*,representation='history'):
    validate(episodes,horizon)
    model={'horizon':horizon,'representation':representation,'coef':[None]*horizon,'families':frozenset(e['family'] for e in episodes),'support':[],'seen':[set() for _ in range(horizon)]}
    for t in reversed(range(horizon)):
        active=[e for e in episodes if t<len(e['steps'])];xs=[];ys=[];actions=[]
        for e in active:
            s=e['steps'][t];a=s['action'];target=e['outcome']
            model['seen'][t].add(s['history'] if representation=='history' else (s['history'][-1],))
            if a!=0 and t<horizon-1:
                chosen,_,q=predict(model,e['steps'][t+1]['history'],t+1);target=q[chosen]
            xs.append(features(s['history'],representation));ys.append(target);actions.append(a)
        x=np.array(xs);y=np.array(ys);actions=np.array(actions);coef=[];counts=[]
        for a in range(3):
            selected=actions==a;counts.append(int(selected.sum()))
            if not selected.any():raise ValueError('stage action absent: no probability support fabricated')
            xa=x[selected];ya=y[selected];penalty=np.eye(DIM)*PENALTY;penalty[0,0]=0
            coef.append(np.linalg.solve(xa.T@xa+penalty,xa.T@ya))
        model['coef'][t]=np.array(coef);model['support'].append({'turn':t,'action_counts':counts})
    return model


def evaluate_holdout(model,episodes):
    validate(episodes,model['horizon'])
    if model['families'] & {e['family'] for e in episodes}:raise ValueError('training/evaluation family overlap')
    scores=[]
    for e in episodes:
        weight=1.;dr=0.
        for t,s in enumerate(e['steps']):
            chosen,_,q=predict(model,s['history'],t)
            if t==0:dr=q[chosen]
            weight*=float(s['action']==chosen)/s['probabilities'][s['action']]
            if t==len(e['steps'])-1:target=e['outcome']
            else:
                nxt,_,nq=predict(model,e['steps'][t+1]['history'],t+1);target=nq[nxt]
            dr+=weight*(target-q[s['action']])
        scores.append({'episode':e['episode'],'family':e['family'],'ipw':weight*e['outcome'],'dr':dr})
    return scores
