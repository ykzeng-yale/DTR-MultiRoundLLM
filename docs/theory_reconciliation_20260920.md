# Reconciliation of the original theory and the experiments-derived draft

**Date:** 2026-09-20. **Scope:** targeted mathematical audit of stopping, selection, identification, support, ESS, certificates, information sets, and the Q11 headline. This is not a claim to have independently validated every result in the 3,097-line experiments draft or its literature/empirical source material. The original [theory.md](theory.md) is unchanged. The new [stopping addendum](theory_addendum_20260920.md) supplies the precise replacement results.

## 1. Q11 decision

**Primary claim: identification and honest evaluation of supported language-intervention regimes.** Horizon-aware valuation, stopping, and selection are applications with distinct estimands and evidence. A new causal critic's general superiority over correctly history-adjusted sequential regression is not the headline. The premise simulations do not establish that such superiority is impossible; they show that the original universal motivation was too strong. A null learned-selector pilot does not establish feature-class impossibility.

Suggested manuscript scope sentence:

> We study how experimental design and available decision-time information determine which adaptive language-intervention, stopping, and candidate-selection values can be identified and evaluated. Full recorded continuations permit unweighted evaluation of frozen stopping rules only when their pre-stop continuation mechanism matches the collector; changes to prompt selection or generation require supported reweighting or new executions. We evaluate practical benefits against matched-information, matched-cost alternatives without assuming that causal adjustment or multi-round feedback improves decisions.

The substantive original user goal—history-specific next-prompt value and optimization—remains a legitimate separate branch of the program. A candidate-bank picker trained on independent initial attempts is not its empirical completion. The selection/stopping study can be useful even if next-prompt improvement remains unproved.

## 2. The two documents concern different designs

| Object | Original theory | Experiments-derived draft | Reconciliation |
|---|---|---|---|
| Randomized intervention | Generate slate C before selecting index J; exact candidate text is logged | Randomize generator class K, then render/sample the class's message | Both are legitimate, but identify different compound interventions. Their propensities cannot be interchanged. |
| STOP | General treatment followed by absorbing padding | Analyst observes each prefix's score even if STOP was never executed | Addendum S1 bypasses STOP assignment using an additional prefix-functional assumption. It does not prove ordinary STOP positivity. |
| Continuation | Arbitrary named supported policy | Proposed stopping-only policy allegedly keeps all-eight-arm logger | W=1 only for that matching continuation. A policy forbidding three logger arms does not match it. |
| Information | Full history for identification; justified compression for learning | Analyst history includes hidden score; policy sees public features | Separate these information sets; a known analyst score is not a deployable stop signal. |
| Value | Net utility or separate quality/cost targets | Some sections assume raw Y−λC belongs to [0,1] | Raw utility can be negative. State actual range or normalize explicitly. |
| Inference | Root-cluster independent evaluation; fixed-policy versus optimal-value distinction | 176 text clusters, extrapolated ESS and certificate tables | Clustering defines the target/sampling model; an overlap ESS lower bound is not observed precision. |
| Evidence | Finite-law tests and planned real-model studies | Sibling replay, new simulations, frozen critic/selection pilots | Preserve source-specific estimands and validation status. Do not transfer results merely because the same method labels appear. |

The experiments draft labels its own approximately 31 withdrawals and is explicitly an input, not the original theory document. Withdrawal of its universal/nonasymptotic/novelty claims does not withdraw the original conditional identification and DR algebra. Conversely a “binding repair specification” is a coordination convention, not evidence that a repaired mathematical assertion is true.

## 3. Substantive findings and required corrections

### R01 — W=1 requires a matching continuation law, not merely observed STOP grades

**Sources:** experiments draft §0, T3, P5, §7/P23; repair specification R1–R3; requirements E1–E3.

**Finding:** correctly observing every prefix identifies accepting that prefix. It does not identify untaken prompt actions before the prefix. The same-class restriction also has to preserve within-class message generation, rendering, receiver/tool state, and measurement. A new target generator or selector changes the prefix law.

**Resolution:** use addendum S1 for matching continuation; use S2, `E_e[W_τ U_τ]`, for changed supported continuation; otherwise collect new executions. Full-rollout STOP evaluation has no STOP probability factor. Generic finite-action DR remains relevant to changed prompt policies.

