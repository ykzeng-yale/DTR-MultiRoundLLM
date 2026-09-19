#!/usr/bin/env python3
"""Audit A1 -- task-pool validity for DTR-MultiRoundLLM.

CPU-only; no model calls. Establishes, before any experiment is frozen, that the
591-task pool can carry a causal experiment whose treatment is a natural-language
message and whose outcome is a hidden-test pass.

Checks
  S1 structural      every task parses, has an entry point, and (MBPP) has at
                     least two assertions after the visible one is carved out.
  S2 visible split   MBPP `signature_example` is exactly `test_list[0]`, so the
                     one assert shown to the receiver is identifiable and can be
                     excluded from grading.
  S3 reference full  the benchmark reference passes ALL of its own assertions in
                     the sandbox. A task whose reference fails is unusable: its
                     outcome would be undefined.
  S4 reference hidden the reference passes the HIDDEN-only program, i.e. the split
                     did not break the harness.
  S5 discrimination  a stub that defines the entry point but returns None FAILS
                     the hidden tests. If a stub passes, the hidden tests do not
                     discriminate and the task cannot measure anything.
  S6 leakage surface how much of the solution BODY appears verbatim in the
                     visible material (prompt + visible assert). A task whose
                     solution is already largely visible cannot show an
                     intervention effect. Measured on the body, not the whole
                     reference: every HumanEval `reference` begins with its
                     `prompt`, so the whole-reference share is ~0.75 by
                     construction and says nothing about leakage.

Outputs results/audits/task_pool/<stamp>/{report.json,report.md,excluded.json}.
Pass/fail rules are in the report and in docs/experiment_protocol.md.
"""
from __future__ import annotations

import argparse, hashlib, json, os, platform, subprocess, sys, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments' / 'common'))

import sandbox  # noqa: E402
from verify import build_program, defines_entry_point, split_tests, verify  # noqa: E402

STUB_MBPP = "def {ep}(*args, **kwargs):\n    return None\n"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def code_sha256() -> str:
    h = hashlib.sha256()
    for p in sorted([Path(__file__), ROOT / 'experiments' / 'common' / 'sandbox.py',
                     ROOT / 'experiments' / 'common' / 'verify.py']):
        h.update(p.read_bytes())
    return h.hexdigest()


def stub_for(task: dict) -> str:
    """A syntactically valid candidate that defines the entry point and does nothing."""
    ep = task['entry_point']
    if task['benchmark'] == 'humaneval':
        # keep the signature from the prompt so the call in `check` binds, then return None
        head = task['prompt'].rstrip()
        # strip the docstring body by re-declaring: simplest robust stub is a *args form
        return "def {ep}(*args, **kwargs):\n    return None\n".format(ep=ep)
    return STUB_MBPP.format(ep=ep)


def audit_one(task: dict) -> dict:
    uid = task['uid']
    sp = split_tests(task)
    ht = sp['hidden_task']
    out = {
        'uid': uid,
        'benchmark': task['benchmark'],
        'entry_point': task['entry_point'],
        'n_tests_total': len(task.get('test_list') or []) if task['benchmark'] == 'mbpp' else 1,
        'n_hidden': sp['n_hidden'],
        'visible_is_first_assert': (task['benchmark'] != 'mbpp') or (
            task.get('signature_example', '') == (task['test_list'][0] if task['test_list'] else '')),
    }
    # S1 structural
    out['reference_defines_entry_point'] = defines_entry_point(task, task['reference'])
    # S3 reference on the FULL test set
    r_full = verify(task, task['reference'])
    out['reference_passes_full'] = bool(r_full['success'])
    out['reference_full_stderr_tail'] = (r_full['run'].get('stderr') or '')[-240:]
    # S4 reference on HIDDEN only
    r_hid = verify(ht, task['reference'])
    out['reference_passes_hidden'] = bool(r_hid['success'])
    out['reference_hidden_stderr_tail'] = (r_hid['run'].get('stderr') or '')[-240:]
    # S5 discrimination: a do-nothing stub must FAIL the hidden tests
    r_stub = verify(ht, stub_for(task))
    out['stub_passes_hidden'] = bool(r_stub['success'])
    # S6 leakage surface: how much of the SOLUTION BODY is already visible before
    # any intervention is sent. For all 164 HumanEval tasks the `reference` field
    # literally begins with `prompt` (signature + docstring), so a share computed
    # against the whole reference measures the prompt against itself and reads
    # ~0.75 by construction. The graded quantity is therefore the body: the
    # reference with that prompt prefix removed. MBPP references do not contain
    # the prompt, so body == reference there.
    visible = (task['prompt'] or '') + '\n' + '\n'.join(sp['visible'])
    ref = (task['reference'] or '')
    body = ref[len(task['prompt']):] if ref.startswith(task['prompt'] or '\0') else ref
    out['visible_chars'] = len(visible)
    out['reference_chars'] = len(ref)
    out['body_chars'] = len(body)
    out['reference_share_visible'] = round(_lcs_share(ref, visible), 4)   # kept for transparency; see note above
    out['body_share_visible'] = round(_lcs_share(body, visible), 4)       # the honest metric
    out['seconds'] = round(r_full['verify_seconds'] + r_hid['verify_seconds'] + r_stub['verify_seconds'], 3)
    return out


