# Audit A1 run directories

Runs are immutable and are never overwritten. Where an earlier run used code that
was later found to be wrong, it is kept and marked superseded here, with the
defect stated.

| run | status | note |
|---|---|---|
| `20260919T214150Z` | **superseded** | S6 measured the visible share of the *whole* `reference`. All 164 HumanEval `reference` fields literally begin with their `prompt`, so the metric read ~0.75 by construction and wrongly flagged 149 tasks as mostly-visible. S1–S5 in this run are unaffected. |
| `20260919T214314Z` | **superseded** | S6 fixed (share of the solution *body*). S5 still gated at exactly zero stub-passing tasks, so the audit exited non-zero on a single excludable task rather than on a pool defect. |
| `20260919T214348Z` | **authoritative** | S6 on the solution body; S5 gated on the stub-passing *rate* (≤1%, excluded rather than fatal); S6 added as a gate. |

## What the authoritative run establishes

* 591/591 benchmark references pass their own full assertion set in the Seatbelt
  sandbox, and 591/591 still pass after the visible assertion is carved out. The
  outcome is therefore well defined and the visible/hidden split does not break
  the harness.
* The MBPP visible assertion is identifiable as `test_list[0]` for all 427 tasks
  (`signature_example` is exactly that string), so the one assertion shown to the
  receiver can be excluded from grading and an intervention can be audited
  mechanically for quoting a *graded* assertion.
* `mbpp/794` is excluded: its two hidden assertions are both `assert not f(...)`,
  which a `return None` stub satisfies. Carving out the visible assertion can
  destroy a task's discriminating power, so S5 must be evaluated on the
  hidden-only program — not on the full set — for every task pool used here.
* Leakage surface before any intervention is sent: the median share of the
  solution body already visible in prompt + visible assertion is 0.12 (MBPP 0.14,
  HumanEval 0.08), and no task exceeds 0.60.

**Usable pool: 590 tasks** (`usable_uids.json` in the authoritative run).

## Superseded by a later correction (2026-09-19)

A1's discrimination check S5 used a single `return None` stub and is **too weak**. A
trivial-stub battery finds 22 such tasks rather than 1, and a universal-equality-dunder
candidate passes 555–557 of 591. See the correction section at the end of
`docs/audits.md` and `experiments/common/integrity.py`. The run directories here are
left unamended because they record what was measured at the time; the usable pool of
590 stated above is superseded by POOL A = 564, and by 230 after intersecting with the
informative difficulty band.