**Executed check:** the finite law gives matching visible-stop direct/replay value `0.4880305375`. Changing continuation raises the direct target value to `0.66029695`; unweighted replay stays at `0.4880305375` and is biased by `−0.1722664125`. Prefix weighting recovers the target within `2.23e−16`.

### R02 — The stated stopping-only subclass conflicts with the admissible policy class

**Sources:** experiments draft §1 policy class, T3 items 2–3, P5 depth table, T20(c); requirements E1/E3.

**Finding:** `Π0` is said to match an eight-arm logger including diagnostic arms A6–A8, while every policy in `Πcp` is forbidden from using those arms. Except policies that never continue, these conditions cannot simultaneously hold. Thus the claimed `Π0 ⊂ Πcp` and weight-free admissible-policy interpretation are false as written.

**Resolution:** define a separate admissible continuation law and collect/reuse genuinely matching rollouts; or reweight the eight-arm data to the allowed target. An unweighted all-eight-arm stopping analysis can be a diagnostic but is not the declared deployable comparator. Merely deleting diagnostic rows may select task/history distributions; special conditioning constructions can work only after proving their exact law. Fixed-length rejection under a constant admissible-arm probability is one such special case, not a general guarantee for variable-depth or outcome-selected trees.

### R03 — STOP positivity does not “hold by degeneracy”

**Sources:** experiments draft A6/T8a; repair specification R1; requirements E2.

**Finding:** if STOP is never assigned, its treatment-assignment probability is zero. The reason it need not be randomized is the additional assumption that accepting at time k returns the already scored artifact without another treatment effect. A perfectly repeatable verifier does not establish that assumption, prefix preservation, or complete observation.

**Resolution:** state S2/S3 explicitly. Replace “positivity holds by degeneracy” with “STOP assignment positivity is unnecessary for the recorded prefix-functional estimand.” Retain ordinary support for every actually varied continuation action. STOP-triggered rewrite, deployment delay/decay, or differing scoring time needs separate measurement.

### R04 — The ESS bound is inverted into an unsupported actual-ESS claim

**Sources:** experiments draft P5, T3 scope note, T20 tables; repair specification R1/R2.

**Finding:** from `EW=1`, `W≤64`, one obtains `EW²≤64` and population proxy `n_eff≥n/64`. At n=176, 2.75 is a **lower bound**, not the actual ESS and not evidence that every depth-two policy has fewer than three effective clusters. The sample ESS is random and is not itself guaranteed by this population inequality.

**Resolution:** call 176,22,2.75 worst-case lower bounds under the chosen population proxy; compute empirical weight/score diagnostics and root-cluster uncertainty for each frozen policy. No universal prohibition on off-policy evaluation follows solely from the bound. Fresh paired execution can still be the preferred practical design for other reasons.

**Executed counterexample:** a slightly changed eight-arm target at each of two decisions has second moment `1.00320256` and actual population ESS `175.4381`, although the coarse upper bound remains64 and lower bound remains2.75.

### R05 — A vacuous sufficient certificate is not an impossibility theorem

**Sources:** experiments draft introductory warning1, T20; requirements open question3 and adversarial finding1/17; repair specification R4.

**Finding:** a sufficient worst-case planning relation of the form `n≥8ML/gap²` does not prove that all valid nonasymptotic tests need that sample size. Treating a worst-case second-moment substitute as an observed empirical variance also overstates what an empirical-Bernstein calculation implies. A single broad bound's failure cannot establish “no certificate is available” or that every weighted comparison is arithmetically impossible.

**Resolution:** withdraw the proposed certificate as a project deliverable if its computed interval is uninformative, but say precisely which bound and data it concerns. Retain optional correctly scoped fixed-policy/finite-class bounds such as addendum S8. Use paired score differences and actual root variation for practical precision. A bootstrap interval is a separate inferential procedure, not a replacement proof of finite-sample coverage.

**Executed counterexample:** independent ±1 paired differences all observed as+1 yield an exact one-sided test with null event probability at most `2^-176≈1.04e−53`. This refutes universal impossibility, not the observation that the project's small current gap may be hard to resolve. No claim about the project's actual test power follows from the constructed example.

### R06 — Utility range and clipping statements need correction

**Sources:** experiments draft T20(a/b); raw outcome definition.

