"""Two-decision public-text Q learner, with STOP and family-separated evaluation.

Classical fitted Q and longitudinal DR score. Hashing the complete public
prefix gives a fixed, lossy representation; no semantic sufficiency is claimed.
This module requires separately joined, source-isolated terminal labels and
must not fit on the reused nine-root development panel.
"""
import hashlib
import json
import math
import re

import numpy as np

from experiments.sequential.public_history import bind_selection, public_view

ACTIONS = ('STOP', 'PATCH', 'RETHINK')
DIM = 256
PENALTY = 1.0


def features(view):
    """Fixed public-only representation; no root, outcome, or audit inputs."""
    v = public_view(view)
    x = np.zeros(DIM, dtype=float)
    x[0] = 1.0
    tokens = ['turn:' + str(len(v['public_observations'])),
              'remaining:' + str(v['remaining_calls'])]
    for i, m in enumerate(v['messages']):
        words = re.findall(r'[a-z_][a-z_0-9]*|\d+', m['content'].lower())
        tokens.extend(f'm:{i}:role:{m["role"]}:word:{w}' for w in words)
        tokens.extend(f'm:{i}:role:{m["role"]}:pair:{a}:{b}' for a, b in zip(words, words[1:]))
    tokens.extend('o:%d:%s' % (o['message_index'], o['status'])
                  for o in v['public_observations'])
    for token in tokens:
        h = hashlib.sha256(token.encode()).digest()
        x[1+int.from_bytes(h[:8], 'big') % (DIM-1)] += 1 if h[8] & 1 else -1
    # Normalize prefix length without dropping chronology.
    norm = np.linalg.norm(x[1:])
    if norm:
        x[1:] /= norm
    return x


def validate(episodes):
    """Require complete assigned trajectories and an actual selection law."""
    if type(episodes) is not list or not episodes:
        raise ValueError('nonempty episodes required')
    identities = set()
    versions = set()
    for e in episodes:
        if type(e) is not dict or set(e) != {'episode', 'family', 'steps', 'outcome'}:
            raise ValueError('episode schema, including complete terminal label')
        if type(e['episode']) is not str or not e['episode'] or e['episode'] in identities:
            raise ValueError('duplicate/invalid episode')
        identities.add(e['episode'])
        if type(e['family']) is not str or not e['family']:
            raise ValueError('family required')
        y = e['outcome']
        if type(y) not in (int, float) or not math.isfinite(y) or not 0 <= y <= 1:
            raise ValueError('missing or out-of-range terminal outcome')
        steps = e['steps']
        if type(steps) is not list or len(steps) not in (1, 2):
            raise ValueError('two-decision horizon')
        for t, step in enumerate(steps):
            if type(step) is not dict or set(step) != {'view', 'selection'}:
                raise ValueError('step schema')
            v = public_view(step['view'])
            for observation in v['public_observations']:
                versions.add((v['receiver_sha256'], v['generator_sha256'],
                              observation['observer_sha256']))
            s = step['selection']
            if len(v['public_observations']) != t+1 or v['remaining_calls'] != 2-t:
                raise ValueError('decision stage mismatch')
            if [a['id'] for a in v['slate']] != list(ACTIONS):
                raise ValueError('supported action slate drift')
            if s != bind_selection(v, s['probabilities'], s['chosen_id']):
                raise ValueError('selection/probability binding drift')
            if any(p <= 0 for p in s['probabilities']):
                raise ValueError('positive probability required for all supported actions')
            if t:
                prev = steps[0]
                old = prev['view']['messages']
                new = v['messages']
                if new[:len(old)] != old or len(new) != len(old)+2 or new[-2]['role'] != 'user':
                    raise ValueError('continuation prefix mismatch')
                chosen = prev['selection']['chosen_id']
                prompt = next(a['text'] for a in prev['view']['slate'] if a['id'] == chosen)
                if chosen == 'STOP' or new[-2]['content'] != prompt:
                    raise ValueError('STOP continuation or changed selected prompt')
        if len(steps) == 1 and steps[0]['selection']['chosen_id'] != 'STOP':
            raise ValueError('continuation/service missing is not STOP')
    if len(versions) != 1:
        raise ValueError('receiver/generator version drift')
    return versions.pop()


def _ridge(xs, ys):
    x = np.stack(xs)
    y = np.asarray(ys, dtype=float)
    penalty = np.eye(DIM)*PENALTY
    penalty[0, 0] = 0
    return np.linalg.solve(x.T @ x + penalty, x.T @ y)


def fit(episodes):
    """Backward Q regression, with observed STOP labels and no oracle input."""
    versions = validate(episodes)
    model = {'coefficients': [None, None],
             'training_families': frozenset(e['family'] for e in episodes),
             'versions': versions,
             'action_counts': [None, None],
             'specification': {'dimension': DIM, 'ridge': PENALTY,
                               'feature_version': 'fixed-public-text-hash-v1',
                               'tie_order': list(ACTIONS)}}
    for t in (1, 0):
        active = [e for e in episodes if t < len(e['steps'])]
        counts = {a: 0 for a in ACTIONS}
        inputs = {a: [] for a in ACTIONS}
        targets = {a: [] for a in ACTIONS}
        for e in active:
            a = e['steps'][t]['selection']['chosen_id']
            y = e['outcome']
            if t == 0 and a != 'STOP':
                _, values = predict(model, e['steps'][1]['view'], turn=1)
                y = max(values.values())
            counts[a] += 1
            inputs[a].append(features(e['steps'][t]['view']))
            targets[a].append(y)
        if min(counts.values()) == 0:
            raise ValueError('absent stage-action support: ' + str((t, counts)))
        model['coefficients'][t] = np.stack([_ridge(inputs[a], targets[a]) for a in ACTIONS])
        model['action_counts'][t] = counts
    return model


def predict(model, view, *, turn):
    if turn not in (0, 1) or len(view['public_observations']) != turn+1:
        raise ValueError('turn mismatch')
    coefficients = model['coefficients'][turn]
    if coefficients is None:
        raise ValueError('stage not fitted')
    values = np.clip(coefficients @ features(view), 0., 1.)
    # Argmax breaks ties in frozen STOP,PATCH,RETHINK order.
    chosen = ACTIONS[int(np.argmax(values))]
    return chosen, {a: float(v) for a, v in zip(ACTIONS, values)}


def evaluate_disjoint(model, episodes):
    """Known-propensity IPW/longitudinal DR for one fixed fitted policy.

    This is evaluation, not DR policy training. It assumes sequential
    randomization, consistency, positive logged support, and correct outcome
    handling. One row per assigned episode is retained.
    """
    if validate(episodes) != model['versions']:
        raise ValueError('evaluation receiver/generator version drift')
    if model['training_families'] & {e['family'] for e in episodes}:
        raise ValueError('training/evaluation family overlap')
    rows = []
    for e in episodes:
        weight = 1.0
        dr = 0.0
        for t, step in enumerate(e['steps']):
            a, q = predict(model, step['view'], turn=t)
            logged = step['selection']['chosen_id']
            prob = step['selection']['selected_probability']
            if t == 0:
                dr = q[a]
            weight *= float(logged == a)/prob
            if t+1 < len(e['steps']):
                next_action, next_q = predict(model, e['steps'][t+1]['view'], turn=t+1)
                target = next_q[next_action]
            else:
                target = e['outcome']
            dr += weight*(target-q[logged])
        rows.append({'episode': e['episode'], 'family': e['family'],
                     'ipw': weight*e['outcome'], 'dr': dr})
    return rows
