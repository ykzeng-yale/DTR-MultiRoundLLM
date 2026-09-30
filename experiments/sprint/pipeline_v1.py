"""Three-stage finite stdio development and direct-strategy collector logic.

Pure preparation/reconciliation. Receiver requests contain original public text
and public status feedback only; graders are explicit supervisor callbacks and
never executed by this module. Every assignment survives STOP/service failures.
No source admission, job release, broad-family transport or efficacy is implied.
"""
import copy
import hashlib
import json
import math
import random
import re
import secrets
import time
from fractions import Fraction

from experiments.bouchet.full_history_pilot_v1 import payload
from experiments.bouchet.checkpoint_requests_v1 import PATCH, RETHINK
from experiments.prompt_choice.status_feedback_v1 import TEXT
from experiments.sequential.public_history import bind_selection, public_view
from experiments.sequential.text_history_q import ACTIONS
from experiments.sprint import learner_v1

VERSION = 'sprint-stdio-three-stage-v1'
EXTRACTOR = 'single-python-fence-or-raw-utf8-v1'
SYSTEM = 'You are a Python programming assistant. Solve the original task accurately.'
TERMINAL = 'Return only a complete standalone Python 3 program reading standard input and writing standard output. Do not include commentary.'
POLICIES = ('STOP', 'PATCH2', 'RETHINK2', 'PASS_GATED_PATCH', 'PASS_GATED_RETHINK',
            'RESAMPLE_SELECT', 'FULL_HISTORY_Q', 'COMPRESSED_HISTORY_Q',
            'SELF_REFINE_ADAPT', 'REFLEXION_ADAPT', 'B1_LOCKED')
B1 = ('STOP', 'PATCH2', 'RETHINK2', 'PASS_GATED_PATCH', 'PASS_GATED_RETHINK')
CRITIQUE = ('Inspect the prior program against the original task and public status. '
            'Give a concise specific correction plan. Do not write replacement code '
            'and do not claim access to private tests.')


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def text_sha(text):
    if type(text) is not str:
        raise ValueError('UTF-8 text required')
    return hashlib.sha256(text.encode('utf-8', errors='strict')).hexdigest()


def extract_program(raw):
    """Pinned deterministic extraction; never guess among multiple blocks."""
    text_sha(raw)
    if '```' not in raw:
        return raw
    blocks = list(re.finditer(r'```([^\n]*)\n(.*?)```', raw, flags=re.S))
    if len(blocks) != 1 or raw.count('```') != 2:
        raise ValueError('multiple/unclosed code fences')
    if blocks[0].group(1).strip().lower() not in ('', 'python', 'python3', 'py'):
        raise ValueError('non-Python code fence')
    return blocks[0].group(2)


def base_messages(task):
    return [{'role': 'system', 'content': SYSTEM},
            {'role': 'user', 'content': task['prompt'] + '\n\n' + TERMINAL}]


def _seed(nonce, root, strategy, phase):
    return int(sha([nonce, root, strategy, phase])[:8], 16)


def randomization_roster(tasks,mode,repeats):
    names={'train':'development','tune':'tuning','eval':'evaluation',
           'development':'development','tuning':'tuning','evaluation':'evaluation'}
    selected=sorted((t for t in tasks if names[t['split']]==mode),key=lambda t:t['root'])
    units=[{'family_id':family,'replicate':rep} for family in sorted({t['family_id'] for t in selected}) for rep in range(repeats)]
    actions=[{'root':t['root'],'replicate':rep} for t in selected for rep in range(repeats)] if mode=='development' else []
    return units,actions


def sample_randomization(tasks,*,mode,repeats):
    """Production: sample ONCE after non-RNG protocol freeze, before outcomes.

    OS CSPRNG independent-uniform sampling is an assumption. Each component x
    replicate nonce drives all roots/arms within that whole vector; arbitrary
    within-vector dependence is permitted. Action coins are independent of
    receiver nonces and uniform by rejection sampling. Realized table/seeds and
    their hashes are excluded from F for prospective randomization inference;
    publishing them binds provenance without conditioning away randomization.
    Tests supply explicit deterministic fixtures and never call this function.
    """
    units,actions=randomization_roster(tasks,mode,repeats)
    return {'version':'sprint-independent-vector-randomization-v1','mode':mode,
            'component_replicate_nonces':[dict(u,nonce_hex=secrets.token_hex(16)) for u in units],
            'development_action_coins':[dict(a,actions=[ACTIONS[secrets.randbelow(3)] for _ in range(2)]) for a in actions]}


def validate_randomization(table,tasks,mode,repeats):
    units,coins=randomization_roster(tasks,mode,repeats)
    if type(table) is not dict or set(table)!={'version','mode','component_replicate_nonces','development_action_coins'} or table['version']!='sprint-independent-vector-randomization-v1' or table['mode']!=mode:
        raise ValueError('external independently sampled vector table required')
    if len(table['component_replicate_nonces'])!=len(units) or len(table['development_action_coins'])!=len(coins):
        raise ValueError('all vector nonces/action assignments required')
    nonces={};actions={}
    for expected,record in zip(units,table['component_replicate_nonces']):
        if set(record)!={'family_id','replicate','nonce_hex'} or any(record[k]!=expected[k] for k in expected) or type(record['nonce_hex']) is not str or len(record['nonce_hex'])!=32 or any(c not in '0123456789abcdef' for c in record['nonce_hex']):
            raise ValueError('vector nonce identity/type')
        nonces[(record['family_id'],record['replicate'])]=record['nonce_hex']
    for expected,record in zip(coins,table['development_action_coins']):
        if set(record)!={'root','replicate','actions'} or any(record[k]!=expected[k] for k in expected) or type(record['actions']) is not list or len(record['actions'])!=2 or any(a not in ACTIONS for a in record['actions']):
            raise ValueError('development independent uniform coin identities')
        actions[(record['root'],record['replicate'])]=record['actions']
    return nonces,actions


