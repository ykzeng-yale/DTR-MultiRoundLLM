"""Export existing operational pilot decisions, never private labels or fitting.

This adapter is specific to the frozen uniform three-action pilot. It must not be
used to infer probabilities for another collector. Metadata stays outside views.
"""
import copy
import hashlib
from experiments.sequential.public_history import bind_selection, public_view
from experiments.bouchet.full_history_pilot_v1 import assignments, ACTIONS, payload
from experiments.bouchet.checkpoint_requests_v1 import PATCH, RETHINK, TERMINAL
from experiments.prompt_choice.status_feedback_v1 import TEXT
from experiments.landmark.collect import digest


def export(state, ledger, receiver_sha256, generator_sha256, observer_sha256):
    if state['phase'] != 3 or state['requests']:
        raise ValueError('terminal pilot required')
    if ledger != assignments(sorted({r['root'] for r in ledger})):
        raise ValueError('frozen uniform assignment law mismatch')
    if len(state['rows']) != len(ledger):
        raise ValueError('assigned rows missing')
    output = []
    for row, assigned in zip(state['rows'], ledger):
        if any(row[k] != v for k, v in assigned.items()):
            raise ValueError('assignment identity drift')
        expected_decisions = 1 if assigned['actions'][0] == 'STOP' else 2
        expected_stop = 'STOP' in assigned['actions'][:expected_decisions]
        if len(row['decisions']) != expected_decisions or row['disposition'] != ('stopped' if expected_stop else 'horizon') or len(row['calls']) != (expected_decisions if expected_stop else 3):
            raise ValueError('incomplete or misclassified terminal pilot')
        obs = []
        stopped = False
        for j, decision in enumerate(row['decisions']):
            if stopped or j > 1:
                raise ValueError('post-STOP or excess decision')
            idx = 2 + 2*j
            prefix = copy.deepcopy(row['messages'][:idx+1])
            if len(prefix) != idx+1 or [m['role'] for m in prefix] != ['system','user','assistant'] + ['user','assistant']*j:
                raise ValueError('transcript order')
            raw = prefix[-1]['content']
            call = row['calls'][j]
            if call['phase'] != j or call['record']['status'] != 'returned' or call['record']['response']['choices'][0]['message']['content'] != raw:
                raise ValueError('response transcript mismatch')
            if call['record']['payload_sha256'] != digest(payload(prefix[:-1],assigned['seeds'][j])):
                raise ValueError('pre-call prefix mismatch')
            if hashlib.sha256(raw.encode()).hexdigest() != decision['response_sha256']:
                raise ValueError('response digest mismatch')
            if decision['turn'] != j+1 or decision['slate'] != list(ACTIONS) or decision['selection_probability'] != 1/3 or decision['action'] != assigned['actions'][j]:
                raise ValueError('decision law drift')
            status = decision['public_status']
            obs.append({'message_index':idx,'status':status,'observer_sha256':observer_sha256})
            slate = [{'id':'STOP','kind':'STOP','text':'','calls_required':0}]
            slate += [{'id':a,'kind':'PROMPT','text':TEXT[status]+'\n'+t+'\n'+TERMINAL,'calls_required':1} for a,t in [('PATCH',PATCH),('RETHINK',RETHINK)]]
            view = public_view({'messages':prefix,'public_observations':copy.deepcopy(obs),'remaining_calls':2-j,'receiver_sha256':receiver_sha256,'generator_sha256':generator_sha256,'slate':slate})
            action = decision['action']
            selected = bind_selection(view,[1/3]*3,action)
            if action == 'STOP':
                stopped = True
                if row['disposition'] != 'stopped' or len(row['messages']) != idx+1 or len(row['calls']) != j+1:
                    raise ValueError('STOP not absorbing')
            elif len(row['messages']) <= idx+1 or row['messages'][idx+1] != {'role':'user','content':slate[list(ACTIONS).index(action)]['text']}:
                raise ValueError('selected prompt drift')
            output.append({'metadata':{'trajectory':row['trajectory'],'root':row['root'],'replicate':row['replicate'],'turn':j+1},'view':view,'selection':selected})
    return output
