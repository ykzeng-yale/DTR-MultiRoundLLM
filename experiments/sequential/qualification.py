"""Known-law, non-oracle STOP qualification. No model calls or benchmark code."""
import random
from collections import defaultdict
from experiments.sequential.finite_history_q import fit,predict,evaluate_holdout

REGIMES=('null','mode_specific','noisy_public')


def transition(z,q,a,regime):
    if a==0:return float(q)
    if regime=='null':return float(q)
    favored=a==1+z
    return (0.88 if favored else .70) if q else (.75 if favored else .20)


def observation(q,regime):
    accuracy=.60 if regime=='noisy_public' else .80
    return accuracy if q else 1-accuracy


def sample(n,seed,regime,prefix):
    rng=random.Random(seed);out=[]
    for i in range(n):
        z=rng.randrange(2);q=int(rng.random()<.55);o=int(rng.random()<observation(q,regime));h=(2*z+o,);steps=[]
        for t in range(2):
            a=rng.randrange(3);steps.append({'history':h,'action':a,'probabilities':(1/3,)*3})
            if a==0:break
            q=int(rng.random()<transition(z,q,a,regime))
            if t==0:h=h+(a,int(rng.random()<observation(q,regime)))
        out.append({'episode':f'{prefix}-{i}','family':f'{prefix}-{i}','steps':steps,'outcome':q})
    return out


def initial(regime):
    for z in (0,1):
        for q in (0,1):
            for o in (0,1):
                p=.5*(.55 if q else .45)*(observation(q,regime) if o else 1-observation(q,regime))
                yield z,q,(2*z+o,),p


def exact_value(policy,regime):
    total=0.;fallback_mass=0.
    for z,q,h,p in initial(regime):
        a,fallback=policy(h,0);fallback_mass+=p*fallback
        if a==0:total+=p*q;continue
        prob=transition(z,q,a,regime)
        for q2 in (0,1):
            for o2 in (0,1):
                w=p*(prob if q2 else 1-prob)*(observation(q2,regime) if o2 else 1-observation(q2,regime))
                b,fb=policy(h+(a,o2),1);fallback_mass+=w*fb
                total+=w*transition(z,q2,b,regime)
    return total,fallback_mass


def public_oracle(regime):
    # Exhaustive Bayes recursion conditioned ONLY on public histories. Hidden
    # q is integrated out by its specified law, never passed to the policy.
    posterior=defaultdict(list)
    for z,q,h,p in initial(regime):
        for a in (1,2):
            prob=transition(z,q,a,regime)
            for q2 in (0,1):
                for o in (0,1):
                    w=p*(prob if q2 else 1-prob)*(observation(q2,regime) if o else 1-observation(q2,regime))
                    posterior[h+(a,o)].append((z,q2,w))
    table={}
    for h,rows in posterior.items():
        den=sum(w for z,q,w in rows)
        values=[sum(w*transition(z,q,a,regime) for z,q,w in rows)/den for a in range(3)]
        table[h]=max(range(3),key=lambda a:(values[a],-a))
    for h in [(i,) for i in range(4)]:
        values=[]
        mass=sum(p for z,q,x,p in initial(regime) if x==h)
        for a in range(3):
            def policy(x,t):return (a if t==0 else table[x]),False
            val=0.
            # Conditional value by zeroing mass from other initial histories.
            for z,q,x,p in initial(regime):
                if x!=h:continue
                if a==0:val+=p*q;continue
                prob=transition(z,q,a,regime)
                for q2 in (0,1):
                    for o in (0,1):
                        w=p*(prob if q2 else 1-prob)*(observation(q2,regime) if o else 1-observation(q2,regime))
                        val+=w*transition(z,q2,table[h+(a,o)],regime)
            values.append(val/mass)
        table[h]=max(range(3),key=lambda a:(values[a],-a))
    return lambda h,t:(table[h],False)


def replicate(n,seed,regime,heldout_n):
    train=sample(n,seed,regime,'train');test=sample(heldout_n,seed+10000000,regime,'test')
    answer={'n':n,'seed':seed,'regime':regime,'variants':{}}
    for rep in ('history','last'):
        try:
            model=fit(train,2,representation=rep)
            policy=lambda h,t:predict(model,h,t)[:2]
            value,fallback=exact_value(policy,regime)
            v={'exact_value':value,'expected_fallback_decisions':fallback,'fit_error':None}
            try:
                scores=evaluate_holdout(model,test)
                v.update(ipw=sum(s['ipw'] for s in scores)/len(scores),dr=sum(s['dr'] for s in scores)/len(scores),score_error=None)
            except ValueError as e:v['score_error']=str(e)
            answer['variants'][rep]=v
        except ValueError as e:answer['variants'][rep]={'fit_error':str(e)}
    return answer