def make_config(tasks, *, mode, repeats, seed, pins, strategies=None,
                model_sha256s=None, selected_b1=None, choice_lock_sha256=None,randomization=None):
    """Bind an outcome-blind externally adjudicated roster; selects no roots."""
    split = mode if mode in ('development','tuning','evaluation') else None
    split_names={'train':'development','tune':'tuning','eval':'evaluation',
                 'development':'development','tuning':'tuning','evaluation':'evaluation'}
    if not split or type(repeats) is not int or repeats < 1 or type(seed) is not int:
        raise ValueError('mode/repeats/seed')
    if not isinstance(tasks, list) or not tasks:
        raise ValueError('frozen public tasks required')
    basic={'root','family_id','root_source_sha256','prompt','public_instrument','split'}
    bundle=basic|{'replicates','component_root_count','root_weight','episode_weight'}
    for task in tasks:
        if set(task) not in (basic,bundle):
            raise ValueError('public task exact schema; no private fields')
        if any(type(task[k]) is not str or not task[k] for k in ('root','family_id','root_source_sha256','prompt','split')):
            raise ValueError('task field type')
        instrument=task['public_instrument']
        if type(instrument) is dict:
            if set(instrument)!={'bundle_path','root','scope','normalization','sealed_reference'} or instrument['root']!=task['root'] or instrument['scope']!='public' or type(instrument['sealed_reference']) is not dict or any(k in instrument['sealed_reference'] for k in ('stdin','expected_stdout','cases')):
                raise ValueError('public instrument only sealed data reference')
        elif type(instrument) is not str or not instrument:
            raise ValueError('public instrument reference')
        if task['split'] not in split_names:
            raise ValueError('source split')
        _digest(task['root_source_sha256'])
    if len({t['root'] for t in tasks}) != len(tasks):
        raise ValueError('duplicate source roots')
    family_splits = {}
    for task in tasks:
        if task['family_id'] in family_splits and family_splits[task['family_id']] != split_names[task['split']]:
            raise ValueError('family crosses train/tune/evaluation')
        family_splits[task['family_id']] = split_names[task['split']]
    for task in tasks:
        if set(task)==bundle:
            count=sum(t['family_id']==task['family_id'] for t in tasks)
            families=len({t['family_id'] for t in tasks if split_names[t['split']]==split_names[task['split']]})
            if type(task['replicates']) is not int or task['replicates']<1 or task['component_root_count']!=count:
                raise ValueError('source assignment replicate/component size')
            for key,expected in (('root_weight',Fraction(1,families*count)),
                                 ('episode_weight',Fraction(1,families*count*task['replicates']))):
                value=task[key]
                if type(value) is not dict or set(value)!={'numerator','denominator'} or any(type(v) is not int for v in value.values()) or value['denominator']<=0 or Fraction(value['numerator'],value['denominator'])!=expected:
                    raise ValueError('prospective source family/root/replicate weight drift')
            if split_names[task['split']]==split and task['replicates']!=repeats:
                raise ValueError('selected source replicate plan drift')
    required = {'receiver', 'generator', 'public_observer', 'private_observer', 'source_roster', 'extractor'}
    if set(pins) != required:
        raise ValueError('all source/runtime pins required')
    for value in pins.values(): _digest(value)
    strategies = ['RANDOMIZED'] if mode == 'development' else list(strategies or ())
    if mode == 'development' and strategies != ['RANDOMIZED']:
        raise ValueError('uniform development only')
    if mode != 'development' and (not strategies or len(set(strategies)) != len(strategies) or set(strategies)-set(POLICIES)):
        raise ValueError('fixed complete strategy roster')
    model_sha256s = dict(model_sha256s or {})
    learned = set(strategies) & {'FULL_HISTORY_Q','COMPRESSED_HISTORY_Q'}
    if set(model_sha256s) != learned:
        raise ValueError('exact frozen learned artifact digests required')
    for value in model_sha256s.values(): _digest(value)
    if 'B1_LOCKED' in strategies:
        if selected_b1 not in B1:
            raise ValueError('tuning-locked B1 required')
        _digest(choice_lock_sha256)
    elif selected_b1 is not None or choice_lock_sha256 is not None:
        raise ValueError('unrequested comparator choice metadata')
    selected = sorted((t for t in tasks if split_names[t['split']] == split), key=lambda t: t['root'])
    if not selected:
        raise ValueError('no assigned roots')
    nonces,action_coins=validate_randomization(randomization,tasks,mode,repeats)
    ledger, initials = [], []
    for task in selected:
        for replicate in range(repeats):
            initial_id = 'initial-' + sha([mode, task['root'], replicate, seed])
            nonce=nonces[(task['family_id'],replicate)]
            initials.append({'initial_execution_id': initial_id, 'root': task['root'],
                             'family_id': task['family_id'], 'replicate': replicate,
                             'seed': _seed(nonce,task['root'],'INITIAL',0)})
            for strategy in strategies:
                identity = 'assignment-' + sha([mode, task['root'], replicate, seed, strategy])
                ledger.append({'assignment_id': identity, 'initial_execution_id': initial_id,
                    'root': task['root'], 'family_id': task['family_id'], 'replicate': replicate,
                    'strategy': strategy, 'actions': copy.deepcopy(action_coins[(task['root'],replicate)]) if strategy == 'RANDOMIZED' else None,
                    'seeds': [_seed(nonce,task['root'],strategy,phase) for phase in (1, 2)]})
    max_calls=len(initials)+sum(0 if r['strategy']=='STOP' or r['strategy']=='B1_LOCKED' and selected_b1=='STOP' else 2 for r in ledger)
    config = {'version': VERSION, 'mode': mode, 'split': split, 'repeats': repeats,
              'seed': seed, 'pins': copy.deepcopy(pins), 'strategies': strategies,
              'randomization':copy.deepcopy(randomization),'randomization_sha256':sha(randomization),
              'randomization_conditioning':'F excludes realized randomization table/seeds/hashes; independent CSPRNG sampling and stable noninterfering receiver law assumed',
              'source_tasks_sha256': sha(tasks), 'public_prefix_sha256': {t['root']: sha(base_messages(t)) for t in selected},
              'model_sha256s':model_sha256s,'selected_b1':selected_b1,'choice_lock_sha256':choice_lock_sha256,
              'inference':{'method':'finite-family-census-execution-v1','alpha':[1,20],
                           'useful_gain':[1,20],'primary_baseline_ids':['B1_LOCKED','RESAMPLE_SELECT']},
              'initials': initials, 'ledger': ledger, 'extractor': EXTRACTOR,
              'fallback': 'last-returned-artifact; completed malformed output remains observed zero', 'probabilities': [1/3]*3,
              'max_receiver_calls': max_calls,
              'max_completion_tokens': 1024*max_calls}
    config['config_sha256'] = sha(config)
    return config