**Finding:** `Y∈[0,1]`, positive cost, and λ=.01 do not imply `Y−λC∈[0,1]`. If `C∈[0,Cmax]`, its range is contained in `[−λCmax,1]`. Clipping a negative weighted utility need not have downward bias. Also the claim that `E[min(W,M)²]≤M EW` fails when an outcome is signed is algebraically false: the inequality concerns weights alone, and `min(W,M)²≤MW` holds for every W≥0 independent of the outcome's sign.

**Resolution:** specify actual score range and rescale if needed; distinguish clipping-bias sign from the weight second-moment bound. Do not import unit-range constants before checking the utility convention.

### R07 — The +0.046 stopping “headroom” is not a fully observed pathwise oracle bound

**Sources:** `docs/audits.md`, headroom paragraph; experiments draft P22; repair constants table.

**Finding:** the source audit imputes a23.9% repair rate for prematurely stopped failures to obtain0.737 from0.691. That is an explicitly optimistic extrapolation into missing suffixes. It is not the observed maximum over complete recorded trajectories required by addendum S5.

**Resolution:** call it an optimistic assumption-dependent sibling-log calculation. A recorded full-rollout oracle bound must be recomputed on complete trajectories with the same continuation and cost target. It cannot automatically supply the effect size, attainable information gain, or ceiling of the proposed new study.

### R08 — A smaller public information set does not prove state insufficiency

**Sources:** experiments draft §1 policy class, T3 final paragraph, T8b; requirements open question5.

**Finding:** `F^O ⊊ F^A` proves that some analyst information is omitted. It does not prove that omitted information changes any needed conditional transition/value. A proper subset can be sufficient; an insufficient current feature vector may still be part of a sufficient full public history. Also current feature sigma-fields need not be nested and cannot automatically be called a filtration.

**Resolution:** define the increasing public filtration, then use the Snell recursion in addendum S3. For a fixed deterministic grader, a hidden grade can still be mathematically a function of public task/artifact; exclusion from model inputs is an operational computation restriction, not automatically a strict sigma-field separation. Either specify latent evaluation assets or state the approved feature/policy class explicitly. For a compressed-state Bellman claim impose the original theory's explicit sufficiency conditions. Without them, a learned feature-based policy remains evaluable as a fixed policy, and a finite candidate search is valid with honest evaluation; it is not necessarily optimal in the unrestricted history policy class.

### R09 — Extreme success probabilities do not establish nonregular optimum mass

**Sources:** requirements “exceptional-law problem” and adversarial finding24; experiments draft related limitations.

**Finding:** tasks with success probability below.05 or above.95 need not have zero treatment contrast or ties between optimal actions. Marginal response-rate mass does not identify an exceptional law for the optimal-value functional. Evaluation of an independently frozen policy is an ordinary mean even if its outcomes often equal0 or1.

**Resolution:** diagnose action-value gaps/ties under the actual continuation if studying the optimal-value functional; do not infer them from a fitted distribution of marginal task success. Do not mandate m-out-of-n bootstrap merely from extreme outcome probabilities. Prefer separate evaluation of the frozen learned rule.

### R10 — Hidden generator memory is a risk, not automatic failure of randomized weighting

**Sources:** experiments draft T3 cancellation paragraph; requirements E8/E9; repair specification R7.

**Finding:** action-dependent latent memory can be included in the common environment transition law. When action assignment is genuinely randomized with observed propensities and the latent dynamics are unchanged, action ratios still cancel common latent/environment factors and identify the marginal observed trajectory after integrating hidden state. The claim that every carried state necessarily destroys cancellation is too strong.

**Resolution:** addendum S10 gives the exact sufficient conditions. Stateless calls are a useful engineering safeguard, particularly for faithful branch restoration. A fresh process or byte-identical stochastic output is not a necessary mathematical condition; neither does a hash test prove mechanism invariance or independence. Assignment confounding, mechanism shift, interference, and branch-state mismatch must be checked separately.

### R11 — A stopping/selection pilot is not the next-prompt causal experiment

**Sources:** COORDINATION K1/Q11; `docs/g1a_selection_pilot.md`; new experiment plans.

**Finding:** a picker chooses among already generated candidate outputs. It changes the return/accept decision, not what feedback causes a receiver to generate next. Independent initial samples and multi-round continuation histories have different joint laws, costs, information, and scientific targets. “First passing candidate” can be a stopping rule, whereas argmax over the full bank is an end-of-budget selector.

