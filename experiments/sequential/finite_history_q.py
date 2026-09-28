"""Finite supported-history fitted Q learner; no simulator truth or private features.

Standard backward Q-learning, not a new identification theorem. This exact-cell
implementation is a synthetic qualification component, not a text encoder or
production LLM controller. STOP's endpoint is learned from observed training
STOP outcomes. No structural public-PASS=correctness assumption is made.
"""
from collections import defaultdict
import math

ACTIONS = ('STOP', 'PATCH', 'RETHINK')


def key(history):
    if type(history) is not tuple or not history:
        raise ValueError('nonempty immutable pre-action history required')
    if any(type(x) is not int for x in history):
        raise ValueError('qualification histories contain public integer symbols only')
    return history


def validate(episodes, horizon):
    if type(horizon) is not int or horizon < 1 or not episodes:
        raise ValueError('nonempty data and positive horizon required')
    seen = set()
    for e in episodes:
        if set(e) != {'episode', 'family', 'steps', 'outcome'}:
            raise ValueError('explicit input fields required; no latent features')
        if e['episode'] in seen: raise ValueError('duplicate episode')
        seen.add(e['episode'])
        if type(e['outcome']) not in (int, float) or not math.isfinite(e['outcome']) or not 0 <= e['outcome'] <= 1:
            raise ValueError('complete bounded outcome required; do not drop missing rows')
        if not 1 <= len(e['steps']) <= horizon: raise ValueError('invalid horizon')
        previous = None
        for t, s in enumerate(e['steps']):
            if set(s) != {'history', 'action', 'probabilities'}: raise ValueError('step schema')
            h = key(s['history'])
            if len(h) != 2*t+1: raise ValueError('history chronology')
            if previous and h[:-2] != previous['history']: raise ValueError('history prefix')
            if previous and h[-2] != previous['action']: raise ValueError('action prefix')
            a = s['action']; b = s['probabilities']
            if type(a) is not int or a not in range(3): raise ValueError('action')
            if len(b) != 3 or any(type(v) not in (int,float) or not math.isfinite(v) or v <= 0 for v in b) or abs(sum(b)-1)>1e-12:
                raise ValueError('full supported logging vector required')
            if a == 0 and t != len(e['steps'])-1: raise ValueError('post STOP decision')
            previous = s
        if len(e['steps']) < horizon and e['steps'][-1]['action'] != 0:
            raise ValueError('early failure cannot be encoded as STOP')


def fit(episodes, horizon, *, representation='history'):
    """Unweighted conditional means require randomization given the chosen history.

Compressed representation is an intentionally misspecified comparison when its
last observation omits relevant public history. An unsupported cell is never
invented: deployment falls back to STOP and records the fallback. The experiment
reports its mass; this behavior is not an identification guarantee.
"""
    validate(episodes, horizon)
    if representation not in ('history','last'): raise ValueError('representation')
    model = {'horizon': horizon, 'representation': representation, 'tables': [{} for _ in range(horizon)], 'families': frozenset(e['family'] for e in episodes)}
    for t in reversed(range(horizon)):
        cell = defaultdict(lambda: defaultdict(list))
        for e in episodes:
            if t >= len(e['steps']): continue
            s=e['steps'][t];h=s['history'];a=s['action']
            if a == 0 or t == horizon-1: target=e['outcome']
            else:
                nxt=e['steps'][t+1]['history'];chosen,_,values=predict(model,nxt,t+1)
                # Absent next STOP outcome has no known truth; abstain from this fit.
                if chosen not in values: raise ValueError('no next-stage STOP support; increase frozen development data or report failed fit')
                target=values[chosen]
            k=h if representation=='history' else (h[-1],)
            cell[k][a].append(target)
        model['tables'][t]={h:{a:(sum(v)/len(v),len(v)) for a,v in arms.items()} for h,arms in cell.items()}
    return model


def predict(model, history, turn):
    h=key(history)
    if type(turn) is not int or not 0<=turn<model['horizon'] or len(h)!=2*turn+1: raise ValueError('turn')
    k=h if model['representation']=='history' else (h[-1],)
    cell=model['tables'][turn].get(k,{})
    values={a:v[0] for a,v in cell.items()}
    if set(values)!=set(range(3)): return 0,True,values
    # Deterministic STOP-first tie rule, fixed before any qualification run.
    return max(range(3),key=lambda a:(values[a],-a)),False,values


def evaluate_holdout(model, episodes):
    """Known-propensity IPW and longitudinal augmented scores for a fixed policy.

These are classical scores; weights use all actual selection probabilities.
Requires disjoint training families, complete outcomes and declared sequential
randomization/consistency. No confidence interval or double-robustness claim is
inferred from a passing numerical check. Q support gaps cause explicit refusal.
"""
    validate(episodes,model['horizon'])
    if model['families'] & {e['family'] for e in episodes}: raise ValueError('training/evaluation family overlap')
    out=[]
    for e in episodes:
        weight=1.;dr=0.;fallbacks=0
        for t,s in enumerate(e['steps']):
            chosen,fallback,q=predict(model,s['history'],t);fallbacks+=fallback
            if set(q)!=set(range(3)): raise ValueError('evaluation Q support gap')
            if t==0: dr=q[chosen]
            weight*=float(s['action']==chosen)/s['probabilities'][s['action']]
            last=t==len(e['steps'])-1
            if last: target=e['outcome']
            else:
                a2,_,q2=predict(model,e['steps'][t+1]['history'],t+1)
                if a2 not in q2: raise ValueError('next evaluation Q support gap')
                target=q2[a2]
            dr+=weight*(target-q[s['action']])
        out.append({'episode':e['episode'],'family':e['family'],'ipw':weight*e['outcome'],'dr':dr,'fallbacks':fallbacks})
    return out