def _lcs_share(a: str, b: str) -> float:
    """Longest common substring of a and b, as a fraction of len(a). O(len(a)*len(b))
    with a rolling row; both strings are short (medians 163 and 96 chars)."""
    if not a or not b:
        return 0.0
    a = ' '.join(a.split())
    b = ' '.join(b.split())
    prev = [0] * (len(b) + 1)
    best = 0
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        ai = a[i - 1]
        for j in range(1, len(b) + 1):
            if ai == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best = cur[j]
        prev = cur
    return best / len(a)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--tasks', default=str(ROOT / 'work' / 'data' / 'tasks.json'))
    ap.add_argument('--workers', type=int, default=4, help='keep low: the GPU is shared with sibling runs')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--out', default=str(ROOT / 'results' / 'audits' / 'task_pool'))
    a = ap.parse_args()

    tasks_path = Path(a.tasks)
    tasks = json.loads(tasks_path.read_text())
    if a.limit:
        tasks = tasks[:a.limit]

    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        rows = list(ex.map(audit_one, tasks, chunksize=4))
    elapsed = time.time() - t0

    # ---- aggregate + pass/fail rules -------------------------------------
    n = len(rows)
    def cnt(f):
        return sum(1 for r in rows if f(r))

    usable = [r for r in rows if r['reference_passes_full'] and r['reference_passes_hidden']
              and not r['stub_passes_hidden'] and r['n_hidden'] >= 1]
    excluded = [r for r in rows if r not in usable]

    summary = {
        'n_tasks': n,
        'n_mbpp': cnt(lambda r: r['benchmark'] == 'mbpp'),
        'n_humaneval': cnt(lambda r: r['benchmark'] == 'humaneval'),
        'S1_reference_defines_entry_point': cnt(lambda r: r['reference_defines_entry_point']),
        'S2_visible_is_first_assert': cnt(lambda r: r['visible_is_first_assert']),
        'S2_min_hidden_asserts_mbpp': min([r['n_hidden'] for r in rows if r['benchmark'] == 'mbpp'] or [0]),
        'S3_reference_passes_full': cnt(lambda r: r['reference_passes_full']),
        'S4_reference_passes_hidden': cnt(lambda r: r['reference_passes_hidden']),
        'S5_stub_passes_hidden': cnt(lambda r: r['stub_passes_hidden']),
        'S6_body_share_visible_median': _median([r['body_share_visible'] for r in rows]),
        'S6_body_share_visible_median_mbpp': _median([r['body_share_visible'] for r in rows if r['benchmark'] == 'mbpp']),
        'S6_body_share_visible_median_humaneval': _median([r['body_share_visible'] for r in rows if r['benchmark'] == 'humaneval']),
        'S6_tasks_body_mostly_visible_ge_0.6': cnt(lambda r: r['body_share_visible'] >= 0.6),
        'S6_whole_reference_share_visible_median': _median([r['reference_share_visible'] for r in rows]),
        'n_usable': len(usable),
        'n_excluded': len(excluded),
    }
    rules = {
        'S1': ('every reference defines its entry point',
               summary['S1_reference_defines_entry_point'] == n),
        'S2': ('MBPP visible assert is identifiable as test_list[0] for every task, and >= 1 hidden assert remains',
               summary['S2_visible_is_first_assert'] == n and summary['S2_min_hidden_asserts_mbpp'] >= 1),
        'S3': ('>= 98% of references pass their own full test set',
               summary['S3_reference_passes_full'] >= 0.98 * n),
        'S4': ('the hidden-only split does not break any reference that passed the full set',
               summary['S4_reference_passes_hidden'] >= summary['S3_reference_passes_full'] - 0),
        # A stub-passing task is excluded, not a fatal pool defect; the gate is on
        # the RATE, because a pool where many tasks are satisfied by a do-nothing
        # stub cannot measure an intervention effect at all.
        'S5': ('at most 1% of tasks are passed by a do-nothing stub (those are excluded)',
               summary['S5_stub_passes_hidden'] <= 0.01 * n),
        'S6': ('no task has >= 60% of its solution body already visible',
               summary['S6_tasks_body_mostly_visible_ge_0.6'] == 0),
    }
    summary['rules'] = {k: {'rule': v[0], 'pass': bool(v[1])} for k, v in rules.items()}
    summary['all_rules_pass'] = all(v[1] for v in rules.values())

    stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    outdir = Path(a.out) / stamp
    outdir.mkdir(parents=True, exist_ok=True)
    manifest = {
        'audit': 'A1_task_pool',
        'created_utc': stamp,
        'tasks_path': str(tasks_path),
        'tasks_sha256': sha256_file(tasks_path),
        'code_sha256': code_sha256(),
        'python': sys.version.split()[0],
        'platform': platform.platform(),
        'sandbox': sandbox.sandbox_info(),
        'workers': a.workers,
        'elapsed_seconds': round(elapsed, 1),
    }
    (outdir / 'report.json').write_text(json.dumps(
        {'manifest': manifest, 'summary': summary, 'rows': rows}, indent=2, sort_keys=True))
    (outdir / 'excluded.json').write_text(json.dumps(
        [{k: r[k] for k in ('uid', 'benchmark', 'reference_passes_full', 'reference_passes_hidden',
                            'stub_passes_hidden', 'reference_full_stderr_tail')} for r in excluded],
        indent=2))
    (outdir / 'usable_uids.json').write_text(json.dumps(sorted(r['uid'] for r in usable), indent=2))
    (outdir / 'report.md').write_text(_markdown(manifest, summary, rows, excluded))
    print((outdir / 'report.md').read_text())
    print('wrote', outdir)
    return 0 if summary['all_rules_pass'] else 1


