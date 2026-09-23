# E0 — known-truth estimator diagnostics

The [corrected E0 report](../../docs/e0_corrected_results_20260920.md),
[matched-fit comparison](../../results/matched_estimator_diagnosis_20260920/summary.json),
and [current portfolio review](../../docs/experiment_portfolio_review_20260922.md)
govern interpretation. Original dated outputs remain immutable.

E0 evaluates the implemented estimators against specified synthetic policy values
and blips. It does not validate every estimator in the project, real-model effects,
unknown-confounding adjustment, or general representation sufficiency. The former
state-only “optimal” reference is a heuristic, not an established optimum.

| File | Role |
|---|---|
| `simulator.py` | Specified finite transition laws and exact dynamic-program truth |
| `estimators.py` | Fitted outcome regressions and policy-value/blip estimators |
| `history_estimators.py` | Root-cross-fitted complete synthetic-prefix comparator; source/fixture validated only |
| `run_grid.py` | Seventeen diagnostic conditions, fixed seeds and saved records |

## Design choices and scope

The ease-distribution parameters and damage scenarios were motivated by historical
corpus diagnostics. They are numerical design choices, not estimates of a validated
real intervention law. The historical 16.2% degradation rate was conditional on the
source loop continuing an initially correct artifact; it does not establish that
every prompt arm is harmful. The historical `n_tasks=230` is a difficulty-selected
subset size, not a measured effective sample size or independent-family count.

Policy truth uses the actual continuation and replicate-specific template-mixture
law. Conditional blips integrate the latent distribution given the specified
observed state. Neither changing the target continuation nor supplying a different
mixture truth is a cosmetic correction. With five actions, a common assignment
floor must satisfy `5 * floor <= 1`; the implementation rejects infeasible floors.

The legacy cell names are retained to preserve record linkage:

- `FAIL_positivity`: positive .02 action floor and weak finite-sample overlap;
  this is not zero-support nonidentification.
- `FAIL_latent`: assignment depends on latent information, but the estimator
  receives the true latent-dependent probabilities. This is not a test of fitted
  behavior models or identification under unknown confounding.
- `FAIL_mislabel`: an explicit treatment-recording error condition.
- `FAIL_coarsening`: a randomized template-mixture condition scored against its
  actual mixture truth. Its corrected result does not establish arbitrary text
  compression validity or intrinsic failure of a declared mixture intervention.

## Delivered and still pending

The corrected grid contains **17 ×80=1,360** diagnostic replications, rather than
completion of a high-precision 1,000-per-cell study. The matched study contains
**5 ×80=400** comparisons using the same fits/folds for plug-in and DR. Known
assignment probabilities are used; outcome regressions are fitted. In weak overlap,
DR coverage is65/80=.8125 in each of two distinct seed sets, with MCSE .0436. Retain
this failure and the matched DR RMSE penalty; theoretical robustness does not
certify finite-sample interval performance.

The [exact history-compression check](../../docs/history_compression_results_20260921.md)
independently reconciles full-history population truth with the dynamic program
within1e-12 in its declared scope. The earlier claim of a two-million-episode Monte
Carlo match to “0.00 MC SE” lacks a located source-bound record in this review and
is not used as validation evidence. Rounded agreement would not imply zero error.

An [available fitted complete-history comparator](../../docs/fitted_history_comparator_20260922.md)
now has source and deterministic-fixture validation. It uses the observed synthetic
state/action prefix, training-only fits/fallback, intact root folds and matched
plug-in/DR Q tables. This does not establish finite-sample adequacy or make the
synthetic quality state an available public LLM feature.

Still pending: numerical validation of that comparator, practical regularization,
a fresh numerical freeze with declared Monte Carlo precision and root-level
inference diagnostics, and independent ranking/policy-value validation.
The [narrow matched-study specification](../../docs/fitted_history_numerical_design_20260922.md)
now defines the three-logger representation/shrinkage diagnostic; it still needs
implemented source and an execution freeze. The [eight-cell proposal](../../docs/literature_simulation_plan_20260921.md)
remains a separate design amendment, not an executed study. Reproduce historical reports from their
recorded source/configuration revisions into new paths; no large rerun or additional
compute is authorized by this README. No simulation result establishes LLM efficacy.
