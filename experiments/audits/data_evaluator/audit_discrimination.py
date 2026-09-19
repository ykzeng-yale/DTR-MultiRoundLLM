#!/usr/bin/env python3
"""Measured additions to the data audits: trivial-pass battery, mutation kill rate,
prompt-literal collision drop. CPU only."""
from __future__ import annotations
import ast, json, re, sys, time, copy
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

ROOT = Path('/Users/yukangzengcmac/DTR-MultiRoundLLM')
sys.path.insert(0, str(ROOT / 'experiments' / 'common'))
from verify import split_tests, verify  # noqa

TASKS = json.load(open(ROOT / 'work' / 'data' / 'tasks.json'))

# ---------------- trivial-pass battery ----------------
STUBS = {
    'none':   "def {ep}(*a, **k):\n    return None\n",
    'zero':   "def {ep}(*a, **k):\n    return 0\n",
    'true':   "def {ep}(*a, **k):\n    return True\n",
    'false':  "def {ep}(*a, **k):\n    return False\n",
    'estr':   "def {ep}(*a, **k):\n    return ''\n",
    'elist':  "def {ep}(*a, **k):\n    return []\n",
    'ident':  "def {ep}(x=None, *a, **k):\n    return x\n",
    'uneq':   ("class _U:\n"
               "    def __eq__(self, o):\n        return True\n"
               "    def __ne__(self, o):\n        return False\n"
               "    def __hash__(self):\n        return 0\n"
               "    def __len__(self):\n        return 0\n"
               "    def __iter__(self):\n        return iter(())\n"
               "    def __contains__(self, o):\n        return True\n"
               "    def __bool__(self):\n        return True\n"
               "    def __getitem__(self, i):\n        return self\n"
               "    def __call__(self, *a, **k):\n        return self\n"
               "def {ep}(*a, **k):\n    return _U()\n"),
}

# ---------------- AST mutations ----------------
class SwapCmp(ast.NodeTransformer):
    MAP = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt,
           ast.Eq: ast.NotEq, ast.NotEq: ast.Eq}
    def __init__(self): self.n = 0
    def visit_Compare(self, node):
        self.generic_visit(node)
        for i, op in enumerate(node.ops):
            t = self.MAP.get(type(op))
            if t is not None and self.n == 0:
                node.ops[i] = t(); self.n += 1
        return node

class OffByOne(ast.NodeTransformer):
    def __init__(self): self.n = 0
    def visit_Constant(self, node):
        if self.n == 0 and isinstance(node.value, int) and not isinstance(node.value, bool):
            self.n += 1
            return ast.copy_location(ast.Constant(value=node.value + 1), node)
        return node

class SwapBool(ast.NodeTransformer):
    def __init__(self): self.n = 0
    def visit_BoolOp(self, node):
        self.generic_visit(node)
        if self.n == 0:
            node.op = ast.Or() if isinstance(node.op, ast.And) else ast.And()
            self.n += 1
        return node

class NegateIf(ast.NodeTransformer):
    def __init__(self): self.n = 0
    def visit_If(self, node):
        self.generic_visit(node)
        if self.n == 0:
            node.test = ast.UnaryOp(op=ast.Not(), operand=node.test)
            ast.fix_missing_locations(node)
            self.n += 1
        return node

class DropLastStmt(ast.NodeTransformer):
    """Remove the last statement of the entry-point function body (if >1 stmt)."""
    def __init__(self, ep): self.ep = ep; self.n = 0
    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        if node.name == self.ep and self.n == 0 and len(node.body) > 1:
            node.body = node.body[:-1]
            if not node.body:
                node.body = [ast.Pass()]
            ast.fix_missing_locations(node)
            self.n += 1
        return node

class SwapArgs(ast.NodeTransformer):
    """Swap the first two parameters of the entry point (argument-order bug)."""
    def __init__(self, ep): self.ep = ep; self.n = 0
    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        if node.name == self.ep and self.n == 0 and len(node.args.args) >= 2:
            node.args.args[0], node.args.args[1] = node.args.args[1], node.args.args[0]
            self.n += 1
        return node

class ArithFlip(ast.NodeTransformer):
    MAP = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.FloorDiv}
    def __init__(self): self.n = 0
    def visit_BinOp(self, node):
        self.generic_visit(node)
        t = self.MAP.get(type(node.op))
        if t is not None and self.n == 0:
            node.op = t(); self.n += 1
        return node


