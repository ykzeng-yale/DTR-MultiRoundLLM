# Known assignment: inference may tolerate a misspecified outcome model

21 September 2026. **Theory clarification with independent internal review**, not
new empirical evidence or a new foundational DR result. This supplements
[Theorem 4 and section 6.2](theory.md#6-longitudinal-doubly-robust-evaluation).
It separates exact mean validity, asymptotic inference and observed finite-sample
coverage in the current weak-overlap diagnostics.

Sequential augmentation with known assignment is established prior work; see
[Jiang and Li (2016)](https://proceedings.mlr.press/v48/jiang16.html).
Cross-fitting and score convergence are established tools; see
[Chernozhukov et al.](https://arxiv.org/abs/1608.00060).
The statement and proof below specify our root-cluster setting rather than claiming
those sources prove every detail of this particular sampling contract.

## Target and conditions

The target is the fixed supported policy value V(d), with the same initial-history,
receiver, reward and continuation laws as the main theory. The policy is fixed
before evaluation, or learned on a separate dataset that we condition on throughout.
Use the **exact full assignment law** e: under the same generator this permits the
logged selector ratio; a changed generator needs the joint generator/selector ratio.
No estimated assignment, weight/score clipping, self-normalization or unmodeled
censoring is covered by this note. Bounded Q-prediction clipping is permitted if
the corresponding V is recomputed from that same Q; it preserves the mean identity.

Let O_i, i=1,...,n, be iid independent root clusters. Each contains a fixed,
prespecified number m of logged trajectories, with arbitrary within-root dependence
consistent with the stated marginal trajectory laws. All trajectories and branches
of a root stay in one fold. Use equal-weight root averages, so the target is the
population average over roots, not a size-biased episode population. Family-dependent
roots require a separately justified independent-family sampling/weighting contract;
calling related tasks different roots does not satisfy this condition.

For a deterministic candidate Q, D_i(Q,e) is the root mean of the longitudinal
augmented scores in equation (4), with V_t(Q)=integral d_t Q_t and a common terminal
outcome. The main identification assumptions and integrability give

    E[D_i(Q,e)] = V(d), for every admissible Q.                 (K1)

Q may compress history or be otherwise misspecified, as long as it is a measurable
function of permitted pre-action history and action. K1 does not say the fitted
Q values themselves are correct conditional treatment effects.

Partition roots independently of their data into K fixed folds I_k, with
n_k/n tending to p_k>0. Fit Q_hat^(-k) using only roots outside I_k, including all
hyperparameter choices; any independent learner randomness belongs to that training
information F_-k. Neither evaluation labels nor evaluation-derived tuning decisions
may enter this fit. Let Q_bar be a deterministic possibly misspecified limit.
The required stability condition is **root-score convergence**:

    r_nk^2 = E_O[(D_O(Q_hat^(-k),e) - D_O(Q_bar,e))^2 | F_-k]
           -> 0 in probability, for each k.                  (K2)

The expectation is over a new independent root, holding the fitted functions fixed.
This is not established merely by small training loss, pointwise Q convergence,
a large episode count or a positive assignment floor. Assume additionally

    0 < sigma_bar^2 = Var[D_i(Q_bar,e)] < infinity.             (K3)

Finite horizon, uniformly bounded rewards/Q and assignment ratios are sufficient
for the moment condition, but potentially large constants still impair finite
sample accuracy. K2 must hold under the actual weighted score law, not just under
an unrelated prediction-error norm.

## Proposition K: root-level asymptotic inference

Under these conditions, define the cross-fitted root scores and value estimate

    D_hat_i = D_i(Q_hat^(-k(i)),e),
    V_hat = n^(-1) sum_i D_hat_i.

Then V_hat is unbiased in finite samples when the scores are integrable, and

    sqrt(n) (V_hat - V(d))
      = n^(-1/2) sum_i [D_i(Q_bar,e) - V(d)] + o_p(1)
      -> Normal(0, sigma_bar^2).                              (K4)

Furthermore,

    s_hat^2 = (n-1)^(-1) sum_i (D_hat_i - V_hat)^2
      -> sigma_bar^2 in probability.                         (K5)

Thus V_hat +/- z_(1-alpha/2) sqrt(s_hat^2/n) has **asymptotic**, not guaranteed
finite-sample, coverage 1-alpha. Q_bar need not equal the true continuation Q.
No n^(-1/4) Q rate is required here: exact e removes the entire mean remainder,
while K2 controls the centered empirical term. This does not waive score stability,
independent roots, integrability or fixed-policy evaluation.

### Proof

For each fold separately, conditional on F_-k, its evaluation roots are iid and
independent of the fitted Q. K1 applied to the fitted and limit functions gives

    E[D_hat_i | F_-k] = E[D_i(Q_bar,e) | F_-k] = V(d).

Taking expectations and averaging proves finite-sample unbiasedness. Do not
condition jointly on all fitted models: their overlapping training sets contain
evaluation roots from other folds and do not preserve that conditional independence.

Write Delta_ik = D_i(Q_hat^(-k),e)-D_i(Q_bar,e). The conditional mean of each
Delta_ik is zero, and

    Var[n_k^(-1) sum_(i in I_k) Delta_ik | F_-k] = r_nk^2/n_k.

Conditional Chebyshev, K2, and n/n_k bounded imply
sqrt(n) n_k^(-1) sum Delta_ik = o_p(1). One can integrate the conditional probability
bound after truncating it at one; this requires convergence in probability of r_nk,
not an unstated convergence of its unconditional expectation. Summing K fixed
fold contributions proves the expansion in K4. Independence across folds is not
required for this finite sum. The ordinary iid-root CLT and K3 give the limit law.

For variance consistency, the conditional expectation of
n_k^(-1) sum Delta_ik^2 equals r_nk^2. Conditional Markov with the same truncated-bound
argument implies n^(-1) sum_i Delta_i^2=o_p(1). The iid law of large numbers gives
n^(-1) sum_i D_i(Q_bar,e)^2 -> E[D_i(Q_bar,e)^2]. Cauchy–Schwarz bounds the difference
of empirical second moments by

    2 sqrt[(n^(-1) sum D_i(Q_bar,e)^2)(n^(-1) sum Delta_i^2)]
      + n^(-1) sum Delta_i^2 = o_p(1).

The empirical means also agree up to o_p(1). Subtract their squared means and
apply n/(n-1)->1 to obtain K5. Slutsky's theorem yields the Wald conclusion. QED.

## Consequences for the reported failures and apparent improvements

The score at Q_bar is the asymptotic linear term in this **known-assignment**
setting. A misspecified limit does not in general attain the efficient variance.
This result gives neither a universal variance ordering of DR and plug-in regression
nor permission to regard any observed bias reduction as a theorem about RMSE.
Estimated/incorrect e requires a separate remainder analysis; the zero mean argument
above no longer follows for arbitrary Q.

In the [matched weak-overlap study](../results/matched_estimator_diagnosis_20260920/summary.json),
the original DR Wald coverage was 81.25% across 80 replications. That observation
is preserved. It does not by itself identify which finite-sample mechanism caused
the undercoverage, and a misspecified compressed Q alone does not refute K1 or
imply that asymptotic inference is impossible. Rare large weights, limited independent
roots, nuisance instability and approximation error remain issues to assess with a
prospectively frozen inference study. We have not verified K2 from these 80 records.

The [empty-cell oracle diagnostic](sparse_cell_diagnostic_results_20260921.md)
changed DR RMSE substantially but did not resolve a paired mean shift. That is
consistent with a change in finite-sample dispersion under mean-valid augmentation;
it does not prove variance reduction for a deployable method or validate the new
variant's confidence intervals. Across finitely many replications, an empirical
mean error need not be zero even when repeated-sampling expectation is zero.
Do not tune Q/fallbacks on those records and relabel them independent validation.

A future declared inference check should report root count, score and weight tails,
root-level SE calibration, interval length, coverage with Monte Carlo uncertainty,
and failures over every frozen cell. Mean validity, asymptotic validity and
useful finite-sample precision must remain separate acceptance criteria. This is
an analysis requirement, not a newly released model or simulation job.

## Review and scope of this delivery

Independent internal review checks the conditioning, cluster unit, stability limit
and empirical-variance argument. See the [review record](../results/known_assignment_inference_review_20260921.json).
This is a mathematical clarification of established machinery. No sampled simulation,
receiver call, candidate/reference execution, package installation or paid spending
was needed; no empirical coverage or efficacy credit is earned. The prior empirical
artifacts remain immutable, and the PDFs remain dated snapshots.

The fixed milestone rubric remains **49%, delta 0 points**. Final theory integration,
adequate-history fitted validation, measurement/receiver release, fresh supported
prompt experiments and independent policy validation remain open. The full project
is not submission-ready.
