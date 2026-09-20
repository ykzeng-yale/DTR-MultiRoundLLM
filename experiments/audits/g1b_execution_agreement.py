#!/usr/bin/env python3
"""G1b -- does cross-candidate EXECUTION AGREEMENT recover the selection headroom?

The question the project now turns on. G0e showed the correct candidate is often already
generated while the cheap visible check fails to identify it (oracle pass@3 0.8192 vs
visible-picker 0.7455 on the 3B: a 7.4-point selection gap). G1a' showed cheap STATIC
features recover none of it. The remaining candidate -- and the strongest known cheap
selector for code -- is agreement: run every candidate on common inputs and prefer the
largest output-agreement cluster (the CodeT / MBR-exec / AlphaCode family).

Why this can be done at zero GPU cost, which was not obvious. Agreement needs no EXPECTED
values -- only that candidates be executed on COMMON inputs. So probe inputs can be
manufactured from the one visible assertion by mutating its literals, and every candidate
in the existing log can be run on them in the sandbox. Nothing here touches a graded
assertion: the selector sees only candidate source, the visible assertion, and outputs on
inputs whose correct answers nobody knows.

Pickers compared on identical candidate sets:
  VISIBLE     first candidate whose visible assertion passes, else the last. The incumbent.
  AGREEMENT   largest cluster of identical output vectors across probes; ties to the
              candidate that also passes the visible assertion, then to the first.
  AGREE+VIS   restrict to visible-passing candidates first, then take the largest
              agreement cluster within them. The natural combination.
  ORACLE      a hidden-passing candidate if one exists. The ceiling.

Cluster size is also reported as a confidence signal, because a selection rule is only
useful for STOPPING if it knows when it does not know.
"""
from __future__ import annotations

import argparse, ast, json, re, sys, time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments' / 'common'))
from sandbox import run_program                      # noqa: E402
from scoring import split_assertions                 # noqa: E402

SRC = Path('/Users/yukangzengcmac/DTR-AgentEvals/results/code_routing/log/episodes.jsonl')
SEP = '@@G1B@@'


