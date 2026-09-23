#!/usr/bin/env python3
"""Deterministic forward-mass check of the fixed E0 regularization target.

Run with .venv/bin/python scripts/check_regularization_truth.py. No trajectories,
random variates, fitted models, benchmark programs or receiver calls are used.
The forward calculation rebuilds ordered-logit probabilities from the simulator
constants, preserves latent ease/error type, and absorbs STOP before transitions.
The simulator's backward dynamic program is used only as a separate comparison.
"""
from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
import time
from pathlib import Path

START_WALL = time.perf_counter()
START_CPU = time.process_time()
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import scipy  # noqa: E402
from experiments.e0 import simulator as sim  # noqa: E402

EXPECTED = 0.6459770061744536
HORIZON = 3
TOLERANCE = 1e-12


def ordered_probabilities(eta):
    """Independent scalar implementation of the declared ordered-logit law."""
    cdf = [1.0 / (1.0 + math.exp(-(float(cut) - eta))) for cut in sim.CUT]
    probabilities = [cdf[0], cdf[1] - cdf[0], cdf[2] - cdf[1], 1.0 - cdf[2]]
    if min(probabilities) < 0 or abs(math.fsum(probabilities) - 1.0) > TOLERANCE:
        raise ValueError('Invalid reconstructed ordered-logit distribution')
    return probabilities


def forward_value():
    if tuple(sim.ARMS) != ('STOP', 'RETRY', 'RESET', 'LOCAL', 'DIVERT') or sim.NS != 4:
        raise ValueError('This fixed target requires the declared five arms and four states')
    if abs(math.fsum(map(float, sim.P_E)) - 1.0) > TOLERANCE:
        raise ValueError('Ease probabilities do not sum to one')
    # E and Z are drawn once and persist; never mix them afresh at each step.
    alive = {}
    transitions = {}
    for e, ease in enumerate(sim.EASE_MID):
        initial = ordered_probabilities(float(sim.OFF + sim.LAM * 1.9 * (ease - .5)))
        for z in (0, 1):
            latent_mass = float(sim.P_E[e]) * (sim.P_Z if z else 1.0 - sim.P_Z)
            for state in range(4):
                alive[e, z, state] = latent_mass * initial[state]
                for arm in sim.ARMS[1:]:
                    eta = float(sim.MU[state] + sim.TH[arm, state, z]
                                + sim.LAM * (ease - .5))
                    transitions[e, z, state, arm] = ordered_probabilities(eta)
    absorbed_mass = 0.0
    stopped_success_terms = []
    stages = []
    for step in range(1, HORIZON + 1):
        alive_before = math.fsum(alive.values())
        stop_mass = .2 * alive_before
        stop_success = .2 * math.fsum(m for (_, _, s), m in alive.items() if s == 3)
        absorbed_mass += stop_mass
        stopped_success_terms.append(stop_success)
        next_terms = {key: [] for key in alive}
        for (e, z, state), mass in alive.items():
            for arm in sim.ARMS[1:]:
                for nxt, probability in enumerate(transitions[e, z, state, arm]):
                    next_terms[e, z, nxt].append(mass * .2 * probability)
        alive = {key: math.fsum(terms) for key, terms in next_terms.items()}
        alive_after = math.fsum(alive.values())
        if abs(absorbed_mass + alive_after - 1.0) > TOLERANCE:
            raise ValueError('Forward probability mass was not conserved')
        stages.append(dict(step=step, alive_before=alive_before,
                           stop_mass=stop_mass, stop_success_mass=stop_success,
                           alive_after=alive_after, cumulative_absorbed_mass=absorbed_mass))
    terminal_success = math.fsum(m for (_, _, s), m in alive.items() if s == 3)
    return math.fsum([*stopped_success_terms, terminal_success]), stages, terminal_success


def main():
    forward, stages, terminal_success = forward_value()
    backward = float(sim.true_value(sim.kernel(1.0), np.full(5, .2), HORIZON))
    if max(abs(forward - EXPECTED), abs(backward - EXPECTED), abs(forward - backward)) > TOLERANCE:
        raise ValueError('Truth mismatch: ' + repr((forward, backward, EXPECTED)))
    paths = [Path(__file__).resolve(), ROOT / 'experiments/e0/simulator.py']
    report = {
        'classification': 'Deterministic synthetic target-value check; not sampled simulation or estimator/LLM efficacy evidence',
        'target': {'horizon': HORIZON, 'policy': [.2] * 5, 'effect_multiplier': 1.0,
                   'template_offsets': None, 'stop': 'Absorb current success before transition'},
        'forward': forward, 'backward_dp': backward, 'expected': EXPECTED,
        'forward_minus_expected': forward - EXPECTED,
        'forward_minus_backward': forward - backward,
        'tolerance': TOLERANCE, 'stages': stages,
        'terminal_alive_success_mass': terminal_success,
        'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        'versions': {'python': platform.python_version(), 'numpy': np.__version__, 'scipy': scipy.__version__},
        'resources': {'wall_seconds_including_scientific_imports': time.perf_counter() - START_WALL,
                      'cpu_seconds_including_scientific_imports': time.process_time() - START_CPU,
                      'random_variates': 0, 'sampled_datasets': 0, 'fitted_models': 0,
                      'model_calls': 0, 'candidate_reference_executions': 0, 'paid_cost_usd': 0},
        'scope': 'Same fixed target for all behavior-policy cells; kappa/floor alter logging, not this value. Shared simulator constants and ease probabilities remain common inputs to both recursions.'
    }
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
