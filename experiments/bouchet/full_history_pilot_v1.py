"""Finite staged operational pilot. No policy learning or private feedback.

All receiver code runs only through the existing isolated literal comparator.
Stage preparation imports no private case files. Natural initial responses, exact
assistant messages and every subsequent user message remain in the transcript.
"""
import ast
import copy
import hashlib
import random
from experiments.landmark.collect import SYSTEM, digest
from experiments.landmark.grade import extract_code
from experiments.bouchet.checkpoint_requests_v1 import PATCH, RETHINK, TERMINAL
from experiments.prompt_choice.status_feedback_v1 import TEXT

ACTIONS = ('STOP', 'PATCH', 'RETHINK')


def assignments(roots):
    if len(roots) != 9 or len(set(roots)) != 9:
        raise ValueError('fixed nine-root roster required')
    rng = random.Random(2026092812)
    rows = []
    for root in sorted(roots):
        for replicate in range(2):
            rows.append({'trajectory': len(rows), 'root': root,
                         'replicate': replicate,
                         'actions': [rng.choice(ACTIONS) for _ in range(2)],
                         'seeds': [rng.randrange(2**32) for _ in range(3)]})
    return rows


def payload(messages, seed):
    return {'messages': copy.deepcopy(messages), 'stream': False,
            'cache_prompt': False, 'temperature': .7, 'top_p': .95,
            'top_k': 40, 'min_p': .05, 'max_tokens': 1024, 'seed': seed}


def request(row, phase):
    return {'slot': row['trajectory'], 'root': row['root'],
            'artifact': 'natural_history', 'arm': 'RANDOMIZED_SEQUENCE',
            'replicate': row['replicate'],
            'payload': payload(row['messages'], row['seeds'][phase])}


def initialize(public, ledger):
    tasks = {p['task_id']: p for p in public}
    if ledger != assignments(list(tasks)):
        raise ValueError('assignment ledger mismatch')
    rows = []
    for a in ledger:
        p = tasks[a['root']]
        row = copy.deepcopy(a)
        row.update(disposition='active', decisions=[], calls=[], messages=[
            {'role': 'system', 'content': SYSTEM},
            {'role': 'user', 'content': p['adapted_public_contract'] +
             '\nRequired signature: ' + p['signature'] + '\n' + TERMINAL}])
        rows.append(row)
    return {'phase': 0, 'rows': rows, 'requests': [request(r, 0) for r in rows]}


def source(raw):
    code = extract_code(raw)
    if not ast.parse(code).body:
        raise ValueError('empty source')
    return code


def advance(state, receipt, public, evaluate):
    """Process one frozen stage; public evaluator only, no private data argument."""
    if state['phase'] not in (0, 1, 2):
        raise ValueError('phase already terminal')
    phase = state['phase']
    expected = state['requests']
    calls = receipt['calls']
    if len(calls) > len(expected) or receipt['unattempted'] != len(expected)-len(calls):
        raise ValueError('stage accounting')
    for c, q in zip(calls, expected):
        if any(c[k] != q[k] for k in ('slot', 'root', 'artifact', 'arm', 'replicate')) or c['payload_sha256'] != digest(q['payload']):
            raise ValueError('stage assignment mismatch')
    out = copy.deepcopy(state)
    by_slot = {c['slot']: c for c in calls}
    tasks = {p['task_id']: p for p in public}
    out['requests'] = []
    for row in out['rows']:
        if row['disposition'] != 'active':
            continue  # STOP is absorbing; no public recheck or further call.
        call = by_slot.get(row['trajectory'])
        row['calls'].append({'phase': phase, 'record': call})
        if call is None or call['status'] != 'returned':
            row['disposition'] = 'generation_unavailable'
            continue
        raw = call['response']['choices'][0]['message']['content']
        row['messages'].append({'role': 'assistant', 'content': raw})
        row['final_raw'] = raw
        if phase == 2:
            row['disposition'] = 'horizon'
            continue
        task = tasks[row['root']]
        case = task['public_case']
        try:
            code = source(raw)
        except (ValueError, SyntaxError, TypeError):
            status = 'INCOMPLETE'
            audit = {'reason': 'extraction_or_syntax_unavailable'}
        else:
            audit = evaluate(code, task['entry_point'], case['args_literal'],
                             ast.literal_eval(case['expected_literal']))
            status = audit['status']
        if status not in TEXT:
            raise ValueError('invalid public status')
        action = row['actions'][phase]
        row['decisions'].append({'turn': phase+1, 'slate': list(ACTIONS),
                                'selection_probability': 1/3, 'action': action,
                                'public_status': status, 'public_audit': audit,
                                'public_case_sha256': digest(case),
                                'response_sha256': hashlib.sha256(raw.encode()).hexdigest()})
        if action == 'STOP':
            row['disposition'] = 'stopped'
        else:
            row['messages'].append({'role': 'user', 'content': TEXT[status] +
                                    '\n' + (PATCH if action == 'PATCH' else RETHINK) +
                                    '\n' + TERMINAL})
            out['requests'].append(request(row, phase+1))
    out['phase'] = phase+1
    return out