**Resolution:** use separate target rows and cost accounting. Theorem S7 identifies bank selection values under a fixed joint candidate law. The original theory evaluates changes to prompting trajectories. A candidate selector inspecting all K candidates pays for K candidates; retrospective early acceptance cannot erase the later computation used to choose it.

### R12 — Pilot nulls do not rule out a whole feature family

**Sources:** `docs/g1a_selection_pilot.md`, “not reachable from this feature set” and “ruled out” paragraphs.

**Finding:** two fitted models not outperforming the baseline do not prove the Bayes-optimal selector measurable in those features cannot improve. Limited training size, fitting error, tuning, uncertainty, and candidate dependencies remain possible. The null supports absence of demonstrated gain for those procedures on those data.

**Resolution:** retain the negative result and intervals; remove feature-class impossibility wording unless an actual information bound or identified Bayes ceiling is supplied. Agreement features are a new intervention/information/compute resource; compare against published strong selectors and count probe-generation/execution costs.

### R13 — Correlation adjustment and horizon are separate dimensions

**Sources:** COORDINATION Q11 and premise findings C1–C4.

**Finding:** full-history sequential regression is a causal identification estimator under exchangeability, as already stated in the original theory. It is not a deliberately deficient “noncausal” baseline. A myopic reward predictor versus a continuation-specific Q predictor differs in horizon target even in randomized data. Effects and rankings also need not react identically to confounding.

**Resolution:** Q11 prioritizes identification/honest evaluation; experimentally separate assignment adjustment, history representation, and continuation horizon. Name every blip's continuation. An apparent estimator gain graded against another continuation is a target mismatch, not an improvement. The parallel implementation audit is checking those numerical target definitions separately.

### R14 — Clustering and target weighting must be explicit

**Sources:** experiments draft §1, requirements clustering question, design E3 §12.

**Finding:** text similarity clustering is a reproducible grouping rule but does not prove independence. Equal family averages estimate a family-weighted mean; equal task averages estimate a task-weighted mean. Pairing can remove shared components of difference variance, but does not eliminate all between-task heterogeneity or create independent seeds.

**Resolution:** state a target population, retain roots/families across splits, choose weights before outcomes, and report clustering sensitivity. Do not transfer176 as a universal independence count into unrelated448/485-task sibling analyses. A fixed benchmark can support a finite-population target distinct from hypothetical iid task sampling.

## 4. Replacement experiment contract for the stopping branch

1. Name a single admissible frozen continuation mechanism. For weight-free evaluation, every candidate policy differs only in public stopping/acceptance decisions before that mechanism would run next.
2. Record every prefix through a common cap, the information genuinely available at that prefix, analyst-only scores, and prefix-computable costs. Record actual full-collection expenditure separately.
3. Demonstrate that a stop accepts the recorded artifact without an extra rewrite/effect and that later calls do not alter earlier scores or states. Preserve failures and missingness explicitly.
4. Train and freeze public stopping rules on separate roots. Hidden scores may provide training labels; they cannot enter held-out serving features, stopping choices, or post hoc policy selection.
5. Evaluate frozen rules by paired independent-root averages only after the matching-mechanism check. If continuation changes, use the supported prefix ratios or fresh paired execution.
6. Report score difference, cost difference, empirical uncertainty, support/completeness diagnostics, and an observed full-path oracle only where it is genuinely observed. Do not substitute optimistic suffix imputation.
7. Keep independently sampled candidate selection and adaptive feedback-content experiments separate. A combined system needs an explicitly defined joint policy and fresh evaluation.

## 5. Executed checks and artifact audit

New source: `scripts/check_stopping_identities.py`; tests: `tests/test_stopping_theory.py`. Executed commands:

```sh
python3 scripts/check_stopping_identities.py --output work/stopping_identities_20260920.json
uv run --extra dev pytest -q tests/test_stopping_theory.py
```

Result: **9 tests passed**, covering 10 identity/counterexample entries. The main stochastic two-decision law is enumerated exactly over512 complete paths, with no Monte Carlo or model calls. Changed-continuation prefix weighting matches direct execution within `3.34e−16`. Additional checks show complete-case bias (.74 versus truth.50, corrected by observation weights), hidden-label information gap (.75 oracle versus.50 public), diagnostic-branch deletion bias (.10 versus.50), and the ESS/certificate counterexamples above.