def _digest(value):
    if type(value) is not str or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('SHA256 required')


def validate_config(config, tasks):
    expected = make_config(tasks, mode=config['mode'], repeats=config['repeats'], seed=config['seed'],
                           pins=config['pins'], strategies=config['strategies'],
                           model_sha256s=config['model_sha256s'],selected_b1=config['selected_b1'],
                           choice_lock_sha256=config['choice_lock_sha256'],randomization=config['randomization'])
    if config != expected:
        raise ValueError('frozen config/assignment/source drift')


def _request(execution_id, grading_unit_id, root, strategy, replicate, messages, seed, phase, slot):
    return {'slot': slot, 'execution_id': execution_id, 'grading_unit_id':grading_unit_id, 'root': root,
            'artifact': 'sprint-stdio-v1', 'arm': strategy, 'replicate': replicate,
            'phase': phase, 'payload': payload(messages, seed)}


def initialize(config, tasks, *, models=None):
    validate_config(config, tasks)
    tasks_by_root = {t['root']: t for t in tasks}
    models = copy.deepcopy(models or {})
    for strategy, mode in (('FULL_HISTORY_Q', 'full'), ('COMPRESSED_HISTORY_Q', 'compressed')):
        if strategy in config['strategies']:
            model = models.get(strategy)
            if not model or model['mode'] != mode:
                raise ValueError('locked learned artifact required')
            if learner_v1.artifact_sha256(model) != config['model_sha256s'][strategy]:
                raise ValueError('learned policy artifact drift')
            if set(model['training_families']) & {r['family_id'] for r in config['ledger']}:
                raise ValueError('learner training/evaluation family overlap')
    rows = []
    for assignment in config['ledger']:
        base = base_messages(tasks_by_root[assignment['root']])
        rows.append(dict(copy.deepcopy(assignment), base_messages=base, messages=copy.deepcopy(base),
                         observations=[], decisions=[], calls=[], candidates=[], disposition='active',
                         initial_raw=None, final_raw=None, final_program=None, initial_public=None,
                         fallback_applied=False, failure_reason=None))
    requests = [_request(i['initial_execution_id'], i['initial_execution_id'], i['root'], 'INITIAL', i['replicate'],
                         base_messages(tasks_by_root[i['root']]), i['seed'], 0, slot)
                for slot, i in enumerate(config['initials'])]
    return {'version': VERSION, 'config_sha256': config['config_sha256'], 'phase': 0,
            'rows': rows, 'requests': requests, 'models': models, 'initial_calls': []}


def primitive_id(scope,unit_id,root,program_sha256,instrument_sha256):
    return sha([scope,unit_id,root,program_sha256,instrument_sha256])


def _public(unit_id,root, raw, observe,instrument_sha256):
    try:
        program = extract_program(raw)
    except ValueError as exc:
        return None, {'status': 'FAIL', 'reason': str(exc), 'elapsed_seconds': 0,
                      'case_starts': 0,'primitive_id':primitive_id('public',unit_id,root,text_sha(raw),instrument_sha256),
                      'audit_sha256': sha({'extractor': EXTRACTOR, 'raw_sha256': text_sha(raw), 'reason': str(exc)})}
    observation = observe(unit_id,root, program)
    if set(observation) - {'status', 'reason', 'elapsed_seconds', 'case_starts', 'audit_sha256','primitive_id'} or observation['status'] not in TEXT:
        raise ValueError('sanitized public observer schema')
    if observation['primitive_id']!=primitive_id('public',unit_id,root,text_sha(program),instrument_sha256):
        raise ValueError('public observation unit/root/program/instrument identity drift')
    _digest(observation['audit_sha256'])
    if not math.isfinite(observation['elapsed_seconds']) or observation['elapsed_seconds'] < 0:
        raise ValueError('public check cost')
    if type(observation['case_starts']) is not int or observation['case_starts'] < 0:
        raise ValueError('public case starts')
    return program, copy.deepcopy(observation)


def _view(row, config, turn):
    status = row['observations'][-1]['status']
    slate = [{'id': 'STOP', 'kind': 'STOP', 'text': '', 'calls_required': 0}]
    for action, text in (('PATCH', PATCH), ('RETHINK', RETHINK)):
        slate.append({'id': action, 'kind': 'PROMPT', 'calls_required': 1,
                      'text': TEXT[status] + '\n' + text + '\n' + TERMINAL})
    return public_view({'messages': row['messages'], 'public_observations': row['observations'],
                        'remaining_calls': 2-turn, 'receiver_sha256': config['pins']['receiver'],
                        'generator_sha256': config['pins']['generator'], 'slate': slate})


