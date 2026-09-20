# A landmark experiment for personalized next-prompt choice

**20 September 2026. Status:** narrow design theory with proofs and exact numerical checks; no new receiver calls or prospective LLM validation. These are standard randomized-treatment, conditional-expectation and policy-regret arguments specialized to the planned experiment, not claims of foundational novelty. The general causal and policy-learning sources are recorded in [the main theory, §12](theory.md#12-source-grounding); [the stopping addendum](theory_addendum_20260920.md) supplies the separate stopping scope. The governing scientific decision remains [the coordinating judgment](scientific_judgment_20260920.md).

**Question:** on fresh roots reaching a declared public conversation prefix, does choosing among a small set of frozen prompt interventions from public history improve expected final quality over a competent fixed or heuristic choice, with the receiver and subsequent continuation held fixed? This is one decision embedded in a conversation. It is neither a comparison of arbitrary language strings nor a validation of repeatedly deploying the selector at every future turn.

## 1. Freeze the intervention before estimating its value

An independent root is a task or, when tasks are dependent, the predeclared task family. Let `H` be the public prefix collected under a frozen prefix policy `r`, and `C` the complete candidate slate generated **before** branch assignment by a frozen generator `G`. Write `Z=(H,C)` for the public decision record and `mu` for its distribution. Eligibility must be determined from pre-assignment public information. Selecting roots because the initial answer fails a hidden test changes the population and gives an undeployable eligibility rule.

For the simplest experiment every root has the same finite set of indices `A={1,...,K}`. An index means a fully specified intervention, including exact rendered text and which prior context is retained. A history-specific feedback candidate may have different text across roots; its generation rule and realized text remain part of the contract. Independent restart can be an index, but it deliberately resets receiver context: its effect is a repair-versus-restart intervention effect, not a pure wording contrast. "Same prefix" means a common pre-intervention checkpoint, not that a restart must retain that checkpoint's answer in its receiver input.

Freeze the receiver `M`, evaluator, decoding law, environment reset, and remaining continuation `nu`. Continuation means the same **policy mapping** at subsequent histories, not necessarily the same realized messages or outputs. One further receiver call followed by scoring is a particularly transparent choice. A timeout/failure must have a prespecified endpoint and realized cost; deleting it violates the assigned-treatment target. Truly unobserved outcomes require their own missingness argument. No theorem below turns missingness into STOP.

Let `B` denote the complete root checkpoint, including any persistent state or latent evaluation assets shared by its branches; `Z` is a function of `B`. Define

$$
q_a(B)=E[Y^{a,\nu}\mid B],\qquad
Q_a(Z)=E[q_a(B)\mid Z]=E[Y^{a,\nu}\mid Z],\quad 0\le Y\le1.
\tag{L1}
$$

For quality, `Y` may be binary benchmark success. Costs are separate measured outcomes until a utility conversion is justified and frozen; a bounded utility can be rescaled for the bounds below. Changing the evaluator, receiver, generator, continuation, or budget changes the scientific contract, not just the estimator.

`Q_a(z)-Q_b(z)` is a **history/slate-conditional mean effect under nu**. Repeated branches do not reveal the joint potential outcomes of one realized future conversation. If all outcome-relevant persistent state is determined by `Z`, then `q_a(B)=Q_a(Z)`. Otherwise repeated seeds at one checkpoint estimate `q_a(B)`, while the public conditional mean averages over checkpoints sharing that public record. Conditional independence of branches given `B` does not imply their independence given `Z`.

The formal optimum below allows all measurable functions of `Z`. An implementation restricted to features `X=phi(Z)` instead has `Q_a^X(X)=E[Q_a(Z)|X]`, or a still smaller declared policy class. Do not call a feature-class optimum the unrestricted public-history optimum. With a deterministic hidden grader, mathematical measurability in raw task text can exceed permitted computational access; use the operational feature/policy restriction explicitly, rather than assuming that deleting a grade column proves a smaller sigma-field.

## 2. Identification by branch execution, with its actual assumptions

The following conditions concern the planned data, not the existing receiver-routing corpus.

1. **Branch consistency and isolation.** Restoring `B` and applying index `a` executes exactly the declared `a,M,nu` law. Prior branches do not change shared files, memory, tools, evaluator state or later branches. A random execution order helps diagnose drift but does not prove absence of interference.
2. **Randomization or complete intervention execution.** In a randomized branch-slot design, `A_ir` is drawn with known probability `e_ir(a|Z_i)` using randomness independent of the checkpoint's latent state and branch potential outcomes, conditional on `Z_i`. The basic formulas use a frozen schedule, not response-adaptive branch allocation. Alternatively execute a predeclared positive number `R_ia` of restored branches for every candidate at every root. Their action-specific sample means then need no action-assignment weight.
3. **Support.** Every candidate whose Q or value is requested has positive assignment probability, or is actually executed in the complete design. Useful precision additionally requires non-negligible probabilities/counts. A finite randomized slate does not identify a new string or a new generator.
4. **Observation and sampling.** Outcomes are observed under the frozen failure rule. Roots have the declared sampling law; all branches, prefixes and repeated seeds of a root stay in the same split. For iid-root formulas, independence is at this root unit. Families of varying size need a declared family-versus-task weighting target.

### Proposition L1: the identified policy target

For any frozen public policy `d(a|Z)`, supported by assignment,

$$
V_\mu^\nu(d)=E_\mu\sum_a d(a|Z)Q_a(Z)
=E\left[\frac{d(A|Z)}{e(A|Z)}Y\right].
\tag{L2}
$$

With complete execution, let `bar Y_ia` average the `R_ia` branches of action `a`. For policies `d,beta` frozen independently of evaluation roots,

$$
D_i=\sum_a\{d(a|Z_i)-\beta(a|Z_i)\}\bar Y_{ia},
\qquad E[D_i]=V_\mu^\nu(d)-V_\mu^\nu(\beta).
\tag{L3}
$$

**Proof.** Conditional on `Z`, randomization gives `E[1{A=a}Y|Z]=e(a|Z)Q_a(Z)`. Divide by the positive probability, multiply by `d`, and sum. For complete execution, branch consistency gives `E[bar Y_ia|B_i]=q_a(B_i)` for a prespecified replicate count. Taking another expectation given `Z_i` yields `Q_a(Z_i)`. Linearity proves (L3). Independence among branches is unnecessary for these mean identities; it is an extra condition for some variance and concentration formulas below. ∎

Direct outcome regression and a one-decision augmented score are legitimate alternatives under the same target. The experiment does not need a longitudinal DR estimator merely because its prefixes came from conversations. Randomization protects identification; it does not guarantee a particular fitted Q learner improves ranking. Complete branch execution also does not justify selecting the best action from those evaluation outcomes and using (L3) as if that action had been frozen.

STOP is a separately named comparator. If stopping means accepting the already observed, invariant initial artifact, its analyst score may be reused without randomized STOP execution under the prefix conditions of the stopping addendum. This does not identify an unexecuted repair. STOP and continuing differ in cost, so the prompt-content mechanism contrast and the total-cost decision must be reported distinctly.

## 3. Zero average arm effects do not exclude useful personalization

Define the public conditional-mean oracle, best constant index, and their difference:

$$
V_{\rm pub}^*=E\max_a Q_a(Z),\quad
V_{\rm fixed}^*=\max_a E Q_a(Z),\quad
\mathcal H_{\rm pub}=V_{\rm pub}^*-V_{\rm fixed}^*\ge0.
\tag{L4}
$$

Both maxima use the same supported candidate indices. For varying eligible sets, replace constant indices by an explicitly admissible baseline class; a constant index absent from some slates is not a comparator. In (L4), "fixed" refers to a fixed index/generation recipe; it need not be a literal constant string.

### Proposition L2: the two-action personalization identity

For `A={0,1}` and `Delta(Z)=Q_1(Z)-Q_0(Z)`, the average arm effect is `E Delta`, whereas

$$
\mathcal H_{\rm pub}
=E\Delta_+-(E\Delta)_+
=\frac{E|\Delta|-|E\Delta|}{2}.
\tag{L5}
$$

**Proof.** The pointwise optimum is `Q_0+Delta_+`; the best constant value is `E Q_0+(E Delta)_+`. Subtract and apply `x_+=(|x|+x)/2`. Nonnegativity follows from the triangle inequality. ∎

**Exact example.** A fair public state has action means `(.8,.4)` in state zero and `(.4,.8)` in state one. Both arms average `.6`; their ATE is zero. A selector using the state has value `.8`, giving **.2** personalization benefit. Requiring a significant average arm difference before fitting/evaluating a selector would reject this favorable case. Conversely, constant means `(.8,.4)` give a large ATE and no benefit over the best fixed action.

Report average arm effects, effect modification and independent learned-policy value as different quantities. A weak or nonsignificant ATE is not the personalization futility gate. Nor is the presence of heterogeneity sufficient: its ranking must be predictable from allowed features, learnable at the available root sample size, and valuable relative to the chosen competent comparator.

## 4. Three oracles that must not be interchanged

For balanced complete branches, define

$$
V_{\rm checkpoint}^*=E\max_a q_a(B),\qquad
V_{{\rm sample},R}=E\max_a\bar Y_a.
\tag{L6}
$$

### Proposition L3: the information gap and the maximum-of-noise gap

For conditionally unbiased branch means,

$$
V_{\rm pub}^*\ \le\ V_{\rm checkpoint}^*\ \le\ V_{{\rm sample},R}.
\tag{L7}
$$

If each arm has at least `R_min` conditionally independent `[0,1]` replicates given `B`, then

$$
0\le V_{{\rm sample},R}-V_{\rm checkpoint}^*
\le\sqrt{\frac{\log K}{2R_{\min}}},\quad K\ge2.
\tag{L8}
$$

The upper bound can be truncated at one. No independence **between arms** is required. It controls only sampling optimism relative to the checkpoint oracle, not the information gap between checkpoint and public oracles.

**Proof.** Conditional Jensen for the convex maximum gives `max_a E[q_a(B)|Z] <= E[max_a q_a(B)|Z]`, proving the first inequality. Apply the same argument to branch means given `B` for the second. For the bound, set `E_a=bar Y_a-q_a(B)`. The bounded-variable exponential inequality gives `E[exp(lambda E_a)|B] <= exp(lambda^2/(8R_a))`. For completeness, a centered variable on an interval of length one has log-mgf second derivative equal to its variance under exponential tilting; that variance is at most `1/4`. Its log-mgf and first derivative vanish at zero. Integrating the second-derivative bound twice yields `log E exp(lambda X) <= lambda^2/8`; conditional independent sums yield the displayed mean bound. Therefore

`E[max_a E_a|B] <= log(sum_a E exp(lambda E_a|B))/lambda <= log(K)/lambda + lambda/(8R_min)`.

The first step follows from `exp(lambda max E_a) <= sum exp(lambda E_a)` and concavity of log. Also `max_a bar Y_a-max_a q_a <= max_a E_a`. Optimize over `lambda>0` at `sqrt(8 R_min log K)` and average over `B`. ∎

In the homogeneous binary null `Q_0=Q_1=.65`, two independent single branches give expected sampled maximum `1-(1-.65)^2=.8775`, despite the attainable mean optimum being `.65`. The **.2275 apparent headroom is entirely noise selection**. Replacing a branch by an `R`-replicate mean reduces this optimism; it does not turn its maximum into an unbiased oracle estimate.

If an unobserved fair root state produces means `(.8,.4)` or `(.4,.8)` while public information is uninformative, `V_pub^*=.6` and `V_checkpoint^*=.8`. As replication grows, the sampled maximum tends to `.8`, not `.6`. This remaining .2 gap is inaccessible information, not finite-replicate noise. The same issue arises when the learner uses an insufficient public feature map, even if the raw history contains more useful information.

**Why splitting seeds within a root is insufficient.** In that latent-state example, use one training branch per arm at a test root, select the larger observed outcome (tie to zero), and evaluate the chosen arm on fresh seeds at the same root. Its expected held-out value is `.68`, exceeding the `.6` pre-intervention public oracle: the training branch labels have revealed information about the root. This is a valid value for a more expensive procedure allowed to inspect those trial outcomes, not for the declared public-prefix-only selector. It is not cured by independent evaluation seeds. Fit, tune and freeze the selector on other roots; evaluation-root branch scores must remain analyst-only.

## 5. A useful finite-action regret bound, and what it does not guarantee

Let an independently trained estimate `hat Q_a(z)` define `hat d(z)=argmax_a hat Q_a(z)` with fixed measurable tie breaking. It uses only the eligible, supported candidates. Write `epsilon(z)=max_a |hat Q_a(z)-Q_a(z)|`.

### Proposition L4: ranking regret under conditional-mean error

Conditional on training data,

$$
0\le V_{\rm pub}^*-V_\mu^\nu(\widehat d)
\le2E_\mu\epsilon(Z).
\tag{L9}
$$

At any history with a unique best arm and best-versus-second gap greater than `2 epsilon(z)`, the estimated greedy choice is correct. If optimization is approximate, with `hat Q_(hat d) >= max_a hat Q_a-eta(z)`, add `E eta(Z)` to the regret bound.

**Proof.** Let `a*` maximize the true Q at `z`. Then

`Q_(a*)-Q_(hat d) = (Q_(a*)-hat Q_(a*)) +(hat Q_(a*)-hat Q_(hat d)) +(hat Q_(hat d)-Q_(hat d)) <= 2 epsilon(z)+eta(z)`.

For exact maximization, a wrong selection would have true loss at least the best-versus-second gap, contradicting the pointwise bound if that gap exceeds `2 epsilon(z)`. Integrate the pointwise inequality. ∎

For a particular frozen comparator `beta`, write `H_beta=V_pub^*-V(beta)`. Then

$$
V(\widehat d)-V(\beta)\ge H_\beta-2E\epsilon
\tag{L10}
$$

for exact maximization. This is a sufficient condition, not an estimable deployment certificate unless both headroom and error are honestly controlled. An uncalibrated ensemble spread does not supply `epsilon`. For a restricted feature record `X`, apply the same result to `Q^X`; it controls regret to that record's oracle. It cannot recover information discarded by the feature map.

For a fixed checkpoint with independent branch replicates, a union of bounded-mean tail bounds gives

`P(max_a |bar Y_a-q_a(B)| > epsilon | B) <= 2K exp(-2 R_min epsilon^2)`.

This controls seed noise around `q(B)`, not generalization error of a fitted language model around `Q(Z)`, nor the public-information gap. More branches are useful for conditional-mean calibration; they are not a replacement for more diverse independent roots.

## 6. Paired-root inference and the value of extra branches

Condition on all training/development data so the evaluation policies are fixed. Let `c_a(Z)=d(a|Z)-beta(a|Z)` and `m(B)=sum_a c_a(Z)q_a(B)`. If arm replicates are independent conditional on `B`, (L3) has

$$
\operatorname{Var}(D_i)
=\operatorname{Var}\{m(B_i)\}
+E\sum_a \frac{c_a(Z_i)^2\sigma_a^2(B_i)}{R_{ia}},
\quad \sigma_a^2(B)=\operatorname{Var}(Y^a\mid B).
\tag{L11}
$$

**Proof.** Given `B`, the means and independent replicate variances are `q_a` and `sigma_a^2/R_a`, so the conditional variance of the linear contrast is the sum in (L11). Apply total variance. ∎

With equal replicate counts and a declared coupling of the arms within each seed block, replace the sum by `c(Z)^T Sigma(B)c(Z)/R`, where `Sigma` is the outcome covariance matrix for one block, and require independent blocks conditional on `B`. Coupling can reduce or increase the variance of a contrast; merely giving arms the same integer seed is not a proof of beneficial covariance. Marginal receiver laws must remain correct.

For iid roots, `Var(bar D)=Var(D_i)/n`, and the sample variance of `D_i` divided by `n` estimates it. A normal/Wald interval is asymptotic with adequate independent-root count and nondegenerate variance, not a universal finite-sample certificate. In a complete-branch quality comparison `D_i` lies in `[-1,1]`; conditional on training, a conservative two-sided finite-sample radius is `sqrt{2 log(2/alpha)/n}` by bounded-root concentration. Such a radius can be practically uninformative, which is a precision limitation, not proof that all honest intervals are impossible. IPW scores need their larger propensity-dependent range.

Even with infinite branch repetition, (L11) leaves `Var(m(B))/n`. Furthermore,

`Var(m(B))=Var(E[m(B)|Z])+E Var(m(B)|Z)`.

The second term captures persistent root information absent from the decision record. Assuming iid branches given `Z` incorrectly drops it. For multiple prefixes per root, first form the prespecified weighted root aggregate of their contrasts and then estimate variance across roots; do not treat prefixes as independent roots. Family sampling may require equal-family aggregates or declared size weights, depending on the target.

**Exact example.** At fair states use `(Q_0,Q_1)=(.2,.6)` or `(.8,.4)`. The fixed arm-one minus arm-zero contrast has between-root variance `.16`, within-root independent-branch variance `.40/R`, and total `.26` at `R=4`. Treating the `4n` branch pairs as iid gives `.56/(4n)=.14/n`, while the correct variance is `.26/n`. Increasing seeds without increasing roots does not fix that underestimate.

The inferential target is the value of the particular trained selector, conditional on its training data. Tuning it on test contrasts or repeatedly choosing a new split breaks this interpretation. Cross-fitting different trained selectors estimates their average value under the declared folds; it is not automatically a test of the final all-data-trained selector. A locked new-root test remains the simplest confirmatory design.

## 7. Landmark distribution is not global policy occupancy

If two regimes use the same prefix law `r`, differ only in the landmark action, and then follow `nu`, their whole-regime value difference is exactly (L3). All earlier contributions are common. If the experiment samples only eligible landmarks and both policies agree outside them, the population value difference is `P(eligible)` times the conditional eligible-population contrast, under the same eligibility law. A useful conditional effect should not be reported as the unconditional task-population effect.

If the selector is later deployed repeatedly, its earlier choices change the distribution of subsequent histories. The new value does not follow from averaging landmark Q values over `mu`. Even for a one-decision target with unchanged conditional Q, transport from `mu` to `mu*` requires support and the appropriate history/slate ratio `w=dmu*/dmu`:

$$
V_{\mu^*}(d)-V_{\mu^*}(\beta)
=E_\mu\left[w(Z)\sum_a(d_a-\beta_a)Q_a(Z)\right].
\tag{L12}
$$

**Proof.** This is the definition of the Radon–Nikodym change of measure applied to the integrable conditional contrast. ∎

A public-record shift can also change the latent checkpoint law given that record, in which case invariance of Q fails and history reweighting alone is insufficient. Changing continuation changes Q even with identical landmark frequencies. These are assumptions to test or avoid, not consequences of action randomization.

**Exact sign reversal.** Arm-one gains `.2` in one history and loses `.8` in another. Weights `(.9,.1)` give landmark gain `.10`; weights `(.1,.9)` give `-.70`. A favorable source-history average is not a global policy-improvement theorem. This limitation does not weaken the valid one-decision experiment; it defines its scope.

## 8. Experimental consequences and what the current checks establish

The coordinated protocol should implement these consequences before collection:

1. **One identifiable question.** Freeze the public eligibility, prefix distribution, receiver, complete slate, treatment rendering/context reset, remaining continuation, evaluator and failure rule. Restore the checkpoint before every branch. Keep repair-versus-restart separate from a wording-only claim.
2. **Preserve support and the root unit.** Use predeclared positive assignment probabilities or fixed complete branch counts. Keep root/family membership across all seeds and histories. Record deviations and outcomes for every assignment.
3. **A personalization test, not an ATE screen.** Report marginal arm differences but do not require one before examining the predeclared history-dependent selector. The decisive comparison is independent-root value against a competent policy chosen using training/development data only. A predefined interaction test can diagnose mechanism; it is not a substitute for that policy comparison.
4. **Do not promote a noisy oracle.** Label sample-max outcomes and sample-max branch means as optimistic diagnostics. Report public versus checkpoint information separately. Choosing an action using outcome labels from any branch of a test root changes the permitted information and cannot validate the public-prefix selector.
5. **Inference and decision thresholds.** Plan precision from the paired root contrast, with multiplicity appropriate to the actual primary claims. The root coordinator fixes meaningful benefit, resource cap, advancement, practical-futility and inconclusive criteria before outcomes; this note supplies no retrospective threshold. Nonsignificance, a wide interval, or low average arm difference is not proof that personalization is impossible.
6. **Match the practical target later.** An equal-continuation quality mechanism study does not establish quality per total deployment cost. Include candidate generation, checks and selection in the later budget comparison with independent sampling. Extra experimental branches are research expenditure, not deployable free information.

`scripts/check_landmark_theory.py` is a deterministic finite-law audit, not an LLM experiment. It verifies zero-ATE personalization, the two oracle gaps, within-root label leakage, correct randomized weighting, the sharp factor-two regret example, full-checkpoint variance including coupling, and a history-distribution sign reversal. It records its own source hash and rejects output overwrite. Run it with a new output path, for example:

```bash
python3 scripts/check_landmark_theory.py --output work/landmark_theory_checks_20260920.json
```

The separate [frozen premise simulation](landmark_premise_simulation_plan.md) uses 1,200 declared train/test datasets and nested `R=1,4` analyses. Source/manifest review found its public-Q truth, root pairing and unavailable-signal conditioning aligned with this note. Its null sample-max excess and zero-ATE interaction are synthetic demonstrations, not evidence for an LLM effect. Near-one coverage in null cells partly reflects learned policies identical to their comparator, yielding exactly zero contrasts and exactly covering degenerate intervals; it should not be advertised as uniform Wald reliability.

**Remaining limit:** these derivations establish what the next experiment would identify and how it should be interpreted. They do not establish useful prompt variation, learnable public-history rankings, sufficient sample size, a novel estimator, or practical superiority. Those remain the scientific premises the fresh experiment must test.