The machine-readable result is `work/stopping_identities_20260920.json` and records source SHA-256 `cb6273aa3d4be4461a66cdd5290bbbb2227bbac4113363858b3615b897040a1b`, full configuration, runtime, and zero model calls/spend. The root workstream may preserve this result in the public results bundle. Re-run to a new output path; the script refuses accidental overwrite.

The independent implementation reviewer checked addendum S1/S2 and found no blocker in the prefix-coupling assumptions or stopped-weight indexing. The reviewer also confirmed that the archived routing logs naturally stop; they are not complete full rollouts and therefore cannot establish S1 values for policies needing their missing later prefixes.

These results validate the finite-model algebra and reproducible counterexamples. They do not verify real-data prefix completeness, public-feature exclusion, receiver stability, task independence, or empirical performance. Literature priority claims and exact real-model effect estimates are outside this mathematical audit and remain subject to the parallel source/implementation checks.

## 6. Follow-up audit of the new selection decision (origin/main 0ee7666)

**Read-only source:** `git show origin/main:docs/selection_decision.md`, inspected 2026-09-20. This section audits the proposed harvestable-stratum bound and the scope of its STOP recommendation. The original decision document is not edited. The parallel implementation audit covers the new G1b/G1c scripts and their concrete cohort construction.

### Exact bound that survives

Fix a joint bank of `r` candidate outputs, their binary scores `Y_1,...,Y_r`, the task distribution, and a baseline selector `B` that returns one bank member. Let `S=\sum_jY_j` and let `J` be any other selector over **the same bank**. Randomized ties can be represented by an independent selector seed. Then

$$
E(Y_J-Y_B)\le E(\max_jY_j-Y_B)
=P(0<S<r,\ Y_B=0)
=P(0<S<r)P(Y_B=0\mid0<S<r).
\tag{R15}
$$

**Proof.** `Y_J\le\max_jY_j` for every bank. For binary outcomes, `\max_jY_j-Y_B=1` exactly when at least one candidate succeeds and the baseline returns a failure. That cannot occur when all candidates succeed or all fail, so the event is the displayed mixed-stratum event. Take expectations and factor its probability. ∎

This is an exact **oracle upper bound on improvement over the specified incumbent for the specified bank law**. It requires no beta-binomial model and no independence among candidates. It is generally not attained by a public selector. Addendum S7 gives the sharper allowed-information upper value `E[max_j E(Y_j|G)]`; subtracting the baseline value yields its corresponding gain ceiling. A computable exact empirical R15 value is a descriptive ceiling on that empirical bank, not a confidence upper bound on a new-task population unless sampling uncertainty and the bank-generation law are addressed.

For randomized baseline selection averaged over ties/order, the same identity holds after integrating the selector seed. Fractional baseline per-task scores represent expected failure probability on that bank; they must not be replaced by arbitrary deterministic first-choice counts.

### The beta-binomial calculation is a model-based forecast

If—and only if—the candidate outcomes are conditionally iid Bernoulli(`p`) within task and `p\sim Beta(α,β)`, with a fixed bank size r,

$$
P(0<S<r)=1-\frac{B(α+r,β)}{B(α,β)}
             -\frac{B(α,β+r)}{B(α,β)}.
\tag{R16}
$$

**Proof.** Conditional probabilities of all successes and all failures are `p^r` and `(1-p)^r`. Integrating each against the beta density gives the two beta-function ratios. Subtract from one. ∎

Fitting `α,β` gives a plug-in prediction, not a distribution-free upper bound. Include parameter uncertainty, fixed versus variable r, candidate dependence, and cohort selection. R16 alone does not determine `P(Y_B=0|mixed)`, which depends on the incumbent's public signal and selection behavior. It therefore does not predict net harvestable improvement from task difficulty alone.

At fixed mean and r≥2, `p^r+(1-p)^r` is convex, so a **mean-preserving contraction in difficulty** increases the mixed probability. That explains one direction of the proposed mechanism under an appropriate distribution comparison. It does not prove that selecting moderately difficult tasks improves public observability, the incumbent-relative gap, cost, or attainable gain. Requiring both fitted beta parameters>1 is neither necessary nor sufficient for a useful selector study. A hard .05 ceiling threshold is a project utility/design choice, not a mathematical impossibility boundary.

