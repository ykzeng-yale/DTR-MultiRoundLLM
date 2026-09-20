<!-- Assembled by the experiments workstream, 2026-09-19. Input for the theory workstream, NOT the theory workstream's own document. -->

> **Historical snapshot; conclusions require the 2026-09-20 corrections.** Read [continuation report](continuation_report_20260920.md), [theory reconciliation](theory_reconciliation_20260920.md), [experiment audit](experiment_recheck_20260920.md), and [literature recheck](literature_recheck_20260920.md) before using this document. Earlier universal impossibility, optimality, matched-cost kill, and feature-no-signal claims are superseded. Original text remains for provenance.

# Multi-turn human–LLM interaction as a dynamic treatment regime — identification and estimation

> **Provenance and status.** The experiments workstream produced this because the
> repository was empty and the experimental designs could not be sized without it.
> **It is input for the theory workstream, not a substitute for it.** `docs/theory.md`
> remains that workstream's to write; this is deliberately named differently.
>
> How it was built: five independent identification routes were drafted and
> independently reviewed, one was chosen and synthesized, five adversarial reviewers
> attacked the synthesis (**90 findings: 20 fatal, 44 major, 26 minor**), a binding
> cross-cutting repair spec resolved the defects that recurred across sections, and
> sixteen agents applied that spec section by section. Roughly **31 results, claims or
> recipes were withdrawn**; each is marked withdrawn *in place*, keeping its number, with
> the reason in the reviewer's own terms. Section 14 is the errata.
>
> **Primary strategy:** design-based identification of stochastic interventions on a
> finite, pre-registered prompt-generator choke point, evaluated in a resettable harness
> — a known-propensity design carrying modified-treatment-policy estimand semantics, with
> branch sampling as the oracle that validates the estimators.
>
> **Four things a reader should know before trusting any number here.**
>
> 1. **The improvement certificate is withdrawn.** At this project's cluster count
>    (176–230 task families) and its measured headroom (0.046), a finite-sample
>    certificate needs between 139× and 8,884× more clusters than exist. Even a paired
>    empirical-Bernstein bound has a half-width of 0.125 against a 0.046 gap. At this
>    sample size **no nonasymptotic bound resolves the effect**, and the replacement is
>    the measured paired precision (half-width ±0.019, MDE 0.027).
> 2. **The positivity floor is fixed by arithmetic, not taste.** A uniform floor over
>    `m` arms requires `m·δ ≤ 1`. STOP is exempt — its potential outcome is
>    analyst-measurable, so positivity holds by degeneracy and it needs no randomization
>    and no GPU. The eight randomized arms therefore take `δ = 1/8`, attained with
>    equality.
> 3. **The flagship deliverable needs no importance weights.** Because the harness runs
>    to `T_max` and grades the outcome at every turn, a stopping-only regime's value is an
>    *unweighted* mean: `W ≡ 1`. Depth-1 class overrides cost `W ≤ 8`; full-depth regimes
>    cost `W ≤ 64` and have an effective sample size of **2.75 clusters**, so their values
>    must come from on-policy rollout, never off-policy weighting.
> 4. **"A naive reward model learns the wrong sign" is true of reported effects and
>    false of decisions.** That split is now stated with numbers rather than asserted, and
>    the critic's motivation has moved onto horizon-aware valuation under known
>    propensities. See `docs/premise_findings.md` and `docs/e0_results.md`.
>
> **Read alongside:** `docs/positioning.md` (what may be claimed after the literature
> audit), `docs/e0_results.md` (the estimators validated against exact truth),
> `docs/audits.md`, `docs/pilot_findings.md`, and `docs/g0e_kill_criterion.md` — the last
> of which fired the programme's baseline-dominance kill criterion after this document
> was drafted, and narrows the deliverable further toward selection and stopping.


---

## 0. Verdict, and the choice of primary route

### 0.1 The primary strategy

**We adopt as PRIMARY: an on-policy, paired, common-random-number head-to-head between a learned regime and a pre-registered named baseline, run inside a resettable harness whose action at each turn is a selector drawn from a known randomization on a finite, pre-registered prompt-generator *choke point*. The design-based off-policy apparatus (T3, T9, P4–P6, P10) is SECONDARY: it governs reuse of one saved branch tree across many candidate policies, and the observational extensions of §11. It is not the route by which the headline number is obtained.**

This ordering is a correction. Earlier drafts made design-based *off-policy* identification primary and built the estimator menu on unpaired i.i.d. units carrying importance weights. The only affordable experiment is the paired one: every arm branches from the same saved root output $O_1$ per (task, seed), and without that pairing power at $\Delta=0.05$ is 0.31 while with it it is $\ge0.95$. The dominant variance component is between-task difficulty (per-task first-attempt success $\mathrm{Beta}(0.348,0.230)$, strongly U-shaped), pairing removes it, and **no variance formula in this document contains that term.** The pre-registered estimator — the mean over the 176 task families of family-mean paired differences with a paired family-clustered bootstrap — enters the menu as **E0** and is the primary estimator. This document's own principle ("where the environment is resettable, off-policy evaluation must justify itself", §12) is the correct verdict, and §0.1 is now stated to agree with it.

Concretely, at the frozen design constants (Part 0 of the repair spec; all of §0 is written at these values and no other):

* At each decision point the harness draws a selector $K_t\in\mathcal K=\{A_0,\dots,A_8\}$, $m=9$, from a known randomization $e_t(\cdot\mid H_t)$, then draws the message from the pinned generator $q_{K_t}(\cdot\mid H_t)$.
* Randomization is **uniform over the eight non-`STOP` arms**: $\mathcal K_G=\{A_1,\dots,A_8\}$, $m_G=8$, $e_t(k\mid H_t)=1/8=0.125$ at every branched state, so the attainable positivity floor is $\delta=1/8$ **with equality** ($m_G\delta=1.000$). A floor of $0.25$ is arithmetically infeasible for $m_G>4$ and is withdrawn wherever it appeared (R1).
* $T_{\max}=3$ turns, $k\in\{1,2\}$, so there are **$D=2$ decision points**. Full override depth is therefore $d=D=2$, and $\delta^{-d}\in\{1,8,64\}$ for $d=0,1,2$. **"$T=5$" appears nowhere in this document.**
* `STOP` $=A_0$ is a *coordinate of the action set*, not a member of the randomized set. Its potential outcome $Y(A_0\text{ at }k)=V_k$ is $H_k^A$-measurable (verifier determinism measured: 1,954 replicate verifications of 597 repeated `(task_uid, sha256(final_code))` pairs, 0 disagreements), so positivity for `STOP` holds **by degeneracy**, it needs no randomization and no nuisance model, and the harness runs every trajectory to $T_{\max}$ and grades $\psi$ at every turn, so every "stop at $k$" value is *observed* rather than weighted. The earlier phrasing "`STOP` is one of the selectors", read as "`STOP` is randomized at the floor like the rest", is withdrawn: randomizing it would buy no information and would deplete late-turn trajectories. It also has a technical consequence carried in §3: there is no emitted message at a stop turn, so no density $q_{A_0}(\tilde a\mid h)$ exists and the marginalized weight of P4 is undefined there; the weight must be written with the stop coordinate as a separate exact factor.
* The library is partitioned: an **evaluated set** $\{A_0,\dots,A_5\}=\mathcal A_{\rm adm}$, and a **diagnostic set** $\{A_6$ DIVERT, $A_7$ MISDIAGNOSE, $A_8$ PATCH$\}$ which appears in the critic's training data and in the leakage/placebo tables and is **barred from every reported policy and every reported baseline value** (R4). The value of the policy that *would* be allowed $A_8$ is a leakage upper anchor, never an effect of feedback.
* Generators are invoked **statelessly**: a fresh process per call, context built deterministically from the recorded $H_t$ and the redacted view $X^-$, no carried KV cache, persona, scratchpad, surviving reasoning tokens, retrieval handle or server-side conversation id. This is not a convenience. T3's density cancellation requires $q_k$ to be a kernel in the recorded $H_t$ alone; any carried state $U_t$ is a function of $K_{1:t-1}$, hence post-treatment with respect to earlier selectors, and the $q$ factors then **do not cancel** (R7). Statelessness is verified by input-provenance hash, fresh-context assertion and an out-of-order replay test (§16 item 1).
* Target regimes **re-weight the selectors**; they never set a text, never tilt token distributions, and never change the library.

This is Route C's design carrying Route B's estimand semantics, with Route D as oracle and validator, and Routes A and E as *coordinates of the same finite action space* rather than competing strategies.

**What is and is not a shippable protocol** (correcting an over-claim). In D1 the message generators write the *user's* turns, executed by a simulated user; no product ships a mechanism that writes its users' messages, and §12 concedes the point directly ("known propensities are purchased by replacing the human"). The target-trial / shippability reading therefore applies **only to the product-side coordinates by name**: the `STOP`/continuation rule, interface and rendering variants, and suggestion policies. **Message-generator arms are a measurement device for blips, not a deployable protocol.** Those product-side coordinates are also where the entire measured headroom sits (+4.6 pp from stopping decisions alone), so this restriction costs the project nothing it had evidence for.

### 0.2 Why this and not the others

1. **It removes the exclusion restriction A19 and the positivity obstacle by construction — and that is the whole of what it removes.** The positivity failure over the language space $\mathbb L$ is dissolved because the coarsening is *manufactured* (Result P2), not assumed; the coarsening-sufficiency exclusion restriction (A19) is never invoked, and we do not claim $Y(a)\perp a\mid K$ because we never intervene on the residual. The earlier claim that this is "the only route that removes the central obstacle without an untestable assumption" was a global claim and is **false as written**: D1 still rests on A11 (outcome validity — the document's own main residual threat), A12 (leakage-scorer adequacy, with a *signed* rather than unsigned caveat — see item 5 of R5: $\hat\Lambda$ understates leakage, which inflates leakage-controlled contrasts), A22 wherever humans appear, and the live A1/A2 hygiene channels (cache sharing, batch nondeterminism, shared budget pools, temperature-0 non-determinism). One untestable assumption is removed on one coordinate; the rest remain and are listed in §12.

2. **$\mathrm{do}$ on a semantic class is ill-posed, not merely unidentified** (P1). A class contains astronomically many messages and a frozen receiver responds differently to different members, so the intervention does not denote a distribution. Any class-level estimand must name a version mix. Our design *is* the version mix.

3. **The propensity is known exactly and bounded below by construction — and this buys robustness for the *value estimate*, not for the deliverables.** With $e$ known and $\delta=1/8$ attained with equality, sequential DR is unbiased in a precisely limited sense:

   > $E[\hat\psi]=\psi$ **for any $\hat Q$ that is fixed conditional on the evaluation fold and internally consistent, $\hat V_t(h)=\sum_k\pi_t(k\mid h)\hat Q_t(h,k)$** (T9(i)).

   Three qualifications the earlier text omitted, all of which bite here. (a) Cross-fitting is *required*: "for any $\hat Q$ whatsoever" as previously written covered same-sample fits, for which $E[\hat\psi]\ne\psi$. (b) A critic that emits $\hat V$ directly, or independently fitted $\hat V$ and $\hat Q$, breaks the telescoping and the exactness with it. (c) The **TMLE variant does not attain finite-sample exactness** — it fluctuates $\hat Q$ with the same data through the clever-covariate score, so it is asymptotically equivalent only; the cross-fitted one-step estimator is the form that is exactly unbiased. So: a cheap badly calibrated LLM critic carries **zero bias risk for the value estimate under cross-fitting**, and its error nevertheless **enters the learned regime at first order** through T19 and supplies the stop decision through T8b. Since the headline deliverable *is* a learned stopping rule, critic calibration is exactly what determines what ships, and "zero bias risk" must never be stated unqualified.

   **The finite-sample improvement certificate (T20) is WITHDRAWN as a headline deliverable and retained as a scope statement (§6).** It was advertised here as "genuinely valid rather than conditional on a correct propensity model". It is valid; it is also numerically vacuous on this task pool and unaffordable at any gap worth certifying. At the corrected bound $n_{\rm clusters}\ge 8M\log(4|\Pi|/\alpha)/\mathrm{gap}^2$ with $M=\delta^{-d}$, $\alpha=0.05$ and $L=\log(4|\Pi|/\alpha)=6.461$ at a pre-registered candidate count of 8 (the count is declared in §16; the value `100` is forbidden, and at 100 every figure multiplies by 1.39): certifying the **only measured headroom, gap $=0.046$**, needs $2.4\times10^4$ clusters unweighted, $2.0\times10^5$ at $M=8$ and $1.6\times10^6$ at $M=64$, against $n_{\rm clusters}=176$ families — short by **139×, 1,110× and 8,884×** (106×, 850×, 6,798× against the ≈230 pool ceiling). Equivalently, the smallest gap certifiable at $n=176$ is **0.542** unweighted against 0.046 of available headroom, a shortfall of **11.8×**, and **1.533 at $M=8$**, which exceeds the range of $Y-\lambda C\in[0,1]$ and is therefore impossible at any gap. The one-sided LCB half-width at $n=176$ for a single policy is **0.254**, 5.5× the gap. In compute: $2.4\times10^4$ units at 3 receiver generation calls each and ≈2,150 calls/hour is **34 GPU-hours** and $2.0\times10^5$ units is **273 GPU-hours**, against a measured affordability ceiling of **20,000 calls ≈ 9.3 h** — 3.7× and 29× over. The sentence "at this corrected rate the machinery costs roughly what a stratified A/B test over the $m$ arms costs" is **deleted**; the honest multiple is **50–120×**. What replaces it is E0: a paired, family-clustered bootstrap interval, measured half-width **±0.019** at $R=8$ with **MDE 0.027** at 80% power — which does resolve a +0.046 effect, and is the reason the paired design is primary (§0.1).

4. **Product-side treatments are shippable mechanisms; message-generator arms are not.** A `STOP` rule, an interface variant, a suggestion policy: these correspond to deployable protocols in the target-trial sense, which is what makes them auditable by randomized implementation. A generator, a template, a best-of-$K$ selector or a redaction level applied to the *user's* message is a **measurement instrument for blips**, and its human-facing analogue is at best an ITT suggestion estimand (P31). The earlier blanket claim "every treatment is a shippable mechanism" is withdrawn, and with it the implication that the third deliverable — a trained free-form generator emitting text outside the pinned library — inherits any guarantee in this document. It does not; see §0.3.

5. **The endogenous horizon is cheap in *causal* nuisance and expensive in *prediction*. "It costs nothing extra" is WITHDRAWN.** The correct statement separates two information sets, which the earlier text conflated (R3). $H_t^A$, the analyst/harness history, includes the programmatic grade $\psi(H_s)$ for every artifact in hand; $H_t^O=\varphi_t(H_t)$, the policy-observable history, is the frozen decision-time signal and **excludes $\psi$ and every hidden-test-derived quantity**, `signature_example` stripped, enforced by feature-builder assertion.
   * **T8a (analyst).** $Q_t(H_t^A,\texttt{STOP})=\psi(H_t)$ exactly. The `STOP` arm carries no causal nuisance, has zero Monte Carlo variance, needs no nuisance model, consumes zero GPU and requires no positivity. This is what makes the stop coordinate weight-free.
   * **T8b (policy).** For $\pi\in\Pi_{\rm cp}$ the implementable stop value is $E[\psi(H_t)\mid\varphi_t(H_t)]$ — an **unknown regression**, the deployable policy's whole handle on "am I already right", a supervised calibration problem with no causal content but with first-order estimation error. It is not a known functional of anything the policy sees. The visible verdict is one bit and is absent on 20.8% of the informative pool, and the sibling loop's own self-check stopped on **50.4%** [0.479, 0.528] of all failures. The **+4.6 pp** is the value of the **oracle** $V$, which is available to no real rule.

   Restated asymmetry: *the `STOP` arm's causal nuisance is nil and its prediction problem is the hardest estimation problem in the design.* The phrases "known stop-arm value", "the endogenous horizon costs nothing extra" and "no medical analogue" are deleted — the medical analogue of T8b is ordinary prognostic modelling. A rule taking its argmax against the harness-known $Q_t(H_t^A,\texttt{STOP})$ is P23's **prophet benchmark**, not a member of $\Pi_{\rm cp}$. **Mandatory reporting: the oracle-$V$ minus $\hat p$-rule value gap as a headline pair, never the oracle value alone.** A11(d) is correspondingly restated as an *information-set restriction* — $\varphi$ excludes $\psi$ — rather than a two-instrument requirement; with a programmatic primary outcome $\sigma=0$ for the primary number and P24(ii)'s selection optimism does not bite on it, and §16's "two prespecified independent measurement channels" is replaced by the $\varphi$-exclusion assertion. If a judge is ever used for a secondary outcome, T8b applies with the corresponding optimism inflation.

   One further honesty item, since this subsection previously sold the horizon apparatus as a free advantage over medical DTRs: **in D1 the stopping coordinate is exogenous by construction.** The simulated user never abandons, so the continuation indicator is the harness's own randomizer and P23's weight $\prod 1/e_t(\texttt{CONT}\mid H_t)$ is pure design noise relative to the on-policy rollout E0/E7 actually runs. The learned `STOP` rule is a **protocol the system imposes, not a model of when users stop.** The motivating structure — satisfied users stopping, informative quit hazards, the identified-set width $\kappa_0(\pi)$ — lives in logs (Ext-E/D3), where A6 fails structurally for continuation. The apparatus is unnecessary where it is valid and invalid where it is motivated; its one real use is reusing a single logged harness run across many candidate $\tau$ without re-rolling out, and the break-even against direct rollout is stated in §7.

6. **The prioritized outcome reduces to a bounded pseudo-outcome (T13) only because $G_0$ is frozen on an independent log — and T13/T14 are DEMOTED to a secondary reporting device.** $G_0$, the mid-rank CDF of $u(Z)$ under a reference regime, is an unknown functional of $P$; "prespecified $\pi_0$" pins the regime, not the functional. With $\hat G_0$ estimated on the analysis sample, $\tilde Y$ carries an outcome-law nuisance, the units are dependent, T9(i)'s exact unbiasedness is lost, $Q_t(\cdot,\texttt{STOP})$ stops being known even in the T8a sense, and the correct expansion is the **two-term** influence function $\varphi_\pi[G_0^-]+\varphi_{\pi_0}[\bar G_\pi]$ that §7 displays — a two-term EIF being precisely the statement that T9 does not apply verbatim. The repair is to take the free option: $G_0$ is computed from the **sibling project's completed 4,488-episode log** (identical `tasks_sha256`, verified not assumed; same machine, inference server and quantizations) and **hashed and frozen before any outcome of this run is examined** — zero GPU time, zero clusters, genuinely independent of this run's outcomes. Then $\tilde Y=2G_0(u(Z))-1$ is a fixed known measurable transform, T8a and T9 do apply verbatim, and the stop-arm value is known in the T8a sense. **The price, stated: the reported win probability is against the frozen sibling reference distribution, not a concurrent $\pi_0$, and $\pi^\star$ is reference-dependent.** Option (ii) — $\hat G_0$ as a nuisance, with the bilinear remainder in $(\hat G_0-G_0,\hat Q-Q)$ and the claim degraded to "doubly robust with a second-order remainder" — is retained in §7 as what *would* be required and is **not used confirmatorily**.

   The demotion: the primary objective is $E[Y^\pi-\lambda C^\pi]$ at the pre-registered $\lambda=0.01$ per turn read off the measured budget, with **degradation (first-correct-then-wrong) reported separately** as audit A3 requires. $Y$ is a binary hidden-test verdict and $N\in\{1,2,3\}$ with cost monotone in $N$ up to token noise, so with tolerances the ordered quotient has about six cells, the tie mass is the majority of pairs, and the win-probability estimand is a coarse monotone re-expression of a $2\times3$ table whose variance is dominated by tie handling — while *shrinking* an effect already at 0.015–0.030. The tie mass must be reported. T13 is scoped to outcomes with a continuous or many-valued primary component. The earlier selling point "scale-free in $(Y,C,N)$, no hand-tuned $\lambda$" is hollow: $\lambda$ is a budget price identified by LP duality in T8 and pinned by a measured budget, not hand-tuned.

7. **Resettability supplies what the observational routes must assume**, and it is also why the off-policy machinery is secondary here: on-policy paired rollouts (so $V(\pi)$ need not be off-policy estimated at all — E0/E7), ground-truth conditional-effect labels with a debiased validation risk (T27), and falsification of reset fidelity, branch isolation and coarsening sufficiency. Where the environment is resettable, off-policy evaluation must justify itself case by case, and for full-depth regimes it cannot (§0.3).

**What the evidence actually attributes the gain to** — this subsection previously leaned on a confounding narrative the project's own simulations refuted, so the split is stated here rather than buried. Two separable deliverables:

* **(a) Honest effect *reporting* from interaction logs**, where the failure of the naive read is dramatic and robust: unadjusted comparisons of intervention classes inverted the true ordering in **0/40** replicates, and conditioning on the intermediate state (a mediator of the earlier action as well as a confounder of the later one) reported a true +0.156 first-turn blip as **+0.005**.
* **(b) Action *selection*, where the gain is attributed to horizon-aware valuation under randomization, not to confounding adjustment.** A plain correlational state-conditioned critic recovered the exact optimal regime in **39/40** replicates (mean regret 0.0010); three attempts to break it with unmeasured confounding moved regret by at most **0.030**; known-propensity IPW repaired the residual only partly and non-monotonically (0.046→0.033, 0.028→0.028, 0.017→**0.019** — one cell got worse). The dominant decision-level error was **myopia**, which loses under randomization too and is therefore not a confounding failure at all. Accordingly the causal-correction claim is a **scoped secondary claim with pre-registered expected value null** (S1), a non-myopic correlational critic is pre-registered as a baseline the framework must beat (B5/B6), and the motivation carried by §0 is *horizon-aware valuation plus a design whose assignment probabilities are known exactly.*

### 0.3 What the choice costs, stated up front

The estimand is **library-relative** (a generator outside $\mathcal K$ is not evaluable), **simulated-user-relative** (external validity to human users is a transport problem, T28, with one term we cannot estimate), and **receiver-version-relative** (all intervals are conditional on one pinned snapshot; importance sampling cannot express uncertainty about "the receiver"). Beyond those, five costs that earlier drafts of this subsection did not state:

**(i) The inference unit is small, and it is the task instance.** Seeds, branches, turns, templates and paraphrases are *within*-cluster; the 1,520 paired units are 190 × 8 root seeds sharing one saved root $O_1$ and are **within-cluster**. $n_{\rm clusters}=\mathbf{176}$ task families, with a pool ceiling of **≈230** (3B) and **≈100** (7B). Every sample-size statement in this document is in clusters and is checked against 176. "Conversations" as a unit is withdrawn wherever it appeared: it manufactures unlimited units from a low-hundreds population whose task text is the dominant variance component.

**(ii) Override depth is an entitlement class, not a free knob, and at full depth off-policy inference is not available.** Depth counts only decision points at which a regime overrides the generator-class distribution; the stopping coordinate contributes **no weight**, because the harness runs to $T_{\max}$ and records $\psi(H_k)$ at every $k$, so a stopping regime's value is an *unweighted* mean. Three declared classes, and every claim must name one:

| class | definition | bound | $n_{\rm eff}\ge n_{\rm clusters}\delta^{d}$ at 176 | how its value is obtained |
|---|---|---|---|---|
| $\Pi_0$ | stopping-only; $\pi_k=e_k$ on $\mathcal K_G$ | $W\equiv1$, $M=1$ | **176** | unweighted means on recorded trajectories; no importance weighting anywhere |
| $\Pi_1$ | depth-1 class override | $W\le8$, $M=8$ | **22** | off-policy estimable; report ESS and $\hat D_2$ with every number |
| $\Pi_2=\Pi_{\rm cp}$ | full depth $d=D=2$, including $\hat\pi$ from backward induction | $W\le64$, $M=64$ | **2.75** | **on-policy rollout (E0/E7) or re-logged policy iteration only**; off-policy certification explicitly disclaimed |

A depth-2 off-policy evaluation on this pool has an effective sample size of **under three clusters**. "The history-shift factor is bounded here by design" (T19) is an advantage over *unbounded* ratios, not a small constant: for $\hat\pi$ and every full-depth member of $\Pi_{\rm cp}$ the bound is 64, and the propagation statement is structural, not a basis for inference. The one piece of good news is that **the deliverable the evidence supports needs no importance weights at all**: the measured headroom is entirely in stopping, and stopping-only regimes sit in $\Pi_0$ with $W\equiv1$.

**(iii) We do not report "the optimal regime".** $\Pi_{\rm cp}$ is the class of regimes measurable with respect to $\mathcal F_k^O=\sigma(\varphi_k(H_k))$ and valued in $\mathcal A_{\rm adm}=\{A_0,\dots,A_5\}$. Because $\mathcal F_k^O\subsetneq\sigma(H_k^A)$, **$\varphi$ is not sufficient**, so the restricted optimum does not satisfy a Bellman equation on $\varphi$-measurable value functions: backward induction returns $\pi^{\rm greedy}$, which is in general not $\arg\max_{\Pi_{\rm cp}}V$. **A19b (state-representation sufficiency) is not assumed by the primary route.** The reported object is $\hat\pi=\arg\max_{\pi\in\Pi}\widehat V(\pi)$ over a **pre-registered finite candidate set** whose count is declared in §16, evaluated out-of-fold (5 folds over the 176 families, all seeds/branches/turns of a family in one fold), with the winner's value re-estimated on held-out data and the selection inflation reported. The phrase "the optimal regime" is reserved for $\arg\max_{\Pi_{\rm cp}}V$, which this design does **not** report. For an infinite class a covering-number bound would be required and **we do not have one.**

**(iv) The certificate is withdrawn and the propagation guarantee may be vacuous at achievable precision.** T20 is withdrawn as a deliverable (§0.2 item 3; §6). T19's value-loss bound $V(\pi^\star)-V(\hat\pi)\le E|\hat\gamma-\gamma|$ is correct and numerically weak here: label noise on the blip pseudo-outcome is Bernoulli, the per-state Monte Carlo SE of $\gamma$ at the frozen $n_b=3$ is **up to 0.29** with $\hat v\approx0.08$, and the measured blip scale is small (repair 0.239, degradation 0.162, with 0.156 of the 3B pool below 0.05 success and 0.334 above 0.95, leaving 0.406 informative). A bound of the order of the total available prize (0.046) is not a guarantee. §6 therefore reports a margin-type statement, the measured distribution of $|\gamma|$, and the critic's per-state error, so a reader can see whether the bound bites.

**(v) $\Omega(K^T)$ is a *search* bound, and "a learned blip estimator is mandatory" was an assumption dressed as a theorem.** The correct statement: exhaustive search over *history-indexed* regimes with no state abstraction is infeasible (T26(c), a needle-in-a-haystack lower bound on the number of leaf queries needed to **find** the optimum), therefore structure must be imposed — and **every guarantee downstream is conditional on that structure**, which where it extrapolates is an identifying assumption and is labelled as one (T7). A learned blip estimator does not evade the lower bound; it substitutes an extrapolation assumption for the query budget. T26(c) changes no design decision, since nobody proposed exhaustive search, and it is a remark rather than a pillar. Relatedly, T26(a)'s "no positivity assumption" is not a removal but a relocation: positivity holds by construction on the expanded action set at every design-reached node and fails precisely off-tree (T26(b)).

**(vi) The third deliverable is outside every guarantee in this document.** A trained *generative* prompt policy emits messages that leave the pinned library. By this document's own T26(b) and §12, its value is neither identified nor certified, T19 does not apply to it, and no statement in §§3–9 covers it. It is reported, if at all, as an engineering artifact with on-policy measurement only.

**(vii) One arm's "floor" is not a floor.** Wherever the simulated-log arm appears, its "floor 0.2" is **not** a randomization floor ($8\times0.2=1.6>1$). It is a **weight-truncation level** ($\hat e$ clipped below at 0.2, so $w\le5$); it introduces clipping bias; A6 does **not** hold in that arm, whose logging policy is confounded by construction; and the truncation rate must be reported.

### 0.4 When an alternative is preferable

| Alternative | Prefer it when | Price |
|---|---|---|
| **Ext-E: stop-only regimes** in observational logs | You have only human logs and want the **weakest positivity requirement**: the language density cancels *identically* and positivity is needed on one binary coordinate (T3, P23). Leakage-immune by construction. | Says nothing about what the user should have *said*; late-continuation regimes are structurally non-identified (P21). The exchangeability burden is **unchanged**, so this is not "the strongest possible identification position": the very mechanism that creates the support failure — satisfied users stop, i.e. continuation probability falls in current quality — is simultaneously an A7 violation whenever the user's perceived quality exceeds what $H_t$ records. So $\kappa_0(\pi)$ is a **lower bound** on the true ambiguity, not a sharp width, and calibration for exactly this is listed OPEN in §15. For the cost-priced objective the width is $\kappa_0\cdot\mathrm{range}(Y-\lambda C)$ with $C$ bounded by the cap, not $\kappa_0$. |
| **Ext-B: exponential tilt** along a frozen feature | You have human logs and want a message-level estimand with **no exclusion restriction**. The weight is a scalar observable normalizer; the EIF collapses (T30). | Estimand is mechanism-relative (a property of the user population, not the receiver), bundled (includes everything co-moving with $\phi$), and capped by a KL budget: recomputed at $n_{\rm clusters}=176$, $n_{\rm eff}^{\min}=30$, $D=2$, $\sum_t\Delta_t^2\le\log(176/30)=1.769$, i.e. $\Delta_t\le0.941$ within-history SD and $\mathrm{KL}_t\le0.442$ nats per turn. **And the binding statistical cost, previously omitted: $\sqrt n$ inference requires a product rate on two text-history nuisances** — the conditional normalizer $Z_t(\theta,h)=E_P[e^{\theta'\phi}\mid H_t=h]$, an infinite-dimensional $P$-dependent object appearing *inside the intervention itself*, and the tilted critic — unverifiable per §12 with no smoothness theory and **no known-propensity fallback**: if $\hat Z$ is inconsistent the estimator is inconsistent, $E[w_t\mid H_t]=Z_t/\hat Z_t\ne1$ so both the exact $P$-martingale property and the $E[w\mid H]=1$ specification check are only approximate, and the anytime-valid certificate of §15 is unavailable. State whether $Z_t$ is cross-fitted, since it is estimated from the same data as the value. The route trades an untestable *identification* assumption (A19) for an unverifiable *estimation* condition. |
| **Ext-A: coarsening** | You must report message-level, version-averaged class effects from logs and will carry a dispersion sensitivity parameter (T29). | Inherits the logged intervener's writing distribution; generator regimes are *not* off-policy estimable this way. |
| **Ext-D: exhaustive branching** | Benchmarking, validating estimators, and the continuation half of the policy class where logs have no support. | Exponential budget; no reach to human users or irreversible environments. |
| **D2: full-message known propensity** | Pinning the within-class version mix, and computing Rao–Blackwellized weights **in the one design where they do anything**. | Never for token-level targets (P6) or cross-model reweighting (P32). And **P4 buys nothing in the frozen design**: the generators are deterministic template renders with a uniformly drawn index over 3 frozen templates using the episode seed, so $q_k$ is a point mass given the recorded index, distinct $k$ produce distinct texts, numerator and denominator each collapse to one term, the marginal weight equals the selector ratio **exactly**, and the Rao–Blackwell variance reduction is **identically zero**. For LM generators it is non-free: computing $q_k$ for the $m_G-1$ untaken arms costs $m_G$ teacher-forced scoring passes per turn on the realized message, using the *sampling-time truncated* distribution, a cost that competes directly with the branch budget and must be priced before P4 is used. P4 also requires non-degenerate, overlapping generator supports and computable truncated densities, is undefined at stop turns (§0.1), and is restricted to the IPW/clipped-IPW forms — the sequential-DR estimator must use the selector-level weight to retain exact unbiasedness, or accept a text-conditioned critic. |

---

---

## 1. Setup and notation

**Units, and the i.i.d. unit (corrected).** The i.i.d. unit is the **task instance — task text only**. Seeds, branches, turns, template indices and paraphrase variants are *within*-cluster and manufacture no independent units. Formally: task instances $i=1,\dots,n_{\rm clusters}$ with $X_i\sim P_X$ i.i.d.; every replicate attached to $X_i$ is a within-cluster draw. Frozen numbers: the E3 pool is **190 tasks**, single-link-clustered into **176 task families**, and $n_{\rm clusters}=176$; the pool ceiling on the informative band is **≈230 tasks with the 3B receiver and ≈100 with the 7B** (audits A2, A4), not 590. The **1,520 paired units** ($190\times8$ root seeds sharing one saved root $O_1$) are within-cluster and are the mechanism by which the *paired* design removes between-task variance — they are not 1,520 clusters. Families, not tasks, are the cross-fitting and bootstrap unit (§5), so every estimability statement in this document is stated in **clusters** and must be checked against 176 (ceiling 230).

> **The earlier definition — "the unit is the task instance (task text $\times$ environment seed)" — is WITHDRAWN.** It was incompatible with §5's fold rule, which puts all branches, replicate seeds, turns and paraphrase variants of one task in the same fold, and it manufactured unlimited "units" from a ~230-element task population whose task text is the dominant variance component (per-task first-attempt success is Beta$(0.348,0.230)$, strongly U-shaped: mass 0.334 above 0.95 success, 0.156 below 0.05, 0.406 informative). Every sample-size figure in this document that was quoted in "conversations" is recomputed in clusters (§4, §6); the certificate that depended on the old unit is withdrawn in §6 T20.

**Horizon and index convention (frozen).** $T_{\max}=3$ turns; interventions are selected at the **$D=2$ decision points** $k\in\{1,2\}$. Displays indexed by $k$ run over decision points, displays indexed by $t$ over turns. The harness runs **every** trajectory to $T_{\max}$ and grades $\psi$ at every turn, so no "stop at $k$" value is ever missing and no stopping value requires a weight (§4 T8a, §6). The string `T = 5` does not appear in this document; the exponential-in-horizon factors are evaluated at $D=2$.

**Action space.** $\mathbb L=\bigcup_{k\le m_{\max}}\mathcal V^k$ over a token vocabulary: **countable**, so every density is an elementary ratio of pmfs and no dominating-measure construction is needed. The positivity problem is therefore *not* measure-theoretic. For an LLM-generated user it is a variance catastrophe ($g_t(a\mid h)=e^{-\Theta(\text{len }a)}$); for a real human it is a genuine **support** failure ($g_t(a\mid h)=0$ for essentially every $a$). These two diagnoses demand different repairs, which is why the slogan "text breaks positivity" is not precise enough to act on.

**Trajectory.** $H_1=X$; $A_t=(R_t,\tilde A_t)$ with $R_t\in\{0,1\}$ (continue/stop, absorbing at 0) and $\tilde A_t\in\mathbb L$; $O_t\sim M(\cdot\mid H_t,\tilde A_t)$; $H_{t+1}=(H_t,\tilde A_t,O_t,S_t,c_t)$, where $S_t$ is a decision-time signal and $c_t$ a cost increment. $T=\min\{t:R_t=0\}$, $N=T-1$, $C=\sum_{t\le N}c_t$, with $T\le T_{\max}=3$ by administrative cap.

**Two histories.** $H_t^A$, the **analyst/harness history**, is everything recorded, including the programmatic grade $\psi(H_s)$ of every artifact in hand for $s\le t$. $H_t^O=\varphi_t(H_t)$, the **policy-observable history**, is the pre-registered frozen decision-time signal: task text, emitted messages, receiver outputs, the *visible* assertion verdict, and the cost channel. $\varphi_t$ **excludes $\psi$ and everything derived from the hidden tests**, and `signature_example` is stripped from every record it can reach. $\mathcal F_t^O:=\sigma(\varphi_t(H_t))\subsetneq\sigma(H_t^A)$. Every regime in $\Pi_{\rm cp}$ is $\mathcal F_t^O$-measurable (see the policy class below); every nuisance the analyst fits may use $H_t^A$. A quantity that is $H_t^A$-measurable but not $\mathcal F_t^O$-measurable is available to the *estimator* and unavailable to the *policy*, and this document states which of the two it means every time it says "known".

**Design.** $K_t\sim e_t(\cdot\mid H_t)$ on the finite, frozen action set $\mathcal K=\{A_0,\dots,A_8\}$, $m=9$, with $A_0=$ `STOP` absorbing; then $\tilde A_t\sim q_{K_t}(\cdot\mid H_t)$ from the pinned library, **invoked statelessly** (A5: a fresh process per call, context built deterministically from the recorded $H_t$ and the redacted view $X^-$, no carried KV cache, persona, scratchpad, surviving reasoning tokens, tool handle or server-side conversation id — this is what makes the $q$ densities cancel in T3, and it is verified, not assumed, §16 item 1). Randomization is **uniform over the $m_G=8$ non-`STOP` arms** $\mathcal K_G=\{A_1,\dots,A_8\}$: $e_t(k\mid H_t)=1/8=0.125$ at every branched state, so the feasible positivity floor is $\delta=1/8$ and $m_G\delta=1.000$ binds with equality (A6; a floor of $0.25$ is infeasible for $m_G>4$ and is withdrawn in §2). `STOP` needs no randomization at all: its potential outcome is $H_t^A$-measurable, so positivity for it holds by degeneracy. The selector is the **pair** $(g,\lambda)$ — generator class and *built-in* leakage level — jointly randomized at $1/8$; `info_cap_bits` and `suffix_words` are frozen **action features** of the arm, not measured covariates of the message (A12, §8). The library is partitioned into an **evaluated set** $\mathcal A_{\rm adm}=\{A_0,\dots,A_5\}$ and a **diagnostic set** $\{A_6$ DIVERT, $A_7$ MISDIAGNOSE, $A_8$ PATCH$\}$; diagnostic arms are barred from every reported policy and from every reported baseline value, and appear only in the critic's training data and the leakage/placebo tables (§6 T20(c), §16).

**Outcome.** $Y=\psi(H_T)$, programmatic: in the frozen design a **binary hidden-test verdict** in $\{0,1\}\subset[0,1]$. $\psi$ is deterministic as measured — 1,954 replicate verifications of 597 repeated `(task_uid, sha256(final_code))` pairs, 0 disagreements — which is what licenses treating a stop-arm value as recorded rather than estimated (§4 T8a). $\psi$ is $H_t^A$-measurable and is **excluded from $\varphi_t$**: the policy never sees it. Terminal record $Z=(Y,C,N)$, $N\in\{1,2,3\}$, for the prioritized objective of §7.

**Estimands.**
- **Reference regime for blips (made explicit).** The reference is a **continuation regime that never stops**: it plays the pinned reference arm at every decision point out to the administrative cap $T_{\max}$. This is required because `STOP` is one of the treatment levels, so the treatment at a decision point changes *the number of subsequent turns*; without a never-stopping reference the two arms of a `STOP` contrast have different horizon supports and the additive blip-down representation has an index set that depends on the very treatments being blipped down.
- Turn-specific blip $\gamma_k(H_k,a,a_{\rm ref})=E\big[Y^{(a\text{ at }k,\ \text{then ref})}-Y^{(a_{\rm ref}\text{ at }k,\ \text{then ref})}\mid H_k\big]$ for $a\in\mathcal K$, with the **stopping convention stated rather than implied**: $\gamma_k(H_k,\texttt{STOP}):=\psi(H_k)-E\big[Y^{(\text{ref from }k)}\mid H_k\big]$, i.e. the `STOP` blip absorbs the entire value of the turns that never occur. Blip-down residuals must be formed with the index set $\{k,\dots,\min(T_i,\bar K)\}$ and an explicit `STOP` term, and on the **net** outcome $Y-\lambda C$ when the target is the net-benefit value; §5 E2 carries that correction.
- $Q_k(H_k,a)$ under continuation $\pi$, with the two information sets of the "two histories" paragraph kept apart: $Q_k(H_k^A,\texttt{STOP})=\psi(H_k)$ exactly, while the implementable stop value $E[\psi(H_k)\mid\varphi_k(H_k)]$ is an unknown regression (§4 T8a/T8b).
- **Primary value:** $V(\pi)=E[Y^\pi-\lambda C^\pi]$ at the pre-registered budget price $\lambda=0.01$ per turn, with **degradation reported separately** (measured 0.162 [0.105, 0.242] of already-correct answers destroyed by continuing), never folded into the mean.
- **Secondary:** the prioritized net benefit of §7. *Demoted from co-primary to a secondary reporting device:* with $Y$ binary and $N\in\{1,2,3\}$, the ordered quotient has about six cells and the tie mass is the majority of pairs, so the win-probability estimand is a coarse monotone re-expression of a $2\times3$ table whose variance is dominated by tie handling, and it shrinks an effect already at 0.015–0.030. Its transform $\tilde Y=2G_0(u(Z))-1$ is a **fixed known** transform only because $G_0$ is frozen on an independent pre-existing log before any outcome of this run is examined; the win probability is therefore reference-dependent (§7, R6). Report the tie mass.

**The policy class.** Let $\varphi_k$ be the pre-registered, frozen, finite-dimensional feature map of the "two histories" paragraph (the 87-coordinate state code, frozen as data before any fit, with $\psi$ and every hidden-test-derived quantity excluded), and $\mathcal F_k^O:=\sigma(\varphi_k(H_k))$. Then
$$\Pi_{\rm cp}:=\Big\{\pi=(\pi_1,\pi_2):\ \pi_k\ \text{is }\mathcal F_k^O\text{-measurable, valued in the simplex over }\mathcal A_{\rm adm}=\{A_0,\dots,A_5\}\Big\},$$
with the depth-graded subclasses $\Pi_0\subset\Pi_1\subset\Pi_2=\Pi_{\rm cp}$ of §4/§6: $\Pi_0$ overrides only the stopping coordinate and carries $W\equiv1$; $\Pi_1$ is a depth-1 class override, $W\le\delta^{-1}=8$; $\Pi_2$ is full depth $d=D=2$, $W\le\delta^{-2}=64$, whose effective sample size on this pool is $176\times\delta^{2}=2.75$ clusters. Because $\mathcal F_k^O\subsetneq\sigma(H_k^A)$, **$\varphi$ is not sufficient**, so the restricted optimum does **not** satisfy a Bellman equation on $\varphi$-measurable value functions: backward induction on $\hat Q_k(\varphi_k,a)$ returns $\pi^{\rm greedy}\in\Pi_{\rm cp}$, which is in general $\ne\arg\max_{\Pi_{\rm cp}}V$. **A19b (state-representation sufficiency) is NOT assumed by the primary route.** Accordingly the reported object is
$$\hat\pi:=\arg\max_{\pi\in\Pi}\widehat V(\pi)$$
over a **pre-registered finite candidate set $\Pi$** whose count is declared in §16, with $\pi^{\rm greedy}$ entered as one member labelled "greedy-in-$\varphi$". $\hat\pi$ is evaluated out-of-fold (5 folds over the 176 families; all seeds, branches and turns of a family in one fold), the winner's value is re-estimated on the held-out half, and the selection inflation is reported. The phrase "the optimal regime" is reserved for $\arg\max_{\Pi_{\rm cp}}V$, which this design does **not** report.

> **$\pi^\star=\arg\max_{\pi\in\Pi_{\rm cp}}V(\pi)$ "over choke-point-measurable policies" — RETAINED as a definition; WITHDRAWN as a reported deliverable.** "Choke-point-measurable" was never defined as a $\sigma$-algebra, and on either reading the old bullet failed: on verbatim text histories every $Q_k$ sits at atoms of probability $e^{-\Theta(mt)}$ visited once, so the max over the class has optimism equal to the outcome's full range; on $\varphi$-measurable rules the Bellman recursion of T8 is invalid because $\varphi$ is not sufficient. $\Pi_{\rm cp}$ is now defined as a $\sigma$-algebra restriction with declared override depth, and the reported object is $\hat\pi$ over a finite pre-registered $\Pi$. Where an infinite class would need a covering-number bound, we say so and state that we do not have one (§6).

**Potential outcomes (A3).** Arm-specific *distributions*, obtained by replacing the user's action kernel and leaving $f_M$ and the law of the decoding noise intact. We adopt distributional semantics deliberately rather than a shared-noise representation: a shared exogenous draw would silently define a joint law across arms, and hence unit-level effect distributions and within-unit win probabilities, that the system does not actually deliver (P12). Under distributional semantics such functionals are *not defined* without a declared coupling (A16), which is the honest statement; what *is* available from the marginals alone is a sharp interval over admissible couplings, reported in §7 P12.

**The confounding structure we are correcting, and what our own evidence says it buys.** The structural pathology is real: $A_{t-1}\to O_{t-1}\to A_t$ and $O_{t-1}\to Y$, and exactly
$$\mathrm{Cov}(Y,\phi_t)=\underbrace{E[\mathrm{Cov}(Y,\phi_t\mid H_t)]}_{\text{local effect}}+\underbrace{\mathrm{Cov}(E[Y\mid H_t],E[\phi_t\mid H_t])}_{\text{artifact}} .$$
A bad output provokes a severe correction, so the second term is expected to be negative and a naive *marginal* comparison of intervention classes reports the wrong sign. (That the sign *is* negative in our data is an empirical conjecture, not a theorem.) Numerically: with $P(\text{bad})=0.5$, $P(\text{harsh}\mid\text{bad})=0.8$, $P(\text{harsh}\mid\text{good})=0.2$, and true means (good: 0.80/0.85, bad: 0.30/0.50), harsh helps at every history by $+0.125$ on average but the marginal comparison shows it $0.13$ *worse*.

**The split this document is committed to, because our own premise checks force it.** The effect-*reporting* claim survives and is large: unadjusted comparisons of intervention classes inverted the true ordering in **0 of 40** replicates (premise check P1), and in P2 the optimal first intervention had the *lowest* observed mean of all four classes (0.186 against 0.637 for a perfunctory retry). The **decision**-level claim is already evidence-against: a purely correlational critic conditioning on the full observed state recovered the **exact optimal regime in 39 of 40** replicates (mean regret 0.0010 against an optimum of 0.751); adding a latent confounder and sweeping its coupling moved the logged-minus-randomized regret gap by at most **0.030**; and known-propensity IPW repaired that residual only partly and **non-monotonically** ($0.046\to0.033$, $0.028\to0.028$, $0.017\to0.019$ — one cell got worse). The dominant decision-level error was **myopia**, which loses under randomization too and is therefore not a confounding failure at all. The measured headroom in this task family points the same way: **+4.6 percentage points** of final success sit in *oracle stopping decisions* with feedback content held completely fixed (audits A3). Accordingly this document motivates its machinery on **horizon-aware valuation and a known-propensity randomized design**, treats "causal correction of a confounded log improves *decisions*" as a scoped secondary claim, and pre-registers a **non-myopic correlational critic** as the baseline the framework must beat (§12, §16). The two deliverables — honest effect reporting, and action selection — carry their own evidence and neither may borrow the other's.

**What coarsening actually buys (corrected).** Not "a cell to adjust within": history strata exist however finely the treatment is defined. What fails at the fine level is **positivity of the treatment within a history stratum**, so the standardized mean is not estimable there. More precisely, and consistently with T29 (§11.2): at the fine level the adjusted contrast is *point-identified* at every $a$ of positive probability but has effective sample size $n\cdot e^{-\Theta(m)}$, hence is not regularly ($\sqrt n$-) estimable; **nonparametric within-stratum** adjustment requires coarsening, whereas **model-based** adjustment does not — which is why the fine level needs either a critic (D1) or a scalar feature (Ext-B, §11.1 T30) rather than a stratum. The earlier sentence "adjustment is only available once the treatment has been coarsened, because at the fine level there is no cell to adjust within" is **withdrawn**: it argued against this document's own primary route, which adjusts by regression and never stratifies on text.

---

---

## 2. Assumptions A1–A22

Stated compactly; the structured assumption list carries full text. "BC" = holds by construction in the primary design; "A" = assumed.

**Frozen constants this table is stated at** (single source of truth; no cell may contradict them). Action set $\mathcal K=\{A_0,\dots,A_8\}$, $m=9$, with $A_0=$ `STOP` absorbing; randomized set $\mathcal K_G=\{A_1,\dots,A_8\}$, $m_G=8$; design propensity $e_t(k\mid H_t)=1/8=0.125$ at every branched state (measured positivity 1.0); floor $\delta=1/8=0.125$, attained with equality ($m_G\delta=1.000$); policy-admissible $\mathcal A_{\rm adm}=\{A_0,\dots,A_5\}$, with $A_6$ DIVERT, $A_7$ MISDIAGNOSE, $A_8$ PATCH diagnostic-only and barred from every $\pi$ and every reported baseline; $T_{\max}=3$, decision points $k\in\{1,2\}$, $D=2$, so full override depth is $d=D=2$ and $\delta^{-d}\in\{1,8,64\}$ for $d\in\{0,1,2\}$; the i.i.d. unit is the **task instance**, $n_{\rm clusters}=176$ task families (from 190 tasks), pool ceiling $\approx230$ (3B) and $\approx100$ (7B); $\lambda=0.01$ per turn, pre-registered.

| | Assumption | Status in D1 |
|---|---|---|
| A1 | Task-level units, **no cross-trajectory interference — assumed, not by construction**. Hygiene (caching off, per-task budget pools, randomized batch composition, no online adaptation) plus a pre-registered drift diagnostic: arm × time-block interaction with the recorded foreign-GPU-load covariate, branch expansions interleaved across task instances with randomized expansion order rather than expanded node-by-node, and a fixed-prompt canary battery replayed each block. | **A**, with randomized batch composition and the drift diagnostic. *Downgraded from BC:* the receiver runs `llama-server -np 4` under an uncontrolled foreign GPU load from sibling projects, the harness records `yielded_seconds_before_start` and `foreign_gpu_load_at_start` precisely because that load is uncontrolled, and `llama.cpp` is not bit-deterministic across batches even at a fixed seed. Randomizing batch composition makes the interference exchangeable; it does not make it absent, and "verify caching changes latency and not tokens" cannot detect prefix-cache dependence, because prefix caching changes kernels and numerics, not token counts. |
| A2 | Frozen receiver $O_t=f_M(H_t,\tilde A_t,\xi_t)$, pinned digest/decoding/tooling | BC; violation makes the estimand **undefined**, not noisy. Consequence, stated here because it is a contradiction in the document and not a refinement: **a model-version epoch cannot be a clustering level.** Clustering by epoch prices snapshot drift as sampling noise around a single well-defined parameter, which is coherent only if the estimand is redefined as an average over a declared snapshot distribution — and A2 refuses that redefinition, while few-cluster cluster-robust inference over a handful of epochs would be invalid on its own terms anyway. Time blocking remains legitimate for within-epoch nuisances (load, latency) and is **not** a remedy for a version change; a detected change splits the run into separate receiver-conditional analyses. §5's "additional clustering for standard errors by model-version epoch" and "balance the drift" are incompatible with this row and are conceded as such (§5 owns the fix). |
| A3 | Stochastic potential outcomes; $\mathrm{do}$ on the user mechanism only | BC (definitional) |
| A4 | $A_t=(R_t,\tilde A_t)$, `STOP` absorbing. `STOP` $=A_0$ is **not a member of the randomized set**: $Y(A_0\text{ at }k)=V_k$ is $H_k^A$-measurable (verifier determinism measured: 1,954 replicate verifications of 597 repeated `(task_uid, sha256(final_code))` pairs, 0 disagreements), the harness runs every trajectory to $T_{\max}$ and grades $\psi$ at every turn, so every "stop at $k$" value is **observed, not weighted**. At a `STOP` draw there is no emitted message and hence no generator density on $\mathcal L$, so the stop coordinate cannot be marginalized out of a weight (§3 P4). | BC |
| A5 | Pinned, pre-registered, version-hashed generator library, invoked **statelessly**: every generator call at turn $t$ is issued in a fresh process from a context constructed **deterministically from the recorded $H_t$** and the redacted view $X^-$ (reference solution and tests removed) — no carried KV cache, no persona or scratchpad memory, no cross-turn hidden state, no reasoning tokens surviving the call, no tool or retrieval handle persisting across turns, no server-side conversation id. The library is partitioned into an **evaluated** set $\{A_0,\dots,A_5\}$ and a **diagnostic** set $\{A_6,A_7,A_8\}$. Generators are built to declared leakage levels (A12). | **BC** for the frozen template library (deterministic renders with a seeded uniform template index); **A, and verified** for any LM-generator arm, by §16 item 1 sub-items (a)–(d) below. |
| A6 | Randomization floor on the **randomized** coordinate: $e_t(k\mid H_t)=\delta$ for all $k\in\mathcal K_G$, with the feasibility constraint $m_G\delta\le1$ stated as part of the assumption. `STOP` is exempt: its potential outcome is $H_t^A$-measurable, so positivity for `STOP` holds by degeneracy. Frozen: $m_G=8$, $\delta=1/8=0.125$, $m_G\delta=1.000$. | BC ($\delta=1/8$; $\delta\ge0.25$ is **infeasible** for $m_G>4$ and is withdrawn) |
| A7 | Sequential exchangeability on the **intervened coordinate** | BC in D1; **A** and untestable in logs |
| A8 | Support compatibility; no change of library, tokenizer, template or sampler mask; **and fixed rendered prompt geometry across arms** — the task specification is re-rendered at a fixed token distance from the generation point in every arm, padded with inert filler verified at $\hat\Lambda=0$. | BC in D1; **the binding condition in D2**. Conceded: message **length** and **position/recency** are caused by the randomized selector and are therefore mediators, not nuisances to adjust; the offered remedy ("within a $\hat\Lambda$ bin, message length no longer predicts $Y$") is a low-power observational regression on post-treatment variables and is withdrawn. Fixed prompt geometry removes the position channel at no receiver cost; the length channel is handled by the separate pre-registered length-calibration block (each class at 2 pre-registered token budgets plus a **filler-only** arm, $\approx570$ receiver calls, §16), and class effects are reported **net of the measured length main effect**. Without that block the class effect is confounded with length by design-mediation. `suffix_words` and `info_cap_bits` are frozen **action features** of the arm, not measured covariates of the message. |
| A9 | $e_t$ depends on $H_t$ only through the recorded, frozen, policy-observable map $\varphi(H_t)$ — the 87-coordinate state code of §1, which excludes $\psi$ and every hidden-test-derived quantity — so $e_t$ is $\mathcal F_t^O$-measurable | BC (the randomizer computes from $\varphi$); false in logs. If A5's statelessness checks fail, the history must be enlarged to contain the carried state $U_t$ and A9's $\varphi$-measurability, together with every "no text critic" claim, must be restated on the enlarged history. |
| A10 | $Y\in[0,1]$, $C\in[0,c_{\max}]$, cost channels kept separate; $\lambda=0.01$ per turn **pre-registered**, grid $\{0,0.005,0.01,0.02\}$ with a union bound if more than one value is reported; degradation reported separately from mean outcome (measured 0.162 [0.105, 0.242]) | BC by pre-registration. Conceded: "$\lambda$ is a budget price, not a hyperparameter" is **withdrawn as used**. The LP-dual multiplier is a functional of $P$ — the supporting hyperplane of the convex hull of *attainable* (value, cost) pairs — so an estimated $\hat\lambda$ would make $Y-\lambda C$ a data-dependent estimand, would invalidate any fixed-parameter $1-\alpha$ bound selected after seeing the data, and would add an influence contribution nowhere carried in §5's EIF. Under pre-registration $\lambda$ **is** a hyperparameter and is reported as one; the dual reading is not used confirmatorily. |
| A11 | Outcome validity: (a) programmatic $\psi$; (b) judge + PPI *only* for secondary outcomes; (c) horizon-invariant scorer; (d) **the stopping signal is $\varphi$-measurable and $\varphi$ excludes $\psi$ and every hidden-test-derived quantity, enforced by feature-builder assertion.** | **A** for (a)–(c); (d) **BC** by construction of $\varphi$ |
| A12 | **Leakage is a coordinate of the randomized action space, not a covariate.** Pinned generators are built to declared leakage levels $\lambda$, the pair $(g,\lambda)$ is randomized, and $\hat\Lambda$ — the log-likelihood gain of a fixed reference receiver on the reference solution given $(H_t,\tilde A_t)$ relative to given $(H_t,\text{null message})$ — is a fidelity measurement that is never conditioned on, stratified on, or filtered by. Generators see the redacted view $X^-$, enforced by prompt-hash assertion. (The leakage level $\lambda$ of this row is a different object from the cost price $\lambda$ of A10; the collision is notational only.) | **BC** for the design coordinate; **A** for scorer dynamic range, with the bias direction stated: $\hat\Lambda$ understates leakage, which inflates leakage-controlled contrasts |
| A13 | Reset fidelity; branch isolation; snapshot hashing; decoding regime matched to deployment | **BC** for reset, branch isolation and snapshot hashing; **A, and testable (P18)** for numeric reproducibility — temperature 0 is not determinism. The deep slice is the most dependence-exposed quantity in the design, because $\hat v(h)$ is estimated from within-node replicates and would absorb cache-induced dependence as independent Monte-Carlo noise. At the frozen $n_b=3$ the per-state MC SE reaches **0.29** against $\hat v\approx0.08$, so the P18(c) duplicate-arm check is powered on the deep slice and the duplicate-arm discrepancy is reported alongside $\hat v$ as a headline diagnostic; if the discrepancy exceeds $\hat v$, $\hat v$ and any risk estimate built on it are declared unusable. |
| A14 | Singleton or pinned reference arm | BC for the pinning. **Conceded as insufficient:** because `STOP` is a treatment level, the treatment at turn $t$ changes the number of subsequent turns, so the two arms of a blip at the `STOP` level have different horizon supports and the additive representation $U_{it}=Y_i-\sum_{s\ge t}\gamma_s$ has an index set whose upper limit is a function of the very treatments being blipped down. A14 does not supply what the blip-down identity needs: a reference defined as a **continuation** regime on all histories to the administrative cap $\bar K$ (never `STOP`), and an explicit convention for $\gamma$ at a `STOP` turn absorbing the value of the turns that never occur. Until §1 and §7/E2 state that convention, blips at the `STOP` level are not well defined by the displayed definitions. |
| A15 | Non-informative administrative cap $\bar K$; frozen $T_{\max}=3$, $D=2$ decision points | BC |
| A16 | Declared randomness coupling — only for within-unit contrasts. The 1,520 paired units ($190\times8$ root seeds sharing one saved root $O_1$) are **within-cluster**, as are branches, turns, templates and paraphrases; the i.i.d. unit is the task instance. | **A**, and design-relative |
| A17 | Prioritized outcome: finite ordered quotient, tolerances $\eta_1>0$, prespecified $u,\eta$, **and $G_0$ frozen on an independent pre-registered reference sample** — the sibling project's completed 4,488-episode log on the identical task pool (`tasks_sha256` verified, not assumed), hashed before any outcome of this run is examined | BC by pre-registration **and** by the freeze of $G_0$. Conceded: pre-specifying the *regime* $\pi_0$ does not pin the *functional* $G_0$, and with $\hat G_0$ fitted on the analysis sample $\tilde Y$ would carry an outcome-law nuisance, the $\tilde Y_i$ would be dependent, exact unbiasedness would degrade to double robustness with a second-order remainder, and $Q_t(\cdot,\texttt{STOP})$ would become an estimated nuisance — which is what the two-term influence function displayed in §7 says. The freeze buys the verbatim reuse of T8a and T9; its price is that the reported win probability is against a **frozen sibling reference distribution** and $\pi^\star$ is reference-dependent. The prioritized form is a **secondary** reporting device (§7): $Y$ is binary, $N\in\{1,2,3\}$, so the ordered quotient has $\approx6$ cells, the tie mass is the majority of pairs and must be reported, and the primary objective is the priced scalar $E[Y^\pi-\lambda C^\pi]$ at $\lambda=0.01$/turn. |
| A18 | **A18a — cross-fitting / sample splitting:** $\hat Q$ (and $\hat G_0$ where estimated) independent of the evaluation fold, 5 folds over the 176 families with all seeds, branches and turns of a family in one fold. **A18b — corrected cross-term product rate on $(\hat e,\hat Q)$:** needed only where $e$ is estimated. | **A18a required in every design, including D1**; **A18b vacuous in D1**. Conceded: the previous single row marked A18 "vacuous in D1" and thereby licensed the implementation that voids the headline robustness claim. Knowing $e$ kills the *rate* condition, not the *fold-independence* condition: with $\hat Q$ fit on the evaluation data, $E[\hat\psi]\ne\psi$ even with $e$ known exactly, and the CLT's empirical-process term relies on fold independence. Accordingly "exactly unbiased for any outcome model whatsoever" is restricted to the **cross-fitted one-step/AIPW** estimator; TMLE (which fits its fluctuation on the data it evaluates, $O(1/n)$ bias), clipped IPW (biased by construction) and any self-normalized variant trade exactness for other properties. |
| A19 | **A19 (coarsening sufficiency) — NOT used by the primary route.** **A19b (state-representation sufficiency: $\varphi$ sufficient for the optimal regime) — also NOT assumed by the primary route.** | not invoked. Consequence, stated because it is load-bearing: $\mathcal F_k^O\subsetneq\sigma(H_k^A)$, so $\varphi$ is not sufficient and the restricted optimum does **not** satisfy a Bellman equation on $\varphi$-measurable value functions. Backward induction on $\hat Q_k(\varphi_k,a)$ returns $\pi^{\rm greedy}\in\Pi_{\rm cp}$, in general $\ne\arg\max_{\Pi_{\rm cp}}V$; the reported object is $\hat\pi$, the best member of the **pre-registered finite candidate set** declared in §16, with $\pi^{\rm greedy}$ entered as one labelled member. "The optimal regime" is reserved for $\arg\max_{\Pi_{\rm cp}}V$, which this design does not report. |
| A20 | Frozen bounded test functions $\phi$; unconditional transforms only (tilt extension). **$\phi$ here is the tilt test function and is a different object from the policy-observable map $\varphi$ of A9/A11(d); the collision is notational only.** | BC by pre-registration. The tilt budget is recomputed at the honest inference unit in §4 ($n_{\rm clusters}=176$, $n_{\rm eff}^{\min}=30$, $D=2$), not at $n=10^4$ conversations with $T=5$. |
| A21 | No decay / artifact-valued outcome | BC by choice of $\psi$. Scope: A21 makes the `STOP` value well defined **in the analyst information set** ($H_t^A$, T8a). It does **not** make the *policy's* stop value known — that is the unknown regression $E[\psi(H_t)\mid\varphi_t(H_t)]$ of T8b. |
| A22 | Suggestion-response invariance (encouragement designs with humans) | **A**. Not claimed here: the intervener is an automated template library, so every effect is an effect of an intervention deliverable by an automated intervener, and transfer to human users is not asserted. |

Three notes worth making loudly, and one list of withdrawals.

**A19's absence is the whole point — for class effects, and only for those.** The standard objection to a taxonomy — "LLMs are paraphrase-sensitive, so your coarsening cannot be sufficient" — is an objection to A19. We do not need it for the *effects*, because the generator *is* the treatment. If one nevertheless wants message-level class effects, A19 is required and is treated in §9.3 as a *measured dispersion parameter* with a breakdown value, never as an assertion (the pre-freeze test has 92% power against a within-class template SD of 0.08 and 57% at 0.06, so a non-rejection is evidence against an effect of 0.08, not evidence of exact sufficiency). What does **not** follow, and what the previous version of this note implied, is that dropping sufficiency is free for *policy learning*: A19b's absence is exactly why backward induction on $\varphi$ returns a greedy rule rather than the restricted optimum, and why the deliverable is $\hat\pi$ over a pre-registered candidate set.

**A21 dissolves the hardest classical pathology, in one information set.** With an artifact-valued, non-decaying outcome, `STOP` is a genuinely absorbing state with a well-defined value, "as-delivered" and "fixed measurement point with carry-forward" coincide, and there is no truncation-by-death despite a random endogenous horizon (T25e). The reflex of measuring satisfaction or acceptance inherits an unnecessary non-identification. What A21 does not buy: "the endogenous horizon costs nothing extra" is **withdrawn**. The `STOP` arm's *causal* nuisance is nil and its *prediction* problem — $E[\psi\mid\varphi]$, the deployable rule's whole handle on "am I already right" — is the hardest estimation problem in the design. The measured difficulty is on record: the visible verdict is one bit and is absent on 20.8% of the informative pool, and the sibling loop's own self-check stopped on 50.4% [0.479, 0.528] of all failures, while the +4.6-point headroom is the value of the **oracle** $V$, available to no real rule.

**A5's statelessness is verified, not assumed, and the failure mode is named.** §16 item 1 carries four sub-items, each reported: (a) an **input-provenance hash** — SHA-256 of the fully rendered generator prompt, logged per call, byte-exactly equal to the hash recomputed offline from the recorded $H_t$ and $X^-$ alone, any mismatch being a hard failure of A5; (b) a **fresh-context assertion** — a new server session per call with prompt caching disabled and an explicit cache reset, asserted and logged per call; (c) an **out-of-order replay test** — a random 2% sample of generator calls re-issued out of chronological order from the same recorded $H_t$ with the same seed, required to be byte-identical (CPU-side for the frozen template library, so effectively free); (d) **on failure of (a)–(c)**, the history is redefined to include the carried state ($H_t$ must contain $U_t$), and A9's $\varphi$-measurability and every "no text critic" claim must be restated on the enlarged history. The reason this is an assumption and not a footnote: any carried KV cache, persona, scratchpad, surviving reasoning tokens, persistent tool handle or server-side conversation id makes $q_{K_t}(\cdot\mid H_t,U_t)$ depend on $U_t=$ a function of $K_{1:t-1}$; $U_t$ is then post-treatment with respect to earlier selectors and mediates them, the $q$ factors differ between the $e$-law and the $\pi$-law and **do not cancel** in T3, and P2's "assign generator $k$ names a fully specified stochastic intervention" collapses at the same point. That is the default implementation of a multi-turn LLM user, so it is barred, not assumed away.

**Withdrawn clauses, kept in place.** Each is retained above in corrected form; none is deleted silently.

1. **A6 "recommend $\delta\ge0.25$" — WITHDRAWN as infeasible.** A uniform floor over $m_G$ arms requires $m_G\delta\le1$, so $\delta\ge0.25$ admits at most four randomized arms against the frozen nine-action taxonomy; every quantity computed at $\delta=0.25$ (notably $E[W^2]\le\delta^{-d}=16$) was evaluated at an unattainable floor. Replaced by $\delta=1/8$, attained with equality, giving $\delta^{-d}=8$ at $d=1$ and $64$ at $d=2$, and $n_{\rm eff}\ge n_{\rm clusters}\delta^d$ of 176 / 22 / 2.75 at $d=0,1,2$.
2. **A6's floor over `STOP` — WITHDRAWN as unnecessary and costly.** Randomizing an arm whose potential outcome is $H_t^A$-measurable buys no information and depletes trajectories geometrically; positivity for $A_0$ holds by degeneracy and the stop coordinate carries no weight.
3. **A11(d) "independent stopping/scoring channels" — WITHDRAWN and replaced by an information-set restriction.** The two-instrument reading collided with T8's "$Q_t(H_t,\texttt{STOP})$ is known": read one way it contradicted A11(d) and manufactured P24(ii) optimism, read the other way the advertised asymmetry evaporated. With a programmatic primary outcome $\sigma=0$, P24(ii) does not bite on the primary number, and the requirement is now the $\varphi$-exclusion assertion. A judge outcome is admissible only for secondary outcomes, where T8b applies together with the P24 inflation term.
4. **A12 "computable pre-treatment leakage $\Lambda$; capped or stratified" — WITHDRAWN.** $\tilde A_t$ is drawn after $K_t$, so $\Lambda(\tilde A_t,H_t)$ is a descendant of the treatment and a plausible mediator: within-bin contrasts are mediator-stratified and collider-exposed rather than T3 contrasts, "stratify randomization on the bin" is not implementable (the bin is unknown until after $K_t$ is drawn), and capping by rejection replaces $q_k$ by a truncated kernel with an unknown normalizer. "Pre-receiver-response" is not "pre-treatment"; the correct word is pre-outcome, and it licenses nothing. Leakage level is now a randomized action coordinate and the realized score is a fidelity measurement only. Not identified, and not claimed: the effect of $g$ holding realized $\Lambda$ fixed, any contrast conditioning on $\hat\Lambda$, and natural direct/indirect leakage effects.
5. **A12's task-blind placebo solver — WITHDRAWN.** A solver that has not seen the task gains almost nothing from "you forgot the base case", so a task-blind scorer has no dynamic range over exactly the messages that matter; $\hat\Lambda$ is redefined as conditional information and validated on a planted set. The old caveat "unsigned" was wrong in a known direction: $\hat\Lambda$ understates leakage.
6. **A18 "vacuous in D1" — WITHDRAWN for the sample-splitting half.** Only A18b (the product rate) is vacuous when $e$ is known; A18a (fold independence) is required everywhere.
7. **A1 "BC with hygiene" — WITHDRAWN; regraded to A.** Shared, drifting foreign GPU load and non-bit-deterministic batching are common shocks across in-flight units; exchangeable is not absent.
8. **A10's "$\lambda$ is a budget price, not a hyperparameter" — WITHDRAWN as used.** $\lambda$ is pre-registered and reported as a hyperparameter with a union bound over the grid.
9. **A17 "BC by pre-registration" alone — WITHDRAWN as insufficient.** Pre-registration pins $\pi_0$, not $G_0$; the freeze on an independent log is what makes $\tilde Y$ a fixed known transform.
10. **A14 as a sufficient reference condition — WITHDRAWN.** It pins the arm but not the horizon convention the blip-down identity needs at a `STOP` level.

---

---

## 3. Identification

**Scope note (R9, R2 — read before T3).** This section establishes what is *identified*. It does not establish what is *inferable on this pool*. The primary inferential route for the frozen design is an **on-policy, paired, common-random-number rollout** (E0, R9): all arms branch from the same saved root output $O_1$ per (task, seed), the estimator is the mean over the 176 task families of family-mean paired differences with a paired family-clustered bootstrap, and no importance weight appears in it. The off-policy apparatus below governs **tree reuse across candidate policies and the observational extensions**, not the headline number. The reason is arithmetic, not taste: at $n_{\rm clusters}=176$ families the depth-graded effective sample sizes are $176$ / $22$ / $2.75$ clusters at override depth $d=0,1,2$ (R1, R2), so a full-depth off-policy value on this pool rests on under three effective clusters. The dominant variance component here is between-task difficulty (per-task first-attempt success $\mathrm{Beta}(0.348,0.230)$, strongly U-shaped), pairing removes it, and **no weighted formula in this section contains that term** — a defect the reviewers raised against the document's ordering and which is conceded here rather than patched.

### T3 (g-formula; the cancellation)

Under A1–A8 — with A5 read in its **stateless** form (see the proof and A5 itself) and A6 at the frozen feasible floor $\delta=1/8=0.125$ on the $m_G=8$ randomized non-`STOP` arms — for any $\pi\ll e$ on the intervened coordinate,
$$V(\pi)=E\Big[W_{1:\tau}\,(Y-\lambda C)\Big],\qquad W_{1:\tau}=\prod_{t\le\tau:\ K_t\in\mathcal K_G}\frac{\pi_t(K_t\mid H_t)}{e_t(K_t\mid H_t)} ,$$
where the product runs over the turns at which $\pi$ **overrides the generator-class distribution**, and the factor is $1$ at every turn at which $\pi_t$ restricted to $\mathcal K_G$ equals $e_t$.

**Three things the displayed weight does and does not contain.**

1. **The stopping coordinate carries no weight** (R2). The harness runs every trajectory to $T_{\max}=3$ and grades $\psi(H_k)$ at every decision point, so the value of "stop at $k$" is *observed*, not reweighted, and $Y(A_0\text{ at }k)=V_k$ is degenerate given $H_k^A$. Positivity for `STOP` therefore holds by degeneracy and `STOP` is exempt from A6; it needs no randomization, no nuisance model and no GPU. In particular a stopping-only regime's value is an **unweighted mean of recorded values**.
2. **The bound is depth-graded, and depth is not a free knob** (R2). With $e_t(k\mid H_t)=\delta=1/8$ on $\mathcal K_G$ at every branched state (measured positivity 1.0, $m_G\delta=1.000$, so the floor is attained with equality and $\delta\ge0.25$ is *infeasible* for $m_G>4$ and is withdrawn), $W_{1:\tau}\le\delta^{-d}=8^{d}$ with $d$ the override depth of the regime. The frozen design has $D=2$ decision points, so full depth is $d=2$ and $8^2=64$ is the **worst case over $\Pi_{\rm cp}$, not a setting**: $W\equiv1$ for $\Pi_0$ (stopping-only), $W\le8$ for $\Pi_1$ (depth-1 class override), $W\le64$ for $\Pi_2=\Pi_{\rm cp}$. "Bounded by design" is an advantage over *unbounded* text-level ratios, not a small constant.
3. **Absolute continuity is one-directional and holds by construction.** $e$ spreads $1/8$ over all eight non-`STOP` arms, including the three diagnostic arms $\{A_6,A_7,A_8\}$; every $\pi$ is supported on $\mathcal A_{\rm adm}=\{A_0,\dots,A_5\}$ and the diagnostic arms are barred from every $\pi$ and every reported baseline (R4 library split), so $\pi\ll e$ is automatic and the per-turn ratio is at most $8$.

*Proof.* The trajectory laws under $e$ and $\pi$ share $P_X$, every generator kernel $q_k$, and every receiver kernel $M$; A2–A3 make the receiver common to observation and intervention, and A7 licenses identifying the g-computation law with the intervened law. In the ratio of densities the $q_k$ and $M$ factors cancel, leaving the displayed selector ratio. Absolute continuity is A8, and $\tau$ is action-measurable by A4. $\square$

**The cancellation step requires more than "pinned", and the extra requirement is stated here because it is the default implementation that violates it (R7).** The $q$ factors cancel only if $q_k$ is a kernel in the **recorded $H_t$ alone** and is conditionally independent of the selector history $K_{1:t-1}$ given $H_t$. A generator implemented as an LLM with any cross-turn hidden state — a carried KV cache, a persona or scratchpad not written into $H_t$, reasoning tokens surviving the call, a persistent tool/retrieval handle, a server-side conversation id — has kernel $q_{K_t}(\cdot\mid H_t,U_t)$ with $U_t$ a function of $K_{1:t-1}$. Then $U_t$ is **post-treatment with respect to the earlier selectors and mediates them**, the trajectory density does *not* factor as (selector terms) $\times$ (common $q$ and $M$ terms), the $q$ factors differ between the $e$-law and the $\pi$-law, and **they do not cancel**. Accordingly A5 now carries an explicit statelessness condition — every generator call is issued in a fresh process from a context constructed deterministically from the recorded $H_t$ and the redacted view $X^-$, with no carried cache, memory, scratchpad, surviving reasoning tokens, tool handle or session id — and §16 item 1 verifies it by (a) a byte-exact input-provenance hash of the rendered generator prompt recomputed offline from $H_t$ and $X^-$, (b) a per-call fresh-session/cache-reset assertion, and (c) an out-of-order replay test on a random 2% of calls requiring byte-identical output. **If any of (a)–(c) fails, T3 as displayed does not hold**: the history must be redefined to include the carried state ($H_t\supseteq U_t$), and A9's $\varphi$-measurability and every "no text critic" claim must be restated on the enlarged history. The frozen primary library — deterministic template renders with a seeded uniform template index — satisfies the condition **by construction** (BC); any LM-generator arm satisfies it only **as a verified assumption** (A). The D2 catalogue's line that discarded chain-of-thought is "pre-treatment generation randomness, not a mediator, so ignorability survives and only computability fails" is true for a **within-turn** scratchpad discarded before the next call and **false for any state carried across turns**; §10 is corrected accordingly.

**On the measurability of $\pi_t$.** The display writes $\pi_t(K_t\mid H_t)$ for uniformity with the $e$-law. Every regime in $\Pi_{\rm cp}$ is in fact $\mathcal F_t^O=\sigma(\varphi_t(H_t))$-measurable (R3, R8), so $\pi_t(K_t\mid H_t)=\pi_t(K_t\mid\varphi_t(H_t))$; the identification argument is indifferent to which of the two histories $\pi$ reads, because $\mathcal F_t^O\subset\sigma(H_t^A)$. What is *not* indifferent is optimization: because $\varphi$ is not sufficient, the restricted optimum does not satisfy a Bellman equation and the reported object is $\hat\pi$, the best member of a pre-registered finite candidate set, not "the optimal regime" (R8, §1, §4 T8).

**Attribution (positioning.md).** T3 is the sequentially-randomized g-formula — Robins (1986); Precup–Sutton–Singh (2000); Thomas–Brunskill (2016) — specialized to a coarsened, prospectively randomized action with logged propensities. The earlier phrasing "**New in this setting: no density over text appears anywhere**" is **weakened**: it is a consequence of the coarsening, not a new identification result, and it is not claimed as novel. Single-period identification for text-valued treatments is Imai & Nakamura (arXiv:2410.00903); longitudinal causal inference over sequences of text features is Nakamura & Imai (arXiv:2605.07834); DTR/Q-learning over a natural-language action space is Zhang, Wang & Dhillon (arXiv:2502.17538). What this project claims is the **design** — prospective sequential randomization of the intervention inside a multi-turn LLM interaction with logged propensities — and **the coarsening stated as the identification content, with the effects of the underlying string explicitly not identified**.

Two specializations matter.

- **Stop-only regimes ($\Pi_0$).** With the generator class left at the **design law $e$** and only `STOP`/`CONT` chosen, $W_{1:\tau}\equiv1$: the language density cancels identically, *and there is no positivity requirement to satisfy at all*, because `STOP` is degenerate given $H_k^A$ and the continuation class distribution is not overridden. Values are unweighted means on recorded trajectories and $n_{\rm eff}=n_{\rm clusters}=176$. This is the strongest identification position available to this project, **and it is the one the evidence needs**: the only measured headroom is $+0.046$ of final success from oracle stopping decisions, so *the deliverable the evidence supports requires no importance weights anywhere*. Two riders, both conceded: the $+0.046$ is the value of the **oracle** $V$, not of any implementable rule, and the implementable stop value $E[\psi(H_t)\mid\varphi_t(H_t)]$ is an unknown regression and the hardest estimation problem in the design (T8b, R3) — the sibling loop's own self-check stopped on $0.504$ [0.479, 0.528] of all failures. The earlier description of this bullet as the strongest *observational* position is **corrected**: in D1 there is no observational arm and no natural policy — the harness replaced the user — so the word "observational" belonged to the extensions, not here.
- **Class regimes under a within-class mix.** The fine ratio also collapses to a coarse indicator ratio (T29, §11.2), which is what the coarsening route buys — at the price of inheriting the *writer's* within-class distribution. Two corrections. (i) The coarse indicator ratio is a **per-turn** factor bounded by $\delta^{-1}=8$; the trajectory weight is a **product over turns** and is bounded by $\delta^{-d}$, so T29's "$\delta^{-1}$ in place of $e^{\Theta(m)}$" understates the trajectory bound and is corrected to $\delta^{-d}$ there (R2). (ii) "The logged writer's within-class distribution" presupposes a writer; in D1 there is none, and the within-class distribution is the **pinned library's, by construction**. The bullet therefore describes the coarsening/observational *extension*, not the frozen design.

**What T3 does not give.** It gives contrasts across randomized action labels. Under R5 the randomized label is the **pair** $(g,\lambda)$ — generator class at a built-in leakage level — so the $\lambda$ main effect and the $g\times\lambda$ interaction are identified by design with **no conditioning**. It does **not** identify the effect of $g$ holding *realized* leakage $\hat\Lambda$ fixed, nor any contrast conditioning on $\hat\Lambda$, message length or message position: those are descendants of the treatment and hence mediators, and conditioning on them is mediator-stratification, not a T3 contrast (§8 T16, §13(c)). Nor does T3 license comparing an already-randomized contrast against a filtered subpopulation: rejection sampling on realized $\Lambda$ replaces $q_k$ by a truncated kernel with an unknown normalizer, and is excluded from T3 and from P4.

### P2 (well-posedness by design)

Under A5 **in its stateless form**, "assign generator $k$" names a fully specified stochastic intervention, because $q_k$ is a pinned kernel *in the recorded history*. Under R5 the randomized object is the pair $(g,\lambda)$ — the class together with its built-in leakage level, jointly randomized at $e=1/8$ — so the fully specified intervention is "assign generator $g$ at declared leakage level $\lambda$", and `info_cap_bits` and `suffix_words` are **frozen action features**, not measured covariates of the emitted message. Compare P1: $\mathrm{do}(S_t=s)$ on a semantic *class* does not determine a law for $O_t$, and hence no $Y(S_t=s)$ exists. The design therefore converts an ill-posed estimand into a well-posed one, and **no exclusion restriction is needed**. This is the sharpest formal difference between the primary route and the coarsening route.

**Conceded qualification (R7).** The well-posedness argument collapses at exactly the point T3's cancellation does. If a generator carries cross-turn hidden state, "assign generator $k$" no longer names a fixed kernel — the kernel then depends on $K_{1:t-1}$ through $U_t$ — and P2's claim is false, not merely harder to estimate. P2 is therefore **BC for the frozen deterministic template library** and **A, verified by §16 item 1(a)–(c), for any LM-generator arm**, with the enlarged-history fallback of A5(d) stated as the consequence of a verification failure. "Pinned" alone was never sufficient and the earlier wording implied that it was.

### P4 (Rao–Blackwellized marginal weights)

> **P4 (Rao–Blackwellized marginal weights) — WITHDRAWN as a technical contribution; retained as an opt-in, per-generator variance device for IPW only.** *We claimed a free variance reduction from marginalizing the selector out of the weight, with the rule "marginalize over every recorded latent randomization whose density you can compute". In the frozen design the generators are deterministic template renders with a uniformly drawn index over 3 frozen templates using the episode seed, so $q_k$ is a point mass given the recorded index and distinct $k$ produce distinct texts: numerator and denominator each collapse to one term, **the marginal weight equals the selector ratio exactly, and the variance reduction is identically zero**. Where generators are LM-based, computing $q_k$ for the $m_G-1=7$ untaken arms costs $m_G=8$ teacher-forced scoring passes per turn on the realized message, using the *sampling-time truncated* distribution rather than the model distribution — a cost the document never priced and which competes directly with the branch budget (frozen $n_b=3$) against a 20,000-call, 9.3-hour affordability ceiling. So P4 is **an identity with no gain in the primary design and non-free in the only design where it bites**. What replaces it: the **selector-level weight is the default everywhere**, and P4 survives only as a pre-registered, per-generator, opt-in variance device for the IPW-family estimators, under the applicability conditions below, with both weights reported.*

The construction, for the record and for the extensions. On **continuation turns only**, over the randomized non-`STOP` arms,
$$\rho_t^{\rm mar}=\frac{\sum_{k\in\mathcal K_G}\pi_t(k\mid H_t)\,q_k(\tilde A_t\mid H_t)}{\sum_{k\in\mathcal K_G}e_t(k\mid H_t)\,q_k(\tilde A_t\mid H_t)}=E\big[\rho_t^{\rm sel}\mid H_t,\tilde A_t\big],$$
so it is valid, has weakly smaller variance by conditional Jensen, and obeys the same $\delta^{-1}=8$ per-turn bound. Equality holds iff the selector ratio is a.s. $\sigma(H_t,\tilde A_t)$-measurable — **not** iff $K_t$ is recoverable from $(H_t,\tilde A_t)$.

Four conditions and concessions now attach to it; none is optional.

1. **The sum runs over $\mathcal K_G$, never over $\mathcal K$.** There is no emitted message and no density $q_{A_0}(\tilde a\mid h)$ on $\mathcal L$ for `STOP`, so a sum over all of $\mathcal K$ leaves $\rho^{\rm mar}$ **undefined at any stop turn**, and the stopping event is $\mathcal K$-measurable and so cannot be integrated out of the trajectory. This is not repaired by a separate stop factor: under R2 the stop coordinate contributes **no** factor at all, because the harness runs to $T_{\max}$ and the stop value is read off $\psi(H_k)$ unweighted. $\rho^{\rm mar}$ is a device for the class-override coordinate and nothing else.
2. **P4 and the finite-sum, text-critic-free DR of T9(iii) cannot both be had.** $\rho_t^{\rm mar}$ is $\sigma(H_t,\tilde A_t)$-measurable while $\hat Q_t(H_t,K_t)$ is $\mathcal K$-measurable, so $E[\rho_t^{\rm mar}\hat Q_t(H_t,K_t)\mid H_t]\ne\sum_k\pi_t(k\mid h)\hat Q_t(h,k)$: the telescoping identity behind T9(i)'s exact unbiasedness **breaks**, and restoring it requires the matched nuisance $E[V_{t+1}\mid H_t,\tilde A_t]$ with $\hat V_t(h)$ summed over the marginal target kernel — i.e. precisely the summation over text that T9(iii) advertises as avoided. **Decision:** P4 is restricted to the IPW and clipped-IPW estimators (E4); the sequential-DR estimator (E1) **must** use the selector-level weight to retain exact unbiasedness. The T20 certificate is no longer a use case, because T20 is withdrawn as a deliverable (R4).
3. **The rule is opt-in per generator, not a general rule.** "Marginalize over every recorded latent randomization whose density you can compute" inherits, per generator, the whole D2 failure catalogue: discarded chain-of-thought, best-of-$n$ or retries, tool calls inside the generator, speculative decoding, template/tokenizer mismatch, and use of the model distribution where a truncated sampler ran. Any one of these makes $q_k$ wrong, and a wrong $q_k$ converts an **exactly unbiased** selector weight into a biased marginal weight — trading away the document's strongest claim (T9(i)) for variance. P4 may be used for a given generator only if that generator satisfies the D2 conditions (plain autoregressive sampling, sampling-time truncated distribution, fully recorded randomness, non-degenerate and overlapping supports, computable densities), the choice is **pre-registered before any outcome is seen**, and **both weights are reported** so the discrepancy is visible. The recommended diagnostic P18(a) is conceded to have no power in exactly the degenerate-weight regime where marginalization is most tempting, so it cannot be the gate.
4. **Cost, priced.** $m_G=8$ teacher-forced scoring passes per turn per unit, on the sampling-time truncated distribution. At the measured receiver cost (3.2 s per 3B call, four contended slots, $\approx2{,}150$ calls/hour) this competes head-on with the branch budget and must be priced against the 20,000-call ceiling before P4 is enabled on any LM-generator arm.

**Signal–variance tension** (retained, with one correction). If all $q_k$ coincide then $W\equiv1$, variance is minimal and $V(\pi)=V(e)$ for every $\pi$: zero signal. "Randomize over many paraphrases" is statistically cheap and causally empty. Generators must be *semantically* distinct. The correction: in the frozen design they already are, and the template renders are distinct with probability one, so there is no lexical overlap left for P4 to recover — the closing promise that "P4 then recovers whatever lexical overlap exists at no cost to the estimand" is **withdrawn for the primary design** (the gain is identically zero there) and holds only in the LM-generator extensions, at the per-turn cost priced in item 4. Note also that $V(e)$ appears here only as a diagnostic denominator: it is the $\delta$-floored mixture over eight arms **including** the negative-control, placebo and leaky diagnostic arms, so $V(\pi)-V(e)$ is monotone in the number of deliberately degraded arms and is not a baseline (R4(c)); the reported denominator is computed on the evaluated stratum $\{A_0,\dots,A_5\}$ and the headline comparison is against B4.

---

---

## 4. Estimability: positivity, weights, horizon

### The reframing
In a language action space, the classical positivity assumption is doing two jobs — identification and $\sqrt n$-estimability — and they must be separated. Uniform positivity over $\mathbb L$ **is** violated (no fixed $\delta$ bounds the probability of a message). Absolute continuity may or may not hold; on a full-support softmax it does, and then *every* policy value including the value of one fixed text is identified, with effective sample size of order $n\,e^{-\Theta(m)}$ — identification and estimability come apart by tens of orders of magnitude. Under a **truncated sampler** (top-$p$/top-$k$/min-$p$/grammar masks — i.e. every real deployment), absolute continuity *fails* for any target that changes the mask, and then the value is **unidentified**, not merely high-variance. Hence A8 is a first-class assumption, verified from the recorded masks, and the choke-point design satisfies it by construction because targets only reweight fixed generators.

**Two arithmetic facts that govern every number in this section, and were wrong in the draft.**

1. **A uniform floor is feasible only if $m_G\delta\le1$.** A floor $\delta$ on each of $m_G$ randomized arms requires $m_G\delta\le\sum_k e_t(k\mid h)=1$, so $\delta\le1/m_G$. The draft's recommendation $\delta\ge0.25$ is satisfiable only for $m_G\le4$ and is **withdrawn as arithmetically infeasible** for the frozen taxonomy. The frozen design randomizes uniformly over the $m_G=8$ non-`STOP` generator classes $\mathcal K_G=\{A_1,\dots,A_8\}$ at $e_t(k\mid H_t)=1/8$, so
$$\boxed{\delta=1/8=0.125},\qquad m_G\delta=1.000\ \text{(equality)},$$
and `STOP` ($A_0$) is **exempt from A6**: $Y(A_0\text{ at }k)=V_k$ is $H_k^A$-measurable, so positivity for `STOP` holds by degeneracy, with no randomization, no nuisance model and zero GPU. Every occurrence of $\delta=0.25$, $E[W^2]\le16$, $M=16$, $\delta=0.1$ and $d=3$ in the draft of this section is corrected below.
2. **The i.i.d. unit is the task instance, and $n$ means clusters.** The draft's arithmetic was in "conversations" while §1 declares the task instance and §5 requires all branches, seeds, turns and paraphrase variants of one task to share a fold. Seeds, branches and turns are **within**-cluster; the 1,520 paired units are $190\times8$ root seeds sharing one saved root $O_1$ and are *not* 1,520 independent units. The honest count is $n_{\rm clusters}=176$ task families (from 190 tasks), against a pool ceiling of $\approx230$ with the 3B receiver and $\approx100$ with the 7B (audits A2, A4, three independent routes to 230). Defining the unit as (task $\times$ seed) manufactures unlimited units out of a $\approx230$-element population whose task text is the dominant variance component (per-task first-attempt success $\mathrm{Beta}(0.348,0.230)$, strongly U-shaped), and it voids the independence every bound in this section needs. **Every quantity below is stated in clusters.**

The replacement for the floor is a **Rényi budget**, $\log E[W^2]=D_2(P^\pi\|P^e)\le\log(1/\varepsilon^2)$ — a joint property of the design and the evaluated class, which the analyst chooses and can verify. Read in cluster units: a budget of $E[W^2]\le M$ leaves $n_{\rm eff}\ge n_{\rm clusters}/M$, so with 176 clusters the entire Rényi budget available before the effective sample falls below 30 clusters is $M\le5.87$.

**What this section prices, and what the primary route actually is (conceded).** The apparatus here — the Rényi budget, P5, P6, the tilt budget — prices an **unpaired, off-policy, importance-weighted** design. That is not the design that will be run. The only affordable experiment is a **paired, common-random-number, on-policy** head-to-head in which every arm branches from the same saved root $O_1$ per (task, seed); the dominant variance component is between-task difficulty, pairing removes it, and **no formula in this section contains that term**. The pre-registered primary estimator is the mean over the 176 families of the family-mean paired difference with a paired family-clustered bootstrap (E0, R9), whose *measured* precision is a $\pm0.019$ half-width at $R=8$ root seeds and an MDE of $0.027$ at 80% power — a design whose precision is measured, against a section whose budgets are worst-case bounds. §4 therefore governs **tree reuse across candidate policies and the observational extensions**, not the headline comparison. Two further facts, both from R2, make this concrete: the only measured headroom is $+0.046$ of final success from **oracle stopping decisions**, and stopping-only regimes lie in $\Pi_0$ with $W\equiv1$ — **the deliverable the evidence supports needs no importance weights at all.**

### P5 (exact second moment; the override-depth bound)
Let $D$ be the number of decision points ($D=2$ in the frozen design, at turns $t=2,3$ of $T_{\max}=3$), let $T\le D$ be the random number of decision points at which a non-`STOP` action is taken, and let
$$w_t:=\frac{\pi_t(K_t\mid H_t)}{e_t(K_t\mid H_t)}$$
be the ratio on the **randomized coordinate only**, i.e. over $\mathcal K_G$. The stopping coordinate contributes **no factor** to $W$: the harness records $\psi(H_k)$ at every decision point, so a stopping regime's value is an *unweighted* mean (R2, T8a). Then, with the convention $\Gamma_{t+1}:=1$ on $\{K_t=\texttt{STOP}\}$ (and $\Gamma_{D+1}\equiv1$),
$$E[W_{1:T}^2]=E[\Gamma_1],\qquad \Gamma_t(h)=E\big[w_t^2\,\Gamma_{t+1}(H_{t+1})\mid H_t=h\big].$$
Equivalently, since $E[w_t^2\mid H_t]=1+\chi^2_t(H_t)$, write $\tilde w_t=w_t^2/(1+\chi^2_t)$ (conditional mean one) to get
$$E[W_{1:T}^2]=E_{\tilde P}\Big[\prod_{t=1}^{\tilde T}\big(1+\chi_t^2(H_t)\big)\Big],\qquad \tilde\pi_t(k\mid h)\propto \frac{\pi_t(k\mid h)^2}{e_t(k\mid h)} ,$$
where $\tilde T$ is the horizon **under $\tilde P$**: the tilted kernel $\tilde\pi\propto\pi^2/e$ re-weights the `STOP` selector too and therefore changes the stopping law, so the two displays do not share a horizon and must not be read as if they did.

**The naive identity $E_P[\prod_t(1+\chi^2_t)]$ is false**: the induction cannot factor because $\mathrm{Cov}\big(w_t^2,\ \Gamma_{t+1}(H_{t+1})\mid H_t\big)\neq0$ whenever the intervention moves the conversation into histories with a different forward second-moment factor. (The draft wrote $\chi^2_{t+1}$ here; the obstruction is the forward factor $\Gamma_{t+1}$, which is what the displayed recursion actually contains.) For the exponential tilt, $\tilde P$ is the $2\theta$-tilted law; the "exact and clean" Gaussian closed form holds only if the conditional variance is history-independent.

**Bounded case (what we actually use).** Let $d$ = *override depth*. Then $W\le\delta^{-d}$, and since $E[W]=1$,
$$E[W^2]\le\|W\|_\infty E[W]=\delta^{-d},\qquad n_{\rm eff}\ge n_{\rm clusters}\,\delta^{d}.$$
$\delta=1/8$, $d=1\Rightarrow E[W^2]\le8$; $d=2\Rightarrow E[W^2]\le64$. Since the frozen design has $D=2$ decision points, $d=2$ **is** full depth, so 64 is the worst case over $\Pi_{\rm cp}$, **not a knob setting** — the draft's "this is the design knob" is withdrawn, as is its $\delta=0.1,d=3\Rightarrow10^3$ illustration, which names a floor and a depth the frozen design does not have. In cluster units $n_{\rm eff}\ge n_{\rm clusters}\delta^{d}$: **176, 22 and 2.75 clusters** at $d=0,1,2$ (and 230, 28.75, 3.59 against the pool ceiling). A depth-2 off-policy evaluation on this pool has an effective sample size of **under three clusters**, which is why on-policy paired rollout is primary (R9, E0).

**Override depth is not a free knob; it is an entitlement class (R2).** $d$ counts **only decision points at which the regime overrides the generator-class distribution**. The draft priced everything at "$d\le2$" while advertising "the optimal regime", which deviates at every decision point and therefore has $d=D$; the two are reconciled by declaring, for every claim, which of three classes it is about.

| class | definition | bound | $n_{\rm eff}$ at 176 | how its value is obtained |
|---|---|---|---|---|
| $\Pi_0$ | stopping-only: $\pi_k$ on $\mathcal K_G$ equals $e_k$; only `STOP`/`CONT` is chosen | $W\equiv1$, $M=1$ | 176 | **unweighted means** on recorded trajectories; no importance weighting anywhere |
| $\Pi_1$ | depth-1 class override | $W\le8$, $M=8$ | 22 | off-policy estimable; report ESS and $\hat D_2$ with every number |
| $\Pi_2=\Pi_{\rm cp}$ | full depth ($d=D=2$), including $\hat\pi$ from backward induction | $W\le64$, $M=64$ | **2.75** | **on-policy rollout (E7) or re-logged policy iteration only**; off-policy certification explicitly disclaimed |

The exponential-in-horizon blow-up is bounded at $8^2=64$ **only** because the frozen design has two decision points; it is not tamed in general, and no claim in this document is quoted at a horizon of five.

*A note on truncation, since it is easily confused with a floor.* The simulated-log arm's "floor 0.2" is **not** a randomization floor ($8\times0.2=1.6>1$). It is a **weight-truncation level** ($\hat e$ clipped below at 0.2, so $w\le5$); it introduces clipping bias, A6 does **not** hold in that arm (the logging policy there is confounded by construction), and the truncation rate must be reported wherever that arm appears.

### P6 (curse of description length, not of horizon)
If instead the target tilts the token distribution,
$$\log E[W^2]\ \ge\ \mathrm{KL}(P^\pi\|P^e)=\sum_t\sum_j E\big[\mathrm{KL}_{\text{token }j}\big]=\bar\kappa\,\bar m\ \Longrightarrow\ n_{\rm eff}\le n_{\rm clusters}\,e^{-\bar\kappa\bar m},$$
by monotonicity of Rényi divergences and the autoregressive chain rule. At $\bar\kappa=0.05$, $\bar m=400$: $n_{\rm eff}\le n_{\rm clusters}\,e^{-20}=2.06\times10^{-9}\,n_{\rm clusters}$, i.e. $\le3.6\times10^{-7}$ clusters at $n_{\rm clusters}=176$. Sequence-level importance sampling over free text is not "high variance", it is dead. (The conclusion is unchanged by the unit correction; only the units are.)

**Design principle.** *Target and logging policy may differ only on a coordinate of $O(1)$ description length.* The decisive knob is the **temporal and structural granularity of randomization**, not the estimator. Two designs bracket the space: trajectory-level mixing over $m$ adaptive policies gives $W\le m$ uniformly in the horizon and in message length but contains no within-trajectory contrast (and a single-turn deviation *inside* such a design has an unbounded ratio, because the arm posterior concentrates once the first message is observed — so blip designs cannot be run inside it); per-turn choke-point randomization supports blips and learning at $\delta^{-d}$, with $\delta=1/8$ and $d\le D=2$.

**Budget arithmetic for the tilt extension, corrected, in clusters.** With $n_{\rm clusters}=176$, $D=2$ and $n_{\rm eff}^{\min}=30$: $\sum_t\Delta_t^2\le\log(176/30)=1.769$, i.e. at most $\Delta_t\le0.941$ within-history SD and $\mathrm{KL}_t\le0.442$ nats per turn. This replaces the draft's "$n=10^4$, $T=5$, 0.96 SD / 0.46 nats", whose $n$ was in conversations and whose horizon was not this design's. Admissible tilt strength shrinks like $1/\sqrt D$. Note also that the tilt extension is exactly the regime in which A6 does not hold and the weight is not bounded by $\delta^{-d}$, so the tilt budget is an *extension* result and is not used for any reported primary number.

**One honest qualification.** $E[W^2]$ is the second moment of the *IPW* weight. The estimator we recommend has variance $\mathrm{Var}(V_1)+\sum_t E[W_{1:t}^2(V_{t+1}-Q_t)^2]$, involving weighted Bellman *residuals*, which can be orders of magnitude smaller. So a budget derived from $E[W^2]$ is a **worst case over outcome models**, and should be reported as such rather than as "what is learnable from $n$ logs". It is also a worst case over *designs*: it contains no pairing term, and the primary paired estimator's precision is measured directly ($\pm0.019$ at $R=8$), not derived from here.

**Affordability, since it binds before any of these budgets do.** A receiver call costs 3.2 s on the 3B (6.4 s on the 7B) at four contended slots, i.e. $\approx2{,}150$ calls per hour; the affordability ceiling is **20,000 receiver calls $\approx9.3$ h**. Any prescription in this section that implies more receiver calls than that is unaffordable and must be cut rather than quoted.

### T7 (blip decomposition)
$$V(\pi)-V(e)=\sum_t E^\pi\Big[\sum_k\big(\pi_t(k\mid H_t)-e_t(k\mid H_t)\big)Q^e_t(H_t,k)\Big],$$
by telescoping over hybrids $(\pi_1..\pi_{t-1},e_t..e_D)$. Equivalently $\sum_t E^\pi[A^e_t(H_t,\pi_t(H_t))]$ with $A^e_t(h,k)=Q^e_t(h,k)-\sum_{k'}e_t(k'\mid h)Q^e_t(h,k')$. The stop-coordinate specialization is $A^e(h,\texttt{STOP})=e^R\gamma$, $A^e(h,\texttt{CONT})=-(1-e^R)\gamma$ — note the propensity weight; the unweighted blip sum is wrong, because the blip only bites where the **logging policy $e$** would have deviated. The word *natural* is deleted throughout: in D1 the harness replaced the user, so there is no natural policy in the data, and "natural/logging policy" fused two different objects. One scope restriction on that specialization: it presumes a strictly positive logging propensity $e^R$ for `STOP`, which the frozen design does **not** have — randomization is uniform over the eight non-`STOP` classes and `STOP` is never drawn (R1) — so the stop-coordinate blip against a logging reference is a statement about the observational and simulated-log extensions only. In the frozen design a stopping regime's value is read off directly as an unweighted mean over recorded trajectories (T8a, $\Pi_0$), which needs no blip against $e$ at all.

**$V(e)$ is a diagnostic denominator, not a baseline.** $V(e)$ is the harness's own $1/8$-uniform mixture over eight arms **including** $A_6$ (DIVERT, negative control), $A_7$ (MISDIAGNOSE, placebo) and $A_8$ (PATCH, leaky). Each sits at probability $1/8$ and drags $V(e)$ down, so $V(\pi)-V(e)$ is **monotone in the number of deliberately degraded arms** and manufacturable with zero learning. Wherever T7 is read as a statement about improvement, $V(e)$ must be recomputed on the **evaluated** stratum $\{A_0,\dots,A_5\}$ with the diagnostic arms excluded, and the headline comparison is against the pre-registered baseline B4, not against $e$ (R4(c)–(d), T20).

**Design corollary.** A policy deviating at a **single** decision point $s$ has $W_{1:s-1}=1$ and a one-turn ratio $\le1/\delta=8$, independent of the horizon *and of message length*. Micro-randomizing one uniformly chosen decision point per trajectory therefore identifies the point-$s$ blip with effective sample size of order
$$n_{\rm clusters}\,\delta\,P(T\ge s)/D ,$$
where the $1/D$ is the turn-selection factor and $P(T\ge s)$ is the **reach probability**, which the draft dropped. Both factors must be kept: under an endogenous horizon later decision points are reached far less often — P21's satisfied users stop — so the omitted factor is smallest exactly at the points of interest. In the frozen branched design the reach factor is benign by construction rather than by luck: the harness runs the recorded trajectories to $T_{\max}$ and grades $\psi$ at every turn, so $P(T\ge s)=1$ under the logging law and the factor bites only in the observational extensions, where the logging horizon is itself endogenous. Depth-$d$ regimes need randomization depth $d$, or a blip-model extrapolation — **which then becomes an identifying assumption and must be labelled as such.**

**Honest caveat.** One round of one-step blips against the logging reference gives a locally valid improvement *direction*, not the value of the greedy regime it suggests. Composing blips into a value requires backward induction with an optimal-future reference, or re-logging (policy iteration), which reintroduces the cost that off-policy evaluation was meant to avoid. At full depth the arithmetic says the same thing more bluntly: $d=D=2$ leaves 2.75 effective clusters, so a full-depth regime's value must come from on-policy rollout (E7), not from weighting.

### T8 (backward induction; the `STOP` arm in two information sets)

**T8a (analyst version).** Under A4, A15, A21 and a programmatic $\psi$ graded at every turn, $Q_t(H_t^A,\texttt{STOP})=\psi(H_t)$ **exactly**: the `STOP` arm carries no causal nuisance, has zero Monte Carlo variance, needs no nuisance model, consumes zero GPU, and requires no positivity (R1). This is the correct reading of the degeneracy $Y(A_0\text{ at }k)=V_k$, and it is what makes the stop coordinate weight-free (R2). Verifier determinism is measured, not assumed: 1,954 replicate verifications of 597 repeated `(task_uid, sha256(final_code))` pairs, 0 disagreements.

**T8b (policy version).** For $\pi\in\Pi_{\rm cp}$ the implementable stop value is $E[\psi(H_t)\mid\varphi_t(H_t)]$ — an **unknown regression**, the deployable policy's whole handle on "am I already right", a supervised calibration problem with no causal content but with first-order estimation error. It is not a known functional of anything the policy sees. The measured difficulty is on record: the visible verdict is one bit and is absent on 20.8% of the informative pool, and the sibling loop's own self-check stopped on **50.4%** [0.479, 0.528] of all failures. The **+4.6 pp** of headroom is the value of the **oracle** $V$, which is not available to any real rule.

Restated asymmetry: *the `STOP` arm's causal nuisance is nil and its prediction problem is the hardest estimation problem in the design.* **"The endogenous horizon costs nothing extra" is WITHDRAWN** — it costs the calibration of $E[\psi\mid\varphi]$ — and **"no medical analogue" is deleted**, since the medical analogue of T8b is ordinary prognostic modelling. The draft's unqualified "the only causal nuisance is the continuation value" and "the stopping decision is a scalar blip with a **known** stop-arm value" are withdrawn with it: they equivocated between $H_t^A$, which contains the hidden-test grade, and $\mathcal F_t^O=\sigma(\varphi_t(H_t))$, which by construction excludes $\psi$ and every hidden-test-derived quantity. A regime whose argmax is taken against the harness-known $Q_t(\cdot,\texttt{STOP})$ is P23's **prophet**, not an element of $\Pi_{\rm cp}$.

**Mandatory reporting.** Report the oracle-$V$ minus $\hat p$-rule value gap as a headline pair, never the oracle value alone.

**Resolution with A11(d) and §16 item 6.** The two readings are separated by information set, not by instrument. A11(d) is an **information-set restriction**: the stopping signal is $\varphi$-measurable and $\varphi$ excludes $\psi$ and every hidden-test-derived quantity, enforced by feature-builder assertion. With a programmatic primary outcome, $\sigma=0$ for the primary number, P24(ii)'s $\Theta(\sigma\sqrt{\log\bar K})$ optimism does not bite on it, and §16 item 6's "two prespecified independent measurement channels" is **replaced** by the $\varphi$-exclusion assertion rather than asserted alongside T8. If a judge is ever used for a secondary outcome, T8b applies together with R20's inflation term and the reported value must be re-estimated on a held-out scoring draw.

Hence
$$V_t^\star(H_t)=\max\Big\{Q_t(H_t,\texttt{STOP}),\ \max_{k\neq\texttt{STOP}}Q_t(H_t,k)\Big\}.$$

This recursion targets the **unrestricted-class** optimum. Under the $\varphi$-measurable class of §1 it returns $\pi^{\rm greedy}$, not $\arg\max_{\Pi_{\rm cp}}V$, unless A19b (state-representation sufficiency) is assumed — which the primary route does **not** assume. Because $\mathcal F_t^O\subsetneq\sigma(H_t^A)$, $\varphi$ is not sufficient, so the restricted optimum does not satisfy a Bellman equation on $\varphi$-measurable value functions; this is the standard failure of dynamic programming under a coarsened state, and T9's exact unbiasedness for any $\hat Q$ does not repair it, being a property of *evaluating* a fixed $\pi$ rather than of *optimizing*. The reported object is therefore
$$\hat\pi:=\arg\max_{\pi\in\Pi}\widehat V(\pi)$$
over a **pre-registered finite candidate set $\Pi$** whose count is declared in §16, with $\pi^{\rm greedy}$ entered as one member labelled "greedy-in-$\varphi$", evaluated out-of-fold over the 176 families and with the selection inflation reported (R16). The phrase "the optimal regime" is reserved for $\arg\max_{\Pi_{\rm cp}}V$, which this design does **not** report; $\Pi_{\rm cp}$ as used elsewhere is infinite, and where a covering-number bound would be needed for it we do not have one and say so.

**Non-regularity, in measured units.** Inference on $V(\pi^\star)$ is **non-regular** where blips vanish (exceptional laws), requiring $m$-out-of-$n$ bootstrap, adaptive intervals, or an online one-step construction; this is a **requirement** in §16, not a suggestion, because on this task family the exceptional set is most of the sample space rather than a corner. The measured null-blip mass for the 3B receiver is **0.156** of task mass below 0.05 hidden-test success (nothing repairs those tasks, so the blip is exactly 0), **0.334** above 0.95 (where the blip is dominated by breakage and the trivial rule "stop iff visible pass" already captures most of it, which is why baseline B4 is hard to beat), and only **0.406** informative. Report the mass of histories with $|\hat\gamma_t|$ near zero, since that mass drives the non-regularity, and note that it also attenuates any marginal blip. Consequently the primary estimand is defined **conditional on the first attempt failing**, with the already-correct stratum analysed separately for *harm* (repair 0.239 [0.210, 0.270] against degradation 0.162 [0.105, 0.242]).

**Well-posedness.** Without cost pricing or a positive tolerance the problem degenerates: if continuing weakly improves retained quality, the supremum is attained only at $\bar K$, and with a quality-first lexicographic objective and zero tolerance the same is true. A strictly positive tolerance $\eta_1>0$ is what makes an endogenous-horizon prioritized objective non-degenerate. A budget-constrained optimum equals the unpenalized optimum of $E[Y^\pi-\lambda C^\pi]$ for some $\lambda\ge0$ by LP duality over the convex hull of attainable (value, cost) pairs, and the constrained optimum is in general a randomization over at most two threshold rules. (That the two thresholds are *adjacent* requires a monotone value–cost trade-off we have not verified: **OPEN**.)

**The claim "$\lambda$ is a budget price, not a hyperparameter" is withdrawn as stated.** It is true economically and false statistically: the dual multiplier is a functional of $P$, determined by the supporting hyperplane of the convex hull of *attainable* (value, cost) pairs, which is unknown and would have to be estimated from the same data — so a one-sided interval or an EIF computed at a data-chosen $\hat\lambda$ is not valid at its stated level, and would omit $\hat\lambda$'s own influence contribution. The design therefore **pre-registers** $\lambda=0.01$ per turn (matching the sibling harness's turn penalty), with the grid $\{0,0.005,0.01,0.02\}$ and a **union bound over the grid** if more than one value is reported. $\lambda$ is a pre-registered hyperparameter carrying a budget-price *interpretation*, and the LP-duality reading is a post-hoc interpretation, not a licence to select $\lambda$ on the analysis sample. One further unit caveat inherited from the prioritized objective: $Y-\lambda C\in[0,1]$ is what the downstream bounds assume, so the prioritized pseudo-outcome $\tilde Y\in[-1,1]$ must be carried as $(\tilde Y+1)/2\in[0,1]$ before it enters any of them (T20(a), R6).

---

---

## 5. Estimators we will implement

**Notation, fixed here to avoid a collision introduced by R3/R8.** $\varphi_t$ denotes the
pre-registered **policy-observable feature map** of R3 ($H_t^O=\varphi_t(H_t)$,
$\mathcal F_t^O=\sigma(\varphi_t(H_t))$). The influence function of a value functional is
written $\mathrm{IF}(Z)$ in this section, not $\varphi(Z)$ as in the earlier draft. Nothing
else changes; the rename is bookkeeping, not a claim.

**Two standing facts that govern everything below** (R2, R3, R9).
Nuisances the analyst fits may use the full analyst/harness history $H_t^A$, including the
programmatic grade $\psi(H_s)$ of every artifact in hand. Policies may use only
$\varphi_t(H_t)$. Every weighted quantity in this section is weighted on the **randomized
generator-class coordinate only**: the harness runs each trajectory to $T_{\max}=3$ and
records $\psi(H_k)$ at every decision point $k\in\{1,2\}$, so the value of a stopping
decision is an **unweighted** mean and the `STOP` arm $A_0$ contributes no weight
(T8a, R2). The design has $D=2$ decision points, so the sum over $t$ below has at most two
terms, and the depth-graded entitlement classes of R2 are
$\Pi_0$ (stopping-only, $W\equiv1$, $M=1$), $\Pi_1$ (depth-1 class override, $W\le\delta^{-1}=8$),
$\Pi_2=\Pi_{\rm cp}$ (full depth $d=D=2$, $W\le\delta^{-2}=64$), at the feasible floor
$\delta=1/8$. **Every number reported from a weighted estimator must name its entitlement
class and its $M$.**

The i.i.d. unit is the **task instance (task text only)**: $n_{\rm clusters}=176$ task
families from 190 tasks, pool ceiling $\approx230$ (3B) and $\approx100$ (7B). Seeds,
branches, turns, templates and paraphrase variants are *within*-cluster. In cluster units
$n_{\rm eff}\ge n_{\rm clusters}\delta^{d}$ gives **176 / 22 / 2.75** clusters at
$d=0,1,2$ (**230 / 28.75 / 3.59** against the ceiling). A depth-2 off-policy evaluation on
this pool has an effective sample size of **under three clusters**, which is why the
ordering of routes below has been reversed relative to the earlier draft: **on-policy
paired rollout is primary, and the off-policy apparatus governs tree reuse across candidate
policies and the observational extensions.**

### T9 (EIF and sequential DR)
Set $V_{T+1}=Y-\lambda C$; on $\{K_t=\texttt{STOP}\}$ set $V:=Y-\lambda C$ and define $Q_t$ on the `STOP`-augmented action set. Then $Q_t(h,k)=E[V_{t+1}(H_{t+1})\mid H_t=h,K_t=k]$, $V_t(h)=\sum_k\pi_t(k\mid h)Q_t(h,k)$, $\psi=E[V_1(H_1)]$, and
$$\mathrm{IF}(Z)=V_1(H_1)-\psi+\sum_{t\le\tau}W_{1:t}\Big(V_{t+1}(H_{t+1})-Q_t(H_t,K_t)\Big),$$
a martingale difference sum: $E[W_{1:t}(V_{t+1}-Q_t)\mid H_t]=0$ by change of measure, since $A_t\sim\pi_t$ under $\pi$.

**$\lambda$ is pre-registered, not estimated.** T8's LP-duality reading — a
budget-constrained optimum equals the unpenalized optimum of $E[Y^\pi-\lambda C^\pi]$ for
some $\lambda\ge0$ — is an *economic* interpretation of a multiplier that is a functional of
$P$. It is **not** a licence to select $\lambda$ on the analysis sample. Were $\hat\lambda$
data-chosen, $Y-\lambda C$ would be a data-dependent estimand: the display above omits
$\hat\lambda$'s influence contribution, any one-sided finite-sample bound would cover an
event selected with the same data, and the prioritized reduction of T13 would inherit the
same defect. Accordingly $\lambda=0.01$ per turn is **pre-registered** (the sibling
harness's turn penalty), the grid $\{0,0.005,0.01,0.02\}$ is pre-registered, and if more
than one grid point is reported every interval carries a **union bound over the grid**. In
those terms $\lambda$ *is* a hyperparameter with a pre-registered value, and this document
says so rather than claiming it away by duality.

**(i) Exact unbiasedness — restated, and the unconditional form withdrawn.** The earlier
claim "with $e$ known, $E[\hat\psi]=\psi$ for **any** $\hat Q$ whatsoever" is **withdrawn as
written**: as stated it covers same-sample fits and $\hat V$ emitted independently of
$\hat Q$, and it is false for both. The correct statement is

> for any $\hat Q$ that is (a) **fixed conditional on the evaluation fold** and (b)
> **internally consistent**, $\hat V_t(h)=\sum_k\pi_t(k\mid h)\hat Q_t(h,k)$, we have
> $E[\hat\psi]=\psi$ **exactly** when $e$ is known.

Both conditions bind. (a) is a *sample-splitting* requirement, not a rate requirement:
A18 must be read as **A18a (cross-fitting / sample splitting — required in every design,
including D1, and not vacuous when $e$ is known)** and **A18b (product rate on
$(\hat e,\hat Q)$ — required only where $e$ is estimated, and vacuous in D1)**. Only A18b is
vacuous here; the ladder row that marked A18 wholesale "vacuous" licensed exactly the
same-sample implementation that voids this result. (b) fails for a critic that emits
$\hat V$ directly and for independently fitted $\hat V,\hat Q$; P10's branch-augmented
version survives only because the two rollout estimates agree **in expectation** given
$H_t$, which is worth saying because it is the whole reason branch augmentation preserves
exactness.

Which estimators attain it: the **cross-fitted one-step / AIPW** form does. **TMLE does
not** — it fluctuates $\hat Q$ using the same data through the clever-covariate score, so
its fitted values are data-dependent and only asymptotic validity holds ($O(1/n)$ bias).
**Clipped IPW (E4) is biased by construction** and **no self-normalized variant is exactly
unbiased.** Any statement elsewhere in the document of the form "a cheap badly-calibrated
LLM critic carries zero bias risk" must read "zero asymptotic bias, and exact
finite-sample unbiasedness for the cross-fitted one-step form only".

**(ii)** The second-order product-bias term therefore vanishes and $\hat Q$ affects variance
only. Asymptotic normality needs $\hat Q$ bounded, **fold-independent**, and convergent to
*some* fixed limit **in the weighted metric**:
$\|\hat Q_t-Q_t^{\infty}\|_{L_2(W_{1:t}\cdot P)}=o_P(1)$. The earlier side condition
$E[W^2\hat Q^2]<\infty$ is **deleted as vacuous** — it is implied by $W\le\delta^{-d}\le64$
and bounded $\hat Q$. Convergence under $W_{1:t}\cdot P$ is strictly stronger than under
$P$ and is the version that binds, which matters because the weighted measure concentrates
on exactly the histories §12 flags as thinly covered.

**(iii)** Because $\mathcal K$ is finite, $\hat V_t(h)=\sum_k\pi_t(k\mid h)\hat Q_t(h,k)$ is an **exact finite sum** — no summation over text, which is precisely what a token-level target cannot do. **But this and P4 cannot both be had, and the choice is made here.** P4's
Rao–Blackwellized *marginal* weight $\rho^{\rm mar}_t$ is
$\sigma(H_t,\tilde A_t)$-measurable while $\hat Q_t(H_t,K_t)$ is $K_t$-measurable, so
$E[\rho^{\rm mar}_t\hat Q_t(H_t,K_t)\mid H_t]\ne\sum_k\pi_t(k\mid h)\hat Q_t(h,k)$: the
telescoping that delivers (i) breaks, and restoring it requires the matched nuisance
$E[V_{t+1}\mid H_t,\tilde A_t]$ together with a sum over messages — i.e. exactly the
summation over text that (iii) advertises as avoided. Decision: **E1 uses the
selector-level weight**, and P4's marginal weight is restricted to the IPW and clipped-IPW
forms (E4), where it is a pure variance statement and no critic is involved. P4 is in any
case **an identity with no gain in the frozen design** (R7): the generators are
deterministic template renders with a uniformly drawn index over 3 frozen templates, so
$q_k$ is a point mass given the recorded index, distinct $k$ produce distinct texts,
numerator and denominator each collapse to one term, and the Rao–Blackwell variance
reduction is **identically zero**. It is non-free in the only design where it would bite
(LM generators: $m_G$ teacher-forced scoring passes per turn on the realized message, at the
sampling-time truncated distribution, competing directly with the branch budget).
$\rho^{\rm mar}$ is also undefined at a stop turn — there is no emitted message — so it is
stated only on continuation turns, with the stop coordinate carried as a separate exact
factor.

**(iv) When $e$ is *estimated*** the remainder carries **cross terms**: the sufficient condition is $\big(\max_s\|\hat e_s-e_s\|\big)\big(\sum_t\|\varepsilon_t\|\big)=o_P(n^{-1/2})$ with $\varepsilon_t$ the weighted Bellman residual, not an index-matched product. In D1 this is vacuous because $e\equiv1/8$ by construction (measured positivity 1.0 at every branched state). It binds only in the **simulated-log arm**, and that arm must be described correctly wherever it appears: its pre-registered **floor 0.2 is a weight-truncation level, not a randomization floor** ($8\times0.2=1.6>1$, so no such floor is feasible). $\hat e$ is clipped below at 0.2, so $w\le5$; the clipping introduces bias; **A6 does not hold in that arm**, whose logging policy is confounded by construction; and the truncation rate must be reported with every number from it.

**(v) Does knowing $e$ lower the longitudinal efficiency bound? — no longer OPEN.** The
earlier "we decline to assert the longitudinal statement" is **withdrawn**: it follows in two
lines from the influence function displayed above. Project $\mathrm{IF}$ onto the turn-$t$
treatment tangent space, $E[\mathrm{IF}\mid H_t,K_t]-E[\mathrm{IF}\mid H_t]$. The turn-$t$
residual has conditional mean zero given $(H_t,K_t)$; all later residuals have conditional
mean zero; all earlier terms and $V_1(H_1)$ are $H_t$-measurable. The difference is
identically $0$, so $\mathrm{IF}$ has zero component in $\bigoplus_t\mathcal T_{A_t}$.
Removing that subspace — which is exactly what knowing $e$ does — leaves $\mathrm{IF}$ an
influence function lying in the reduced tangent space, so it is the EIF in both models and
$\mathrm{Var}(\mathrm{IF})$ is the bound in both. **Knowing $e$ does not lower the
longitudinal bound for a fixed $\pi$**; the Hahn (1998) point-treatment analogue does carry
over (van der Laan–Robins). What knowing $e$ buys is **exact finite-sample unbiasedness and
design-based validity, not asymptotic efficiency** — which is what the document wanted to
say. The OPEN flag is narrowed to the cases where it genuinely survives: MSM parameters
indexed by $e$; $V(\pi^\star)$ under exceptional laws; and the $P$-dependent tilt regime of
T30, whose intervention itself depends on $P$. §15 item 1 is amended accordingly.

### The estimator menu

**Ordering, corrected.** The earlier menu presented unpaired off-policy machinery as primary
and on-policy rollout as a seventh afterthought. That ordering priced a design nobody will
run: the only affordable experiment is a **paired, common-random-number, on-policy**
head-to-head in which every arm branches from the same saved root output $O_1$ per
$(\text{task},\text{root seed})$, the dominant variance component is between-task difficulty
(measured per-task first-attempt success $\sim\mathrm{Beta}(0.348,0.230)$, strongly
U-shaped), and pairing removes it. No variance formula in the earlier draft contained that
term. E0 is therefore listed first and is primary; E7 is its rollout engine.

- **E0. Paired common-random-number on-policy contrast (PRIMARY).** The pre-registered
  estimator: the mean over the **176 task families** of the family-mean paired difference
  $D_i$, with a **paired family-clustered bootstrap** ($B=10{,}000$, percentile 95% CI).
  Families, not tasks, are the bootstrap and cross-fitting unit, because families are the
  cross-fitting unit. 1,520 paired units $=190\times8$ root seeds sharing one saved root
  $O_1$ are **within**-cluster and do not enter as independent observations. Variance is
  written in $\mathrm{Var}(D_i)$ at the family level, so the between-task component is
  cancelled rather than paid for. Measured precision: half-width **$\pm0.019$** at $R=8$
  root seeds ($\pm0.026$ at $R=4$, $\pm0.015$ at $R=12$, $\pm0.013$ at $R=16$); **MDE 0.027**
  at 80% power. For **stopping-only regimes ($\Pi_0$) this estimator carries no importance
  weights at all** ($W\equiv1$), which matters because the only measured headroom — **+0.046**
  of final success from oracle stopping decisions — lies entirely in the stopping
  coordinate. A finite-sample one-sided version, if reported, is a paired empirical-Bernstein
  bound on $D_i\in[-1,1]$ certified on $(D_i+1)/2\in[0,1]$, never on $D_i$ directly, since
  sign-definiteness and the second-moment bound both require a non-negative summand.
- **E1. Cross-fitted one-step / AIPW with known weights (primary among the off-policy
  estimators).** Efficient, exactly unbiased under T9(i)(a)–(b), no text critic, selector-level
  weight (T9(iii)). **The TMLE variant — logistic fluctuation of $\hat Q_t$ with $W_{1:t}$ as
  clever covariates — is demoted from co-primary to a robustness row**, because it fits the
  fluctuation parameter on the data it evaluates and is therefore *not* finite-sample exact;
  it keeps in-range fitted values and solves the EIF equation, and those are its only
  advertised properties here.
- **E2. g-estimation of a choke-point SNMM for blips.** $\sum_i\sum_t d(H_{it})\{\mathbf 1\{K_{it}=k\}-e_t(k\mid H_{it})\}U_{it}(\beta)=0$ with
  $$U_{it}(\beta)=(Y_i-\lambda C_i)-\sum_{s\in\{t,\dots,\min(T_i,\bar K)\}}\gamma_s(H_{is},K_{is};\beta)$$
  and isotonic constraints along ordered axes. Three corrections to the earlier form, all
  needed and none cosmetic. (1) The residual is blipped down from the **value outcome**
  $Y-\lambda C$, not from $Y$; the earlier display used $Y$ while the estimand is
  $Y-\lambda C$. (2) Because `STOP` is one of the treatment levels, the treatment at turn $t$
  changes the *number of subsequent turns*, so the additive representation needs a reference
  regime and an explicit stop convention: the reference is a **continuation regime defined to
  the administrative cap $\bar K$ (never `STOP`)**, the index set is
  $\{t,\dots,\min(T_i,\bar K)\}$, and at a stop turn
  $\gamma_s(H_s,\texttt{STOP}):=E[Y^{(\text{ref from }s)}\mid H_s]-\psi(H_s)$ — the blip
  absorbs the entire value of the turns that never occurred. Without that convention the
  blip-down identity $E[U_{it}\mid H_{it}]=E[Y^{(\text{ref from }t)}\mid H_{it}]$ does **not**
  follow from §1's definitions, and A14 ("singleton or pinned reference arm") does not supply
  it. The conditional mean-zero property is re-checked turn by turn under that convention.
  (3) With an **active** isotonic constraint $\hat\beta$ has non-standard
  (boundary / cube-root-type) asymptotics; the unconstrained fit is reported alongside, or a
  projection-based interval is used. E2 requires only **per-turn** overlap, so it escapes the
  trajectory budget; the price is that identification of $\beta$ leans on the blip model.
- **E3. Branch-augmented DR** (P10 below).
- **E4. Clipped IPW + empirical Bernstein — retained as a diagnostic only.** The
  improvement certificate T20 it was built for is **withdrawn as a deliverable** (R4): at
  $n_{\rm clusters}=176$ the smallest gap it can resolve is **0.542** for an unweighted
  comparison against **+0.046** of available headroom, and it is *arithmetically impossible*
  for any weighted regime, since the required gap (1.53 at $M=8$) exceeds the range of
  $Y-\lambda C\in[0,1]$. E4 therefore produces a scope statement and a diagnostic
  denominator, not a guarantee. Three technical points survive and must be stated where E4
  appears: never self-normalize inside a certificate; at the recommended $M=\delta^{-d}$
  **clipping never binds and the clipping bias is identically zero**, so T20(a)'s
  sign-definiteness is not load-bearing in the primary route and the $E[W^2]/M$ bound is
  vacuous rather than alarming; and sign-definiteness and $E[\min(W,M)^2]\le M$ both require
  a **non-negative** outcome, so the prioritized pseudo-outcome $\tilde Y\in[-1,1]$ (E5,
  T13) must be certified on $(\tilde Y+1)/2\in[0,1]$ and never on $\tilde Y$.
- **E5. Rank-transformed DR** for the prioritized outcome (T13, T14) — **demoted to a
  secondary reporting device.** $\tilde Y=2G_0(u(Z))-1$ is a fixed known measurable transform
  **only because $G_0$ is frozen on an independent pre-registered reference sample**: the
  sibling project's completed **4,488-episode** log on the identical task pool (verified
  `tasks_sha256`, same machine, inference server and quantizations), hashed **before any
  outcome of this run is examined**. That freeze costs zero GPU time and zero clusters and is
  what buys the verbatim reuse of T8a and T9; its price is that the reported win probability
  is **reference-dependent on a frozen reference** and $\pi^\star$ is reference-dependent with
  it. Had $G_0$ been estimated on the analysis sample, $\tilde Y$ would carry an outcome-law
  nuisance, the $\tilde Y_i$ would be dependent, the martingale-difference argument would
  fail, exact unbiasedness would degrade to double robustness with a second-order remainder,
  and $Q_t(\cdot,\texttt{STOP})$ would become an estimated nuisance — which is why the
  two-term influence function retained in §7 is displayed there as what *would* be required
  and is not used confirmatorily. The demotion is independent of the freeze: $Y$ is a binary
  hidden-test verdict and $N\in\{1,2,3\}$, so with tolerances the ordered quotient has about
  six cells, the tie mass is the majority of pairs, and the estimand is a coarse monotone
  re-expression of a $2\times3$ table whose variance is dominated by tie handling — on an
  effect already at 0.015–0.030 it *shrinks* what it measures. **Report the tie mass.** The
  primary objective is $E[Y^\pi-\lambda C^\pi]$ at $\lambda=0.01$/turn with **degradation
  reported separately** (measured 0.162 [0.105, 0.242]), never folded into a mean.
- **E6. Tilt DR** for the observational extension (T30).
- **E7. Direct on-policy rollout** for $V(\pi)$ whenever the environment is resettable — the
  engine of E0 and, for **full-depth regimes $\Pi_2=\Pi_{\rm cp}$, the only admissible route**:
  at $M=64$ off-policy evaluation has **2.75 effective clusters** on this pool, so off-policy
  certification of a full-depth regime is explicitly disclaimed rather than attempted. Saying
  this plainly is more useful than reporting an off-policy interval three times the effect
  size. Off-policy evaluation is legitimate only for: reusing one expensive dataset across
  many candidates and a policy search; policies whose deployment is costly, slow or risky;
  and logs from real users. If none applies, the OPE apparatus is decoration.

### P10 (branch-augmented DR and budget allocation)
Replacing $\hat Q$, $\hat V$ by fresh rollouts from the logged history keeps exact unbiasedness and the martingale property (rollout noise is independent of the logged residual given $H_t$, by A2/A13), and the exactness argument of T9(i)(b) goes through because the two rollout estimates agree **in expectation** given $H_t$. There are **two** noise sources, because $\hat Q_t(H_t,K_t)$ enters weighted by $W_{1:t}$ while $\hat V_t(H_t)$ enters by $W_{1:t-1}$. The earlier additive display was wrong in two ways and is replaced:
$$\mathrm{Var}\approx\sum_tP(T\ge t)\Big[\frac{E[W_{1:t}^2]\sigma^2_{Q,t}}{m_t}+\frac{E[W_{1:t-1}^2]\sigma^2_{V,t}}{m'_t}-\frac{2\pi_t(K_t\mid H_t)E[W_{1:t-1}W_{1:t}]\sigma^2_{Q,t}}{m_t}\Big]+V_0 .$$

**(a) The cross term.** If the *same* branch rollouts serve both nuisances the two noise
sources are **not independent**: $\hat V_t(H_t)=\sum_k\pi_t(k\mid H_t)\hat Q_t(H_t,k)$
contains the arm-$K_t$ rollout mean that also constitutes $\hat Q_t(H_t,K_t)$, and the two
enter with opposite signs at weights $W_{1:t-1}$ and $W_{1:t}$. The earlier additive form was
therefore neither exact nor a bound, and allocating $(m_t,m'_t)$ separately double-counted
the shared rollouts. **Decision: draw disjoint rollout sets** for $\hat Q_t(H_t,K_t)$ and for
$\hat V_t(H_t)$, in which case the cross term is zero, the additive formula is exact, and the
two allocations are genuinely separate. If shared rollouts are used instead, the cross term
above must be carried into the Lagrangian before it is solved. §13(b) item 7's
"corrected two-noise-source" contribution is restated in these terms.

**(b) The reach probability.** The endogenous horizon was missing. A trajectory contributes at
turn $t$ only if it reaches $t$, hence the $P(T\ge t)$ factors, and the budget constraint must
charge for reaching $t$: $\sum_t(c_0t+c_t)m_tP(T\ge t)\le B$ with $c_0$ the roll-in cost that
P5b carries and P10 previously omitted. Under that constraint $m_t\propto\sqrt{\alpha_t/c_t}$
with optimal value $(\sum_t\sqrt{\alpha_tc_t})^2/B$ in the disjoint-rollout case, where
$\alpha_t=P(T\ge t)E[W^2_{1:t}]\sigma^2_{Q,t}$.

**(c) "Spend the branching budget late" is withdrawn as a theorem and retained as a
measurable condition.** The slogan rested on an unverified monotonicity. With override depth
$d\le D=2$ and deviations at early turns, $E[W^2_{1:t}]$ is **flat** for $t>d$, while
$\sigma^2_{Q,t}$ typically *shrinks* late (less remaining trajectory randomness) and
$P(T\ge t)$ decays — and P21 says late histories are rare because satisfied users stop, so the
omitted factor is smallest exactly at the turns of interest. So $\alpha_t$ need not grow and
the allocation can point **early**. Rule as it now stands: estimate $\alpha_t$, $c_t$ and
$P(T\ge t)$ in the pilot and allocate by the formula, not by the slogan; "spend late" holds
only when the growth in $E[W^2_{1:t}]$ outruns the decay in $P(T\ge t)\sigma^2_{Q,t}$, which is
a measurable condition. What survives intact is the structural point: P10 exhibits a
continuum from pure IPW, through learned-critic DR and branch-based DR, to full rollout, and it
is the constructive answer to "if you can branch, why estimate?" — you can only branch at a few
nodes, and this says which.

### P5b (design allocation: estimation and benchmarking want opposite designs)
With paired branch contrasts $D_i=\gamma(H_i)+e_i$, $\gamma(h)=\phi(h)'\beta+u(h)$, and a call budget $B\propto n(c_0+n_b)$ including the roll-in cost $c_0$,
$$\mathrm{Var}(\hat\beta)\propto\frac{\sigma_e^2/n_b+\sigma_m^2}{n}.$$

**The conclusion drawn from this in the earlier draft — "the budget-optimal design for
fitting a blip model is the widest one, $n_b=1$ paired contrast per history" — is WITHDRAWN
as false in general.** Substituting $n=B/(c_0+n_b)$ gives
$$f(n_b)=\Big(\frac{\sigma_e^2}{n_b}+\sigma_m^2\Big)(c_0+n_b)=\frac{\sigma_e^2c_0}{n_b}+\sigma_e^2+\sigma_m^2c_0+\sigma_m^2n_b,\qquad f'(n_b)=\sigma_m^2-\frac{\sigma_e^2c_0}{n_b^2},$$
so $f$ is **decreasing** on $n_b<\sigma_e\sqrt{c_0}/\sigma_m$ and only then increasing: the
optimum is **interior**,
$$n_b^\star=\max\big(1,\ \sigma_e\sqrt{c_0}/\sigma_m\big),$$
and $n_b=1$ is optimal only in the regime $\sigma_m^2\ge\sigma_e^2c_0$, equivalently
$c_0\le\sigma_m^2/\sigma_e^2$ — which was never asserted and is unlikely here, since the
roll-in cost of a multi-turn conversation is substantial and branch outcome noise $\sigma_e$ is
large relative to blip heterogeneity $\sigma_m$ in exactly the small-effect regime this project
expects. The monotone-increasing claim holds only in the $c_0=0$ special case, which contradicts
the document's own cost model; §14 Route D records $B\propto n(c_0+n_b)$ as a deliberately
carried correction. **§16 item 4 must pick $n_b$ from a pilot estimate of
$(\sigma_e,\sigma_m,c_0)$ rather than hard-coding $n_b=1$**, and the direction of the earlier
prescription was probably inverted.

**The frozen value, and what it costs.** The design freezes $n_b=3$ branch replicates. That
is a **budget decision, not the solution of the display above**, and the document says so.
Its measured consequences: per-state Monte Carlo SE **up to 0.29**, variance floor
$\hat v\approx0.08$ per state. The earlier "narrow deep benchmark slice with $n_b\gtrsim8$"
is **withdrawn as unaffordable**: at 400 states $\times$ 8 classes, $n_b\ge8$ is 25,600 nodes,
above the measured **20,000-call / 9.3-hour** affordability ceiling. The slice is run at the
$n_b$ the node ceiling permits, and the resulting resolution is reported with it.

**Three conditions the deep slice must satisfy, none of which the earlier text stated.**

1. **Matched-slice condition for $\hat v$.** T27's debiased risk
   $\hat R=n^{-1}\sum_i(\hat\gamma-\tilde\gamma)^2-n^{-1}\sum_i\hat v$ is unbiased only if
   $E[\hat v]$ averages over the **same history law** as the squared-error term. Importing a
   deliberately narrow, selected deep slice's average $\hat v$ into a wide slice's risk is
   valid only if the two slices share that law. Either estimate $v$ on a **random subsample of
   the validation histories** ($n_b=2$ suffices for unbiasedness, at high variance), or require
   and **verify** that the deep slice is a uniform random subsample of the wide slice's
   histories. Otherwise only the **ranking** use of T27 is available, where the offset cancels.
2. **Dependence exposure — the deep slice is the worst case in the design, not the best.** It
   repeatedly re-sends near-identical prefixes for one task instance, which is the
   maximal-exposure configuration for provider-side prefix/KV caching and batch-level numeric
   coupling — the A1 threats §12.13 lists and §9 concedes exist even at temperature 0. Client
   side one cannot verify caching is off, and "verify caching changes latency and not tokens"
   **cannot detect it**: prefix caching changes kernels and numerics, not token counts. This
   matters more here than for ordinary arms because $\hat v$ is estimated from within-node
   replicates and will absorb cache-induced dependence as independent Monte-Carlo noise,
   biasing $E[\hat v]$ and hence $\hat R$ by an unknown amount. Required: **interleave branch
   expansions across task instances with a cooldown** rather than expanding a node's arms back
   to back; **randomize expansion order** (already required for the permutation test, and now
   applied to the deep slice); **power the P18(c) duplicate-arm check specifically on the deep
   slice** and report the duplicate-arm discrepancy beside $\hat v$ as a headline diagnostic,
   declaring $\hat v$ and $\hat R$ **unusable** if the discrepancy exceeds $\hat v$; and replay
   a **fixed-prompt canary battery each block** to detect prefix-cache and numeric drift
   directly. Note that `llama.cpp` at `-np 4` is not bit-deterministic across batches even at a
   fixed seed, which is why the design is paired rather than assuming independence.
3. **Selection inflation in estimator ranking.** Offset cancellation makes the ranking
   criterion unbiased *for each fixed learner*; taking the minimum over $L$ candidate learners
   on one noisy criterion computed on the **smallest** sample in the study biases the winner's
   apparent risk downward by roughly $\sigma_R\sqrt{2\log L}$ — the pathology P11 catches for
   branch selection and P24(ii) for stopping, and which §13(a) already cites
   Andrews–Kitagawa–McCloskey for. Required: **split the deep slice into a ranking half and a
   reporting half** and report the winner's risk on the held-out half, or report an
   AKM/Bonferroni-corrected interval; in either case report **$L$** and the spread of $\hat R$
   across candidates.

What survives: the two-slice structure itself. For **fitting a blip model** the budget-optimal
width is $n_b^\star$ above, not the boundary; for **pointwise oracle truth** one needs
$n_b\gtrsim\sigma_e^2/\varepsilon^2$ per arm; carve out a **wide shallow training slice** and a
**deep benchmark slice**, and the deep slice remains the only place the Monte-Carlo variance
floor $v(h)$ needed by T27 can be estimated — subject to condition 1.

### P11 (winner's curse in branch selection)
$0\le E[\max_k\bar Y_k]-\max_kQ(h,a_k)\le\sigma\sqrt{2\log K/n_b}$ — an **upper bound**; for $K=8$ i.i.d. Gaussian errors the actual inflation is about $1.43\sigma$, not $2.04\sigma$, where $\sigma$ here is the standard error of a branch mean. Selection/evaluation splitting within each node gives an estimate unbiased for the implemented data-dependent rule and conservative for $\max_kQ$. At the frozen $n_b=3$ with $K=8$ and a measured per-state Monte Carlo SE of up to 0.29, the inflation from "branch eight prompts and report the best" is of order **0.4** — roughly an order of magnitude above the **+0.046** of measured headroom, and larger than any effect this project expects to report. This is the same selection mechanism as P5b condition 3 and P24(ii), and it is the reason ground truth is usable **pooled or on strata, not per state**.

### Cross-fitting scheme
**5 folds at the task-family level** over the **176 families**: all branches, replicate seeds,
turns, templates and paraphrase variants of one task in the same fold. Five critic instances,
each fit on four folds; every live decision scored by the critic whose training folds exclude
that unit's family, so the "policy" is a fold-indexed family of policies and every live decision
is out-of-family. The **fold-to-fold argmax agreement rate** is reported and is an abort trigger.

**$n$ means clusters, everywhere.** The i.i.d. unit is the task instance (task text only);
$n_{\rm clusters}=176$, ceiling $\approx230$. Defining the unit as (task $\times$ seed) would
manufacture unlimited units out of a $\approx230$-element task population whose **task text is
the dominant variance component**, which is precisely the loophole that made the earlier
sample-size arithmetic look feasible while voiding the independence any i.i.d. bound needs.
Wherever $n$ appears in this document it is stated as $n_{\rm clusters}$ and checked against
176. Averaging weighted terms within a task can only reduce the second moment, so
$E[\min(W,M)^2]\le M$ survives at the cluster level; what does not survive is the pretence that
there are more clusters than there are.

**Model-version epoch is DELETED as a clustering level.** The earlier prescription — cluster by
time block **and model-version epoch**, and randomize arms within time blocks so residual
provider drift is "balanced rather than confounded" — is **withdrawn as incoherent with A2**.
A2 states that violation of the frozen-receiver condition makes the estimand **undefined, not
noisy**, and §12.9 states that all uncertainty is conditional on one frozen receiver. Clustering
variance by epoch treats snapshot drift as a random component of sampling error around a single
well-defined parameter, which is only coherent if the estimand is redefined as an average over a
population of snapshots; balancing a version change across arms averages two estimands the
document has declared non-combinable; and cluster-robust inference on a handful of epochs is
invalid on its own terms (few-cluster bias), so it is not even a conservative fix. It is also
the prescription an implementer would actually follow, silently converting an
undefined-estimand event into a slightly wider interval. **Regime chosen: A2 holds.** Estimates
are reported **per pinned snapshot**; clustering is by **task family** (primary) and time block
only. Drift is handled by a **tripwire-and-discard rule**: a fixed canary prompt battery
replayed at the start of every block, compared by the P18(c) two-sample next-token
log-probability test with pre-registered multiplicity control; on detection the affected blocks
are **excluded** and the run is reported as **two separate receiver-conditional analyses**. Time
blocking is retained only for within-epoch nuisances (load, latency, contention) and is stated
explicitly **not** to be a remedy for a version change.

**Report with every weighted quantity:** the **entitlement class** ($\Pi_0$, $\Pi_1$ or
$\Pi_2$) and its $M\in\{1,8,64\}$; per-turn ESS $=(\sum_iw_{it})^2/\sum_iw_{it}^2$;
$\hat\chi^2_t$; $\hat D_2$; $n_{\rm eff}$ in **cluster** units (176 / 22 / 2.75 at $d=0,1,2$;
230 / 28.75 / 3.59 against the ceiling); and $\kappa(\pi)$, the mass of $\pi$-reachable
histories with zero design probability. In the simulated-log arm add the **truncation rate** at
the 0.2 weight-truncation level. Stability of $\hat\psi$ across learners and folds is part of
the report, not a footnote.

**State representation — and the policy class it defines (A19b, *not* assumed).** Histories
grow, so nuisances must be modelled on a summary. Two distinct uses, and the document now says
which is which. Used for estimation *within* the support, a summary is an approximation; used to
extrapolate *across* a positivity violation, it becomes an **identifying assumption** and must
be labelled as such.

The policy-side use is the one the earlier text left undefined. Let $\varphi_k$ be the
pre-registered frozen finite-dimensional feature map of R3 — the 87-coordinate state code,
frozen as data before any fit, with $\psi$ and every hidden-test-derived quantity excluded —
and $\mathcal F_k^O=\sigma(\varphi_k(H_k))$. Because $\mathcal F_k^O\subsetneq\sigma(H_k^A)$,
**$\varphi$ is not sufficient**, so the restricted optimum does **not** satisfy a Bellman
equation on $\varphi$-measurable value functions: backward induction on
$\hat Q_k(\varphi_k,a)$ returns $\pi^{\rm greedy}\in\Pi_{\rm cp}$, which is in general
$\ne\arg\max_{\Pi_{\rm cp}}V$. **A19b (state-representation sufficiency) is NOT assumed by the
primary route**, and T9's robustness does not repair this: exact unbiasedness is a property of
*evaluating* a fixed $\pi$, not of *optimizing*. The reported object is therefore
$\hat\pi=\arg\max_{\pi\in\Pi}\widehat V(\pi)$ over a **pre-registered finite candidate set
$\Pi$** whose count is declared in §16 (the string "$|\Pi|=100$" is forbidden; the arithmetic is
printed at $|\Pi|=8$, $L=\log(4|\Pi|/\alpha)=6.461$, and at $|\Pi|=100$, $L=8.987$, a factor
1.39), with $\pi^{\rm greedy}$ entered as one member labelled "greedy-in-$\varphi$". $\hat\pi$ is
evaluated out-of-fold on the 5 folds over the 176 families, the winner's value is re-estimated
on the held-out half, and the selection inflation is reported. The phrase "the optimal regime"
is reserved for $\arg\max_{\Pi_{\rm cp}}V$, which this design does **not** report. Where an
infinite class would require a covering-number bound, we say so and say that we do not have one
for a learned blip-threshold family.

**Two honest limits on what a learned critic buys, stated here because this is where the
summary is introduced.** (a) The product-rate condition licensing $\sqrt n$ inference is, for
text-valued histories, **unverifiable**: there is no smoothness theory for regressions on long
never-repeating text states. We flag this as open rather than claiming orthogonality delivers
what it delivers in low dimensions. (b) **T19's value-loss guarantee is numerically vacuous at
every critic precision this design can reach, and that is conceded rather than finessed.** The
blip pseudo-outcome's label noise is Bernoulli: the measured per-state Monte Carlo SE at the
frozen $n_b=3$ is **up to 0.29**, the pooled per-row noise SD of a paired binary contrast is
about 0.5, and the training set is 400 branch states $\times$ 8 classes $\times$ 3 seeds
($\approx$ 9.6k rows, 87 features). On the reviewers' own reckoning an honest
$E|\hat\gamma-\gamma|$ is **$O(0.1)$** — two to four times the entire **+0.046** of available
headroom, and larger than the true blips themselves, since repair 0.239 and degradation 0.162
imply $|\gamma|$ mostly below 0.25 and often below 0.05. "You lose at most 0.1–0.2 of value" is
not a guarantee on a scale where the total prize is 0.046. What can be non-vacuous here is a
**margin** statement, $V(\pi^\star)-V(\hat\pi)\le E\big[|\gamma|\,\mathbf 1\{|\hat\gamma-\gamma|\ge|\gamma|\}\big]$,
reported together with the **measured distribution of $|\gamma|$** and of the critic's per-state
error so a reader can see whether the bound bites. And explicitly: **a trained free-form
generator — a policy emitting messages outside the pinned library — is outside every guarantee
in this document.** By T26(b) and §12.2 its value is neither identified nor certified, T19 does
not apply to it, and "every treatment is a shippable mechanism" does not close that gap.

---

---

## 6. Policy learning and the improvement certificate

### T19 (value loss from blip error) — correct, and **numerically vacuous at achievable critic precision**; retained as a structural statement

**T19(a) — the margin form, which is the statement we make.** For a binary choke point with one-step deviation, a sign error at $h$ requires $|\hat\gamma(h)-\gamma(h)|\ge|\gamma(h)|$ and the value lost there is $|\gamma(h)|$, so

$$V(\pi^\star)-V(\hat\pi)\ \le\ E\big[|\gamma|\,\mathbf 1\{|\hat\gamma-\gamma|\ge|\gamma|\}\big].$$

**No factor of 2.** For $|\mathcal K|>2$ the per-turn loss is $|\hat Q-Q|(k^\star)+|\hat Q-Q|(\hat k)\le2\max_k|\hat Q_t-Q_t|$. Over the **$D=2$** decision points of the frozen design, $V(\pi^\star)-V(\hat\pi)\le\sum_{t\le D}E^{\pi^\star}[\Delta_t(H_t)]$ with $\Delta_t$ the per-turn sub-optimality, the expectation under the comparison regime's history law.

**T19(b) — the $L^1$ relaxation is withdrawn as a guarantee.** The chain $E[|\gamma|\mathbf 1\{\cdot\}]\le E|\hat\gamma-\gamma|$ is true and, at every precision this design can reach, uninformative. The measured inputs: branch replicates are frozen at $n_b=3$, so the per-state Monte Carlo SE of $\gamma$ is **up to 0.29** and the pooled per-row noise of a paired binary contrast is of order $0.5$; the fitted within-class template SD is $\hat v\approx0.08$; and on the 3B receiver **0.156** of task mass sits below 0.05 success and **0.334** above 0.95, so the blips that exist are concentrated on the **0.406** informative mass and are mostly small (repair 0.239, degradation 0.162 bound $|\gamma|$ well under 0.25 and often under 0.05). An honest $E|\hat\gamma-\gamma|$ on this design is of order 0.1 — two to four times the **+0.046** of measured headroom, and larger than the blips themselves. A bound of the form "you lose at most 0.1–0.2 of value" on a scale where the whole prize is 0.046 is not a guarantee, and we do not present it as one. What T19 buys is qualitative: value loss is controlled by *sign* accuracy on states where $|\gamma|$ is large, not by uniform $L^1$ accuracy, which is why the pre-registered critic validation targets are the class **ordering** of pooled $\gamma_2$, the pooled per-class $\rho$ and $\beta$, and the sign and rank correlation of $\hat\gamma_2$ against state-level Monte Carlo values — not an $L^1$ error. The measured distribution of $|\gamma|$ and of the critic's per-state error must be reported alongside T19 so the reader can see directly that the bound does not bite.

**T19(c) — the history-shift factor, restated (was: "bounded here *by design*").** The history-shift factor is bounded by $\delta^{-d}$ with $d$ the override depth of the regime whose history law is used. For $\hat\pi$ and every full-depth member of $\Pi_{\rm cp}$, $d=D=2$ and the bound is $8^2=64$; "bounded by design" is an advantage over *unbounded* ratios, not a small constant. At $n_{\rm clusters}=176$ a factor of 64 leaves **2.75 effective clusters**, so the propagation bound is a structural statement, not a basis for inference. The floor is $\delta=1/8=0.125$ over the $m_G=8$ randomized non-`STOP` arms, attained with equality; the earlier $\delta\ge0.25$ is infeasible for $m_G>4$ and is withdrawn (R1). The exponential-in-horizon blow-up is capped at 64 **only** because the frozen design has two decision points.

**T19(d) — which regret this is, and which it is not.** $\Pi_{\rm cp}$ is the class of $\mathcal F_k^O$-measurable rules on the frozen 87-coordinate feature map $\varphi_k$, valued in $\mathcal A_{\rm adm}=\{A_0,\dots,A_5\}$ (§1). Because $\mathcal F_k^O\subsetneq\sigma(H_k^A)$, $\varphi$ is not sufficient and **A19b is not assumed by the primary route**: backward induction returns $\pi^{\rm greedy}$, not $\arg\max_{\Pi_{\rm cp}}V$, and the reported object is $\hat\pi=\arg\max_{\pi\in\Pi}\widehat V(\pi)$ over the pre-registered finite candidate set whose count is declared in §16. T19 therefore bounds regret against the unrestricted optimum **only under A19b**; without it there is a further representation gap between $\arg\max_{\Pi_{\rm cp}}V$ and the unrestricted optimum which this document does **not** bound and does not claim to. The phrase "the optimal regime" is reserved for $\arg\max_{\Pi_{\rm cp}}V$, which this design does not report.

**T19(e) — where the measured headroom actually is, and what it needs.** The only measured headroom is **+4.6 pp** of final success from **oracle** stopping decisions, and stopping-only regimes sit in $\Pi_0$ with $W\equiv1$: **the deliverable the evidence supports needs no importance weights, no blip estimator at full depth, and no part of T19's propagation argument.** T19 governs the class-choice coordinate, where the measured gap against the strong baseline B4 is **+0.015 to +0.030** — smaller than the bound's own slack.

**T19(f) — scope, stated once and explicitly.** A trained *free-form* generative prompt policy, whose messages leave the pinned library, is **outside every guarantee in this document**: its treatment is not a member of $\mathcal K$, its value is neither identified (T26(b)) nor certified, T19 does not apply to it, and it voids the information-cap guarantee. Nothing in §0.2 item 4 ("every treatment is a shippable mechanism") extends any result here to it.

The propagation constant still depends on whether blips are defined under the optimal or the estimated continuation, and with an endogenous horizon the accounting is delicate: **partially OPEN**; we do not assert a clean constant.

---

### T20 (finite-sample improvement certificate) — **WITHDRAWN as a deliverable; retained as a scope statement**

We claimed a finite-sample certificate of strict improvement over the logging policy as a headline deliverable. It is **numerically vacuous on this task pool and unaffordable at any gap worth certifying**, and the baseline it certified against was an artifact of the design's own composition. A certificate is available in principle; at the honest inference unit it is uninformative, and we report a paired, family-clustered bootstrap interval instead (E0, R9).

**(a) The bound, correctly written.** With $Y-\lambda C\in[0,1]$, $\hat V_M(\pi)=n^{-1}\sum_i\min(W_i,M)(Y_i-\lambda C_i)$ and $n$ the number of **independent task clusters**, the empirical-Bernstein LCB holds with probability $\ge1-\alpha$ at

$$L=\log(4|\Pi|/\alpha)$$

— the union over the pre-registered candidate set **and** over the two one-sided bounds of (c) — giving $n\ge 8ML/\mathrm{gap}^2$. Clipping bias is sign-definite, $0\le V(\pi)-E[\hat V_M]\le E[W\mathbf 1\{W>M\}]\le E[W^2]/M$, which is the conservative direction one wants; but at the recommended $M=\delta^{-d}$ **clipping never binds and the bias is identically zero**, since $W\le\delta^{-d}$ almost surely in D1. So (a) is **not load-bearing here**, and the $E[W^2]/M$ bound — which equals 1 at $M=E[W^2]=\delta^{-d}$, twenty times the target effect — is *vacuous rather than alarming*. The clipping discussion applies only to designs where $W$ is unbounded. In particular, the simulated-log arm's "floor 0.2" is **not** a randomization floor ($8\times0.2=1.6>1$): it is a **weight-truncation level** ($\hat e$ clipped below at 0.2, so $w\le5$), it does introduce clipping bias, **A6 does not hold in that arm** (the logging policy is confounded by construction), and the truncation rate must be reported. For the prioritized pseudo-outcome $\tilde Y\in[-1,1]$, sign-definiteness and $E[\min(W,M)^2]\le M\,E[W]=M$ both fail; certify on $(\tilde Y+1)/2\in[0,1]$ and restate (a), (b) and (d) in those units.

**$\lambda$ must be pre-registered whenever a certificate is reported.** The LP-duality reading of $\lambda$ as a budget price is an economic interpretation, not a licence to select $\lambda$ on the analysis sample: a $\hat\lambda$ chosen from the estimated (value, cost) frontier makes $Y-\lambda C$ a data-dependent estimand and voids the $1-\alpha$ level. Frozen: $\lambda=0.01$ per turn, pre-registered; if more than one point of the grid $\{0,0.005,0.01,0.02\}$ is reported, the bound must hold simultaneously over the grid by a union bound, and $\lambda$ is then a hyperparameter and must be called one.

**(b) The three numbers.**

Required $n_{\rm clusters}\ \ge\ 8\,M\,\log(4|\Pi|/\alpha)/\mathrm{gap}^2$, with $M=\delta^{-d}$, $\alpha=0.05$, $|\Pi|=8$ so $L=\log(640)=6.461$ (at $|\Pi|=100$, $L=\log(8000)=8.987$; multiply every entry by 1.39). Clustering is legitimate: averaging the weighted terms within a task can only reduce the second moment, so $E[\min(W,M)^2]\le M$ survives at the cluster level.

| gap | $M=1$ ($\Pi_0$) | $M=8$ ($\Pi_1$) | $M=64$ ($\Pi_2$) |
|---|---|---|---|
| 0.015 | $2.3\times10^5$ | $1.8\times10^6$ | $1.5\times10^7$ |
| 0.030 | $5.7\times10^4$ | $4.6\times10^5$ | $3.7\times10^6$ |
| **0.046 (only measured headroom)** | $\mathbf{2.4\times10^4}$ | $\mathbf{2.0\times10^5}$ | $\mathbf{1.6\times10^6}$ |
| 0.10 | $5.2\times10^3$ | $4.1\times10^4$ | $3.3\times10^5$ |
| 0.20 | $1.3\times10^3$ | $1.0\times10^4$ | $8.3\times10^4$ |

Evaluated at this project's numbers ($n_{\rm clusters}=176$ task families; pool ceiling 230):

| | $M=1$ | $M=8$ | $M=64$ |
|---|---|---|---|
| required / available at gap 0.046 | 24,429/176 = **139×** short | 195,432/176 = **1,110×** | 1,563,455/176 = **8,884×** |
| same against the 230 ceiling | **106×** | **850×** | **6,798×** |
| **smallest certifiable gap at $n=176$** | **0.542** | **1.533** (exceeds the outcome range — impossible at any gap) | **4.336** (impossible) |
| smallest certifiable gap at $n=230$ | 0.474 | 1.341 (impossible) | 3.793 (impossible) |
| LCB half-width at $n=176$, single policy | **0.254** | 0.973 | 4.786 |
| ratio to the 0.046 gap | **5.5×** | 21× | 104× |

(The last-but-one row is the full two-term empirical-Bernstein half-width $\sqrt{2M\log(2/\alpha)/n}+7M\log(2/\alpha)/(3(n-1))$ at $\alpha=0.05$ for a *single* pre-specified policy, i.e. the most favourable reading available; the rows above it carry the union of (c).)

**Verdict, in these words.** The smallest gap this certificate can resolve on this task pool is **0.542** for an unweighted comparison against **0.046** of available headroom — a shortfall of **11.8×** — and it is *arithmetically impossible* for any weighted regime, because the required gap (1.53 at $M=8$) exceeds the range of $Y-\lambda C\in[0,1]$. A one-sided LCB that is always negative certifies nothing. For completeness, on the measured compute envelope: at 3 receiver generation calls per unit and 2,150 calls/hour, $2.4\times10^4$ units is **34 GPU-hours** and $2.0\times10^5$ units is **273 GPU-hours**, against the **9.3-hour / 20,000-call** affordability ceiling — 3.7× and 29× over. The earlier sentence "at this corrected rate the machinery costs roughly what a stratified A/B test over the $m$ arms costs" is **deleted**: a single prespecified two-arm comparison at gap 0.05 needs $\approx1.3\times10^3$ per arm and a stratified design over the arms $\approx8\times10^3$, so the honest multiple is **50–120×**. The figures $5\times10^4$ and $1.2\times10^4$ conversations, the $\delta=0.25$ / $M=16$ arithmetic they rested on, and the claim that sample complexity being *linear* in $M$ makes the machinery cheap, are all **withdrawn**. Linear in $M$ remains true; it was never the binding constraint.

**The inference unit.** $n$ above is **task clusters**, never conversations. The i.i.d. unit is the task instance (task text only); seeds, branches, turns, templates and paraphrase variants are *within*-cluster, and the 1,520 paired units ($190\times8$ root seeds sharing one saved root $O_1$) are within-cluster by construction. $n_{\rm clusters}=176$ families; ceiling $\approx230$ (3B), $\approx100$ (7B). Defining the unit as (task $\times$ seed) manufactures unlimited units from a $\approx230$-element population whose task text is the dominant variance component (per-task first-attempt success Beta(0.348, 0.230), strongly U-shaped), and it is exactly that loophole which made the old arithmetic look feasible while voiding the independence the bound needs.

**Depth entitlements (R2).** $M$ is not a free knob. $\Pi_0$ (stopping-only, $\pi_k=e_k$ on $\mathcal K_G$): $W\equiv1$, $M=1$, values obtained as **unweighted means** on recorded trajectories because the harness runs every trajectory to $T_{\max}$ and records $\psi(H_k)$ at every $k$. $\Pi_1$ (depth-1 class override): $W\le8$, $M=8$, off-policy estimable with ESS and $\hat D_2$ reported alongside every number. $\Pi_2=\Pi_{\rm cp}$ (full depth, $d=D=2$, including $\hat\pi$ from backward induction): $W\le64$, $M=64$, effective sample size **2.75 clusters** at $n=176$, so its values must be obtained by **on-policy rollout (E7) or a re-logged policy-iteration step**, and off-policy certification is explicitly disclaimed. Every claim below and every claim elsewhere that invokes this certificate must name which class it is about. Note the consequence: the deliverable the measured evidence supports — stopping decisions, +4.6 pp — lives in $\Pi_0$, needs no importance weights at all, and so needs none of the machinery T20 prices.

**(c) Why the baseline was not a baseline.** $V(e)$ is the harness's own $\delta$-floored mixture over eight arms **including** $A_6$ (DIVERT, negative control), $A_7$ (MISDIAGNOSE, placebo) and $A_8$ (PATCH, leaky). Each sits at probability $1/8$ and drags $V(e)$ down, so $V(\pi)-V(e)$ is **monotone in the number of deliberately degraded arms** and manufacturable with zero learning: one more placebo mechanically widens the certified gap. In D1 there is also no *natural* policy in the data — the harness replaced the user, so $e$ is the analyst's own randomizer — so "natural/logging policy" fused two different objects and the word **"natural" is deleted**. $V(e)$ is a diagnostic denominator only, computed on the **evaluated** stratum $\{A_0,\dots,A_5\}$ with the diagnostic arms excluded. Correspondingly, the library is partitioned into an **evaluated set** $\{A_0,\dots,A_5\}$ and a **diagnostic set** $\{A_6,A_7,A_8\}$: diagnostic arms appear in the critic's training data and in the leakage/placebo tables, and are barred from every $\pi$, from $\mathcal A_{\rm adm}$, and from every reported baseline value. The value of the policy that *would* be allowed $A_8$ is the **leakage upper anchor**, never the effect of feedback. The certificate's original selling point — "the baseline needs no weights" — survives as a technical remark about $V(e)$ being an unweighted mean; it was never a reason to treat $V(e)$ as a comparator.

**(d) What replaces it.** The primary comparison is against a **pre-registered named baseline**, with four denominators in one table:

1. single-shot no-feedback;
2. **B2**, fixed unary retry to $T_{\max}$ with no stopping rule — the zero-information arm that `positioning.md` constraint 2 makes mandatory;
3. **B4**, the strong pre-registered baseline the design is powered against (always the single class with the best marginal blip on the training folds, plus stop-iff-`visible_pass`: the fixed policy a competent engineer would ship);
4. the truncated prophet bound (P22, R21) and $V(e)$, as diagnostics only.

**The headline gap is against B4**, which strictly dominates the reviewers' demand for a fixed-string denominator: B2 breaks one already-correct answer in six (degradation 0.162 [0.105, 0.242]), so beating B2 is nearly free and proves nothing — sizing against B2 gives an apparent +0.07 to +0.12, against B4 +0.015 to +0.030. The estimator is the one actually pre-registered: the mean over the 176 task families of the family-mean paired difference on the 1,520 common-root paired units, with a paired family-clustered bootstrap (E0). Its measured precision is a half-width of **±0.019** at $R=8$ with an **MDE of 0.027** at 80% power — the only reported interval in this document that is narrower than the effect it is aimed at, and the reason the paired on-policy route is primary and the off-policy apparatus is secondary. Pairing is what makes this affordable: without the common-$O_1$ pairing the between-task variance dominates and power at $\delta=0.05$ against B2 is 0.31; with it, $\ge0.95$. No formula in T20 contains that between-task term, which is precisely why T20 prices a design nobody will run.

**(e) Never use a self-normalized estimator inside a certificate**: it is not one-sided and carries $O(1/n)$ bias. Retained as written.

---

A pleasing coincidence, now scoped: the estimability constraint $D_2(P^\pi\|P^e)\le\varepsilon$ and a PPO-style trust region are *related* objects — the radius here is **derived** from a variance bound and has a statistical meaning — but they are **not the same object**: different divergence orders, and PPO clips per-token ratios in the reverse direction. They are linked only by monotonicity of Rényi divergences. Two caveats belong with it. First, the Rényi budget prices an **unpaired** off-policy design and contains no between-task variance term, so it is not the constraint that governs the primary comparison; in this design the off-policy apparatus governs tree reuse across candidate policies and the observational extensions, while the primary comparison is the paired on-policy head-to-head of (d). Second, per R2 the budget binds at $\delta^{-d}$ with the override depth of the regime in question, so for full-depth regimes it is a statement about a factor of 64 on 176 clusters, not a tunable radius.

---

---

## 7. Endogenous horizon and prioritized outcomes

### The three faces of a short conversation
Whether a termination is **treatment** (`STOP` as an action), **censoring** (the target says continue, the user quit — informative, because the quit hazard depends on prior quality), or a **competing event** (accept vs abandon) is a property of the **estimand you choose**, not of the data. For the fixed-horizon target "continue to $K$ regardless", the IPCW functional and the dynamic-regime value are the *same* functional with the same weights; they diverge the moment the stop rule is history-dependent, and even when they agree the censoring view makes cost a constant of the design rather than a component of the objective. A protocol that says "evaluate at a fixed horizon of $T_{\max}$ turns" has silently chosen censoring, and that is almost never what one wants.

**Which of the three faces the frozen design actually has (D1) — stated before the apparatus, because the apparatus is mostly a D3 object.** In D1 the horizon is **not endogenous at all**. The harness runs every trajectory to $T_{\max}=3$ and grades $\psi(H_k)$ at every turn; there is no user, the simulated intervener never abandons (§12 item 7, T28), and $R_t$ is the harness's own randomizer. Three consequences, all of which the earlier draft of this section suppressed:

1. $e_t(\texttt{CONT}\mid H_t)=1$ at every $t<T_{\max}$ by construction, so the continuation weight of P23 is **identically one** in D1. Stopping-only regimes are exactly the class $\Pi_0$ of R2, whose value is an **unweighted mean over recorded trajectories**: $W\equiv1$, $M=1$, $n_{\rm eff}=n_{\rm clusters}=176$ families. The measured headroom (+0.046, oracle stopping, audits A3) lives entirely in this class, so **the deliverable the evidence supports needs no importance weights anywhere**.
2. The learned `STOP` rule in D1 is therefore a **protocol the system imposes**, not a model of when users stop. It is not a censoring correction and it is not a quit-hazard model. Nothing in §7 licenses reading it as one.
3. Everything that *motivates* the weighted apparatus below — P21's "satisfied users stop", informative quit hazards, the identified-set width $\kappa_0(\pi)$, and the competing-event decomposition of T25 — is a property of **observational logs, i.e. the D3 extension**, where A6 fails structurally for continuation. So the weighted machinery is unnecessary where it is valid (D1) and invalid where it is motivated (D3). **The claim "the endogenous horizon costs nothing extra" is WITHDRAWN** (R3): in D1 the horizon costs nothing because it is exogenous, not because the theory absorbed it; and the real cost of the stopping coordinate is elsewhere, in the calibration of $E[\psi(H_k)\mid\varphi_k(H_k)]$ (T8b), which is the hardest estimation problem in the design.

### P23 (early-stopping estimand, with the indicator fixed)
For $\pi=$ "continue until $\tau$, then `STOP`" with $\tau$ implementable — meaning $\tau$ is a stopping time of the **policy-observable filtration** $\mathcal F_t^O=\sigma(\varphi_t(H_t))$ of R3, which excludes $\psi$ and every hidden-test-derived quantity; a rule reading an end-of-episode oracle is not a policy but the prophet benchmark of P22:
$$V(\pi)=E\Big[\mathbf 1\{T\ge\tau\}\ \frac{\psi(H_\tau)}{\prod_{t<\tau}e_t(\texttt{CONT}\mid H_t)}\Big].$$
The indicator is $\mathbf 1\{T\ge\tau\}$ — the turn-$\tau$ stop factor marginalizes to one because $\psi(H_\tau)$ is $H_\tau^A$-measurable (T8a). Sanity check at $\tau\equiv2$: $E[\mathbf 1\{R_1=1\}Y_1/e_1(\texttt{CONT}\mid X)]=E\big[E[Y_1\mid X,\texttt{CONT}]\big]$. ✓

$\log W=\sum_{t<\tau}\log\big(1/e_t(\texttt{CONT}\mid H_t)\big)$ is the **surrogate-user surprisal of the regime's own continuation path**: variance is governed by override depth, not conversation length. Where the regime continues only where the logging process continues with probability near one, the estimator is essentially an unweighted mean.

**Scope of P23 — restricted (finding: "the apparatus is unnecessary where it is valid and invalid where it is motivated").**

* **In D1 the display above collapses.** $e_t(\texttt{CONT}\mid H_t)=1$, so $W\equiv1$ and P23 reduces to an unweighted re-read of recorded trajectories. Its one real use in D1 is exactly that: **reusing a single logged harness run to evaluate many candidate $\tau$ without re-rolling out.** The break-even is worth stating because it is large and favourable. Re-reading a recorded run for a new candidate $\tau$ costs **zero receiver calls**. A fresh on-policy rollout of one candidate $\tau$ over the paired design costs up to $190\times8\times3=4{,}560$ receiver calls $\approx2.1$ h at 2,150 calls/hour, so **at most four** such rollouts fit inside the 20,000-call / 9.3-hour affordability ceiling. Re-reading is free and unweighted; rollout is the scarce resource. This, not importance weighting, is what P23 buys in the primary design.
* **In D3 the display is the substantive object**, and there $W$ is a genuine weight whose variance is bounded by $\delta^{-d}$ with $d$ the override depth of the continuation coordinate (R2), not by conversation length. Since the frozen design has $D=2$ decision points, the worst case is $\delta^{-2}=64$, which at $n_{\rm clusters}=176$ leaves **2.75 effective clusters** — a structural statement, not a basis for inference. That is why the primary route is on-policy paired rollout (E0/E7, R9) and not off-policy re-weighting.
* P23 makes **no** claim that the stopping coordinate is free. Under R2 the stopping coordinate contributes no weight in D1; under T8b its *prediction* problem is unsolved and is the binding difficulty.

### P21 (the structural non-identification)
**Scope: this is a D3 result. It does not describe D1**, where continuation is exogenous by construction (above).

In logs, the natural continuation probability *decreases in current quality*: satisfied users stop. So the histories where "would one more turn have helped?" is interesting are exactly the histories with no support. Late-continuation regimes are therefore **not point-identified** from logs. Three corrections to the earlier statement of the width, all conceded here rather than argued away:

1. **The width is conditional on exchangeability holding for the continuation coordinate.** Under A7 for the binary continuation coordinate, the sharp identified set for $V(\pi)=E[Y^\pi]$ has width $\kappa_0(\pi)=P^\pi(\exists t<\tau: e_t(\texttt{CONT}\mid H_t)=0)$, sharpened to one-sided under free disposal.
2. **$\kappa_0$ is a lower bound on the true ambiguity, not the ambiguity.** The very mechanism P21 invokes to motivate the support failure — quality-dependent quitting — is *simultaneously* an A7 violation whenever the user's perceived quality exceeds what $H_t$ records, and this document insists elsewhere that the recorded signal is a noisy channel rather than the user's private assessment. On the *supported* histories the estimator is then not consistent for the regime value either, and the true identified set is strictly wider than $\kappa_0$ in a way **no computation of $\kappa_0$ will reveal**. §10 lists A7 for D3 as assumed and untestable and §15 item 8 lists the corresponding calibration as OPEN; those are the governing statements. Accordingly the earlier word **"sharp" is withdrawn for the unconditional claim** and retained only in the form "sharp given A7 for the continuation coordinate".
3. **The width is not $\kappa_0$ for the priced objective.** For $E[Y^\pi-\lambda C^\pi]$ the unsupported event carries extra cost as well as extra outcome, so the width is $\kappa_0(\pi)\cdot\mathrm{range}(Y-\lambda C)$ with $C$ bounded by the turn cap — at $T_{\max}=3$ and $\lambda=0.01$ per turn the range is bounded, but it is not 1 and it must be written out rather than inherited from the unpriced case.

This is a design verdict: randomize continuation, or branch. And a violated floor is **silent** — the estimator converges to the value of a *different* regime (the one that stops wherever the natural user would) unless $\kappa(\pi)$ is computed and reported as a headline number. Correspondingly, §0.4's Ext-E row should read "**the weakest positivity requirement**", not "the strongest possible identification position": the exchangeability burden is unchanged and item 2 above makes it heavier, not lighter.

### P22 (weight-free prophet benchmark, corrected)
For the **truncated** rule $\tau'=\min(\tau,T)$,
$$\sup_{\text{implementable }\tau,\ \tau\le T}E\big[\psi(H_{\tau'})\big]\ \le\ E\big[\max_{t\le T}\psi(H_t)\big],$$
and both sides are ordinary unweighted means of observed quantities, identified **under A21 (artifact-valued outcome, no decay) and the T8a stop-arm structure** ($Y(A_0\text{ at }k)=\psi(H_k)$ exactly, so stopping early does not change the measured quantity) — *not* "by consistency alone with no assumptions". The **unrestricted** claim over all implementable rules is false: with $e_1(\texttt{CONT}\mid X)=0.01$, $\psi(H_1)=0$, $\psi(H_2)=1$, the rule "always continue then stop" has value $1$ against a bound of $0.01$.

**Reporting device — the unrestricted form is WITHDRAWN and replaced in place.** The earlier device ("at most $X$ points of quality are recoverable by *any implementable stopping rule*") re-asserted exactly the unrestricted claim the counterexample above withdraws, and it did so for the interesting case — continuing where the natural user stopped. The only form that may be reported is:

> "At most $X$ points of quality are recoverable by any stopping rule that **never continues past the natural horizon** — i.e. that only shortens the conversation, never extends it — and our learned rule recovers $Y$ of them."

One sentence must accompany it: **continuation-extending regimes are not bounded by this benchmark**, and their values require P23's weights (in D3) or fresh rollout (in D1). In D1, where the harness forces continuation to $T_{\max}$, "the natural horizon" is $T_{\max}$ itself and the restriction is not binding — which is precisely why the device is usable here and would not be usable on logs.

**Magnitude, measured.** On the sibling project's completed 4,488-episode log, the gap this benchmark bounds is **+0.046** (observed final success 0.691 against 0.737 under oracle stopping decisions, audits A3), under that audit's own optimistic assumptions (prematurely stopped failures assumed to repair at 0.239, and oracle stopping unavailable to any real rule). So $X\approx4.6$ points and the honest headline is the **pair** (oracle value, $\hat p$-rule value), never the oracle value alone (T8b, mandatory reporting). Against measured precision — paired family-clustered bootstrap half-width $\pm0.019$ at $R=8$, MDE 0.027 — a benchmark gap of 0.046 is resolvable by the paired design and is **not** resolvable by any certificate (T20, withdrawn; the smallest gap the certificate can resolve at $n_{\rm clusters}=176$ is 0.542, a shortfall of $11.8\times$). P22 is therefore a **diagnostic denominator** in T20(d), alongside $V(e)$, and not a guarantee.

**Deleted, with the reason stated in place.** The invocation of "the i.i.d. prophet constant $\approx0.745$" is **deleted**. That constant is for independent draws from a known distribution; $\psi(H_1),\dots,\psi(H_T)$ is a dependent, non-stationary adapted process with a design-controlled horizon, and no constant-factor prophet guarantee holds for dependent sequences (the independent non-identical case already degrades to $1/2$). It was decorative, not conservative. If a competitive ratio is wanted for this process it must be computed in the simulator for the actual dependent $\psi$ sequence; we do not have one and do not claim one.

**On the measurement channel.** The earlier instruction "compute the benchmark on the independent measurement channel, or it inherits P24" is superseded by R3. With a **programmatic** primary outcome $\psi$ the benchmark carries no judge noise, $\sigma=0$ for the primary number, and P24(ii) does not bite on it; the operative requirement is instead the $\varphi$-exclusion assertion of A11(d) — the *policy* must not see $\psi$, while the *benchmark* is an analyst-side ($H_t^A$-measurable) quantity and is allowed to. If the benchmark is ever computed on a judge channel for a secondary outcome, T8b applies and R20's inflation term must be carried.

### T13 / T14 (prioritized outcome) — **DEMOTED to a secondary reporting device; retained with $G_0$ frozen**
We presented the prioritized (win-probability) objective as a primary route that removes the need for a cost price $\lambda$. It is demoted for two independent reasons — the functional $G_0$ is an estimated nuisance unless it is frozen off-sample, and on *this* project's outcome the construction is close to degenerate — and it is retained only as a secondary reporting device, under the freeze described below. **The primary objective is the priced scalar $E[Y^\pi-\lambda C^\pi]$ at the pre-registered $\lambda=0.01$ per turn, with degradation reported separately** as audits A3 requires.

Coarsen $Y$ by $\eta_1>0$, then $C$ by $\eta_2$, then $N$, and compare lexicographically (A17). With $u$ representing the preorder and $G_0$ the mid-rank CDF of $u(Z)$ under a reference $\pi_0$,
$$\theta_{\rm NB}(\pi,\pi_0)=P(\text{win})-P(\text{loss})=E\big[\tilde Y^\pi\big],\qquad \tilde Y=2G_0(u(Z))-1\in[-1,1].$$

**The $G_0$ problem, and the decision (R6).** "Prespecified $\pi_0$" pins the *regime*, not the *functional*: $G_0$ is the mid-rank CDF of $u(Z^{\pi_0})$, an unknown feature of a counterfactual law that must itself be identified and estimated. With $\hat G_0$ plugged in, $\tilde Y_i$ is not a fixed function of $Z_i$, the $\tilde Y_i$ are dependent across units, the martingale-difference argument behind T9 fails, $Q_k(\cdot,\texttt{STOP})$ requires $G_0$ and is no longer known even in the T8a sense, and T9(i)'s exact unbiasedness is lost — which is exactly what the two-term influence function displayed below says. The decision is option (i), and it is free:

> With $G_0$ **frozen on an independent pre-registered reference sample** — here the sibling project's completed 4,488-episode log (`ykzeng-yale/DTR-AgentEvals`, identical `tasks_sha256`, verified not assumed; same machine, inference server and quantizations), hashed before any outcome of this run is examined — $\tilde Y$ is a fixed known measurable transform of the unit's own terminal record, and T8a and T9 apply verbatim with $Y$ replaced by $\tilde Y$; the stop arm's value remains known **in the T8a (analyst) sense**, because $Y_{k-1}$, accrued cost and turn count are all components of $H_k^A$. Were $G_0$ instead estimated on the analysis sample, none of that would hold: $\tilde Y$ would carry an outcome-law nuisance, the units would be dependent, the two-term influence function $\varphi_\pi[G_0^-]+\varphi_{\pi_0}[\bar G_\pi]$ displayed below would be the correct expansion, exact unbiasedness would be replaced by double robustness with a second-order remainder, and $Q_k(\cdot,\texttt{STOP})$ would become an estimated nuisance. The freeze is what buys the verbatim reuse, and its price is that the win probability is reference-dependent on a *frozen* reference.

The freeze costs zero GPU time and zero clusters. Its price must be stated wherever the number is reported: **the reported win probability is against the frozen sibling log, and $\pi^\star$ is reference-dependent**; the sibling's prompt format and grading are its own, so $G_0$ is a reference from a related but not identical regime. That is acceptable only because $G_0$'s sole job is to be a fixed monotone transform. Option (ii) — $\hat G_0$ as a cross-fitted nuisance with the two-term EIF and a bilinear remainder in $(\hat G_0-G_0,\hat Q-Q)$ — is **not used confirmatorily**; it is retained below as what *would* be required. $G_0$ is added to the §15 item 6 OPEN list, which previously flagged only $u$ and $\eta$.

EIF of $\theta=P(u(Z^\pi)>u(Z^{\pi_0}))$ **under option (ii), i.e. when $G_0$ is estimated on the analysis sample**: $\varphi_\pi[G_0^-]+\varphi_{\pi_0}[\bar G_\pi]$, each centered, where $\varphi_\pi[h]$ is the sequential-DR influence function for $E[h(u(Z^\pi))]$; both arms are identified from the *same* observed law, so the two pieces add inside one influence function. A two-term EIF **is** the statement that T9 does not apply verbatim; under the freeze the second term is absent, and that is the whole content of the freeze.

**Why demoted even with the freeze — the degeneracy on this outcome.** $Y$ is a binary hidden-test verdict, $N\in\{1,2,3\}$ at $T_{\max}=3$, and cost is a monotone function of $N$ up to token noise. With tolerances $\eta$ the ordered quotient has about **six cells**, the tie mass is the majority of pairs (two failures at the same turn count tie exactly), the variance of the win-probability estimand is dominated by tie handling, and the transform **shrinks** an effect already at 0.015–0.030 (the headline gap against B4) rather than stabilising it. The prioritized form here is a coarse monotone re-expression of a $2\times3$ table. Therefore: **T13 is scoped to outcomes with a continuous or many-valued primary component**; for a binary primary outcome the prioritized form reduces to the $(Y,N)$ table, **the tie mass must be reported**, and the priced scalar stays primary.

**And the motivation was hollow, so it is withdrawn.** "Scale-free in $Y,C,N$ (no hand-tuned $\lambda$)" is withdrawn as a selling point: $\lambda$ is not hand-tuned here. It is **pre-registered at 0.01 per turn**, read off the measured budget (`docs/measured_calibration.md`), with the grid $\{0,0.005,0.01,0.02\}$ available and a **union bound over the grid** required if more than one value is reported. The LP-duality reading of $\lambda$ as a budget price (T8) is a **post-hoc economic interpretation, not a licence to select $\lambda$ on the analysis sample**: the dual multiplier is a functional of $P$, determined by the supporting hyperplane of the attainable (value, cost) frontier, so a $\hat\lambda$ chosen after seeing the data makes every downstream "fixed bounded outcome" statement data-dependent — a one-sided certificate at $\hat\lambda$ is not valid at the stated level, and T9's EIF would omit $\hat\lambda$'s contribution. Pre-registration, not duality, is what makes $Y-\lambda C$ a fixed outcome. This is the same double-dipping failure as $\hat G_0$, one level up, and it is resolved the same way: freeze it before outcomes are examined.

The remaining bonus survives: $\tilde Y$ is bounded, which helps variance and cross-fitting. One boundedness caveat must travel with it: $\tilde Y\in[-1,1]$ is **not** non-negative, so T20(a)'s sign-definite clipping bias and the bound $E[\min(W,M)^2]\le M$ do not hold on $[-1,1]$. Any certificate on the prioritized objective must be computed on $(\tilde Y+1)/2\in[0,1]$. (T20 is withdrawn as a deliverable in any case; this is stated so the withdrawal is not doing the work that a correct restatement should.)

Three corrections carried. **Ties.** Under a lexicographic hierarchy with tolerances, ties have positive probability, so $\theta(\pi,\pi_0)+\theta(\pi_0,\pi)\ne1$; use the net-benefit form (or explicit half-credit), otherwise a "tournament" is ill-defined. On this outcome the tie mass is not a nuisance at the margin but the dominant cell mass, and it is a reported quantity. **Moments.** For the doubly-weighted $U$-statistic, $E[(W_iW_j)^2]=E[W^2]^2$ by independence of the pair, so **second** moments suffice for a Hájek-projection CLT; no fourth-moment condition. Note that the pair independence is at the level of the **task cluster** (R9), not the (task, seed) record. **Non-transitivity.** Pairwise win probabilities need not be transitive, so "the optimal prioritized regime" requires a prespecified reference, exactly as a clinical win ratio is always versus control; here the reference is the frozen sibling log. The resulting $\pi^\star$ is reference-dependent, and that is a genuine conceptual cost to be reported, not hidden. **OPEN:** pathwise differentiability when $u$, $\eta$ or (under option (ii)) $G_0$ are estimated — we believe it fails, which makes prespecification and the freeze necessary rather than merely good practice; and existence of a Condorcet winner among blip-threshold rules.

### P12 (matched versus marginal win probabilities)
Between-unit prioritized comparisons — the **classical** Finkelstein–Schoenfeld / win-ratio estimand, formed across independent units in different arms — are functionals of the arm marginals and **are identified** and coupling-invariant. Within-unit win probabilities, individual-effect variances, and every other coupling functional are **not** determined by the marginals.

**Closed form reinstated (correcting an over-correction).** Because $c(v,w)=\mathbf 1\{v>w\}$ is neither supermodular nor submodular — checked both ways: $v=1,v'=3,w=0,w'=2$ breaks submodularity; $v=0,v'=1,w=0,w'=1$ breaks supermodularity — the extrema are **not** attained at the comonotone/antimonotone couplings, so the **naive Fréchet–Hoeffding substitution remains withdrawn**. But the further conclusion that no closed form exists was too strong and is itself withdrawn. Since T13 reduces the lexicographic comparison to a **scalar** $u(Z)$, and $\mathbf 1\{v>w\}=\mathbf 1\{v-w>0\}$, the sharp bounds are the classical Makarov (1981) / Rüschendorf (1982) bounds on the distribution of a difference under fixed marginals — closed-form, attained at explicitly constructible shuffle couplings:
$$\sup_{\text{couplings}}P(V>W)=1-\sup_t\big\{F_V(t)-F_W(t)\big\}^+,\qquad \inf_{\text{couplings}}P(V>W)=\sup_t\big\{F_W(t)-F_V(t)\big\}^+,$$
up to one-sided limits, with $V=u(Z^\pi)$, $W=u(Z^{\pi_0})$ and $F_V,F_W$ the two estimated marginal CDFs of $u$. Those references are already in §13(a). So: **report the Makarov–Rüschendorf interval** for the scalar comparison, note that the maximizer is a shuffle rather than the comonotone coupling, and reserve the optimal-transport LP for the **multi-level, vector-valued, non-scalarizable** lexicographic comparison, which is the only part §15 item 6 should keep as open. The blanket "LP-only" statement is withdrawn.

**Couplings and the paired design.** Sharing a decoder seed across text branches manufactures a coupling with no real-world referent: the RNG stream is consumed in an action-dependent way, so once prompts diverge the induced dependence is implementation-defined. This does **not** condemn the paired common-random-number design (R9), and the distinction must be stated precisely rather than left to the reader. The 1,520 paired units ($190$ tasks $\times\ 8$ root seeds sharing one saved root $O_1$) are a **variance-reduction device for a between-unit marginal contrast**, and they are *within*-cluster relative to the 176 task families that carry the i.i.d. structure. Pairing removes between-task variance from the contrast; it does **not** license reading a within-unit win probability, an individual-effect variance, or any other coupling functional off the shared seed. **Reporting obligation:** any matched win ratio must declare its coupling and show sensitivity across couplings (now via the closed-form interval above, not an LP); reporting a within-unit quantity while computing a between-unit one (or vice versa) is a substantive error.

### T25 (competing risks, separable effects, truncation)
**Scope: T25 is a D3 extension.** In D1 there is no abandonment — the simulated intervener never quits (§12 item 7, T28) — so (a)–(c) below are *vacuous in the primary design* and must not be advertised as things the frozen experiment delivers.

(a) The **total effect** on the cumulative incidence of acceptance by turn $k$ is identified with no intervention on abandonment. (b) A controlled direct effect ("eliminate abandonment") needs abandonment's own exchangeability and its own floor. (c) Unlike mortality, the competing event here is **behavioral and intervenable** — a never-quitting proxy annotator realizes the eliminating intervention — which defuses the standard objection but changes the target population.

(d) **Separable effects: interface construction discharges the receiver-side condition only.** Decompose the turn action into a component $A^Y$ rendered into the receiver's context and a component $A^D$ reaching the user's continuation decision (progress indicator, rendering, displayed cost meter, displayed confidence, surface tone). What code buys, and what it does not:

* **Discharged by construction (receiver side).** That $A^D$ does not enter the receiver's input $M$ directly is verifiable by inspecting the rendered prompt, and under A5's input-provenance hash (§16 item 1(a)) it is a byte-exact check rather than a statistical test. This half is genuinely a software guarantee.
* **Assumed, and must be numbered before any confirmatory use — condition (ISO-U), user-kernel dismissibility.** That $A^D$ affects $Y$ *only* through the continuation event, and that $A^Y$ affects the continuation decision only through $O_t$, is a claim about the **user's behavioural kernel** and is *false in the obvious implementation*: a displayed cost meter, confidence indicator or progress bar plausibly changes what the user writes conditional on continuing, hence $H_{t+1}$, hence $Y$. With a simulated user the problem is architectural, not incidental: $A^D$ is inserted into the simulated user's prompt, and a language model conditioning on its whole context will in general alter both its stop head and its message content, so "reaching only the user's continuation decision" holds **only** if the simulated user is split into two calls with disjoint contexts — at which point the estimand is relative to that artificial split rather than to "the user", and that must be said in the estimand's own statement. (ISO-U) is therefore an **assumption**, not a construction, and it must be registered in the §2 table before T25(d) is used confirmatorily.
* **The falsification test that is actually available.** In the harness, branch on $A^D$ at fixed $A^Y$ and test whether the conditional distribution of the next message given continuation is invariant. This is a real test, and it must be **priced before it is scheduled**: it is an additional branch axis against the 20,000-receiver-call / 9.3-hour affordability ceiling, and no budget for it is claimed here.
* **Withdrawn string.** "In medicine the decomposition is hypothetical; here it is code" is withdrawn as written, because it asserted for the whole decomposition what holds only for the receiver-side half. Restricted form: *interface construction makes the receiver-side isolation condition checkable in code; the user-side dismissibility condition (ISO-U) is assumed here exactly as it is in medicine, and only its falsification test is cheaper.*

(e) **Truncation by death is a property of the outcome definition**, not of the endogenous horizon: artifact-valued outcomes under A21 have no problem; session-valued outcomes are undefined on abandonment and not identified by any weighting (options: a composite conflating quality with persistence; a principal-stratum effect with Zhang–Rubin bounds; separable effects). Choose artifact-valued — which the frozen design does, and which is what makes P22's unweighted sandwich available at all.

### Fair comparison across horizons
Under A21, "as-delivered" and "fixed measurement point with carry-forward" coincide, so comparing $E[Y^{\rm last,\pi}]$ across regimes *is* a comparison at a common point, with $(Y,C,N)$ all measured there. Without A21 the two differ by a decay term and **which is the target is a substantive question** that must be stated. Either fix the budget (and price cost with the pre-registered $\lambda=0.01$ per turn, **not** with a $\hat\lambda$ read off the analysis sample — see T13 above) or fix the measurement point; never compare on an unpriced quality outcome. At $T_{\max}=3$, $D=2$ and $N\in\{1,2,3\}$ the horizon range being compared over is small, which is what keeps the comparison tractable and also what makes the prioritized re-expression degenerate.

Two further obligations. First, **a mean-outcome comparison across horizons hides degradation**: iteration destroys 0.162 [0.105, 0.242] of already-correct answers (audits A3), so the first-correct-then-wrong stratum is a **separately reported outcome**, not a component of an average, in every horizon comparison. Second, a category error to avoid: since $N$ and $C$ are *chosen by the regime*, "our regime causes fewer turns" is not an estimated effect — putting $N$ and $C$ inside the value is legitimate, reporting them as effects is not.

---

---

## 8. Measurement threats

**Scope of this section, corrected.** The frozen design's **primary** outcome is programmatic: $Y=\psi(\text{artifact})$, the binary hidden-test verdict, graded at every turn, with verifier determinism *measured* rather than assumed (1,954 replicate verifications of 597 repeated `(task_uid, sha256(final_code))` pairs, 0 disagreements). Therefore $\sigma=0$ for every primary number, and **the judge apparatus of P15 governs no primary quantity in this design.** What has teeth is narrower than the draft implied, and it is the following four things: (1) the information-set separation between the policy-observable history $\varphi_k(H_k)$ and the analyst history $H_k^A$ (R3, A11(d)); (2) selection/evaluation splitting, both per state (§5 P11) and over the pre-registered candidate set $\Pi$ (R16); (3) a *measured* horizon-drift coefficient $\beta$ for any scorer that is ever used, replacing the powerless calibration test the draft proposed; and (4) leakage, length and position, which are **descendants of the randomized treatment** and are therefore handled in the action space (R5), not by conditioning. P15 is retained in full, renumbering nothing, but it is now explicitly **secondary-outcome-only**: it applies if and only if a judge is used for a secondary outcome under A11(b), and then together with the inflation term of R20 as made concrete in the P24(ii) correction below.

### P15 (judge-based outcomes — applies to SECONDARY outcomes only, A11(b))

(a) **Differential** judge error $\beta(H,A)$ biases the estimand by exactly $E^\pi[\beta]$ and **no weighting scheme repairs it**, because importance sampling is linear in the outcome; randomization protects against confounding, not against outcome artifacts aligned with treatment. (b) **Non-differential** noise is amplified by exactly $E[W^2]$, so cheap noisy judges are far more expensive off-policy than on-policy, and the optimal allocation of replicates is $r_i\propto W_i$. (c) For tilt-type estimands the bias is $E[\mathrm{Cov}(\beta,\phi_t\mid H_t)]$, i.e. judge error contaminates the effect only insofar as its systematic component covaries with the treated feature *within history strata*, giving a one-parameter sensitivity analysis in $\rho$ with bound $\rho\sigma_b\sum_tE[\mathrm{sd}(\phi_t\mid H_t)]$ — a statement about the observational tilt extension (D3), not about D1. (d) **PPI:** $\hat\gamma_{\rm PPI}=\hat\gamma(Y_J)+|V|^{-1}\sum_{i\in V}w_i(Y_i-Y_{J,i})$ with $w_i$ the influence weights evaluated at the *same* nuisances, cross-fitted so $w_i$ is independent of the validation draw. (e) **The judge is itself resettable**, so its style sensitivity is the estimand of an auxiliary branching experiment: among outputs with identical programmatic content signature, execute content-preserving stylistic rewrites and record the score shift. Honest asymmetry: this bounds only the manipulated dimensions, is a **lower** bound on total differential bias, must widen a confidence interval rather than adjust a point estimate, and is unavailable exactly where judges are most needed (open-ended tasks). (f) **Show the judge only the final artifact, never the transcript** — this cuts the direct wording$\to$score path but not the mediated path through the output's own style, so blinding is necessary and not sufficient. Style-only interventions are exactly where judge bias is maximal, so a "be concise" arm scored by a transcript-reading judge is close to worthless. Cost is the happy exception: it is measured, not modelled.

**Three corrections to P15, all forced.**

1. **(b) recomputed at the feasible floor (R1, R2).** The draft's amplification factor was quoted at an infeasible floor. With $m_G=8$ randomized non-`STOP` arms at $e=1/8$, the feasible floor is $\delta=1/8=0.125$ and $E[W^2]\le\delta^{-d}$: **$W\equiv1$ and no amplification at all for stopping-only regimes $\Pi_0$; $E[W^2]\le8$ at depth 1 ($\Pi_1$); $E[W^2]\le64$ at full depth $d=D=2$ ($\Pi_2=\Pi_{\rm cp}$).** In cluster units, $n_{\rm eff}\ge n_{\rm clusters}\delta^{d}$ gives **176 / 22 / 2.75** clusters at $d=0,1,2$ from $n_{\rm clusters}=176$ task families. A noisy secondary judge outcome evaluated off-policy at full depth therefore sits on under three effective clusters and is not reportable; noisy judge outcomes are admissible only for $\Pi_0$-type comparisons, where $W\equiv1$ and the amplification vanishes. The figure 16 that appeared here (at $\delta\ge0.25$, $d\le2$) is **withdrawn as computed at an unattainable floor**: a uniform floor over $m_G$ arms requires $m_G\delta\le1$, so $\delta\ge0.25$ is feasible only for $m_G\le4$.
2. **(d) the two variance terms are not independent as displayed.** $\mathrm{Var}(\varphi(Y_J))/n+\mathrm{Var}(w\varepsilon)/|V|$ holds only when the validation set $V$ is drawn **separately** from the $n$ units carrying the judge-based estimate. Under the arm-by-arm within-run validation the draft assumed, $V\subset$ the $n$, so there is a covariance between $\varphi(Y_J)$ on $V$ and the correction, plus a finite-population factor of order $(1-|V|/n)$; cross-fitting $w_i$ removes the nuisance-induced dependence but **not the overlap**. Decision: $V$ is a **pre-registered disjoint fold of task families**, drawn disjointly from the estimation sample, and this is stated wherever PPI is reported; if for any reason $V$ is not disjoint, the covariance term and the $(1-|V|/n)$ factor must be carried explicitly. This costs nothing here, because the programmatic label $\psi$ exists for every unit, so "validation" is a relabelling of folds and not extra GPU.
3. **(e) and (f) are unpriced and must not be assumed into the budget.** The style-rewrite auxiliary experiment of (e) is a secondary-outcome diagnostic; no receiver-call budget is reserved for it in the frozen design, and if it is run it must be priced against the affordability ceiling of **20,000 receiver calls $\approx$ 9.3 h** before it is frozen, not after. And (f) is in direct tension with the calibration test the draft demanded — see the replaced requirements paragraph below.

### P24 (the pathologies created by endogenous stopping) — rescoped, with (ii) rewritten

(i) For a first-crossing rule on a **noisy** signal, the bias $E[\varepsilon_\tau]$ is strictly positive **on the crossing event**; the unconditional sign is not guaranteed when the rule can be forced to the cap, where the last error is truncated from above. **This is the bias that does not average away**, because the same realized scoring noise both triggers the stop and scores the outcome. **Scope, stated plainly: it is zero for the primary number of this design.** $\psi$ is deterministic given the artifact, so $\varepsilon\equiv0$ in the scored outcome; and by A11(d) the stopping signal is $\varphi$-measurable while $\varphi$ excludes $\psi$ and every hidden-test-derived quantity, so the shared-noise channel that generates (i) is absent by construction rather than by assumption. P24(i) is retained as the statement that applies to any judge-derived secondary outcome, where $\varepsilon\ne0$ and the channel is shared.

(ii) **REWRITTEN; the draft's magnitude claim is WITHDRAWN as overstated by about two orders of magnitude.** The draft wrote the selection inflation as $\Theta(\sigma\sqrt{\log\bar K})$, never defined $\sigma$, and asserted that at "realistic judge noise and $\bar K\approx5$" it is "comparable to any real effect this project hopes to report". Two defects: the rate omits the replicate/sample factor that §5 P11 correctly retains, and $\bar K\approx5$ is not this design's horizon — $T_{\max}=3$, so there are $\bar K=3$ candidate stopping times and $D=2$ decision points. Corrected statement: for a rule selected by maximizing an estimated value, the inflation is
$$\Theta\!\Big(\sigma\sqrt{\tfrac{\log\bar K}{n_h}}\Big),\qquad n_h=\text{the number of independent scorings per decision node,}$$
with $n_h=1$ for a per-trajectory or per-state argmax and $n_h=n_{\rm clusters}$ for a global rule selected across units. Both cases, at this project's measured numbers:

| case | $\sigma$ | inflation | comparison |
|---|---|---|---|
| $n_h=1$: per-state argmax over branch means | per-state Monte Carlo SE up to **0.29** at the frozen $n_b=3$ | $0.29\sqrt{2\log 3}\approx\mathbf{0.43}$ | $\approx9\times$ the **+0.046** of measured headroom; **this is the case where the "comparable to real effects" warning is kept**, and it is branch-selection noise (§5 P11), not judge noise |
| $n_h=n_{\rm clusters}=176$: global rule chosen over the pre-registered $\Pi$ | SE of the value estimate $\approx0.019/1.96\approx\mathbf{0.0097}$, from the measured paired family-clustered bootstrap half-width $\pm0.019$ at $R=8$ | bound $0.0097\sqrt{2\log 8}\approx\mathbf{0.020}$; actual $\approx1.43\sigma\approx\mathbf{0.014}$ for 8 i.i.d. Gaussian errors | below the measured **MDE 0.027** and 2.3–3.3$\times$ below the 0.046 gap; **removed** by the pre-registered selection/evaluation split, the winner's value being re-estimated on the held-out half (R16) |

So: selection inflation **vanishes in $n$** and is a sample-size-and-splitting problem; P24(i)'s within-unit bias **does not** and is an information-set problem. The draft conflated them and therefore misdirected its own remedy. Two further consequences, both stated where they bite: the independent-channel requirement is **not** justified by (ii) — it was justified by the differential-bias argument of P15(a) and by (iii) — and, with a programmatic primary outcome, $\sigma=0$ and the judge-noise version of (ii) **does not bite on the primary number at all** (R3). What survives for the primary number is exclusively the $n_h=1$ branch-selection case, which is why branch ground truth is usable **pooled or on strata, never per state** (§5 P11), and the $n_h=176$ case, which is handled by the split.

(iii) A scorer whose score rises by $\beta$ per turn shifts the estimated blip by $-\beta$, moving the effective threshold on true marginal quality gain from $\lambda$ to $\lambda-\beta$; if $\beta\ge\lambda$ the estimated optimal rule never stops before the cap. Because horizon is the treatment coordinate here, the best-documented LLM-judge pathology (length/verbosity bias) maps one-to-one onto bias in the estimand. **Two things the draft left implicit.** First, for the primary number $\beta=0$ by construction: $\psi$ is a function of the final artifact alone, is horizon-invariant in the literal sense, and is verifier-deterministic as measured. Second, the pre-registered price is $\lambda=\mathbf{0.01}$ **per turn**, so on a scorer measured on the same $[0,1]$ scale as $\psi$ a drift of one point of success probability per turn already drives the effective threshold to zero and inverts the stopping rule. That margin is the quantitative reason **no judge may supply the primary outcome or the stopping signal in this design** — not a preference, an arithmetic incompatibility between $\lambda=0.01$ and any realistic $\beta$.

**Requirements, not recommendations — REPLACED (R3).** The draft's three requirements were: programmatic outcomes primary; two prespecified independent measurement channels, one for stopping and one for scoring; and a horizon-invariance calibration test scoring one frozen artifact presented at two different conversation lengths. The first stands; the second and third are withdrawn and replaced, for reasons that must be recorded here rather than elsewhere.

1. **Programmatic outcomes primary — retained, and strengthened to a precondition.** $Y=\psi$ is the binary hidden-test verdict under the audited visible/hidden assertion split, graded at every turn, verifier-deterministic as measured. Every horizon and stopping result in this document is conditional on this; none of them is claimed for a judge-derived outcome.
2. **WITHDRAWN: "two prespecified independent measurement channels, one for stopping and one for scoring."** This could not be held simultaneously with T8's "$Q_t(H_t,\texttt{STOP})$ is known": read as a shared channel, T8 held and this requirement was violated and P24(ii)'s optimism was manufactured; read as two instruments, this requirement held and the advertised stop-arm asymmetry evaporated. It is replaced by an **information-set restriction** (A11(d), R3): the stopping signal is $\varphi$-measurable, $\varphi$ excludes $\psi$ and every hidden-test-derived quantity, `signature_example` is stripped from every record $\varphi$ can reach, and the feature builder **raises** on any of `{test_list, test, challenge_test_list, reference, signature_example, V, Y}`, with a test asserting the raise for each forbidden key. $\mathcal F_k^O:=\sigma(\varphi_k(H_k))\subsetneq\sigma(H_k^A)$: a quantity may be available to the *estimator* ($H_k^A$, T8a) and unavailable to the *policy* ($\mathcal F_k^O$, T8b), and which of the two is meant is stated every time. The honest cost of this restriction is measured and belongs here: the visible verdict is **one bit** and is **absent on 20.8% of the informative pool** (50/240), and the sibling loop's own self-check stopped on **50.4%** [0.479, 0.528] of all failures, so $E[\psi\mid\varphi]$ is the hardest estimation problem in the design (T8b) and the **+4.6 pp** of headroom is the value of the **oracle** $V$, not of any $\varphi$-measurable rule. Mandatory reporting: the oracle-$V$ minus $\hat p$-rule value gap as a headline **pair**, never the oracle value alone.
3. **WITHDRAWN: the horizon-invariance calibration test as stated** ("score one frozen artifact presented as a 1-turn and as a longer conversation"). Under P15(f) the judge's input is the artifact alone, so the two presentations feed the judge **byte-identical input**: the test passes with probability one and has exactly **zero power**. It also quoted a horizon this design does not have. The channel that actually produces the (iii) threshold shift is the mediated one P15(f) explicitly does *not* cut: longer conversations produce stylistically different artifacts (longer, more hedged, more commented) and a judge rewards those. **Replacement, using machinery the document already has:** within strata of identical programmatic content signature, regress the judge score on artifact length and style features and estimate $\beta$ **directly**; report the induced threshold shift $\beta/\lambda$ in cost units as a mandatory number; and report the **artifact length distribution by horizon arm**, since a length imbalance across arms is by itself sufficient to generate the entire horizon result. A11(c)'s horizon-invariant scorer is thereby a *measured* coefficient, not an assumption. For the primary programmatic outcome this test is vacuous in the good sense ($\beta=0$ by construction), and it is mandatory for any judge-scored secondary outcome.
4. **Selection/evaluation splitting is a requirement, not a recommendation**, in both the forms P24(ii) now distinguishes: per state (§5 P11, $n_h=1$, inflation of order 0.4 at $n_b=3$) and over the candidate set (R16, $n_h=176$, inflation $\approx0.014$–$0.020$, removed by re-estimating the winner on the held-out half).

**OPEN, restated.** The draft's open problem was "debiasing in the realistic intermediate case where the two channels are correlated but not identical". With the two-channel requirement withdrawn, that question is **moot for the primary number** — there is one programmatic channel, and the separation that matters is the information-set separation of item 2, which is enforced rather than assumed. It remains open for judge-scored secondary outcomes, where the stopping signal and the scorer are correlated functions of the same text, and where neither the clean-independence nor the shared-noise analysis applies.

### T16 (leakage) — the draft's central claim is WITHDRAWN; leakage level becomes a randomized coordinate

**Withdrawn, in the reviewer's terms.** The draft claimed: "$\Lambda$ is a function of $(\tilde A_t,H_t)$ only (A12), so capping it per generator or including binned $\Lambda$ as a design coordinate involves **no post-treatment conditioning**, and contrasts of severity/specificity *within* a $\Lambda$ bin are identified by T3", with the recipe "bin it; stratify randomization on the bin; verify that within a bin, message length no longer predicts $Y$". Every clause of that is withdrawn. In the primary design the treatment is the **selector** $K_t$ and the message $\tilde A_t$ is drawn *after* it from $q_{K_t}$, so $\Lambda(\tilde A_t,H_t)$ is a **descendant of the treatment** and a plausible **mediator** of the $k\to Y$ effect, since severity plausibly works partly by conveying information. A function of the realized treatment is post-treatment by definition; "pre-receiver-response" is not "pre-treatment", and by the draft's own criterion the treatment itself would be pre-treatment. The correct word is **pre-outcome**, and it licenses nothing. Consequently: (a) within-$\Lambda$-bin generator contrasts are **mediator-stratified and collider-exposed** through unmeasured message attributes that co-determine $\Lambda$ and $Y$, not T3 contrasts; (b) "stratify randomization on the bin" is **not implementable in the stated order**, because the bin is unknown until $K_t$ has been drawn and a message sampled; (c) "capping $\Lambda$ per generator" is **rejection sampling on a function of the message**, replacing the pinned kernel $q_k$ by $q_k(\cdot\mid h,\Lambda\in b)$ with an **unknown normalizer** — precisely the entry in this document's own D2 failure catalogue ("best-of-$n$/rejection sampling/retries: order-statistic factors, unknown normalizers"), which voids P2's pinned-kernel well-posedness and A6/A9's by-construction status in exactly the arms the leakage story depends on, and silently redefines the estimand away from the pinned library (A5/A8). The draft's own concession — "the within-$\hat\Lambda$-bin contrast is a valid causal contrast for a different coarsening… unsigned" — **understated** this: it is not a different coarsening of the treatment, it is conditioning on a post-treatment variable. The string "**no post-treatment conditioning**" is deleted, and §13(c)'s "leakage is a pre-treatment design coordinate, not a mediator" is replaced by "**leakage level is a coordinate of the randomized action space; the realized leakage score is post-treatment and is never conditioned on**".

**T16, restated as the design decision that replaces it (R5).**

1. **The action is the pair.** Define pinned generators $q_{(g,\lambda)}$ *built* to a target leakage level by construction of their prompts, verified offline against the pinned library **before the freeze**. The selector is the pair $(g,\lambda)$, jointly randomized at $e=1/8$ over the $m_G=8$ non-`STOP` arms. The frozen taxonomy already enumerates these: the **graded redaction series** and $A_8$ (`info_cap_bits` 12, uncapped) are library members at declared levels, and `info_cap_bits` is a frozen **action feature** — a design covariate of the arm, not a measured covariate of the message.
2. **$\hat\Lambda$ is a fidelity measurement, never a stratifier and never a filter.** Report the observed $\hat\Lambda$ distribution per arm against that arm's declared level. Nothing is conditioned on it, binned by it, or filtered by it.
3. **Rejection sampling on realized $\Lambda$ is prohibited confirmatorily.** If it is run at all it is a **separate arm**, labelled a redefinition of the generator with an uncomputable density, excluded from P4, and reported as **ITT over the unfiltered generator** together with the rejection rate.
4. **$\Lambda$ is redefined as conditional information.** $\Lambda$ is the log-likelihood gain of a fixed reference receiver on the reference solution given $(H_t,\tilde A_t)$ relative to given $(H_t,\text{null message})$: condition on the task and the prior output, withhold nothing but the message. Dynamic range is validated on a **planted set** — messages that literally state the fix must score at the top, pure-affect messages at the bottom.
5. **Answer-withholding is promoted from an arm to an architectural invariant.** Generators receive a redacted view $X^-$ with the reference solution and tests removed, enforced by **prompt-hash assertion** (§16 item 1). The answer-visible condition ($A_8$) runs only as a declared **positive control**, and under the library split (R4) it is the **leakage upper anchor**, never the effect of feedback: $\{A_6,A_7,A_8\}$ are diagnostic, barred from every $\pi$, from $\mathcal A_{\rm adm}=\{A_0,\dots,A_5\}$ and from every reported baseline value.

**The placebo-solver definition is WITHDRAWN, and the "unsigned" caveat was wrong in a known direction.** The draft defined $\Lambda$ by "a placebo solver (a deliberately weakened receiver given the message alone, with task and prior output withheld)". A message like "you inverted the sign in the loop bound" or "you forgot the base case" carries **near-zero** information to a solver that has not seen the task or the prior output, and enormous information conditional on them. Leakage in multi-turn feedback is almost entirely **task-conditional**, so a task-blind scorer has essentially no dynamic range over exactly the messages that matter, its bins are degenerate, and $\hat\Lambda$ is systematically near zero for the highest-leakage messages. So the relation is **not unsigned**: $\hat\Lambda$ **understates** leakage, and understating it makes any leakage-controlled contrast look **larger**. That direction is now stated wherever $\hat\Lambda$ appears (A12).

**What is identified, and what is not.** Identified by T3 with **no conditioning**: contrasts across $(g,\lambda)$ pairs — "assign generator $g$ at built-in leakage level $\lambda$" — so the $\lambda$ main effect and the $g\times\lambda$ interaction come at the same cost as any other class contrast. Not identified: the effect of $g$ holding **realized** $\Lambda$ fixed (a mediator-controlled direct effect); any contrast conditioning on $\hat\Lambda$; and natural direct/indirect leakage effects (§12 item 6 stands). The restricted-kernel route — treating the treatment as (generator $k$, leakage bin $b$) with kernel $q_k(\cdot\mid h,\Lambda\in b)$ — is legitimate in principle and T3 would apply to it, but it acquires the normalizer $P_{q_k}(\Lambda\in b\mid h)$, which is **not exactly known** and would have to be Monte-Carlo estimated (degrading T9's exact unbiasedness to the estimated-$e$ case with A18's cross-term rate), and it imposes a **new positivity condition** $P_{q_g}(\Lambda\in b\mid h)\ge\delta_\Lambda$ at every history, which will fail exactly where it matters — a maximally severe generator may never emit a low-leakage message. **We do not take that route.**

**Two corrections retained from the draft, unchanged.** The effect at leakage level zero is a controlled-direct-effect-style quantity **only** under an explicit assumption that a message with prescribed style *and* prescribed information content is constructible; the **natural** direct effect requires the cross-world object (one message's style with another's content) and is **not identified**. And the bound $|\mathrm{CDE}-\mathrm{NDE}|\le\kappa\cdot\mathrm{Lip}$ remains **withdrawn as structurally wrong**: the style$\times$leakage interaction is exactly what makes them differ even when the sanitizer's style displacement is zero.

**The moment-constraint alternative, scoped.** For the **observational tilt extension only**, leakage neutrality can be imposed as a linear moment constraint $E_q[\phi^{\rm leak}\mid h]=E_g[\phi^{\rm leak}\mid h]$, yielding a two-parameter tilt. It is cleaner than taxonomy design there, but it holds only the *measured proxy* fixed and only *in expectation* — and by the paragraph above that proxy understates leakage — and, see T30, it introduces a second history-indexed $P$-dependent nuisance, so its efficiency theory does **not** carry over verbatim. The primary D1 design does not need it: leakage level is randomized.

**T16, companion: length and position are mediators too — the same defect, the same fix (R5).** Severity and specificity classes differ systematically in token count (`suffix_words`, a frozen **action feature**: $A_1$ 0, $A_5$ 9, $A_6$ 12, $A_4$ 12–16, $A_2$ 14, $A_3$ 13, $A_7$ 13), and the feedback message is always the most recent content in the receiver's context, so a long message pushes the task specification further from the generation point. Both are **caused by the randomized selector** and are therefore mediators, and the draft's only remedy — "within a $\Lambda$ bin, message length no longer predicts $Y$" — is a low-power observational regression on post-treatment variables with no stated power calculation. **It is withdrawn**, and the concession is explicit: a positive "severity helps" result is fully explained by "longer prompt, task spec re-anchored closer to the generation point", so **without the calibration block below the class effect is confounded with length by design-mediation.** The affordable fix, in three parts:

* **(a) Harness requirement, all arms.** Re-render the task specification at a **fixed token distance** from the generation point in every arm, padding with inert filler verified at $\hat\Lambda=0$. This is prompt geometry, it costs nothing, and it removes the position channel outright.
* **(b) A separate pre-registered length-calibration block** — not a second primary axis. Each class at **2 pre-registered token budgets** plus a **filler-only arm** (pure context-length increase, no semantic content): $190\text{ tasks}\times3\text{ arms}\times1\text{ turn}\approx\mathbf{570}$ receiver calls. At the spec's constant table (2,150 calls/hour) that is $\approx0.27$ h; at the superseding multi-turn measurement in `docs/measured_calibration.md` (909 calls/hour for 3B multi-turn work) it is $\approx0.63$ h. Either way it is far inside the **20,000-call / 9.3-hour** affordability ceiling. (The two throughput figures conflict; the conflict is reported, not resolved here.)
* **(c) Reporting.** The class effect is reported **net of the measured length main effect** from that block.

### P17 (labeler discipline)

(a) A **post-treatment** label ("was this feedback helpful?") is not a function of $(\tilde A_t,H_t)$, so no version mix and no intervention is defined, and the contrast is selection on the outcome: with label $\mathbf 1\{Y=1\}$ the estimated contrast equals $1$ at every history, even for a receiver that ignores the message entirely. In LLM-feedback research this is the *natural* mistake, since the obvious way to label a message is by its apparent effect. This is the **same defect class as the withdrawn T16 recipe**, one step further along: T16 conditioned on a function of the realized treatment, P17(a) conditions on a function of the outcome. Both are barred by the same rule — *nothing downstream of the selector enters the conditioning set of a confirmatory contrast.*

(b) A **stochastic** labeler is misclassification, not coarsening; pin it deterministic (then it is simply a noisier admissible coarsening whose cost is measurable) or treat its recorded seed as part of the treatment definition. In the frozen D1 design this is largely moot and should be said so: the generators are **deterministic template renders** with a uniformly drawn index over 3 frozen templates using the episode seed, invoked **statelessly** under A5 (fresh process per call, no carried KV cache, persona, scratchpad, surviving reasoning tokens, tool handle or server-side conversation id), with a byte-exact input-provenance hash per call. The recorded index *is* the seed, so the deterministic branch of (b) holds by construction. The stochastic branch binds only in the LM-generator extension, where A5 must be **verified** rather than assumed, and where a failure of the out-of-order replay test forces the history to be enlarged to contain the carried state (R7(d)) — at which point the labeler's error and the generator's hidden state are the same problem. Whether longitudinal labeler error attenuates is **OPEN**: the argument that a product of independently attenuated factors is not an attenuated product does not by itself establish non-attenuation, and in the classical non-differential case per-turn attenuation does compose.

---

---

## 9. Falsification, hygiene, and the oracle

**Scope note, stated before the battery, because it governs everything below.** The frozen design (D1) is a sequentially randomized harness with $m=9$ actions, $\mathcal K_G=\{A_1,\dots,A_8\}$ randomized uniformly at $e_t(k\mid H_t)=1/8=\delta$ (measured positivity 1.0 at every branched state), $A_0=\texttt{STOP}$ absorbing and exempt from the floor, $T_{\max}=3$ turns and $D=2$ decision points. The i.i.d. unit is the **task instance**: $n_{\rm clusters}=176$ task families drawn from 190 tasks, pool ceiling $\approx230$ (3B) and $\approx100$ (7B); the 1,520 $=190\times8$ paired root-seed units are **within**-cluster. Two histories are in play throughout (R3): the analyst/harness history $H_t^A$, which contains the programmatic grade $\psi$, and the policy-observable $H_t^O=\varphi_t(H_t)$, with $\mathcal F_t^O=\sigma(\varphi_t(H_t))\subsetneq\sigma(H_t^A)$, from which $\psi$ and every hidden-test-derived quantity are excluded. Every diagnostic below states which of the two it is computed on.

**And the fact that reorders this section.** The only measured headroom in the whole program is $+0.046$ of final success from **oracle stopping decisions** (audits A3). Stopping-only regimes are the class $\Pi_0$ of R2, for which $W\equiv1$, $M=1$ and $n_{\rm eff}=n_{\rm clusters}=176$: **the deliverable the evidence supports needs no importance weights anywhere.** The off-policy machinery this section proposes to validate (T27) is therefore a validation of apparatus that the primary deliverable does not use, and it is presented as such and not as the headline.

### P18 (design falsification)

The four items are retained with their labels. What has changed is that each now carries (i) whether its null is true by construction and (ii) its power at $n_{\rm clusters}=176$. The previous closing sentence asserted that a run reporting all four is an experiment; as written, **no item in (a)–(d) had both a valid null and demonstrated power**, which is the finding this rewrite concedes.

**(a) Weight-mean specification checks — valid null, weak power, and only one arm where it has anything to falsify.**
The identity must be written in **stopped/indicator form**. Under an endogenous horizon $W_{1:t}$ and $H_t$ are undefined on $\{T<t\}$ and $E^\pi[g(H_t)]$ presupposes reaching $t$ under $\pi$, so the naive equality flags false positives on exactly the trajectory sets with early stopping — the regime this document cares about. Use either the **restricted-to-reached** form
$$E\big[W_{1:t}\,\mathbf 1\{T\ge t\}\,g(H_t)\big]=E^\pi\big[\mathbf 1\{T^\pi\ge t\}\,g(H_t)\big],$$
or the **stopped-process** form with $t\wedge T$; declare which one is computed, and compute the right-hand side with the *same* indicator so the check is an equality of two identified quantities.
Where it bites: in the D1 primary arm the assignment density is $1/8$ **by construction** and $W\equiv1$ for $\Pi_0$, so there is no logged density to falsify and the check is vacuous there. Its one real home is the **simulated-log arm**, where $\hat e$ is fitted by multinomial logistic regression on $S_k$. That arm's pre-registered level **0.2 is not a randomization floor** — $8\times0.2=1.6>1$, so no such floor exists — it is a **weight-truncation level** ($\hat e$ clipped below at 0.2, hence $w\le5$); it introduces clipping bias, **A6 does not hold in that arm** (the logging policy is confounded by construction, $\kappa\in\{0,1,2,4\}$), and the truncation rate must be reported alongside the check.
Power, computed rather than asserted: with $g\equiv1$ the null mean is 1 and $\mathrm{Var}(\hat{}\,)\le(E[W^2]-1)/n_{\rm clusters}$. At $d=1$, $E[W^2]\le\delta^{-1}=8$, so the worst-case standard error is $\sqrt{7/176}=\mathbf{0.20}$; at $d=2$, $E[W^2]\le\delta^{-2}=64$ and it is $\sqrt{63/176}=\mathbf{0.60}$. **Run it on bounded prefix weights at $t=1$ ($d=1$) only, and report the realized value with this standard error.** At $d=2$ it is vacuous: with degenerate weights the sample mean sits below 1 with high probability even when every logged density is exactly right, so a "violation" at depth 2 is uninformative and a pass is an admission of no power.

**(b) Randomization tests — exact in this design at depth 1, not in general.**
The original objection stands and is retained: under a **history-adaptive** schedule re-drawing selectors changes the realized histories and therefore the assignment densities, so the statistic is not recomputable under a sharp null on $Y$ alone, and exactness requires either a non-adaptive schedule ($e_t$ depending only on $t$ and past selectors) or a sharp null on the entire output path. Two design facts narrow this for D1, and both are conditions, not hopes:
* the frozen schedule is **non-adaptive** — $e_t(k\mid H_t)=1/8$ depends on neither $H_t$ nor $K_{1:t-1}$ — so the assignment densities are invariant to re-drawing; and
* in the E2 branch tree **every non-`STOP` arm is executed at every branched state**, so for a re-assignment of the depth-1 selector the re-assigned arm's outcome is *observed*.

Consequently the depth-1 randomization test is exact **conditional on the realized replicate draws**, with no sharp null required. It does **not** extend past depth 1: the tree's depth-2 continuations are policy-fixed, so re-assignment at turn 2 is not recomputable from observed data. Power: a family-clustered permutation test over 176 clusters, at the design's measured precision (paired family-clustered bootstrap half-width $\pm0.019$ at $R=8$, MDE 0.027 at 80% power).

**(c) Branch battery — the one item with real power, now pointed at the place it is most needed.**
As before: resume fidelity via a two-sample test on next-token log-probability vectors (high power against version drift, prefix and template mismatch; power against subtle state leakage remains **OPEN**, and multiplicity control must be stated, since under provider nondeterminism this is a high-dimensional distributional test, not an equality check); duplicate arms carrying the identical message at different tree positions; randomized execution order with a permutation test against execution index and wall clock; snapshot-hash assertions. Three additions, forced by the A1-interference exposure of the deep slice and free or near-free:
1. **Interleave branch expansions across task instances with a cooldown** rather than expanding one node's arms back to back, and apply the **randomized expansion order to the deep slice too** (it was required for the permutation test but not applied there). The deep slice repeatedly re-sends near-identical prefixes for one task instance, which is the maximal-exposure configuration for provider-side prefix/KV caching and batch-level numeric coupling.
2. **A fixed-prompt canary battery replayed each block**, to detect prefix-cache and numeric drift directly. This is necessary because the previously proposed check — "verify caching changes latency and not tokens" — **cannot detect the failure it is aimed at**: prefix caching changes kernels and numerics, not the token count, so "tokens unchanged" is fully consistent with cache-induced dependence across branches, and client-side one cannot verify that caching is off.
3. **Report the duplicate-arm discrepancy on the deep slice beside $\hat v$ as a headline diagnostic, and if the discrepancy exceeds $\hat v$, declare $\hat v$ (and $\hat R$) unusable.** This matters more here than for ordinary arms because $\hat v(h)$ in T27 is built from within-node replicates and will absorb cache-induced dependence as if it were independent Monte Carlo noise, biasing $E[\hat v]$ and hence $\hat R$ by an unknown amount. The "real ground truth" is thus the most dependence-exposed quantity in the design, and saying so is part of claiming it.

Also inherited from A5/R7 and reported here: the **input-provenance hash** (SHA-256 of the fully rendered generator prompt, recomputed offline from the recorded $H_t$ and the redacted view $X^-$ alone, byte-exact), the **fresh-context assertion** per call, and the **out-of-order replay test** on a random 2% sample requiring byte-identical output. For the frozen template library these are CPU-side and effectively free.

**(d) P18(d) (negative control on a causally inert dimension) — WITHDRAWN as a falsification test; replaced in place by two controls whose truth is known by construction.**
*What was claimed:* that a generator differing only on a causally inert dimension (politeness markers, greeting, capitalization) must return zero, and that a non-zero effect indicts confounding, judge bias or a broken weight. *Why it fails, in the reviewer's terms:* the control has no valid null inside this document's own framework. §2 asserts that LLMs are paraphrase-sensitive and §11.1's ceiling argument presumes that within-history phrasing variation may be causally material, so a non-zero politeness effect on a pinned receiver is a **true effect of the intervention**, not an indictment of the design, and the test cannot separate artifact from real sensitivity. It commits precisely the error §11.2 prohibits — a null that is a priori false, so rejection is uninformative and non-rejection is an admission of low power. *What replaces it:*

* **(d.i) Guaranteed null — a hash-verified withheld channel.** An arm identical to $A_1$ (bare retry) except for a perturbation written to a logged field that the input-provenance hash of §16 item 1(a) proves is **absent from the rendered receiver prompt, byte-exact**. The truth is exactly zero on $Y$ and it is *software-verifiable*, not statistical. Two consequences worth stating plainly. First, because the rendered prompt hash equals $A_1$'s, the common-random-number cache (rollouts keyed by `sha256(state_prefix || message || seed)`) serves this arm the same draw, so it costs **zero receiver calls**; `llama.cpp` at `-np 4` is not bit-deterministic across batches, so caching is reuse of one draw rather than reproduction of it, and here reuse is exactly what is wanted, since it makes the null exact. Second, the statistical version of the test therefore audits the **estimator and pipeline** — fold leakage, a weight bug, judge bias where a judge is used for a secondary outcome, cache or batch dependence — and not the design. Its power is the design's own: it detects pipeline errors of $\ge0.027$ in the outcome scale and nothing smaller.
* **(d.ii) Guaranteed positive — the answer-visible arm, read as a ceiling.** $A_8$ (`PATCH`, `info_cap_bits` uncapped) appends the reference fix and is already a randomized member of $\mathcal K_G$ at $1/8$, so it costs nothing extra. Its effect must be large and near the design's measured ceiling, and it is reported as **the scale against which every other arm is read** — the **leakage upper anchor**, never as the effect of feedback. If it is *not* large, the defect is in the harness or in the receiver's instruction-following, and that is itself the finding. $A_8$ is diagnostic-only: barred from every $\pi$, from $\mathcal A_{\rm adm}=\{A_0,\dots,A_5\}$ and from every reported baseline value (R4).
* **What $A_6$ (`DIVERT`, negative control) and $A_7$ (`MISDIAGNOSE`, placebo) are, then.** They remain diagnostic arms and they remain reported, but **their nulls are not known to be zero** for exactly the paraphrase-sensitivity reason above. They are *anchors*: they measure the pinned receiver's response to inert and to misleading content. A non-zero value is a true effect on that receiver, not evidence of a broken design, and it may not be read as a falsification. The zero-information comparator that content effects must be measured against is not $A_6$ but the pre-registered baseline **B2** (fixed unary retry to $T_{\max}$, no stopping rule), which `positioning.md` constraint 2 makes mandatory.

**Closing statement, replacing "a run that does not report (a)–(d) is not an experiment".** All four items must be reported, and the report must state for each what it can and cannot detect: (a) has a valid null but only in the simulated-log arm and only at $d=1$, with a worst-case SE of 0.20 (0.60 at $d=2$, where it is vacuous); (b) is exact at depth 1 in this non-adaptive design and not beyond it; (c) has demonstrated power against version, prefix and template drift and **OPEN** power against subtle state leakage; (d.i) is a software assertion with a known-zero truth whose statistical form audits the pipeline at MDE 0.027, and (d.ii) is a known-large positive read as a ceiling. A run reporting all four with these caveats stated has been audited; a run reporting them as if each were a two-sided falsification of the design has overclaimed.

### T26 (what the oracle buys, and its cost)

**(a) Positivity is relocated, not removed.** Under A1–A5, A13 the branch data are a sequentially randomized experiment **by construction**: $Q_t(H_t^A,a)$, blips, $V(\pi)$ for executable regimes and the value of any executable modified treatment policy are identified with **no ignorability assumption over $\mathbb L$** and with **no density ratio over the string space**, because we sample from the intervened kernel rather than reweighting. Here $\delta=1/m_G=1/8$ *because the design is uniform*; in general the floor is $\delta$ and not $1/m$. The previous clause "and **no** positivity assumption" is **corrected**: it was contradicted two lines later by (b). The accurate statement is
> **positivity holds by construction on the expanded action set at every design-reached node, and fails precisely off-tree (T26(b))** — i.e. the positivity condition is *relocated* from $\mathbb L$ to the expanded tree, not dispensed with.

**(b) Off-tree non-identification.** Unchanged, and it is the positivity condition of (a) in its contrapositive form: if $\pi$ selects an action never expanded at a positively-reached node, $V(\pi)$ is not a functional of the branch data (two-model argument).

**(c) $\Omega(m_G^{D})$ lower bound — DEMOTED to a remark; retained because it is true, not because anything follows from it.** *What was claimed:* that without structure, identifying the optimal tree-supported deterministic regime requires $\Omega(K^T)$ leaf rollouts (a randomized algorithm making $q$ leaf queries succeeds with probability at most $q/K^T+o(1)$, needle-in-a-haystack over leaf-valued instances), and that this is "the formal reason a learned blip estimator is **mandatory** rather than convenient". *Why the inference fails, in the reviewer's terms:* it is a non sequitur, and the bound is for a setting this design does not inhabit. The construction lower-bounds **exhaustive search over history-indexed regimes with no state abstraction**; the document then immediately models every nuisance on a frozen finite-dimensional summary $\varphi(H_t)$, under which dynamic programming costs $O(m\cdot D\cdot|\mathcal S|)$. A learned blip estimator does not *evade* the bound — it substitutes a function-class assumption, which in the region where it extrapolates **is an identifying assumption and must be labelled as such** (the T7 caveat). Calling it "mandatory" converts an assumption into a theorem. And it is numerically inert at the frozen constants: $m_G^{D}=8^2=64$ leaves, which is what the E2 depth-1 tree already enumerates exhaustively at every branched state. **No design decision turns on T26(c), since no one proposed exhaustive history-indexed search.** The surviving statement is: *exhaustive history-indexed search is infeasible in general, therefore structure must be imposed, and every guarantee downstream is conditional on that structure.*

**(d) Two distinct costs, with the frozen numbers.** Evaluating one fixed executable regime costs $O(nD)$ calls; greedy inference-time rollout **under a fixed continuation** costs $O(m_G(D-k))$ per decision. The $m_G^{D-k}$ figure applies to exhaustive recursive search over history-dependent continuations, not to greedy rollout. Priced: one on-policy rollout of a single candidate over the paired design is up to $190\times8\times3=4{,}560$ receiver calls $\approx2.1$ h at 2,150 calls/hour, so **at most four** such rollouts fit inside the 20,000-call / 9.3-hour affordability ceiling. Rollout is the scarce resource; re-reading a recorded run for a new candidate $\tau$ costs nothing (P23).

**Therefore, restated.** The oracle is not a substitute for causal estimation; it is the object causal estimation compresses. Positivity has been converted into a **purchased budget on the expanded tree**, where it holds by construction and fails off-tree. Structure plus backward induction is the only route past history-indexed search that this document has — and two scope limits travel with that sentence: the structure is an identifying assumption wherever it extrapolates (T7), and backward induction on $\varphi$-measurable value functions returns $\pi^{\rm greedy}$, **not** $\arg\max_{\Pi_{\rm cp}}V$, because $\varphi$ is not sufficient and A19b is not assumed by the primary route (R8). The object this design reports is $\hat\pi$, the best member of the pre-registered finite candidate set declared in §16.

Also: temperature 0 is not determinism (batching, floating-point non-associativity, MoE routing, speculative decoding), which is why A3 integrates provider randomness out and A13 requires the branch decoding regime to match deployment. This concession is load-bearing twice over — it is also why the cache and batch-coupling channels of P18(c) cannot be dismissed, and why $\hat v$ in T27 must be read against the duplicate-arm discrepancy.

### T27 (debiased validation risk — a ranking device, not the headline experiment)

**Status: the absolute debiased risk is WITHDRAWN as a deliverable; the ranking use is retained, with its selection inflation reported.** *What was claimed:* that $\hat R$ is an unbiased estimate of the true conditional-effect risk on the real system and that this "should be a headline experiment, not an appendix". *Why the absolute number fails:* the subtracted variance offset is 2–8× the estimand it is subtracted from at the affordable replicate count; the offset's unbiasedness requires a matched history law that the frozen tree violates by design; and the labels are unbiased for the **fixed-continuation** blip, not for the blip under an optimal continuation the critic actually targets. *What replaces it:* the same identity used only for **ranking** competing estimators, where the offset cancels, together with the scope restriction and the selection correction below. The headline comparison of this program is the paired on-policy family-clustered contrast against **B4** (E0/E7, R9), not T27.

**(i) The identity, unchanged.** If $\hat\gamma$ is fit on data independent of the oracle branches and $\tilde\gamma$ is an oracle estimate with $E[\tilde\gamma\mid h]=\gamma(h)$, $\mathrm{Var}(\tilde\gamma\mid h)=v(h)$, then
$$E\big[(\hat\gamma-\tilde\gamma)^2\big]=E\big[(\hat\gamma-\gamma)^2\big]+E[v],$$
so $\hat R=n^{-1}\sum_i(\hat\gamma-\tilde\gamma)^2-n^{-1}\sum_i\hat v$ is unbiased for the true conditional-effect risk **provided $E[\hat v]=E_{\rm val}[v]$**, and may be negative in finite samples. For **ranking** competing estimators on the same oracle labels the offset cancels and no variance estimate is needed at all. $v(h)$ needs $n_b\ge2$ per arm.

**(ii) The offset swamps the absolute number at the affordable $n_b$.** Branch replicates are frozen at $n_b=3$. At $p\approx0.5$, $v(h)\approx p(1-p)/n_b\approx\mathbf{0.083}$, i.e. a per-state Monte Carlo SE of up to **0.29** — the design's own measured figure — whereas the quantity being measured, $E[(\hat\gamma-\gamma)^2]$, is **0.01–0.04** for any plausible critic. The subtracted offset is therefore **2–8× the estimand**, and $\hat R$'s Monte Carlo error over the tree's $\approx400$ states is of the same order as the difference between a good critic and a useless one. Ground truth on this tree is usable **pooled or on strata, not per state** — which is already the pre-registered validation target (class ordering of pooled $\gamma_2$; pooled $\rho$ and $\beta$ per class; sign and rank correlation of $\hat\gamma_2$ against state-level Monte Carlo values) and is the form T27 must take.

**(iii) $n_b\ge8$ is WITHDRAWN as unaffordable, with the resulting resolution stated.** A deep slice at $n_b\ge8$ over the tree's 400 states and 8 non-`STOP` classes is $400\times8\times8=\mathbf{25{,}600}$ branch rollouts **for the slice alone** — above the 20,000-call ceiling by itself, $\approx11.9$ h at 2,150 calls/hour. At the $\approx50$ states that are affordable at $n_b=8$ ($50\times8\times8=3{,}200$ rollouts, $\approx1.5$ h), $\hat R$'s error is $\approx\pm0.05$, which does not separate 0.01 from 0.04 and therefore **ranks nothing**. The frozen figure is $n_b=3$, and the resolution it buys is the pooled/stratified target of (ii) — not a per-state risk.
> **Conflict to report rather than resolve (spec PART 0 vs `docs/measured_calibration.md`).** The binding table gives $\approx2{,}150$ calls/hour and a 20,000-call $\approx9.3$-hour ceiling. `docs/measured_calibration.md` **supersedes 2,150 for multi-turn work** with 909 calls/hour (3B) and 619 (7B), noting that 2,150 "makes multi-turn designs look about 2.4× cheaper than they are". Under the superseding figure, 25,600 rollouts is $\approx28.2$ h, 20,000 calls is $\approx22$ h, and 9.3 h buys only $\approx8{,}450$ multi-turn calls. Every affordability verdict in this section holds *a fortiori* under the superseding figure; the arithmetic above is printed at 2,150 for consistency with the rest of the document, and the conflict is flagged here as required.

**(iv) The matched-slice condition, and why the frozen tree violates it.** Unbiasedness of $\hat R$ requires the variance offset to be an average over the **same history distribution** as the squared-error term. P5b places $v$-estimation in a narrow deep slice and the wide slice at $n_b=1$, where $v$ cannot be estimated at all, so importing the deep slice's average $v$ is valid only if the two slices share the history law. They do not: E2 stratifies state selection on the **visible** verdict with failure oversampling 3:1, and those known sampling probabilities must be carried as weights in any case. Either (α) estimate $v$ on a **random subsample of the validation histories** ($n_b=2$ suffices for unbiasedness, at high variance), or (β) require the deep slice to be a uniform random subsample of the wide slice's histories and **verify it**. Absent (α) or (β), only the ranking use is available, and the absolute risk number is not reported. This mismatch is in addition to the two caveats the earlier text did flag (continuation regime, branch-history restriction).

**(v) Continuation mismatch is a scope restriction, not a caveat.** The E2 tree branches at depth 1 with **policy-fixed** depth-2 continuations, while the critic's stage-1 target is the blip under an optimal continuation ($\max$ over $\mathcal A_{\rm adm}$ inside $\tilde V_2$). $\tilde\gamma$ is therefore an unbiased label for the **fixed-continuation** blip, and $\hat R$ is unbiased *for the wrong target* if the critic targets the optimal continuation. The depth-2 supplement (200 depth-1 outcome states $\times$ 8 classes $\times$ 2 seeds $=3{,}200$ rollouts) is too small to repair this. Accordingly the claim is stated as **"validated against the fixed-continuation blip on the branch history distribution"** — a scope restriction on the deliverable, written into the claim rather than appended to it. Any stage-1 critic evaluated this way is extrapolating and must be reported as such.

**(vi) Selection inflation, which the document catches twice elsewhere and did not apply here.** Offset cancellation makes the ranking criterion unbiased *for each fixed learner*; taking the minimum over $L$ candidate learners on a single noisy criterion computed on the study's **smallest** sample reproduces exactly the pathology P11 catches for branch selection and P24(ii) for stopping — the winner's apparent risk is biased downward by roughly $\sigma_R\sqrt{2\log L}$ (a factor of 2.04 at $L=8$), and the "validated" estimator is chosen by that noise. Mandatory, therefore: **split the deep slice into a ranking half and a reporting half and report the winner's risk on the held-out half**, or report the ranking with an AKM/Bonferroni-corrected interval; and in either case report $L$ and the spread of $\hat R$ across candidates so the selection inflation is visible. Report the ranking as the **paired difference of squared errors with a family-clustered bootstrap interval** over the 176 families, all seeds, branches and turns of a family in one fold.

**What the asset still is, stated without the overclaim.** Applied causal inference validates CATE estimators on synthetic DGPs because ground-truth conditional effects do not exist. A resettable receiver with a programmatic outcome supplies **real** unbiased conditional-effect labels on the **real** system, and the literature audit found no deployment paper with this asset; it is claimed as a design choice rather than apologised for. What is withdrawn is the claim that the **debiased absolute risk** is a headline deliverable. On the frozen budget it is a **ranking** device on the branch history distribution against the fixed-continuation blip, reported with $L$, the spread, the held-out winner's risk, and the duplicate-arm discrepancy beside $\hat v$.

**The symmetric use — validating the off-policy machinery — is retained but rescoped, and the "curse-of-horizon curve" is WITHDRAWN.** One can log a behaviour policy, compute exact propensities, and compare sequential IPW / self-normalized / DR estimates of $V(\pi)$ against on-policy rollout truth. What cannot be delivered is "a real, non-synthetic curse-of-horizon curve **as a function of $T$**": the frozen design has $D=2$ decision points, so override depth takes the three values $d\in\{0,1,2\}$ with $M=\delta^{-d}\in\{1,8,64\}$ and $n_{\rm eff}\ge n_{\rm clusters}\delta^{d}$ equal to **176, 22 and 2.75 clusters** at $n_{\rm clusters}=176$ (230, 28.75, 3.59 at the 230 ceiling). That is a **two-point comparison** ($d=1$ against $d=2$, with $d=0$ the unweighted reference), not a curve, and at $d=2$ the effective sample is under three clusters, so the comparison can exhibit degeneracy but cannot estimate its rate. Report ESS and $\hat D_2$ with every off-policy number. And the ordering must be said out loud: the measured $+0.046$ of headroom lives entirely in stopping, stopping-only regimes are $\Pi_0$ with $W\equiv1$, and **the deliverable the evidence supports needs no importance weights at all** — so this is a validation of machinery the primary route does not use. Never a self-normalized estimator inside a certificate (T20(e)); and T20 itself is withdrawn as a deliverable (R4), so nothing here is feeding a certificate.

### T28 (sim-to-real transport — an exact identity, then a bound with four terms)

**The exact identity, displayed alone, because it has no third term.**
$$V^{U}-V^{\hat U}=\sum_t E_{H_t\sim P^{U}}\Big[\int\big(U_t-\hat U_t\big)(da\mid H_t)\ Q_t^{\hat U}(H_t,a)\Big].$$
This is exact, and it rolls in under the **real** user's history law. Every computable quantity lives on the simulator's history law $P^{\hat U}$, so a *usable bound* arises only after the change of measure $P^U\to P^{\hat U}$ — and **that change of measure is where the history-shift term comes from**. The earlier presentation conflated the identity with the bound and so left the third term's origin invisible.

**The bound, with the residual split as the algebra requires.** From
$$\Big|\int(U-\hat U)Q\Big|\ \le\ \Big|\int(U-\hat U)\,\bar q\circ S\Big|\ +\ \int U\,|Q-\bar q|\ +\ \int \hat U\,|Q-\bar q|,$$
plus the change of measure, there are **four** named terms, not two and not three:

1. a coarsened per-turn discrepancy $\|S_\#U_t(\cdot\mid h)-S_\#\hat U_t(\cdot\mid h)\|_1$ scaled by $\tfrac12\mathrm{span}(\bar q_t(h,\cdot))$. The earlier claim that the real-user factor "**is** estimable from ordinary unbranched logs with a classifier for $S$" is **WITHDRAWN**: this is a per-history $L^1$ distance between two conditional action laws at $H_t\sim P^U$, and real-user logs contain each text history **exactly once**, so it is not estimable at $h$. It is estimable only after pooling across histories through a smoothed model of $U_t(\cdot\mid h)$ — precisely the extrapolation over long, never-repeating text states that §5 and §15 item 2 declare unverifiable. Relabelled: **estimable only under a stated smoothness/pooling model for $U_t(\cdot\mid h)$**, which must be given with its diagnostic or the term demoted alongside term 4. As written it sits in the **same epistemic class** as the transport term this document does flag.
2. $\rho^{U}_t=E_{P^U}\big|Q_t-\bar q_t\circ S\big|$ — the coarsening residual under the **real** user's action law. Only **partially replayable**: the human's own logged message at a logged prefix *is* executable by replay under A13 (P14b), but only against *our* generated alternatives, so it is mix-relative, and it inherits P14b's stale-reference pathology.
3. $\rho^{\hat U}_t$ — the same residual under the **simulator's** law. Branchable, hence estimable, but **only relative to a declared, pre-registered and deliberately diverse within-cell candidate mix**, and satisfying only $\rho_t\le\sqrt{E[r_t^2]}$ by Cauchy–Schwarz; it is **not equal** to the within-cell variance unless $\bar q$ is defined as the within-cell mean under that same mix. Collapsing (2) and (3) into a single $\rho_t$ hid that one of the two is much the harder object; they are now separate with separate estimability statuses.
4. the **history-shift / transport** term between the $S$-coarsened history laws, arising from the change of measure in the paragraph above. The earlier flat claim that it is "**not estimable**" is **too wide and is corrected**: since the identity rolls in under $P^U$, and $P^U$ is exactly what human logs provide, the simulator's continuation can be rolled out from a **real logged prefix** under A13 — the mechanism P14b already establishes as executable — so no density ratio between coarsened history laws is needed for histories the logs reach. What is genuinely unestimable is narrower: **$\pi$-reachable real histories the logs never visit**, plus replay-fidelity and stale-reference error. The named sensitivity parameter moves to that residual.
   **But in the frozen design this narrowing is not available.** D1 has **no real-user log at all** — the intervener is automated and `positioning.md` states that transfer to human users is not claimed — so in D1 term 4 remains a named sensitivity parameter in full, and the correction above is an entitlement of a D3 extension that possesses such a log on the same task pool and interface. The narrowing is a statement about what *would* be estimable, and it is labelled as one.

**The demotion, restated at its correct strength.** "Two separately estimable numbers" was already demoted once, to "one estimable term, one mix-relative term, one unestimable transport term"; that is still too generous. The honest reading is: **one branchable mix-relative term (3); one term estimable only under an unverified pooling model (1); and two terms requiring a real-user log this design does not have (2 and 4).** Note also that the total-variation specialization is vacuous — two LLM text policies have *identical* (full) support while their high-probability mass is nearly mutually singular, so TV $\approx1$. And branching identifies the value of a modified treatment policy on the **simulator's** base kernel, not the real user's, so it validates an observational tilt estimator only when that estimator is run on harness-generated behaviour data with the harness's own base kernel.

**Finally, the horizon inside the harness, stated so it cannot be read as an advantage.** Inside the harness a `STOP`-inclusive regime is evaluated by on-policy rollout with **no censoring correction at all** — because the simulated intervener never abandons. In D1 the stopping coordinate is therefore **exogenous by construction**: $e_t(\texttt{CONT}\mid H_t)=1$ at every $t<T_{\max}$, the harness runs every trajectory to $T_{\max}=3$ and grades $\psi(H_k)$ at every turn, and $R_t$ is the harness's own randomizer. Two consequences. First, the learned `STOP` rule is a **protocol the system imposes**, not a model of when users stop; nothing here licenses reading it as a quit-hazard model, and real-user abandonment is a pure transport problem about which the harness has nothing to say. Second, **"the endogenous horizon costs nothing extra" is WITHDRAWN** (R3): in D1 the horizon costs nothing because it is exogenous, not because the theory absorbed it, and the real cost of the stopping coordinate is elsewhere — in the calibration of $E[\psi(H_k)\mid\varphi_k(H_k)]$ (T8b), the deployable rule's whole handle on "am I already right" and the hardest estimation problem in the design. The measured difficulty is on record: the visible verdict is one bit and absent on 20.8% of the informative pool, and the sibling loop's own self-check stopped on **50.4%** [0.479, 0.528] of all failures, while the $+0.046$ headroom is the value of the **oracle** $V$, available to no real rule. Report the oracle-$V$ minus $\hat p$-rule gap as a headline pair, never the oracle value alone.

### P14b (replay continuation identifies a static regime)

**Scope: P14b is a D3 object.** It requires real logged human messages, and the frozen design has none; in D1 there is nothing to replay. It is stated here because it is the mechanism T28 term 4's narrowing leans on, so its pathology propagates into that narrowing.

Continuing a branch by replaying the human's actually-observed later messages is a legitimate identified estimand — the value of a deterministic **static** regime. But it is not the effect under natural continuation, and it suffers a **stale-reference** pathology ("fix the typo on line 3" in a branch with no line 3) whose bias is *plausibly adverse to beneficial interventions*: the more a branch improves the output, the more incoherent the replayed continuation. Usable only as a deliberately conservative anchor, or when the outcome is measured immediately at turn $t$. The sign claim is **OPEN** but empirically checkable by regressing replayed-message coherence on output distance — and it is checkable only where a real log exists, so in this program it is an extension-conditional check, not a deliverable. One cannot replay a patient's later treatments, which is why the object needs stating at all rather than being imported from the medical DTR literature; that observation is a remark about replay, and no claim of costlessness or of a missing analogue elsewhere rests on it (R3).

---

---

## 10. The design ladder

| | **D0 branching harness** | **D1 choke point (primary)** | **D2 known generator, full-message log-probs** | **D3 human logs** |
|---|---|---|---|---|
| A1 hygiene | **A**, not BC: randomized batch composition plus the pre-registered drift diagnostic (arm × time-block interaction with the recorded foreign-GPU-load covariate); §16 item 12 | **A**, not BC — same hygiene and same diagnostic | **A**, not BC — same | assumed |
| A2 frozen receiver | BC | BC | BC | assumed (retro-pinning) |
| A5 pinned library, invoked **statelessly** | BC for the frozen template library (deterministic renders, seeded uniform template index) | BC for the frozen template library; **A, and verified** for any LM-generator arm. The library is partitioned into an **evaluated** set $\{A_0,\dots,A_5\}$ and a **diagnostic** set $\{A_6,A_7,A_8\}$ | **A, and verified**, never BC — here the LM *is* the library, so statelessness is the thing at risk, not a formality: §16 item 1 (a) byte-exact input-provenance hash, (b) fresh-context assertion with prompt caching disabled, (c) out-of-order replay test on a 2% sample | — |
| A6 floor | BC (or exhaustive) | BC: **$e_t(k\mid H_t)=\delta=1/8=0.125$ uniform over the $m_G=8$ randomized non-`STOP` arms, $m_G\delta=1.000$**, attained with equality; `STOP` $=A_0$ is **exempt** (its potential outcome is $H_t^A$-measurable, so positivity holds by degeneracy). *The earlier cell "BC ($\delta\ge0.25$)" is **withdrawn**: a uniform floor needs $m_G\delta\le1$, so $\delta\ge0.25$ is feasible only for $m_G\le4$ and is arithmetically incompatible with the frozen 9-action taxonomy.* | **fails** over messages | **fails structurally** for continuation |
| A7 exchangeability | BC | BC (selector) | BC *iff* the three statelessness checks of §16 item 1 pass. **Input-provenance *logging* is not sufficient**: any carried KV cache, persona, scratchpad, surviving reasoning tokens, tool handle or server-side conversation id makes the generator kernel $q_{K_t}(\cdot\mid H_t,U_t)$ with $U_t$ a function of $K_{1:t-1}$ — post-treatment with respect to earlier selectors and a mediator of them — so the $q$ factors differ between the $e$-law and the $\pi$-law and **do not cancel** (§3 T3, §2 A5). On failure the history is redefined to contain $U_t$ | **assumed, untestable, believed false** at the text level; weaker and arguable for the stop coordinate |
| A8 support | BC, and it now includes **fixed rendered prompt geometry across arms**: the task specification is re-rendered at a fixed token distance from the generation point in every arm, padded with inert filler verified at $\hat\Lambda=0$ | BC, same geometry requirement (it is a harness requirement, not an analysis choice, and it is what removes the position/recency channel) | **binding**: fails if mask/tokenizer/template changes → *unidentified* | n/a (no known $g$) |
| A9 $\varphi$-measurable propensity | BC | BC — $\varphi$ is the frozen 87-coordinate policy-observable map, which **excludes $\psi$** and every hidden-test-derived quantity (§1, §2 A11(d)) | BC if the generator conditions on $\varphi$; if A5's statelessness checks fail, $\varphi$-measurability and every "no text critic" claim must be restated on the enlarged history containing $U_t$ | **false** for any compact $\varphi$ |
| A13 reset | BC + tested for reset, branch isolation and snapshot hashing; **A, and testable (P18)** for numeric reproducibility — temperature 0 is not determinism | optional | — | impossible |
| A18a sample splitting | **required** | **required** — knowing $e$ kills the *rate* condition, not the *fold-independence* condition; 5 folds over the 176 task families, all seeds, branches and turns of a family in one fold | **required** | required |
| A18b product rate on $(\hat e,\hat Q)$ | vacuous | vacuous | vacuous for $e$ | required, with the cross-term form |
| A19 coarsening sufficiency; A19b state-representation sufficiency | not needed | **neither is assumed by the primary route** | not needed | **A19 required** for message-level class effects |

*The A18 row has been split.* The previous single row marked "A18 rates: vacuous" in D1, which licensed fitting $\hat Q$ on the evaluation fold and thereby voided the exact-unbiasedness claim it was supposed to protect. Only the product-rate half (A18b) is vacuous when $e$ is known; cross-fitting (A18a) is required in every column, D1 included, and the "exactly unbiased for any outcome model" claim belongs to the cross-fitted one-step/AIPW estimator alone — not to TMLE, clipped IPW or any self-normalized variant.

*A19b matters here even though it is not assumed.* Because $\mathcal F_k^O=\sigma(\varphi_k(H_k))\subsetneq\sigma(H_k^A)$, $\varphi$ is not sufficient, so the optimum over the $\varphi$-measurable class does **not** satisfy a Bellman equation: backward induction on $\hat Q_k(\varphi_k,a)$ returns $\pi^{\rm greedy}\in\Pi_{\rm cp}$, in general $\ne\arg\max_{\Pi_{\rm cp}}V$. Every D1 entry below is therefore about $\hat\pi$, the best member of the pre-registered finite candidate set declared in §16, and not about "the optimal regime".

**What each identifies.**

- **D0.** $Q_t(H_t,a)$ and blips at every expanded action and design-reached history; $V(\pi)$ for executable regimes, best obtained by **direct rollout**; the value of executable MTPs on the harness's own kernel; ground-truth labels for T27; falsification of A13 and of A19; the judge's style sensitivity at fixed content. *Not:* anything about human users, unexpanded actions, irreversible environments, latent quality behind a judge, within-unit couplings.

- **D1.** Blips for all library generators and $Q_t$ on the **evaluated** action set $\{A_0,\dots,A_5\}$. The diagnostic arms ($A_6$ DIVERT, $A_7$ MISDIAGNOSE, $A_8$ PATCH) are estimated and reported in the leakage/placebo tables, and are **barred from every $\pi$, from $\mathcal A_{\rm adm}$ and from every reported baseline value**; the value of a policy that *would* be allowed $A_8$ is the leakage upper anchor, never the effect of feedback. Under R5 the randomized label is the **pair** $(g,\lambda)$, so the $\lambda$ main effect and the $g\times\lambda$ interaction are identified with no conditioning, while the effect of $g$ holding *realized* $\hat\Lambda$ fixed is not identified at all. Beyond that, the entitlements are **graded by override depth and must be named**, not quoted at one weight bound:

  - $W\equiv1$ for stopping-only regimes $\Pi_0$; $W\le\delta^{-1}=8$ for depth-1 class overrides $\Pi_1$; $W\le\delta^{-D}=64$ for full-depth regimes $\Pi_2=\Pi_{\rm cp}$, whose effective sample size on this pool is **2.75 clusters** and whose values must therefore be obtained by on-policy rollout, not off-policy weighting. In cluster units $n_{\rm eff}\ge n_{\rm clusters}\delta^{d}$ gives **176 / 22 / 2.75** at $n_{\rm clusters}=176$ (230 / 28.75 / 3.59 against the 230-task ceiling). *The earlier cell "$V(\pi)$ and $\pi^\star$ over $\Pi_{\rm cp}$ with $W\le\delta^{-d}$" conflated two incompatible targets — shallow-deviation regimes, which are off-policy estimable, and full-depth regimes, which are not — and is withdrawn in that form.*
  - The practical consequence, which is the reason the grading is worth stating: the **only measured headroom is +0.046 from stopping decisions**, and stopping-only regimes live in $\Pi_0$ with $W\equiv1$, evaluated by **unweighted means on recorded trajectories**. The deliverable the evidence supports needs no importance weights anywhere. The exponential-in-$T$ blow-up is bounded at $8^2=64$ only because the frozen design has $D=2$ decision points.
  - `STOP`-inclusive regimes and the endogenous horizon, **with the asymmetry stated correctly and the earlier phrase "at no extra cost" WITHDRAWN** (§4 T8): the `STOP` arm's *causal* nuisance is nil in the analyst information set — $Q_t(H_t^A,\texttt{STOP})=\psi(H_t)$ exactly, no nuisance model, zero GPU, no positivity (T8a) — while the *implementable* stop value is the unknown regression $E[\psi(H_t)\mid\varphi_t(H_t)]$ (T8b), which is the hardest estimation problem in the design. The measured difficulty is on record: the visible verdict is one bit and absent on 20.8% of the informative pool, and the sibling loop's own self-check stopped on **0.504** [0.479, 0.528] of all failures. The +0.046 is the value of the **oracle** $V$, available to no real rule, so the oracle-minus-$\hat p$-rule gap is reported as a headline pair.
  - The prioritized win probability against a **frozen** reference: $G_0$ is computed from the sibling project's completed 4,488-episode log on the identical task pool and hashed before any outcome of this run is examined, which is what buys the verbatim reuse of T8a and T9. The price is that the win probability is **reference-dependent** and $\pi^\star$ is reference-dependent with it. T13/T14 are a **secondary reporting device**, not the primary objective, which is $E[Y^\pi-\lambda C^\pi]$ at $\lambda=0.01$ per turn with degradation reported separately.
  - **A certified strict improvement over the logging policy — WITHDRAWN as a D1 deliverable (§6 T20).** It was advertised here as a headline entitlement. It fails three ways: the certificate is numerically vacuous at the honest inference unit (at $n_{\rm clusters}=176$ the smallest certifiable gap is **0.542** unweighted against **0.046** of available headroom, and 1.533 at $M=8$, which exceeds the range of $Y-\lambda C\in[0,1]$ and is impossible at any gap); it is unaffordable (34 and 273 GPU-hours against the 9.3-hour, 20,000-call ceiling); and $V(e)$ was never a baseline, because it is the harness's own $\delta$-floored mixture over eight arms **including** the negative-control, placebo and leaky arms, so the certified gap is monotone in the number of deliberately degraded arms and manufacturable with zero learning. In D1 there is also no *natural* policy in the data — the harness replaced the user — so "natural/logging policy" fused two different objects, and the word "natural" is deleted. What D1 does deliver instead: a **paired, family-clustered bootstrap** comparison (E0) against pre-registered named baselines — single-shot no-feedback; **B2**, fixed unary retry to $T_{\max}$ with no stopping rule; and **B4**, the strong baseline the design is powered against, which carries the headline gap — with $V(e)$ and the truncated prophet bound (P22) as diagnostic denominators only. Measured precision: half-width **±0.019** at $R=8$, MDE **0.027**.

  *Not:* generators outside the library; the effect of one specific text (identified, not estimable); any contrast holding realized leakage, message length or message position fixed; $\arg\max_{\Pi_{\rm cp}}V$ (only $\hat\pi$ over the pre-registered candidate set is reported); the real-user value; and — since the message generators write the *user's* turns — a shippable protocol at the message-generator coordinates, which are a **measurement device for blips**. The target-trial reading applies only to the product-side coordinates: `STOP`/continuation, interface and rendering variants, and suggestion policies.

- **D2.** Any support-compatible target reweighting the *same* library and mask, within a Rényi budget; token-level tilts identified but not estimable. **Correct role:** pin the within-class version mix and supply the $E[W_{1:t}]=1$ specification check. *Rao–Blackwellized weights are no longer claimed as D2's contribution (§3 P4, withdrawn as a technical contribution and retained as an opt-in, per-generator variance device for IPW only):* in the frozen design the generators are deterministic template renders with a seeded uniform index over 3 templates, so $q_k$ is a point mass given the recorded index and distinct $k$ produce distinct texts — the marginal weight equals the selector ratio exactly and **the variance reduction is identically zero**; and where generators are LM-based, computing $q_k$ for the $m_G-1=7$ untaken arms costs $m_G=8$ teacher-forced scoring passes per turn on the realized message, at the sampling-time truncated distribution, which competes head-on with the branch budget and must be priced against the 20,000-call ceiling. So the device is an identity with no gain in the primary design and non-free in the only design where it bites; each per-generator opt-in must also satisfy the catalogue below, because a wrong $q_k$ converts an exactly unbiased selector weight into a biased marginal weight. **Failure catalogue for "the propensity is known exactly":** discarded chain-of-thought (an intractable latent marginal — record it and define the action as the pair; **for a within-turn scratchpad discarded before the next call** it is pre-treatment generation randomness, not a mediator, so ignorability survives and only computability fails, **but this is false for any state carried across turns** — a KV cache, persona, scratchpad, surviving reasoning tokens, tool handle or server-side conversation id is post-treatment with respect to earlier selectors and mediates them, which breaks the density cancellation of T3, not merely its computability, and is the default implementation of a multi-turn LLM user: see A5 and §16 item 1); best-of-$n$/rejection sampling/retries (order-statistic factors, unknown normalizers — and rejection sampling on realized $\Lambda$ additionally replaces $q_k$ by a truncated kernel with an unknown normalizer, so it is excluded from T3 and P4 and may only be reported as ITT over the unfiltered generator with the rejection rate); unlogged tool calls inside the simulator (breaks A7 too, since a parent of $A_t$ is missing); speculative decoding and non-deterministic kernels; human editing of a draft; tokenizer/chat-template mismatch. Exact computability is true **only** for plain autoregressive sampling with fully recorded randomness **and verified statelessness**, and the *sampling-time* (truncated) distribution must be used — using the model distribution where a truncated sampler ran is a silent bias and a common implementation bug.

- **D3.** (i) stop-coordinate blips at or below the natural horizon, **under A7 for the continuation coordinate**, and for the **binary** coordinate only. The identified-set width $\kappa_0(\pi)$ of P21 is sharp *given* that A7, and is otherwise a **lower bound on the true ambiguity**: the behavioural mechanism P21 invokes to create the support failure — satisfied users stop — is simultaneously an A7 violation whenever the user's perceived quality exceeds what $H_t$ records, so on the supported histories the estimator is not consistent for the regime value either, and no computation of $\kappa_0$ will reveal the shortfall (this row's own grade for A7 in D3 is "assumed, untestable"; §15 item 8 lists the corresponding calibration as OPEN). For the cost-priced objective the width is $\kappa_0(\pi)\cdot\mathrm{range}(Y-\lambda C)$ with $C$ bounded by the cap, not $\kappa_0(\pi)$. (ii) version-averaged coarse-class effects under the natural mix, inheriting the logged intervener population; (iii) tilt functionals along a frozen $\phi$ within a KL budget, with **no** exclusion restriction and only a scalar normalizer; (iv) the truncated prophet benchmark and the $S$-coarsened real-user class marginals that T28 needs. *Not:* late-continuation regimes; generator-replacement policies; specific-text effects. **Role: external-validity anchor and descriptive confirmation, never the confirmatory arm.**

- **Real humans in the loop (P31).** Randomize a *suggestion* and you identify, under A22, the value of any **suggestion policy** — an ITT estimand, and a perfectly respectable one, since a suggestion mechanism is what a product ships. The value of a **message policy** is not identified without A19, an estimated user law, or an IV argument whose exclusion restriction is dubious because the suggestion is visible and shapes framing. **There is no design with both exact human-message propensities and a human user.** This bullet is the governing statement for the shippability question, and §0.2 and §12 now agree with it: in D1 the message generators write the user's turns, so the target-trial / shippability reading is restricted by name to the product-side coordinates, and message-generator arms are a measurement device for blips rather than a deployable protocol.

---

---

## 11. Extensions, stated precisely

**Scope note for the whole section (binding).** §11 describes *extensions*, not deliverables. Neither Ext-B (T30) nor Ext-A (T29) is on the confirmatory path: the primary route is the design-based analysis of §3–§5 with the paired, family-clustered on-policy comparison (E0, R9) as the primary inferential device. Every quantity below is stated in the section's own units and then re-stated in the document's global constants: the i.i.d. unit is the **task instance**, $n_{\rm clusters}=176$ task families (pool ceiling $\approx230$ with the 3B receiver, $\approx100$ with the 7B), $T_{\max}=3$ turns with $D=2$ decision points, $m=9$ actions of which $m_G=8$ are randomized at $e=1/8$, so the feasible positivity floor is $\delta=1/8=0.125$ and $\delta^{-d}$ is $1,8,64$ at $d=0,1,2$. Nothing in this section may be read as licensing a sample size, a certificate, or a novelty claim; on the last point see the corrected novelty paragraph at the end of §11.1.

### 11.1 Ext-B: the exponential tilt (T30)
With a frozen bounded $\phi$ (A20) and $q^\theta_t(a\mid h)\propto g_t(a\mid h)e^{\theta'\phi(a,h)}$:
$$w_t=\frac{e^{\theta'\phi(A_t,H_t)}}{Z_t(\theta,H_t)},\qquad Z_t(\theta,h)=E_P\big[e^{\theta'\phi(A_t,H_t)}\mid H_t=h\big].$$
**The human language mechanism cancels**: $Z_t$ is a conditional expectation of an *observed scalar*, so at the **true** $Z_t$ we have $E[w_t\mid H_t]=1$ exactly, support is preserved by construction, and the cumulative ratio is an exact $P$-martingale. The cancellation is a statement about kernels and therefore inherits A5 as corrected (R7): it requires $q^\theta_t$ and $g_t$ to be kernels in the **recorded** $H_t$ alone, conditionally independent of $K_{1:t-1}$ given $H_t$. Any carried KV cache, persona, scratchpad, surviving reasoning tokens, tool handle or server-side conversation id makes the tilt kernel a function of hidden state $U_t$ that is post-treatment with respect to earlier selectors, and then the $g$ factors do not cancel and the martingale property fails. Statelessness is therefore a precondition of T30, verified by the input-provenance hash, fresh-context assertion and out-of-order replay test of §16 item 1, not an idealization.

The EIF is $\tilde Q_1-\psi+\sum_tR_t(\tilde Q_{t+1}-\tilde Q_t)$.

> **T30's "the action-level text critic disappears" — WITHDRAWN as stated; replaced by the weaker true statement.** *We claimed that the action-level text critic disappears from the influence function. It does not: the residual term involves $\tilde Q_{t+1}(H_{t+1})$ and $H_{t+1}=(H_t,\tilde A_t,O_t,\dots)$ contains the realized message, so the critic is action-dependent, and the claim was contradicted three clauses later by this subsection's own concession about the soft-optimal recursion. What is true, and is a clean result: **no integration of the critic over the action space $\mathbb L$ is required — the critic is evaluated only at observed history–action pairs.** The limit of that claim is the retained concession below: the soft-optimal recursion still needs a text-conditioned critic at history–action pairs never observed.*

Local blips are within-history covariances $E[\mathrm{Cov}(Y,\phi_t\mid H_t)]$ with an orthogonal residual-on-residual estimator; the naive association differs by exactly the between-history covariance term. **No exclusion restriction is required**, because $\phi$ *defines an intervention* rather than a conditional independence — at the price that the effect is of a *bundle*: the minimum-KL nudge along $\phi$ including everything co-moving with it.

**The statistical price, which the earlier draft's price column omitted (this is the binding one).**

> **T30's "double robustness is *exact* in both directions" — WITHDRAWN as an estimator property; retained as a property of the population EIF at the true normalizer.** *The exactness, the identity $E[w_t\mid H_t]=1$, the $P$-martingale property and the $E[w\mid H]=1$ specification check all hold at the **true** $Z_t(\theta,H_t)$. But $Z_t$ is itself a conditional expectation over a long, never-repeating text history: an infinite-dimensional, $P$-dependent nuisance sitting **inside the intervention**. Root-$n$ inference for Ext-B therefore rests entirely on a product rate $\lVert\hat Z-Z\rVert\cdot\lVert\hat{\tilde Q}-\tilde Q\rVert=o_P(n^{-1/2})$ on **two** text-history regressions, which §12.12 and §15.2 concede is unverifiable and has no smoothness theory for text. **Unlike D1 there is no known-propensity fallback**: if $\hat Z$ is inconsistent the estimator is inconsistent; with $\hat Z$ in place $E[w_t\mid H_t]=Z_t/\hat Z_t\ne1$, so the exact martingale property and the specification check that was advertised as Ext-B's safeguard are both only approximate, and the Ville-type anytime-valid certificate floated in §15.3 is unavailable. Ext-B trades an untestable **identification** assumption (A19) for an unverifiable **estimation** condition. It is not a route to a certified number.*

$\hat Z_t$ is **cross-fitted on the same fold structure as the critic** — 5 folds over the 176 task families, with all seeds, branches, turns, templates and paraphrases of a family in one fold (R8, R9) — because it is estimated from the same data as the value; a non-cross-fit $\hat Z$ would put the nuisance and the value on the same observations and is not permitted. The cross-fit does not repair the product-rate requirement; it only removes the own-observation bias.

Corrections carried: the variance identity is P5's recursion under the doubly-tilted law (Gaussian closed form exact only under history-independent conditional variance); the KL budget must be defined under the **intervened** law and be the same object in all three places it appears; identification is stated only for kernels $q_t(\cdot\mid h_t)$ (natural-value-dependent kernels need the *induced marginal* kernel, not $q/g$); per-turn gains aggregate as $\sqrt{2\varepsilon\sum_t\sigma_t^2}$ by Cauchy–Schwarz, a factor $\sqrt D$ larger than the draft's per-turn figure — with the frozen design's $D=2$ decision points that factor is $\sqrt2$, and the horizon-length variable does not appear anywhere in this document at any other value; the natural-gradient step is a **local diagnostic only**, since the admissible radius lies far outside the first-order regime and the predicted gain can otherwise exceed the outcome's range; softmax-of-$K$ ($K\to\infty$ at fixed $\theta$) and best-of-$K$ ($\theta\to\infty$ at fixed $K$) are **different families**, and best-of-$K$ — with ratio bounded by $K$ — is better treated as a **pinned generator in the library**, which is exactly how the primary route absorbs it (and in the frozen design it is gated on E2, see §11.2); "no off-support extrapolation" overstates the case, since the soft-optimal recursion still needs a text-conditioned critic at history-action pairs never observed, so the honest distinction is extrapolation *within* the support versus *outside* it; conditional-quantile clipping and within-stratum rank normalization **violate A20** and are replaced by unconditional pre-specified transforms (which genuinely respecify the estimand rather than biasing it); asking a real user for $K$ drafts does not deliver i.i.d. draws, and presenting $K$ paraphrases of the user's own message is a *natural-value-dependent* regime with a different estimand — and both human-facing variants are **out of scope** for this project, whose intervener is automated by design, so the effects it can claim are effects of interventions deliverable by an automated intervener (`positioning.md`, scope statement).

**The route's ceiling, stated quantitatively at this project's numbers.** The KL-regularized policy-improvement step the LLM community already performs *is* the optimal longitudinal MTP inside a KL trust region, hence a causally identified estimand whose overlap holds by construction — conditional on statelessness (A5/R7) and on the true normalizer, per the price paragraph above. Its achievable per-turn gain is $\mathrm{sd}_g(Q^\star_t(H_t,A)\mid H_t)\sqrt{2\mathrm{KL}_t}$. The admissible budget is the one recomputed in §4 at the honest inference unit: at $n_{\rm clusters}=176$, $n_{\rm eff}^{\min}=30$ and $D=2$, $\sum_t\Delta_t^2\le\log(176/30)=1.769$, i.e. $\Delta_t\le0.941$ within-history SD and $\mathrm{KL}_t\le0.442$ nats per turn. Since $Y-\lambda C\in[0,1]$ gives $\sigma_t\le1/2$, the Cauchy–Schwarz aggregate over the two decision points is at most $\sqrt{2\cdot0.884\cdot2\sigma^2}\le0.94$ — about **twenty times** the only measured headroom in the whole design (**+0.046** from oracle stopping). **The KL ceiling therefore does not bind and constrains nothing here**: the binding quantity is $\sigma_t$, the within-history dispersion of $Q^\star$ under $g$, which is unmeasured. **If within-history phrasing variation is causally inert, the entire achievable gain is zero** and the interesting questions require leaving the support the generators span — which this extension, by design, cannot do. *Measuring that variance is experiment #1.* In the frozen design the within-class variation available to measure is **template** variation, not human variation (3 frozen templates drawn uniformly with the episode seed), and the instrument that measures it is E2's coarsening-sufficiency test, whose measured power is 92% against a within-class SD of $\hat v\approx0.08$ and 57% at 0.06 (`docs/design_e3_critic_policy.md`).

> **"Certifiable gain" — withdrawn as vocabulary.** *The word "certifiable" appeared here when §6 T20 still advertised a finite-sample improvement certificate. T20 is **withdrawn as a deliverable** (R4): on this task pool the smallest gap the certificate can resolve is 0.542 unweighted against 0.046 of available headroom, and it is arithmetically impossible for any weighted regime. Read every gain figure in this subsection as an **achievable** gain in a population sense, with no finite-sample certificate attached, and with inference supplied by the paired family-clustered bootstrap (measured half-width $\pm0.019$ at $R=8$, MDE 0.027) rather than by a Bernstein LCB.*

Two further scope facts about Ext-B at this design's size. First, the tilt regime is **$P$-dependent** — the intervention contains $Z_t(\theta,\cdot)$ — so whatever §5 T9(v) concludes about known randomization probabilities and the longitudinal efficiency bound for a *fixed* $\pi$ does not transfer to T30, and this subsection makes no efficiency-bound claim. Second, the tilt route is *not* an instance of the depth-graded weight bounds of R2: $w_t$ here is bounded by the range of $e^{\theta'\phi}$ over the frozen bounded $\phi$, not by $\delta^{-d}$, and no $\delta$-based effective-sample-size figure may be quoted for it.

**Novelty caution, updated after the literature audit (`docs/positioning.md`, `docs/literature_audit.md`, last checked 2026-09-19).** The earlier instruction "this must be checked against the literature before any novelty claim is made" has been discharged, and the result constrains this subsection. For binary actions with an indicator feature this is exactly Kennedy's incremental propensity score intervention, and longitudinal incremental interventions with efficient influence functions exist in the literature. In addition, the audit forbids claiming novelty for prompt-as-treatment framing (Wang et al., AAAI-25; Frauen et al., KDD 2026; CPO arXiv:2602.01711), DTR/Q-learning over a natural-language action space (arXiv:2502.17538), longitudinal causal inference over sequences of text features (arXiv:2605.07834), single-period text-treatment identification (arXiv:2410.00903), per-context off-policy prompt policy learning (arXiv:2504.02646), neural SNMM/blip estimation (DeepBlip, arXiv:2511.14545), and orthogonal DR Q-learning (DRQ-learner, arXiv:2509.26429). These are cited, not re-derived. What remains as a *candidate* delta is narrow: tilting along a frozen semantic feature over a text action space — the audit records that no one has extended modified treatment policies to a text action space, and that the one infinite-dimensional extension (arXiv:2606.27518) works only through linear basis structure text lacks — together with the EIF collapse for a $P$-dependent regime. It is a candidate for an extension paper, it is not evidenced by this design, and it is not claimed here.

### 11.2 Ext-A: coarsening (T29)
If message-level class effects are wanted: under fine-level exchangeability, countable $\mathbb L$, and a designated message in the observed support, the canonical-message value **is point-identified**. The draft's partial-identification claim and its sharpness argument remain **withdrawn**: $Q(h,a)$ is a functional of the observed law at every $a$ of positive probability.

> **T29's "point-identified — it is simply not *regularly* estimable" — WITHDRAWN as a mischaracterization; replaced by the correct statement.** *We used "irregular" as a synonym for "huge variance". Irregularity is a precise property — non-existence of a pathwise-differentiable representation with a finite variance bound, hence no $\sqrt n$-consistent estimator — and it does **not** hold under this document's own conditions. With countable $\mathbb L$, a full-support softmax and absolute continuity, $E[Y(a)]$ has the ordinary AIPW influence function*
> $$\varphi(O)=\frac{\mathbf 1\{A=a\}}{g(a\mid X)}\big(Y-Q(X,a)\big)+Q(X,a)-\psi,$$
> *whose variance is bounded by a multiple of $E[1/g(a\mid X)]$ and is finite whenever $g(a\mid X)>0$ a.s. and $E[1/g(a\mid X)]<\infty$; the longitudinal analogue multiplies the per-turn ratios. The canonical-message value is therefore **regularly estimable at $\sqrt n$ with a semiparametric efficiency bound of order $e^{\Theta(m)}$** — a catastrophic constant, not an irregularity. Genuine irregularity requires the separate, checkable condition $E[1/g(a\mid X)]=\infty$ (the Khan–Tamer weak-overlap regime this document cites elsewhere but does **not** invoke here). Accordingly "never estimable" is wrong wherever it appears, and the $T\rho$ object is relabelled a **finite-sample variance band**, with "irregularity" dropped from its description.*

The consequence for the project's thesis survives the correction in a slightly weaker form: *the obstruction is the size of the efficiency bound, not identification.* Stated at this design's numbers, the distinction is technically load-bearing and inferentially immaterial: with verbatim text histories the relevant cells sit at atoms of probability $e^{-\Theta(mt)}$ visited once, so an efficiency bound of order $e^{\Theta(m)}$ at $m=9$ leaves an effective sample far below **one** of the 176 task-family clusters. Fine-level cellwise contrasts are not reportable here at any horizon, and the document does not report them.

Under the natural within-class mix the fine ratio cancels exactly, leaving the coarse indicator ratio $\prod_t\mathbf 1\{S_t=\pi(H_t)\}/g_t(\pi(H_t)\mid H_t)$. Because that ratio is a **product over turns**, its bound is $\delta^{-d}$ with $d$ the override depth of the regime (R2), **not** $\delta^{-1}$: at $\delta=1/8$ this is $1$ for stopping-only regimes $\Pi_0$, $8$ for depth-1 class overrides $\Pi_1$, and $\delta^{-D}=64$ at full depth $d=D=2$ for $\Pi_2=\Pi_{\rm cp}$. In cluster units at $n_{\rm clusters}=176$ that is **176 / 22 / 2.75** effective clusters. So the coarsening converts an impossible constant, $e^{\Theta(m)}$, into an affordable one only for $\Pi_0$ and $\Pi_1$; at full depth 2.75 effective clusters is not a basis for inference, and full-depth values must be obtained by on-policy paired rollout (E0, E7), not by off-policy weighting. This matters in exactly the right direction for the project: the only measured headroom (+0.046, oracle stopping) lies in the stopping coordinate, stopping-only regimes sit in $\Pi_0$ with $W\equiv1$, and the harness runs every trajectory to $T_{\max}$ and grades $\psi$ at every turn, so the deliverable the evidence supports is estimated by **unweighted** means and needs no importance weights at all.

The cancellation's price is that the estimand inherits the logged intervener's within-class writing distribution, so a coarse blip is a property of **(receiver, task distribution, intervener population)**. In the frozen design that price is paid in a controlled form rather than incurred: the within-class mix is a **design choice** — the template index for the LM-free arms is drawn uniformly from 3 frozen templates with the episode seed, and the template index is a nuisance covariate, never a policy action — so the estimand's mix is the generator's by construction, which is what the primary route does. The cancellation also requires the within-class writing kernel to be a kernel in the recorded $H_t$ alone (A5 as corrected, R7); a stateful intervener breaks it for the same reason it breaks T3.

Further corrections: with a singleton reference the breakdown defect for a turn-$t$ blip is $\rho^\star=|\hat\gamma|$ standardized, **not** $|\hat\gamma|/T$; within-class dispersion is pointwise monotone under refinement for the **range** but only monotone *on average* (law of total variance) for the **variance**, which is the only version branching can estimate (counterexample: parent slice $Q\in\{0,0.5,1\}$ at $(0.98,0.01,0.01)$ has variance $0.0123$, while the refined sub-slice $\{0.5,1\}$ at 50/50 has $0.0625$); branching estimates dispersion under the mix one can **sample**, not under the logged human mix, so either one assumes the version writer reproduces that mix (strong) or one redefines the estimand's mix as the generator's — which is precisely what the primary route does, and which the frozen uniform-over-3-templates mix makes explicit; the suprema in the abstraction-gap bound must be restricted to the observed support with an $\varepsilon$-argument, since the sup need not be attained in countable $\mathbb L$; "the coarsened process is a valid causal model" holds with **verbatim** histories as states, and with coarse histories needs A9; the off-support caveat (sensitivity parameters must be *assumed* at histories never observed) applies to all three bounds, not just one; the trajectory variance constant should be re-derived from the **efficient** bound (per-step residual variances), not from unaugmented IPW with $E[Y^2]$ under the wrong measure; and **generator regimes do not enjoy the cancellation** — their $\chi^2$ against a human mix is exponential in message length, so they must be rolled out, not off-policy estimated from human logs, which is also why `positioning.md` constraint 4 forbids token-level importance weighting outright.

One further coordinate-level correction, carried from R5. The graded exclusion mechanisms below refer to locality and information content as *coordinates of the class*. Read that in the corrected sense: the **declared leakage level** $\lambda$ is a coordinate of the randomized action space, jointly randomized with the generator identity as the pair $(g,\lambda)$ at $e=1/8$; the **realized** leakage score $\hat\Lambda$ is post-treatment, is a fidelity measurement only, and is never conditioned on, stratified on, or filtered by. A coarse class effect is identified as a contrast across $(g,\lambda)$ pairs; the effect of $g$ holding realized $\Lambda$ fixed is not identified by anything in this section.

Retain nonetheless: the graded exclusion restriction E1$\Rightarrow$E2$\Rightarrow$E3 with only E3 ever used, and its three plausibility mechanisms (a coarse/binary outcome absorbs kernel differences that do not cross the decision boundary; an adaptive continuation repairs version noise, so exclusion is most plausible early and least plausible at the last turn — a **pre-registrable per-turn prediction**, and with $D=2$ decision points it is a two-point prediction, not a curve; the class already pins outcome-relevant content when locality and declared information content are coordinates). And the methodological instruction, now stated so that it does not contradict the frozen design: for **inference about dispersion, estimate rather than test.** $H_0:\sigma=0$ is a priori false for a paraphrase-sensitive receiver, so a rejection is uninformative as evidence and a non-rejection is an admission of low power; report $\hat\sigma$ with an interval and the breakdown value. This does **not** retire E2's pre-registered coarsening-sufficiency test, which `docs/design_e3_critic_policy.md` makes a **gate on GPU spend** rather than an inferential claim: the best-of-$K$ arm runs only if E2 rejects at $\alpha=0.05$, because under a sufficient coarsening a free-form proposal is scored by the critic only through its class label and best-of-$K$ provably cannot beat argmax within the critic's resolution. Where that test is reported it must be quoted with its measured power — 92% against a within-class SD of 0.08, 57% at 0.06 — and a non-rejection quoted as evidence against a template effect of 0.08, never as evidence of exact sufficiency. (Flagged for the editor: the earlier blanket instruction "test nothing, estimate" conflicted with that pre-registered gate; the design document wins, and the instruction is narrowed to inference about $\sigma$.)

### 11.3 Ext-E and Ext-D
Covered in §7 and §9. The one-line statements, with the qualifications the repairs force:

The **stop/text factorization** is the strongest **observational** position available, because the language density cancels identically — subject to A5 statelessness (R7), which is what makes the cancellation a statement about kernels in the recorded history. Its asymmetry must be read in the two information sets of R3: the stop arm carries **no causal nuisance** on the analyst history ($Q_t(H_t^A,\texttt{STOP})=\psi(H_t)$ exactly, zero Monte Carlo variance, zero GPU, no positivity requirement — T8a), while the **deployable** stopping rule is $E[\psi(H_t)\mid\varphi_t(H_t)]$, an unknown regression on the policy-observable history and the hardest estimation problem in the design (T8b). The measured record is on the hard side: the visible verdict is one bit and absent on 20.8% of the informative pool, and the sibling loop's own self-check stopped on **50.4%** [0.479, 0.528] of all failures. The **+4.6 pp** is the value of the *oracle* $V$ and is not available to any real rule, so it is reported only as an oracle-minus-implementable pair. "The endogenous horizon costs nothing extra" does not appear in this section and is withdrawn wherever it did.

**Branching** is the strongest **experimental** position, because positivity is replaced by a purchased budget — but the purchase is small and its limits are measured, so the claim is about *validation*, not about inference at scale. The budget is frozen at $n_b=3$ branch replicates; the resulting per-state Monte Carlo SE is up to **0.29**, so branch-sampled ground truth is usable **pooled or on strata, never per state**, and the pre-registered validation targets are the pooled class ordering, the pooled per-class parameters, and the sign and rank correlation of the fitted blips against the state-level Monte Carlo values. The whole purchase sits under the affordability ceiling of **20,000 receiver calls $\approx9.3$ h** at 3.2 s per 3B call and $\approx2{,}150$ calls/hour; any branching prescription over that ceiling is cut or marked unaffordable.

Branching remains necessary for three things, and the list is shorter than the draft's. (i) For the **continuation** half of the policy class, and specifically for full-depth regimes $\Pi_2=\Pi_{\rm cp}$, whose off-policy effective sample size on this pool is 2.75 clusters and whose values must therefore come from on-policy rollout (R2). It is **not** needed to value the stopping coordinate: the harness runs to $T_{\max}$ and records $\psi$ at every $k$, so stopping-only regimes $\Pi_0$ are valued by unweighted means on already-recorded trajectories with $W\equiv1$. (ii) For **within-unit contrasts relative to a declared coupling** — here the common-root pairing in which all arms share the same saved root output $O_1$ for each (task, seed) unit, with rollouts keyed by `sha256(state_prefix || message || seed)` so that identical messages from identical states reuse a cached draw. The coupling must be declared as what it is: `llama.cpp` with `-np 4` is not bit-deterministic across batches even at a fixed seed, so caching is *reuse of one sampled draw, not reproduction of it*, which is exactly why the estimator is paired rather than assuming independence. Note also that the 1,520 paired units ($190\times8$ root seeds) are **within-cluster**: they buy precision, not clusters, and the measured paired family-clustered bootstrap half-width is $\pm0.019$ at $R=8$ with MDE 0.027. (iii) For **validating everything else**, which is the resettable-receiver asset `positioning.md` identifies as this design's genuine advantage, with its stated non-licences: no transfer to real users (the intervener is a template, more deterministic than an LLM intervener, let alone a human), no transfer to other receivers, no ground truth beyond the branched depth, and no reuse of one tree for both fitting and evaluating without the family-level split.

---

---

## 12. Scope and limitations

A hostile reviewer should be able to sign this list. Items 1–15 keep their numbers and
their original subject matter; items 16–21 are limitations the reviewers established that
this list previously omitted. Where an earlier formulation was wrong rather than
incomplete, the correction is marked in place.

1. **We do not identify the effect of a specific message.** Identified in principle on a
   full-support logging policy. **Correction (the earlier "never estimable" was wrong as
   stated):** under the conditions this document assumes — countable $\mathcal L$,
   full-support softmax, absolute continuity — $E[Y(a)]$ for a fixed string $a$ has the
   ordinary AIPW influence function, with variance bounded by $E[1/g(a\mid X)]$, which is
   finite whenever $g(a\mid X)>0$ a.s. and $E[1/g]<\infty$. The functional is therefore
   **regularly estimable at $\sqrt n$ with a semiparametric efficiency bound of order
   $e^{\Theta(m)}$** — a catastrophic constant, not an irregularity. Genuine irregularity
   (the Khan–Tamer weak-overlap regime) requires the separate, checkable condition
   $E[1/g(a\mid X)]=\infty$, which we do not invoke here. The $T\cdot\rho$ object is
   relabelled a **finite-sample variance band**; "irregularity" is withdrawn from it, and
   with it the errata's Route-A resolution as originally worded (T29, §14 Route A).
   Under a truncated sampler with a changed mask the fixed-string value is **not
   identified at all**, which is a separate and stronger failure.

2. **We do not identify the value of a generator outside the pinned library**, a different
   tokenizer, template or mask, or any target not absolutely continuous with the design.
   Identification of library members themselves additionally requires **stateless
   invocation** (A5): no carried KV cache, persona or scratchpad memory, no surviving
   reasoning tokens, no persistent tool handle or server-side conversation id. If the
   per-call input-provenance hash, the fresh-context assertion or the out-of-order replay
   test fails, the density cancellation in T3 fails with it: the history must then be
   redefined to include the carried state, and every "no text critic" and
   $\varphi$-measurability claim restated on the enlarged history.

3. **We do not reach the human user population.** Known propensities are purchased by
   *replacing the human*, or by retreating to an ITT estimand on suggestions under A22.
   External validity is a transport problem with one **unestimable** term (T28).
   **Consequence for the shippability claim (§0.2 item 4), stated here because this item
   is what contradicts it:** the target-trial reading applies only to the coordinates that
   are genuinely product-side — `STOP`/continuation, interface and rendering variants, and
   suggestion policies. No product ships a mechanism that writes its users' turns.
   **Message-generator arms are a measurement device for blips, not a deployable
   protocol**, and the coordinates the measured evidence actually values (+4.6 pp from
   stopping decisions alone) are exactly the product-side ones.

4. **We do not identify late-continuation regimes from logs.** The positivity failure is
   structural and confounded with the outcome by construction; Manski bounds are often
   uninformatively wide, which is itself the finding. Related correction, wherever the
   **simulated-log arm** appears: its "floor 0.2" is **not** a randomization floor
   ($8\times0.2=1.6>1$ is infeasible). It is a **weight-truncation level** ($\hat e$
   clipped below at 0.2, so $w\le5$); it introduces clipping bias; **A6 does not hold in
   that arm**, whose logging policy is confounded by construction; and the truncation rate
   must be reported with every number computed there.

5. **We do not identify within-unit win probabilities, individual-effect distributions, or
   any coupling functional** without a declared coupling, and with one they are
   design-relative rather than properties of the world. Two further scope statements now
   attach here. (i) $G_0$ is **frozen on an independent pre-registered reference sample** —
   the sibling project's completed 4,488-episode log on the identical task pool, hashed
   before any outcome of this run is examined — so $\tilde Y$ is a fixed known transform
   and T8a/T9 apply verbatim; the price is that **the reported win probability is against
   the frozen sibling log and $\pi^\star$ is reference-dependent**, not a comparison
   against a concurrent $\pi_0$. (ii) **T13/T14 are demoted to a secondary reporting
   device.** With a binary hidden-test verdict, $N\in\{1,2,3\}$ and cost monotone in $N$ up
   to token noise, the ordered quotient has roughly six cells, the tie mass is the majority
   of pairs, and the prioritized estimand is a coarse monotone re-expression of a
   $2\times3$ table whose variance is dominated by tie handling — while *shrinking* an
   effect already at 0.015–0.030. The tie mass must be reported. The primary objective is
   $E[Y^\pi-\lambda C^\pi]$ at the pre-registered $\lambda=0.01$ per turn, with
   **degradation reported separately** (audits A3). T13 is scoped to outcomes with a
   continuous or many-valued primary component.

6. **We do not identify any leakage contrast that conditions on the realized leakage
   score, and we do not identify natural direct/indirect leakage effects.** The earlier
   formulation of this item was wrong in its central move and is replaced. The treatment is
   the *selector*; the message is drawn after it, so $\Lambda(\tilde A_t,H_t)$ is a
   **descendant of the treatment and a plausible mediator**. "Pre-receiver-response" is not
   "pre-treatment"; the correct word is **pre-outcome**, and it licenses nothing.
   Accordingly: **leakage level is a coordinate of the randomized action space; the
   realized leakage score is post-treatment and is never conditioned on, stratified on, or
   filtered by** (A12). Identified, by T3 with no conditioning: contrasts across pinned
   pairs $(g,\lambda)$ — "assign generator $g$ at built-in leakage level $\lambda$" —
   including the $\lambda$ main effect and the $g\times\lambda$ interaction, at the same
   cost as any other class contrast. Not identified: the effect of $g$ holding realized
   $\Lambda$ fixed (a mediator-controlled direct effect); any within-$\hat\Lambda$-bin
   contrast, which is mediator-stratified and collider-exposed; and cross-world natural
   direct/indirect effects. "Bin it and stratify randomization on the bin" is **not
   implementable** — the bin is unknown until after $K_t$ is drawn — and capping $\Lambda$
   is rejection sampling, which replaces $q_k$ by a truncated kernel with an unknown
   normalizer; if run at all it is a separate arm with an uncomputable density, excluded
   from P4 and reported as ITT over the unfiltered generator with its rejection rate.
   **The old "explicitly unsigned relation" caveat is withdrawn as too weak: the direction
   is known.** $\hat\Lambda$, defined as the log-likelihood gain of a fixed reference
   receiver on the reference solution given $(H_t,\tilde A_t)$ versus given a null message,
   *understates* leakage, which makes any leakage-controlled contrast look **larger**; the
   task-blind placebo solver is withdrawn, because a message like "you forgot the base
   case" carries near-zero information to a solver that has not seen the task, so a
   task-blind scorer has no dynamic range over exactly the messages that matter.
   **Message length and in-context position are the same defect and get the same
   treatment.** Severity and specificity classes differ systematically in token count, and
   the feedback message is always the most recent context, so both are caused by the
   randomized selector and are mediators; "within a $\Lambda$ bin, length no longer predicts
   $Y$" is a low-power observational regression on post-treatment variables and is not a
   remedy. The design instead re-renders the task specification at a **fixed token distance**
   from the generation point in every arm, padding with inert filler verified at
   $\hat\Lambda=0$, and runs a separate pre-registered length-calibration block (each class
   at two token budgets plus a filler-only arm; ≈570 calls ≈0.27 h). The class effect is
   reported net of that block's measured length main effect, and **without the block the
   class effect is confounded with length by design-mediation.** `info_cap_bits` and
   `suffix_words` are frozen **action features**, not measured covariates of the message.

7. **Judge-based outcomes break the following:** differential error biases the estimand by
   $E^\pi[\beta]$ with no weighting repair; noise is amplified by $E[W^2]$; length bias
   shifts the estimated optimal horizon late by $\beta/\lambda$ in cost units at the
   pre-registered $\lambda=0.01$ per turn; the resettable-judge audit bounds only
   manipulated style dimensions and is unavailable on open-ended tasks. **Two corrections to
   the shared-channel claim.** (i) The earlier "a shared stopping/scoring channel
   manufactures $\Theta(\sigma\sqrt{\log\bar K})$ of pure-noise gain" conflated two
   objects and overstated the first. The **selection inflation** is
   $\Theta\big(\sigma\sqrt{\log\bar K/n_h}\big)$, with $\sigma$ **the standard error of the
   value estimate at the analysis $n$** and $n_h$ the number of independent scorings per
   decision node: $n_h=1$ for a per-trajectory argmax, where the warning stands, and
   $n_h=n$ for a rule selected globally across units, where it vanishes. Numerically, at
   this design's measured precision ($\pm0.019$ paired family-clustered half-width at
   $R=8$, i.e. $\sigma\approx0.010$) and $\bar K\approx5$, the global-selection inflation is
   about **0.012** — real, below the **0.027** MDE, of the same order as a $+0.015$ to
   $+0.030$ target gap, and removable by the selection/evaluation split already required
   (P11). Read as per-unit outcome noise ($\sigma\approx0.43$ for a binary verdict) the old
   figure would have been ≈0.5, exceeding the usable span of the outcome, which is how the
   error is visible. (ii) The non-vanishing quantity is a **different** object: P24(i)'s
   within-unit optimistic bias $E[\varepsilon_\tau]$, which persists as $n\to\infty$ because
   the same realized judge noise both triggers the stop and scores the outcome. Independent
   channels address (ii); sample size and a selection/evaluation split address (i). **With a
   programmatic primary outcome, $\sigma=0$ for the primary number and P24(ii) does not bite
   on it**; A11(d)'s earlier "two prespecified independent measurement channels" is replaced
   by the $\varphi$-exclusion assertion — $\varphi_t$ excludes $\psi$ and every
   hidden-test-derived quantity, enforced by feature-builder assertion — and the independent
   -channel requirement survives only for judge-scored secondary outcomes, justified from
   P15(a)'s differential-bias argument plus P24(iii), not from the selection rate. Any
   horizon-invariance calibration test is defined at $T_{\max}=3$. Programmatic outcomes are
   not a preference, they are a precondition for the horizon results.

8. **Session-valued outcomes are not identified under abandonment.** We avoid this by fiat
   (A21), and say so.

9. **All uncertainty is conditional on one frozen receiver, version and decoding
   configuration.** Importance sampling cannot express uncertainty about "the receiver";
   reporting standard errors that appear to cover generalization across model versions
   would be misleading. **The regime is now declared, because §5 previously prescribed the
   opposite:** A2 holds. Estimates are reported **per pinned snapshot**; clustering is by
   **task family** (primary) and time block; **model-version epoch is deleted as a
   clustering level**. Clustering by epoch would treat snapshot drift as sampling noise
   around a single parameter, which is coherent only if the estimand is redefined as an
   average over a declared snapshot distribution — the opposite of A2, under which a
   violation makes the estimand *undefined, not noisy* — and few-cluster inference over a
   handful of epochs is invalid on its own terms, so it is not even a conservative fix.

10. **Benchmark contamination** does not break internal validity but distorts the
    task-difficulty distribution and can make a class look effective because the answer was
    memorized. **Correction to the direction, which was stated backwards for the coordinate
    this project makes central:** contamination attenuates **content** blips toward zero, but
    it *inflates* stop-arm advantages and cost-priced gaps. On a memorized task the receiver
    is already correct at turn 1, so stopping immediately is genuinely optimal, the
    cost-priced value $E[Y-\lambda C]$ of any early-stopping regime rises relative to a
    talkative mixture that keeps paying $c_t$, and the learned horizon is biased short. Any
    comparison against such a mixture is therefore **anti-conservative** under this
    document's own primary objective, not conservative. Consequences: the prioritized net
    benefit and any certificate-style number are reported primarily within the
    pre-registered **uncontaminated** stratum with the contaminated stratum shown
    separately; a per-task contamination score (turn-1 pass rate under a no-feedback single
    shot) is a **stratification variable** in §16, not only a post hoc report; and because
    $G_0$ is frozen on the sibling log over the identical task pool (item 5), the reference
    distribution inherits the same contamination through its $C$ and $N$ components. Nulls
    on contaminated tasks remain uninformative for content arms.

11. **Simulated users dissolve informative censoring by construction**, which is exactly why
    the harness has nothing to say about real-user abandonment. Stated the other way round,
    since §0.2 previously sold this as a free advantage: **in D1 the stopping coordinate is
    exogenous by construction.** The simulated user never abandons, so $R_t$ is entirely the
    harness's own randomizer, and the learned `STOP` rule is a **protocol the system
    imposes, not a model of when users stop**. P23's continuation weight
    $\prod 1/e_t(\texttt{CONT}\mid H_t)$ is then pure design noise, and P23 is restricted to
    its one real use — reusing a single logged harness run across many candidate $\tau$
    without re-rolling out — with the break-even against direct rollout stated. The
    motivating structure (P21's "satisfied users stop", informative quit hazards, the
    identified-set width $\kappa_0(\pi)$) lives only in logs, where A6 fails structurally for
    continuation; it belongs to the D3 extension with **non-identification as its headline**.
    "The endogenous horizon costs nothing extra" is **withdrawn** (item 16 and T8b): it costs
    the calibration of $E[\psi\mid\varphi]$.

12. **The product-rate condition licensing $\sqrt n$ inference is unverifiable for
    text-valued histories.** Where the propensity is known this does not threaten
    unbiasedness; where it is estimated, it is an assumption, not a theorem. The primary
    route does not rest on it: the pre-registered primary comparison is a **paired,
    common-random-number, on-policy** head-to-head (E0), whose estimator is the mean over 176
    task families of the family-mean paired difference with a paired family-clustered
    bootstrap, and which invokes no product rate and no importance weight.

13. **A1 is threatened by specific, checkable channels**: shared prompt/KV caching,
    batch-level decoding nondeterminism, shared token or rate-limit budget pools (an
    interference channel *specific* to horizon-valued treatments — one trajectory's length
    consumes another's available horizon), online receiver adaptation, within-batch judge
    drift. **Consequence for A1's grading, which this item contradicts:** on the machine this
    runs on, A1 cannot hold *by construction*. The receiver is `llama-server` with `-np 4`
    under an uncontrolled foreign GPU load from sibling projects — which is why the harness
    records `yielded_seconds_before_start` and `foreign_gpu_load_at_start` — and llama.cpp is
    not bit-deterministic across batches even at a fixed seed. A1 is therefore **assumed**,
    with randomized batch composition and a pre-registered drift diagnostic (arm × time-block
    interaction, foreign-load covariate); randomizing batch composition makes the interference
    exchangeable, not absent. The **deep branch slice is the most exposed configuration in the
    design**, because it re-sends near-identical prefixes for one task instance and its
    within-node replicate spread $\hat v$ would absorb cache-induced dependence as if it were
    independent Monte Carlo noise; "verify caching changes latency and not tokens" cannot
    detect this, since prefix caching changes kernels and numerics rather than token counts.
    At the frozen $n_b=3$ and $\hat v\approx0.08$, the duplicate-arm discrepancy must be
    reported alongside $\hat v$ as a headline diagnostic, and if it exceeds $\hat v$ the
    branch-sampled ground truth is declared unusable.

14. **Cross-model off-policy evaluation by token-level reweighting is not available** and any
    such claim is likely an error (P32).

15. **Where the environment is resettable, off-policy evaluation must justify itself.** If
    none of the four legitimate reasons applies, run the policy. **The same test now applies
    to the baseline, which it previously did not.** $V(e)$ is the harness's own
    $\delta$-floored mixture over eight arms **including** $A_6$ (negative control), $A_7$
    (placebo) and $A_8$ (leaky); each sits at $1/8$ and drags $V(e)$ down, so
    $V(\pi)-V(e)$ is **monotone in the number of deliberately degraded arms and
    manufacturable with zero learning**. In D1 there is also no *natural* policy in the data —
    the harness replaced the user — so "natural/logging policy" fused two objects and the word
    "natural" is deleted. Accordingly: the library is partitioned into an **evaluated** set
    $\{A_0,\dots,A_5\}$ and a **diagnostic** set $\{A_6,A_7,A_8\}$, the diagnostic arms are
    barred from every $\pi$, from $\mathcal A_{\rm adm}$ and from every reported baseline
    value, $V(e)$ is a **diagnostic denominator only** computed on the evaluated stratum, and
    the value of a policy that *would* be allowed $A_8$ is the **leakage upper anchor**, never
    the effect of feedback. The headline comparison is against a pre-registered **named**
    baseline, with four denominators in one table: single-shot no-feedback; **B2**, fixed unary
    retry to $T_{\max}$ with no stopping rule (the mandatory zero-information arm); **B4**, the
    strong pre-registered comparator the design is powered against; and the truncated prophet
    bound (P22) with $V(e)$ as diagnostics. **The headline gap is against B4.** Beating B2 is
    nearly free and proves nothing — B2 breaks one already-correct answer in six (degradation
    0.162) — which is why sizing against B2 gives $+0.07$ to $+0.12$ while sizing against B4
    gives $+0.015$ to $+0.030$.

16. **We do not deliver a finite-sample improvement certificate.** T20 is **withdrawn as a
    deliverable and retained as a scope statement**: at the honest inference unit it is
    numerically vacuous and it is unaffordable at any gap worth certifying. At
    $n_{\rm clusters}=176$ the smallest gap the corrected bound
    $n\ge8M\log(4|\Pi|/\alpha)/\mathrm{gap}^2$ can resolve is **0.542** for an unweighted
    comparison against **0.046** of available headroom, a shortfall of **11.8×**, and it is
    *arithmetically impossible* for any weighted regime, because the required gap (1.53 at
    $M=8$) exceeds the range of $Y-\lambda C\in[0,1]$; a one-sided LCB that is always negative
    certifies nothing. The cost side agrees: $2.4\times10^4$ clusters at 3 receiver generation
    calls per unit and ≈2,150 calls/hour is **34 GPU-hours**, and $2.0\times10^5$ is **273**,
    against the **9.3-hour / 20,000-call** ceiling. The sentence claiming this was "roughly
    what a stratified A/B test over the $m$ arms costs" is **deleted**; the honest multiple is
    **50–120×**. What we report instead is the paired family-clustered bootstrap interval of
    item 12 (half-width $\pm0.019$ at $R=8$, MDE 0.027). Relatedly, **"the stopping decision
    is a scalar blip with a known stop-arm value" is withdrawn in its unqualified form**: the
    stop arm is known to the *analyst* ($Q_t(H_t^A,\texttt{STOP})=\psi(H_t)$, T8a, zero GPU, no
    positivity needed) and is an **unknown regression** $E[\psi(H_t)\mid\varphi_t(H_t)]$ to the
    *policy* (T8b) — the hardest estimation problem in the design, with the visible verdict one
    bit and absent on 20.8% of the informative pool and the sibling loop's own self-check
    stopping on **50.4%** [0.479, 0.528] of all failures. The **+4.6 pp** is the value of the
    **oracle** $V$, available to no real rule, and the oracle-minus-$\hat p$-rule gap is
    reported as a headline pair, never the oracle alone.

17. **We do not report "the optimal regime."** $\Pi_{\rm cp}$ is the class of
    $\mathcal F_k^O$-measurable rules on the frozen finite-dimensional feature map $\varphi_k$,
    valued in $\mathcal A_{\rm adm}=\{A_0,\dots,A_5\}$. Because
    $\mathcal F_k^O\subsetneq\sigma(H_k^A)$, **$\varphi$ is not sufficient**, so the restricted
    optimum does not satisfy a Bellman equation on $\varphi$-measurable value functions:
    backward induction returns $\pi^{\rm greedy}$, which is in general **not**
    $\arg\max_{\Pi_{\rm cp}}V$. **A19b (state-representation sufficiency) is not assumed by the
    primary route.** The reported object is $\hat\pi=\arg\max_{\pi\in\Pi}\widehat V(\pi)$ over
    a **pre-registered finite candidate set** whose count is declared in §16 (the earlier
    $|\Pi|=100$ is not a count we use, and the certificate arithmetic is printed at both
    $|\Pi|=8$, $L=6.461$, and $|\Pi|=100$, $L=8.987$, so the sensitivity is visible), with
    $\pi^{\rm greedy}$ entered as one labelled member, evaluated out-of-fold over the 176
    families and re-estimated on a held-out half with the selection inflation reported. A
    covering-number bound would be required to say anything about the infinite class; **we do
    not have one and do not claim one.** The phrase "the optimal regime" is reserved for
    $\arg\max_{\Pi_{\rm cp}}V$, which this design does not report. Relatedly, override depth is
    not a free knob: every claim must name its entitlement class, $\Pi_0$ (stopping-only,
    $W\equiv1$, unweighted means, 176 effective clusters), $\Pi_1$ ($W\le8$, 22) or
    $\Pi_2=\Pi_{\rm cp}$ ($W\le\delta^{-D}=64$, **2.75** effective clusters, values obtainable
    only by on-policy rollout, off-policy certification explicitly disclaimed). The
    exponential-in-horizon blow-up is capped at $8^2=64$ **only** because the frozen design has
    two decision points. Since the measured headroom is entirely in stopping, the deliverable
    the evidence supports lives in $\Pi_0$ and needs **no importance weights at all**.

18. **The exceptional set is most of the sample space, not a corner.** This list previously
    said nothing about null-blip mass, and treated non-regularity as a reporting footnote. On
    the 3B receiver, audit A2's fit puts **0.156** of task mass below 0.05 success — where the
    blip is exactly 0 for every class, because nothing repairs those tasks — and **0.334**
    above 0.95, where the blip is dominated by breakage and the trivial rule "stop iff
    `visible_pass`" already captures most of what there is, which is why B4 is hard to beat;
    only **0.406** is informative. So (i) inference on $V(\hat\pi)$ is non-regular over a large
    fraction of the population rather than a measure-zero set, and (ii) any marginal blip is
    attenuated by the null mass — the same attenuation item 10 attributes to contamination but
    which is here a property of task difficulty. The states where a learned critic can beat the
    trivial rule are essentially the false-pass states, whose rate
    $\phi=P(\text{visible pass}\mid\text{hidden fail})$ is **unmeasured**: the sizing grid
    assumes 0.10–0.25 (the risk register admits 0.05–0.40), and power spans **0.35 to 0.91**
    across that assumption and $\pi^\star$'s repair gain. Consequently the primary estimand is
    defined **conditional on the first attempt failing**, with the already-correct stratum
    analysed separately for **harm** (audits A2, A3), and the non-regularity remedy — an
    $m$-out-of-$n$ bootstrap or adaptive intervals — is a **requirement** in §16, not a
    suggestion.

19. **Our own premise checks limit what the causal machinery can be claimed to buy at the
    decision level, and this list previously omitted them.** In hand-built tabular simulations
    (exploratory, not pre-registered, no text and no receiver model — they test the logic of the
    claim, not LLM behaviour): unadjusted comparisons inverted the class ordering in **0 of 40**
    replicates recovering the sign, so *reporting* effects off logs is dramatically wrong; but a
    correlational critic conditioning on the full observed state recovered the **exact optimal
    regime in 39 of 40** replicates (mean regret 0.0010), three attempts to break it with latent
    confounding moved the logged-minus-randomized regret gap by at most **0.030**, and
    known-propensity IPW repaired the residual only partly and **non-monotonically**
    ($0.046\to0.033$, $0.028\to0.028$, $0.017\to0.019$ — one cell got worse). The dominant
    decision-level error was **myopia**, which loses under randomization too and is therefore
    not a confounding failure at all. So effect *reporting* and action *selection* are
    **separate deliverables with separate evidence, and neither may borrow the other's**; the
    gain the evidence attributes to this framework is horizon-aware valuation under
    randomization; and a **non-myopic correlational critic is a pre-registered baseline the
    framework must beat** (with the causal-vs-correlational comparison pre-registered at an
    expected value of **null**).

20. **We do not do anything that costs more than the measured budget.** Receiver calls cost
    3.2 s (3B) or 6.4 s (7B) at four contended slots, ≈2,150 calls/hour, so the affordability
    ceiling is **20,000 receiver calls ≈ 9.3 wall-hours**. Any prescription above it is cut or
    marked unaffordable in place — which is what happened to the certificate (item 16), and
    what constrains the branch budget to $n_b=3$ with per-state Monte Carlo SE up to **0.29**.
    The i.i.d. unit is the **task instance**: seeds, branches, turns, templates and paraphrases
    are *within*-cluster, so the 1,520 paired units are 176 independent clusters against a pool
    ceiling of ≈230 (3B) or ≈100 (7B), and **no sample-size claim may be stated in
    conversations** or in units of $10^4$–$10^5$.

21. **We do not claim novelty for the framing, the estimators, or the action space.**
    Conceded to prior work and cited rather than re-derived: prompt-as-treatment as a framing;
    DTR/Q-learning over a natural-language action space (arXiv:2502.17538); longitudinal causal
    inference over sequences of text features (arXiv:2605.07834); single-period text-treatment
    identification (arXiv:2410.00903); per-context off-policy prompt policy learning
    (arXiv:2504.02646); neural SNMM/blip estimation (DeepBlip, arXiv:2511.14545); and orthogonal
    doubly robust Q-learning (DRQ-learner, arXiv:2509.26429). What is claimed is the
    prospectively sequentially randomized, propensity-logged design, the coarsening stated as
    identification, the branch-sampled ground truth, and the boundary results reported as
    results.

---

---

## 13. What is actually new here

**Read this section against `docs/positioning.md`.** After the literature audit, the surviving novelty of this project is **the design**, not the framing and not the estimators. Novelty is *not* claimed for: prompt- or instruction-as-treatment (Wang et al., AAAI-25; Frauen et al., KDD 2026; CPO arXiv:2602.01711); DTR / Q-learning over a natural-language action space (Zhang, Wang & Dhillon, arXiv:2502.17538); longitudinal causal inference over sequences of text features (Nakamura & Imai, arXiv:2605.07834); single-period identification for text-valued treatments (Imai & Nakamura, arXiv:2410.00903); per-context off-policy prompt policy learning (Kiyohara, Cao, Saito & Joachims, arXiv:2504.02646); neural SNMM / blip estimation (DeepBlip, arXiv:2511.14545); or orthogonal doubly robust Q-learning (DRQ-learner, arXiv:2509.26429). These are **cited and used, not re-derived**. "We are the first to formulate multi-turn prompting as a DTR" is **false and is withdrawn wherever it appeared**; "a causal critic instead of a correlational reward model" is CPO's published rhetorical position, not ours.

**The one claim this section leads with**, because it is the one the audit found clean as of 2026-09-19: *prospective sequential randomization of an in-conversation intervention with logged, exactly known propensities, on a resettable receiver with a programmatic outcome, validated against branch-sampled Monte Carlo ground truth (T27).* Everything in (b) below is subordinate to that; several items in (b) are accounting identities rather than contributions and are labelled as such.

### (a) Classical results we merely instantiate
The g-formula and time-varying confounding (Robins 1986, 1997); the extended g-formula and stochastic/modified treatment policies (Robins–Hernán–Siebert 2004; Richardson–Robins 2013; Muñoz–van der Laan 2012; Haneuse–Rotnitzky 2013; Young–Hernán–Robins 2014; Díaz–Williams–Hoffman–Schenck 2023); incremental propensity score interventions (Kennedy 2019); random dynamic strategies (Robins 1986; Murphy–van der Laan–Robins 2001; Didelez–Dawid–Geneletti 2006; Dawid–Didelez 2010); MSMs and sequential IPW (Robins 1998, 2000; Hernán–Brumback–Robins 2000); SNMMs, blips and g-estimation, with exceptional-law non-regularity (Robins 1994, 1997, 2004; Vansteelandt–Joffe 2014; Chakraborty–Murphy–Strecher 2010; Laber et al. 2014); optimal DTRs, advantages and value-regret bounds (Murphy 2003, 2005; Qian–Murphy 2011; Moodie–Richardson–Stephens 2007; Chakraborty–Moodie 2013; Tsiatis et al. 2019); iterated-regression DR, TMLE, one-step estimators, orthogonality and cross-fitting (Robins–Rotnitzky–Zhao 1994; van der Laan–Robins 2003; Bang–Robins 2005; van der Laan–Rubin 2006; Luedtke et al. 2017; Rotnitzky–Robins–Babino 2017; Chernozhukov et al. 2018; Luedtke–van der Laan 2016); OPE, sequential importance sampling and the curse of horizon (Precup–Sutton–Singh 2000; Jiang–Li 2016; Thomas–Brunskill 2016; Liu et al. 2018; Xie–Ma–Wang 2019); HCOPE / safe policy improvement and empirical Bernstein (Ionides 2008; Thomas–Theocharous–Ghavamzadeh 2015; Swaminathan–Joachims 2015; Maurer–Pontil 2009); Rényi/ESS accounting for importance weights (Cortes–Mansour–Mohri 2010; Metelli et al. 2018); the performance-difference and simulation lemmas (Kearns–Singh 2002; Kakade–Langford 2002); state-abstraction value loss (Li–Walsh–Littman 2006); KL-regularized / soft dynamic programming (Todorov; Ziebart; Peters et al.; Schulman et al.); multiple versions of treatment, compound treatments and ambiguous manipulation (Spirtes–Scheines 2004; Hernán–VanderWeele 2011; VanderWeele–Hernán 2013); balancing scores (Rosenbaum–Rubin 1983); collider/selection bias (Hernán–Hernández-Díaz–Robins 2004); censoring, per-protocol effects and IPCW (Robins–Finkelstein 2000; Hernán–Robins); competing events — total effects, controlled direct effects, separable effects (Young–Stensrud–Tchetgen Tchetgen–Hernán 2020; Stensrud et al. 2022; Robins–Richardson 2010); truncation by death and principal strata (Rubin 2000; Zhang–Rubin 2003); prioritized outcomes and win ratios (Finkelstein–Schoenfeld 1999; Buyse 2010; Pocock et al. 2012; Mao 2019; Oakes 2016); cross-world non-identification and transport bounds (Makarov 1981; Rüschendorf 1982; Fan–Park 2010; Firpo–Ridder); prophet inequalities (Krengel–Sucheston; Hill–Kertz; Correa et al. 2017); inference on winners (Andrews–Kitagawa–McCloskey); micro-randomized trials (Klasnja et al. 2015; Boruvka et al. 2018); temporal exactness for adaptive designs (Bojinov–Shephard 2019); prediction-powered inference (Angelopoulos et al. 2023); SIR (Rubin 1987/88); weak-overlap irregularity (Khan–Tamer 2010; D'Amour et al. 2021); constrained MDPs (Altman 1999).

One correction to how this list is *used*: Makarov (1981) and Rüschendorf (1982) are not merely adjacent background. Because T13 reduces the lexicographic comparison to a **scalar** $u(Z)$, and $\mathbf 1\{v>w\}=\mathbf 1\{v-w>0\}$, those bounds supply the **closed form** for the sharp identified set of a matched win probability under fixed marginals; the earlier blanket statement that only an optimal-transport LP is available is withdrawn in §7 P12, and the LP is reserved for the multi-level, non-scalarizable comparison (§15 item 6). We instantiate a classical result here that the document previously said did not exist.

### (a2) Recent language-action causal work we cite and do not re-derive
The concession table in `docs/positioning.md` is part of this section by reference. In particular: the **estimands** vocabulary for AI-mediated conversation (arXiv:2607.03597), **user-side text as a time-varying treatment** in human–LM collaboration (CausalCollab, arXiv:2404.00207), a **learned cost-penalized stop rule** for interaction (arXiv:2512.04068, arXiv:2510.25441), and **turn-level attribution auditing** (arXiv:2605.26655, arXiv:2609.05882) are all prior art. The stopping deliverable this document ends up recommending (§6 T19(e), §7) therefore claims novelty only in *how it is identified and validated* — prospective randomization, exactly known propensities, resettable branch-sampled ground truth — and not in the idea of learning when to stop.

### (b) Real technical contributions
1. **The exact second-moment recursion** for sequential weights and its squared-kernel measure-change form, correcting the naive product-of-$\chi^2$ identity; with the **override-depth bound** $E[W^2]\le\delta^{-d}$ and $n_{\rm eff}\ge n_{\rm clusters}\delta^{d}$ (P5). *Demoted to a useful accounting identity, not a contribution:* it is the tower rule applied to $\prod_t w_t^2$ plus a one-line change of measure, and it belongs in §4 as bookkeeping. Numbers, at the frozen design and the honest inference unit: the feasible floor is $\delta=1/8=0.125$ over the $m_G=8$ randomized non-`STOP` arms ($m_G\delta=1.000$, attained with equality; $\delta\ge0.25$ is **infeasible** for $m_G>4$ and is withdrawn), so $E[W^2]\le8$ at $d=1$ and $\le64$ at $d=2$, and since the frozen design has $D=2$ decision points, $d=2$ **is** full depth. At $n_{\rm clusters}=176$ task families this gives $n_{\rm eff}\ge$ **176 / 22 / 2.75** clusters at $d=0,1,2$ (at the pool ceiling 230: 230 / 28.75 / 3.59). The identity's real content in this project is negative: a depth-2 off-policy evaluation here has an effective sample size of **under three clusters**.
2. **The curse of description length**: $n_{\rm eff}\le n\,e^{-\bar\kappa\bar m}$ by the autoregressive KL chain rule, and the design principle that target and logging policy may differ only on an $O(1)$-description-length coordinate (P6). *Demoted to a useful accounting identity:* it is monotonicity of Rényi divergences composed with the chain rule, and its conclusion — sequence-level importance sampling over free text is dead — is folklore in the RLHF/OPE literature and is also the audit's constraint 4 (arXiv:2606.05558 measured it with exact per-token log-probs). Retained because the arithmetic is worth printing: at $\bar\kappa=0.05$ per token and $\bar m=400$ tokens, $n_{\rm eff}\le n\,e^{-20}=2.06\times10^{-9}\,n$, i.e. $\le3.6\times10^{-7}$ clusters at $n=176$. The conclusion is unchanged and is why the action is the selector, never the string.
3. **The tilt weight as a scalar observable normalizer** and the consequent **structural simplification of the EIF**, with **exact two-sided double robustness** for a $P$-dependent stochastic intervention (T30, §11.1) — subject to the literature check stated there. *Restated, because the original wording overstated a real result and was contradicted inside T30's own subsection:* what disappears is the need to **integrate** a critic over the action space — the critic is evaluated only at **observed** history–action pairs. It does **not** follow that the action-level text critic disappears: the EIF's residual term involves $\tilde Q_{t+1}(H_{t+1})$ and $H_{t+1}$ contains the realized message, so the critic is action-dependent. T30's own concession stands as the limit of the claim: the soft-optimal recursion still needs a text-conditioned critic at history–action pairs never observed. "The action-level text critic disappears" is **withdrawn**.
4. **The stop/text factorization** under which the language density cancels identically, with path-surprisal variance accounting and the corrected early-stopping estimand (T3, P23). *Two conditions, both now explicit and both load-bearing.* (i) The cancellation requires each $q_k$ to be a kernel in the recorded $H_t$ alone, so generators must be invoked **statelessly** (A5, as rewritten): no carried KV cache, persona or scratchpad memory, surviving reasoning tokens, persistent tool or retrieval handle, or server-side conversation id. Any carried state $U_t$ is a function of $K_{1:t-1}$, hence post-treatment with respect to earlier selectors and a mediator of them; the $q$ factors then differ between the $e$-law and the $\pi$-law and **do not cancel**, and P2's "assign generator $k$" no longer names a fixed kernel. This is the *default* implementation of a multi-turn LLM user, so it is barred by assumption and **verified** (input-provenance prompt hash, fresh-context assertion, out-of-order replay; §16 item 1). (ii) The corrected early-stopping estimand requires the stopping time to be a stopping time of the **policy-observable** filtration $\mathcal F_t^O=\sigma(\varphi_t(H_t))$, which excludes $\psi$ and every hidden-test-derived quantity (R3); a rule reading the grade is the prophet benchmark (P22), not a policy.
5. **Rank-transform reduction** of a prioritized terminal outcome over an **endogenous-horizon** regime to a bounded pseudo-outcome, with the DR/EIF assembly, tie handling and the second-moment (not fourth-moment) $U$-statistic condition (T13, T14). *Demoted to a secondary reporting device, and conditional on a freeze.* The construction reuses T8a/T9 verbatim only because $G_0$ is **frozen on an independent pre-registered reference sample** — the sibling project's completed 4,488-episode log on the identical task pool (`tasks_sha256` verified), hashed before any outcome of this run is examined — which makes $\tilde Y=2G_0(u(Z))-1$ a fixed known measurable transform at zero GPU cost and zero clusters; the price is that the reported win probability is **reference-dependent** on a frozen reference rather than on a concurrent $\pi_0$. With $\hat G_0$ estimated on the analysis sample instead, $\tilde Y$ carries an outcome-law nuisance, units become dependent, exact unbiasedness is replaced by double robustness with a second-order remainder, and the stop-arm value is no longer known even in the T8a sense; that route is retained in §7 as what *would* be required and is not used confirmatorily. It is demoted rather than headlined because on this outcome it is nearly degenerate: $Y$ is a binary hidden-test verdict, $N\in\{1,2,3\}$ at $T_{\max}=3$, cost is monotone in $N$ up to token noise, the ordered quotient has about six cells, the tie mass is the majority of pairs, and the transform **shrinks** an effect already at 0.015–0.030. The primary objective is the priced scalar $E[Y^\pi-\lambda C^\pi]$ at the pre-registered $\lambda=0.01$ per turn, with degradation reported separately (audits A3) and the tie mass reported.
6. **Rao–Blackwellized marginal weights over recorded latent randomization (P4) — WITHDRAWN as a technical contribution; retained as an opt-in, per-generator variance device for IPW only.** We claimed a free variance reduction from marginalizing the selector out of the weight. In the frozen design the generators are deterministic template renders with a uniformly drawn index over 3 frozen templates using the episode seed, so $q_k$ is a point mass given the recorded index and distinct $k$ produce distinct texts: numerator and denominator each collapse to one term, **the marginal weight equals the selector ratio exactly and the variance reduction is identically zero**. Where generators are LM-based, computing $q_k$ for the $m_G-1=7$ untaken arms costs $m_G=8$ teacher-forced scoring passes per turn on the realized message, using the *sampling-time truncated* distribution — a per-turn cost the document never priced, which competes directly with the branch budget (frozen $n_b=3$) against the 20,000-call / 9.3-hour affordability ceiling. So P4 is an identity with no gain in the primary design and non-free in the only design where it bites; it is also incompatible with T9(iii)'s exactly unbiased finite-sum DR (§3, item 2 there), so the selector-level weight is the default everywhere.
7. **Branch-augmented DR** with the corrected two-noise-source variance and the late-budget allocation rule (P10), plus the estimation-versus-benchmarking design dichotomy (P5b). Retained as a design statement, with the frozen numbers attached rather than an aspirational branch budget: replicates are frozen at $n_b=3$, the per-state Monte Carlo SE of a branch-sampled blip is **up to 0.29**, and the fitted within-class template SD is $\hat v\approx0.08$. The dichotomy — wide-and-shallow for estimation, narrow-and-deep for benchmarking — is what the frozen allocation implements; the per-state precision it delivers is reported with every branch-sampled quantity, and no claim here rests on a deeper slice than the one that is frozen.
8. **The debiased validation risk** with real oracle labels and offset cancellation for rankings (T27). This is the item that carries the surviving design claim: a resettable receiver plus a programmatic outcome lets us grade our own estimator against Monte Carlo truth, which almost no applied causal paper can do. Its scope is the mixes we chose (see (c)), and it is a validation asset, not a certificate.
9. **The $\Omega(K^T)$ query lower bound** (T26). *Demoted to a remark, and its inference withdrawn.* The needle-in-a-haystack construction lower-bounds **exhaustive search over history-indexed regimes with no state abstraction**; it is a textbook argument, and the design does not inhabit that setting, because every nuisance here is modelled on a frozen finite-dimensional summary $\varphi(H_t)$ under which dynamic programming costs $O(K\cdot T\cdot|\mathcal S|)$. The correct statement is: *exhaustive history-indexed search is infeasible, therefore structure must be imposed, and every guarantee downstream is conditional on that structure.* A learned blip estimator does not evade the bound — it **adds a function-class assumption**, which must be labelled an identifying assumption. The claim that the bound is "the formal reason a learned blip estimator is mandatory rather than convenient", and that "structure plus backward induction is the only known way past the barrier", is **withdrawn**: it converted an assumption into a theorem, and it changes no design decision, since no one proposed exhaustive search. What survives is the resettability reading — a resettable oracle converts positivity into a purchased budget — which is a scope statement about cost, not a necessity proof.
10. **The corrected three-term sim-to-real transport decomposition** (T28), with the third term (a history-shift / transport term) stated as **not estimable** from this design's data and reported as an assumption rather than a bound.
11. **The winner's curse of optimized stopping** $\Theta(\sigma\sqrt{\log\bar K})$ and the horizon-bias threshold shift $\lambda\to\lambda-\beta$ (P24). *Scope corrected.* The primary outcome here is **programmatic** (hidden tests, verifier determinism measured: 1,954 replicate verifications of 597 repeated `(task_uid, sha256(final_code))` pairs, 0 disagreements), so $\sigma=0$ for the primary number and **P24(ii) does not bite on it**. The result applies to judge-scored **secondary** outcomes, where $\sigma>0$, and there it is real and must be corrected for. The quantified-optimism claim is therefore retained as a constraint on secondary reporting and **withdrawn as a statement about the primary endpoint**; the original framing derived its force from a stop-arm value that the *policy* does not see (R3), which is a calibration problem, not a noisy-max problem.
12. **T20 (finite-sample improvement certificate) — WITHDRAWN as a deliverable; retained as a scope statement.** We claimed a corrected linear-in-$M$ certificate rate and that an exactly known language-action propensity makes the certificate genuinely finite-sample valid. The validity claim is true and uninteresting; the **deliverable** is numerically vacuous on this task pool and unaffordable at any gap worth certifying, and the baseline it certified against ($V(e)$) was an artifact of the design's own composition — a $\delta$-floored mixture including the negative-control, placebo and leaky diagnostic arms, so $V(\pi)-V(e)$ is **monotone in the number of deliberately degraded arms** and manufacturable with zero learning. Corrected arithmetic, $n_{\rm clusters}\ge8ML/\mathrm{gap}^2$ with $L=\log(4|\Pi|/\alpha)$: at the only measured headroom (gap **0.046**) this needs $2.4\times10^4$ clusters at $M=1$ and $2.0\times10^5$ at $M=8$, against **176** available (ceiling 230) — $139\times$ and $1{,}110\times$ short — and the smallest gap certifiable at $n=176$ is **0.542** unweighted, or arithmetically impossible ($1.533>1$) for any weighted regime. On compute, $2.4\times10^4$ units is 34 GPU-hours against a 9.3-hour ceiling. The figures $5\times10^4$ and $1.2\times10^4$ conversations, the $\delta=0.25$/$M=16$ arithmetic behind them, the "conversations" inference unit, and the sentence "roughly what a stratified A/B test over the $m$ arms costs" (honest multiple: **50–120×**) are all **withdrawn**. What replaces it: a **paired, family-clustered bootstrap interval** against pre-registered named baselines, with the headline gap against **B4** (measured half-width $\pm0.019$ at $R=8$, MDE 0.027), and B2 (fixed unary retry, the mandatory zero-information arm), single-shot no-feedback, the truncated prophet bound and $V(e)$ as the other denominators.

### (c) Conceptual / framing contributions only
- $\mathrm{do}(S=s)$ on a semantic class is **ill-posed**, not merely unidentified, and this is generic in a language action space; the version mix must be part of the estimand (P1) — and the design can **manufacture** it, which is what removes the exclusion restriction (P2). The manufacture is only as good as its verification: it requires the stateless-invocation guarantee of A5, because a generator carrying state across turns does not name a fixed version mix at all.
- Positivity's two jobs — identification and $\sqrt n$-estimability — must be separated for language actions, and the floor replaced by a **Rényi budget that is a design parameter, not a fact about nature**. With the feasibility constraint stated: a uniform floor over $m_G$ randomized arms requires $m_G\delta\le1$, so the frozen design's budget is $\delta=1/8$ with $m_G\delta=1.000$ — the budget is a design parameter, but it is **bounded above by the size of the action set**, and at $d=D=2$ the purchased budget leaves 2.75 effective clusters. "A design parameter" never meant "a free parameter".
- **The temporal and structural granularity of randomization** is the decisive knob; coarse-in-time randomization buys bounded weights and forfeits within-trajectory contrasts. Override depth is part of that knob and is **not free**: the three entitlement classes $\Pi_0$ (stopping-only, $W\equiv1$), $\Pi_1$ ($W\le8$) and $\Pi_2=\Pi_{\rm cp}$ ($W\le64$, 2.75 clusters) must be named by every claim.
- **Treatment vs censoring vs competing risk is an estimand choice**, and "evaluate at a fixed turn count" silently chooses censoring and moves cost outside the objective. Stated at the frozen horizon: $T_{\max}=3$, $D=2$, $N\in\{1,2,3\}$, cost priced at the pre-registered $\lambda=0.01$ per turn.
- **Separable-effects isolation is enforceable by interface construction — on the receiver side only.** Withholding $A_D$ from the receiver's context guarantees by code that $A_D$ does not enter $M$ directly, and that half is a software guarantee rather than a statistical test. The non-trivial **dismissibility** condition is not: that $A_D$ affects $Y$ only through the continuation event, and affects the message distribution given continuation not at all, is a claim about the **user kernel**, and it is false in the obvious implementation — a displayed cost meter, confidence indicator or progress bar plausibly changes what is written conditional on continuing, hence $H_{t+1}$, hence $Y$; with a simulated intervener, $A_D$ enters that model's whole context and will in general move both its stop head and its message content unless the intervener is split into two calls with disjoint contexts, at which point the estimand is relative to that artificial split. So that condition is **assumed, numbered and falsifiable** (§7 T25(d)), with the available test being: branch on $A_D$ at fixed $A_Y$ in the harness and test invariance of the next-message distribution given continuation. The phrase "in medicine the decomposition is hypothetical; here it is code" is **withdrawn except for the receiver-side half**.
- **Leakage level is a coordinate of the randomized action space; the realized leakage score is post-treatment and is never conditioned on.** The earlier "leakage is a pre-treatment design coordinate, not a mediator" is **withdrawn as a category error**: $\tilde A_t$ *is* the treatment, so any function of it is post-treatment, and by the old criterion the treatment itself would be pre-treatment. What is identified is contrasts across randomized $(g,\lambda)$ pairs — generator class at a **built-in** leakage level, verified offline against the pinned library before the freeze — including the $\lambda$ main effect and the $g\times\lambda$ interaction, with no conditioning. What is not identified is the effect of $g$ holding *realized* $\hat\Lambda$ fixed (a mediator-controlled direct effect), any contrast conditioning on $\hat\Lambda$, and natural direct/indirect leakage effects (§12 item 6). "Bin it and stratify randomization on the bin" is **not implementable** (the bin is unknown until the action is drawn) and capping realized $\Lambda$ is rejection sampling, which replaces $q_k$ by a truncated kernel with an unknown normalizer; $\hat\Lambda$ is a **fidelity measurement** only, and its bias direction is known — it *understates* leakage, which makes any leakage-controlled contrast look larger.
- **The same category error, the same fix, for message length and position.** Severity and specificity classes differ systematically in token count, and the feedback message is always the most recent context, so a long message pushes the task specification further from the generation point. Both are caused by the randomized selector and are therefore mediators, and "within a $\Lambda$ bin, message length no longer predicts $Y$" is a low-power observational regression on post-treatment variables, not a control. The fix is design-side: re-render the task specification at a **fixed token distance** from the generation point in every arm (padding with inert filler verified at $\hat\Lambda=0$), plus a separate pre-registered length-calibration block ($190$ tasks × 3 arms × 1 turn $\approx570$ calls $\approx0.27$ h) including a filler-only arm, with the class effect reported **net of the measured length main effect**. Without that block, the class effect is confounded with length by design-mediation, and the document says so.
- **The two histories, and the honest shape of the stop arm.** $H_t^A$ (analyst/harness) contains the programmatic grade $\psi$; $H_t^O=\varphi_t(H_t)$ (policy-observable) excludes $\psi$ and every hidden-test-derived quantity. The asymmetry that survives is: *the `STOP` arm's causal nuisance is nil* — $Q_t(H_t^A,\texttt{STOP})=\psi(H_t)$ exactly, with no nuisance model, no Monte Carlo variance, no positivity requirement and zero GPU — *and its prediction problem is the hardest estimation problem in the design*, because the deployable rule must use $E[\psi(H_t)\mid\varphi_t(H_t)]$, an unknown regression whose measured difficulty is on record (the visible verdict is one bit and absent on 20.8% of the informative pool; the sibling loop's self-check stopped on **50.4%** [0.479, 0.528] of all failures). Accordingly "the stopping decision is a scalar blip with a **known** stop-arm value", "the endogenous horizon costs nothing extra" and "no medical analogue" are all **withdrawn**: the horizon costs the calibration of $E[\psi\mid\varphi]$, and the medical analogue of that is ordinary prognostic modelling. The **+4.6 pp** of headroom is the value of the **oracle**, so the oracle value is never reported alone — always paired with the implementable $\hat p$-rule value.
- **Adjustment changes reported effects a lot and decisions a little, and this document is committed to that split.** The confounding structure is real and the reported-effects claim is large (unadjusted comparisons inverted the true class ordering in 0 of 40 replicates), but the decision-level claim is already evidence-against in our own premise checks: a correlational critic conditioning on the full observed state recovered the exact optimal regime in 39 of 40 replicates, a swept latent confounder moved the logged-minus-randomized regret gap by at most 0.030, and known-propensity IPW repaired the residual only partly and non-monotonically. The dominant decision-level error was **myopia**, which loses under randomization too and is therefore not a confounding failure at all. The framing contribution is the split itself, not the causal critic: the machinery is motivated on **horizon-aware valuation and a known-propensity randomized design**, and a non-myopic *correlational* critic is pre-registered as the baseline this framework must beat.
- **Resettability converts assumption-validity into estimable variance components and supplies ground-truth benchmarks — but only for the mixes we chose**, so a small dispersion number from a near-paraphrase generator is self-flattery.
- **Off-policy evaluation must justify itself** when the environment is resettable — and on this project it does not, for the deliverable the evidence supports. The measured headroom is entirely in stopping, stopping-only regimes sit in $\Pi_0$ with $W\equiv1$, and the harness runs every trajectory to $T_{\max}$ and records $\psi(H_k)$ at every $k$, so their values are **unweighted means on recorded trajectories**: no importance weights anywhere. The off-policy apparatus is secondary, and full-depth regimes must be valued by on-policy rollout.
- The KL-regularized policy improvement the field already performs *is* the optimal MTP inside a trust region — a causal reading of an existing practice. This is a reading, not a result, and it inherits the tilt-budget feasibility arithmetic of §4 rather than licensing an unbounded trust region.

**Net claim.** One design contribution (prospective sequential randomization with logged exact propensities on a resettable, programmatically graded receiver, validated against branch-sampled truth), a coarsening-as-identification argument stated as such with the string-level effects explicitly disclaimed, a set of accounting identities that price what the language action space costs, and a set of **boundary results reported as results** — where adjustment moves reported effects but not decisions, where horizon dominates confounding, repair 0.239 against degradation 0.162, and the 0.046 that oracle stopping is worth. Two advertised deliverables (the improvement certificate T20, the free variance reduction P4) are withdrawn in place, and three further claims (the $\Omega(K^T)$ necessity argument, the known stop-arm value, the action-level-critic-free EIF) are weakened to what they actually support.

---

---

## 14. Errata: reviewer findings and their resolution

**This section supersedes the previous §14.** The old errata mapped the five route
drafts' reviewers onto the synthesis. It is retired: its content is subsumed by the
numbered results themselves, and one of its headline resolutions was wrong — "the
canonical-message value is point-identified but not *regularly* estimable" is a
mischaracterization (finding 60 below), so the old §14's claim to have resolved the
Route-A contradiction "by the identified-but-irregularly-estimable reading" is
withdrawn along with the phrase.

What this section maps instead is the adversarial review of the synthesis document:
**90 findings — 20 fatal, 44 major, 26 minor** (`work/theory/attack_findings.json`,
cited below by their zero-based index in that file, which is the only identifier they
carry). Every fatal and major finding is tabulated with its disposition. Nothing is
dropped: where a result was broken it keeps its number and its position and is
rewritten as a withdrawal, and where a defect could not be fixed it is conceded in
the reviewer's own terms.

**Disposition vocabulary.**

| tag | meaning |
|---|---|
| **FIXED** | the claim is repaired and the repaired claim is true as stated |
| **CONCEDED** | the defect is real and unfixable here; the text now states it in the reviewer's terms |
| **WITHDRAWN** | the result is retired in place, number kept, with what was claimed, why it fails, and what replaces it |
| **DEMOTED** | retained but reclassified (deliverable → diagnostic, primary → secondary, theorem → remark) |
| **NARROWED** | the claim survives on a strictly smaller scope |

Eleven results are withdrawn, demoted or weakened in place; the register is §14.5.
Numbers that changed are in §14.4. Conflicts the section repairs could not resolve
alone are resolved in §14.6.

---

### 14.1 The nine cross-cutting repairs, in one line each

These are the decisions from which most individual repairs follow. R-numbers are the
binding repair specification's.

1. **R1 — the positivity floor.** $\delta\ge0.25$ is arithmetically infeasible: a
   uniform floor over $m_G$ arms needs $m_G\delta\le1$. Frozen: $m=9$ actions,
   $m_G=8$ randomized non-`STOP` arms at $e=1/8$, $\delta=1/8=0.125$ attained with
   equality. `STOP` is exempt — its potential outcome is $H_t^A$-measurable, so
   positivity holds by degeneracy.
2. **R2 — override depth is an entitlement class, not a knob.** $\Pi_0$ (stopping-only,
   $W\equiv1$, $M=1$, 176 clusters), $\Pi_1$ ($M=8$, 22), $\Pi_2=\Pi_{\rm cp}$
   ($d=D=2$, $M=64$, **2.75 clusters**, on-policy rollout only). Every claim names
   its class. The only measured headroom is in stopping, which sits in $\Pi_0$ and
   needs no importance weights at all.
3. **R3 — two histories.** $H_t^A$ (analyst/harness, contains $\psi$) and
   $H_t^O=\varphi_t(H_t)$ (policy-observable, excludes $\psi$ and every
   hidden-test-derived quantity). Every "known" in the document now says which.
4. **R4 — the improvement certificate is withdrawn as a deliverable** and retained as
   a scope statement, with the corrected bound $n\ge8ML/\mathrm{gap}^2$,
   $L=\log(4|\Pi|/\alpha)$, and the library split that removes $V(e)$ from the role of
   baseline.
5. **R5 — leakage, length and position are descendants of the treatment.** Leakage
   *level* becomes a randomized action coordinate; realized $\hat\Lambda$ is a fidelity
   measurement that is never conditioned on.
6. **R6 — $G_0$ is frozen on an independent existing log** (the sibling project's
   completed 4,488-episode run), which is what buys the verbatim reuse of T8a and T9,
   at the price of a reference-dependent win probability.
7. **R7 — generators must be stateless**, verified byte-exact, or T3's density
   cancellation fails rather than merely becoming uncomputable.
8. **R8 — the policy class is a $\sigma$-algebra restriction.** $\varphi$ is not
   sufficient, so backward induction returns $\pi^{\rm greedy}$, not
   $\arg\max_{\Pi_{\rm cp}}V$. The reported object is $\hat\pi$ over a pre-registered
   finite $\Pi$ with $|\Pi|=8$ declared in §16 item 16.
9. **R9 — the i.i.d. unit is the task instance**, $n_{\rm clusters}=176$ families,
   and the primary route is the paired on-policy family-clustered contrast (E0), not
   off-policy weighting.

---

### 14.2 Fatal findings (20)

| # | target | disposition | what was done | where |
|---|---|---|---|---|
| 0 | A6 floor $\delta\ge0.25$; P5, T20(d), §16.3, §0.3 | **FIXED** | Feasibility constraint $m_G\delta\le1$ written *into* A6; $\delta=1/8$ with $m_G\delta=1.000$; $\delta\ge0.25$ withdrawn as infeasible; every dependent recomputed ($E[W^2]\le8$ at $d=1$, $\le64$ at $d=2$; the figure 16 is gone). The reviewer's alternative repair (a floor on $\mathrm{supp}(\pi)$ only, $\delta\ge1/(2|K|)$) was **not** adopted: a uniform $1/8$ meets the feasibility objection exactly and needs no support-restricted assumption. | §2 A6, §4 P5, §6 T20(a)(b), §10 A6 row, §16 item 3, §0.3, §12 |
| 1 | T20(c)–(d): $V(e)$ as baseline | **FIXED + WITHDRAWN** | Library split into evaluated $\{A_0..A_5\}$ and diagnostic $\{A_6,A_7,A_8\}$; the diagnostic arms are barred from every $\pi$ and every reported baseline; $V(e)$ demoted to a diagnostic denominator on the evaluated stratum, with the statement that a gap against the full mixture is **monotone in the number of deliberately degraded arms** and manufacturable with zero learning; the certificate itself withdrawn. | §6 T20(c)(d), §10 D1, §16 item 14, §13(b)12, §0.1–§0.2 |
| 2 | T16 "leakage as design, not mediation"; A12; §16.7 | **FIXED** | Leakage *level* becomes a coordinate of the randomized action space: pinned $q_{(g,\lambda)}$ built to declared levels and verified offline before the freeze, the pair jointly randomized at $1/8$; realized $\hat\Lambda$ is fidelity-only; "no post-treatment conditioning" deleted; rejection sampling on realized $\Lambda$ barred confirmatorily. | §8 T16, §2 A12, §16 item 7, §13(c), §15 item 15 |
| 3 | T8 vs A11(d), P24(ii)–(iii), §16.6 | **FIXED** | The two-history split; T8 split into **T8a** (analyst: $Q_t(H_t^A,\texttt{STOP})=\psi$ exactly, no nuisance, no positivity, zero GPU) and **T8b** (policy: $E[\psi\mid\varphi_t]$ is an unknown regression and the hardest estimation problem in the design); A11(d) becomes a $\varphi$-exclusion information-set restriction; §16 item 6's two-channel requirement replaced. | §1, §2 A11, §4 T8, §8 P24, §16 items 5–6, §10 D1 |
| 17 | T20(d) budgets and vacuity | **WITHDRAWN** | T20 retired as a deliverable in place, retained as a scope statement, with the corrected formula and three tables: required $n$ by gap, required-vs-available at 176/230, and the smallest certifiable gap (**0.542** unweighted; 1.533 at $M=8$, which exceeds the outcome range and is impossible at any $n$). Replaced by E0's measured $\pm0.019$ half-width and MDE 0.027. | §6 T20, §0.2.3, §10 D1, §13(b)12, §16 item 14, verdict |
| 18 | A6 (duplicate of 0) | **FIXED** | as 0 | as 0 |
| 19 | T8 stop-arm "known" (D1 row, §0.2.5) | **FIXED** | as 3 | as 3 |
| 20 | T19; "a learned blip estimator is mandatory"; §5 state representation | **WITHDRAWN as a guarantee** | The $L^1$ bound $V(\pi^\star)-V(\hat\pi)\le E\lvert\hat\gamma-\gamma\rvert$ is conceded numerically vacuous at every achievable critic precision (per-state MC SE up to **0.29** at $n_b=3$, $\hat v\approx0.08$, null-blip mass 0.156/0.334/0.406, repair 0.239 vs degradation 0.162, against **0.046** of headroom) and replaced by the margin form $E[\lvert\gamma\rvert\mathbf 1\{\lvert\hat\gamma-\gamma\rvert\ge\lvert\gamma\rvert\}]$ reported with the measured $\lvert\gamma\rvert$ distribution. "Mandatory" withdrawn (see 42). A trained free-form generator is declared outside every guarantee in the document. | §6 T19, §0.3, §5, §9 T26(c) |
| 31 | A6 (duplicate of 0) | **FIXED** | as 0 | as 0 |
| 32 | T20(d) "roughly what a stratified A/B test costs" | **FIXED** | Sentence deleted; honest multiple stated as **50–120×**, with the compute comparison (34 and 273 GPU-hours at the spec's throughput, against the 20,000-call ceiling). | §6 T20(d), §0.2.3 |
| 33 | §1 Units; §5 folds; §4 and §6 arithmetic | **FIXED** | The i.i.d. unit is the **task instance (task text only)**; (task × seed) withdrawn in place; seeds, branches, turns, templates, paraphrases and the 1,520 paired units are within-cluster; $n_{\rm clusters}=176$ families with a pool ceiling $\approx230$ (3B) / $\approx100$ (7B); "conversations" as a unit withdrawn everywhere. | §1 Units, §4, §5 folds, §6, §16 items 8 and 12 |
| 34 | T8 (duplicate of 3) | **FIXED** | as 3 | as 3 |
| 50 | A6 (duplicate of 0) | **FIXED** | as 0 | as 0 |
| 51 | override depth in P5, T19, D1 row, T20(d) | **FIXED** | The $\Pi_0/\Pi_1/\Pi_2$ entitlement split with $M=1/8/64$ and $n_{\rm eff}=176/22/2.75$; "bounded here by design" restated as bounded by $\delta^{-d}$ at the regime's own depth, i.e. 64 for full depth — an advantage over *unbounded* ratios, not a small constant. | §4 P5, §6 T19/T20, §10 D1, §16 items 3/8/15, §0.3 |
| 52 | T13/T14 "apply verbatim"; A17 | **FIXED** | $G_0$ frozen on the sibling project's completed 4,488-episode log (identical `tasks_sha256`, verified) and hashed **before any outcome of this run is examined**, so $\tilde Y$ is a fixed known measurable transform and T8a/T9 do apply verbatim. Option (ii) (on-sample $\hat G_0$) retained as what would otherwise be required, with the two-term EIF named as the statement that T9 does *not* apply verbatim. | §7 T13/T14, §2 A17, §16 item 2, §15 item 6, §5 E5 |
| 68 | A6 (duplicate of 0) | **FIXED** | as 0 | as 0 |
| 69 | T3 proof; A5; P2 | **FIXED** | A5 rewritten to require **stateless invocation** (fresh process, no KV cache, persona, scratchpad, surviving reasoning tokens, tool handle, server-side conversation id); the conditional-independence requirement added to T3's cancellation step with the statement that carried state is post-treatment w.r.t. earlier selectors and the $q$ factors **do not cancel**; three verification tests plus the enlarged-history consequence; the D2 chain-of-thought line corrected (true for a within-turn scratchpad, false for cross-turn state). | §2 A5, §3 T3/P2, §10 A5/A7/A9 rows and D2, §16 item 1 |
| 70 | §1 Estimands; T8; §5 state representation; T20(d) | **FIXED** | $\Pi_{\rm cp}$ defined as the set of $\mathcal F_k^O=\sigma(\varphi_k(H_k))$-measurable regimes valued in $\mathcal A_{\rm adm}$; $\varphi$ declared **not sufficient**, so no Bellman equation holds on $\varphi$-measurable value functions and backward induction returns $\pi^{\rm greedy}$; **A19b is not assumed**; the reported object is $\hat\pi=\arg\max_{\pi\in\Pi}\hat V$ over a pre-registered finite set with $\boxed{\lvert\Pi\rvert=8}$ declared in §16 item 16 ($L=6.461$; 8.987 at 100, ×1.39); the missing covering-number bound for the infinite class is conceded. "The optimal regime" reserved for $\arg\max_{\Pi_{\rm cp}}V$, which is not reported. | §1, §4 T8, §5, §6, §10, §16 item 16, verdict |
| 71 | T13/T14 (duplicate of 52) | **FIXED** | as 52 | as 52 |
| 72 | T8; A11(d); §8 requirements; P24(ii) (duplicate of 3) | **FIXED** | as 3 | as 3 |

---

### 14.3 Major findings (44)

| # | target | disposition | what was done | where |
|---|---|---|---|---|
| 4 | A2/A8, §16.3 "one primary axis", T16 length check | **FIXED + CONCEDED** | Fixed prompt geometry in *all* arms (task spec re-rendered at a fixed token distance, inert filler verified at $\hat\Lambda=0$); a separate pre-registered length-calibration block (2 token budgets per class plus a filler-only arm, $\approx570$ calls); class effects reported net of the measured length main effect. The within-$\Lambda$-bin length regression is withdrawn as a low-power observational remedy, and the text **concedes** that without the block the class effect is confounded with length by design-mediation. | §8 T16 companion, §2 A2/A8, §16 items 1c and 7.6 |
| 5 | $\Lambda$ via a task-blind placebo solver | **FIXED** | $\Lambda$ redefined as conditional information (log-likelihood gain of a fixed reference receiver on the reference solution given $(H_t,\tilde A_t)$ vs given a null message); task-blind scorer withdrawn; the "unsigned" caveat corrected to a **signed** direction ($\hat\Lambda$ understates leakage, inflating leakage-controlled contrasts); dynamic range validated on a planted set; answer-withholding promoted to an architectural invariant. | §8 T16, §2 A12, §16 items 1b and 7.4, §15 item 15 |
| 6 | P18(d) negative control; §16.10; §9 closing | **WITHDRAWN + replaced** | The politeness-style control has no valid null in this document's own framework, so it is retired in place and replaced by two controls whose truth is known by construction: **(d.i)** a hash-verified withheld-channel arm (software-verifiable zero on $Y$, zero receiver calls, and its statistical form audits the *pipeline* at MDE 0.027), and **(d.ii)** $A_8$ `PATCH` read as the measured ceiling and leakage upper anchor. "A run that does not report (a)–(d) is not an experiment" weakened to a per-item statement of what each can and cannot detect. | §9 P18(d) and closing, §16 items 10–11 |
| 7 | horizon-invariance calibration test vs P15(f) | **WITHDRAWN + replaced** | The test has exactly zero power under an artifact-only interface (byte-identical input). Replaced by estimating $\beta$ directly — regress the judge score on artifact length and style features within strata of identical programmatic content signature — plus mandatory reporting of $\beta/\lambda$ and of the artifact length distribution by horizon arm. For the programmatic primary, $\beta=0$ by construction. | §8 P24 requirements, §16 item 5 |
| 8 | §12.10 contamination "only attenuates" | **FIXED** | Amended to: contamination attenuates **content** blips and **inflates** stop-arm advantages and cost-priced gaps, so the headline was anti-conservative under the document's own objective. Primary numbers on a pre-registered uncontaminated stratum with the contaminated stratum shown separately; a per-task contamination score (turn-1 single-shot pass rate) becomes a stratification variable, not a post-hoc report; the distortion of $G_0$ through $C$ and $N$ is stated. | §12 item 10, §16 items 3 and 13 |
| 9 | T27 selection over $L$ learners on the deep slice | **FIXED** | Ranking-half / reporting-half split, or an AKM/Bonferroni-corrected interval, with $L$ and the spread of $\hat R$ across candidates reported. | §9 T27, §5 P5b, §16 item 4 |
| 10 | deep slice vs A1 hygiene and A13 | **FIXED + CONCEDED** | Interleaved expansion across task instances with cooldown, randomized expansion order applied to the deep slice too, a fixed-prompt canary battery per block, the duplicate-arm check powered on the deep slice, and the rule that $\hat v$ and $\hat R$ are **unusable** if the discrepancy exceeds $\hat v$. The "verify caching changes latency and not tokens" check is withdrawn as non-diagnostic, and the text concedes that client-side one cannot rule out prefix-cache or batch numeric coupling. A1 regraded BC → **A** with a pre-registered drift diagnostic. | §9 P18(c), §2 A1/A13, §10 A1/A13 rows, §16 items 4 and 12 |
| 11 | T13/T14: $G_0$ is a functional, not a regime | **FIXED** | as 52 (the freeze), with $G_0$ added to §15 item 6's open list as the nuisance that *would* have to be estimated. | §7, §2 A17, §16 item 2, §15 item 6 |
| 12 | clustering by model-version epoch vs A2 | **FIXED** | Epoch/model-version clustering withdrawn as incoherent with A2 (a version change makes the estimand *undefined*, not noisy); the SE cluster is the **task family and only the task family**; a detected version change triggers discard-and-report of the affected blocks and two receiver-conditional analyses, not an extra variance dimension. | §5 cross-fitting, §2 A2, §16 item 12 |
| 21 | §0.1 ordering; the missing paired estimator | **FIXED** | **E0 added**: the paired common-random-number on-policy contrast is now the primary estimator (mean over 176 families of family-mean paired differences on 1,520 paired units, paired family-clustered bootstrap, measured half-width $\pm0.019$ at $R=8$, MDE 0.027), with the off-policy apparatus demoted to tree reuse and the observational extensions. The text concedes that **no weighted formula in the document contains the between-task variance component** (Beta(0.348, 0.230)) that pairing removes, and states the 0.31-unpaired vs $\ge0.95$-paired power fact. | §0.1, §5 E0, §4, §6, §16 item 14 |
| 22 | §1/§0.2 confounding narrative | **CONCEDED** | Replaced by an explicit two-deliverable split with the premise-check numbers in the text (0/40 sign recovery; +0.156 reported as +0.005; 39/40 exact optimal regime at regret 0.0010; $\le0.030$ confounding gap; non-monotone IPW repair 0.046→0.033, 0.028→0.028, 0.017→0.019). Causal correction of decisions is demoted to a scoped secondary claim with a **pre-registered expected null**, and a non-myopic *correlational* critic is pre-registered as the baseline the framework must beat. | §1, §0.2, §13(c), §16 verdict |
| 23 | A6/A4: randomizing `STOP` at a floor | **FIXED** | `STOP` exempted: $Y(A_0\text{ at }k)=V_k$ is $H_k^A$-measurable given measured verifier determinism (1,954 replicate verifications of 597 repeated pairs, 0 disagreements), so positivity holds by degeneracy — no randomization, no nuisance model, zero GPU. The earlier reading is withdrawn as wasteful and trajectory-depleting. | §2 A6/A4, §4 P5, §16 item 3, §0.2.5 |
| 24 | T8 exceptional laws; §12 | **CONCEDED + FIXED** | The measured null-blip mass is now in the text (3B: 0.156 below 0.05 success, 0.334 above 0.95, only 0.406 informative), so non-regularity covers roughly half the population rather than a corner. $m$-out-of-$n$ / adaptive intervals become a requirement; the primary estimand is conditional on the first attempt failing, with the already-correct stratum analysed separately for harm. | §4 T8, §12 item 18, §16 item 3 |
| 25 | T27 / P5b / §16.4 affordability | **WITHDRAWN** | $n_b\ge8$ withdrawn as unaffordable ($400\times8\times8=25{,}600$ nodes, above the 20,000-call ceiling by itself; at the $\approx50$ states affordable at $n_b=8$, $\hat R$'s error is $\approx\pm0.05$ and ranks nothing). Frozen $n_b=3$ recorded as a **budget decision**, with its measured consequences, and ground truth usable pooled or on strata, never per state. | §5 P5b, §9 T27, §16 item 4 |
| 26 | P4; §13(b)6; D2 row | **WITHDRAWN as a contribution** | In the frozen deterministic-template design $q_k$ is a point mass given the recorded index and distinct $k$ produce distinct texts, so the marginal weight equals the selector ratio exactly and **the variance reduction is identically zero**; for LM generators it costs $m_G=8$ teacher-forced scoring passes per turn on the sampling-time truncated distribution. Retained only as a pre-registered, per-generator, opt-in device for IPW / clipped IPW. | §3 P4, §10 D2, §13(b)6, §5 T9(iii) |
| 35 | override depth; "the optimal regime" | **FIXED** | as 51 and 70 | as 51, 70 |
| 36 | P5b algebra | **FIXED** | Corrected: $f(n_b)=(\sigma_e^2/n_b+\sigma_m^2)(c_0+n_b)$, $f'=\sigma_m^2-\sigma_e^2c_0/n_b^2$, interior optimum $n_b^\star=\max(1,\sigma_e\sqrt{c_0}/\sigma_m)$. "The budget-optimal design is the widest one ($n_b=1$)" **withdrawn as false in general**, valid only when $c_0\le\sigma_m^2/\sigma_e^2$; the slice width must come from a pilot estimate of $(\sigma_e,\sigma_m,c_0)$. | §5 P5b, §16 item 4 |
| 37 | T16 (duplicate of 2) | **FIXED** | as 2 | as 2 |
| 38 | T13/T14 "scale-free, no hand-tuned $\lambda$" | **DEMOTED** | T13/T14 demoted to a **secondary reporting device**; the primary objective is $E[Y^\pi-\lambda C^\pi]$ at the pre-registered $\lambda=0.01$ per turn with degradation reported separately; the "no hand-tuned $\lambda$" selling point retired; the near-degeneracy stated (binary $Y$, $N\in\{1,2,3\}$, $\approx6$ cells, tie mass the majority of pairs) and the tie mass made a reported quantity. | §7 T13/T14, §2 A10/A17, §16 item 13, §0.2.6 |
| 39 | §0.2.4 "every treatment is a shippable mechanism" | **WITHDRAWN** | Restricted by name to product-side coordinates (`STOP`/continuation, interface and rendering, suggestion policies). Message-generator arms are declared a **measurement device for blips**, not a deployable protocol: no product ships a mechanism that writes its users' turns. | §0.2.4, §10 P31 bullet, §12 item 3 |
| 40 | T20(c) "natural/logging policy" | **FIXED** | "Natural" deleted — in D1 the harness replaced the user, so $e$ is the analyst's own randomizer and the phrase fused two objects. The comparator becomes a pre-registered named baseline; $V(e)$ is a diagnostic denominator on the evaluated stratum. | §6 T20(c), §10 D1, §16 item 14 |
| 41 | confounding narrative (duplicate of 22) | **CONCEDED** | as 22 | as 22 |
| 42 | $\Omega(K^T)$ "mandatory"; T26(c) | **DEMOTED** | T26(c) demoted to a remark and its inference withdrawn: the bound is for exhaustive search over history-indexed regimes with no state abstraction, while the document immediately models nuisances on $\varphi$. A learned blip estimator substitutes a **function-class assumption**, which is an identifying assumption wherever it extrapolates; "mandatory" converted an assumption into a theorem. Numerically inert at the frozen constants ($m_G^D=64$ leaves, which E2 enumerates). | §9 T26(c), §0.3, §13(b)9 |
| 43 | P22 final two sentences | **FIXED** | The unrestricted reporting device is withdrawn in place and replaced by "any stopping rule that **never continues past the natural horizon**"; the 0.745 prophet constant is **deleted** with the reason (dependent, non-stationary adapted process; even independent non-identical gives only 1/2). | §7 P22 |
| 44 | §0.2 item 1 "no untestable assumption" | **NARROWED** | Narrowed to "removes A19 and the positivity obstacle by construction", with A11, A12, A22 and the A1/A2 hygiene channels named as the untestable assumptions that remain. | §0.2 item 1 |
| 53 | A18; T9(i)–(ii); E1 TMLE | **FIXED** | A18 split in place: **A18a** (cross-fitting / fold independence) is required in every design including D1; only **A18b** (the product rate) is vacuous when $e$ is known. The blanket "vacuous in D1" is withdrawn, since it licensed same-sample fits that void the claim it protected. | §2 A18, §5 T9/E1, §10 A18 rows |
| 54 | clustering (duplicate of 12) | **FIXED** | as 12 | as 12 |
| 55 | P5b / §16.4 (duplicate of 36) | **FIXED** | as 36 | as 36 |
| 56 | P12 vs Makarov/Rüschendorf | **FIXED** | The "no closed form available" conclusion is withdrawn as an over-correction: for T13's scalar comparison the sharp bounds are the classical Makarov (1981) / Rüschendorf (1982) bounds, $\sup=1-\sup_t\{F_V-F_W\}^+$, $\inf=\sup_t\{F_W-F_V\}^+$, attained at explicitly constructible shuffle couplings rather than the comonotone one. The transport LP is reserved for the genuinely vector-valued non-scalarizable case; §15 item 6 corrected accordingly. | §7 P12, §15 item 6, §13(a) |
| 57 | T9(v) "OPEN"; §15 item 1 | **WITHDRAWN as open** | The projection of the influence function onto the turn-$t$ treatment tangent space is identically zero, so knowing $e$ does not lower the longitudinal bound for fixed $\pi$: knowing $e$ buys **exact unbiasedness and finite-sample validity, not asymptotic efficiency**. The OPEN flag is narrowed to (a) MSM parameters indexed by $e$, (b) $V(\pi^\star)$ under exceptional laws, (c) the $P$-dependent tilt of T30. | §5 T9(v), §15 item 1 |
| 58 | "$\lambda$ is a budget price, not a hyperparameter" | **FIXED** | Withdrawn as used: $\lambda=0.01$ per turn is **pre-registered**, with the grid $\{0,0.005,0.01,0.02\}$ and a union bound if more than one point is reported; a $\hat\lambda$ read off an estimated (value, cost) frontier is prohibited because it puts a data-dependent estimand inside every fixed-parameter bound. The LP-duality reading survives as an economic interpretation only. | §2 A10, §4 T8, §5 T9, §6 T20, §7, §16 item 13, §15 item 5 |
| 59 | P24(ii) rate; §12.7; §15.7 | **FIXED** | Rewritten as $\Theta(\sigma\sqrt{\log\bar K/n_h})$ with the two cases tabulated at this project's measured numbers: $n_h=1$ gives $\approx0.43$ (branch-selection noise at $n_b=3$, $\approx9\times$ the 0.046 headroom — the one case where the "comparable to real effects" warning is kept), $n_h=176$ gives $\approx0.014$–$0.020$, below the MDE and removed by the selection/evaluation split. P24(i)'s within-unit $E[\varepsilon_\tau]$ presented separately as the bias that does not average away. The draft's magnitude claim is withdrawn as overstated by about two orders of magnitude. | §8 P24(ii), §12 item 7, §15 item 7 |
| 60 | T29 "not regularly estimable"; §12.1 "never estimable"; old §14 | **FIXED** | Replaced by "**regularly estimable at $\sqrt n$ with a semiparametric efficiency bound of order $e^{\Theta(m)}$**", with the AIPW influence function and its variance bound $\propto E[1/g(a\mid X)]$ displayed, and the separate checkable Khan–Tamer condition $E[1/g]=\infty$ named as the one under which genuine irregularity obtains. The $T\rho$ object is relabelled a finite-sample variance band. "Never estimable" corrected. **This also retires the old §14's headline resolution of the Route-A contradiction.** | §11.2 T29, §12 item 1, this section |
| 61 | P10 variance and allocation | **FIXED** | The omitted cross-covariance term is stated, and the design fixed: **disjoint rollout sets** for $\hat Q_t(H_t,K_t)$ and $\hat V_t(H_t)$, under which the additive form is exact and the two allocations separate; with shared rollouts the cross term must be carried before solving the Lagrangian. "Spend the branching budget late" downgraded from a theorem to a measurable condition, with $P(T\ge t)$ and the roll-in cost added. | §5 P10, §13(b)7 |
| 62 | §0.4 Ext-B row; §11.1 | **FIXED** | The price column now carries the binding statistical cost: $\sqrt n$ inference needs a product rate on **two text-history nuisances** (the conditional normalizer $Z_t$ *inside the intervention*, and the tilted critic), unverifiable per §12.12, with **no known-propensity fallback**; with estimated $Z_t$ the exact $P$-martingale property and the $E[w\mid H]=1$ check are only approximate and the anytime-valid certificate is unavailable; $\hat Z_t$ is cross-fitted on the same 5-fold family structure. T30's "exact two-sided double robustness" withdrawn as an estimator property and retained as a property of the population EIF at the true normalizer. | §0.4 Ext-B, §11.1 T30, §15 item 2 |
| 73 | T16; §13(c); A12 (duplicate of 2) | **FIXED** | as 2 | as 2 |
| 74 | $\rho^{\rm mar}$ at stop turns; P4 vs T9(iii) | **FIXED (by a stronger route)** | Sums restricted to $\mathcal K_G$; the stop coordinate carries **no weight at all** rather than the reviewer's separate exact factor, because the recorded trajectories run to $T_{\max}$ and $\psi$ is graded at every turn. P4's marginal weight and T9(iii)'s finite-sum critic-free DR are conceded incompatible: P4 is restricted to IPW / clipped IPW, and E1 uses the selector weight to keep exact unbiasedness. The scope limit of the no-weight argument is stated in §14.6 C4. | §3 P4, §5 T9(iii), §0.1 |
| 75 | T25(d) "in medicine hypothetical, here it is code" | **FIXED + CONCEDED** | Split: the receiver-side non-entry of $A^D$ into $M$ is a byte-exact software guarantee; the **user-kernel dismissibility** condition is named **(ISO-U)**, declared an assumption, declared false in the obvious implementation (a displayed cost meter or progress bar plausibly changes what is written conditional on continuing) and architecturally false for a simulated intervener unless it is split into two calls with disjoint contexts — at which point the estimand is relative to that artificial split. It must be registered in §2 before confirmatory use; the falsification test is given and left explicitly unpriced. | §7 T25(d), §13(c) |
| 76 | P22 sandwich and following paragraphs | **FIXED** | The sup restricted to $\tau\le T$; "identified by consistency alone with no assumptions" replaced by "under A21 and the T8a stop-arm structure"; 0.745 deleted; continuation-extending regimes declared not bounded by this benchmark. | §7 P22 |
| 77 | T28 items 1 and 2 | **FIXED** | Term 1's "**is** estimable from ordinary unbranched logs" withdrawn — real-user logs contain each text history exactly once — and relabelled "estimable only under a stated smoothness/pooling model for $U_t(\cdot\mid h)$", i.e. the same epistemic class as the transport term. $\rho_t$ split into $\rho^U_t$ and $\rho^{\hat U}_t$ with separate estimability statuses. The exact identity and the bound are displayed as two equations so the history-shift term's origin is visible. | §9 T28, §15 item 2 |
| 78 | P21 sharpness; Ext-E row; D3 bullet (i) | **FIXED + CONCEDED** | "Sharp" withdrawn for the unconditional claim: sharp only *given* A7 on the continuation coordinate, and otherwise $\kappa_0(\pi)$ is a **lower bound on the true ambiguity**, because the mechanism that creates the support failure ("satisfied users stop") simultaneously violates A7 and no computation of $\kappa_0$ reveals the shortfall. For the priced objective the width is $\kappa_0\cdot\mathrm{range}(Y-\lambda C)$. Ext-E's "strongest possible identification position" replaced by "the weakest positivity requirement". | §7 P21, §0.4 Ext-E, §10 D3(i), §15 item 8 |
| 79 | T20(a)(b) vs $\tilde Y\in[-1,1]$; T8 well-posedness; E5 | **FIXED** | Sign-definite clipping bias and $E[\min(W,M)^2]\le M$ require a non-negative outcome, so any certificate on the prioritized objective is computed on $(\tilde Y+1)/2\in[0,1]$; and at the recommended $M=\delta^{-d}$ clipping never binds, so the bias is identically zero and the $E[W^2]/M$ bound is vacuous rather than alarming. $\lambda$ handled as in 58. | §6 T20(a), §5 E4/E5, §7 T13, §4 |
| 80 | E2; §1 blip definition; A14 | **FIXED + CONCEDED** | The reference regime is fixed as a **never-stopping continuation regime run to the administrative cap** $\bar K$; the `STOP` blip convention is stated explicitly (absorbing the value of turns that never occur); the index set is $\{k,\dots,\min(T_i,\bar K)\}$ and $U_{it}$ is written with $(Y_i-\lambda C_i)$. A14 is conceded **insufficient**: blips at the `STOP` level are not well defined until the continuation reference and the blip-down convention are stated, and the mean-zero property is re-checked turn by turn. | §1, §5 E2, §2 A14 |
| 81 | T9(i); §0.2.3; E1 | **FIXED** | Exact unbiasedness restated for any $\hat Q$ that is **fold-independent and internally consistent** ($\hat V_t=\sum_k\pi_t\hat Q_t$). "Any outcome model whatsoever" withdrawn; the cross-fitted one-step/AIPW attains it, TMLE is demoted from co-primary to a robustness row and is explicitly not finite-sample exact, and clipped IPW and self-normalized forms are named as not exact. "A cheap badly-calibrated LLM critic carries zero bias risk" narrowed to the value estimate under cross-fitting. | §5 T9(i)/E1, §0.2.3, §10 A18 row |

---

### 14.4 The 26 minor findings

All were dispatched inside the sections that own the text; none was dropped. The ones
whose repair is visible as changed text: **13, 27, 64** (certificate constants,
$L=\log(4\lvert\Pi\rvert/\alpha)$, $\alpha$-split, the retired $5\times10^4$ /
$1.2\times10^4$ budgets — §6); **14, 67(a), 88** (the "adjustment requires coarsening"
sentence — §1; what fails is *within-stratum positivity*, and model-based adjustment
needs no coarsening); **15** (P4 is not a free rule: opt-in, pre-registered, both
weights reported — §3); **16** (the endogenous horizon is exogenous *by construction*
in D1 — §7, §9, §12); **28, 65** (P24(ii) rate and the PPI variance overlap — §8);
**29** (the prioritized outcome's near-degeneracy — §7); **30** (A1 regraded BC → A —
§2, §10); **45, 84** (the reach factor $P(T\ge t)$ in T7's ESS and P10's budget —
§4, §5); **46** (T9(v) — §5, §15); **47** (the §13(b) contribution list demotions);
**48** (the "zero bias risk" qualifier — §0.2); **49** (the judge apparatus rescoped to
secondary outcomes — §8); **63** (T28's third term as a named sensitivity parameter —
§9); **66(a)–(d)** (the $\mathrm{Cov}(w_t^2,\Gamma_{t+1})$ form, T29's $\delta^{-1}$
per-turn factor, T7's ESS, the vacuous second-moment side condition — §3, §4, §5);
**67(b)** ($U_{it}$ with $Y-\lambda C$, plus the boundary asymptotics caveat under an
active isotonic constraint — §5); **82** (P18(a) has no power with degenerate weights —
§9); **83** (P12's supermodularity counterexamples kept, the over-correction withdrawn —
§7); **85** (the random-horizon `STOP` convention and the tilted law — §4); **86**
(the matched-slice condition for $\hat v$ — §5, §9, §16); **87** (T26(a)'s "no
positivity" corrected to positivity-by-construction on the expanded action set —
§9); **89** (T30's two withdrawals — §11).

---

### 14.5 Register of everything withdrawn, demoted or weakened in place

| result | status | replaced by |
|---|---|---|
| **T20** (finite-sample improvement certificate) | **WITHDRAWN as a deliverable**, retained as a scope statement | E0's paired family-clustered bootstrap: $\pm0.019$ half-width, MDE 0.027, headline gap against B4 |
| **T19**'s $L^1$ value-loss guarantee | **WITHDRAWN as a guarantee**, retained as a true but vacuous relaxation | the margin form, reported with the measured $\lvert\gamma\rvert$ distribution |
| **T26(c)** ($\Omega(K^T)$ necessity of a learned blip estimator) | **DEMOTED to a remark**; the inference withdrawn | "structure must be imposed, and every downstream guarantee is conditional on it" |
| **T27**'s absolute debiased risk | **WITHDRAWN as a deliverable** | the same identity as a **ranking** device, with $L$, the spread and the held-out winner's risk |
| **T29**'s "not regularly estimable" | **WITHDRAWN as a mischaracterization** | regularly estimable at $\sqrt n$ with bound of order $e^{\Theta(m)}$; Khan–Tamer condition named separately |
| **T30**'s "the action-level text critic disappears" and "exact two-sided double robustness" | **WITHDRAWN as stated / as estimator properties** | the weaker true statements at the population EIF and the true normalizer |
| **T16**'s "no post-treatment conditioning" | **WITHDRAWN** | leakage level as a randomized action coordinate; $\hat\Lambda$ as fidelity measurement only |
| **T13/T14** | **DEMOTED to a secondary reporting device** | $E[Y^\pi-\lambda C^\pi]$ at $\lambda=0.01$/turn, degradation reported separately |
| **T8**'s "known stop-arm value" / "the endogenous horizon costs nothing extra" / "no medical analogue" | **WITHDRAWN** | T8a (analyst, exact) vs T8b (policy, an unknown regression and the hardest estimation problem in the design) |
| **P4** (Rao–Blackwellized marginal weights) | **WITHDRAWN as a technical contribution** | an opt-in, per-generator variance device for IPW / clipped IPW only |
| **P18(d)** (inert-dimension negative control) | **WITHDRAWN as a falsification test** | the hash-verified withheld-channel null and the $A_8$ ceiling |
| **P22**'s unrestricted prophet device and the 0.745 constant | **WITHDRAWN / deleted** | the device restricted to rules that never continue past the natural horizon; no replacement constant claimed |
| **P21**'s "sharp" width | **WEAKENED** | sharp only given A7; otherwise a lower bound on the ambiguity; width $\kappa_0\cdot\mathrm{range}(Y-\lambda C)$ |
| **$\pi^\star$ over $\Pi_{\rm cp}$** as a reported object | **WITHDRAWN as a deliverable**, retained as a definition | $\hat\pi$ over a pre-registered $\Pi$ with $\lvert\Pi\rvert=8$ |
| **A6**'s $\delta\ge0.25$; **A14** as a sufficient reference condition; **A18**'s blanket vacuity; **A10**'s "$\lambda$ is not a hyperparameter"; **A12**'s cap-or-stratify and the task-blind scorer; **A1**'s BC grade; **A17**'s "BC by pre-registration" | **WITHDRAWN / regraded** | see §14.2–§14.3 rows 0, 80, 53, 58, 2/5, 30, 52 |
| **§16 item 6**'s two independent measurement channels; **§16 item 4**'s $n_b=1$ and $n_b\ge8$; **§16 item 10**'s politeness control; **§16 item 12**'s epoch clustering; the "caching changes latency not tokens" check | **WITHDRAWN** | the $\varphi$-exclusion assertion; $n_b^\star$ from a pilot with $n_b=3$ frozen; the two known-truth controls; family-only clustering with discard-on-drift; the canary battery |
| the old **§14** errata's "identified-but-irregularly-estimable" resolution | **WITHDRAWN** | finding 60's corrected statement |

### 14.6 Numbers that changed

| quantity | was | is |
|---|---|---|
| randomization floor | $\delta\ge0.25$ | $\delta=1/8=0.125$, $m_G\delta=1.000$ |
| $M=\delta^{-d}$ | 16 | **1 / 8 / 64** at $d=0/1/2$ |
| effective sample | $n/16$ conversations | **176 / 22 / 2.75 clusters** (230 / 28.75 / 3.59 at the ceiling) |
| i.i.d. unit | conversation, or (task × seed) | **task instance**; $n_{\rm clusters}=176$ families |
| certificate size at the only measured gap (0.046) | $5\times10^4$ / $1.2\times10^4$ | $2.4\times10^4$ ($M{=}1$) / $2.0\times10^5$ ($M{=}8$) / $1.6\times10^6$ ($M{=}64$) |
| smallest certifiable gap at $n=176$ | not stated | **0.542** ($M{=}1$); 1.533 and 4.336 exceed the outcome range and are impossible |
| one-sided LCB half-width at $n=176$ | not stated | **0.254** / 0.973 / 4.786 |
| certificate vs a stratified A/B test | "roughly the same" | **50–120×** |
| $\lvert\Pi\rvert$ | 100 (placeholder) | **8**, declared in §16 item 16; $L=6.461$ (8.987 at 100) |
| horizon | $T=5$ | $T_{\max}=3$, $D=2$, $\bar K=3$ |
| tilt budget | $n=10^4$, $T=5$: 0.96 SD / 0.46 nats | $\sum_t\Delta_t^2\le\log(176/30)=1.769$: $\Delta_t\le0.941$ SD, $\mathrm{KL}_t\le0.442$ nats |
| selection inflation | $\Theta(\sigma\sqrt{\log\bar K})$ at $\bar K\approx5$ | $\Theta(\sigma\sqrt{\log\bar K/n_h})$: $\approx0.43$ at $n_h{=}1$, $\approx0.014$–$0.020$ at $n_h{=}176$ |
| branch replicates | $n_b=1$ (training) / $n_b\ge8$ (benchmark) | $n_b^\star=\max(1,\sigma_e\sqrt{c_0}/\sigma_m)$ from a pilot; **frozen $n_b=3$** |
| prophet constant | 0.745 | deleted |

---

### 14.7 Conflicts the section repairs could not resolve alone, and their resolution

The eighteen section agents were instructed to report rather than resolve conflicts
between the binding repair specification and `docs/`. Each reported conflict is
resolved here.

**C1 — $n_{\rm clusters}=176$ "from 190 tasks" versus `audits.md`'s 230.** Reported by
the §0, §1, §2, §4 and §7 repairs as unresolved provenance. **It is resolvable and
there is no conflict.** `docs/design_e3_critic_policy.md` supplies the chain: the E3
primary pool is **190 tasks** = the A2 informative pool (240 uids with 3B posterior
mass in 0.1–0.9) **intersected with "has a visible check"**, dropping the 50 HumanEval
tasks whose prompt carries no `>>>` doctest (composition 163 MBPP + 27 HumanEval); and
single-link clustering of those 190 prompts on stop-word-filtered token Jaccard
$\ge0.5$ gives **176 families**, largest of size 3. `audits.md`'s **230** (155 MBPP +
75 HumanEval) is the informative pool by the integrity/mutation and assertion-split
routes, *before* the visible-verdict restriction. So: **176 families is the inference
unit and the denominator of every effective-sample statement; 190 tasks is the pool;
230 is the ceiling on the informative pool.** Two residues, both documentation rather
than theory: the A2 posterior-mass route gives 240 while the POOL-A ∩ scoring-usable
route gives 230, and the 50 dropped tasks are a *reported* secondary stratum on which
$U_k$ is absent — the design doc already says both, and §16 item 8 now carries 176 with
the $\approx230$ / $\approx100$ ceilings beside it.

**C2 — receiver cost: 3.2 s / 2,150 calls-per-hour versus 3.96 s / 909.** Reported by
the §2, §5 and §8 repairs. **Resolved in favour of the docs, as the spec's own
precedence rule requires.** `docs/measured_calibration.md` marks its own 3.2 s /
2,150-per-hour block **"SUPERSEDED for multi-turn work"**, and
`docs/pilot_findings.md` measures **3.96 s per 3B call** and **5.82 s per 7B call** on
this project's own multi-turn workload, stating that the 2,150 figure "makes multi-turn
designs look about 2.4× cheaper than they are". Decision: **the binding affordability
unit is receiver calls — 20,000 — and no claim may rest on a wall-clock figure alone.**
Where hours are quoted, the basis must be named, because the three available readings
of the same measurements differ by 4×: 2,150/hour (sustained, mixed, single-attempt),
$\approx$1,818/hour (3.96 s at the design doc's two effective contended slots, giving
$\approx$11 h for the frozen 20,151-call programme), and 909/hour (the pilot's
conservative serial reading, giving $\approx$22 h). §16 item 17 states the conflict;
this section adds the decision. Consequence worth recording: the withdrawn
certificate's 34 and 273 GPU-hours become roughly 80 and 645 hours at 909/hour, which
only strengthens the withdrawal.

**C3 — $n_b=3$ frozen, $n_b\ge8$ demanded, $n_b^\star\approx10$ implied.** Reported by
the §5 repair. **Resolved as far as arithmetic allows.** $n_b\ge8$ is withdrawn as
unaffordable (finding 25); $n_b=3$ is recorded as a **budget decision, not the solution
of P5b's variance display**; and the corrected interior optimum
$n_b^\star=\max(1,\sigma_e\sqrt{c_0}/\sigma_m)$ must be evaluated from a pilot estimate
before the freeze. The residual — that the frozen 3 is neither the withdrawn boundary
nor the corrected optimum — is not a conflict between documents but a live design
decision, and it is open question **Q2** below.

**C4 — "the harness runs every trajectory to $T_{\max}$" versus the design doc's 0.63
continuation calls per unit for the live policy arms.** Reported by the §4 repair, and
it is the most consequential of these. `docs/design_e3_critic_policy.md` §13 charges
**2.0** turns to B2/B3a/B3b and **0.63** each to B2t, B4, B5, B6 and $\pi^\star$, i.e.
the live policy arms **stop endogenously and are not run to $T_{\max}$**. Resolution,
stated precisely so that R1/R2's weight-free stop coordinate is not over-claimed:

> The stop coordinate carries no importance weight when a regime's value is obtained
> either **(i)** from data recorded to the administrative cap — the branch tree and the
> full-depth arms B2/B3a/B3b, where $\psi(H_k)$ exists at every $k$ — or **(ii)** by
> running the regime itself on-policy, where the realized trajectory *is* the estimand's
> sample path. A weight would be required only to evaluate one stopping rule from a log
> generated by a *different*, early-stopping rule, and this design never does that.
> Therefore the endogenously-stopping live arms' logs do **not** support reading off the
> value of any other stopping rule; that job belongs to the tree and to the full-depth
> arms, which must be preserved for it (requirement E12).

**C5 — findings 1 and 40 demand a fixed-string denominator as the headline; the spec
says B4.** Reported by the §0 repair. **Resolved in favour of the spec, and the
deviation is recorded rather than hidden.** B2 (fixed unary retry to $T_{\max}$, no
stopping rule) is **mandatory** — `positioning.md` constraint 2 — and is reported in
the four-denominator table, but the **headline gap is against B4**, because B2 breaks
one already-correct answer in six (degradation 0.162), so beating B2 is nearly free:
sizing against B2 gives an apparent +0.07 to +0.12, against B4 +0.015 to +0.030. The
reviewers' demand is therefore met in the weaker sense that a zero-information
denominator is mandatory and printed, not that it is the headline.

**C6 — finding 17's own arithmetic versus the corrected formula.** Resolved: the
stricter form $n\ge8ML\,/\,\mathrm{gap}^2$ with $L=\log(4\lvert\Pi\rvert/\alpha)$
governs, so §6's printed figures differ from the finding's by design, in the
conservative direction.

**C7 — the LCB half-width row (0.254 / 0.973 / 4.786) is not reproducible from
$8ML/\mathrm{gap}^2$.** Reported by the §6 repair. **Resolved:** those three numbers
are the two-term empirical-Bernstein half-width for a **single** policy,
$\sqrt{2M\log(2/\alpha)/n}+7M\log(2/\alpha)/(3(n-1))$ at $\alpha=0.05$, $n=176$ —
verified to reproduce 0.254, 0.973 and 4.786 exactly at $M=1,8,64$. It carries no union
over $\Pi$ and no gap split, so it is the **most favourable reading available**, which
is the right way to quote it against 0.046; the certificate's own requirement remains
the union-bounded $8ML/\mathrm{gap}^2$. §6 now names the formula in place.

**C8 — spec R2 (no stop weight) versus finding 74's separate exact stop factor.**
Reported by the §3 repair. Resolved by C4: R2 governs in this design, and the
reviewer's factor is the correct object only in the case C4 excludes.

**C9 — index convention.** The mandated R3 block is written in $t$ (turns) and the R8
block in $k$ (decision points). Resolution: **$t$ indexes turns $1..T_{\max}=3$ and $k$
indexes decision points $1..D=2$**; the histories $H_t^A$, $H_t^O$ are written in $t$
and regimes in $k$, with the convention stated once at first use in §1. No claim
changes.

**C10 — $\varphi$ is overloaded three ways.** It is the policy-observable feature map
(R3, R8), the influence function in §5's display, and the tilt basis in §11's
$e^{\theta'\varphi}$ and A20's test function. Resolution: **$\varphi_k$ is reserved for
the policy-observable map; influence functions are written $\mathrm{IF}(Z)$; the tilt
basis is written $\varphi^{\rm leak}$ / $\varphi^{\rm tilt}$.** §5 has made the first
two changes; §11 and A20 still write $\theta'\varphi$ and must be renamed at copy-edit.
This is a notation obligation, not a claim.

**C11 — the spec's R10–R22 were truncated in transmission.** Reported by the §2 repair.
The sections cite R16 (selection/evaluation splitting), R19 (horizon-invariant scorer),
R20 (judge optimism inflation) and R21 (truncated prophet) without having their
statements. Resolution: the *content* of each is supplied by the repaired text — R16 by
§1/§16 item 16 and §8 item 4, R19 by §8's measured-$\beta$ replacement and §16 item 5,
R20 by §8 P15/P24 and §15 item 7, R21 by §7 P22 — so no claim rests on a missing spec
item; but the canonical numbering must be confirmed before the document is frozen
(open question **Q10**).

**C12 — P23's weighted display is vacuous in D1.** Reported by the §7 repair. Resolved:
in D1 $e_t(\texttt{CONT}\mid H_t)=1$, so the continuation weight is identically 1 and
P23 is an **unweighted re-read** of recorded trajectories; the weighted form is a D3
object. The economics are stated where P23 sits: re-reading a recorded run for a new
candidate $\tau$ costs **zero** receiver calls, while one fresh on-policy rollout costs
up to $190\times8\times3=4{,}560$ calls, so at most four fit under the ceiling.

**C13 — "the strongest observational identification position".** Corrected in place in
§3: in D1 there is no natural policy in the data, because the harness replaced the user.

**C14 — the cross-section obligations from finding 78** (rewording §0.4's Ext-E row and
the §10 D3 bullet) and **from findings 11 and 56** (adding $G_0$ to §15 item 6 and
removing the withdrawn closed-form claim) were flagged by the §7 repair as outside its
own section. Both are **discharged**: §10's D3 row now reads "lower bound on the true
ambiguity", §0.4's Ext-E row reads "the weakest positivity requirement", and §15 item 6
carries both the restored Makarov–Rüschendorf closed form and $G_0$.

---

### 14.8 Requirements this theory imposes on the experimental design

Consolidated here so the execution side has one list; §16 remains the normative text
and each item points at the result that forces it. **E** for experiment.

**Randomization and the action space**

1. **E1 — Randomize the selector uniformly over the eight non-`STOP` arms at
   $e_t(k\mid H_t)=1/8$ at every branched decision point, and log the propensity with
   the draw.** A uniform floor needs $m_G\delta\le1$, so $1/8$ is the largest feasible
   floor for this taxonomy and it is attained with equality. *(A6, R1, §16.3)*
2. **E2 — Do not randomize `STOP`.** $Y(A_0\text{ at }k)=V_k$ is $H_k^A$-measurable, so
   positivity holds by degeneracy; randomizing it at a floor would deplete trajectories
   geometrically for no information. *(T8a, R1)*
3. **E3 — Freeze the action set at $m=9$ and partition it: evaluated
   $\mathcal A_{\rm adm}=\{A_0..A_5\}$, diagnostic $\{A_6,A_7,A_8\}$.** Diagnostic arms
   stay in the randomization and in the critic's training data, and are barred from
   every $\pi$ and every reported baseline value, because $V(e)$ over the full library is
   monotone in the number of deliberately degraded arms. *(T20(c), R4, §16.3)*
4. **E4 — Make leakage a coordinate of the action:** pinned generators
   $q_{(g,\lambda)}$ built to declared leakage levels by prompt construction, verified
   offline against the pinned library before the freeze, with the pair $(g,\lambda)$
   jointly randomized at $1/8$. *(T16, A12, R5)*
5. **E5 — Condition on nothing downstream of the selector.** No conditioning,
   stratification, binning, filtering or rejection sampling on realized $\hat\Lambda$,
   message length, message position, or any function of the outcome; $\hat\Lambda$ is
   reported as a per-arm fidelity measurement against the declared level, with the
   direction of its error stated (it understates leakage). *(T16, P17(a), R5)*
6. **E6 — Fix prompt geometry across arms:** re-render the task specification at a fixed
   token distance from the generation point in every arm, padding with inert filler
   verified at $\hat\Lambda=0$. This removes the position/recency channel, which is
   otherwise a mediator of the randomized selector. *(T16 companion, R5, §16.1c)*
7. **E7 — Run the length-calibration block** — each class at two pre-registered token
   budgets plus a filler-only arm, $\approx570$ receiver calls — and report class effects
   **net of the measured length main effect**. Without it the class effect is confounded
   with length by design-mediation, and the text must say so. *(T16 companion, R5,
   §16.7.6)*

**Statelessness and provenance**

8. **E8 — Invoke every generator statelessly:** fresh process and server session per
   call, context built deterministically from the recorded $H_t$ and the redacted view
   $X^-$; no carried KV cache, persona, scratchpad, surviving reasoning tokens,
   persistent tool/retrieval handle or server-side conversation id. Carried state is
   post-treatment with respect to earlier selectors and the $q$ factors do not cancel —
   T3 fails, not merely its computability. *(A5, T3, R7)*
9. **E9 — Verify E8, three ways, and report all three:** (a) byte-exact SHA-256
   input-provenance hash per call, recomputed offline from $H_t$ and $X^-$ alone; (b)
   fresh-context assertion with prompt caching disabled and an explicit reset, logged per
   call; (c) out-of-order replay of a random 2% sample requiring byte-identical output.
   **On any failure the history is redefined to contain the carried state**, and A9's
   $\varphi$-measurability and every "no text critic" claim must be restated on the
   enlarged history. *(§16.1(a)–(d), R7)*
10. **E10 — Redact by architecture, not by arm:** generators receive $X^-$ with the
    reference solution and tests removed, and `signature_example` (byte-identical to
    `test_list[0]` on 427/427 MBPP tasks) is stripped from every record a generator or the
    feature builder can reach. Answer-visible ($A_8$) runs only as a declared positive
    control. *(A12, R5, §16.1b)*

**The information-set firewall**

11. **E11 — Enforce $\varphi$-exclusion in code:** $\varphi$ is the frozen 87-coordinate
    policy-observable map, and `build_features` **must raise** on any of `{test_list,
    test, challenge_test_list, reference, signature_example, V, Y}`, with a unit test per
    forbidden key. This replaces the withdrawn two-independent-channel requirement.
    *(A11(d), T8b, R3, §16.6)*
12. **E12 — Grade $\psi$ at every turn, and preserve full-depth data.** The branch tree
    and the full-depth arms (B2/B3a/B3b) must run to $T_{\max}$ so that every "stop at
    $k$" value is *observed* rather than weighted. The endogenously-stopping live policy
    arms do not carry grades past their stop, so no other stopping rule's value may be
    read from their logs. *(T8a, R1/R2, conflict C4)*
13. **E13 — Report the oracle-$V$ minus $\hat p$-rule value gap as a headline pair; never
    the oracle value alone.** The +4.6 pp is the value of an oracle available to no real
    rule, and the implementable stop value $E[\psi\mid\varphi]$ is an unknown regression.
    *(T8b, R3, audits A3)*

**Frozen before any outcome of this run is examined**

14. **E14 — Freeze and hash:** the generator library and its evaluated/diagnostic
    partition; the coarsening map; the leakage scorer; $\varphi$ **as data**; the
    176-family file and the 5-fold assignment; the task pool file; $\lambda=0.01$ per turn
    and the grid $\{0,0.005,0.01,0.02\}$; the candidate set $\Pi$ with
    $\lvert\Pi\rvert=8$; the action-feature code (`channel`, `info_cap_bits`,
    `carries_verdict_bit`, `suffix_words`, `template_index`) as **action features of the
    arm, not measured covariates of the message**; baselines B0–B7; the primary and
    ordered secondary outcome list. Record the freeze commit id. *(§16.2, §16.16, R8)*
15. **E15 — Compute $G_0$ from the sibling project's completed 4,488-episode log**
    (identical `tasks_sha256`, verified), hash it before any outcome of this run is
    examined, and report the win probability as **reference-dependent on a frozen
    reference**. Estimating $G_0$ on the analysis sample would make $\tilde Y$
    nuisance-carrying and the units dependent, and would cost exact unbiasedness.
    *(T13/T14, A17, R6)*

**The inference unit, folds and estimators**

16. **E16 — The i.i.d. unit is the task instance.** Cluster and cross-fit on the **176
    task families only** — 5 folds, all seeds, branches, turns, templates and paraphrase
    variants of a family in one fold. Never cluster by epoch or model version: a mid-run
    version change makes the estimand undefined, so affected blocks are **discarded and
    reported as discarded**. *(§1 Units, A2, R9, §16.12)*
17. **E17 — Primary estimator is the paired, common-root, family-clustered contrast
    (E0):** mean over the 176 families of the family-mean paired difference on the 1,520
    paired units ($190\times8$ root seeds sharing one saved root $O_1$), paired
    family-clustered bootstrap; measured half-width $\pm0.019$ at $R=8$, MDE 0.027. The
    headline gap is against **B4**, with B2, single-shot, and ($V(e)$ on the evaluated
    stratum, the truncated prophet bound) as the other three denominators in one table.
    *(R9, T20(d), §16.14, conflict C5)*
18. **E18 — Report $n_{\rm eff}$ in clusters and by entitlement class.** $\Pi_0$:
    $W\equiv1$, no weighted quantity exists. $\Pi_1$: $W\le8$, print ESS and $\hat D_2$
    with every number. $\Pi_2$: $W\le64$ and **2.75 effective clusters**, so its values
    come from on-policy rollout and off-policy certification of them is explicitly
    disclaimed. *(R2, §16.8, §16.15)*
19. **E19 — Cross-fit every nuisance, including in D1** (A18a is not vacuous when $e$ is
    known; only the product rate A18b is), and confine the exact-unbiasedness claim to
    the cross-fitted one-step/AIPW estimator with an internally consistent
    $\hat V_t=\sum_k\pi_t\hat Q_t$. TMLE, clipped IPW and self-normalized forms may not be
    reported as finite-sample exact, and no self-normalized estimator may appear inside
    any certificate. *(T9(i), A18, findings 53 and 81)*
20. **E20 — Split selection from evaluation, twice.** Per state: a per-state argmax over
    branch means carries an inflation of order **0.43** at $n_b=3$, roughly nine times the
    available headroom, so branch ground truth is used **pooled or on strata, never per
    state**. Over $\Pi$: re-estimate the winner's value on held-out families and report the
    inflation. *(P11, P24(ii), R16, §16.4)*

**Measurement, stratification and reporting**

21. **E21 — Report degradation as a separate outcome, never folded into a mean**, and
    stratify on first-attempt status: the primary estimand is conditional on the first
    attempt failing, with the already-correct stratum analysed separately for **harm**
    (measured repair 0.239 [0.210, 0.270] against degradation 0.162 [0.105, 0.242]).
    *(audits A2/A3, §12.18, §16.13)*
22. **E22 — Carry a per-task contamination score (turn-1 single-shot pass rate) as a
    pre-registered stratification variable**, and report cost-priced and prioritized
    numbers primarily on the uncontaminated stratum. Contamination attenuates content
    blips but **inflates** stop-arm advantages and cost-priced gaps, so it is
    anti-conservative for this design's central coordinate. *(§12.10, finding 8)*
23. **E23 — Log the cost channel separately and price it at the pre-registered
    $\lambda=0.01$ per turn.** If more than one grid point is reported, every interval
    carries a union bound over the grid and $\lambda$ is called a hyperparameter; a
    $\hat\lambda$ read off an estimated (value, cost) frontier is prohibited. A policy
    exceeding the primary comparator's mean completion tokens by more than 10% has not met
    the primary criterion even with a positive point estimate. *(A10, R6, §16.13)*
24. **E24 — Branch hygiene:** interleave expansions across task instances with a
    cooldown; randomize expansion order, including on the deep slice; replay a
    fixed-prompt canary battery each block; power the duplicate-arm check on the deep
    slice; report the duplicate-arm discrepancy beside $\hat v$ and **declare $\hat v$ and
    $\hat R$ unusable if it exceeds $\hat v$**. The "caching changes latency and not
    tokens" check is not diagnostic and may not be used. *(A1, A13, P18(c), §16.4/16.12)*
25. **E25 — $n_b$ is frozen at 3 and is a budget decision.** Report the resolution it
    buys (per-state MC SE up to 0.29 against $\hat v\approx0.08$); use T27 as a **ranking**
    device with $L$ and the spread reported; print an absolute debiased risk only if the
    matched-slice condition for $\hat v$ is verified. Set $n_b$ from a pilot estimate of
    $(\sigma_e,\sigma_m,c_0)$ against $n_b^\star=\max(1,\sigma_e\sqrt{c_0}/\sigma_m)$.
    *(P5b, T27, findings 25/36/86)*
26. **E26 — Run the falsification battery and publish it with the power of each item
    stated.** The inert-dimension negative control is replaced by (i) a **hash-verified
    withheld-channel arm** whose truth is a software-verifiable zero and which costs zero
    receiver calls, and (ii) $A_8$ as a **guaranteed positive** read as the measured
    ceiling and leakage upper anchor. No passing battery may be presented as evidence of
    correctness. Hard halt on any failure of the item-1 provenance tests, the
    $\varphi$-exclusion assertion, or the G2/G3 message gates. *(P18, §16.10–11)*
27. **E27 — Use disjoint rollout sets for $\hat Q_t(H_t,K_t)$ and $\hat V_t(H_t)$**, so
    P10's additive variance is exact and the two branch allocations separate; with shared
    rollouts the cross-covariance term must be carried before the allocation is solved.
    *(P10, finding 61)*

**Budget and scope discipline**

28. **E28 — Price every prescription in receiver calls against the 20,000-call ceiling,
    and name the basis of any wall-clock figure** (909 calls/hour for multi-turn 3B work;
    2,150 only for single-attempt work). Anything above the ceiling is cut or marked
    unaffordable — this section marks two: the $n_b\ge8$ deep slice and the improvement
    certificate. *(measured_calibration/pilot_findings, §16.17, conflict C2)*
29. **E29 — Do not report as identified or certified:** the value of a free-form
    generative policy, of a generator outside the pinned library, of a late-continuation
    regime from logs, of a full-depth ($\Pi_2$) regime evaluated off-policy, or of any
    contrast holding realized leakage, length or position fixed. *(§16.15, T16, R2)*
30. **E30 — The simulated-log arm's "floor 0.2" is a weight-truncation level** ($\hat e$
    clipped below at 0.2, so $w\le5$), not a randomization floor ($8\times0.2=1.6>1$). A6
    does **not** hold in that arm, clipping bias is introduced, and the truncation rate
    must be reported. *(R1)*
31. **E31 — Register (ISO-U) in the §2 table before any separable-effects claim is made
    confirmatorily**, and if it is tested, the test is: branch on $A^D$ at fixed $A^Y$ in
    the harness and test invariance of the next-message law given continuation. The
    receiver-side half is a software guarantee; the user-kernel half is an assumption that
    is false in the obvious implementation. *(T25(d), finding 75)*

---

### 14.9 Open questions for the theory workstream

These are the things this repair could not settle. Each needs a human decision, and
none of them is dispatchable by re-reading the documents.

1. **Does family clustering buy what it claims?** 176 families come from single-link
   Jaccard $\ge0.5$ clustering of 190 prompts, largest family 3. Whether that threshold
   delivers approximate independence — and whether power should be quoted at 176 or at
   190 — is a modelling judgement the robustness row (0.4/0.6/0.7) reports but does not
   settle. Everything numerical in §4, §6 and §16 is quoted at 176.
2. **$n_b$: accept 3, or re-plan the tree?** The corrected P5b algebra gives an interior
   optimum $n_b^\star=\max(1,\sigma_e\sqrt{c_0}/\sigma_m)$, plausibly near 10, while the
   frozen design has 3 and $n_b\ge8$ is unaffordable. The options — fewer states at
   higher $n_b$, accept pooled-only ground truth, or drop the absolute-risk ambition
   entirely — trade the validation asset against the tree's breadth, and only a human can
   pick.
3. **Is any certificate worth keeping?** T20 is withdrawn. Whether the paper should carry
   a bounded-width guarantee of a different kind — e.g. an anytime-valid bound on $\Pi_0$,
   where $W\equiv1$ and the binding number is the 0.254 half-width against 0.046 — or no
   guarantee at all, is a positioning decision with a real cost either way.
4. **T8b is the deliverable's bottleneck and is not yet a theory.** The implementable stop
   value $E[\psi\mid\varphi]$ is the hardest estimation problem in the design; the visible
   verdict is one bit and absent on 20.8% of the informative pool; and the false-pass rate
   $\phi=P(\text{visible pass}\mid\text{hidden fail})$, which governs where a learned
   critic can beat the trivial rule, is **unmeasured**. The headline deliverable is
   currently gated on an unmeasured quantity.
5. **Should the greedy-in-$\varphi$ rule be in $\Pi$ at all**, given $\varphi$ is not
   sufficient and backward induction therefore returns it rather than the restricted
   optimum? And is a covering-number bound for $\Pi_{\rm cp}$ worth deriving? We have
   none, and without one no statement about the infinite class can be made.
6. **Debiasing P24(i) when the two channels are correlated by construction** remains open
   for judge-scored secondary outcomes. Neither the clean-independence nor the
   shared-noise analysis applies, and the document currently offers only the
   oracle-minus-rule reporting pair.
7. **Can (ISO-U) be made testable within budget?** The falsification test is specified and
   unpriced, and the two-call disjoint-context split that would make it architecturally
   true changes the estimand to one relative to that artificial split. Someone must decide
   whether that estimand is the one the paper wants.
8. **How is the conditional-information leakage scorer validated** now that
   answer-withholding is architectural? The scorer needs a reference receiver that *has*
   seen the reference solution, which sits outside the redaction invariant; the planted-set
   validation is specified but its sufficiency is not established.
9. **Is the exceptional-law problem a patch or a re-specification?** Roughly half the task
   mass sits at the boundaries (0.156 below 0.05, 0.334 above 0.95). $m$-out-of-$n$ and
   adaptive intervals are prescribed, but a design whose primary estimand is non-regular
   over half its population may need a different estimand rather than a bootstrap patch.
10. **Confirm the canonical numbering of the binding specification (R10–R22).** R16, R19,
    R20 and R21 are cited across the repaired sections; their statements were truncated in
    transmission and their content was reconstructed from the repaired text (conflict
    C11). This must be reconciled before the freeze.
11. **Fix the notation obligations:** $\varphi$ is still overloaded in §11 and A20
    ($\theta'\varphi$ for the tilt basis), and the $t$/$k$ index convention needs to be
    applied consistently (conflicts C9, C10). Editorial, but it touches every displayed
    weight.
12. **Keep or drop T13/T14?** They are demoted to a secondary reporting device on a
    frozen, reference-dependent $G_0$, over an outcome with roughly six cells and a tie
    mass that is the majority of pairs. Demotion may be the wrong answer: deletion is
    cleaner, and the only cost is a reporting device nobody has asked for.
13. **What survives if A5's replay test fails on an LM-generator arm?** The prescribed
    fallback — redefine the history to contain the carried state — has not been worked
    out: it is not established which of A9, T3, P2, T9 and the "no text critic" claims
    survive on the enlarged history, or whether $\varphi$-measurability can be restored at
    all.
14. **Should the document be reorganized around the claim the evidence supports?** The
    surviving contributions are the design, honest effect reporting, and the boundary
    results — "adjustment moves reported effects a lot and decisions a little", horizon
    over confounding, repair 0.239 against degradation 0.162, and the 0.046 that oracle
    stopping is worth. The document is still organized around identification of blips,
    which is now the secondary claim.
15. **Is the frozen-reference win probability publishable as such?** $G_0$ comes from a
    sibling run with its own prompt format and grading, so the reported win probability
    and $\pi^\star$ are reference-dependent on a related-but-not-identical regime. The
    freeze is what buys the theory; whether the resulting estimand is one a reviewer will
    accept is a judgement call.

---

---

## 15. Open problems

**How to read this list after the repair.** Three things changed. (i) Two entries were
not open: item 1 follows in two lines from the influence function this document already
displays, and the scalar half of item 6 is a classical closed form whose references are
already in §13(a). Both are **withdrawn in place** below, with their numbers kept.
(ii) Several entries were stated as future refinements when the recomputed constants make
them *binding obstructions now* — item 4 above all. Each such entry now carries the
number that makes it binding. (iii) Two entries were stated at the wrong rate or on the
wrong information set, and are restated.

**What none of this list is on the critical path for.** The only measured headroom in the
design is **+0.046** of final success from oracle stopping decisions, and stopping-only
regimes lie in $\Pi_0$, where $W\equiv1$ and every value is an *unweighted* mean on
recorded trajectories (R2). Items 2, 3, 4, 10, 13 and 14 are all problems of the
importance-weighted and observational-tilt machinery. **The deliverable the evidence
supports needs no importance weights at all**, so a reader should treat those six as
scope statements about the extensions, not as gaps in the primary claim. Items 7 and 15
are the ones that bear on the primary deliverable, and item 7 bears on it only through
the judge-scored secondary outcomes.

---

1. **Efficiency bounds in submodels with the propensity known — WITHDRAWN as an open
   problem for $V(\pi)$ at fixed $\pi$; retained, narrowed, for three residual
   functionals.** *We claimed that the longitudinal analogue of Hahn (1998) — whether
   knowing $e$ lowers the semiparametric efficiency bound — was open, and declined to
   assert it. It is not open: the influence function
   $\varphi=V_1(H_1)-\psi+\sum_t W_{1:t}(V_{t+1}-Q_t)$ has identically zero projection
   onto the turn-$t$ treatment tangent space, because the turn-$t$ residual has
   conditional mean zero given $(H_t,K_t)$, all later residuals have conditional mean
   zero, and all earlier terms together with $V_1$ are $H_t$-measurable. Removing that
   subspace — which is exactly what knowing $e$ does — leaves $\varphi$ an influence
   function in the reduced tangent space, so $\varphi$ is efficient in both models and
   $\mathrm{Var}(\varphi)$ is the bound in both. The statement and the projection
   argument belong to §5 T9(v) and are not restated here; this is the standard
   van der Laan–Robins result and declining to assert it was a gap, not caution.
   **Knowing $e$ buys exact unbiasedness and finite-sample validity, not asymptotic
   efficiency** — which is what the document wanted to say in the first place.* What
   remains open, and only this: (a) MSM parameters indexed by $e$ itself; (b) $V(\pi^\star)$
   under exceptional laws, where the functional is not pathwise differentiable at all;
   (c) the $P$-dependent tilt regime of §11.1 T30, whose *intervention* depends on $P$
   through the conditional normalizer, so the model whose bound one would compute is not
   fixed as $P$ varies.

2. **Estimating conditional normalizers / nuisances over unique text histories — scoped
   to the extensions; not load-bearing in D1.** In the primary design the nuisances are
   regressions on the **frozen finite-dimensional feature map** $\varphi_k$ (the
   87-coordinate state code of R3/§1), not on verbatim text, and the propensity is known
   by construction, so the product-rate condition is **not** what buys unbiasedness of
   D1's value estimates (T9(i)); it buys the efficiency claim and the nominal width of
   the intervals. The item bites where there is no known-propensity fallback: in Ext-B the
   conditional normalizer $Z_t(\theta,h)=E_P[e^{\theta'\varphi}\mid H_t=h]$ is a genuine
   conditional expectation over a long, never-repeating text history, it sits *inside the
   intervention itself*, and $\sqrt n$ inference rests entirely on
   $\lVert\hat Z-Z\rVert\cdot\lVert\hat{\tilde Q}-\tilde Q\rVert=o_P(n^{-1/2})$ for two
   text-history regressions. No smoothness theory exists for such regressions (§12.12),
   so this is an assumption and is declared as one; if $\hat Z$ is inconsistent the
   estimator is inconsistent, and $E[w_t\mid H_t]=Z_t/\hat Z_t\ne1$ breaks both the exact
   $P$-martingale property and the $E[w_t\mid H_t]=1$ specification check. The same
   unverifiable pooling model is what §9 T28's per-turn discrepancy term needs, and that
   term should be read in this epistemic class rather than as "estimable from ordinary
   logs". The heteroskedastic-Gaussian shortcut for the tilt's normalizer remains
   attractive and its misspecification cost remains uncharacterized.

3. **Inference under bounded-but-large weights — restated: the obstruction is effective
   sample size, not tail behaviour.** In D1 the weights are **bounded almost surely by
   design**: $W\le\delta^{-d}$ with $\delta=1/8$, so $W\equiv1$ for $\Pi_0$, $W\le8$ for
   $\Pi_1$ and $W\le64$ for $\Pi_2$ (R1, R2), and at the recommended clip level
   $M=\delta^{-d}$ clipping never binds and its bias is identically zero. "Heavy tails"
   is therefore the wrong frame for the primary route; the right frame is that
   $n_{\rm eff}\ge n_{\rm clusters}\delta^{d}$ gives **176 / 22 / 2.75** clusters at
   $d=0,1,2$. The exact martingale structure of the tilt ratio does suggest Ville-type
   anytime-valid certificates, and two things must be said about them. First, with
   *estimated* normalizers the exactness is lost, so the anytime-valid route is
   **unavailable in Ext-B** (item 2). Second, in D1 it is available in principle and
   still does not help: an anytime-valid bound cannot be narrower at the same $\alpha$
   than the fixed-sample bound of R4, whose one-sided half-width at $n_{\rm clusters}=176$
   is **0.254** for an unweighted comparison against **0.046** of available headroom —
   a factor of **5.5**. This open problem is genuinely open and is not on this project's
   critical path.

4. **Minimal randomization designs for full override depth without a Markov assumption —
   now binding, not a refinement.** Override depth is not a free knob (R2): it counts the
   decision points at which a regime overrides the generator-class distribution, and the
   frozen design has $D=2$, so for $\hat\pi$ and every full-depth member of
   $\Pi_2=\Pi_{\rm cp}$, $d=D=2$ and $M=\delta^{-D}=64$. At $n_{\rm clusters}=176$ that
   leaves **2.75 effective clusters**, and the certificate arithmetic of R4 is worse than
   uninformative there: the smallest gap resolvable at $M=64$ is **4.336**, which exceeds
   the range of $Y-\lambda C\in[0,1]$, so no gap is certifiable at any sample size this
   pool could reach (required $1.6\times10^6$ clusters at gap 0.046, i.e. **8,884×**
   short). The consequence is stated wherever a full-depth value is reported: **values of
   full-depth regimes are obtained by on-policy paired rollout (E7) or by re-logged policy
   iteration, never by off-policy weighting**, and off-policy certification of them is
   explicitly disclaimed. A design that would restore depth-2 estimability without a
   Markov assumption is therefore the single most valuable missing piece of design theory
   for this line of work, and we do not have it. Note also that the exponential-in-horizon
   blow-up is capped at $8^2=64$ *only* because there are two decision points; nothing
   here extends to a longer interaction.

5. **Structure of the budget-constrained optimum**: adjacency of the two mixed thresholds
   for history-dependent finite-horizon rules. One clarification the repair forces, since
   it was nowhere in §12 or here. T8's LP-duality reading makes $\lambda$ a *budget
   price*, i.e. a functional of $P$ determined by the supporting hyperplane of the convex
   hull of attainable (value, cost) pairs — which would be estimated from the same data
   and would put a data-dependent estimand inside every bound that treats $Y-\lambda C$
   as fixed. **This design does not take that route: $\lambda=0.01$ per turn is
   pre-registered as a hyperparameter**, read off the measured budget, with the grid
   $\{0,0.005,0.01,0.02\}$ and a union bound if more than one value is reported. So the
   dual price is fixed by fiat and the double-dipping problem is avoided rather than
   solved; the sampling behaviour of an *estimated* dual price, and the post-selection
   correction it would need, is open and is not attempted here.

6. **Pathwise differentiability of the causal win probability — the transport half is
   WITHDRAWN for the scalar comparison; the rest is retained and demoted to a secondary
   route.** *We listed "closed-form sharp transport bounds for three-level lexicographic
   comparisons" as open. For the comparison T13 actually performs this is wrong: T13
   reduces the lexicographic order to a **scalar** $u(Z)$, and sharp bounds on
   $P(u(Z^\pi)>u(Z^{\pi_0}))$ with fixed marginals are the classical Makarov (1981) /
   Rüschendorf (1982) bounds on the distribution of a difference —
   $\sup=1-\sup_t\{F_V(t)-F_W(t)\}^+$ and $\inf=\sup_t\{F_W(t)-F_V(t)\}^+$ up to one-sided
   limits — closed-form and attained at explicitly constructible shuffle couplings, not at
   the comonotone one. Those references are already in §13(a). The optimal-transport LP is
   needed only for a genuinely vector-valued, non-scalarizable comparison, which is what
   this item now retains.* Still open: **pathwise differentiability when $u$ or the
   tolerances are estimated** (we believe it fails); **existence of a Condorcet winner
   among blip-threshold rules**; and sharp bounds for the non-scalarizable multi-level
   case. Added, because it is the nuisance that would actually have to be estimated in
   every run: **$G_0$**, the mid-rank CDF of $u(Z)$ under the reference regime, which is a
   functional of $P$ and not pinned by naming $\pi_0$. The confirmatory route does not
   leave it open — $G_0$ is **frozen on the sibling project's completed 4,488-episode log**
   on the identical task pool and hashed before any outcome of this run is examined (R6),
   which makes $\tilde Y$ a fixed known measurable transform and buys the verbatim reuse of
   T8a and T9, at the price that the reported win probability is **reference-dependent on a
   frozen reference**. What is open is option (ii): estimating $G_0$ on the analysis sample,
   where $\tilde Y$ carries an outcome-law nuisance, the units are dependent, the two-term
   influence function $\varphi_\pi[G_0^-]+\varphi_{\pi_0}[\bar G_\pi]$ is the correct
   expansion, and exact unbiasedness degrades to double robustness with a bilinear
   remainder in $(\hat G_0-G_0,\hat Q-Q)$. Scope note: T13/T14 are now a **secondary
   reporting device**, not the primary objective (R6), so items in this entry are open
   problems of a secondary route.

7. **Debiasing the optimized-stopping winner's curse — restated at the correct rate, and
   split into the two distinct objects that were conflated.** The two are:
   (a) **selection inflation**, $\Theta\!\big(\sigma\sqrt{\log \bar K/n_h}\big)$ with $n_h$
   the number of independent scorings per decision node — $n_h=1$ for a per-trajectory
   argmax, $n_h=n$ for a global rule selected across units — which **vanishes in $n$** and
   is *not* comparable to a fixed effect size except in the $n_h=1$ case, where the earlier
   "comparable to any real effect this project hopes to report" warning is retained;
   (b) **the within-unit optimistic bias** $E[\varepsilon_\tau]$ of P24(i), which persists
   as $n\to\infty$ because the same realized scoring noise both triggers the stop and
   scores the outcome. The remedies are not interchangeable and the earlier framing
   misdirected them: sample size fixes (a), an independent measurement channel fixes (b).
   Two scope facts follow from R3. First, the **primary** outcome is programmatic, so
   $\sigma=0$ for it and neither (a) nor (b) bites on the headline number; both bite on
   judge-scored secondary outcomes, where T8b's inflation term applies. Second, the
   stopping signal is $\varphi$-measurable and $\varphi$ **excludes** $\psi$ and every
   hidden-test-derived quantity by construction, so "the stopping signal and the outcome
   score are correlated but not identical" is not an accident to be debiased but the
   design's information-set restriction, and the honest handle on it is the mandatory
   headline pair: the **oracle-$V$ minus $\hat p$-rule value gap**, never the oracle value
   alone. What is genuinely open is a debiasing correction for case (b) when the two
   channels are correlated by construction rather than independent. One arithmetic fact to
   report rather than assume away: over the pre-registered candidate set,
   $\sqrt{2\log|\Pi|/n_{\rm clusters}}=0.153$ outcome-SD units at $|\Pi|=8$ and
   $n_{\rm clusters}=176$, which is why the winner's value is re-estimated out of fold and
   the selection inflation is reported (R8, R16) rather than declared negligible.

8. **Sensitivity calibration for exchangeability on the continuation coordinate** — how
   much can unrecorded private user state shift both the quit hazard and final quality? No
   domain calibration exists, and this remains open. Two clarifications. (i) It is an
   **extension-only** problem: in D1 there is no user — the harness replaced the user, it
   runs every trajectory to $T_{\max}$, and there is no private state to be unrecorded.
   The item is live for the human-in-the-loop extension (§10, P31) and for the late-
   continuation regimes of P21. (ii) Because this calibration is missing, P21's width
   $\kappa_0(\pi)$ is a **lower bound** on the true ambiguity, not a sharp width: the
   behavioural mechanism that creates the support failure ("satisfied users stop")
   simultaneously threatens A7 for the continuation coordinate, so on the supported
   histories consistency is not guaranteed either. The exploratory premise checks
   (`docs/premise_findings.md`, hand-built tabular laws, not evidence about LLMs) found
   decision-level regret moving by at most 0.030 under deliberately hostile unmeasured
   confounding while horizon dominated; that is a reason to expect this item to matter more
   for *reported effects* than for *chosen actions*, not a substitute for the calibration.

9. **Recommendation vs compliance**: whether to headline the ITT effect of a continuation
   nudge or the per-protocol effect; the IV route needs monotonicity assumptions we have
   not examined. Scope, added: in D1 the assigned action is **delivered by construction** —
   generators are invoked statelessly from a context built deterministically from the
   recorded $H_t$, verified byte-exact by prompt hash (A5, R7) — so ITT and per-protocol
   coincide in the confirmatory design and this item too is live only for the human-user
   extension. A receiver that ignores a delivered message is an outcome, not
   non-compliance.

10. **Whether within-history phrasing variation is causally material at all — partly
    measurable here, and the design already measures the proxy.** By T30 the entire
    achievable gain of the observational tilt route is governed by
    $\mathrm{sd}_g(Q^\star(H_t,A)\mid H_t)$; "certifiable" is deleted, since T20 is
    withdrawn as a deliverable (R4) and there is nothing left to certify against. The
    design's measurable proxy is the **within-class template SD**, which E2's
    coarsening-sufficiency test targets directly: its power is **92% against a within-class
    template SD of 0.08** and **57% against 0.06**, so a non-rejection must be quoted as
    evidence against template effects of 0.08, **not** as evidence of exact sufficiency.
    Two honest limits. (i) It cannot be read off the primary branch budget: at the frozen
    $n_b=3$ the per-state Monte Carlo SE is up to **0.29** against a branch-value spread of
    $\hat v\approx0.08$, so branch ground truth is usable pooled or on strata and never per
    state; any attempt to estimate a *within-history* SD directly needs a dedicated
    replicate block, and that block must be priced against the **20,000 receiver call /
    9.3 hour** ceiling before it is prescribed. (ii) The quantity T30 actually needs is the
    SD over **human** phrasing, and there are no human users here; `docs/positioning.md`
    forbids claiming transfer to human users, so the human version of this question stays
    open and stays unmeasured by this design. Note also that the template index is a
    nuisance drawn uniformly from 3 frozen templates and is **never a policy action**,
    precisely so that the policy does not act at a finer granularity than E2's test covers.

11. **Transportability calculus for mechanism-relative estimands** across user populations
    sharing a feature map but not its conditional law. Retained as written, with the scope
    made explicit: the estimand here is already relative to a frozen receiver and a frozen
    generator library, and — after R6 — the win-probability reading is additionally relative
    to a frozen sibling reference log, so there are three distinct relativities to transport
    and this document does not claim any of them transports. Transfer to human users is not
    claimed at all.

12. **Relaxing the no-decay assumption** to measured decay: a discount factor probably
    suffices, but the as-delivered / fixed-measurement-point equivalence genuinely fails and
    the substantive choice of target becomes unavoidable. Retained. Two notes. The horizon
    range over which decay could act is small here ($T_{\max}=3$, $D=2$), which limits the
    exposure but also means this design cannot measure decay. And the horizon-invariance
    requirement on the scorer (A11(c)) is not discharged by the calibration test as it was
    originally written — see the replacement in §8 — so "no decay" and "horizon-invariant
    scoring" must not be read as two independently verified conditions.

13. **Composition of a logged generator with a known deterministic edit** — the most natural
    merge of the known-propensity and stochastic-intervention routes, possibly evaluable
    without new data. Retained, with three conditions that were missing. (i) The composed
    generator must still be **stateless** in the sense of A5/R7: no carried KV cache,
    persona, scratchpad, surviving reasoning tokens, retrieval handle or server-side
    conversation id. If any carried state $U_t$ exists, $U_t$ is post-treatment with respect
    to earlier selectors and mediates them, the $q$ factors do not cancel in T3, and the
    history must be redefined to contain $U_t$ — with A9's $\varphi$-measurability and every
    "no text critic" claim restated on the enlarged history. (ii) "Without new data" means
    on a *logged* arm, where **A6 does not hold** — the logging policy is confounded by
    construction — and the "floor 0.2" that appears in the simulated-log arm is **not a
    randomization floor** ($8\times0.2=1.6>1$): it is a **weight-truncation level**
    ($\hat e$ clipped below at 0.2, so $w\le5$), it introduces clipping bias, and the
    truncation rate must be reported. (iii) The only real log available is the sibling
    4,488-episode run, which R6 spends on freezing $G_0$; reusing it here is permissible but
    creates a shared dependence across two reported quantities that must be declared.

14. **History-dependent tilt directions and post-selection inference** for the value of an
    intervention whose direction was chosen from data. Retained, and now the *only*
    remaining post-selection gap, because the policy-selection problem is handled by
    construction: $\hat\pi$ is the argmax over a **pre-registered finite candidate set
    $\Pi$** whose count is declared in §16, evaluated out of fold over the 176 families with
    all seeds, branches and turns of a family in one fold, with the winner re-estimated on
    held-out data and the inflation reported (R8, R16). A data-chosen tilt *direction*
    indexes an infinite class, for which a covering-number bound would be required and
    **we do not have one**; we therefore do not report any value for a direction chosen from
    the same data.

15. **Auditing semantic scorers as causal features — rewritten: under the repaired design a
    bad scorer degrades a measurement, not an identification.** Measurement error in a
    scorer does not break identification (the estimand is *defined* by the scorer) but
    changes *which* intervention is evaluated. Two distinct scorers are involved and the
    earlier statement collapsed them. (a) **Leakage is a coordinate of the randomized
    action space, not a covariate** (A12, R5): pinned generators are built to declared
    leakage levels, the pair $(g,\lambda)$ is randomized at $e=1/8$, and the realized
    leakage score $\hat\Lambda$ is **post-treatment** — a fidelity measurement that is never
    conditioned on, stratified on, or filtered by. So a scorer that partially reads the
    answer no longer "silently reintroduces leakage" into the identified contrasts; it
    mismeasures a reported diagnostic, and it does so **in a known direction**:
    $\hat\Lambda$ *understates* leakage, which makes any leakage-controlled contrast look
    **larger**. The earlier caveat that the proxy-to-ideal relation is "unsigned" was wrong.
    $\hat\Lambda$ is now defined as conditional information — the log-likelihood gain of a
    fixed reference receiver on the reference solution given $(H_t,\tilde A_t)$ versus given
    $(H_t,\text{null message})$ — and the open problem is the narrower one of **validating
    its dynamic range**, on a planted set with messages that literally state the fix at the
    top and pure-affect messages at the bottom. Answer-withholding is an architectural
    invariant, not an arm: generators see the redacted view $X^-$, enforced by prompt-hash
    assertion. (b) As **policy features**, the frozen map $\varphi_k$ must exclude $\psi$
    and every hidden-test-derived quantity (R3), so a feature built from a scorer that reads
    the answer is a breach of the $\varphi$-exclusion assertion and is caught by the
    feature-builder assertion rather than left to audit. What remains open in (b) is the
    Ext-B case, where $\varphi$ defines the *intervention* itself through $\theta'\varphi$:
    there, scorer error redefines the target and there is no assertion that can detect it,
    because the estimand moves with the scorer.

---

---

## 16. What an experiment must do

Every item below is a requirement on the frozen design, and every quantity in it is
either a frozen design choice or a measured number with a source. Items 1–15 keep their
original numbers; where a requirement was wrong it is **withdrawn or replaced in place**,
with one sentence saying why, rather than deleted. Items 16 and 17 are new and carry two
declarations the rest of the document points at (the candidate count $|\Pi|$, and the
affordability ledger).

1. **Freeze and record the environment exactly** (model id, weights digest, decoding
   parameters, per-turn seed, tool versions, system-prompt hash); verify fixed-seed token
   reproducibility. Two additions, both load-bearing and both cheap:

   **(1a) Stateless generator invocation must be verified, not assumed (A5, R7).** T3's
   density cancellation requires $q_k$ to be a kernel in the recorded $H_t$ alone. Any
   carried KV cache, persona or scratchpad memory, surviving reasoning tokens, persistent
   tool/retrieval handle or server-side conversation id makes the generator kernel a
   function of $K_{1:t-1}$, which is post-treatment with respect to the earlier selectors
   and mediates them, and then the $q$ factors **do not cancel**. This is the default
   implementation of a multi-turn LLM user, so it is barred by assumption and checked by
   three tests, each of which must be reported:

   - **(a) Input-provenance hash.** SHA-256 of the fully rendered generator prompt is
     logged per call and must equal the hash recomputed offline from the recorded $H_t$
     and the redacted view $X^-$ alone, **byte-exact**. Any mismatch is a hard failure of
     A5.
   - **(b) Fresh-context assertion.** A new server session per call, prompt caching
     disabled, an explicit cache reset, asserted and logged per call.
   - **(c) Out-of-order replay.** Re-issue a random **2%** sample of generator calls out of
     chronological order from the same recorded $H_t$ with the same seed and require
     **byte-identical** output. For the frozen template library this is CPU-side and
     effectively free.
   - **(d) On failure of (a)–(c)** the history is redefined to include the carried state
     ($H_t$ must contain $U_t$), and A9's $\varphi$-measurability and every "no text
     critic" claim must be restated on the enlarged history. That consequence is stated
     here so it cannot be discovered after the fact.

   **(1b) Answer-withholding is an architectural invariant, not an arm (R5).** Generators
   receive a redacted view $X^-$ with the reference solution and the tests removed, and
   `signature_example` — byte-identical to `test_list[0]` on 427/427 MBPP tasks — is
   stripped from every record the feature builder or the generator can reach. Enforced by
   prompt-hash assertion in the same provenance test as (1a). Answer-visible ($A_8$
   `PATCH`) runs only as a declared positive control in the diagnostic stratum.

   **(1c) Prompt geometry is fixed across arms (R5).** The task specification is
   re-rendered at a **fixed token distance** from the generation point in every arm,
   padded with inert filler verified at $\hat\Lambda=0$. This costs nothing and removes
   the position/recency channel, which is otherwise a mediator of the randomized
   selector and would make "severity helps" indistinguishable from "task spec
   re-anchored closer to the generation point".

2. **Pre-register and version-pin**, all before any outcome of this run is examined: the
   generator library and its partition into evaluated and diagnostic sets; the coarsening
   map; the leakage scorer; the prioritized utility and its tolerances; the reference
   regime; the 87-coordinate policy-observable feature map $\varphi$ **frozen as data**;
   the 176-family file and the 5-fold assignment; the task pool file; $\lambda=0.01$ per
   turn and the grid $\{0,0.005,0.01,0.02\}$; the candidate set $\Pi$ of item 16; the
   action-feature code (`channel`, `info_cap_bits`, `carries_verdict_bit`, `suffix_words`,
   `template_index`) — these are **action features of the arm, not measured covariates of
   the message**; the baseline set B0–B7; the primary and ordered secondary outcome list;
   and any semantic feature.

   **Two additions the repairs force.**

   - **$G_0$ is frozen on an independent, already-existing log (R6).** The prioritized
     outcome's reference CDF $G_0$ is *not* pinned by pre-registering the reference
     regime $\pi_0$: $G_0$ is the mid-rank CDF of $u(Z)$ under $\pi_0$, an unknown feature
     of $P$. It is therefore computed from the sibling project's **completed
     4,488-episode log** (`ykzeng-yale/DTR-AgentEvals`, identical `tasks_sha256` —
     verified, not assumed; same machine, inference server and quantizations), hashed and
     frozen **before any outcome of this run is examined**. Zero GPU time, zero clusters
     consumed. The price, which must be stated wherever a win probability is reported:
     **the win probability is against the frozen sibling reference distribution, and
     $\pi^\star$ is reference-dependent.**
   - **A pre-registered length-calibration block (R5).** See item 7.

3. **Cap the taxonomy** — *replaces* the earlier "about 5–6 effective classes per decision
   point, floor $\delta\ge0.25$, override depth $d\le2$", which was arithmetically
   impossible ($m_G\delta\le1$ forces $\delta\le1/m_G$):

   > The frozen action set is $m=9$ ($A_0$ `STOP` plus 8 generator classes), randomized
   > uniformly over the 8 non-`STOP` classes at $e=1/8$, so the feasible floor is
   > $\delta=1/8=0.125$ and $m_G\delta\le1$ binds with equality. A floor of 0.25 would cap
   > the action set at four arms including `STOP` and is not compatible with this
   > taxonomy; **$\delta\ge0.25$ is withdrawn as infeasible.** Policy-admissible arms are
   > $\{A_0,\dots,A_5\}$; $A_6$ `DIVERT`, $A_7$ `MISDIAGNOSE` and $A_8$ `PATCH` are
   > diagnostic and barred from every reported policy and baseline. Override depth is
   > **not a free knob** (R2): declare each reported regime's entitlement class. One
   > primary randomized axis; other axes held fixed within an arm or used only as
   > pre-registered refinement coordinates.

   Consequences that must be carried wherever they appear: $M=\delta^{-d}$ is 1 at $d=0$,
   **8** at $d=1$ and **64** at $d=2$ (never 16); with $D=2$ decision points, $d=2$ **is**
   full depth, so 64 is the worst case over $\Pi_{\rm cp}$, not a knob setting; and
   $n_{\rm eff}\ge n_{\rm clusters}\delta^{d}$ gives **176 / 22 / 2.75** clusters at
   $d=0,1,2$ (230 / 28.75 / 3.59 against the pool ceiling). `STOP` is **exempt** from the
   floor: $Y(A_0\text{ at }k)=V_k$ is $H_k^A$-measurable given verifier determinism
   (1,954 replicate verifications of 597 repeated `(task_uid, sha256(final_code))` pairs,
   0 disagreements), so positivity for `STOP` holds by degeneracy, it needs no
   randomization and no nuisance model, and randomizing it at a floor would deplete
   trajectories geometrically for no information. The simulated-log arm's "floor 0.2" is
   **not** a randomization floor ($8\times0.2=1.6>1$): it is a **weight-truncation level**
   ($\hat e$ clipped below at 0.2, so $w\le5$), it introduces clipping bias, A6 does
   **not** hold in that arm (the logging policy is confounded by construction), and the
   truncation rate must be reported.

4. **Make it possible to draw several messages from the same history:** at least one
   resettable arm. The earlier prescription — "a wide-shallow training slice
   ($n_b=1$ paired contrast) and a narrow-deep benchmark slice ($n_b\ge8$)" — is
   **withdrawn on both halves.**

   - **$n_b=1$ is withdrawn as a general optimum.** With budget $B\propto n(c_0+n_b)$ the
     substituted variance $f(n_b)=(\sigma_e^2/n_b+\sigma_m^2)(c_0+n_b)$ has
     $f'(n_b)=\sigma_m^2-\sigma_e^2c_0/n_b^2$, so the optimum is **interior** at
     $n_b^\star=\max(1,\sigma_e\sqrt{c_0}/\sigma_m)$; $n_b=1$ is optimal only when
     $\sigma_m^2\ge\sigma_e^2c_0$, which is not this design's regime. The slice width must
     be chosen from a **pilot estimate of $(\sigma_e,\sigma_m,c_0)$**, not hard-coded.
   - **$n_b\ge8$ is withdrawn as unaffordable.** At 400 states $\times$ 8 classes it is
     25,600 nodes, above the 20,000-call ceiling of item 17. The frozen design is
     $n_b=3$, whose measured per-state Monte Carlo SE is **up to 0.29** with
     $\hat v\approx0.08$; the requirement is therefore *the $n_b$ the node ceiling
     permits, reported together with the resolution it buys*. At $n_b=3$ ground truth is
     usable **pooled or on strata, never per state**, and "branch eight prompts and report
     the best" carries a selection inflation of order 0.4 — roughly an order of magnitude
     above the +0.046 of measured headroom.
   - **The variance-offset slice must match the validation histories.** The debiased
     validation risk $\hat R$ is unbiased only if $E[\hat v]$ averages over the *same*
     history law as its squared-error term. Either estimate $v$ on a **uniform random
     subsample of the validation histories** ($n_b=2$ suffices for unbiasedness, at high
     variance) and verify it, or use $\hat R$ as a **ranking device only**, where the
     offset cancels: report the paired difference of squared errors with its bootstrap
     interval. The absolute risk number requires the matched-slice condition and must not
     be printed without it.
   - **Interleave and canary the deep slice.** Expanding a node's arms back to back is the
     maximal-exposure configuration for provider-side prefix/KV caching and batch-level
     numeric coupling, which no client-side check can rule out — and "caching changes
     latency and not tokens" cannot detect it, because prefix caching changes kernels and
     numerics, not token counts. Interleave branch expansions across task instances with
     a cooldown, randomize expansion order, replay a fixed-prompt canary battery each
     block, and power the duplicate-arm check on the deep slice specifically. Report the
     duplicate-arm discrepancy beside $\hat v$; **if the discrepancy exceeds $\hat v$,
     declare $\hat v$ and $\hat R$ unusable.**

5. **Use programmatically verifiable outcomes.** The primary outcome is $\psi$, a
   programmatic hidden-test verdict graded at every turn, with MBPP graded on
   `test_list[1:]` and HumanEval on the assertion-split remainder. If a judge is used at
   all it is for **secondary outcomes only**: show it the final artifact and nothing else,
   run it inside a PPI wrapper with arm-by-arm validation, and inherit the R20 optimism
   inflation term. **Horizon-invariance is then satisfied by construction rather than by a
   test that contradicts the interface** (R19): a scorer shown only the final artifact has
   no access to the turn count, so there is nothing for a turn-count calibration test to
   probe; the earlier prescription of scoring one frozen artifact presented as a short and
   then as a long conversation required showing the judge a transcript, which the same
   section forbids, and it is withdrawn in favour of the interface restriction.
   $T_{\max}=3$ throughout; no result in this document is stated at a longer horizon.

6. ~~Separate the stopping signal from the outcome score into independent channels.~~
   **REPLACED (R3) by an information-set restriction, because the two-channel requirement
   both contradicted T8 and was unnecessary under a programmatic outcome.** The
   requirement is now:

   > The stopping signal is **$\varphi$-measurable, and $\varphi$ excludes $\psi$ and
   > every hidden-test-derived quantity**, enforced by a feature-builder assertion:
   > `build_features` accepts a whitelisted record and **must raise** on any of
   > `{test_list, test, challenge_test_list, reference, signature_example, V, Y}`, with a
   > unit test per forbidden key.

   Why the replacement rather than the original: "two prespecified independent measurement
   channels" was asserted in order to stop the stopping rule reading the outcome score,
   but with a programmatic primary outcome the scorer noise is $\sigma=0$, the winner's
   curse term does not bite on the primary number, and the original requirement was
   simultaneously vacuous and in direct conflict with T8's degeneracy. The real hazard is
   the *policy* seeing the grade, and that is what the $\varphi$-exclusion assertion
   forbids. Two consequences are reported, not buried: the visible verdict is **one bit**
   on MBPP and is **absent on 20.8%** of the informative pool, and the sibling loop's own
   self-check stopped on **0.504** [0.479, 0.528] of all failures — so the implementable
   stop value $E[\psi(H_t)\mid\varphi_t(H_t)]$ is an unknown regression and the hardest
   estimation problem in the design, even though the *analyst's* stop-arm value is exact.
   The **oracle-$V$ minus $\hat p$-rule value gap is a headline pair; the oracle value is
   never reported alone.**

7. **Measure and constrain leakage, length and position — as randomized coordinates, not
   as covariates (R5).** The earlier recipe "scorer on every message, graded redaction
   series, a leakage-neutral arm, a hard answer-withheld arm, a copy-receiver placebo",
   read together with "bin $\Lambda$ and stratify randomization on the bin", is
   **withdrawn in its conditioning half**: the treatment is the selector and the message
   is drawn *after* it, so $\Lambda(\tilde A_t,H_t)$ is a descendant of the treatment and
   a plausible mediator; binning is mediator stratification with collider exposure,
   stratifying randomization on the bin is not implementable (the bin is unknown until
   after $K_t$ is drawn), and capping $\Lambda$ is rejection sampling that replaces $q_k$
   by a truncated kernel with an unknown normalizer. "Pre-receiver-response" is not
   "pre-treatment"; the correct word is **pre-outcome**, and it licenses nothing. What is
   required instead:

   1. **The action is the pair.** Pinned generators $q_{(g,\lambda)}$ *built* to a target
      leakage level by construction of their prompts, verified offline against the pinned
      library before the freeze; the pair $(g,\lambda)$ is jointly randomized at $e=1/8$.
      The graded redaction series and $A_8$ (`info_cap_bits` 12, uncapped) are library
      members at declared levels. The $\lambda$ main effect and the $g\times\lambda$
      interaction are then identified by design at the same cost as any other class
      contrast; the effect of $g$ *holding realized $\Lambda$ fixed* is **not identified**
      and is not reported.
   2. **$\hat\Lambda$ is a fidelity measurement, never a stratifier and never a filter.**
      Report the observed $\hat\Lambda$ distribution per arm against the declared level.
   3. **Rejection sampling on realized $\Lambda$ is prohibited confirmatorily.** If run at
      all it is a separate arm, labelled a redefinition of the generator with an
      uncomputable density, excluded from P4, and reported as ITT over the *unfiltered*
      generator with the rejection rate.
   4. **$\Lambda$ is redefined as conditional information:** the log-likelihood gain of a
      fixed reference receiver on the reference solution given $(H_t,\tilde A_t)$ relative
      to given $(H_t,\text{null message})$ — condition on task and prior output, withhold
      nothing but the message. The **task-blind placebo solver is withdrawn**: "you forgot
      the base case" carries near-zero information to a solver that has not seen the task,
      so leakage here is almost entirely task-conditional and a task-blind scorer has no
      dynamic range over exactly the messages that matter. The earlier caveat "unsigned"
      is **wrong in a known direction**: $\hat\Lambda$ *understates* leakage, which makes
      any leakage-controlled contrast look **larger**. Validate dynamic range on a planted
      set (messages that literally state the fix at the top; pure-affect messages at the
      bottom).
   5. **Hard gates stay, as gates and not as estimands.** Any emitted message tripping G2
      (an `assert` or `==`) or G3 (hidden-input AST call-key overlap) is a protocol
      violation: halt, quarantine the run directory, record it. The template arms trip
      these at 0.000 by construction.
   6. **A pre-registered length-calibration block, not a second primary axis.** Severity
      and specificity classes differ systematically in token count, so length is caused by
      the randomized selector and is a mediator; the earlier remedy ("within a $\Lambda$
      bin, message length no longer predicts $Y$") is a low-power observational regression
      on post-treatment variables and is withdrawn. Instead: each class at **2**
      pre-registered token budgets plus a **filler-only arm** (pure context-length
      increase, no semantic content) — 190 tasks $\times$ 3 arms $\times$ 1 turn
      $\approx$ **570 calls $\approx$ 0.27 h**. The class effect is reported **net of the
      measured length main effect** from that block, and without the block the class effect
      is confounded with length by design-mediation — which the text must say.

8. **Report the statistical budget alongside every point estimate:** per-turn
   $\hat\chi^2_t$, ESS, $\hat D_2$, $n_{\rm eff}$, $\kappa(\pi)$, and the effective sample
   size of every weighted quantity. Two requirements on the units:
   $n_{\rm eff}$ is quoted in **independent task clusters** and checked against
   $n_{\rm clusters}=176$ (ceiling $\approx230$ on the 3B, $\approx100$ on the 7B), never
   in conversations; and the budget is reported **by entitlement class** — $\Pi_0$
   (stopping-only) carries $W\equiv1$ so ESS is trivially $n$ and no weighted quantity
   exists, $\Pi_1$ carries $W\le8$ and must print ESS and $\hat D_2$ with every number,
   and $\Pi_2=\Pi_{\rm cp}$ carries $W\le64$ and **2.75 effective clusters**, which is why
   its values come from on-policy rollout and not from weighting.

9. **Include a randomized calibration arm implementing the same intervention by
   best-of-$K$ / softmax-of-$K$ selection** — the only direct audit of exchangeability at
   the level of the estimand — **conditional, priced, and with its own leakage table.** It
   runs **only if** the coarsening-sufficiency test rejects at $\alpha=0.05$: if the
   coarsening is sufficient, a free-form proposal is scored only through its class label,
   so best-of-$K$ cannot beat the masked argmax within the critic's resolution and running
   it spends GPU to re-measure the same quantity with extra noise. A non-rejection must be
   quoted as **evidence against template effects of 0.08** (power 92%; 57% at 0.06), not
   as evidence of exact sufficiency. Cost if it runs: $\approx$**3,800 rollouts**
   ($\approx$0.85 GPU-h on the 3B proposer). A free-form arm voids the information-cap
   guarantee, so every emitted message passes the item-7 gates, the rejection rate is
   reported, and the arm is **outside every guarantee in this document** — it is not a
   member of $\mathcal K$ and its value is neither identified nor certified.

10. ~~Include a negative-control intervention on a causally inert dimension.~~
    **REPLACED (R5/R7-adjacent, from the falsification audit): the politeness-style
    negative control has no valid null in this document's own framework**, which asserts
    that a frozen receiver is paraphrase-sensitive, so a non-zero effect is a *true* effect
    of the intervention on the pinned receiver rather than an indictment of the design, and
    the test commits the error of testing an a-priori-false $H_0$. Replaced by two controls
    whose truth is known by construction, both already in the frozen taxonomy:

    - **Guaranteed null:** an arm perturbing only text rendered to the user-side channel
      and **provably withheld** from the receiver's context, using the interface isolation
      of T25(d) — a software-verifiable zero on $Y$.
    - **Guaranteed positive:** $A_8$ `PATCH`, which appends answer-bearing content, whose
      effect must be large. It is reported as the design's **measured ceiling and leakage
      upper anchor**, the scale against which every other arm is read, and **never** as the
      effect of feedback.

    $A_6$ `DIVERT` and $A_7$ `MISDIAGNOSE` remain in the **diagnostic stratum**: they are
    informative about the resampling and targeting channels and they appear in the critic's
    training data and in the leakage/placebo tables, but they are barred from every $\pi$,
    from $\mathcal A_{\rm adm}$, and from every reported baseline value.

11. **Run the branch falsification battery and publish its results, with the power of each
    item stated.** The earlier closing claim — "a run without it is not an experiment" —
    is **weakened**, because the document concedes that no item in the battery has both a
    valid null and demonstrated power: the weight diagnostic has no power when weights are
    degenerate (and in the tree they are known and non-degenerate, so it tests nothing),
    the permutation test is not exact under an adaptive design, and power against state
    leakage is **OPEN**. The honest requirement: report each item with what it can and
    cannot detect and at what power, plus the two known-truth controls of item 10, and do
    not present a passing battery as evidence of correctness. What a failure *does* license
    is unchanged and is strong: any failure of the item-1 provenance tests, of the
    $\varphi$-exclusion assertion, or of the item-7 gates is a hard halt.

12. **Block against drift; cluster by the inference unit only.** Randomize task order,
    stratify by time block, stamp every episode with the model digest, config hash, code
    hash and the foreign-load fields. The earlier prescription "**cluster by epoch and
    model-version epoch**" is **withdrawn as incoherent with A2**: a mid-run change of
    model version does not make the estimand noisy, it makes it **undefined**, and adding
    an epoch dimension to the variance estimator prices a between-version comparison the
    document forbids. The standard-error cluster is the **task family, and only the task
    family** (176 families; seeds, branches, turns, templates and paraphrase variants are
    within-cluster). If the model version changes mid-run, the affected blocks are
    discarded and reported as discarded, not clustered over. Blocks are complete across all
    arms simultaneously, so truncation is uninformative with respect to arm. The check
    "verify caching changes latency and not tokens" is **withdrawn as non-diagnostic** and
    replaced by the canary battery and duplicate-arm checks of item 4.

13. **Log the full cost channel separately** (prompt/completion tokens, turns, tool calls,
    latency, money) and report the cost-priced value, never quality alone. $\lambda=0.01$
    per turn is **pre-registered** from the measured budget; if more than one point of the
    grid $\{0,0.005,0.01,0.02\}$ is reported, every interval carries a **union bound over
    the grid** and $\lambda$ is called what it then is, a hyperparameter. A $\hat\lambda$
    read off the estimated (value, cost) frontier voids the stated level and is
    prohibited. Report per arm: mean receiver generation calls, mean completion tokens,
    mean wall seconds, mean turns to stop; a policy exceeding the primary comparator's
    mean completion tokens by more than **10%** has not met the primary criterion even
    with a positive point estimate. **Degradation is a separate reported outcome, never
    folded into a mean** (measured: repair **0.239** [0.210, 0.270] against degradation
    **0.162** [0.105, 0.242], so iteration destroys about one already-correct answer in
    six).

14. **Report bounds, not point estimates, wherever $\kappa(\pi)>0$**, and report four
    denominators in one mandatory table. The earlier instruction to report "the
    truncated prophet benchmark and the **natural-policy value** as free denominators" is
    **corrected**: in this design there is no natural policy in the data — the harness
    replaced the user, so $e$ is the analyst's own randomizer, and "natural/logging policy"
    fused two different objects. The word **"natural" is deleted**, and $V(e)$ is demoted
    to a diagnostic denominator computed on the **evaluated stratum $\{A_0,\dots,A_5\}$
    with the diagnostic arms excluded** — because $V(e)$ over the full library is
    **monotone in the number of deliberately degraded arms** and a gap against it is
    manufacturable with zero learning. The mandatory table:

    | # | denominator | role |
    |---|---|---|
    | (a) | single-shot, no feedback | floor |
    | (b) | **B2**, fixed unary retry to $T_{\max}$, no stopping rule | the zero-information arm `positioning.md` constraint 2 makes mandatory |
    | (c) | **B4**, best marginal class on the training folds plus stop-iff-`visible_pass` | **the headline comparator** |
    | (d) | truncated prophet bound (P22, R21) and $V(e)$ on the evaluated stratum | diagnostics only |

    **The headline gap is against B4**, which strictly dominates a fixed-string
    denominator: B2 breaks one already-correct answer in six, so beating B2 is nearly free
    and proves nothing — sizing against B2 gives an apparent **+0.07 to +0.12**, against
    B4 **+0.015 to +0.030**. The estimator is the paired, common-root, family-clustered
    one (E0): mean over the 176 families of the family-mean paired difference on the 1,520
    paired units, paired family-clustered bootstrap, measured half-width **$\pm0.019$** at
    $R=8$ and **MDE 0.027** at 80% power. **The finite-sample improvement certificate (T20)
    is withdrawn as a deliverable** — at the honest inference unit the smallest gap it can
    resolve is 0.542 against 0.046 of available headroom, and it is arithmetically
    impossible for any weighted regime — so no reporting requirement in this section may
    be discharged by citing it, and the earlier claim that a certified strict improvement
    over the logging policy is among the deliverables is withdrawn wherever it appeared.

15. **Do not report a generator-replacement or late-continuation estimand from logs as if
    identified.** Evaluate such policies by running them, and say explicitly what was not
    estimated. This extends to two cases the repairs surfaced: a **full-depth regime**
    ($\Pi_2$, $d=D=2$) has 2.75 effective clusters off-policy and its value must come from
    on-policy rollout or a re-logged policy-iteration step, with off-policy certification
    explicitly disclaimed; and a **free-form generative policy** whose messages leave the
    pinned library is outside every guarantee here and must be reported as such.

16. **Declare $|\Pi|$ — the pre-registered candidate count — here, before any fit.** This
    is the declaration the rest of the document points at, and the placeholder `100` is
    forbidden. The frozen candidate set, drawn from `docs/design_e3_critic_policy.md`
    §9–§10 and restricted to $\mathcal A_{\rm adm}=\{A_0,\dots,A_5\}$, has
    $\boxed{|\Pi|=8}$ members:

    1. the boosted two-part critic's masked argmax at $\lambda=0$ (the greedy-in-$\varphi$
       member, labelled as such);
    2. the same, cost-adjusted at $\lambda=0.01$ per turn;
    3. the pre-registered linear-blip (RidgeCV) critic's argmax, the misspecification check;
    4. the myopic critic ($\gamma_2\equiv0$ inside the continuation value);
    5. the correlational supervised critic's argmax;
    6. **B4**, best marginal class plus stop-iff-`visible_pass`;
    7. **B2**, fixed unary retry to $T_{\max}$;
    8. single-shot (`STOP` at the first decision point).

    All eight are evaluated **on-policy** in the paired head-to-head, so their entitlement
    class matters only for any off-policy reuse of the branch tree. Any interval that
    ranges over this set carries $L=\log(4|\Pi|/\alpha)=\log(640)=6.461$ at $\alpha=0.05$;
    the same arithmetic at $|\Pi|=100$ gives $L=\log(8000)=8.987$, a factor of 1.39, and
    both are printed wherever the sensitivity matters. If the set changes before the
    freeze, the count is restated here and $L$ recomputed; it is never changed afterwards.
    Where an **infinite** class is at issue — $\Pi_{\rm cp}$ as a $\sigma$-algebra
    restriction rather than a finite list — a covering-number bound would be required and
    **we do not have one**; the reported object is $\hat\pi=\arg\max_{\pi\in\Pi}\widehat
    V(\pi)$ over this list, evaluated out-of-fold with the winner re-estimated on held-out
    families and the selection inflation reported. The phrase "the optimal regime" is
    reserved for $\arg\max_{\Pi_{\rm cp}}V$, which this design does not report.

17. **Price every prescription in this section against the measured ceiling, and cut what
    does not fit.** The affordability ceiling is **20,000 receiver calls**. Provenance, with
    the conflict stated rather than resolved: single-attempt throughput was measured at
    $\approx$2,150 calls/hour (3.2 s per 3B call at four contended slots), which puts
    20,000 calls at $\approx$9.3 h; `docs/measured_calibration.md` then **supersedes that
    figure for multi-turn work** with a measured 3.96 s per 3B call, $\approx$909
    calls/hour, which puts the same 20,000 calls nearer 22 h. Either way the binding unit
    is calls, and the frozen programme sits just under the ceiling: depth-2 supplement
    3,200; pilot 1,523; shared roots 1,520; policy continuations 13,908; **total
    $\approx$20,151 rollouts**, with the $R=12$ contingency at 26,428 and the conditional
    best-of-$K$ arm at +3,800. A prescription above the ceiling is **cut or marked
    unaffordable**, and this section marks two: the $n_b\ge8$ deep slice (25,600 nodes,
    item 4) and the improvement certificate (24,429 clusters at the only measured gap,
    i.e. 139$\times$ the available 176, item 14). Every null is reported with the realized
    $n$, the realized half-width and the MDE, because a null from a design with a stated
    MDE is evidence and a null without one is nothing.

---

### One-paragraph verdict

The primary route achieves genuine, design-based identification of turn-specific blips,
$Q$-functions and regime values over a finite, pinned, semantically meaningful prompt
action space that includes `STOP` — with sequential exchangeability, positivity and
propensity knowledge holding *by construction* at the feasible floor $\delta=1/8$ over the
eight randomized classes (`STOP` needing no randomization at all, since its potential
outcome is analyst-measurable by verifier determinism), sequential DR exactly unbiased for
any cross-fitted, internally consistent outcome model, and branch-sampled ground truth for
validating the estimators pooled or on strata. Five things earlier claimed here are
withdrawn and are named rather than dropped: the **finite-sample improvement certificate**
against the logging policy (numerically vacuous at the honest inference unit — smallest
resolvable gap 0.542 against 0.046 of measured headroom — unaffordable at any gap worth
certifying, and certified against a denominator monotone in the number of deliberately
degraded arms); **"the optimal regime"**, which is reserved for
$\arg\max_{\Pi_{\rm cp}}V$ and not reported, the reported object being the best member of
a declared 8-policy candidate set, selected on a non-sufficient feature map where backward
induction returns the greedy rule rather than the restricted optimum; the **known
stop-arm value** as a policy-side advantage, since the grade is known to the analyst and
withheld from the policy, whose implementable stop value is an unknown regression and the
hardest estimation problem in the design; the **prioritized win probability** as a primary
estimand, demoted to a secondary reporting device on a frozen, reference-dependent $G_0$;
and the **"costs about what a stratified A/B test costs"** comparison, whose honest
multiple is 50–120$\times$. What remains, and is worth the paper, is threefold: a
prospectively randomized, propensity-logged multi-turn design with a programmatic outcome
and branch-sampled ground truth; **honest effect reporting** from interaction logs, where
the failure of unadjusted comparisons is dramatic and robust; and a paired, on-policy,
family-clustered head-to-head against a strong pre-registered baseline at a measured
$\pm0.019$ half-width on 176 clusters. The framing of the machinery as the route to better
*decisions* is a scoped secondary claim, not the headline: the project's own premise checks
found a plain state-conditioned critic recovering the exact optimal regime 39/40 times,
latent confounding moving regret by at most 0.030, known-propensity IPW repairing the
residual only partly and non-monotonically, and the dominant decision-level error being
**myopia, which loses under randomization too and is therefore not a confounding failure at
all** — so the pre-registered comparator the framework must beat is a non-myopic
correlational critic, and the expected result of that comparison is null. The measured
headroom is +4.6 points of final success from **oracle** stopping, which lives in the
stopping coordinate: that deliverable sits in $\Pi_0$, needs no importance weights, no
full-depth blip estimator and none of the machinery the certificate priced, and is gated on
information the intervener does not have. Framing, likewise scoped: prompt-as-treatment,
DTR/$Q$-learning over a natural-language action space (arXiv:2502.17538), longitudinal
causal inference over text-feature sequences (arXiv:2605.07834), single-period text-treatment
identification (arXiv:2410.00903), per-context off-policy prompt policy learning
(arXiv:2504.02646), neural SNMM/blip estimation (DeepBlip, arXiv:2511.14545) and orthogonal
DR $Q$-learning (DRQ-learner, arXiv:2509.26429) are **cited, not claimed**. It does not
identify the effect of any particular sentence, the value of a generator outside the
library, the effect of a class holding realized leakage fixed, or anything about a real
human user population; those are, respectively, an estimability barrier, a design boundary,
a post-treatment barrier, and a transport problem with one term we cannot estimate. Written
this way — with the withdrawals in the text, the unit in clusters, and the gap measured
against B4 — it is a paper. Written as "we intervened on the prompt and measured the
effect", it is not.
