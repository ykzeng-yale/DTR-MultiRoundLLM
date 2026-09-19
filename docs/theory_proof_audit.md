# Proof audit and implementation obligations

**Date:** 2026-09-19. **Scope:** [theory.md](theory.md). This is an internal mathematical audit and a record of an exact finite-state numerical identity check. A separate agent subsequently reviewed the proof and triggered the support corrections recorded below; external expert review and LLM experiments remain pending. “Proved” below means proved within the stated mathematical model, not validated as an empirical assumption about real conversations.

## 1. Result inventory

| Result | Claim actually proved | Essential scope condition | Established foundation or project-specific assembly |
|---|---|---|---|
| Theorem 1 | G-formula, Bellman identification, cumulative likelihood-ratio evaluation | Consistency, sequential exchangeability, target support, stable kernels | Established longitudinal causal inference, written for generated slates and selected indices |
| Same-generator corollary | Generator densities cancel, leaving `π(J|H,C)/b(J|H,C)` | Identical frozen generator law in logging and target | Project design specialization |
| Generator-change corollary | Full generator density ratio is required when `G* != G0` | Absolute continuity and correct ordered-slate density after all filters | Change-of-measure consequence |
| Proposition 2 | Realized ITE distribution and unsupported prompt values are not identified in general | No additional joint-potential-outcome or extrapolation structure | Explicit observational-equivalence counterexamples |
| Proposition 3 | Controlled-Markov representation conditions imply represented Q | Action/transition sufficiency, terminal measurability, compatible policy and slate exclusion | Standard backward induction plus representation-specific boundary |
| Theorem 4 | Exact longitudinal DR remainder and stagewise mixed robustness | Integrated target values, correct terminal utility, independent nuisance fitting for sample expectation claims | Established augmentation identity; complete proof in project notation |
| Equation (7) | Exact product bound in weighted stage norms | Relative assignment error; finite weighted measures | Cauchy–Schwarz; no hidden uniform density lower bound |
| Theorem 5 | Canonical gradient for fixed external target policy in unrestricted full-history model | Regular submodels, square integrability, target fixed externally | Established semiparametric principle; explicit tangent-score verification |
| Equation (9) | Additional slate tangent component for unknown natural generator target | Generator is part of the varying observed-data functional | Project-specific observation-model distinction |
| Theorem 6 | Exact conditional pseudo-outcome bias | Positive true and fitted propensity for every queried index, plus explicitly controlled continuation bias | Conditional augmentation identity |
| Equation (13) | Bellman-optimal selector within fixed generator candidate class | Finite eligible supported slates and measurable tie breaking | Standard finite-horizon dynamic programming |
| Theorem 7 | Performance difference and improvement conditional on simultaneous critic bounds | Same generator; target occupancy; valid uniform error event | Standard policy improvement, specialized to slates and STOP |
| Equation (16) | Simultaneous finite-class holdout value bounds | Fixed policies/nuisances before independent bounded root scores | Hoeffding plus union bound |
| Theorem 8 | Exact coverage/ranking decomposition and uniform regret bound | Identical eligible supported maxima/greedy sets, slate exclusion, common costs, specified optimal continuation | Connected project error decomposition using standard telescoping |
| Equation (20) | Exponential-in-K coverage failure bound | Original independent proposals with near-optimal eligible mass, preservation, and 0 <= eta <= B | Elementary probability; not valid automatically for correlated beams |
| Equation (21) | Policy-gradient identity | Current-policy Q and occupancy, dominated differentiation, frozen transitions | Standard likelihood-score derivation |
| Equation (22) | Root-cluster variance for prespecified root-average scores | Independent identically sampled roots; appropriate within-root weights | Independent-cluster variance identity |

The theorem numbering includes Propositions 2 and 3; there are eight numbered results in total, plus explicitly derived corollaries and equations. This count is not a claim of eight novel theorems.

## 2. Algebra checks and fixes

### 2.1 Remainder sign, timing, and robustness

The correct sign is

`bias = sum_t E[What_(t-1) integral d_t (1 - e_t/ehat_t) (Qhat_t-Qtrue_t)]`.

It is not `(1-ehat/e)` and not a ratio product ending at `t` outside the stage integral. The proof cancels all true Bellman residuals before reindexing Q errors. The terminal difference is zero because the observed terminal utility is used exactly.

