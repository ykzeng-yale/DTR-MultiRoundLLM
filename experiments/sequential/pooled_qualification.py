"""Same declared simulator and seeds; changed regression implementation only."""
from experiments.sequential.qualification import sample,exact_value,public_oracle
from experiments.sequential.pooled_history_q import fit,predict,evaluate_holdout

def replicate(n,seed,regime,heldout_n):
    train=sample(n,seed,regime,'train');test=sample(heldout_n,seed+10000000,regime,'test')
    answer={'n':n,'seed':seed,'regime':regime,'variants':{}}
    for representation in ('history','last'):
        try:
            model=fit(train,2,representation=representation)
            value,unseen=exact_value(lambda h,t:predict(model,h,t)[:2],regime)
            scores=evaluate_holdout(model,test)
            answer['variants'][representation]={'fit_error':None,'score_error':None,'exact_value':value,'expected_unseen_history_decisions':unseen,'stage_action_counts':model['support'],'ipw':sum(x['ipw'] for x in scores)/len(scores),'dr':sum(x['dr'] for x in scores)/len(scores)}
        except ValueError as e:answer['variants'][representation]={'fit_error':str(e)}
    return answer