def _schedule(state, config):
    turn = state['phase']-1
    if turn == 2:
        state['requests'] = []
        return
    requests = []
    for row in state['rows']:
        if row['disposition'] != 'active': continue
        strategy = config['selected_b1'] if row['strategy']=='B1_LOCKED' else row['strategy']
        status = row['observations'][-1]['status']
        selector_start=time.perf_counter()
        view = _view(row, config, turn)
        if strategy == 'RANDOMIZED':
            action = row['actions'][turn]
            selection = bind_selection(view, config['probabilities'], action)
        elif strategy in ('FULL_HISTORY_Q', 'COMPRESSED_HISTORY_Q'):
            action, values = learner_v1.predict(state['models'][strategy], view, turn=turn)
            selection = {'chosen_id': action, 'values': values, 'model_sha256': learner_v1.artifact_sha256(state['models'][strategy])}
        else:
            action = 'STOP' if strategy == 'STOP' or strategy.startswith('PASS_GATED_') and status == 'PASS' else (
                'PATCH' if strategy in ('PATCH2', 'PASS_GATED_PATCH') else 'RETHINK' if strategy in ('RETHINK2', 'PASS_GATED_RETHINK') else strategy)
            selection = {'chosen_id': action}
        row['decisions'].append({'view': view, 'selection': selection, 'turn': turn,
                                 'selector_wall_seconds':time.perf_counter()-selector_start,
                                 'response_status': 'STOP' if action == 'STOP' else 'PENDING', 'response_sha256': None})
        if action == 'STOP':
            row['disposition'] = 'STOP'; continue
        if strategy == 'RESAMPLE_SELECT':
            messages = copy.deepcopy(row['base_messages'])
        elif strategy in ('SELF_REFINE_ADAPT', 'REFLEXION_ADAPT') and turn == 0:
            messages = copy.deepcopy(row['messages']) + [{'role': 'user', 'content': TEXT[status]+'\n'+CRITIQUE}]
        elif strategy == 'REFLEXION_ADAPT':
            messages = copy.deepcopy(row['base_messages']) + [{'role': 'user', 'content': 'Reflection from prior attempt:\n'+row['reflection']+'\n'+TERMINAL}]
        elif strategy == 'SELF_REFINE_ADAPT':
            messages = copy.deepcopy(row['messages']) + [{'role': 'user', 'content': 'Use your critique above to revise the program.\n'+TERMINAL}]
        else:
            prompt = next(a['text'] for a in view['slate'] if a['id'] == action)
            messages = copy.deepcopy(row['messages']) + [{'role': 'user', 'content': prompt}]
        row['pending_messages'] = messages
        requests.append(_request(row['assignment_id']+f':{state["phase"]}', row['initial_execution_id'], row['root'], row['strategy'],
                                 row['replicate'], messages, row['seeds'][turn], state['phase'], 0))
    # Outcome-blind materialized order avoids always running one arm first.
    requests.sort(key=lambda q: sha([config['seed'], q['execution_id']]))
    for slot, request in enumerate(requests): request['slot'] = slot
    state['requests'] = requests


