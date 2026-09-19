#!/usr/bin/env python3
"""Audit A3 -- how much is there to win from multi-turn iteration at all?

At zero GPU cost, from a completed real run. Before designing an experiment about
adaptive prompting it is worth knowing whether iteration on this task family has
any headroom, and where the headroom sits: in better feedback CONTENT, or in
better decisions about WHEN to iterate.

Source: ykzeng-yale/DTR-AgentEvals, code-routing log stage,
results/code_routing/log/episodes.jsonl -- 4,488 episodes, 0 errors, Qwen2.5-3B and
Qwen2.5-7B (q4_k_m) over the same 591-task pool (identical tasks_sha256).

Scope. That project's intervention is its own repair prompt (it re-prompts the model
with the failures of its model-written visible checks), and its stopping rule is
"stop when the visible checks pass". Both differ from this project's intervention
taxonomy and stopping rule. So these numbers bound and motivate; they are not this
project's results. What transfers is the STRUCTURE: a real loop, a hidden-test
outcome, and a stopping rule that is not the outcome.

Definitions, all conditional on the hidden-test status of the FIRST candidate:
  repair rate       P(final correct | first wrong, another turn taken)
  degradation rate  P(final wrong   | first correct, another turn taken)
  missed repair     first wrong, but the loop stopped after one turn because its
                    self-check said the answer was fine
"""
from __future__ import annotations

import argparse, json, math, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = Path('/Users/yukangzengcmac/DTR-AgentEvals/results/code_routing/log/episodes.jsonl')


def wilson(k: int, n: int, z: float = 1.96):
    """Wilson score interval; the counts here are small enough that a normal
    approximation on the proportion would be misleading."""
    if n == 0:
        return (float('nan'), float('nan'))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--episodes', default=str(SRC))
    ap.add_argument('--out', default=str(ROOT / 'results' / 'audits' / 'iteration_value'))
    a = ap.parse_args()

    n = 0
    cells = {('correct', 'iterated'): [0, 0],   # [n, n_ended_wrong]
             ('correct', 'stopped'): [0, 0],
             ('wrong', 'iterated'): [0, 0],     # [n, n_ended_correct]
             ('wrong', 'stopped'): [0, 0]}
    stop_reason = {}
    sha = set()
    for line in Path(a.episodes).open():
        r = json.loads(line)
        n += 1
        sha.add(r.get('tasks_sha256'))
        nd = r.get('n_decisions') or len(r.get('decisions') or [])
        first_ok = bool(r.get('success_first_candidate'))
        fin_ok = bool(r.get('success'))
        arm = 'iterated' if nd > 1 else 'stopped'
        key = ('correct' if first_ok else 'wrong', arm)
        cells[key][0] += 1
        if first_ok and not fin_ok:
            cells[key][1] += 1
        if (not first_ok) and fin_ok:
            cells[key][1] += 1
        k = (key[0], arm, r.get('stop_reason'))
        stop_reason[k] = stop_reason.get(k, 0) + 1

    ci, si = cells[('correct', 'iterated')], cells[('correct', 'stopped')]
    wi, ws = cells[('wrong', 'iterated')], cells[('wrong', 'stopped')]
    rep_k, rep_n = wi[1], wi[0]
    deg_k, deg_n = ci[1], ci[0]

    # observed final success
    final_ok = si[0] - si[1] + (ci[0] - ci[1]) + wi[1] + ws[1]
    base_rate = final_ok / n

    # headroom from STOPPING DECISIONS ALONE, holding the feedback content fixed:
    # (i) iterate on the failures that were stopped early, assuming they repair at
    # the same observed rate; (ii) do not iterate when the answer is already correct.
    rep_rate = rep_k / max(rep_n, 1)
    gain_from_not_stopping_early = ws[0] * rep_rate
    gain_from_stopping_when_correct = deg_k
    potential = (final_ok + gain_from_not_stopping_early + gain_from_stopping_when_correct) / n

    out = {
        'audit': 'A3_iteration_value',
        'created_utc': time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()),
        'source': str(a.episodes),
        'source_episodes': n,
        'source_tasks_sha256': sorted(x for x in sha if x),
        'cells': {
            'first_correct_and_iterated': {'n': ci[0], 'ended_wrong': ci[1]},
            'first_correct_and_stopped': {'n': si[0], 'ended_wrong': si[1]},
            'first_wrong_and_iterated': {'n': wi[0], 'ended_correct': wi[1]},
            'first_wrong_and_stopped': {'n': ws[0], 'ended_correct': ws[1]},
        },
        'rates': {
            'repair_rate_given_wrong_and_iterated': {
                'estimate': rep_rate, 'k': rep_k, 'n': rep_n, 'wilson95': wilson(rep_k, rep_n)},
            'degradation_rate_given_correct_and_iterated': {
                'estimate': deg_k / max(deg_n, 1), 'k': deg_k, 'n': deg_n, 'wilson95': wilson(deg_k, deg_n)},
            'fraction_of_failures_stopped_after_one_turn': {
                'estimate': ws[0] / max(ws[0] + wi[0], 1), 'k': ws[0], 'n': ws[0] + wi[0],
                'wilson95': wilson(ws[0], ws[0] + wi[0])},
            'fraction_of_episodes_taking_more_than_one_turn': (ci[0] + wi[0]) / n,
        },
        'headroom_from_stopping_decisions_only': {
            'observed_final_success_rate': base_rate,
            'if_no_failure_were_stopped_early_and_no_correct_answer_were_disturbed': potential,
            'absolute_gain': potential - base_rate,
            'components': {
                'successes_recoverable_from_prematurely_stopped_failures': gain_from_not_stopping_early,
                'successes_preserved_by_not_iterating_on_correct_answers': gain_from_stopping_when_correct,
            },
            'assumptions': [
                'prematurely stopped failures would repair at the same rate as the failures that were iterated, '
                'which is optimistic if the self-check stopped precisely on the cases that look easy but are not',
                'stopping when already correct is only available to an oracle; a real rule must infer correctness',
                'feedback content is held fixed at the source project\'s repair prompt',
            ],
        },
        'stop_reason_breakdown': {f'{k[0]}|{k[1]}|{k[2]}': v for k, v in
                                  sorted(stop_reason.items(), key=lambda kv: -kv[1])},
    }
    outdir = Path(a.out) / out['created_utc']
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / 'summary.json').write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    print('\nwrote', outdir)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
