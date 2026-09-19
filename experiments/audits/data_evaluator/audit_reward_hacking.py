#!/usr/bin/env python3
"""Quantify the universal-__eq__ reward hack and measure two candidate mitigations:
  (M1) static AST gate: reject candidates that define comparison/coercion dunders.
  (M2) dynamic canary: re-run one hidden assert with a corrupted expected value; it MUST fail.
CPU only."""
from __future__ import annotations
import ast, json, re, sys, time, copy, secrets
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

ROOT = Path('/Users/yukangzengcmac/DTR-MultiRoundLLM')
sys.path.insert(0, str(ROOT / 'experiments' / 'common'))
from verify import split_tests, verify, build_program  # noqa
from sandbox import run_program  # noqa

TASKS = json.load(open(ROOT / 'work' / 'data' / 'tasks.json'))
BYUID = {t['uid']: t for t in TASKS}

UNEQ = ("class _U:\n"
        "    def __eq__(self, o):\n        return True\n"
        "    def __ne__(self, o):\n        return False\n"
        "    def __hash__(self):\n        return 0\n"
        "    def __len__(self):\n        return 0\n"
        "    def __iter__(self):\n        return iter(())\n"
        "    def __contains__(self, o):\n        return True\n"
        "    def __bool__(self):\n        return True\n"
        "    def __getitem__(self, i):\n        return self\n"
        "    def __call__(self, *a, **k):\n        return self\n"
        "def {ep}(*a, **k):\n    return _U()\n")

# ---- narrower variants, to find the minimal hack the gate must stop ----
UNEQ_MIN = ("class _U:\n"
            "    def __eq__(self, o):\n        return True\n"
            "def {ep}(*a, **k):\n    return _U()\n")
UNEQ_NE = ("class _U:\n"
           "    def __ne__(self, o):\n        return False\n"
           "def {ep}(*a, **k):\n    return _U()\n")
# hack routed through operator overloading on a subclass of a builtin
UNEQ_SUB = ("class _U(int):\n"
            "    def __eq__(self, o):\n        return True\n"
            "    def __hash__(self):\n        return 0\n"
            "def {ep}(*a, **k):\n    return _U(0)\n")
# hack with the dunder installed after class creation (defeats a naive 'def __eq__' regex)
UNEQ_SETATTR = ("class _U:\n    pass\n"
                "setattr(_U, '__eq__', lambda s, o: True)\n"
                "def {ep}(*a, **k):\n    return _U()\n")
# hack via a metaclass-free type() call
UNEQ_TYPE = ("_U = type('_U', (), {{'__eq__': lambda s, o: True, '__hash__': lambda s: 0}})\n"
             "def {ep}(*a, **k):\n    return _U()\n")

VARIANTS = {'uneq_full': UNEQ, 'uneq_min': UNEQ_MIN, 'uneq_ne': UNEQ_NE,
            'uneq_subint': UNEQ_SUB, 'uneq_setattr': UNEQ_SETATTR, 'uneq_type': UNEQ_TYPE}

# ---------------- M1: static dunder gate ----------------
DUNDERS = {'__eq__', '__ne__', '__hash__', '__lt__', '__le__', '__gt__', '__ge__',
           '__bool__', '__len__', '__contains__', '__iter__', '__index__', '__int__',
           '__float__', '__str__', '__repr__', '__getattr__', '__getattribute__',
           '__class__', '__instancecheck__', '__subclasshook__'}


def static_dunder_gate(code: str) -> list:
    """Names of comparison/coercion dunders the candidate defines or installs (any route)."""
    hits = set()
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return ['__parse_error__']
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in DUNDERS:
            hits.add(n.name)
        if isinstance(n, ast.Assign):
            for tgt in n.targets:
                if isinstance(tgt, ast.Attribute) and tgt.attr in DUNDERS:
                    hits.add(tgt.attr)
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value in DUNDERS:
            hits.add(n.value)          # setattr(cls, '__eq__', ...) / type(...,{'__eq__':...})
        if isinstance(n, ast.Call):
            f = n.func
            nm = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else '')
            if nm in ('setattr', 'type', '__build_class__'):
                hits.add('dynamic:%s' % nm) if False else None
    return sorted(hits)