def advance(state, receipt, config, tasks, observe):
    """Consume immutable model data and only public checks; no private argument."""
    validate_config(config, tasks)
    if state['config_sha256'] != config['config_sha256'] or state['phase'] not in (0, 1, 2):
        raise ValueError('state/config/stage drift')
    frozen = {r['assignment_id']:r for r in config['ledger']}
    if len(state['rows']) != len(frozen) or {r['assignment_id'] for r in state['rows']} != set(frozen):
        raise ValueError('all assigned state rows required')
    for row in state['rows']:
        if any(row[k] != frozen[row['assignment_id']][k] for k in frozen[row['assignment_id']]):
            raise ValueError('frozen branch assignment drift')
        if sha(row['base_messages']) != config['public_prefix_sha256'][row['root']]:
            raise ValueError('original source prefix drift')
    for sid, expected_sha in config['model_sha256s'].items():
        if learner_v1.artifact_sha256(state['models'][sid]) != expected_sha:
            raise ValueError('locked policy state artifact drift')
    requests = state['requests']; calls = receipt['calls']
    if len(calls) > len(requests) or receipt['unattempted'] != len(requests)-len(calls):
        raise ValueError('all assigned stage accounting')
    expected = {q['execution_id']: q for q in requests}; mapped = {}
    for call in calls:
        q = expected.get(call['execution_id'])
        if q is None or call['execution_id'] in mapped or any(call[k] != q[k] for k in ('slot','root','artifact','arm','replicate','phase','grading_unit_id')) or call['payload_sha256'] != sha(q['payload']):
            raise ValueError('receiver response assignment/payload mismatch')
        mapped[q['execution_id']] = call
    if any(c['status'] == 'returned' for c in calls) and receipt.get('state_unchanged') is not True:
        raise ValueError('receiver drift: preserve failed stage; no continuation')
    out = copy.deepcopy(state); phase = state['phase']
    public_initial = {}
    if phase == 0:
        out['initial_calls'] = copy.deepcopy(calls)
    for row in out['rows']:
        if row['disposition'] != 'active': continue
        eid = row['initial_execution_id'] if phase == 0 else row['assignment_id']+f':{phase}'
        call = mapped.get(eid)
        row['calls'].append({'phase': phase, 'record': copy.deepcopy(call), 'execution_id': eid})
        if call is None or call['status'] != 'returned':
            row['disposition'] = 'UNATTEMPTED' if call is None else 'SERVICE_MISSING'
            row['failure_reason'] = 'unattempted' if call is None else str(call.get('error', 'receiver failure'))
            if phase:
                row['decisions'][-1]['response_status'] = 'UNATTEMPTED' if call is None else 'SERVICE_MISSING'
                # Keep the most recent completed program artifact rather than
                # choosing the earlier artifact by its observed quality.
                row['fallback_applied'] = row['final_raw'] is not None
                kind=call.get('failure_kind') if call is not None else 'unattempted_administrative'
                row['disposition'] = 'SERVICE_TERMINAL' if call is not None and kind=='isolated_service_failure' else 'RESOURCE_TERMINAL'
                row['censoring_reason']=None if row['disposition']=='SERVICE_TERMINAL' else kind
            continue
        response = call['response']; raw = response['choices'][0]['message']['content']; text_sha(raw)
        usage = response['usage']
        if type(usage.get('completion_tokens')) is not int or not 0 <= usage['completion_tokens'] <= 1024 or type(usage.get('prompt_tokens')) is not int or not 0 <= usage['prompt_tokens'] <= 7168:
            raise ValueError('receiver context/token accounting')
        row['messages'] = (row['base_messages'] if phase == 0 else row.pop('pending_messages')) + [{'role': 'assistant', 'content': raw}]
        if phase and row['strategy'] == 'RESAMPLE_SELECT':
            # Resampling deliberately resets receiver context. Earlier public
            # grades stay in candidates/audits for selection, not in this new
            # answer's reset transcript chronology.
            row['observations'] = []
        if phase:
            row['decisions'][-1].update(response_status='RETURNED', response_sha256=text_sha(raw))
        if phase == 1 and row['strategy'] in ('SELF_REFINE_ADAPT', 'REFLEXION_ADAPT'):
            row['reflection'] = raw
            # Critique is not a program and receives no execution/check.
            continue
        row['final_raw'] = raw
        if phase == 0:
            row['initial_raw'] = raw
        must_check = phase < 2 or row['strategy'] == 'RESAMPLE_SELECT'
        if must_check:
            if phase == 0 and eid in public_initial:
                program, audit = public_initial[eid]
            else:
                program, audit = _public(row['initial_execution_id'],row['root'], raw, observe,config['pins']['public_observer'])
                if phase == 0: public_initial[eid] = (program, audit)
            row['observations'].append({'message_index': len(row['messages'])-1,
                'status': audit['status'], 'observer_sha256': config['pins']['public_observer']})
            if any(old['primitive_id']==audit['primitive_id'] and old!=audit for old in row.get('public_audits',[])):
                raise ValueError('inconsistent reused public primitive audit')
            row.setdefault('public_audits', []).append(audit)
            row['candidates'].append({'raw': raw, 'program': program, 'status': audit['status'],
                                      'raw_sha256': text_sha(raw), 'program_sha256': text_sha(program) if program is not None else None})
        else:
            try: program = extract_program(raw)
            except ValueError: program = None
        row['final_program'] = program
        if phase == 0:
            row['initial_program'] = program; row['initial_public'] = row['observations'][-1]['status']
        if phase == 2:
            if row['strategy'] == 'RESAMPLE_SELECT':
                rank = {'PASS': 2, 'FAIL': 1, 'INCOMPLETE': 0}
                chosen = max(range(len(row['candidates'])), key=lambda i: (rank[row['candidates'][i]['status']], -i))
                row['selected_candidate'] = chosen
                row['final_raw'] = row['candidates'][chosen]['raw']; row['final_program'] = row['candidates'][chosen]['program']
            row['disposition'] = 'HORIZON'
    out['phase'] = phase+1
    if phase == 1:
        # Critique rows keep initial public status but the decision view must
        # still refer to a public-observed program, not the unexecuted critique.
        for row in out['rows']:
            if row['disposition'] == 'active' and row['strategy'] in ('SELF_REFINE_ADAPT','REFLEXION_ADAPT'):
                row['critique_history'] = copy.deepcopy(row['messages'])
                row['messages'] = copy.deepcopy(row['decisions'][0]['view']['messages'])
    _schedule(out, config)
    if phase == 1:
        for row in out['rows']:
            if 'critique_history' in row:
                if row['strategy'] == 'SELF_REFINE_ADAPT' and row['disposition'] == 'active':
                    row['pending_messages'] = row.pop('critique_history') + [{'role':'user','content':'Use your critique above to revise the program.\n'+TERMINAL}]
                    q = next(q for q in out['requests'] if q['execution_id'] == row['assignment_id']+':2')
                    q['payload'] = payload(row['pending_messages'], row['seeds'][1])
                else:
                    row.pop('critique_history')
    return out


def terminal_label_join(state, config, tasks, private_grade):
    """Open sealed labels only after ALL trajectories terminate; no policy input."""
    validate_config(config, tasks)
    if state['phase'] != 3 or state['requests'] or any(r['disposition']=='active' for r in state['rows']):
        raise ValueError('private grade before all assigned trajectories terminal')
    if {r['assignment_id'] for r in state['rows']} != {r['assignment_id'] for r in config['ledger']} or len(state['rows']) != len(config['ledger']):
        raise ValueError('terminal assignment loss')
    labels = [];cache={}
    for row in state['rows']:
        raw = row['final_raw']; program = row['final_program']
        if raw is None:
            grade = {'status':'UNAVAILABLE','value':None,'reason':'missing_or_unextractable_program','audit_sha256':None,'primitive_id':None,'elapsed_seconds':0,'case_starts':0}
        elif program is None:
            # Prospectively declared finite operational artifact endpoint:
            # completed malformed output is observed failure, never a fallback
            # chosen after looking at its quality.
            grade = {'status':'OBSERVED','value':0,'reason':None,
                     'primitive_id':primitive_id('private',row['initial_execution_id'],row['root'],text_sha(raw),config['pins']['private_observer']),
                     'audit_sha256':sha({'extractor':EXTRACTOR,'raw_sha256':text_sha(raw),'disposition':'malformed_artifact_fail_zero'}),
                     'elapsed_seconds':0,'case_starts':0}
        else:
            key=(row['initial_execution_id'],row['root'],text_sha(program),config['pins']['private_observer'])
            if key not in cache:cache[key]=private_grade(row['initial_execution_id'],row['root'], program)
            grade=cache[key]
            if grade['status'] not in ('OBSERVED','UNAVAILABLE') or set(grade) != {'status','value','reason','audit_sha256','primitive_id','elapsed_seconds','case_starts'}:
                raise ValueError('sanitized private grade schema')
            if grade['primitive_id']!=primitive_id('private',*key):
                raise ValueError('private grade vector/root/program/instrument identity drift')
            if grade['status'] == 'OBSERVED' and (grade['value'] not in (0,1) or grade['reason'] is not None):
                raise ValueError('binary conjunction endpoint')
            if grade['status'] == 'UNAVAILABLE' and (grade['value'] is not None or not grade['reason']):
                raise ValueError('private missingness reason')
            _digest(grade['audit_sha256'])
        labels.append({'assignment_id':row['assignment_id'],'grading_unit_id':row['initial_execution_id'],'root':row['root'],'family_id':row['family_id'],
                       'config_sha256':config['config_sha256'],'raw_sha256':text_sha(raw) if raw is not None else None,
                       'program_sha256':text_sha(program) if program is not None else None,'extractor':EXTRACTOR,
                       'instrument_sha256':config['pins']['private_observer'],
                       'administrative_censoring_reason':row.get('censoring_reason') if row['disposition']=='RESOURCE_TERMINAL' else None,
                       'grade':copy.deepcopy(grade)})
    return {'version':VERSION,'config_sha256':config['config_sha256'],'state_sha256':sha(state),'labels':labels}