def _median(xs):
    xs = sorted(xs)
    if not xs:
        return 0.0
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else round((xs[m - 1] + xs[m]) / 2, 4)


def _markdown(manifest, s, rows, excluded) -> str:
    L = []
    L.append('# Audit A1 — task-pool validity\n')
    L.append('Run %s, %s, sandbox `%s`, %d workers, %.1f s.\n'
             % (manifest['created_utc'], manifest['python'], manifest['sandbox'].get('kind'),
                manifest['workers'], manifest['elapsed_seconds']))
    L.append('Task file `%s`\n\nsha256 `%s`\n' % (manifest['tasks_path'], manifest['tasks_sha256']))
    L.append('## Result\n')
    L.append('| check | quantity | value |')
    L.append('|---|---|---|')
    L.append('| — | tasks | %d (MBPP %d, HumanEval %d) |' % (s['n_tasks'], s['n_mbpp'], s['n_humaneval']))
    L.append('| S1 | references defining their entry point | %d / %d |' % (s['S1_reference_defines_entry_point'], s['n_tasks']))
    L.append('| S2 | MBPP visible assert identifiable as `test_list[0]` | %d / %d |' % (s['S2_visible_is_first_assert'], s['n_tasks']))
    L.append('| S2 | minimum hidden asserts per MBPP task | %d |' % s['S2_min_hidden_asserts_mbpp'])
    L.append('| S3 | references passing their full test set | %d / %d |' % (s['S3_reference_passes_full'], s['n_tasks']))
    L.append('| S4 | references passing the hidden-only program | %d / %d |' % (s['S4_reference_passes_hidden'], s['n_tasks']))
    L.append('| S5 | tasks passed by a do-nothing stub | %d |' % s['S5_stub_passes_hidden'])
    L.append('| S6 | median share of the solution BODY already visible | %s (MBPP %s, HumanEval %s) |'
             % (s['S6_body_share_visible_median'], s['S6_body_share_visible_median_mbpp'], s['S6_body_share_visible_median_humaneval']))
    L.append('| S6 | tasks with >= 60%% of the body already visible | %d |' % s['S6_tasks_body_mostly_visible_ge_0.6'])
    L.append('| S6 | median share of the *whole reference* visible (artifact: HumanEval references embed the prompt) | %s |' % s['S6_whole_reference_share_visible_median'])
    L.append('| — | **usable tasks** | **%d** |' % s['n_usable'])
    L.append('| — | excluded | %d |' % s['n_excluded'])
    L.append('\n## Pass/fail rules\n')
    L.append('| rule | statement | pass |')
    L.append('|---|---|---|')
    for k, v in s['rules'].items():
        L.append('| %s | %s | %s |' % (k, v['rule'], 'yes' if v['pass'] else '**NO**'))
    L.append('\nAll rules pass: **%s**\n' % ('yes' if s['all_rules_pass'] else 'no'))
    if excluded:
        L.append('## Excluded tasks\n')
        L.append('| uid | ref full | ref hidden | stub passes |')
        L.append('|---|---|---|---|')
        for r in excluded[:60]:
            L.append('| %s | %s | %s | %s |' % (r['uid'], r['reference_passes_full'],
                                                r['reference_passes_hidden'], r['stub_passes_hidden']))
        if len(excluded) > 60:
            L.append('\n(%d more in `excluded.json`.)\n' % (len(excluded) - 60))
    L.append('\n## Reading\n')
    L.append('S3/S4 establish that the outcome is well defined: a task whose own reference '
             'cannot pass its assertions has no attainable outcome and must be dropped. '
             'S5 establishes that the outcome can *move*: a pool where a stub passes measures nothing. '
             'S2 is what makes the treatment separable from the outcome in this project — the single '
             'assertion shown to the receiver is identifiable, so it can be excluded from grading and '
             'interventions can be audited for quoting a graded assertion. S6 bounds how much of the '
             'answer is visible before any intervention is sent.\n')
    return '\n'.join(L) + '\n'


if __name__ == '__main__':
    raise SystemExit(main())