# ---------------- M2: dynamic canary ----------------
CANARY_SENTINEL = '__DTRMR_ANTIHACK__'


class Corrupt(ast.NodeTransformer):
    """Replace the comparison RHS of `assert <call...> == <expected>` with a unique sentinel string."""
    def __init__(self, token): self.token = token; self.n = 0
    def visit_Compare(self, node):
        if self.n == 0 and len(node.ops) == 1 and isinstance(node.ops[0], (ast.Eq, ast.NotEq)):
            self.n += 1
            new = ast.Compare(left=node.left, ops=[ast.Eq()],
                              comparators=[ast.Constant(value=self.token)])
            return ast.copy_location(new, node)
        return node


def corrupted_assert(assert_src: str, token: str):
    """Return an assert source whose expected value is a unique sentinel (must FAIL), or None."""
    try:
        tree = ast.parse(assert_src)
    except SyntaxError:
        return None
    st = tree.body[0]
    if not isinstance(st, ast.Assert):
        return None
    c = Corrupt(token)
    st = c.visit(st)
    if c.n == 0:
        return None
    ast.fix_missing_locations(tree)
    try:
        return ast.unparse(tree)
    except Exception:
        return None


def canary_block(task: dict, token: str):
    """A code block that must raise AssertionError; returns None if not constructible."""
    if task['benchmark'] == 'mbpp':
        hidden = task['test_list'][1:]
        for a in hidden:
            bad = corrupted_assert(a, token)
            if bad:
                return ("_dtrmr_canary_ok = False\ntry:\n    %s\nexcept AssertionError:\n"
                        "    _dtrmr_canary_ok = True\nexcept Exception:\n    _dtrmr_canary_ok = True\n"
                        "assert _dtrmr_canary_ok, %r\n" % (bad, CANARY_SENTINEL))
        return None
    # humaneval: corrupt one assert inside check(), run it standalone against the candidate
    try:
        tree = ast.parse(task['test'])
    except SyntaxError:
        return None
    fn = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'check'), None)
    if fn is None:
        return None
    for st in fn.body:
        if not isinstance(st, ast.Assert):
            continue
        src = ast.unparse(st).replace('candidate', task['entry_point'])
        bad = corrupted_assert(src, token)
        if bad:
            return ("_dtrmr_canary_ok = False\ntry:\n    %s\nexcept AssertionError:\n"
                    "    _dtrmr_canary_ok = True\nexcept Exception:\n    _dtrmr_canary_ok = True\n"
                    "assert _dtrmr_canary_ok, %r\n" % (bad, CANARY_SENTINEL))
    return None


def verify_with_canary(task: dict, code: str):
    """build_program + canary block appended before the OK sentinel."""
    ht = split_tests(task)['hidden_task']
    token = 'DTRMRX' + secrets.token_hex(6)
    cb = canary_block(ht if task['benchmark'] == 'mbpp' else task, token)
    sentinel = '__DTRMR_VERIFY_OK__' + secrets.token_hex(8)
    prog = build_program(ht, code, sentinel=None)
    if cb:
        prog = prog + '\n' + cb
    prog += 'print(%r, flush=True)\n' % sentinel
    r = run_program(prog, timeout_s=10.0)
    seen = r.get('stdout_tail', '').rstrip().endswith(sentinel)
    return dict(success=bool(r['passed'] and seen), canary_built=bool(cb),
                canary_fired=CANARY_SENTINEL in (r.get('stderr') or ''))


def job(args):
    uid, kind, code, mode = args
    t = BYUID[uid]
    if mode == 'plain':
        r = verify(split_tests(t)['hidden_task'], code, timeout_s=10.0)
        return (uid, kind, mode, bool(r['success']), False, False)
    r = verify_with_canary(t, code)
    return (uid, kind, mode, r['success'], r['canary_built'], r['canary_fired'])