def fit_models(state, joined, config, tasks):
    if config['mode'] != 'development' or joined['config_sha256'] != config['config_sha256'] or joined['state_sha256'] != sha(state):
        raise ValueError('development label/state binding')
    validate_config(config, tasks)
    expected = {r['assignment_id']:r for r in state['rows']}
    labels = {r['assignment_id']:r for r in joined['labels']}
    if set(labels) != set(expected) or len(joined['labels']) != len(expected):
        raise ValueError('all assigned development labels required')
    episodes = []
    for identity, row in expected.items():
        label = labels[identity]
        if any(label[k]!=row[k] for k in ('root','family_id')) or label['grading_unit_id']!=row['initial_execution_id'] or label['config_sha256']!=config['config_sha256'] or label['instrument_sha256']!=config['pins']['private_observer'] or label['extractor']!=EXTRACTOR:
            raise ValueError('development source/grade/vector binding')
        if row['disposition'] not in ('STOP','HORIZON','SERVICE_TERMINAL') or label['grade']['status'] != 'OBSERVED':
            raise ValueError('any incomplete assignment aborts fit; no complete-case selection')
        if label['raw_sha256'] != text_sha(row['final_raw']) or label['program_sha256'] != (text_sha(row['final_program']) if row['final_program'] is not None else None):
            raise ValueError('terminal label/artifact drift')
        episodes.append({'episode':identity,'family':row['family_id'],
                         'steps':[{'view':d['view'],'selection':d['selection'],'response_status':d['response_status']} for d in row['decisions']],
                         'outcome':label['grade']['value'],'termination':row['disposition']})
    learner_v1.validate_episodes(episodes)
    roots = {}
    for row in state['rows']: roots.setdefault(row['family_id'],set()).add(row['root'])
    weights = {r['assignment_id']:Fraction(1,len(roots)*len(roots[r['family_id']])*config['repeats']) for r in state['rows']}
    models = {sid:learner_v1.fit(episodes,weights,mode=mode) for sid,mode in
              (('FULL_HISTORY_Q','full'),('COMPRESSED_HISTORY_Q','compressed'))}
    return {'version':VERSION,'config_sha256':config['config_sha256'],'label_join_sha256':sha(joined),
            'models':models,'model_sha256s':{k:learner_v1.artifact_sha256(v) for k,v in models.items()}}


def select_b1(state, joined, config):
    """Development-locked baseline choice on tune labels, fixed earliest tie."""
    if config['mode'] != 'tuning' or config['strategies'] != list(B1) or joined['state_sha256'] != sha(state) or joined['config_sha256'] != config['config_sha256'] or state['config_sha256']!=config['config_sha256'] or state['phase']!=3 or state['requests'] or sha({k:v for k,v in config.items() if k!='config_sha256'})!=config['config_sha256']:
        raise ValueError('complete frozen tuning comparator ledger required')
    ledger={r['assignment_id']:r for r in config['ledger']}
    rows={r['assignment_id']:r for r in state['rows']}
    labels = {r['assignment_id']:r for r in joined['labels']}
    if len(rows)!=len(state['rows']) or len(labels)!=len(joined['labels']) or set(rows)!=set(ledger) or set(labels)!=set(ledger):
        raise ValueError('all tuning assignments required')
    roots = {}
    for r in state['rows']: roots.setdefault(r['family_id'],set()).add(r['root'])
    bounds = {s:[Fraction(0),Fraction(0)] for s in B1}
    for row in state['rows']:
        label=labels[row['assignment_id']];grade=label['grade']
        if any(row.get(k)!=v for k,v in ledger[row['assignment_id']].items()) or any(label[k]!=row[k] for k in ('root','family_id')) or label['grading_unit_id']!=row['initial_execution_id'] or label['config_sha256']!=config['config_sha256'] or label['instrument_sha256']!=config['pins']['private_observer'] or label['extractor']!=EXTRACTOR:
            raise ValueError('tuning source/grade/vector binding')
        if row['disposition'] not in ('STOP','HORIZON','SERVICE_TERMINAL') or grade['status']!='OBSERVED':
            raise ValueError('any incomplete tuning policy aborts choice; no administrative fallback selection')
        raw_sha=text_sha(row['final_raw']);program_sha=text_sha(row['final_program']) if row['final_program'] is not None else None
        if label['raw_sha256']!=raw_sha or label['program_sha256']!=program_sha or grade['primitive_id']!=primitive_id('private',row['initial_execution_id'],row['root'],program_sha or raw_sha,config['pins']['private_observer']) or type(grade['value']) is not int or grade['value'] not in (0,1) or grade['reason'] is not None:
            raise ValueError('tuning terminal label/artifact drift')
        _digest(grade['audit_sha256'])
        weight = Fraction(1,len(roots)*len(roots[row['family_id']])*config['repeats'])
        lo,hi = (grade['value'],grade['value']) if grade['status']=='OBSERVED' else (0,1)
        bounds[row['strategy']][0] += weight*lo; bounds[row['strategy']][1] += weight*hi
    if any(lo != hi for lo,hi in bounds.values()):
        raise ValueError('unavailable tuning labels: no conditional winner selection')
    selected = max(B1,key=lambda s:(bounds[s][0],-B1.index(s)))
    return {'version':VERSION,'selected_b1':selected,'config_sha256':config['config_sha256'],
            'label_join_sha256':sha(joined),'equal_family_quality':{s:float(v[0]) for s,v in bounds.items()},
            'tie_order':list(B1),'selection':'tuning-only quality; no efficacy or cost optimality claim'}


