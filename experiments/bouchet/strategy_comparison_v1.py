"""Matched complete strategies on every saved natural start; no private inputs.

Development only: these reused roots cannot validate a learned DTR policy.
Every strategy starts with the identical natural answer and public observation.
"""
import copy
import random
from experiments.landmark.collect import digest
from experiments.bouchet.full_history_pilot_v1 import payload, source
from experiments.bouchet.checkpoint_requests_v1 import PATCH, RETHINK, TERMINAL
from experiments.prompt_choice.status_feedback_v1 import TEXT

POLICIES = ('STOP', 'PATCH2', 'RETHINK2', 'GATED_PATCH', 'GATED_RETHINK',
            'PUBLIC_SWITCH', 'RESAMPLE_SELECT', 'SELF_REFINE_ADAPT', 'REFLEXION_ADAPT')
GATED = ('GATED_PATCH', 'GATED_RETHINK', 'PUBLIC_SWITCH')
REFLECT = ('SELF_REFINE_ADAPT', 'REFLEXION_ADAPT')
CRITIQUE = ('Inspect the previous solution against the original task and public check. '
            'Explain specific possible errors and a concrete correction plan, including '
            'cases the public check does not cover. Do not write the replacement solution. '
            'Do not claim access to hidden tests. Return concise feedback for the next attempt.')


def assignment_table():
    rng = random.Random(2026092820)
    rows = [{'slot': i*len(POLICIES)+j, 'trajectory': i, 'policy': p,
             'seeds': [rng.randrange(2**32), rng.randrange(2**32)]}
            for i in range(18) for j,p in enumerate(POLICIES)]
    return rows


def action(policy, status):
    if status not in TEXT or policy not in POLICIES:
        raise ValueError('unknown policy/status')
    if policy=='STOP' or policy in GATED and status=='PASS':
        return 'STOP'
    if policy in ('PATCH2','GATED_PATCH'):
        return 'PATCH'
    if policy in ('RETHINK2','GATED_RETHINK'):
        return 'RETHINK'
    if policy=='PUBLIC_SWITCH':
        return 'PATCH' if status=='INCOMPLETE' else 'RETHINK'
    return policy


def prompt_request(row, phase):
    policy=row['policy'];a=action(policy,row['public_status'])
    if a=='STOP':
        row['disposition']='stopped'
        return None
    if policy=='RESAMPLE_SELECT':
        messages=copy.deepcopy(row['base_messages'])
    elif policy in REFLECT and phase==0:
        messages=copy.deepcopy(row['history'])+[{'role':'user','content':TEXT[row['public_status']]+'\n'+CRITIQUE}]
    elif policy=='REFLEXION_ADAPT':
        messages=copy.deepcopy(row['base_messages'])+[{'role':'user','content':'Reflection from the previous attempt:\n'+row['reflection']+'\nUse this memory to produce a new solution.\n'+TERMINAL}]
    elif policy=='SELF_REFINE_ADAPT':
        messages=copy.deepcopy(row['history'])+[{'role':'user','content':'Use your feedback above to revise the solution.\n'+TERMINAL}]
    else:
        messages=copy.deepcopy(row['history'])+[{'role':'user','content':TEXT[row['public_status']]+'\n'+(PATCH if a=='PATCH' else RETHINK)+'\n'+TERMINAL}]
    row['pending_messages']=messages
    row['decisions'].append({'phase':phase,'action':a,'public_status':row['public_status']})
    return {'slot':row['slot'],'root':row['root'],'artifact':'matched_natural_start',
            'arm':policy,'replicate':row['replicate'],
            'payload':payload(messages,row['seeds'][phase])}


def schedule(rows,phase):
    requests=[]
    for row in rows:
        if row['disposition']=='active':
            req=prompt_request(row,phase)
            if req:requests.append(req)
    random.Random(2026092821+phase).shuffle(requests)
    return requests


def initialize(initial, ledger):
    if ledger!=assignment_table() or len(initial)!=18:
        raise ValueError('assignment mismatch')
    rows=[]
    for a in ledger:
        b=initial[a['trajectory']]
        if b['trajectory']!=a['trajectory'] or b['public_status'] not in TEXT:
            raise ValueError('initial identity/status')
        # Allowlist prevents prior randomized actions or private results entering state.
        row={**copy.deepcopy(a), 'root':b['root'],'replicate':b['replicate'],
             'base_messages':copy.deepcopy(b['base_messages']),
             'history':copy.deepcopy(b['base_messages'])+[{'role':'assistant','content':b['raw']}],
             'final_raw':b['raw'],'public_status':b['public_status'],
             'candidates':[{'raw':b['raw'],'public_status':b['public_status']}],
             'calls':[],'decisions':[],'disposition':'active'}
        rows.append(row)
    return {'phase':0,'rows':rows,'requests':schedule(rows,0)}


def advance(state, receipt, observe):
    if state['phase'] not in (0,1):raise ValueError('terminal state')
    requests=state['requests'];calls=receipt['calls'];phase=state['phase']
    if len(calls)>len(requests) or receipt['unattempted']!=len(requests)-len(calls):raise ValueError('accounting')
    for c,q in zip(calls,requests):
        if any(c[k]!=q[k] for k in ('slot','root','artifact','arm','replicate')) or c['payload_sha256']!=digest(q['payload']):raise ValueError('assignment mismatch')
    by_slot={c['slot']:c for c in calls};out=copy.deepcopy(state)
    for row in out['rows']:
        if row['disposition']!='active':continue
        c=by_slot.get(row['slot']);row['calls'].append({'phase':phase,'record':c})
        if c is None or c['status']!='returned':
            row['disposition']='generation_unavailable';continue
        raw=c['response']['choices'][0]['message']['content']
        row['history']=row.pop('pending_messages')+[{'role':'assistant','content':raw}]
        if row['policy'] in REFLECT and phase==0:
            row['reflection']=raw  # Critique is not executable solution or free compute.
            continue
        row['final_raw']=raw
        status,audit=observe(row['root'],raw)
        if status not in TEXT:raise ValueError('invalid public observation')
        row['public_status']=status
        row['candidates'].append({'raw':raw,'public_status':status,'public_audit':audit})
        if phase==1:
            if row['policy']=='RESAMPLE_SELECT':
                rank={'PASS':2,'FAIL':1,'INCOMPLETE':0}
                chosen=max(enumerate(row['candidates']),key=lambda iv:(rank[iv[1]['public_status']],-iv[0]))
                row['selected_candidate']=chosen[0];row['final_raw']=chosen[1]['raw']
            row['disposition']='horizon'
    out['phase']=phase+1
    out['requests']=schedule(out['rows'],1) if phase==0 else []
    return out