### Why “33 effective observations” and inevitable nulls do not follow

In the reported 3B bank,33/448 is the fraction of tasks on which an oracle could improve the incumbent. It is not the number of independent observations for the paired-policy estimand. All448 roots contribute to its mean and uncertainty, subject to the actual root/family independence model. The67 mixed tasks that the baseline already solves can contribute **negative** gains if a proposed selector degrades them; they do not disappear from the scientific problem.

For deterministic binary returned scores, a paired difference `D=Y_J-Y_B` lies in `{-1,0,+1}`. Write `p_+=P(D=1)` and `p_-=P(D=-1)`. Then

$$
E D=p_+-p_-,\qquad
\operatorname{Var}(D)=p_++p_--(p_+-p_-)^2.
\tag{R17}
$$

**Proof.** `D²=1` exactly on discordance, so `ED²=p_++p_-`; subtract the squared mean. ∎

The independent-root sample mean has variance `Var(D)/n`, not a denominator equal to the number of oracle-opportunity events. For tie-averaged selectors the paired score is fractional, and its actual variance should be used instead of (R17). In the artificial best-case oracle difference `D=1` on33/448 and0 elsewhere, the ordinary independent-root standard error is approximately.01234, so this ceiling is not inherently undetectable at448 roots. This is an illustration of the logical error, not an attained public-selector result or a proposed post hoc test.

The reported0.0737 ceiling is already **net of the incumbent's harvested mixed tasks**: approximately `(100/448)×(33/100)`. Saying that two thirds of that0.0737 is gone before selection starts subtracts the incumbent's advantage twice. The gross mixed mass is approximately0.223; the residual oracle gain is0.0737.

Consequently neither the bound nor the small opportunity count makes the observed nulls inevitable. Whether a practical effect is worth detecting depends on its attainable size, harm rate, paired variance, root population, costs, and a prespecified decision threshold. The bound limits scale; it does not establish inability to learn.

### Reconciling the new fixed-bank 7B signal without mixing budgets

The corrected local result in [selection_corrected_results_20260920.md](selection_corrected_results_20260920.md) evaluates a separate frozen four-initial-candidate bank:561 roots,336 training roots,225 evaluation roots, all initial candidates retained regardless of later routing, and a permutation-averaged visible selector. Its 7B logistic improvement is **+0.02852**, exploratory task-level95% interval **[+0.01186,+0.04518]**. The internal read-only reconstruction is in `results/selection_review_20260920.json`.

This result is compatible with R15 and does not establish a low-cost stopping advantage. All four candidates are generated and charged for both selectors; the comparison is not against an approximately one-call adaptive resampler. It also uses another cohort/baseline definition than the G1a/G1b/G1c summaries, so subtracting their displayed means or importing their oracle ceiling is invalid. Label reuse, four model/learner comparisons, unresolved family dependence, and full-test versus hidden-only measurement prevent a confirmatory claim.

Nevertheless, a mathematical conclusion that **no public-feature selector can recover anything in this general receiver/benchmark setting** is not justified. The corrected exploratory signal is a concrete reason to preserve a bounded fresh fixed-bank validation hypothesis. Conversely, it does not refute a cost-based decision to decline an agreement gate that requires extra draws while offering little gain at a specified adaptive budget.

### Decision wording that the evidence supports

Treat “STOP” as a **resource-allocation recommendation for the tested small-bank agreement procedures and specified budget**, conditional on the implementation audit, not as a proved inability to answer the entire selection-and-stopping question or a theorem invalidating all critic/prompt-policy work. The oracle bound does not cover changing the bank generator, new feedback interventions, richer public evidence, another bank size, or another population. Those are different targets that need their own costed evidence.

Preserve the exact fixed-bank oracle decomposition as a diagnostic feasibility calculation; label beta-binomial extrapolation and its uncertainty; retain the negative agreement results with their intervals; and separately retain the positive but exploratory fixed-bank logistic hypothesis. A single bounded fresh evaluation with frozen hypotheses can adjudicate the latter. Any attempt to establish an advantage at the adaptive-baseline cost requires its own prespecified sequential sampling/selection policy and an actual matched-cost comparison.