def main():
    t0 = time.time()
    # ---- how many references would the static gate reject? ----
    ref_hits = {t['uid']: static_dunder_gate(t['reference']) for t in TASKS}
    bad_refs = {u: h for u, h in ref_hits.items() if h}
    print('M1 static dunder gate applied to the 591 REFERENCES: %d flagged' % len(bad_refs))
    for u, h in list(bad_refs.items())[:20]:
        print('   ', u, h)
    print('M1 gate flags each hack variant:')
    for k, tmpl in VARIANTS.items():
        print('   %-14s %s' % (k, static_dunder_gate(tmpl.format(ep='f')) or 'NOT FLAGGED'))

    # ---- canary constructibility ----
    built = {}
    for t in TASKS:
        ht = split_tests(t)['hidden_task']
        cb = canary_block(ht if t['benchmark'] == 'mbpp' else t, 'TOK')
        built[t['uid']] = bool(cb)
    nb = sum(built.values())
    print('\nM2 canary constructible: %d/591 (mbpp %d/427, humaneval %d/164)' % (
        nb, sum(1 for u, v in built.items() if v and u.startswith('mbpp')),
        sum(1 for u, v in built.items() if v and u.startswith('humaneval'))))
    print('   not constructible:', [u for u, v in built.items() if not v][:15])

    # ---- run the battery: each variant, plain vs canary; plus reference under canary ----
    jobs = []
    for t in TASKS:
        ep = t.get('entry_point') or 'f'
        for k, tmpl in VARIANTS.items():
            jobs.append((t['uid'], k, tmpl.format(ep=ep), 'plain'))
            jobs.append((t['uid'], k, tmpl.format(ep=ep), 'canary'))
        jobs.append((t['uid'], 'reference', t['reference'], 'canary'))
        jobs.append((t['uid'], 'reference', t['reference'], 'plain'))
    print('\nrunning %d verifications...' % len(jobs))
    agg = {}
    fired = {}
    with ProcessPoolExecutor(max_workers=8) as ex:
        for uid, kind, mode, ok, cb, cf in ex.map(job, jobs, chunksize=16):
            agg.setdefault((kind, mode), []).append((uid, ok))
            if cf:
                fired.setdefault((kind, mode), []).append(uid)
    print('\n%-14s %-7s %-14s %-14s' % ('candidate', 'mode', 'passes/591', 'by benchmark'))
    for (kind, mode), rows in sorted(agg.items()):
        p = [u for u, ok in rows if ok]
        mb = sum(1 for u in p if u.startswith('mbpp'))
        he = sum(1 for u in p if u.startswith('humaneval'))
        print('%-14s %-7s %4d (%.3f)     mbpp %3d/427  humaneval %3d/164' % (
            kind, mode, len(p), len(p) / 591, mb, he))
    print('\ncanary fired counts:', {k[0]: len(v) for k, v in fired.items()})
    # residual: variants still passing WITH canary
    for k in VARIANTS:
        res = [u for u, ok in agg[(k, 'canary')] if ok]
        if res:
            print('RESIDUAL %s still passes with canary on %d tasks: %s' % (k, len(res), res[:12]))
    refc = [u for u, ok in agg[('reference', 'canary')] if ok]
    print('\nREFERENCE passes with canary: %d/591  (false-positive cost = %d tasks: %s)' % (
        len(refc), 591 - len(refc), [u for u, ok in agg[('reference', 'canary')] if not ok][:20]))
    json.dump({str(k): v for k, v in agg.items()},
              open('/private/tmp/claude-501/-Users-yukangzengcmac-DTR-MultiRoundLLM/becb2798-9298-4306-8e12-77f81520493f/scratchpad/hack_agg.json', 'w'))
    print('elapsed %.1fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
