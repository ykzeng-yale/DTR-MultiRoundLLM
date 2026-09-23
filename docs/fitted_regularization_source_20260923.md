# Matched regularization implementation: scope and acceptance

23 September 2026. Lead-owned issue #2 work while the experimental worker prepares MRL-23. This is implementation and deterministic verification, not the planned 600-dataset numerical study and not LLM evidence. Existing E0 results, including weak-overlap failures, remain unchanged.

## Prespecified estimator implemented

The new `experiments/e0/regularized_history_estimators.py` implements the [previously specified comparison](fitted_history_numerical_design_20260922.md), leaving the pinned simulator, original estimators and complete-history wrapper unchanged. It crosses compressed state/time and complete recorded state/action prefixes with shrinkage0 and5. All four nuisance variants share the dataset and root folds, and each supplies the same fitted Q to its matched plug-in and DR scores.

Within a training stage, the cell and action/stage pool means are episode-weighted. The penalty uses the number m of **distinct training roots** in that cell:

`q = (m*q_cell + lambda*q_pool)/(m+lambda)`.

An unseen cell uses the action/stage pool; an absent action uses the training-stage mean; an empty stage uses zero. Every variant computes its own downstream values and backward pseudo-outcomes. Applying shrinkage only after completing the unregularized recursion is a different procedure. Training roots supply support counts, not predictor features or independent effective sample sizes. Global episode duplication with the same root labels leaves the penalty and fitted values unchanged.

The rule intentionally applies to STOP cells too. Pooling STOP across states can move an otherwise exact observed STOP response away from its state-specific value. This is a limitation of the specified uniform heuristic, not a reason to silently insert an oracle exception. Shrinkage5 is neither optimized nor guaranteed to improve error. Expanding to full histories may reduce representation bias while increasing sparsity. Synthetic quality states include information not assumed publicly available in actual LLM histories.

## What validation can establish

Handcrafted finite records check raw-fit parity at lambda0, half pooling at m5, unchanged-root episode duplication, own-variant backward propagation, unseen-cell fallback, held-out isolation, absorbing STOP, root-fold integrity and reuse of the same Q by both scores. They can expose implementation errors; they cannot estimate bias, RMSE or coverage under the planned data-generating laws.

The lead independently reran the new and existing history-estimator suites: **42 passed in 0.80 seconds** (1.083 seconds command wall, 0.798 seconds child CPU, one CPU). The pinned simulator and both prior estimator files remain byte-identical to HEAD at review. The [validation record](../results/e0_regularization_source_validation_20260923.json) records the command, source hashes and scope.

The separate [deterministic truth check](../results/e0_regularization_truth_check_20260923.json) reproduces the declared uniform-policy value **0.6459770061744536** in two ways: the existing backward dynamic program and an independently written forward calculation accumulating absorbed STOP mass and terminal success. No sampled dataset or receiver call was used. A separate reviewer reproduced the forward calculation from scalar ordered-logit probabilities while retaining the persistent latent state and checking probability-mass conservation; the lead reran the saved [reproduction script](../scripts/check_regularization_truth.py). Both calculations share the simulator constants, so agreement checks arithmetic under that law, not the law's empirical validity.

The [machine-readable prospective plan](../experiments/e0/regularization_comparison_plan_v1.json) and [600-job seed table](../experiments/e0/regularization_comparison_seed_plan_v1.csv) instantiate the existing three cells and fixed interleaved order. These are unexecuted planned jobs. The [seed audit](../results/e0_regularization_seed_audit_20260923.json) finds no overlap between the 1,200 proposed inputs and 3,435 recorded inputs or the checked initial generator states, including 400 historical spawned reference states. It distinguishes documented prior seeds from unobserved external runs; absence of recorded collision is not proof of independent streams or universal freshness.

Independent mathematical/source review accepts the implemented rule within this scope. With independent roots, exact logged assignment probabilities and the stated causal assumptions, the held-out DR mean argument can be applied conditional on each fold's training data and then averaged. The training folds overlap: that argument does not make all scores independent or validate a root-score normal interval. Variance consistency needs additional conditions; coverage is untested. Support query counts are not ESS or target-policy occupancy.

## Remaining numerical-study gate

The numerical runner, complete failure-preserving output/summary schema, hard 600-second outer limit and 256-MiB output cap are still required. The current estimator source has independent review; the connected runner still needs review, followed by a final source/environment freeze before any sampled simulation. The planned one-CPU bound is not renewed by a heartbeat. No model calls, benchmark programs, paid service or installation are needed or authorized here.

This work tests estimator implementation against deterministic expectations. It supplies no new prompt efficacy, conditional-ranking, policy benefit or interval-coverage result. The experimental worker retains E14 ownership and the original ten-task source/mock allowance. Overall completion remains **58%, change 0 percentage points** under the fixed rubric; the full project is not submission-ready.
