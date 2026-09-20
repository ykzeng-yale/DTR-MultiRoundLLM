#!/usr/bin/env python3
"""(a) final pool composition after all exclusions; (b) P-suite (contamination probe)
constructibility: rename the entry point + parameters, rewrite the hidden tests to match,
and check the reference still passes. CPU only."""
from __future__ import annotations
import ast, json, re, sys, time, hashlib
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

ROOT = Path('/Users/yukangzengcmac/DTR-MultiRoundLLM')
SCR = Path('/private/tmp/claude-501/-Users-yukangzengcmac-DTR-MultiRoundLLM/becb2798-9298-4306-8e12-77f81520493f/scratchpad')
sys.path.insert(0, str(ROOT / 'experiments' / 'common'))
from verify import split_tests, verify  # noqa

TASKS = json.load(open(ROOT / 'work' / 'data' / 'tasks.json'))
BYUID = {t['uid']: t for t in TASKS}

stub_pass = json.load(open(SCR / 'stub_pass.json'))
mut = json.load(open(SCR / 'mutation_kill.json'))          # [uid, killrate, n, nsurv]
he_stats = json.load(open(SCR / 'he_assert_stats.json'))   # [uid, n, ncollide, nsurv]
diff = json.load(open(ROOT / 'results/audits/difficulty/20260919T215634Z/per_task.json'))
informative = set(json.load(open(ROOT / 'results/audits/difficulty/20260919T215634Z/pool_informative.json')))

killrate = {u: r for u, r, n, s in mut}
nmut = {u: n for u, r, n, s in mut}
he_surv = {u: s for u, n, c, s in he_stats}

# ---- exclusion sets ----
E_stub = {u for u, kinds in stub_pass.items() if [k for k in kinds if k != 'uneq']}
E_he_thin = {u for u, s in he_surv.items() if s < 2}
E_kill0 = {u for u, r in killrate.items() if r == 0.0}
E_kill50 = {u for u, r in killrate.items() if r <= 0.5}
E_nomut = {t['uid'] for t in TASKS if t['uid'] not in killrate}   # no mutant constructible -> untested

print('exclusion sets')
print('  E_stub  (passed by a non-eq trivial stub)        %3d  %s' % (len(E_stub), sorted(E_stub)))
print('  E_he_thin (HumanEval <2 asserts after prompt-lit drop) %3d  %s' % (len(E_he_thin), sorted(E_he_thin)))
print('  E_kill0 (mutation kill rate 0.00)               %3d  %s' % (len(E_kill0), sorted(E_kill0)))
print('  E_kill50 (mutation kill rate <=0.50)            %3d' % len(E_kill50))
print('  E_nomut (no mutant constructible -> untestable)  %3d  %s' % (len(E_nomut), sorted(E_nomut)[:20]))

pool_A = {t['uid'] for t in TASKS} - E_stub - E_he_thin - E_kill0
pool_B = pool_A - E_kill50
print('\nPOOL A (drop stub-passable, thin-HE, kill-rate-0):            %d' % len(pool_A))
print('POOL B (A, also drop kill-rate<=0.50):                        %d' % len(pool_B))
print('POOL A INTERSECT informative(0.1-0.9, n=%d):                  %d' % (len(informative), len(pool_A & informative)))
print('POOL B INTERSECT informative:                                 %d' % len(pool_B & informative))
for nm, P in (('A', pool_A), ('B', pool_B)):
    ii = P & informative
    print('  pool %s informative by benchmark: mbpp %d, humaneval %d' % (
        nm, sum(1 for u in ii if u.startswith('mbpp')), sum(1 for u in ii if u.startswith('humaneval'))))

# per-task 3B rate for the surviving informative pool
r3 = {d['uid']: d.get('qwen2.5-3b-instruct_rate') for d in diff}
ii = sorted(pool_A & informative)
band = {}
for u in ii:
    v = r3.get(u)
    if v is None:
        band['no3b'] = band.get('no3b', 0) + 1
        continue
    k = '%.2f' % v
    band[k] = band.get(k, 0) + 1
print('\n3B first-attempt rate histogram over POOL A ∩ informative (n=%d): %s' % (len(ii), dict(sorted(band.items()))))
json.dump(sorted(pool_A), open(SCR / 'pool_A.json', 'w'))
json.dump(sorted(pool_A & informative), open(SCR / 'pool_A_informative.json', 'w'))


