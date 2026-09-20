# G1a′ pilot — cheap policy-observable features recover **none** of the selection headroom

> **Historical snapshot; conclusions require the 2026-09-20 corrections.** Read [continuation report](continuation_report_20260920.md), [theory reconciliation](theory_reconciliation_20260920.md), [experiment audit](experiment_recheck_20260920.md), and [literature recheck](literature_recheck_20260920.md) before using this document. Earlier universal impossibility, optimality, matched-cost kill, and feature-no-signal claims are superseded. Original text remains for provenance.

**Executed 2026-09-19, zero GPU cost.** `experiments/audits/g1a_selection_pilot.py`;
output `results/audits/g1a_selection/`.

`docs/gate1_rescope.md` named the risk that now decides the project: the selection gap
is only worth chasing if a rule that **cannot see the hidden verdict** can find the
correct candidate more often than the incumbent cheap check. This tests exactly that, on
the existing log, with cross-fitting over **tasks** so the model never scores a task it
trained on.

Three pickers over the same candidate sets: **visible** (return the first candidate whose
visible check passes — the incumbent), **learned** (argmax of a cross-fitted model of
`P(hidden pass | features)`, features excluding the hidden verdict and everything derived
from it), and **oracle** (return a hidden-passing candidate if one exists — the ceiling).

| receiver | n tasks | single | visible picker | learned picker | oracle | learned − visible | selection gap | fraction recovered |
|---|---|---|---|---|---|---|---|---|
| Qwen2.5-3B | 448 | 0.7169 | **0.7455** | 0.7321 (GBM) | 0.8192 | −0.0134 [−0.0339, +0.0071] | 0.0737 | **−0.18** |
| Qwen2.5-3B | 448 | 0.7169 | **0.7455** | 0.7411 (logit) | 0.8192 | −0.0045 [−0.0292, +0.0203] | 0.0737 | **−0.06** |
| Qwen2.5-7B | 485 | 0.7954 | **0.8041** | 0.8041 (both) | 0.8392 | +0.0000 [−0.0128, +0.0128] | 0.0351 | **0.00** |

Features offered: visible pass, fraction of visible assertions failed, assertion count,
failure class, timeout flag, completion and prompt tokens, benchmark, and thirteen
cheap structural properties of the candidate (length, line count, `def`/`return` counts,
loop/branch/try/import presence, recursion, parse success, AST node count, AST depth).

**The result is null, and on the 3B slightly negative.** Neither a gradient-boosted model
nor a regularized linear one beats "return the first candidate that passes the visible
check". The 3.5–7.4 points of selection headroom are **not reachable from this feature
set**.

## What this rules out, and what it does not

**Ruled out:** that the selection gap can be harvested with cheap static features plus a
single visible assertion. That was the cheapest possible version of the story and it does
not work.

**Not ruled out, and now the specific next test:** **cross-candidate execution
agreement.** Nothing in the feature set above compares candidates *to each other*. The
strongest known cheap selector for code does exactly that — execute every candidate on
common inputs and prefer the largest output-agreement cluster (the CodeT / AlphaCode
family). It is absent here because the only input with a known expected value is the
visible assertion, and every candidate that passes it already agrees there by
construction; extracting signal requires *generating additional inputs*, which is real
work and belongs inside Gate 1 rather than in a free re-analysis.

Two honest caveats on that next step. First, agreement clustering is a **published strong
baseline**, so if it works it is another bar this project must clear, not a contribution
of it. Second, these candidates come from a routing experiment with only 3–4 draws per
task; the re-scoped G1a draws 8 per task by design, which both strengthens agreement
signal and widens the oracle gap.

## Consequence for the programme

The re-scoped Gate 1 primary stands, but its **feature map is now the binding
constraint rather than an implementation detail.** G1a must therefore record, per
candidate, everything an agreement-based selector needs — the candidate's outputs on a set
of generated probe inputs, not merely its verdict on the one visible assertion — or it
will reproduce this null result at 3.07 GPU-hours instead of at zero.

Stated plainly: after four independent lines converged on selection-and-stopping as the
place where the measured value sits, the first test of whether that value is *reachable*
came back negative for the cheap version. The project's viability now turns on whether
agreement-based features recover it, and that is a well-posed question with a known-strong
comparator and a measured ceiling.