def public_assignments(state, receipt):
    """Enumerate distinct public observations needed before advance().

    This extracts text only. The separate qualified grader owns execution and
    immutable observation receipts. Initials are shared; critiques are excluded.
    """
    requests = {q['execution_id']:q for q in state['requests']}
    needed = {}
    for call in receipt['calls']:
        q = requests.get(call['execution_id'])
        if q is None or call['payload_sha256'] != sha(q['payload']):
            raise ValueError('public request binding')
        if call['status'] != 'returned': continue
        if state['phase'] == 1 and q['arm'] in ('SELF_REFINE_ADAPT','REFLEXION_ADAPT'): continue
        if state['phase'] == 2 and q['arm'] != 'RESAMPLE_SELECT': continue
        raw = call['response']['choices'][0]['message']['content']
        try: program = extract_program(raw)
        except ValueError: continue
        h = text_sha(program)
        needed[(q['grading_unit_id'],q['root'],h)] = {'grading_unit_id':q['grading_unit_id'],'root':q['root'],'program':program,'program_sha256':h,
                                 'raw_sha256':text_sha(raw),'scope':'public','extractor':EXTRACTOR}
    return list(needed.values())


def private_assignments(state):
    """Distinct terminal programs only; refuse any pending collection."""
    if state['phase'] != 3 or state['requests'] or any(r['disposition']=='active' for r in state['rows']):
        raise ValueError('private observation before terminal')
    needed = {}
    for row in state['rows']:
        program = row['final_program']
        if program is not None:
            h = text_sha(program)
            needed[(row['initial_execution_id'],row['root'],h)] = {'grading_unit_id':row['initial_execution_id'],'root':row['root'],'program':program,'program_sha256':h,
                                     'scope':'private','extractor':EXTRACTOR}
    return list(needed.values())


def accounting(state):
    """Physical shared starts and logical per-policy deployment separately.

    Tokens, seconds, USD and unknown energy are distinct. Failed attempts with
    absent token usage have unknown totals rather than zero-token success.
    Private grading belongs to separate experimental overhead receipts.
    """
    def cost(records):
        attempted = [c for c in records if c is not None]
        usage = [c.get('response',{}).get('usage',{}) for c in attempted]
        return {'calls':len(attempted),'input_tokens':sum(u['prompt_tokens'] for u in usage) if all(type(u.get('prompt_tokens')) is int for u in usage) else None,
                'completion_tokens':sum(u['completion_tokens'] for u in usage) if all(type(u.get('completion_tokens')) is int for u in usage) else None,
                'elapsed_seconds':sum(c['seconds'] for c in attempted) if all(type(c.get('seconds')) in (int,float) for c in attempted) else None,
                'usd':0,'energy_joules':None}
    physical = {};physical_public={};logical_public={};selection={}
    logical = {}
    for row in state['rows']:
        records = []
        for item in row['calls']:
            record = item['record']
            if record is not None:
                eid = item['execution_id']
                if eid in physical and physical[eid] != record:
                    raise ValueError('shared physical execution drift')
                physical[eid] = record; records.append(record)
        logical[row['assignment_id']] = cost(records)
        policy_public={}
        for audit in row.get('public_audits',[]):
            identity=audit['primitive_id']
            if identity in physical_public and physical_public[identity]!=audit:
                raise ValueError('inconsistent shared public cost/audit receipt')
            physical_public[identity]=audit;policy_public[identity]=audit
        logical_public[row['assignment_id']]={'primitive_ids':sorted(policy_public),
            'elapsed_seconds':sum(a['elapsed_seconds'] for a in policy_public.values()),
            'case_starts':sum(a['case_starts'] for a in policy_public.values())}
        selection[row['assignment_id']]={'wall_seconds':sum(d['selector_wall_seconds'] for d in row['decisions'])
            if all(type(d.get('selector_wall_seconds')) in (int,float) for d in row['decisions']) else None,
            'cpu_seconds':None,'energy_joules':None,'usd':0}
    return {'physical_receiver':cost(list(physical.values())),
            'physical_execution_ids':sorted(physical),'logical_assignments':logical,
            'logical_public_checks':logical_public,'logical_selector':selection,
            'physical_public_checks':{'primitive_ids':sorted(physical_public),
                'elapsed_seconds':sum(a['elapsed_seconds'] for a in physical_public.values()),
                'case_starts':sum(a['case_starts'] for a in physical_public.values())},
            'shared_initial_included_per_logical_deployment':True,
            'receiver_cost_scope':'receiver-only; selector CPU/energy unknown, no complete total-cost benefit claim',
            'private_grading':'separate overhead, never policy input'}


