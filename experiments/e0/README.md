# E0 — reference simulator and estimator validation

> **Corrected 2026-09-20.** The [corrected E0 report](../../docs/e0_corrected_results_20260920.md) supersedes historical target/optimality/failure interpretations below. The current code includes first-action weighting, replicate-specific mixture truth, explicit logging-versus-target comparisons, a heuristic reference, exact seed counts and saved replicate records. Executed run sources are snapshotted with each dated result.

CPU only, no model calls. This is the work that proceeds while the GPU is held by a
sibling project, and it is the gate every estimator must pass before it is trusted on
real data.

| file | contents |
|---|---|
| `simulator.py` | the data-generating process, the exact dynamic program, and the two failure mechanisms |
| `estimators.py` | six estimators, three of which are meant to fail |
| `run_grid.py` | the 17-cell grid, manifests, metrics |

## What it is for

Every estimator in this project is validated here against a law whose optimal regime,
policy values and turn-level blip effects are computed exactly by dynamic programming
rather than estimated. It licenses statements of the form *"estimator X recovers, or
fails to recover, a known truth under condition Y"*. It licenses no statement about
what any real intervention does to any real model.

## Calibrated to this project's own measurements, not invented

* The ease distribution is the **beta-binomial fitted in audit A2** to per-task
  first-attempt success for Qwen2.5-3B (α 0.348, β 0.230), which is why it is U-shaped:
  tasks are reliably solved or reliably unsolved, not concentrated in a middle.
* `n_tasks = 230` is the **effective pool measured by three independent routes**
  (A2's beta-binomial, the integrity/mutation exclusions, and the A4 scoring rule).
* Every arm is **harmful in the correct state**, because audit A3 measured a 16.2%
  degradation rate when a correct answer is iterated on.
* State 2 — passes the visible assertion, fails the hidden ones — exists because the
  harness's own visible/hidden split creates it, and it is the configuration in which
  A3 found a self-check stopping rule stopping on half of all failures.

## Two structural features that carry the study

**Blips are graded against the posterior-weighted truth.** An estimator conditioning
on the observed state `S_1 = s` targets a blip that integrates the latents over
`P(E, Z | S_1 = s)`, not over their prior. The prior-weighted version is a different
number — at `s = 1` the two differ by about 0.09 — and grading against it would
misattribute a correct estimator's behaviour to bias. `true_blips` (prior) is kept
only so the two can be compared; `true_blips_posterior` is the truth.

**The positivity floor is not a free parameter.** A per-arm floor `δ` over `K` arms
requires `K·δ ≤ 1`, so at `K = 5` the largest attainable floor is `0.20`, which is
exactly uniform randomization. `make_beh` raises on an infeasible floor rather than
silently renormalizing. This is the arithmetic that five independent reviewers found
violated in the theory draft, where a floor of 0.25 was recommended alongside 5–6
arms plus STOP.

## Failure cells are part of the design

`FAIL_positivity` (floor 0.02 with strong confounding), `FAIL_latent` (the logging
policy tracks the unobservable that determines which arm is best), `FAIL_mislabel`
(15% of localization interventions recorded as retries — what a text-log classifier
produces), and `FAIL_coarsening` (three paraphrases per class with genuinely different
effects, violating the assumption that the outcome depends on the message only through
its class). A simulation study that only shows the causal estimators winning is an
advertisement; these cells are pre-registered so the boundary is reported rather than
discovered by a reviewer.

## Reproduce

```bash
python experiments/e0/run_grid.py --list
python experiments/e0/run_grid.py --cell base --reps 200 --workers 6
python experiments/e0/run_grid.py --reps 1000 --workers 6      # pre-registered R
```

Results land in an immutable `results/e0/<stamp>/<cell>/` with a manifest recording
the seed table, code hash and the exact truth each cell was graded against.

## Verified

The exact dynamic program matches a 2,000,000-episode Monte Carlo of `V(uniform-5)` to
**0.00 MC SE** (0.645977 both), and every conditional blip matches its brute-force
Monte Carlo within about one MC SE. That is E0's hardest abort condition and it passes.