# ================= P-suite: rename perturbation =================
KEYWORDS = set(__import__('keyword').kwlist)


def new_name(old: str, salt: str) -> str:
    h = hashlib.sha256((old + salt).encode()).hexdigest()[:6]
    return 'fn_%s' % h


def rename_task(task: dict):
    """Return (new_task, mapping) with entry point and its parameters renamed opaquely.
    Hidden tests are rewritten by AST-level Name substitution, never by regex."""
    ep = task.get('entry_point')
    if not ep:
        return None, None
    try:
        rtree = ast.parse(task['reference'])
    except SyntaxError:
        return None, None
    fn = next((n for n in ast.walk(rtree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == ep), None)
    if fn is None:
        return None, None
    mapping = {ep: new_name(ep, task['uid'])}
    for i, a in enumerate(fn.args.args):
        if a.arg in KEYWORDS or a.arg == 'self':
            continue
        mapping[a.arg] = 'p%d_%s' % (i, hashlib.sha256((a.arg + task['uid']).encode()).hexdigest()[:4])

    class Ren(ast.NodeTransformer):
        def visit_Name(self, n):
            if n.id in mapping:
                n.id = mapping[n.id]
            return n
        def visit_arg(self, n):
            if n.arg in mapping:
                n.arg = mapping[n.arg]
            return n
        def visit_FunctionDef(self, n):
            self.generic_visit(n)
            if n.name in mapping:
                n.name = mapping[n.name]
            return n
        def visit_keyword(self, n):
            self.generic_visit(n)
            if n.arg in mapping:
                n.arg = mapping[n.arg]
            return n

    try:
        newref = ast.unparse(Ren().visit(rtree))
    except Exception:
        return None, None
    nt = dict(task)
    nt['reference'] = newref
    nt['entry_point'] = mapping[ep]
    # docstring / prompt: strip the old name textually (prompt is model-facing, not executed)
    nt['prompt'] = task['prompt'].replace(ep, mapping[ep])
    if task['benchmark'] == 'mbpp':
        newtests = []
        for a in task['test_list']:
            try:
                newtests.append(ast.unparse(Ren().visit(ast.parse(a))))
            except SyntaxError:
                return None, None
        nt['test_list'] = newtests
        nt['signature_example'] = newtests[0]
    else:
        try:
            nt['test'] = ast.unparse(Ren().visit(ast.parse(task['test'])))
        except SyntaxError:
            return None, None
    return nt, mapping


def job(uid):
    t = BYUID[uid]
    nt, mp = rename_task(t)
    if nt is None:
        return (uid, 'unbuildable', False, 0)
    r = verify(split_tests(nt)['hidden_task'], nt['reference'], timeout_s=10.0)
    return (uid, 'ok', bool(r['success']), len(mp))


def main():
    t0 = time.time()
    uids = [t['uid'] for t in TASKS]
    res = []
    with ProcessPoolExecutor(max_workers=8) as ex:
        for row in ex.map(job, uids, chunksize=8):
            res.append(row)
    unb = [u for u, s, ok, n in res if s != 'ok']
    built = [r for r in res if r[1] == 'ok']
    passing = [u for u, s, ok, n in built if ok]
    print('\n=== P-suite (opaque rename of entry point + parameters) ===')
    print('constructible: %d/591; reference still passes renamed hidden tests: %d/%d (%.3f)' % (
        len(built), len(passing), len(built), len(passing) / len(built)))
    print('unbuildable: %d %s' % (len(unb), unb[:20]))
    fail = [u for u, s, ok, n in built if not ok]
    print('built but reference FAILS after rename: %d %s' % (len(fail), fail[:20]))
    print('mean identifiers renamed per task: %.1f' % (sum(n for _, _, _, n in built) / len(built)))
    ok_set = set(passing)
    print('P-suite valid AND in POOL A ∩ informative: %d' % len(ok_set & set(json.load(open(SCR / 'pool_A_informative.json')))))
    json.dump(sorted(ok_set), open(SCR / 'psuite_ok.json', 'w'))
    print('P-suite build+verify wall: %.1fs CPU-seconds-of-wall on 8 workers' % (time.time() - t0))


if __name__ == '__main__':
    main()