def mutants(ref: str, ep: str) -> dict:
    try:
        base = ast.parse(ref)
    except SyntaxError:
        return {}
    out = {}
    makers = {'cmp': lambda: SwapCmp(), 'int1': lambda: OffByOne(), 'bool': lambda: SwapBool(),
              'negif': lambda: NegateIf(), 'droplast': lambda: DropLastStmt(ep),
              'swapargs': lambda: SwapArgs(ep), 'arith': lambda: ArithFlip()}
    for name, mk in makers.items():
        tree = copy.deepcopy(base)
        m = mk()
        tree = m.visit(tree)
        if m.n == 0:
            continue
        ast.fix_missing_locations(tree)
        try:
            src = ast.unparse(tree)
        except Exception:
            continue
        if src.strip() == ast.unparse(base).strip():
            continue
        out[name] = src
    return out


# ---------------- prompt-literal collision (HumanEval) ----------------
def he_asserts(test_src: str):
    """Return list of (assert_source, [literal reprs of call args]) from check()."""
    try:
        tree = ast.parse(test_src)
    except SyntaxError:
        return []
    fn = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'check'), None)
    if fn is None:
        return []
    res = []
    for st in fn.body:
        if not isinstance(st, ast.Assert):
            continue
        lits = []
        for call in [n for n in ast.walk(st) if isinstance(n, ast.Call)]:
            f = call.func
            nm = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else '')
            if nm != 'candidate':
                continue
            for a in call.args:
                try:
                    lits.append(ast.unparse(a))
                except Exception:
                    pass
        res.append((ast.unparse(st), lits))
    return res


def norm(s: str) -> str:
    return re.sub(r'\s+', '', s)


def collide(lits, prompt_norm) -> bool:
    """True iff EVERY call-arg literal of this assert already appears in the prompt."""
    if not lits:
        return False
    return all(len(norm(l)) >= 2 and norm(l) in prompt_norm for l in lits)


# ---------------- workers ----------------
def job_stub(args):
    uid, kind, code = args
    task = next(t for t in TASKS if t['uid'] == uid)
    ht = split_tests(task)['hidden_task']
    r = verify(ht, code, timeout_s=10.0)
    return (uid, kind, bool(r['success']))


def job_mut(args):
    uid, kind, code = args
    task = next(t for t in TASKS if t['uid'] == uid)
    ht = split_tests(task)['hidden_task']
    r = verify(ht, code, timeout_s=10.0)
    return (uid, kind, bool(r['success']))