A stagewise mixed specification is valid: assignment can be correct at stage 1 and target Q correct at stage 2. But saying a fitted regression model is “correct at stage 2” requires the actual target-continuation Q, not a regression on biased continuation targets. The conditional pseudo-outcome theorem exposes the remaining downstream bias explicitly.

### 2.2 Density rates

An initial absolute-density-error shorthand was corrected during review. A bounded target/logging likelihood ratio does not imply a lower bound on the fitted behavior density. Equation (7) therefore uses the exact relative error `1-e/ehat` under the weighted stage measure induced by prior fitted weights and the target current action law. An absolute error bound for finite selection probabilities is permitted only after imposing an explicit positive lower bound on `bhat` and appropriate measure domination.

### 2.3 Known versus natural candidate generator

The main integrated score uses `V_t(H)=E_G sum_j π_j Q_t(H,C,j)`. Theorem 5 fixes this target generator externally; it has no natural-generator score term.

If the unknown observed generator is itself part of the target, a generator submodel changes the target value. Its canonical gradient includes `Omega_(t-1)[W_t(H,C)-V_t(H)]`. The practical recursion in [training_and_serving.md](training_and_serving.md) uses `Z_t=(H_t,C_t)` as the state and is compatible with this natural-slate formulation. A constant finite slate makes the extra term zero. Do not copy an efficiency claim from one formulation into the other without this distinction.

### 2.4 Optimal Q versus baseline Q

The performance difference theorem requires `Q^beta` for baseline continuation and proves improvement relative to that baseline. The candidate regret theorem's ranking part uses `Q^{*,G}`, the optimal continuation inside the generator-constrained class. These cannot be interchanged. A one-step greedy update based on a baseline critic does not establish global prompt optimality.

### 2.5 Shared-prefix dependence

The sampling unit in inferential rates and standard errors is an independent root cluster. Branch count is a computation budget, not the independent sample size. A repeated fork estimates a conditional mean over repeated stochastic continuations; it does not identify a user's joint latent counterfactual outcomes.

### 2.6 Independent review: candidate support and coverage

The implementation reviewer identified a substantive mismatch: (13) maximized over eligible supported indices, while the initial (17)–(20) used an unqualified slate maximum. An unsupported high-value candidate could then make the coverage loss zero even though no admissible policy could select it, invalidating (19). All maxima, greedy choices, and uniform error events in the repaired subsection now use the identical `J(h,c)` of eligible indices with positive logging support, and compared policies put zero mass outside it.

The reviewer also identified that target-policy positivity is insufficient for every-index pseudo-outcomes: a candidate with zero target mass can still have an unidentified Q if its logging propensity is zero. Equation (11) and Theorem 6 now explicitly require both true and fitted selection probability to be positive for each queried index, regardless of its target probability.

The coverage corollary now states `0 <= eta <= B`, so its tighter probability bound has the correct monotonicity. Its `K` counts original independent draws; a near-optimal draw must remain eligible/selectable after the full protocol. Deduplication preserving one supported copy is harmless for the maximum event, whereas dependent filtering or counting only post-filter unique candidates does not justify the independent-draw formula.

## 3. Exact finite-state numerical identity check executed

An independent two-stage enumerator was run on 2026-09-19 as an algebra check. Its executable source is [check_random_slate_remainder.py](../scripts/check_random_slate_remainder.py); machine-readable results and the source SHA-256 are in [random_slate_remainder.json](../results/random_slate_remainder.json). Reproduce with `python3 scripts/check_random_slate_remainder.py --output results/random_slate_remainder_rerun.json`. It is separate from the repository's reference simulator and uses random slates, randomized candidate selection, stochastic receiver transitions, generation/action costs, and both fixed and shifted generator laws. Every finite trajectory was enumerated, so the numbers below have floating-point error rather than Monte Carlo standard error.

The executable checks all eight cases, probability normalization, complete enumeration of 128 trajectories per case, the exact remainder identity, stagewise robustness, and nonzero bias in the both-wrong cases. The complete data-generating specification is:

* `P(H_1=1)=0.4`; current state summary `s` is the latest binary receiver state.
* Two decisions; binary slate type `c` and binary selected index `j`.
* Logging generator: `P(c=1|s)=0.65` if `s=1`, otherwise `0.35`.
* Changed target generator: `P(c=1|s)=0.48` if `s=1`, otherwise `0.58`.
* Logging selector: `P(j=1|s,c)=0.25+0.20c+0.15s`.
* Target selector: `P(j=1|s,c)=0.70-0.25c+0.05s`.
* Receiver: `P(s_next=1|s,c,j)=0.12+0.38j+0.18c+0.13s`.
* Turn reward: `-0.06j-0.02c`; terminal reward: last `s_next`.
* Wrong selector nuisance: `P_hat(j=1|s,c)=0.70-0.20c`.
* Wrong Q nuisance: `Q_hat=0.39+0.14c-0.07j+0.08s` at either stage.
* Correct Q computed by exact backward recursion for the specified target. Assignment numerator includes the target generator law; denominator includes the true logging generator and either true or wrong selector.

