"""Pure construction of public-only requests from qualified fixed checkpoints."""
import hashlib,json,random
from experiments.landmark.collect import SYSTEM
from experiments.prompt_choice.status_feedback_v1 import TEXT
PATCH='Review your previous answer against the original task and the public check status. Preserve correct behavior and change only what is needed for the full stated domain. A public pass does not establish correctness elsewhere. Do not hard-code examples. Return one complete solution.'
RETHINK='Re-derive a solution from the original task. Use the public check status as evidence about the previous answer, without assuming its algorithm is correct. Check the full stated domain. Return one complete solution.'
TERMINAL='Return only Python source with the required function and imports, optionally in exactly one code fence. Do not include tests or explanatory prose.'

def build(public,artifacts,statuses):
    requests=[]
    for task in public:
        root=task['task_id'];prompt=task['adapted_public_contract']+'\nRequired signature: '+task['signature']+'\n'+TERMINAL
        for artifact in artifacts[root]:
            code=artifact['code'];kind=artifact['kind'];status=statuses[(root,kind)]
            if status not in TEXT:raise ValueError('unknown public status')
            base=[{'role':'system','content':SYSTEM},{'role':'user','content':prompt}]
            prefix=base+[{'role':'assistant','content':code}]
            for arm in ['PATCH','RETHINK','FRESH']:
                messages=base if arm=='FRESH' else prefix+[{'role':'user','content':TEXT[status]+'\n'+(PATCH if arm=='PATCH' else RETHINK)+'\n'+TERMINAL}]
                requests.append({'root':root,'artifact':kind,'arm':arm,'initial_artifact_sha256':hashlib.sha256(code.encode()).hexdigest(),'public_status':status,'payload':{'messages':messages,'stream':False,'cache_prompt':False,'temperature':.7,'top_p':.95,'top_k':40,'min_p':.05,'max_tokens':1024,'seed':2026092801+len(requests)}})
    random.Random(2026092800).shuffle(requests)
    for i,r in enumerate(requests):r['slot']=i
    return requests
