# Next known-truth study: measurement, representation and policy value

21 September 2026. **Design amendment, not a completed simulation or execution
freeze.** It extends rather than reruns the [completed personalization premise
study](landmark_premise_results_20260920.md). The implementation, numerical laws,
estimators and seed/config hashes must be committed before execution. Existing
negative results and all previous completed runs remain immutable.

The [literature review](literature_guided_design_20260921.md) identifies three
missing tests: a prompt changes a stochastic receiver output before reward is
measured; feedback and final-answer selection can distort the endpoint; and good
outcome prediction does not necessarily produce good action rankings or policies.
This package tests those mechanisms under exactly computable truth. It cannot
estimate their real-world prevalence.

## Construction and truth contract

Use finite public history H, exact prompt index A, receiver output O and bounded
terminal reward Y. Enumerate P(O|H,A) and E[Y|H,A,O], so the action value is

`Q(H,A) = sum_o P(O=o | H,A) E[Y | H,A,O=o]`.

Here the two kernels are the **specified intervention law at the restored
history**, not automatically the observed conditional laws of a confounded log.
Their substitution by observed laws needs the corresponding identification
assumptions. If a hidden-confounding extension is added, truth integrates a latent
state over its pre-action distribution given H, not its action-selected observed
distribution. The randomized latent-only effect-modifier cell does not by itself
introduce hidden confounding.

The reference enumerator must be separate from data generation and learner code.
No sampled-output reward field is substituted for Q. Include multiple exact
prompts with the same response distribution; in a separate violation cell allow
prompt versions collapsed into one embedding to have different response/reward
laws. Sharing an embedding is not assumed to prove causal equivalence.

The first phase targets one landmark. A later two-decision extension must
enumerate the target policy's induced second-stage history distribution. Averaging
local branch advantages over the logger's histories does not by itself evaluate a
different full policy. Do not relabel the landmark phase a longitudinal-policy
validation.

Use separate training, tuning and evaluation roots, with nested branches and seed
repetitions. Conditional on a fitted policy, compute its exact value and the
development-selected fixed comparator's value. Evaluate their paired difference
on independent generated roots. Include an explicitly unavailable latent modifier
only in a negative-control cell; no deployable policy or fitted nuisance gets its
value. State exactly what the logged propensity conditions on. In particular,
supplying a latent-informed assignment probability can itself reveal adjustment
information; do not use that construction and then claim to have demonstrated
failure under hidden confounding.

## Prespecified scientific cells

The following is a targeted grid, not a Cartesian search for a favorable case.
Freeze the numerical probabilities and actual analysis list before executing it.

| Cell | Change from common process | Claim tested / failure to expose |
|---|---|---|
| 1. Full observed history, randomized actions | Action propensity uniform; receiver output mediates reward | Matched fitted-Q plug-in and DR should target the same value. A DR variance penalty is permissible. |
| 2. Observed severity drives action choice | Full pre-action severity available; propensities known by construction; overlap varies | Confounded marginal contrasts versus correctly history-adjusted regression and DR. Weak overlap can make weighting noisy. |
| 3. Misspecified Q / coarsened history | Remove one relevant interaction from the Q class; retain valid full-history propensity for DR | Separate robustness from unfair learner/feature advantages. Report which information the estimator still receives. |
| 4. Many prompts map to similar outputs | Duplicate response distributions, then violate equality within the proposed representation | Variance benefit from genuine structure versus bias from unsupported coarsening. |
| 5. Useful interaction versus unavailable signal | Opposite prompt rankings across public histories; separate latent-only modifier cell | Marginal cancellation, achievable personalization and inaccessible oracle headroom. Do not use outcome-selected opportunity roots for power. |
| 6. Misleading public diagnostics | Root-correlated diagnostic false pass/fail; zero-check states retained | Whether the policy exploits a valid signal, learns a spurious proxy or worsens answers. Use explicit confusion denominators. |
| 7. Oracle stopping / extra information | Under a null revision effect, compare final-output scoring with max-so-far; separately inject answer-relevant information into one arm | Detect favorable artifacts caused by hidden selection or unequal information rather than personalization. |
| 8. Administrative loss and budget | Arm-dependent unavailable outcomes; complete attempted-cost ledger; compare fixed calls with total-cost constraints | Selective retention, falsely grading unavailable execution zero, and overstated savings from post-hoc stopping. |

Do not combine every violation and then call the result a clean test of DR.
Each cell needs an explicit assumption-to-data mapping. Support-zero actions are
flagged as unidentified rather than rescued by a fitted regression. If a changed
generator or receiver law is studied, name its target and recompute truth.

## Learner and comparison contract

1. Fit a sequential/history-adjusted regression plug-in and DR critic with the
   **same features, folds, Q family and tuning budget**. Include simple stratified
   means where the finite state makes them appropriate. Known Q is an oracle
   reference. Actual logged randomized propensities are available in practice and
   are the primary DR/IPW assignment inputs; estimated-propensity variants are
   separate diagnostics.
2. Separate nuisance fitting, policy selection and final evaluation. Root/family
   folds contain all repeats and branches. Freeze ties and hyperparameters before
   evaluating a policy. Report direct randomized continuation evaluation as the
   reference when available; a fully observed branch design does not require DR
   merely to earn a causal label.
3. Report action-value bias/RMSE, conditional contrast error, calibration, ranking
   regret, exact policy regret and held-out policy gain separately. Lower outcome
   RMSE alone is not a successful personalization result. Report costs for all
   compared policies, not only their selected continuations.
4. For final inference, compare a small **prespecified** set of candidate
   procedures under null, rare discordance, heterogeneity and family dependence.
   Report coverage, false-positive rate, interval width and Monte Carlo SE.
   Existing conservative bounds stay valid within their assumptions; new methods
   must earn their own justification. Do not select an interval on real trial
   results or interpret failure of a sufficient bound as impossibility.
5. Compare allocation to more roots versus more receiver repeats at the same
   simulation budget. Report root variation and conditional receiver noise
   separately. Replication is useful for noise reduction but does not multiply
   the independent family count.

## Open-source reuse and bounded implementation handoff

Use the pinned `aiueola/offline-prompts` architecture as an inspected reference for
output-mediated synthetic rewards and competing policy learners. The current
release differs from the original arXiv v1; do not claim to reproduce that paper
by running the latest defaults. Port only a needed, license-compatible component
with attribution, or implement the declared finite law independently. Its
continuous Torch/generation stack is unnecessary for exact finite truth.

CausalCollab informs observed-confounding and distribution-shift cells. Its
inspected implementation has no verified LICENSE; do not copy its code. The
feedback papers motivate cells 6–8. They do not supply our unknown numerical
parameters or certify our theory.

Proposed first validation ceiling after a committed numerical freeze: eight cells,
at most 200 independent train/evaluation datasets per cell, at most 800 training
and 800 evaluation roots, R=1 and R=4 nested analyses, **one CPU worker, 10 minutes,
1 GB output, zero model calls, $0 spend**. Stop cleanly at the cap and report the
actual completed replicate count; do not discard failed fits or extrapolate
coverage from an incomplete preferred subset. At 200 replicates nominal 95%
coverage has a Monte Carlo standard error around 1.5 percentage points, so this
is diagnostic precision rather than a tight final coverage certificate. A larger
final Monte Carlo study requires its own justified cap and freeze.

Acceptance for this handoff is a reviewed numerical DGP/configuration, independent
enumeration tests, matched learner implementation and preregistered analysis—not
a claim that writing this plan has completed statistical validation. The
coordinator remains responsible for adjudicating failures against the target.
