# Synthetic reference experiment

**Executed, CPU-only, $0 external spend. No LLM or neural value model was trained or evaluated.**

The target stochastic feedback policy has exact value **0.798750**. There are 400 independent Monte Carlo replications, each with 800 tasks and 2 continuations per task; horizon 3. Truth is computed by backward recursion and independently checked by complete trajectory enumeration.

H1 includes the initial receiver answer. At every active round the same finite candidate slate offers RETRY, CORRECT, and STOP. STOP freezes quality and incurs no further cost. The logged feedback depends on current answer quality, which earlier feedback can change. Terminal utility subtracts 0.035 per cost unit by default (RETRY costs 1, CORRECT costs 2).

## Fixed-nuisance robustness and uncertainty

`correct` is the known simulator nuisance; `wrong` is a deliberately fixed misspecification. No nuisance fitting or cross-fitting performance is claimed. The code supplies task-fold assignment for future fitted experiments. All interval standard errors first average continuations within task.

| Estimator | Exact bias | MC bias (MCSE) | RMSE | 95% coverage (MCSE) |
|---|---:|---:|---:|---:|
| DR_both_correct | 0.000000 | 0.00069 (0.00050) | 0.00995 | 0.950 (0.011) |
| DR_propensity_correct_Q_wrong | 0.000000 | 0.00075 (0.00052) | 0.01036 | 0.953 (0.011) |
| DR_Q_correct_propensity_wrong | 0.000000 | -0.00377 (0.00279) | 0.05595 | 0.950 (0.011) |
| DR_both_wrong | 0.631259 | 0.62552 (0.00282) | 0.62805 | 0.000 (0.000) |
| IPW_propensity_correct | -0.000000 | 0.00053 (0.00202) | 0.04033 | 0.932 (0.013) |
| IPW_propensity_wrong | 0.579312 | 0.57094 (0.00386) | 0.57613 | 0.000 (0.000) |
| Direct_Q_correct | 0.000000 | 0.00054 (0.00033) | 0.00652 | 0.955 (0.010) |
| Direct_Q_wrong | -0.213881 | -0.21301 (0.00054) | 0.21328 | 0.000 (0.000) |

The exact expectation calculation, not simulation alone, verifies double robustness. Coverage is finite-sample evidence for this toy process only. Zero estimated coverage MCSE at observed coverage 0 or 1 is a plug-in Monte Carlo value, not a certainty claim. `Direct_Q_correct` uses oracle conditional means and therefore has information unavailable to a fitted model. Intervals for biased estimators are shown to expose failure; they do not repair misspecification.

## Confounding reversal

The following compares the next-answer quality after CORRECT versus RETRY. The causal contrast standardizes both interventions over the same active histories under the logging regime. It uses immediate quality (equivalently, terminal quality under STOP thereafter), not the main cost-penalized adaptive-policy outcome.

| Stage | Observed contrast | Causal standardized contrast |
|---|---:|---:|
| 1 | -0.2694 | 0.2117 |
| 2 | -0.2683 | 0.1680 |
| 3 | -0.2598 | 0.1497 |

## Exact policy values

| Policy | Utility | Quality | Feedback calls |
|---|---:|---:|---:|
| adaptive_stochastic | 0.7987 | 0.8648 | 1.062 |
| logging_behavior | 0.6663 | 0.7802 | 2.264 |
| always_retry | 0.4106 | 0.5156 | 3.000 |
| always_correct | 0.6555 | 0.8655 | 3.000 |
| accept_initial | 0.4750 | 0.4750 | 0.000 |
| oracle_optimal | 0.8683 | 0.9333 | 0.929 |

`oracle_optimal` is known-process dynamic programming, not a learned prompt generator. The conditional value file illustrates baseline-history-specific mean effects under two named continuation policies; these are not realized individual treatment effects.

## Reproduce and extend

```sh
uv run --extra dev python scripts/run_synthetic.py --replicates 400 --tasks 800 --episodes-per-task 2 --seed 20260919 --horizon 3 --cost-penalty 0.035 --output results/new_reproduction
uv run --extra dev pytest -q
```

Use a fresh output path; the runner refuses to overwrite an existing result. Config records seeds, source hashes, costs, sampling unit, and estimator definitions. Replicate estimates, exact policy values, conditional effects, overlap moments, and environment details are separate machine-readable files.

Limitations: finite supported candidates, randomized known behavior, four baseline strata, a fixed receiver transition law, no hidden confounding, no generator shift, no representation loss, no learned policies, no human users, and no empirical LLM effectiveness claim. Real experiments require frozen checkpoints, task-level train/calibration/test splits, fresh randomized continuations, terminal scorer isolation, failure accounting, and predeclared cost/support diagnostics.
