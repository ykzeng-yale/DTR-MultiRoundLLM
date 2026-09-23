# STOP anchoring: score identity and prospective mechanism study

23 September 2026. **LEAD-E0-STOP-01: accept the theoretical clarification; proceed with source/design preparation only; hold numerical execution.** This is a new post-result diagnostic question motivated by the [capped matched study](e0_regularization_results_20260923.md), not completion of that study or a replacement for E14 and independent prompt-policy validation. Existing results, source freezes and unused reserved seeds remain immutable.

## What the previous result does and does not imply

The previous weak-overlap result combines prediction error, sparse training cells, fallback, backward propagation and importance-weight variation. Pooling a deterministic STOP value produces a specific Q-prediction error. It does not, by itself, establish DR bias or identify the fraction of total error caused by STOP. High fallback frequency likewise does not isolate a causal mechanism. Both fitted representations contain synthetic true quality S; this is not information asserted available to an LLM prompting policy.

The score argument below is a specialization of classical sequential doubly robust evaluation, not a novelty claim. See [Jiang and Li (2016)](https://proceedings.mlr.press/v48/jiang16.html) and [the existing longitudinal score/remainder treatment](theory.md#6-longitudinal-doubly-robust-evaluation). The derivation explicitly matches the absorbing-STOP implementation in `experiments/e0/estimators.py`.

## Exact score difference and its assumptions

Use t=1,...,T. Let I_t indicate that a trajectory is still eligible, rho_t=pi_t(A_t|H_t)/b_t(A_t|H_t), and W_t be the cumulative ratio, with W_0=1 and ratios one after stopping. For fixed fitted functions q, define v_t(q)=sum_a pi_t(a|H_t)q_t(H_t,a); set continuation values to zero after termination. Terminal rewards are the same for both scores. For q' versus q, put Delta_t=q'_t-q_t and delta_v_t=sum_a pi_t(a|H_t)Delta_t(H_t,a). Subtraction and reindexing give

    D(q') - D(q)
      = sum_t I_t W_(t-1) [delta_v_t - rho_t Delta_t(H_t,A_t)].        (1)

Indeed, the rewards cancel. The next-stage value differences shifted from the preceding stage, together with the initial value difference, equal sum_t I_t W_(t-1) delta_v_t. The action-prediction differences supply the second term.

Condition on the training information for the held-out root's fold and the pre-action history. If b is the actual assignment law on target support and q,q' are predictable and the weighted score increments are integrable, then

    E_b[rho_t Delta_t(H_t,A_t) | training, pre-action history]
      = sum_a pi_t(a|H_t)Delta_t(H_t,a) = delta_v_t.                  (2)

Thus each increment in (1) is centered. A fixed target policy, honest exclusion of the entire evaluation root from nuisance fitting/tuning, correct absorbing termination, and complete outcome accounting are essential. Neither nuisance correctness nor sufficiency of a compressed representation is required for this mean equality. With consistency, the randomized law and target support, comparison to q=0 gives the usual unbiased policy-value score.

Averaging trajectories within each root and then roots preserves the identity and expectation. Apply the conditioning fold by fold, not jointly on every fold's fit: overlapping training sets do not make all cross-fitted root scores independent. The result does not prove the reported root-score SE or normal interval valid. It also does not apply unchanged to the subset selected by a time cap or estimator return; the earlier partial-run interpretation remains descriptive.

Writing L=D(q')-D(q), whenever second moments exist,

    Var[D(q')] - Var[D(q)] = 2 Cov[D(q), L] + Var[L].                (3)

Hence centering alone supplies no variance ordering. For a root-level comparison, D and L must be root averages so that within-root covariance is retained.

For evaluation-only STOP anchoring, leave every non-STOP prediction fixed and replace all active STOP queries by f_t=1{S_t=3}, including unseen cells. Then (1) reduces to

    L_STOP = sum_t I_t W_(t-1) pi_t(STOP|H_t)
             [f_t - q_t(H_t,STOP)]
             [1 - 1{A_t=STOP}/b_t(STOP|H_t)].                      (4)

Full backward refitting is different: changed downstream values alter upstream pseudo-outcomes, means and fallback values. Equation (1) still applies, but Delta must include those changes. Equation (4) alone does not describe the refitted estimator.

A counterexample rules out a universal variance-improvement guarantee. With one stage, two equiprobable logged/target actions, Y=0 under both actions and q=(c,c), 0<c<=1, the original DR score is identically zero. Anchoring only STOP produces q'=(0,c) and scores +c/2 and -c/2, increasing variance to c^2/4. These arbitrary predictable nuisances are not claimed to arise from the present sample-mean fitter in the all-zero training population. This is a counterexample to a universal claim, not evidence that anchoring harms the implemented E0 estimator.

Independent mathematical reviewers checked (1)–(4), root/fold conditioning, the counterexample and interpretation limits. The [exact rational checker](../scripts/check_stop_anchor_algebra.py) enumerates a separate ten-path, two-stage toy law with absorbing STOP and changes beyond STOP. All 19 arithmetic assertions pass; original and modified scores both have expectation 23/40. The counterexample with c=1/2 has variances 0 and 1/16. This checks finite examples, not the general proof or empirical performance. [Accounting](../results/e0_stop_anchor_algebra_20260923.json): 0 draws, fits, model calls, tokens or benchmark executions; $0; approximately 0.0013 seconds for the check and 0.030 seconds including interpreter launch.

## Proposed comparison: distinguish direct adjustment from propagation

Preserve the policy-value target and synthetic law: uniform probability 1/5 on all five actions including STOP, 230 roots with 40 trajectories each, horizon 3, effect multiplier 1 and gz=mislabel=template_sd=0. Use the weak-overlap logger only (kappa=2.5, floor .02), with actual probabilities recorded for every action. This intentionally narrows the new diagnostic question after seeing the old results. It is not a confirmatory replication or evidence about interactions across logging laws. The reference value remains 0.6459770061744536, subject to exact-reference binding at any later freeze.

Use 96 fresh independent simulated datasets and three shared root folds per dataset, with all branches of a root together. Every dataset receives the same 2 representations × 2 penalties × 3 modes:

| Factor | Levels |
|---|---|
| Representation | Compressed (S_t,t); complete recorded S/A prefix |
| Penalty | Original lambda=0; original lambda=5 |
| STOP handling | Original fit; evaluation-only anchor; recursively anchored fit |

There are 12 nuisance sequences, each supplying plug-in and DR estimates: **24 slots per dataset, 2,304 planned slots**. Only eight sequences require backward fitting per fold; the four evaluation-only sequences reuse the original fits. They remain separately labeled estimators. Compute their direct score adjustment through (4) and verify it against an independently evaluated changed-Q score in fixtures. Their plug-in adjustment uses the changed initial v only. Never substitute that evaluation-only rule for recursive refitting.

The recursive mode applies f_t at every active STOP query during backward continuation construction and held-out scoring, including observed and unseen cells. Non-STOP fitting rules and distinct-root penalties remain fixed, but their pseudo-outcomes change through the recursion. In the original lambda=0 fit, observed STOP cells are already exact; differences therefore involve unseen STOP fallback and propagation. Lambda=5 additionally changes observed-cell pooling. Structural anchors must never be counted as observed training support.

The primary diagnostic is the paired squared-error difference for **recursive versus original, full history, lambda=5, DR**. Always report the direct-versus-original, recursive-versus-direct and recursive-versus-original differences for all representation/penalty/method combinations (24 pairs), with actual jointly returned denominators. Report root-score changes and the covariance/variance accounting in (3). The empirical decomposition within a dataset is descriptive algebra; distinguish it from variance across dataset-level estimates and from uncertainty claims. Report STOP/non-STOP and observed/unseen fallback separately, upstream Q changes, root counts, bias, RMSE and empirical dispersion for both methods. Report SE, interval widths and returned versus operational coverage for DR only; do not construct plug-in confidence intervals from fitted score dispersion. No winner selection or efficacy claim follows.

## Precision, stopping and resource proposal

The fixed dataset count is a mechanism-study ceiling, not a coverage-validation sample size. At 96 complete independent replicates, nominal-95% coverage has binomial MCSE about 2.22 percentage points; the worst-case MCSE is 5.10 points. These are planning calculations, not a guarantee about the capped subset or calibrated intervals. For the primary paired squared-error difference, report its Monte Carlo SE and flag precision as insufficient if it exceeds 0.005 squared-value units. This analyst-chosen diagnostic threshold is fixed before any new outcomes; passing it alone does not establish improvement or statistical significance. Retain negative or inconclusive results. There is no prompt useful-gain test in this synthetic mechanism study.

Stop after the fixed 96 datasets or the hard resource cap, whichever comes first; do not inspect outcomes to tune, extend, replace seeds or stop for efficacy/futility. Any cap truncation or failed return requires all planned/attempted/returned/failed/unattempted and paired-exclusion denominators. A partial set remains incomplete and loses the fixed-size precision interpretation. None of its intervals authorizes prompt collection or policy release.

The proposed later ceiling remains **one CPU worker, 600 total seconds, 256 MiB of output, zero model/benchmark executions, zero tokens and $0**. It is not released by this document. Previous completed jobs took 583.705787/432=1.351171 seconds on average for four nuisance variants across three folds (12 backward fits). A deliberately approximate threefold cost multiplier for the new fits and score diagnostics, multiplied by 96 and a 1.25 allowance, gives 486.42 seconds. This is an extrapolation from a different run, not a worst-case bound or evidence that the new source fits the cap. The previous raw journal excluded dataset arrays, so its size is not a total-output projection for this design. Record actual imports, data generation, fits, scoring, reporting, cleanup and artifact sizes; preserve every partial slot if the hard cap binds. Time for any later read-only reconciliation remains separately accounted.

## Exact implementation and release dependencies

1. Create separate versioned adapters and manifests. The frozen runner, reporter and reconciler encode four nuisance fits, eight slots and 600 jobs; feeding them this plan would be wrong. Preserve their hashes and prior results.
2. Use a state-dependent query adapter shared by plug-in and DR. The old scalar STOP fallback cannot encode 1{S_t=3} for unseen histories. Apply it during the recursive variant's own backward construction as well as held-out evaluation.
3. Before sampling, commit a complete ordered 96-row data/fold seed table, audit against all previously reserved seeds including unattempted ones, bind environment/RNG/source hashes and every estimator's exact specification. Seed uniqueness alone does not establish independence. Store the actual minimal arrays used for estimation, fold assignments and their hashes in immutable files; account for them within the output cap.
4. Source/mock acceptance must establish original-mode parity; observed/unseen STOP behavior for both penalties; direct equation (4) versus an independent score calculation; recursive propagation; common nuisance queries; training-only dependence; root-fold integrity; inactive padding; structural-versus-observed support; all 2,304 slot identities; and durable interruption/failure accounting. Handcrafted fixtures require no simulation draws.
5. A complete source freeze, independent review, feasible output/runtime accounting, fresh factual host/lease checks and a separate explicit lead release must precede execution. No scheduling tick renews LEAD-E0-REG-01 or grants this run. No oracle-Q or generator extension is included.

This follow-up targets nuisance handling under the same fixed synthetic policy value; it does not establish history-conditional prompt ranking, independent policy improvement or observability of true correctness. MRL-23/E14 delivery remains the primary experiment blocker. Overall research completion remains **58%, change 0 percentage points** under the unchanged rubric; efficacy is unestablished and the full project is not submission-ready.
