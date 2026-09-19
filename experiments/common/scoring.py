"""Visible/hidden assertion split, at assertion level, for both benchmarks.

Why this module replaces `verify.split_tests` for design purposes
----------------------------------------------------------------
Two things are needed of a task in this project, and they are in tension:

* the **intervener** must be able to see *some* verdict on the receiver's attempt,
  because an intervention round with no external evidence is closed off by the
  self-correction literature -- a model critiquing itself with nothing to go on
  degrades rather than improves;
* the **outcome** must be graded on assertions no intervention can ever reveal,
  or "more informative feedback works better" is true by construction.

`verify.split_tests` gave MBPP exactly that (the one assertion shown in the prompt
is `test_list[0]`, so grade on `test_list[1:]`), but treated HumanEval's `check`
function as one opaque unit. That left HumanEval with **no** intervener-observable
verdict and a hidden-assertion count of 1, which blocks any design that conditions
on an observed verdict -- 164 of 591 tasks, and only 76 of those have a `>>>`
doctest from which a check could be scavenged.

The fix here makes the two benchmarks structurally identical instead of excluding
the 88 HumanEval tasks without doctests: parse `check` into its individual
assertions, drop any assertion the prompt's own docstring already reveals, then
hold out the first of the remainder as visible and grade on the rest.

Measured on the 591-task pool (see `audit_scoring_split.py`): 158/164 HumanEval
`check` bodies are pure assertion lists and can be split; the other 6 wrap their
assertions in a `for` loop and are indivisible.
"""
from __future__ import annotations

import ast
import re

__all__ = ['check_asserts', 'revealed_by_prompt', 'split_assertions', 'SplitResult']


def _norm(s: str) -> str:
    return re.sub(r'\s+', '', s or '')


def check_asserts(task: dict) -> list | None:
    """Top-level assertions of a HumanEval `check` function, as source strings.

    Returns None when the body is not a flat list of assertions (and statements
    that cannot themselves fail, such as imports and assignments) -- those tasks
    hide assertions inside control flow and cannot be split without changing what
    is being tested.
    """
    if task['benchmark'] != 'humaneval':
        raise ValueError('check_asserts is for humaneval only')
    try:
        tree = ast.parse(task['test'])
    except SyntaxError:
        return None
    fns = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'check']
    if not fns:
        return None
    body = fns[0].body
    inert = (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign, ast.Pass)
    for n in body:
        if isinstance(n, ast.Assert) or isinstance(n, inert):
            continue
        if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant):
            continue          # a docstring
        return None           # For / While / If / Try / a real expression: indivisible
    asserts = [ast.unparse(n) for n in body if isinstance(n, ast.Assert)]
    preamble = [ast.unparse(n) for n in body if isinstance(n, inert)]
    return {'asserts': asserts, 'preamble': preamble} if asserts else None


def revealed_by_prompt(assert_src: str, prompt: str) -> bool:
    """True when the prompt's docstring already shows this assertion's inputs.

    HumanEval prompts frequently contain `>>>` examples, and 76 of 164 do. An
    assertion over inputs the prompt already displays is not hidden in any useful
    sense, so it must not be graded as if it were. The test is deliberately crude
    and one-sided: it compares the rendered argument list of the call against the
    whitespace-stripped prompt, so it over-detects rather than under-detects.
    """
    p = _norm(prompt)
    if not p:
        return False
    try:
        node = ast.parse(assert_src).body[0]
    except SyntaxError:
        return False
    for call in ast.walk(node):
        if isinstance(call, ast.Call) and call.args:
            args = _norm(', '.join(ast.unparse(a) for a in call.args))
            if len(args) >= 3 and args in p:
                return True
    return False


class SplitResult(dict):
    """dict with attribute access, so callers can read r.visible as well as r['visible']."""
    __getattr__ = dict.get


def split_assertions(task: dict) -> SplitResult:
    """Split a task's assertions into visible (shown to the intervener) and hidden
    (graded). Uniform across benchmarks.

    Returns SplitResult with:
      splittable      whether an assertion-level split was possible at all
      visible         list of assertion sources the intervener may see
      hidden          list of assertion sources used for grading
      preamble        statements that must precede the assertions (HumanEval imports)
      n_hidden        len(hidden)
      dropped_revealed  assertions excluded because the prompt already reveals them
      u_source        how the intervener's verdict is derived
      usable          n_hidden >= 1 and splittable
    """
    if task['benchmark'] == 'mbpp':
        tests = list(task['test_list'])
        extra = list(task.get('challenge_test_list') or [])
        return SplitResult(splittable=True, visible=tests[:1], hidden=tests[1:] + extra,
                           preamble=list(task.get('test_imports') or []),
                           n_hidden=len(tests[1:] + extra), dropped_revealed=[],
                           u_source='visible_assert', usable=len(tests[1:] + extra) >= 1)
    if task['benchmark'] != 'humaneval':
        raise ValueError(task['benchmark'])

    ca = check_asserts(task)
    if ca is None:
        # `check` hides its assertions inside control flow: grade it whole, and the
        # intervener gets no assertion-level verdict.
        return SplitResult(splittable=False, visible=[], hidden=['<check>'], preamble=[],
                           n_hidden=1, dropped_revealed=[], u_source='none', usable=False)
    asserts, preamble = ca['asserts'], ca['preamble']
    revealed = [a for a in asserts if revealed_by_prompt(a, task['prompt'])]
    remaining = [a for a in asserts if a not in revealed]
    if not remaining:
        # everything the check tests is already displayed in the prompt
        return SplitResult(splittable=True, visible=list(asserts[:1]), hidden=[], preamble=preamble,
                           n_hidden=0, dropped_revealed=revealed, u_source='visible_assert',
                           usable=False)
    return SplitResult(splittable=True, visible=remaining[:1], hidden=remaining[1:],
                       preamble=preamble, n_hidden=len(remaining[1:]),
                       dropped_revealed=revealed, u_source='visible_assert',
                       usable=len(remaining[1:]) >= 1)