# ---------------------------------------------------------------------------
# probe construction: mutate the literals of the visible assertion's call
# ---------------------------------------------------------------------------
class _Mutate(ast.NodeTransformer):
    def __init__(self, mode):
        self.mode = mode
        self.did = False

    def visit_Constant(self, n):
        v = n.value
        m = self.mode
        if isinstance(v, bool):
            if m in ('a', 'd'):
                self.did = True
                return ast.Constant(not v)
        elif isinstance(v, int):
            if m == 'a':
                self.did = True; return ast.Constant(v + 1)
            if m == 'b':
                self.did = True; return ast.Constant(0)
            if m == 'c':
                self.did = True; return ast.Constant(v * 2)
            if m == 'd':
                self.did = True; return ast.Constant(-v)
        elif isinstance(v, float):
            if m in ('a', 'c'):
                self.did = True; return ast.Constant(v * 2)
            if m == 'b':
                self.did = True; return ast.Constant(0.0)
        elif isinstance(v, str):
            if m == 'a' and len(v) > 1:
                self.did = True; return ast.Constant(v[:-1])
            if m == 'b':
                self.did = True; return ast.Constant('')
            if m == 'c':
                self.did = True; return ast.Constant(v + v)
        return n

    def visit_List(self, n):
        return self._seq(n, ast.List)

    def visit_Tuple(self, n):
        return self._seq(n, ast.Tuple)

    def _seq(self, n, cls):
        self.generic_visit(n)
        m = self.mode
        if len(n.elts) >= 2:
            if m == 'e':
                self.did = True
                return cls(elts=list(reversed(n.elts)), ctx=ast.Load())
            if m == 'f':
                self.did = True
                return cls(elts=n.elts[:max(1, len(n.elts) // 2)], ctx=ast.Load())
            if m == 'g':
                self.did = True
                return cls(elts=n.elts + n.elts[:1], ctx=ast.Load())
        return n


def call_args(assert_src: str, entry: str):
    """Argument source strings of the entry-point call inside an assertion."""
    try:
        tree = ast.parse(assert_src)
    except SyntaxError:
        return None
    best = None
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            fn = n.func
            name = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else None)
            if name in (entry, 'candidate') and n.args:
                best = n
    if best is None:
        return None
    return [ast.unparse(a) for a in best.args]


def probes_for(task: dict, n_max: int = 8):
    """The visible call, plus mutated variants of its literals. Inputs only; the correct
    outputs are unknown and unused."""
    sp = split_assertions(task)
    if not sp['visible']:
        return None
    args = call_args(sp['visible'][0], task['entry_point'])
    if not args:
        return None
    base = '(' + ', '.join(args) + ')'
    out = [base]
    for mode in ('a', 'e', 'f', 'b', 'c', 'g', 'd'):
        try:
            mutated = []
            ok = False
            for a in args:
                t = ast.parse(a, mode='eval')
                mu = _Mutate(mode)
                t2 = ast.fix_missing_locations(mu.visit(t))
                mutated.append(ast.unparse(t2))
                ok = ok or mu.did
            if ok:
                cand = '(' + ', '.join(mutated) + ')'
                if cand not in out:
                    out.append(cand)
        except Exception:
            continue
        if len(out) >= n_max:
            break
    return out


def probe_program(code: str, entry: str, probes, preamble) -> str:
    """One program per candidate: define it, then print a delimited repr per probe."""
    L = list(preamble or [])
    L.append(code)
    L.append('')
    L.append('import sys as _s')
    for i, p in enumerate(probes):
        L.append('try:')
        L.append('    _v = %s%s' % (entry, p))
        L.append('    _r = repr(_v)[:200]')
        L.append('except BaseException as _e:')
        L.append('    _r = "ERR:" + type(_e).__name__')
        L.append('print("%s%d" + chr(9) + _r, flush=True)' % (SEP, i))
    return '\n'.join(L) + '\n'


def run_cell(job):
    """Execute every candidate of one cell on the shared probes; return output vectors."""
    uid, entry, probes, preamble, cands = job
    vecs = []
    for c in cands:
        prog = probe_program(c['code'], entry, probes, preamble)
        r = run_program(prog, timeout_s=12.0)
        out = {}
        for line in (r.get('stdout') or '').splitlines():
            if line.startswith(SEP):
                try:
                    idx, val = line[len(SEP):].split('\t', 1)
                    out[int(idx)] = val
                except ValueError:
                    pass
        vecs.append(tuple(out.get(i, 'MISSING') for i in range(len(probes))))
    return uid, vecs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--episodes', default=str(SRC))
    ap.add_argument('--tasks', default=str(ROOT / 'work' / 'data' / 'tasks.json'))
    ap.add_argument('--min-reps', type=int, default=3)
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--out', default=str(ROOT / 'results' / 'audits' / 'g1b_agreement'))
    a = ap.parse_args()

    tasks = {t['uid']: t for t in json.loads(Path(a.tasks).read_text())}

    cells = defaultdict(list)
    for line in Path(a.episodes).open():
        r = json.loads(line)
        ds = r.get('decisions') or []
        if not ds:
            continue
        models = {d.get('model_alias') for d in ds if d.get('model_alias')}
        if len(models) > 1:
            continue
        d0 = ds[0]
        val = d0.get('validation') or {}
        nf = val.get('n_fail')
        if nf is None or not (d0.get('code') or '').strip():
            continue
        cells[(r['task_uid'], models.pop() if models else '?')].append({
            'code': d0['code'], 'visible': int(nf == 0),
            'hidden': int(bool(r.get('success_first_candidate')))})
    cells = {k: v for k, v in cells.items() if len(v) >= a.min_reps}

    jobs = []
    skipped = Counter()
    for (uid, m), cands in sorted(cells.items()):
        t = tasks.get(uid)
        if t is None:
            skipped['no_task'] += 1; continue
        pr = probes_for(t)
        if not pr or len(pr) < 2:
            skipped['no_probes'] += 1; continue
        sp = split_assertions(t)
        jobs.append(((uid, m), t['entry_point'], pr, sp['preamble'], cands))
    if a.limit:
        jobs = jobs[:a.limit]
    print('cells: %d usable, skipped %s; probes/cell median %d' %
          (len(jobs), dict(skipped), int(np.median([len(j[2]) for j in jobs])) if jobs else 0))

    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        results = dict(ex.map(run_cell, jobs, chunksize=2))
    el = time.time() - t0
    print('executed %d cells in %.1f s' % (len(results), el))

    by_model = defaultdict(list)
    for j in jobs:
        key, entry, pr, pre, cands = j
        vecs = results.get(key)
        if vecs is None:
            continue
        uid, m = key
        vis = np.array([c['visible'] for c in cands])
        hid = np.array([c['hidden'] for c in cands])
        n = len(cands)
        cnt = Counter(vecs)
        # agreement picker: largest cluster, tie to visible-passing then first
        def pick_agree(idxs):
            sub = Counter(vecs[i] for i in idxs)
            top = max(sub.values())
            cand = [i for i in idxs if sub[vecs[i]] == top]
            for i in cand:
                if vis[i]:
                    return i
            return cand[0]
        all_idx = list(range(n))
        i_ag = pick_agree(all_idx)
        vp = [i for i in all_idx if vis[i]]
        i_av = pick_agree(vp) if vp else pick_agree(all_idx)
        i_vis = int(np.argmax(vis)) if vis.any() else n - 1
        top_frac = max(cnt.values()) / n
        by_model[m].append({
            'uid': uid, 'r': n, 'n_probes': len(pr),
            'n_clusters': len(cnt), 'top_cluster_frac': top_frac,
            'single': float(hid.mean()),
            'visible': int(hid[i_vis]), 'agreement': int(hid[i_ag]),
            'agree_plus_visible': int(hid[i_av]), 'oracle': int(hid.any()),
        })

    out = {'audit': 'G1b_execution_agreement',
           'created_utc': time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()),
           'source': str(a.episodes), 'elapsed_seconds': round(el, 1),
           'cells_usable': len(jobs), 'skipped': dict(skipped), 'receivers': {}}

    for m, rows in sorted(by_model.items()):
        def ms(k):
            v = np.array([r[k] for r in rows], float)
            return {'mean': float(v.mean()), 'se': float(v.std(ddof=1) / np.sqrt(len(v)))}
        res = {'n_tasks': len(rows),
               'mean_probes': float(np.mean([r['n_probes'] for r in rows])),
               'mean_clusters': float(np.mean([r['n_clusters'] for r in rows])),
               'mean_top_cluster_frac': float(np.mean([r['top_cluster_frac'] for r in rows])),
               'single_attempt': ms('single'), 'visible_picker': ms('visible'),
               'agreement_picker': ms('agreement'), 'agree_plus_visible': ms('agree_plus_visible'),
               'oracle': ms('oracle')}
        gap = res['oracle']['mean'] - res['visible_picker']['mean']
        res['selection_gap'] = gap
        for nm, key in (('agreement', 'agreement'), ('agree_plus_visible', 'agree_plus_visible')):
            d = np.array([r[key] - r['visible'] for r in rows], float)
            se = float(d.std(ddof=1) / np.sqrt(len(d)))
            res['%s_minus_visible' % nm] = {
                'delta': float(d.mean()), 'se': se,
                'ci95': [float(d.mean() - 1.96 * se), float(d.mean() + 1.96 * se)],
                'fraction_of_gap': (float(d.mean()) / gap) if gap > 1e-9 else None}
        # is cluster size a usable confidence signal for stopping?
        tf = np.array([r['top_cluster_frac'] for r in rows])
        hv = np.array([r['agree_plus_visible'] for r in rows], float)
        if tf.std() > 1e-9:
            res['corr_topcluster_vs_correct'] = float(np.corrcoef(tf, hv)[0, 1])
            hi, lo = tf >= np.median(tf), tf < np.median(tf)
            res['accuracy_when_cluster_large'] = float(hv[hi].mean())
            res['accuracy_when_cluster_small'] = float(hv[lo].mean())
        out['receivers'][m] = {**res, '_per_task': rows}

    outdir = Path(a.out) / out['created_utc']
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / 'summary.json').write_text(json.dumps(out, indent=2))
    for m, r in out['receivers'].items():
        print('\n=== %s :: %d tasks, %.1f probes, %.2f clusters/task, top cluster %.2f of candidates ==='
              % (m, r['n_tasks'], r['mean_probes'], r['mean_clusters'], r['mean_top_cluster_frac']))
        print('  single %.4f | visible %.4f | AGREEMENT %.4f | AGREE+VIS %.4f | oracle %.4f  (gap %.4f)'
              % (r['single_attempt']['mean'], r['visible_picker']['mean'], r['agreement_picker']['mean'],
                 r['agree_plus_visible']['mean'], r['oracle']['mean'], r['selection_gap']))
        for nm in ('agreement', 'agree_plus_visible'):
            d = r['%s_minus_visible' % nm]
            print('  %-20s - visible = %+.4f [%+.4f, %+.4f]  fraction of gap %s'
                  % (nm, d['delta'], d['ci95'][0], d['ci95'][1],
                     ('%.3f' % d['fraction_of_gap']) if d['fraction_of_gap'] is not None else 'n/a'))
        if 'accuracy_when_cluster_large' in r:
            print('  cluster size as confidence: corr %+.3f ; accuracy large-cluster %.4f vs small-cluster %.4f'
                  % (r['corr_topcluster_vs_correct'], r['accuracy_when_cluster_large'], r['accuracy_when_cluster_small']))
    print('\nwrote', outdir)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
