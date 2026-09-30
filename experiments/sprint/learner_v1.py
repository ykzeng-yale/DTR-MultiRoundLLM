"""Matched public-text weighted fitted Q: full history versus latest history.

Quality-only classical backward fitted Q, not DR training or cost optimization.
The representation, ridge and weighting are fixed before collection. Both
selectors act on the same receiver transcript; compression changes selector
information only. Completeness/support/family admissibility remain caller gates.
"""
import hashlib
import json
import re

import numpy as np

from experiments.sequential.public_history import public_view, bind_selection
from experiments.sequential.text_history_q import ACTIONS
from experiments.sequential.weighted_text_history_q import _weights, _weight_hash

VERSION = 'sprint-weighted-history-q-v1'
HASH_DIM = 64
DIM = HASH_DIM + 6
PENALTY = 1.0
MODES = ('full', 'compressed')


def validate_episodes(episodes):
    """All assigned, observed operational labels including forced terminals.

    A service failure terminates its assigned continuation without inventing a
    next history. Its prospectively declared retained artifact supplies Y.
    SERVICE_TERMINAL is distinct from STOP; neither missing Y nor omitted rows
    can be repaired by this validator. The caller binds outcomes to source
    artifacts and retains attempt costs in the immutable collection state.
    """
    if type(episodes) is not list or not episodes:
        raise ValueError('nonempty all-assigned episodes required')
    seen=set();versions=set()
    for e in episodes:
        if set(e) != {'episode','family','steps','outcome','termination'} or not isinstance(e['episode'],str) or not e['episode'] or e['episode'] in seen or not isinstance(e['family'],str) or not e['family']:
            raise ValueError('operational episode exact schema/identity')
        seen.add(e['episode'])
        if type(e['outcome']) not in (int,float) or not np.isfinite(e['outcome']) or not 0<=e['outcome']<=1:
            raise ValueError('missing/out-of-range operational terminal label')
        if type(e['steps']) is not list or len(e['steps']) not in (1,2) or e['termination'] not in ('STOP','HORIZON','SERVICE_TERMINAL'):
            raise ValueError('operational termination/stages')
        for turn,step in enumerate(e['steps']):
            if set(step) != {'view','selection','response_status'}:
                raise ValueError('operational step schema')
            v=public_view(step['view']);s=step['selection']
            if len(v['public_observations']) != turn+1 or v['remaining_calls'] != 2-turn or [a['id'] for a in v['slate']] != list(ACTIONS):
                raise ValueError('operational stage/slate drift')
            if s != bind_selection(v,s['probabilities'],s['chosen_id']) or any(p<=0 for p in s['probabilities']):
                raise ValueError('supported actual selection probability')
            versions.add((v['receiver_sha256'],v['generator_sha256'],v['public_observations'][-1]['observer_sha256']))
            if turn:
                old=e['steps'][turn-1];old_view=old['view'];action=old['selection']['chosen_id']
                selected=next(a['text'] for a in old_view['slate'] if a['id']==action)
                if action=='STOP' or old['response_status']!='RETURNED' or v['messages'][:len(old_view['messages'])] != old_view['messages'] or len(v['messages'])!=len(old_view['messages'])+2 or v['messages'][-2]!={'role':'user','content':selected} or v['public_observations'][:-1]!=old_view['public_observations']:
                    raise ValueError('full public prefix/post-STOP drift')
        final=e['steps'][-1];action=final['selection']['chosen_id'];status=final['response_status']
        if e['termination']=='STOP':
            okay=action=='STOP' and status=='STOP'
        elif e['termination']=='HORIZON':
            okay=len(e['steps'])==2 and action!='STOP' and status=='RETURNED'
        elif e['termination']=='SERVICE_TERMINAL':
            okay=action!='STOP' and status=='SERVICE_MISSING'
        else:
            okay=False
        if not okay:raise ValueError('forced terminal is not absorbing STOP or successful continuation')
    if len(versions)!=1:raise ValueError('public receiver/generator/observer drift')
    return versions.pop()