| Target | Nuisance condition | Oracle value | Score bias | Exact remainder | Absolute identity error |
|---|---|---:|---:|---:|---:|
| Same generator | All assignment mechanisms correct; both Q wrong | 0.408993500000 | 0 to numerical precision | 0 | 5.55e-17 |
| Same generator | Both assignments wrong; all Q correct | 0.408993500000 | 0 to numerical precision | 0 | 1.67e-16 |
| Same generator | Assignment correct only at stage 1; Q correct only at stage 2 | 0.408993500000 | 0 to numerical precision | 0 | 1.11e-16 |
| Same generator | Both nuisance types wrong at both stages | 0.408993500000 | -0.091167490168 | -0.091167490168 | 2.50e-16 |
| Changed generator | All assignment mechanisms correct; both Q wrong | 0.412327000000 | 0 to numerical precision | 0 | 1.11e-16 |
| Changed generator | Both assignments wrong; all Q correct | 0.412327000000 | 0 to numerical precision | 0 | 5.55e-17 |
| Changed generator | Assignment correct only at stage 1; Q correct only at stage 2 | 0.412327000000 | 0 to numerical precision | 0 | 0 |
| Changed generator | Both nuisance types wrong at both stages | 0.412327000000 | -0.075305899868 | -0.075305899868 | 1.80e-16 |

**Interpretation:** this validates the implemented algebra of this finite enumerator, including the mixed robustness case and nonzero product bias. It does not validate exchangeability in human logs, text encoder sufficiency, real-model efficacy, estimator rates, or confidence coverage.

## 4. Required implementation checks

1. **Treatment identity:** exact rendered text, slate, index, eligibility masks, generator/receiver/evaluator versions, and true selection probability are logged before observing response.
2. **Assignment support:** probability vectors sum to one; excluded actions have target mass zero; deterministic padding after STOP has ratio one; missing candidates cannot be silently assigned positive target probability.
3. **Generator support:** same-generator evaluation asserts the version/protocol match. Changed generator evaluation either uses the full valid slate ratio or is rejected and recollected.
4. **Terminal convention:** use per-stage cost plus terminal quality, or total terminal utility, and verify equality between the two encodings on identical trajectories.
5. **Continuation labels:** Q and pseudo-outcomes carry a frozen continuation-policy identifier. Current Q is never evaluated under an unnamed or revised continuation.
6. **Candidate representation:** index alone cannot encode prompt semantics across histories. Exact text enters the critic; any omitted slate context has a documented exclusion assumption.
7. **Root partitions:** all branches, duplicate task variants, common-prefix states, and evaluator labels from one root stay in one split. No hidden test score enters serving history.
8. **Inference:** uncertainty uses root clusters; finite-policy holdout tests use a policy class fixed before viewing the holdout; nuisance clipping and proposal truncation are reported.
9. **STOP and failures:** STOP preserves the current answer and ends calls. Timeouts/failures are outcomes or separately modeled censoring, not deleted cases or convenient STOP conversions.
10. **Comparators:** include correct sequential Q regression, true-randomization IPW/DR, intentionally misspecified regression, fixed prompt sequences, and cost-matched prompt optimization baselines. A causal score beating an intentionally confounded marginal predictor alone is insufficient.

## 5. Unproved or not-yet-delivered claims

No convergence theorem for a particular Transformer architecture, valid simultaneous neural confidence band, universal text representation theorem, unmeasured-confounding robustness theorem, or unconstrained language-generation optimality theorem is asserted. No real-receiver trial or empirical superiority result is established by this proof file. No literature priority claim follows from these derivations. These limitations should remain visible in the manuscript and agent handoff until the relevant evidence exists.

The immediately reviewable statistical package is: explicit estimands; randomized candidate-selection design; exact identification, DR, and conditional-label algebra; policy-improvement/coverage bounds with stated assumptions; and a root-cluster evaluation protocol. The next empirical agent should implement and test those exact objects before adding broad generative training claims.
