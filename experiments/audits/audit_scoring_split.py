#!/usr/bin/env python3
"""Audit A4 -- does the assertion-level visible/hidden split give every task an
intervener-observable verdict and enough graded assertions? CPU only.

Blocker this closes: `verify.split_tests` left all 164 HumanEval tasks without a
visible verdict and with a hidden-assertion count of 1, which blocks any design
conditioning on an observed verdict. `common/scoring.py` splits `check` at
assertion level instead. This audit measures what that yields, and executes the
resulting hidden program against the reference to prove the split did not break
grading.
"""
from __future__ import annotations

import json, statistics as st, sys, time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments' / 'common'))
from sandbox import run_program, sandbox_info          # noqa: E402
from scoring import split_assertions                  # noqa: E402


def hidden_program(task: dict, code: str, sp) -> str:
    """The graded program: candidate + preamble + hidden assertions only."""
    parts = list(sp['preamble']) + [code, '']
    if task['benchmark'] == 'humaneval':
        parts += ['def check(candidate):'] + ['    ' + a for a in sp['hidden']]
        parts += ['check(%s)' % task['entry_point']]
    else:
        parts += list(sp['hidden'])
    return '\n'.join(parts) + '\n'


def one(task: dict) -> dict:
    sp = split_assertions(task)
    out = {'uid': task['uid'], 'benchmark': task['benchmark'], 'splittable': bool(sp['splittable']),
           'n_visible': len(sp['visible']), 'n_hidden': sp['n_hidden'],
           'n_dropped_revealed': len(sp['dropped_revealed']), 'usable': bool(sp['usable']),
           'u_source': sp['u_source']}
    if sp['usable']:
        r = run_program(hidden_program(task, task['reference'], sp), timeout_s=10.0)
        out['reference_passes_hidden'] = bool(r['passed'])
        out['stderr_tail'] = (r.get('stderr') or '')[-160:]
    else:
        out['reference_passes_hidden'] = None
    return out


def main() -> int:
    tasks = json.loads((ROOT / 'work' / 'data' / 'tasks.json').read_text())
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=4) as ex:
        rows = list(ex.map(one, tasks, chunksize=4))
    el = time.time() - t0

    def sel(b):
        return [r for r in rows if r['benchmark'] == b]
    summary = {'audit': 'A4_scoring_split', 'created_utc': time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()),
               'elapsed_seconds': round(el, 1), 'sandbox': sandbox_info(), 'n': len(rows)}
    for b in ('mbpp', 'humaneval'):
        rs = sel(b)
        hid = [r['n_hidden'] for r in rs if r['usable']]
        summary[b] = {
            'n': len(rs),
            'splittable': sum(r['splittable'] for r in rs),
            'usable': sum(r['usable'] for r in rs),
            'unusable': sum(not r['usable'] for r in rs),
            'with_visible_verdict': sum(r['n_visible'] > 0 for r in rs),
            'tasks_with_revealed_assertions_dropped': sum(r['n_dropped_revealed'] > 0 for r in rs),
            'total_revealed_assertions_dropped': sum(r['n_dropped_revealed'] for r in rs),
            'n_hidden_mean': round(st.mean(hid), 2) if hid else 0,
            'n_hidden_median': st.median(hid) if hid else 0,
            'n_hidden_min': min(hid) if hid else 0,
            'n_hidden_max': max(hid) if hid else 0,
            'reference_passes_hidden': sum(1 for r in rs if r['reference_passes_hidden']),
            'reference_fails_hidden': sum(1 for r in rs if r['reference_passes_hidden'] is False),
        }
    summary['unusable_uids'] = sorted(r['uid'] for r in rows if not r['usable'])
    summary['reference_failures'] = sorted(r['uid'] for r in rows if r['reference_passes_hidden'] is False)
    summary['usable_uids'] = sorted(r['uid'] for r in rows if r['usable'] and r['reference_passes_hidden'])
    summary['pass_rules'] = {
        'every usable task has exactly one visible assertion':
            all(r['n_visible'] == 1 for r in rows if r['usable']),
        'every usable task has at least one hidden assertion':
            all(r['n_hidden'] >= 1 for r in rows if r['usable']),
        'every usable task reference still passes the hidden-only program':
            not summary['reference_failures'],
    }
    summary['all_rules_pass'] = all(summary['pass_rules'].values())

    outdir = ROOT / 'results' / 'audits' / 'scoring_split' / summary['created_utc']
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / 'summary.json').write_text(json.dumps(summary, indent=2))
    (outdir / 'per_task.json').write_text(json.dumps(rows, indent=2))
    print(json.dumps({k: v for k, v in summary.items()
                      if k not in ('usable_uids', 'unusable_uids')}, indent=2))
    print('unusable:', summary['unusable_uids'])
    print('wrote', outdir)
    return 0 if summary['all_rules_pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
