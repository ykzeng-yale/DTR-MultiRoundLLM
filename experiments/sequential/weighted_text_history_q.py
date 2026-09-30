"""Versioned, episode-weighted quality-only backward fitted Q.

Uses the original fixed public-text representation and supported action slate.
Positive episode weights must be constructed prospectively without outcomes;
this API verifies their identities and values, not that provenance. The caller
must reconcile every assigned episode before fitting: no complete-case release
or family validity is established here. This is not DR training or a cost-optimal
controller, and no existing pilot has been fitted by introducing this module.
"""
from fractions import Fraction
import hashlib
import json
import math

import numpy as np

from experiments.sequential.text_history_q import (
    ACTIONS, DIM, PENALTY, features, predict, validate,
)

VERSION = 'weighted-public-text-fitted-q-v1'
NORMALIZATION = 'normalize once over all episodes to sum N; never renormalize stage/action subsets'


def _weight_records(weights):
    return [{'episode': identity, 'weight': [value.numerator, value.denominator]}
            for identity, value in sorted(weights.items())]


def _weight_hash(weights):
    raw = json.dumps(_weight_records(weights), sort_keys=True,
                     separators=(',', ':'), ensure_ascii=True).encode()
    return hashlib.sha256(raw).hexdigest()


def _weights(episodes, sample_weights):
    identities = {episode['episode'] for episode in episodes}
    if (type(sample_weights) is not dict
            or any(type(key) is not str for key in sample_weights)
            or set(sample_weights) != identities):
        raise ValueError('sample weights must bind every exact episode ID')
    raw = {}
    for identity, value in sample_weights.items():
        if type(value) not in (int, float, Fraction):
            raise ValueError('positive finite sample weights required')
        if type(value) is float and not math.isfinite(value):
            raise ValueError('positive finite sample weights required')
        value = Fraction(value)
        if value <= 0:
            raise ValueError('positive finite sample weights required')
        raw[identity] = value
    total = sum(raw.values(), Fraction(0))
    normalized = {identity: len(episodes) * value / total
                  for identity, value in raw.items()}
    numeric = {}
    for identity, value in normalized.items():
        converted = float(value)
        if not math.isfinite(converted) or converted <= 0:
            raise ValueError('normalized sample weights must remain positive finite floats')
        numeric[identity] = converted
    return raw, normalized, numeric


def _weighted_ridge(xs, ys, weights):
    """Use supplied globally normalized subset weights without rescaling them.

    The intercept is unpenalized, as in the original fit. A scalar multiplication
    of the supplied subset weights would change its ridge-to-loss ratio; global
    scale invariance is supplied by the one-time normalization in fit_weighted().
    """
    x = np.stack(xs)
    y = np.asarray(ys, dtype=float)
    w = np.asarray(weights, dtype=float)
    if (x.ndim != 2 or x.shape[1] != DIM or y.shape != (len(x),)
            or w.shape != (len(x),) or not np.isfinite(x).all()
            or not np.isfinite(y).all() or not np.isfinite(w).all()
            or np.any(w <= 0)):
        raise ValueError('finite matching regression rows and positive weights required')
    penalty = np.eye(DIM) * PENALTY
    penalty[0, 0] = 0
    return np.linalg.solve(x.T @ (w[:, None] * x) + penalty,
                           x.T @ (w * y))


def fit_weighted(episodes, sample_weights):
    """Fit weighted backward Q with unchanged quality targets and STOP labels.

    For N provided complete episodes, the normalized weights are
    N * supplied_weight / sum(supplied_weights). Thus uniform supplied weights
    reproduce the original ridge penalty convention. Every surviving decision
    retains its episode's globally normalized weight at both stages; neither
    active-stage nor selected-action weights are renormalized. This is a
    declared regularization convention, not a proof of representation/support
    sufficiency or an automatically equal-family design.
    """
    versions = validate(episodes)
    raw, exact_weights, weights = _weights(episodes, sample_weights)
    families = frozenset(episode['family'] for episode in episodes)
    family_totals = {family: sum((exact_weights[episode['episode']]
                                 for episode in episodes if episode['family'] == family),
                                Fraction(0))
                     for family in sorted(families)}
    model = {
        'version': VERSION,
        'coefficients': [None, None],
        'training_families': families,
        'versions': versions,
        'action_counts': [None, None],
        'action_weight_totals': [None, None],
        'specification': {
            'dimension': DIM, 'ridge': PENALTY,
            'feature_version': 'fixed-public-text-hash-v1',
            'tie_order': list(ACTIONS), 'objective': 'quality-only weighted backward fitted Q',
            'weight_normalization': NORMALIZATION,
        },
        'sample_weight_metadata': {
            'episode_count': len(episodes), 'family_count': len(families),
            'input_weight_sha256': _weight_hash(raw),
            'normalized_weight_sha256': _weight_hash(exact_weights),
            'input_weight_sum': [sum(raw.values()).numerator, sum(raw.values()).denominator],
            'normalized_weight_sum': len(episodes),
            'normalized_family_totals': {
                family: [total.numerator, total.denominator]
                for family, total in family_totals.items()
            },
            'provenance': 'prospective outcome-independent construction and all-assigned reconciliation required from caller',
        },
    }
    for turn in (1, 0):
        active = [episode for episode in episodes if turn < len(episode['steps'])]
        counts = {action: 0 for action in ACTIONS}
        inputs = {action: [] for action in ACTIONS}
        targets = {action: [] for action in ACTIONS}
        stage_weights = {action: [] for action in ACTIONS}
        exact_totals = {action: Fraction(0) for action in ACTIONS}
        for episode in active:
            action = episode['steps'][turn]['selection']['chosen_id']
            target = episode['outcome']
            if turn == 0 and action != 'STOP':
                _, values = predict(model, episode['steps'][1]['view'], turn=1)
                target = max(values.values())
            identity = episode['episode']
            counts[action] += 1
            inputs[action].append(features(episode['steps'][turn]['view']))
            targets[action].append(target)
            stage_weights[action].append(weights[identity])
            exact_totals[action] += exact_weights[identity]
        if min(counts.values()) == 0:
            raise ValueError('absent stage-action support: ' + str((turn, counts)))
        model['coefficients'][turn] = np.stack([
            _weighted_ridge(inputs[action], targets[action], stage_weights[action])
            for action in ACTIONS
        ])
        model['action_counts'][turn] = counts
        model['action_weight_totals'][turn] = {
            action: [value.numerator, value.denominator]
            for action, value in exact_totals.items()
        }
    return model