def features(view, mode):
    v = public_view(view)
    if mode not in MODES or not v['public_observations']:
        raise ValueError('fixed representation and public observation required')
    latest = v['public_observations'][-1]
    x = np.zeros(DIM)
    x[:3] = (1, len(v['public_observations']) / 2, v['remaining_calls'] / 2)
    x[3 + ('PASS', 'FAIL', 'INCOMPLETE').index(latest['status'])] = 1
    messages = list(enumerate(v['messages']))
    if mode == 'compressed':
        # Fixed original system/task prefix plus latest receiver answer only.
        # The original prefix has exactly two messages in this new collector.
        messages = messages[:2] + [messages[latest['message_index']]]
    tokens = []
    for i, message in messages:
        words = re.findall(r'[a-z_][a-z_0-9]*|\d+', message['content'].lower())
        tokens.extend(f'{i}:{message["role"]}:w:{word}' for word in words)
        tokens.extend(f'{i}:{message["role"]}:p:{a}:{b}' for a, b in zip(words, words[1:]))
    if mode == 'full':
        tokens.extend(f'observation:{i}:{o["status"]}' for i, o in enumerate(v['public_observations']))
    else:
        tokens.append(f'observation:{len(v["public_observations"])-1}:' + latest['status'])
    for token in tokens:
        h = hashlib.sha256(token.encode()).digest()
        x[6 + int.from_bytes(h[:8], 'big') % HASH_DIM] += 1 if h[8] & 1 else -1
    norm = np.linalg.norm(x[6:])
    if norm:
        x[6:] /= norm
    return x


def predict(model, view, *, turn):
    v = public_view(view)
    if model['version'] != VERSION or turn not in (0, 1) or len(v['public_observations']) != turn + 1:
        raise ValueError('model/stage drift')
    versions = (v['receiver_sha256'], v['generator_sha256'],
                v['public_observations'][-1]['observer_sha256'])
    if tuple(model['versions']) != versions:
        raise ValueError('predictor public source version drift')
    coefficients = np.asarray(model['coefficients'][turn], dtype=float)
    if coefficients.shape != (3, DIM) or not np.isfinite(coefficients).all():
        raise ValueError('unfitted/nonfinite model')
    q = np.clip(coefficients @ features(v, model['mode']), 0, 1)
    return ACTIONS[int(np.argmax(q))], dict(zip(ACTIONS, map(float, q)))


def fit(episodes, sample_weights, *, mode):
    versions = validate_episodes(episodes)
    if mode not in MODES:
        raise ValueError('fixed feature mode')
    raw, normalized, numeric = _weights(episodes, sample_weights)
    model = {'version': VERSION, 'mode': mode, 'versions': list(versions),
             'training_families': sorted({e['family'] for e in episodes}),
             'coefficients': [None, None], 'action_counts': [None, None],
             'specification': {'hash_dimensions': HASH_DIM, 'dimensions': DIM,
                 'ridge': PENALTY, 'tie_order': list(ACTIONS),
                 'objective': 'quality-only backward fitted Q',
                 'compression': 'selector original task + latest answer/status; receiver full history unchanged',
                 'weights': 'one global normalization to sum N; no stage/action renormalization'},
             'sample_weight_metadata': {'episode_count': len(episodes),
                 'input_sha256': _weight_hash(raw), 'normalized_sha256': _weight_hash(normalized),
                 'provenance': 'prospective outcome-independent weights; all-assigned caller reconciliation required'}}
    for turn in (1, 0):
        counts = {a: 0 for a in ACTIONS}
        coefficients = []
        for action in ACTIONS:
            active = [e for e in episodes if len(e['steps']) > turn and
                      e['steps'][turn]['selection']['chosen_id'] == action]
            counts[action] = len(active)
            if not active:
                raise ValueError('absent stage-action support: ' + str((turn, action)))
            xs, ys, ws = [], [], []
            for episode in active:
                target = episode['outcome']
                if turn == 0 and action != 'STOP' and len(episode['steps'])>1:
                    _, values = predict(model, episode['steps'][1]['view'], turn=1)
                    target = max(values.values())
                xs.append(features(episode['steps'][turn]['view'], mode))
                ys.append(target); ws.append(numeric[episode['episode']])
            x, y, w = np.stack(xs), np.asarray(ys), np.asarray(ws)
            penalty = np.eye(DIM) * PENALTY
            penalty[0, 0] = 0
            beta = np.linalg.solve(x.T @ (w[:, None] * x) + penalty, x.T @ (w * y))
            if not np.isfinite(beta).all():
                raise ValueError('nonfinite fitted coefficients')
            coefficients.append(beta.tolist())
        model['coefficients'][turn] = coefficients
        model['action_counts'][turn] = counts
    return model


def artifact_sha256(model):
    return hashlib.sha256(json.dumps(model, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()
