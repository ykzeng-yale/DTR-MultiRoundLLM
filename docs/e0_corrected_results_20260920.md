# Corrected E0 simulation study, 2026-09-20

**Executed: 17 cells × 80 replications = 1,360 replications, local CPU only.** This is a corrected diagnostic grid, not the planned 1,000-replication-per-cell final precision study. Every replication retains its seed, fitted-Q results, exact actual-template-mixture truth, rule values and offsets. Each run includes a matching source snapshot. Original results are preserved; the Sept 19 interpretation is superseded.

## What changed

The first-action inverse probability factor now restores the latent distribution within the initial state. Conditional raw regression is evaluated both against its own logging-continuation association and against the distinct uniform-continuation target. Template heterogeneity is graded against the replicate-specific mixture kernel, rather than the zero-offset kernel. The previously named state-only optimum is a heuristic reference; its difference from a learned rule is not optimal-policy regret. The driver now executes exactly the requested number of distinct seeds, independent of worker count, and saves per-replication records.

## Fitted-Q policy-value results

| Cell | Replications | DR bias | Bias MCSE | 95% coverage | Coverage MCSE |
|---|---:|---:|---:|---:|---:|
| FAIL_coarsening | 80 | -0.0029 | 0.0016 | 0.9625 | 0.0212 |
| FAIL_latent | 80 | +0.0020 | 0.0018 | 0.9250 | 0.0294 |
| base | 80 | -0.0020 | 0.0017 | 0.9625 | 0.0212 |
| kappa0 | 80 | -0.0002 | 0.0015 | 0.9625 | 0.0212 |
| FAIL_mislabel | 80 | +0.0002 | 0.0017 | 0.9125 | 0.0316 |
| FAIL_positivity | 80 | -0.0158 | 0.0086 | 0.8125 | 0.0436 |
| T2 | 80 | -0.0040 | 0.0018 | 0.9500 | 0.0244 |
| T5 | 80 | -0.0021 | 0.0018 | 0.9500 | 0.0244 |
| floor0.02 | 80 | +0.0014 | 0.0023 | 0.9000 | 0.0335 |
| floor0.05 | 80 | -0.0015 | 0.0016 | 0.9500 | 0.0244 |
| half_effect | 80 | -0.0004 | 0.0018 | 0.9375 | 0.0271 |
| kappa0.5 | 80 | -0.0030 | 0.0017 | 0.9375 | 0.0271 |
| kappa2 | 80 | -0.0005 | 0.0018 | 0.9625 | 0.0212 |
| latent_track | 80 | +0.0004 | 0.0015 | 0.9625 | 0.0212 |
| n590 | 80 | +0.0020 | 0.0010 | 0.9625 | 0.0212 |
| runs10 | 80 | +0.0021 | 0.0021 | 0.9000 | 0.0335 |
| runs160 | 80 | -0.0011 | 0.0014 | 0.9625 | 0.0212 |

Known logging probabilities are used throughout; the outcome regressions are actually fitted and cross-fitted by root task. Persistent latents make the compressed state Q potentially misspecified. In latent-dependent assignment cells, recorded B contains the true latent-dependent assignment probability: this is not identification from unknown confounding. No fitted behavior-model claim is made.

The weak-overlap cell still has a positive .02 probability floor, so it demonstrates practical finite-sample failure, not nonidentification from zero support. Its coverage is .8125 (MCSE .0436), with bias −.0158 (see table); Wald intervals cannot be assumed reliable there. The template-mixture cell now has .9625 coverage (MCSE .0212), using its actual law. This removes the earlier invalid interpretation that template variation intrinsically breaks a declared class-mixture intervention. Eighty replications remain too imprecise to establish nominal coverage at high precision. No multiplicity-selected winner is claimed.

## Reproduce and extend

Run `uv run python experiments/e0/run_grid.py --reps 80 --workers 4 --seed-base 20260920 --out results/new_corrected_grid`. Seeds are tied to the stable cell registry, so the two executed batches and a combined invocation share seeds. Numerical source snapshots are under the two dated runs in `results/e0_corrected_20260920/`; timing/platform fields can differ.

Before using these as a final manuscript coverage study, freeze a desired Monte Carlo precision, increase replications accordingly, and include a correct full-history sequential-regression baseline for the same continuation target. A separate observational-data claim requires actually fitted propensity nuisances and their assumptions. The synthetic study does not establish real prompt efficacy.
