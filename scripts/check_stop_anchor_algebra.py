"""Exact finite-tree checks for a design note; no sampling, fitting or LLM calls."""
from __future__ import annotations

from fractions import Fraction as F
import json
import time


def check():
    assertions = 0
    def equal(a, b):
        nonlocal assertions
        assertions += 1
        assert a == b, (a, b)

    # Toy law: two actions, two decisions, absorbing STOP and complete outcomes.
    # Nuisance values are arbitrary rational functions fixed before evaluation.
    def policy(t):
        return (F(1, 2), F(1, 2)) if t == 0 else (F(2, 5), F(3, 5))
    def behavior(h):
        p = (F(1, 3) if h[0] == 0 else F(2, 3)) if len(h) == 1 else (F(1, 4) if h[-1] == 0 else F(3, 4))
        return p, 1-p
    def q(mode, h, a):
        original = F(2 + h[0] + 2*a + (h[-1] if len(h) > 1 else 0), 10)
        if mode == 'original':
            return original
        if a == 0:
            return F(h[-1])
        # Also perturb an upstream continuation prediction: the general
        # identity must cover changes beyond STOP. This is not a fitted model.
        return original + (F(1, 10) if len(h) == 1 else 0)

    paths = []
    for x, px in [(0, F(1, 3)), (1, F(2, 3))]:
        h0 = (x,)
        paths.append((px * behavior(h0)[0], px * policy(0)[0], [(h0, 0)], F(x)))
        pz = F(1, 4) if x == 0 else F(3, 4)
        for z, prob in [(0, 1-pz), (1, pz)]:
            h1 = (x, z)
            for a1 in range(2):
                paths.append((px * behavior(h0)[1] * prob * behavior(h1)[a1],
                              px * policy(0)[1] * prob * policy(1)[a1],
                              [(h0, 1), (h1, a1)], F(z if a1 == 0 else 1-z)))

    def score(mode, rows, y):
        values = [sum(policy(t)[a] * q(mode, h, a) for a in range(2)) for t, (h, _) in enumerate(rows)] + [F(0)]
        result, weight = values[0], F(1)
        for t, (h, a) in enumerate(rows):
            weight *= policy(t)[a] / behavior(h)[a]
            reward = y if t == len(rows)-1 else F(0)
            result += weight * (reward + values[t+1] - q(mode, h, a))
        return result

    def increment_sum(rows):
        result, previous_weight = F(0), F(1)
        for t, (h, a) in enumerate(rows):
            delta = [q('modified', h, j)-q('original', h, j) for j in range(2)]
            ratio = policy(t)[a] / behavior(h)[a]
            result += previous_weight * (sum(policy(t)[j]*delta[j] for j in range(2))-ratio*delta[a])
            previous_weight *= ratio
        return result

    equal(sum(p for p, _, _, _ in paths), 1)
    equal(sum(p for _, p, _, _ in paths), 1)
    truth = sum(p*y for _, p, _, y in paths)
    means = {mode: sum(p*score(mode, rows, y) for p, _, rows, y in paths) for mode in ('original','modified')}
    for _, _, rows, y in paths:
        equal(score('modified',rows,y)-score('original',rows,y), increment_sum(rows))
    equal(means['original'], truth)
    equal(means['modified'], truth)
    equal(sum(p*increment_sum(rows) for p, _, rows, _ in paths), 0)

    # Universal-claim counterexample, not a realization of the E0 fitted model.
    c = F(1, 2)
    old = [c-c, c-c]
    anchored = [c/2, -c/2]
    equal(sum(old)/2, 0)
    equal(sum(anchored)/2, 0)
    equal(sum(x*x for x in old)/2, 0)
    equal(sum(x*x for x in anchored)/2, c*c/4)
    return {
        'classification': 'Exact rational toy-law identities; not sampled performance or an E0 estimator rerun',
        'enumerated_paths': len(paths), 'assertions': assertions,
        'target_value': str(truth), 'original_mean': str(means['original']),
        'modified_mean': str(means['modified']),
        'counterexample': {'c': str(c), 'old_variance': '0', 'anchored_variance': str(c*c/4),
                          'scope': 'Arbitrary predictable nuisance sequences; not claimed attainable by the current E0 fitter under this degenerate law'},
        'random_draws': 0, 'sampled_datasets': 0, 'fits': 0,
        'model_calls': 0, 'prompt_tokens': 0, 'completion_tokens': 0,
        'benchmark_executions': 0, 'paid_usd': 0,
    }


if __name__ == '__main__':
    wall, cpu = time.perf_counter(), time.process_time()
    result = check()
    result['check_wall_seconds'] = time.perf_counter()-wall
    result['check_cpu_seconds'] = time.process_time()-cpu
    print(json.dumps(result, indent=2))