def analyze(state, joined, config, *, baseline_ids=('B1_LOCKED','RESAMPLE_SELECT')):
    """Frozen equal-family/root descriptive contrast and missingness envelopes.

    This prepares balanced family-execution vectors for the lead's separately
    frozen census inference. Repetitions are stochastic executions within the
    fixed source-relative roster, not additional independent task families.
    """
    if config['mode'] != 'evaluation' or joined['config_sha256'] != config['config_sha256'] or joined['state_sha256'] != sha(state):
        raise ValueError('evaluation terminal join binding')
    if sha({k:v for k,v in config.items() if k!='config_sha256'})!=config['config_sha256'] or config['inference']!={'method':'finite-family-census-execution-v1','alpha':[1,20],'useful_gain':[1,20],'primary_baseline_ids':['B1_LOCKED','RESAMPLE_SELECT']} or tuple(baseline_ids)!=('B1_LOCKED','RESAMPLE_SELECT'):
        raise ValueError('frozen primary order/alpha/five-point inference drift')
    private_assignments(state)
    ids = set(config['strategies'])
    if 'FULL_HISTORY_Q' not in ids or set(baseline_ids)-ids or len(baseline_ids)!=2:
        raise ValueError('frozen full-Q and two baselines required')
    expected = {r['assignment_id']:r for r in config['ledger']}
    labels = {r['assignment_id']:r for r in joined['labels']}
    if len(labels)!=len(expected) or len(joined['labels'])!=len(expected) or set(labels)!=set(expected):
        raise ValueError('all assigned evaluation labels required')
    rows = {}; roots = {}
    for row in state['rows']:
        label = labels[row['assignment_id']]
        if any(label[k]!=row[k] for k in ('root','family_id')) or label['raw_sha256'] != (text_sha(row['final_raw']) if row['final_raw'] is not None else None) or label['program_sha256'] != (text_sha(row['final_program']) if row['final_program'] is not None else None):
            raise ValueError('evaluation label/artifact identity drift')
        grade = label['grade']
        intended_terminal=row['disposition'] in ('STOP','HORIZON','SERVICE_TERMINAL')
        bound = [grade['value']]*2 if grade['status']=='OBSERVED' and intended_terminal else [0,1]
        if label['grading_unit_id']!=row['initial_execution_id']:
            raise ValueError('evaluation grading vector identity drift')
        rows[(row['family_id'],row['root'],row['replicate'],row['strategy'])] = (bound,label,intended_terminal)
        roots.setdefault(row['family_id'],set()).add(row['root'])
    envelope = {sid:[Fraction(0),Fraction(0)] for sid in config['strategies']}
    counts = {sid:{'actual_artifact_pass':0,'actual_artifact_fail':0,'actual_artifact_unavailable':0,
                   'intended_policy_unavailable':0,'administratively_censored':0,
                   'stop':0,'horizon':0,'service_missing':0,'fallback':0} for sid in config['strategies']}
    for row in state['rows']:
        sid=row['strategy'];grade=labels[row['assignment_id']]['grade']
        weight=Fraction(1,len(roots)*len(roots[row['family_id']])*config['repeats'])
        bound=rows[(row['family_id'],row['root'],row['replicate'],sid)][0]
        for j in (0,1):envelope[sid][j]+=weight*bound[j]
        counts[sid]['actual_artifact_unavailable' if grade['status']!='OBSERVED' else 'actual_artifact_pass' if grade['value'] else 'actual_artifact_fail']+=1
        counts[sid]['intended_policy_unavailable']+=grade['status']!='OBSERVED' or row['disposition'] not in ('STOP','HORIZON','SERVICE_TERMINAL')
        counts[sid]['administratively_censored']+=row['disposition']=='RESOURCE_TERMINAL'
        for disposition,key in (('STOP','stop'),('HORIZON','horizon'),('SERVICE_TERMINAL','service_missing')):
            counts[sid][key]+=row['disposition']==disposition
        counts[sid]['fallback']+=row['fallback_applied']
    vectors=[]
    contrasts = list(baseline_ids) + (['COMPRESSED_HISTORY_Q'] if 'COMPRESSED_HISTORY_Q' in ids else [])
    aggregate={sid:[Fraction(0),Fraction(0)] for sid in contrasts}
    for family in sorted(roots):
        for replicate in range(config['repeats']):
            bounds={sid:[Fraction(0),Fraction(0)] for sid in contrasts}
            for root in sorted(roots[family]):
                full,full_label,full_terminal=rows[(family,root,replicate,'FULL_HISTORY_Q')]
                for sid in contrasts:
                    other,other_label,other_terminal=rows[(family,root,replicate,sid)]
                    same=(full_terminal and other_terminal and full_label['program_sha256'] is not None and
                          full_label['program_sha256']==other_label['program_sha256'] and
                          full_label['grading_unit_id']==other_label['grading_unit_id'] and
                          full_label['instrument_sha256']==other_label['instrument_sha256'] and
                          full_label['grade']['primitive_id'] is not None and
                          full_label['grade']['primitive_id']==other_label['grade']['primitive_id'])
                    if same and full_label['grade']!=other_label['grade']:
                        raise ValueError('inconsistent shared primitive audit/grade')
                    lo,hi=(0,0) if same else (full[0]-other[1],full[1]-other[0])
                    bounds[sid][0]+=Fraction(lo,len(roots[family]));bounds[sid][1]+=Fraction(hi,len(roots[family]))
            vectors.append({'family_id':family,'replicate':replicate,
                            'contrasts':{sid:[float(v) for v in bounds[sid]] for sid in contrasts}})
            for sid in contrasts:
                for j in (0,1):aggregate[sid][j]+=bounds[sid][j]/(len(roots)*config['repeats'])
    return {'version':VERSION,'config_sha256':config['config_sha256'],'state_sha256':sha(state),
            'label_join_sha256':sha(joined),'assigned':len(expected),'families':len(roots),
            'roots':sum(map(len,roots.values())),'replicates':config['repeats'],
            'strategy_counts':counts,'quality_completion_envelopes':{s:list(map(float,b)) for s,b in envelope.items()},
            'contrast_completion_envelopes':{s:list(map(float,b)) for s,b in aggregate.items()},
            'family_execution_vectors':vectors,'baseline_ids':list(baseline_ids),
            'compressed_secondary':'prespecified descriptive method ablation, no best-arm promotion',
            'costs':accounting(state),'interval_kind':'missingness completion envelopes, not confidence intervals',
            'administrative_censoring':'intended complete-policy quality unknown; actual retained artifact grade reported separately',
            'target':'fixed source-relative family roster; operational publisher battery, no all-input or broad transport claim'}
