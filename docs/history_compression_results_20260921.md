# How much of the E0 regression error is history compression?

21 September 2026. **Exact synthetic population diagnostic**, not sampled
simulation, a fitted learner, or real prompt efficacy. Plan/code/config were
committed at 5f9febe, with a provenance-only completion at **91f9a74** before the
report was executed. Historical finite-sample results remain unchanged.

## Finding

The compressed state/time sequential regression has a small nonzero population
bias in the base and weak-overlap cells. An oracle using complete observed
synthetic history agrees with the target-policy truth. The uniform-logger control
agrees in aggregate despite the persistent latent variables.

| Existing E0 condition | Compressed population value | Exact target value | Compression bias, percentage points |
|---|---:|---:|---:|
| Base | .644590174629 | .645977006174 | -.138683 |
| Uniform logger | .645977006174 | .645977006174 | 0, up to rounding |
| Weak overlap, positive .02 floor | .637250556750 | .645977006174 | -.872645 |

The exact full-history reference is .645977006174 in all three cells: only logging
changes, while the receiver transition law, initial population and uniform target
policy are unchanged. Full-history posterior traversal and the existing latent-
state backward dynamic program agree within 1e-12. An independent reviewer used a
separate scalar occupancy recursion and forward STOP/terminal accounting, reproducing
all three compressed values and the common target value within 1e-12.

In the earlier matched finite-sample study, weak-overlap plug-in bias was
-.0542930210, versus -.0087264494 in this population diagnostic. Their difference
is -.0455665716. This is a comparison with a noisy finite-replication estimate,
not an identified decomposition into additional causal mechanisms. History
compression alone is not an adequate explanation of that larger finite result.
Finite estimation, sparse cells/fallbacks, realized task composition and Monte
Carlo variation remain possible contributors; this calculation does not isolate
them. It also does not compare finite-sample variance of learned full-history and
compressed regressions. More conditioning can create a sparsity problem of its own.

## Target and method

The target is the same three-decision uniform policy, with STOP absorbing at the
current correctness score. The [frozen plan](history_compression_plan_20260921.md)
defines an infinite-independent-task population, not infinite repetitions of a
fixed roster. Logger occupancy preserves active survival mass; STOP paths do not
propagate. Backward compressed regressions average their own next-stage values
under the logger's current state/action-specific latent mixture. This is the
population counterpart of the existing unsmoothed state/time `fit_q` when cell
frequencies grow and empty-cell fallbacks disappear.

The full-history reference instead propagates a latent posterior over all previous
synthetic states and actions. It uses the known simulation law, not the realized
latent class as a policy input. At gz=0, assignment depends only on current observed
state, so action factors cancel given full history. Thus the discrepancy here is
history truncation and changed logger/target latent mixtures, not hidden treatment
confounding. The full synthetic state includes the distinction between
visible-pass/hidden-fail and correct states; it is not a certified public feature
set for the real coding application.

On-policy aggregate equality does not prove correct conditional Q values, blips,
or Markov sufficiency. Likewise, the .02 action floor creates weak finite-sample
overlap, not zero-support nonidentification. This diagnostic is consistent with
the existing robustness identities and with poor finite-sample DR variance or
coverage. It supplies no new policy-effect confidence interval.

## Validation and provenance

Seven structural checks cover horizons 1–3 under the on-policy logger, a one-
decision off-policy comparison, removal of transition heterogeneity, a nonuniform
target full-history/DP comparison, and rejection of latent-dependent assignment
outside this scope. The project suite passed 229 tests and 8 subtests before the
metadata-only freeze completion. These checks validate the calculation's stated
scope; their count is not empirical evidence.

The runner verifies exact committed bytes for its script, plan, tests, config and
three existing E0 sources before calculating. The report records Python 3.14.4,
NumPy 2.5.3 and SciPy 1.18.1; SciPy determines the initial ease distribution. See
[machine-readable results](../results/history_compression_20260921.json) and
[process invocation](../results/history_compression_20260921_invocation.json).

The main calculation traversed 17,476 full-history nodes and took .030442 seconds;
the complete process took .926082 seconds, below the frozen 60-second cap. Output
was below 10 MiB. Receiver calls/tokens, sampled trajectories, fitted models,
candidate/reference executions and paid spend were all zero. The independent
reviewer's short scalar calculation had no separately recorded runtime; no total
research wall-time claim is made. No package installation or GPU work occurred.

Reproduce from the frozen commit, or a later commit retaining identical pinned
sources, into an unused output file:

```bash
.venv/bin/python scripts/check_history_compression.py --output work/history_compression_recheck.json
```

This is independent internal mathematical/numerical review, not external peer
review or formal proof verification. It does not complete the planned fitted
adequate-history comparison or broader known-truth simulation grid. Progress
remains **49%, delta 0 points**; real prompt efficacy and submission readiness are
unchanged. Keep MRL-01–04 and the frozen same-prefix study as the empirical priority.