def main():
    t0 = time.time()
    # ---- MBPP structural re-verification ----
    mb = [t for t in TASKS if t['benchmark'] == 'mbpp']
    he = [t for t in TASKS if t['benchmark'] == 'humaneval']
    sig_eq = sum(1 for t in mb if t['signature_example'].strip() == t['test_list'][0].strip())
    chal_empty = sum(1 for t in mb if not t.get('challenge_test_list'))
    hidden_counts = {}
    for t in mb:
        n = len(t['test_list']) - 1
        hidden_counts[n] = hidden_counts.get(n, 0) + 1
    print('MBPP signature_example == test_list[0]: %d/%d' % (sig_eq, len(mb)))
    print('MBPP challenge_test_list empty: %d/%d' % (chal_empty, len(mb)))
    print('MBPP hidden-assert count histogram (after carving visible):', dict(sorted(hidden_counts.items())))

    # ---- HumanEval assert counts and prompt-literal collisions ----
    he_stats = []
    for t in he:
        aa = he_asserts(t['test'])
        pn = norm(t['prompt'])
        nc = sum(1 for _, lits in aa if collide(lits, pn))
        he_stats.append((t['uid'], len(aa), nc, len(aa) - nc))
    tot = sum(a for _, a, _, _ in he_stats)
    totc = sum(c for _, _, c, _ in he_stats)
    import statistics as st
    surv = [s for _, _, _, s in he_stats]
    print('\nHumanEval: %d tasks, %d total check-asserts, mean %.1f, median %d' %
          (len(he), tot, tot / len(he), st.median([a for _, a, _, _ in he_stats])))
    print('HumanEval asserts whose EVERY call-arg literal appears in the prompt: %d (%.3f of all)' % (totc, totc / tot))
    print('HumanEval tasks with >=1 such assert: %d/%d' % (sum(1 for _, _, c, _ in he_stats if c), len(he)))
    print('HumanEval surviving-assert distribution after drop: min %d, median %d, mean %.1f' %
          (min(surv), st.median(surv), sum(surv) / len(surv)))
    for k in (0, 1, 2, 3):
        print('  tasks with exactly %d surviving asserts: %d' % (k, sum(1 for s in surv if s == k)))
    print('  tasks with <2 surviving asserts: %d' % sum(1 for s in surv if s < 2))
    json.dump(he_stats, open('/private/tmp/claude-501/-Users-yukangzengcmac-DTR-MultiRoundLLM/becb2798-9298-4306-8e12-77f81520493f/scratchpad/he_assert_stats.json', 'w'))

    # ---- trivial-pass battery ----
    jobs = []
    for t in TASKS:
        ep = t.get('entry_point') or 'f'
        for kind, tmpl in STUBS.items():
            jobs.append((t['uid'], kind, tmpl.format(ep=ep)))
    print('\ntrivial-pass battery: %d verifications...' % len(jobs))
    passes = {}
    per_task_pass = {}
    with ProcessPoolExecutor(max_workers=8) as ex:
        for uid, kind, ok in ex.map(job_stub, jobs, chunksize=16):
            if ok:
                passes.setdefault(kind, []).append(uid)
                per_task_pass.setdefault(uid, []).append(kind)
    print('stub pass counts (out of 591):')
    for kind in STUBS:
        u = passes.get(kind, [])
        print('  %-9s %3d  %s' % (kind, len(u), ','.join(sorted(u)[:8])))
    print('tasks passed by ANY stub: %d  -> %s' % (len(per_task_pass), json.dumps({k: v for k, v in sorted(per_task_pass.items())})[:1200]))
    json.dump(per_task_pass, open('/private/tmp/claude-501/-Users-yukangzengcmac-DTR-MultiRoundLLM/becb2798-9298-4306-8e12-77f81520493f/scratchpad/stub_pass.json', 'w'))
    print('elapsed %.1fs' % (time.time() - t0))

    # ---- mutation kill rate ----
    mjobs = []
    mcount = {}
    for t in TASKS:
        ms = mutants(t['reference'], t.get('entry_point') or '')
        mcount[t['uid']] = len(ms)
        for kind, src in ms.items():
            mjobs.append((t['uid'], kind, src))
    print('\nmutation battery: %d mutants over %d tasks (%.1f per task)...' %
          (len(mjobs), sum(1 for v in mcount.values() if v), len(mjobs) / max(1, sum(1 for v in mcount.values() if v))))
    surv_m = {}
    tot_m = {}
    with ProcessPoolExecutor(max_workers=8) as ex:
        for uid, kind, ok in ex.map(job_mut, mjobs, chunksize=16):
            tot_m.setdefault(uid, []).append(kind)
            if ok:  # mutant PASSED hidden tests -> survived -> tests failed to discriminate
                surv_m.setdefault(uid, []).append(kind)
    nm = len(mjobs)
    ns = sum(len(v) for v in surv_m.values())
    print('mutants surviving (hidden tests failed to kill): %d/%d = %.4f' % (ns, nm, ns / nm))
    print('kill rate = %.4f' % (1 - ns / nm))
    bykind = {}
    for uid, kinds in surv_m.items():
        for k in kinds:
            bykind[k] = bykind.get(k, 0) + 1
    bytot = {}
    for uid, kinds in tot_m.items():
        for k in kinds:
            bytot[k] = bytot.get(k, 0) + 1
    print('survival by mutation kind:')
    for k in sorted(bytot):
        print('  %-9s %4d/%4d = %.3f' % (k, bykind.get(k, 0), bytot[k], bykind.get(k, 0) / bytot[k]))
    # per-task kill rate distribution
    kr = []
    for uid, kinds in tot_m.items():
        s = len(surv_m.get(uid, []))
        kr.append((uid, 1 - s / len(kinds), len(kinds), s))
    kr.sort(key=lambda x: x[1])
    print('tasks with kill rate < 1.0: %d/%d' % (sum(1 for _, r, _, _ in kr if r < 1.0), len(kr)))
    print('tasks with kill rate <= 0.5: %d' % sum(1 for _, r, _, _ in kr if r <= 0.5))
    print('tasks with kill rate == 0.0: %d  -> %s' % (sum(1 for _, r, _, _ in kr if r == 0.0),
          [u for u, r, _, _ in kr if r == 0.0][:20]))
    by_bench = {}
    for uid, r, n, s in kr:
        b = uid.split('/')[0]
        by_bench.setdefault(b, []).append(r)
    for b, v in by_bench.items():
        print('  %s: mean kill rate %.4f over %d tasks' % (b, sum(v) / len(v), len(v)))
    json.dump(kr, open('/private/tmp/claude-501/-Users-yukangzengcmac-DTR-MultiRoundLLM/becb2798-9298-4306-8e12-77f81520493f/scratchpad/mutation_kill.json', 'w'))
    print('\ntotal elapsed %.1fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
