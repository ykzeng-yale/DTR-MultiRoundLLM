# Causal value models for adaptive prompting: estimands, identification, estimation, and decisions

**Version:** 2026-09-19. **Status:** results proved below under the stated assumptions; initial mathematical audit completed, independent review pending. This is an initial research theory package, not a claim of new foundational DTR theory or completed empirical validation. Companion audit: [theory_proof_audit.md](theory_proof_audit.md).

## 1. Scientific question and contribution boundary

For a fixed receiver LLM, tool environment, task distribution, and evaluator, what would happen if the next feedback prompt were changed, and which supported adaptive prompting policy improves final task performance after accounting for cost? The intended deployed system observes a request and the receiver's answer, generates possible feedback, scores their downstream values, chooses feedback or STOP, and repeats. We call the score a **causal prompt value model** only when the intervention, continuation policy, outcome, and identification assumptions are explicit.

The object is a history-conditional expected counterfactual outcome or contrast, not an individual's unknowable realized treatment effect. A neural value predictor and a generative actor do not themselves establish causality. Randomization or defensible sequential exchangeability establishes identification; function approximation estimates an identified functional; independent evaluation establishes whether decisions improve.

The core DTR, g-computation, importance weighting, augmentation, and policy improvement arguments are established statistical ideas. This package specializes and connects them to a two-stage language intervention: **generate a candidate slate, then randomize a selected candidate**. Potential research contributions are the support-aware language intervention design, history-conditional learning and calibration, candidate-generation versus selection error decomposition, and empirical evidence that the resulting decisions improve over adequately adjusted alternatives. Novelty requires a separate literature audit. Merely using a Transformer, calling a critic causal, or applying DTR to prompts is insufficient.

## 2. Timeline, unit, and exact intervention

### 2.1 Unit and time origin

The primary independent unit is a **root task** sampled from a declared target population. A root can produce several randomized continuations, but those continuations are not independent roots. A user with several related tasks can instead be the independence cluster when cross-task dependence is material.

Let $X$ be the fixed original user request and baseline metadata; let $O_0$ be the receiver's initial answer. Set $H_1=(X,O_0,\text{baseline metadata})$. Turns $t=1,...,T$ are subsequent feedback opportunities. Thus this version estimates feedback effects conditional on the initiating request; it does not estimate the effect of choosing an entirely different original task. To study initial-prompt wording, hold the underlying task and target answer fixed and add an initial randomized wording decision before $O_0$.

At turn $t$:

1. Observe full pre-generation history $H_t$.
2. Draw an ordered candidate slate $C_t=(a_{t1},...,a_{tK_t})$ from a frozen generator kernel $G_{0t}(dc|H_t)$.
3. Observe all eligible candidates, including an explicit $\mathrm{STOP}$ candidate, then draw index $J_t$ from logging selector $b_t(j|H_t,C_t)$.
4. Render and send the exact selected intervention $A_t=a_{tJ_t}$; observe response, costs, and the next history.

The mathematically general action is $U_t=(C_t,J_t)$. Treating this compound action as the intervention avoids hidden assumptions about whether unselected candidates affect cost or future controller behavior. A contrast between $j$ and $j'$ within the same realized slate holds generation fixed and changes the selected prompt.

$H_t$ includes every variable used by the controller or generator, receiver-visible transcript, prior actions, past outputs, available tool results, remaining budget, model versions, and relevant logged prior slate/selection information. It never includes a hidden test label or future evaluator result unavailable at deployment. If previous candidates are neither retained nor used by any future mechanism, they can be omitted by a declared conditional-independence restriction. A learned embedding is not automatically a sufficient replacement for $H_t$.

Candidate order, duplicates, truncation, formatting, tool attachments, forbidden-action filters, and rendering are part of treatment definition. The same text at two indices can have different index probabilities. Keep indices and the full slate in the log; do not silently treat index propensity as marginal text propensity.

### 2.2 Frozen environment and rewards

Freeze receiver model/version, system instruction, decoding parameters, tools, retrieval corpus snapshot where feasible, and evaluator definition. Stochastic receiver responses remain part of the transition distribution. New model versions or externally changing tool state require a new environment stratum or a transport assumption, not a silent pooling operation.

Let $R_t$ be a bounded turn utility, often minus the measured incremental computational cost. Let $Y=y(H_{T+1})$ be terminal quality under a prespecified scoring rule. The total utility is

$$
U^{\mathrm{tot}}=\sum_{t=1}^{T}R_t+Y.
$$

One equivalent implementation sets all $R_t=0$ and includes cumulative costs in terminal $Y$. Do not count costs twice. Report quality, cost, and stopping time separately even when optimizing $Y-\lambda \,\mathrm{cost}$; choose $\lambda$ before the confirmatory comparison. Resource-constrained optimization and multivariate outcomes are valid alternative targets but are not automatically summarized by a single scalar value.

Generation cost is incurred before selection and is charged even if STOP is then chosen. A cheaper pre-generation stopping gate is a distinct decision stage. A baseline that receives fewer model calls is not cost-matched merely because both systems use the same number of feedback turns.

### 2.3 STOP, missingness, and failure

STOP accepts the current output. It is an observed treatment that leads to an absorbing state: after STOP, pad the horizon with a deterministic dummy STOP, no further cost, no new receiver call, and an unchanged terminal output. The deterministic padding has likelihood ratio one. Randomized support is required for the actual stop/continue decision, not for artificial padding.

An API failure, missing final score, or lost log is not STOP. A timeout can be a prespecified unfavorable outcome, or it can be censoring requiring a separate observation model. Deleting failed calls estimates a selected-success population. The theorems below assume all defined rewards and terminal outcomes are observed. Missing-at-random and positive observation probabilities can justify added censoring weights; informative missingness is not repaired by treatment weights alone.

## 3. Policies and estimands

A target policy consists of an externally specified generator $G_t^*$ and selector $\pi _t$; write $d_t(dc,j|h)=G_t^*(dc|h)\pi _t(j|h,c)$. The logging action kernel is $e_t(dc,j|h)=G_{0t}(dc|h)b_t(j|h,c)$. Integrals below include a sum over the finite slate indices.

Main first-stage deployment/evaluation freezes $G_t^*=G_{0t}$ and learns only the selector. Its **marginal text policy** is

$$
\bar\pi_t(a\mid h)=\int G_{0t}(dc\mid h)
  \sum_j\pi_t(j\mid h,c)1\{c_j=a\}.
$$

The logged probability $b_t(J_t|H_t,C_t)$ is a conditional selection propensity, not $P(A_t=a|H_t)$ and not a candidate generator token probability.

Define remaining-utility value and action value by a policy-specific Bellman recursion:

$$
V_{T+1}^d(h)=y(h),\qquad
Q_t^d(h,c,j)=E\{R_t+V_{t+1}^d(H_{t+1})\mid
                    H_t=h,\operatorname{do}(C_t=c,J_t=j)\},
$$
$$
W_t^d(h,c)=\sum_j\pi_t(j\mid h,c)Q_t^d(h,c,j),\qquad
V_t^d(h)=\int G_t^*(dc\mid h)W_t^d(h,c),
\qquad \mathcal V(d)=E\{V_1^d(H_1)\}.
$$

Every $Q$ depends on the **future** policy. A score trained for generic retry continuation cannot be relabeled as the value under a newly optimized autonomous continuation without updating or reevaluating that continuation.

The within-slate history-specific contrast is

$$
\tau_t^d(h,c;j,j')=Q_t^d(h,c,j)-Q_t^d(h,c,j').
$$

This answers: among roots at this history and realized slate, what expected downstream utility changes when selecting this candidate instead of the comparator and then using $d$? STOP, a specific fixed prompt, or a prespecified stochastic baseline can be the comparator. Historical costs before this decision cancel in the contrast.

A more compact $Q_t^d(h,a)$ requires a **slate-exclusion assumption**: conditional on $h$ and exact rendered $a$, transition utility and every future policy-relevant variable are invariant to unselected candidates and index. If generation cost is already sunk and subtracted from both compared values, exclusion can hold for the remaining receiver outcome even when it fails for total system cost. If future policies retain slate content, or the receiver sees multiple candidates, exclusion can fail. In those cases retain $(h,c,j)$.

For a newly arriving user, these are population conditional means for histories like the observed history under the stated environment. Exact-history conditional means are defined almost surely; a unique long transcript typically has no replicated observations. Neural generalization and uncertainty at that transcript require regularity and training support beyond identifiability of a population functional.

## 4. Identification assumptions

**A1 (well-defined intervention and consistency).** Selected rendered prompt, slate-generation protocol, STOP, response mechanism, and utility are sufficiently specified. Observed outcomes equal the corresponding potential outcomes for the realized actions. There is no interference across independent root clusters; copying a live state and executing a branch must not mutate another branch's tools or hidden memory.

**A2 (sequential exchangeability).** Conditional on full $H_t$, assignment of $U_t$ is independent of future potential rewards and states under supported interventions. For fixed-generator selection comparisons this can be stated in two steps: slate generation uses only $H_t$ and independent randomness; conditional on $(H_t,C_t)$, randomized $J_t$ is independent of future potential outcomes. Observational human-feedback logs need all common causes of treatment and outcome measured; latent human knowledge or inaccessible task facts can violate this condition.

**A3 (sequential support).** At every history reachable under the target, $d_t$ is absolutely continuous with respect to $e_t$. Ratios must be finite for identification; bounded or sufficiently integrable products are additionally needed for precision and asymptotic inference. Under the same generator the requirement reduces to $\pi _t(j|h,c)>0 \Rightarrow  b_t(j|h,c)>0$, together with support along the preceding target trajectory. Deterministic target selection is permitted when its selected indices have logging support.

**A4 (stable transition and measurement law).** Conditional transition kernel $P_t(d r,d h'|h,c,j)$ and scoring rule apply both in logging and target execution. This is not assured by adjusting for a model-name string if the underlying model, tools, evaluator, or task distribution changed.

**A5 (sampling and integrability).** Root clusters are independent under the primary design; relevant moments exist. Additional boundedness/rate conditions are stated at the result where needed.

These assumptions do not require a low-dimensional Markov state: full history is always the state in this formulation. They also do not make observational confounding an inherent flaw of ordinary Q regression. Correct sequential regression on full sufficient history identifies the same causal Q under A1–A4. A fair comparison includes this adequately adjusted regression, as well as confounded marginal reward prediction.

### Theorem 1: longitudinal identification and change of measure

Under A1–A4, the counterfactual law under $d$ is identified by

$$
 p^d(dh_1,d\bar u,d\bar r,d\bar h')=
 p(dh_1)\prod_{t=1}^T d_t(du_t\mid h_t)
          P_t(dr_t,dh_{t+1}\mid h_t,u_t).
\tag{1}
$$

The preceding Bellman equations identify $Q_t^d$, $V_t^d$, and $\mathcal V(d)$ on supported histories. With

$$
\rho_t=\frac{d_t(U_t\mid H_t)}{e_t(U_t\mid H_t)},\qquad
\Omega_t=\prod_{s=1}^t\rho_s,\quad\Omega_0=1,
$$

and integrable quantities, the value also satisfies

$$
\mathcal V(d)=E_e\!\left[\sum_{t=1}^T\Omega_t R_t+\Omega_TY\right].
\tag{2}
$$

**Proof.** Consistency identifies the observed transition conditional on a realized treatment with the corresponding potential transition. Sequential exchangeability removes selection into that treatment conditional on prior full history. Apply these facts at the final decision, then induct backward to replace every counterfactual transition by $P_t$. Integrating the last transition proves the terminal Bellman step; iterating proves (1) and the complete recursion. Absolute continuity implies that the target law through transition $t$ has Radon–Nikodym derivative $\Omega_t$ with respect to the logging law through that transition; all transition factors cancel. Therefore $E_d R_t=E_e(\Omega_tR_t)$ and $E_dY=E_e(\Omega_TY)$. Sum these equalities. No cross-world joint distribution of two different action outcomes has been used. ∎

**Same-generator corollary.** If $G^*=G_0$, then $\rho_t=\pi _t(J_t|H_t,C_t)/b_t(J_t|H_t,C_t)$. The generator probabilities cancel even if a black-box generator cannot provide tractable sequence likelihoods. This does **not** authorize changing that generator while retaining the ratio.

**Generator-change corollary.** For a different generator with supported, evaluable density ratio,

$$
\rho_t=
\frac{dG_t^*(\cdot\mid H_t)}{dG_{0t}(\cdot\mid H_t)}(C_t)
\frac{\pi_t(J_t\mid H_t,C_t)}{b_t(J_t\mid H_t,C_t)}.
\tag{3}
$$

This is the density of the complete ordered slate after its actual sampling, filtering, and deduplication procedure. Multiplying raw token probabilities is correct only if it exactly reproduces that procedure. Without support or a valid generator ratio, collect new randomized trajectories under the revised frozen generator. Updating an actor is an engineering operation; it is not automatically an identifiable offline causal evaluation.

### Proposition 2: limits of individual and unsupported-prompt claims

(a) Randomized data do not generally identify the distribution of literal individual effects $Y_i(a)-Y_i(a')$.

(b) Without support or structural extrapolation assumptions, the value of an arbitrary unseen prompt is not nonparametrically identified.

**Proof.** For (a), let the two potential outcomes each be Bernoulli with probability one half. In model I they are identical; in model II they are complements. Independently randomized treatment yields the same observed distribution in both models. Every individual effect is zero in I, whereas effects are $-1$ or $+1$ in II. Thus the observed law identifies both means and their difference, but not the individual-effect distribution. For (b), choose an action with zero logging probability at a target-relevant history. Two transition kernels can agree on every observed action and assign terminal means zero and one, respectively, to this action. They induce the same logging law and different target values. ∎

Formal positive token probability for every string is weaker than useful support: probabilities can be so small that finite-sample estimation is effectively unconstrained. Embedding proximity and a language-model prior are extrapolation assumptions, not replacements for this argument.

## 5. Representations, text treatments, and what a neural critic must learn

Let $S_t=f(H_t)$ and $Z_t=z(A_t)$ be representations. Three distinct claims should not be conflated:

* **Prediction approximation:** a sufficiently flexible $q(S,Z)$ predicts observed outcomes well.
* **Decision sufficiency for a fixed continuation:** $Q_t^d(h,c,j)=q_t^d(f(h),z(c_j))$ for every supported action under the declared exclusion restrictions.
* **Controlled Markov sufficiency:** conditional reward and the next represented state depend on full history and intervention only through the represented state/action; terminal quality is a function of the terminal representation; target/logging policies and generator laws are representable on the same state when a reduced-state likelihood is used.

The second permits estimating the specified Q; the third supports recursive planning and reusable Bellman equations for policies measurable in the representation. Neither follows from a high-dimensional encoder architecture or from predicting average reward accurately.

### Proposition 3: sufficient representations and a counterexample

Suppose for all admissible actions the conditional law of $(R_t,S_{t+1})$ given full history and action depends only on $(S_t,Z_t)$, terminal $Y$ is measurable in $S_{T+1}$, slate exclusion holds, and the target generator/selector uses only the represented variables. Then backward recursion gives $Q_t^d(h,a)=q_t^d(S_t,z(a))$.

**Proof.** At the terminal stage the value is measurable in $S_{T+1}$. If $V_{t+1}^d$ is a function of $S_{t+1}$, conditional expectation of $R_t+V_{t+1}^d$ is a function of $(S_t,Z_t)$ by the controlled transition restriction. Integrating over a represented target policy makes $V_t^d$ a function of $S_t$. Induct backward. ∎

Without these restrictions, let $H$ be a fair binary variable, $A$ be independently randomized binary treatment, and $Y=1(A=H)$. An encoder $S=0$ loses no marginal mean prediction beyond the constant one half, but both encoded action means equal one half; the full-history policy $A=H$ achieves one and an encoded policy achieves at most one half. Thus randomization survives in this example while action-relevant heterogeneity is destroyed. In observational data, collapsing a true confounder can additionally destroy exchangeability.

A prompt embedding $z(a)$ can collapse wording variants with different effects. A well-defined intervention $do(Z=z)$ then requires either treatment-version irrelevance or a specified distribution over exact strings mapping to $z$. The latter is a stochastic textual intervention, with value depending on that distribution. Decoding an optimized embedding into a new string does not prove either property.

## 6. Longitudinal doubly robust evaluation

### 6.1 Target fixed outside the evaluation sample

First freeze $d$ independently of the evaluation sample. This can be a prespecified policy or a policy learned on separate training roots. All nuisance functions below are also fixed when taking conditional expectations; cross-fitting implements this condition fold by fold.

Let $\widehat Q_t(h,u)$ be any bounded candidate Q functions and let

$$
\widehat V_t(h)=\int d_t(du\mid h)\widehat Q_t(h,u),\qquad
\widehat V_{T+1}=Y.
$$

Let $\widehat e_t$ be positive on target support and define

$$
\widehat\rho_t=d_t/\widehat e_t,\qquad
\widehat\Omega_t=\prod_{s=1}^t\widehat\rho_s.
$$

The score is

$$
D_d(O;\widehat\eta)=\widehat V_1(H_1)+
\sum_{t=1}^T\widehat\Omega_t
\{R_t+\widehat V_{t+1}(H_{t+1})-\widehat Q_t(H_t,U_t)\}.
\tag{4}
$$

A terminal-utility implementation has $R_t=0$ and $\widehat V_{T+1}=Y$ including its accumulated costs. The cross-fitted value estimate averages (4), with every root and all of its branches confined to one fold.

### Theorem 4: exact remainder and stagewise robustness

Let $\delta_t=\widehat Q_t-Q_t^d$, and assume integrability. Then

$$
E_e D_d(O;\widehat\eta)-\mathcal V(d)=
\sum_{t=1}^T E_e\!\left[
 \widehat\Omega_{t-1}
 \int d_t(du\mid H_t)
 \left\{1-\frac{e_t(u\mid H_t)}{\widehat e_t(u\mid H_t)}\right\}
 \delta_t(H_t,u)
\right].
\tag{5}
$$

Thus the score is unbiased when all assignment mechanisms are correct or all target-continuation Q functions are correct. More generally, each stage's summand is zero if **at that stage** either $\widehat e_t=e_t$ or $\widehat Q_t=Q_t^d$. Arbitrary stagewise choices of these conditions suffice. This statement concerns actual target Q functions, not regression fits that may inherit misspecification from earlier pseudo-outcomes.

**Proof.** Write $\widehat V_t=V_t^d+\delta V_t$ where $\delta V_t(h)=\int d_t\delta_t$, and $\delta V_{T+1}=0$. For every $t$, the true Bellman residual $R_t+V_{t+1}^d-Q_t^d$ has conditional mean zero given $(H_t,U_t)$, hence its product with $\widehat\Omega_t$ also has mean zero. Subtract $\mathcal V(d)$ from the mean of (4). The remaining expression is

$$
E\delta V_1+\sum_{t=1}^TE\{
\widehat\Omega_t\delta V_{t+1}
-\widehat\Omega_t\delta_t(H_t,U_t)\}.
$$

Reindex the first term of the sum, using $\widehat\Omega_0=1$ and $\delta V_{T+1}=0$, to obtain

$$
\sum_{t=1}^TE\{\widehat\Omega_{t-1}\delta V_t
-\widehat\Omega_t\delta_t(H_t,U_t)\}.
$$

Conditional on $H_t$, integrate the second term under the true action law $e_t$: it equals $\widehat\Omega_{t-1}\int e_t(d_t/\widehat e_t)\delta_t$. Subtraction gives (5). All robustness statements follow by making either factor in each integrand zero. ∎

For a fixed same generator, use $\widehat e=G_0\widehat b$ and $d=G_0\pi$. Equation (5) reduces to

$$
\sum_t E\!\left[\widehat\Omega_{t-1}
\int G_{0t}(dc\mid H_t)\sum_j π_t(j\mid H_t,c)
(1-b_t/\widehat b_t)\delta_t(H_t,c,j)\right].
\tag{6}
$$

Known randomization probabilities should ordinarily be used as logged. Estimated propensities cannot fix missing intervention support. Weight clipping changes the exact identity and trades bias for variance; report it as a sensitivity estimator alongside unclipped identification targets.

### 6.2 Orthogonality and rates

Equation (5) is a product remainder. At truth, a small perturbation in either nuisance while the other stays true has zero first derivative in the score mean. This is the claimed Neyman orthogonality; it is not a guarantee about a neural optimizer finding the correct functions.

For a conditional-on-training statement, define the finite weighted stage measure

$$
\mu_t(dh,du)=E_e\{\widehat\Omega_{t-1}1(H_t\in dh)\}\,d_t(du\mid h).
$$

Cauchy–Schwarz applied directly to (5) gives the precise bound

$$
|E D_d-\mathcal V(d)|
\le\sum_{t=1}^T
\left\|1-\frac{e_t}{\widehat e_t}\right\|_{L_2(\mu_t)}
\|\widehat Q_t-Q_t^d\|_{L_2(\mu_t)}.
\tag{7}
$$

The assignment error is **relative** to the fitted assignment density. Bounded likelihood ratios alone do not convert it into an ordinary absolute density-error norm when densities can approach zero. In the fixed-generator finite-selection design, the explicit lower bound $\widehat b_t(j|h,c)\ge \varepsilon >0$ gives $|1-b_t/\widehat b_t|\le |b_t-\widehat b_t|/\varepsilon$; dominated weighted stage measures then give the familiar absolute-propensity-error product bound. Analogous absolute-density claims for unrestricted language require an appropriate lower-bound/domination condition and should not be assumed.

For fixed $T$, products in (7) that sum to $o_p(n^{-1/2})$, score convergence in $L_2$, and independent-root cross-fitting yield asymptotic linearity. Both the relative assignment error and the Q error converging at $o_p(n^{-1/4})$ in these weighted norms is one sufficient regime, not a necessary universal requirement. The mass and domination constants of these measures can grow exponentially with horizon; the bound does not remove the curse of overlap. With known randomized $e$, the bias remainder is exactly zero even for misspecified Q, although efficiency then depends on Q quality.

**Asymptotic expansion.** With a fixed finite number of folds, condition on a fold's training sample. Decompose its score average into the empirical mean of the true score, the centered empirical mean of $D(\widehat\eta)-D(\eta_0)$, and its conditional mean. Conditional independence and $L_2$ score convergence make the centered difference $o_p(n^{-1/2})$ by its conditional variance; (7) controls the mean. Sum the finite folds. The ordinary independent-root central limit theorem then applies to the true influence scores. This proof fails if branches from one root leak across training and evaluation folds.

**Known-assignment clarification (21 September 2026).** Correct continuation Q is
not necessary for valid asymptotic inference when all assignment probabilities
are known exactly. The [root-level proof note](known_assignment_inference_20260921.md)
shows that convergence in root-score L2 to a deterministic possibly misspecified
Q limit, finite positive limiting variance, independent roots and proper
cross-fitting suffice. The limiting score then uses that Q limit rather than the
efficient true-Q score; no n^(-1/4) Q rate is needed in this special case. Exact
mean validity alone does not imply the stability or finite-sample coverage conditions.
The note covers equal prespecified root aggregates, not outcome-selected policy
evaluation or estimated/clipped assignment weights.

### Theorem 5: efficient influence function in the stated model

Consider a nonparametric finite-horizon full-history model whose unknown factors are the initial-history law, logging action laws, and transition/reward laws. The target action law $d$ is fixed externally and does not vary with this observed-data model. Assume positivity, differentiability along regular submodels, and square-integrability of the expression. Then

$$
\phi_d(O)=V_1^d(H_1)-\mathcal V(d)+
\sum_{t=1}^T\Omega_t
\{R_t+V_{t+1}^d(H_{t+1})-Q_t^d(H_t,U_t)\}
\tag{8}
$$

is the canonical gradient, hence efficient influence function. It remains canonical if known logging randomization mechanisms are removed from this model.

**Proof.** A regular submodel score decomposes into $S_0(H_1)+\sum _t S_{e,t}(U_t|H_t)+\sum _t S_{P,t}(R_t,H_{t+1}|H_t,U_t)$, each component having conditional mean zero at its factor. Differentiating the g-formula, the initial-law derivative is $E[(V_1^d-\mathcal V)S_0]$. The target law does not contain $e$, so every logging-law derivative is zero. For a transition perturbation at stage $t$, its derivative is the target expectation of remaining return times $S_{P,t}$. Conditional expectation of the later return is $R_t+V_{t+1}^d$; earlier rewards are measurable before this transition and contribute zero. Change of measure and subtraction of the conditional mean yield $E[\Omega_t(R_t+V_{t+1}^d-Q_t^d)S_{P,t}]$.

Now pair (8) with the whole score. Conditional mean-zero and iterated expectation eliminate all cross-factor terms; only the displayed derivative for the matching factor remains. Also $E\phi_d=0$. Each summand is a permissible initial or transition tangent component multiplied by a function measurable before its transition. Thus (8) belongs to the tangent-space closure and represents every pathwise derivative, which makes it the canonical gradient. It is orthogonal to all logging-action tangent components; removing known-action score components leaves the same canonical gradient. ∎

**Model boundary.** Full history contains previous outcomes, so this result does not exploit time-homogeneous or low-dimensional Markov restrictions. In smaller models the efficient gradient can differ, and marginalized occupancy ratios may be more efficient. Claiming universal efficiency for (8) is incorrect.

### 6.3 Random slates: fixed design versus natural-generator target

When the generator is an externally fixed sampling protocol $G_0$, (4) integrates over this known protocol in each $\widehat V_t$; (8) has no generator-score term. Exact integration is a mathematical assumption of these formulas. Finite Monte Carlo slate integration creates additional numerical error; use sufficiently accurate independent draws or carry that error into inference. One should not silently substitute a single logged slate into every integrated value and retain the same efficiency claim.

If instead the estimand keeps the **unknown natural** generator $G_P$ from the observed population, then the target $d(P)=G_P\pi$ itself changes when $P$ changes. In the full-history model the canonical gradient additionally contains

$$
\sum_{t=1}^T\Omega_{t-1}
\{W_t^{\pi,G_P}(H_t,C_t)-V_t^{\pi,G_P}(H_t)\}.
\tag{9}
$$

**Derivation.** A generator perturbation at $t$ contributes its score $S_{G,t}(C_t|H_t)$ to the target g-formula. The remaining conditional target value after seeing $C_t$ is $W_t(H_t,C_t)$. Change the measure only through the previous selection, since the generator distribution is unchanged between logging and target at this turn; this yields $E[\Omega_{t-1}(W_t-V_t)S_{G,t}]$. The conditional mean subtraction makes it a generator tangent component. Adding it to (8) gives the derivative for every model factor. ∎

Equivalently, treat $(H_t,C_t)$ as the decision state; the usual nonparametric longitudinal score then includes candidate variability. That score can also be used with a known generator as an unbiased but generally less efficient estimator. These are different observation models and efficiency statements, not conflicting algorithms. A fixed finite slate in the simulator makes the extra term identically zero.

## 7. History-specific causal Q and blip learning

The scalar value score does not by itself give a root-specific label for every prompt. For same-generator randomized slates, define the downstream corrected remaining-return variable

$$
Z_{t+1}=\widehat V_{t+1}(H_{t+1})+
\sum_{s=t+1}^{T}\left(\prod_{k=t+1}^{s}
  \frac{\pi_k(J_k\mid H_k,C_k)}{\widehat b_k(J_k\mid H_k,C_k)}\right)
\{R_s+\widehat V_{s+1}(H_{s+1})-\widehat Q_s(H_s,C_s,J_s)\},
\tag{10}
$$

with $Z_{T+1}=Y$. Integration over the fixed generator is understood in $\widehat V$. For each candidate index $j$ in the realized slate **whose conditional action value is to be learned**, require both $b_t(j|h,c)>0$ and $\widehat b_t(j|h,c)>0$ at the relevant histories. This requirement also applies when $\pi _t(j|h,c)=0$: target-policy support alone does not identify every candidate-specific Q. Excluded or zero-logging-probability candidates receive no such label. For each index meeting these conditions, define

$$
\Gamma_{t,j}=\widehat Q_t(H_t,C_t,j)+
\frac{1\{J_t=j\}}{\widehat b_t(j\mid H_t,C_t)}
\{R_t+Z_{t+1}-\widehat Q_t(H_t,C_t,j)\}.
\tag{11}
$$

This is a vector of potentially noisy corrected labels over the supported indices of the finite realized slate. Only one residual is observed, so it is not a full-information counterfactual observation. Fit a critic by honest regression of these labels on $(H_t,C_t,j)$ or on exact prompt text under justified exclusion; use cross-fitting at root level.

### Theorem 6: exact conditional bias of the pseudo-outcome

For a queried index satisfying $b_j>0$ and $\widehat b_j>0$, put $z=(h,c)$, $b_j=b_t(j|z)$, $\widehat b_j=\widehat b_t(j|z)$, and

$$
B_{t+1}(z,j)=E\{Z_{t+1}-V_{t+1}^d(H_{t+1})\mid H_t=h,C_t=c,J_t=j\}.
$$

Then

$$
E(\Gamma_{t,j}\mid H_t=h,C_t=c)-Q_t^d(h,c,j)
=\left(1-\frac{b_j}{\widehat b_j}\right)
   \{\widehat Q_t(h,c,j)-Q_t^d(h,c,j)\}
 +\frac{b_j}{\widehat b_j}B_{t+1}(z,j).
\tag{12}
$$

**Proof.** Conditional on the slate and history, only $J_t=j$ contributes to the residual. Its expected multiplier is $b_j/\widehat b_j$. By the Bellman equation, $E[R_t+Z_{t+1}|z,J=j]=Q_t^d(z,j)+B_{t+1}(z,j)$. Substitute in (11) and collect terms. ∎

Consequently, local propensity correctness alone does not remove biased downstream labels. Conditional unbiasedness holds when the future recursion is conditionally unbiased at reachable next histories and the current propensity or current Q is correct. Theorem 4 applied starting from any such history supplies sufficient downstream conditions. Contrasts $\Gamma_{t,j}-\Gamma_{t,j'}$ estimate the conditional blip after regression under the same conditions.

Weighted squared loss, contrast losses, or ranking losses can train a neural critic, but they solve different statistical problems. Squared regression targets Q calibration; direct contrast loss can target heterogeneity; ranking loss targets decisions and need not calibrate Q. Bootstrap ensemble spread alone is not a proved pointwise confidence interval for the conditional causal effect. Smoothness, complexity, overlap, and distributional calibration assumptions are needed for honest conditional inference. With continuously varying histories or text, a point-evaluation Q is generally not a regular root-$n$ functional in the unrestricted model; the root-$n$ result for marginal policy value does not transfer to every neural prediction.

## 8. Optimality, policy improvement, and conservative selection

### 8.1 Supported optimal policy

For a fixed generator $G$, let $V_t^{*,G}$ solve

$$
Q_t^{*,G}(h,c,j)=E\{R_t+V_{t+1}^{*,G}(H_{t+1})\mid h,c,j\},
\quad V_t^{*,G}(h)=E_{C\sim G(\cdot|h)}\max_{j\in\mathcal J(h,C)}Q_t^{*,G}(h,C,j).
\tag{13}
$$

$\mathcal J$ contains eligible, supported candidates including STOP. With finite nonempty slates and measurable tie breaking, backward induction gives an optimal deterministic selector within this generator-constrained policy class. The maximization occurs after seeing the slate, so $E max_j Q$ is appropriate; $max_j E Q$ is generally not.

**Proof.** At the last decision, conditional expected utility is maximized by the largest supported Q. Assuming optimal continuation values are available at $t+1$, the same pointwise maximization at $t$ dominates every other first-stage selection followed by any admissible continuation. Integrating over the generator and inducting backward proves global optimality within the class. ∎

### Theorem 7: performance difference and certified local improvement

Let $\beta$ and $\pi$ be selectors sharing the same generator and environment. Then

$$
\mathcal V(\pi)-\mathcal V(\beta)=
\sum_{t=1}^T E_{\pi,G}\!\left[
\sum_j\{\pi_t(j\mid H_t,C_t)-\beta_t(j\mid H_t,C_t)\}
 Q_t^\beta(H_t,C_t,j)\right].
\tag{14}
$$

If a simultaneous event guarantees $|\widehat Q_t^\beta (h,c,j)-Q_t^\beta (h,c,j)|\le u_t(h,c,j)$ on all target-reachable histories/candidates, define

$$
L_t(h,c;\pi,\beta)=
\sum_j(\pi_j-\beta_j)\widehat Q_t^\beta(h,c,j)
-\sum_j|\pi_j-\beta_j|u_t(h,c,j).
\tag{15}
$$

On that event, $\mathcal V(\pi )-\mathcal V(\beta )\ge \sum _tE_{\pi ,G}L_t$. In particular, restricting policy changes to those with $L_t\ge 0$ pointwise guarantees nondecrease on the same event.

**Proof.** Under target trajectories sum the baseline Bellman residuals $R_t+V_{t+1}^\beta (H_{t+1})-V_t^\beta (H_t)$. The state values telescope to $U^{tot}-V_1^\beta (H_1)$. Conditional averaging gives $E_G\sum _j\pi _jQ_t^\beta -V_t^\beta =E_G\sum _j(\pi _j-\beta _j)Q_t^\beta$, proving (14). Substituting $Q=\widehat Q+(Q-\widehat Q)$ and bounding each error term below by $-|\pi _j-\beta _j|u_j$ proves (15) and its consequences. ∎

The required simultaneous event is a substantial statistical condition. Ordinary per-candidate pointwise intervals, post hoc best-of-many selection, or uncalibrated neural uncertainty do not establish it. An average advantage on logging histories alone also does not prove improvement under a changed trajectory distribution. A safer practical release gate is an independent root-level evaluation of the frozen proposed policy against baseline, with uncertainty for the policy-value difference.

STOP is handled by the same theorem. A deterministic continue candidate is preferred to STOP only if its supported downstream utility exceeds the stopping value after all future costs. The guarantee applies to the measured utility, not to an unmeasured preference or an oracle label leaked into policy input.

### 8.2 Finite-policy holdout guarantee

Suppose a training sample fixes $m$ proposed policies and their nuisance functions. An independent evaluation set contains $n$ independent roots, and a score for each policy lies in $[a,b]$ almost surely. If assignment probabilities are correct, its score mean is unbiased. Then, with probability at least $1-\alpha$, simultaneously for every policy,

$$
|\widehat{\mathcal V}(d)-\mathcal V(d)|
\le (b-a)\sqrt{\frac{\log(2m/\alpha)}{2n}}.
\tag{16}
$$

**Proof.** Apply Hoeffding's inequality to each policy's independent bounded root scores and union bound over $m$. If only a known bias bound $r_d$ from (5) is available, add it to that policy's radius. ∎

A policy can be released when its lower value bound exceeds the baseline upper bound, or more efficiently when a paired score-difference lower bound exceeds zero. This is a finite-class holdout result; repeatedly inspecting the same holdout and generating additional policies violates its fixed-class premise. Fresh holdouts, a predeclared simultaneous class, or sequentially valid inference are needed for ongoing adaptation.

### 8.3 Candidate coverage versus critic error

To compare with unrestricted prompts, additionally assume slate exclusion, candidate-independent action reward/transition, a common cost convention, and an admissible prompt space $\mathcal A(h)$ with a measurable maximum or arbitrarily close maximizers. Let $Q_t^*,V_t^*$ denote unrestricted optimal continuation values. Every slate maximum, greedy selection, and error bound in this subsection is over the **same eligible, positive-logging-support index set** $\mathcal J(h,c)$ used in (13), which is nonempty and contains STOP. Every compared selector assigns zero probability outside this set. Merely appearing in the slate does not make an excluded or unsupported candidate selectable. Define the candidate coverage loss

$$
c_t(h)=V_t^*(h)-E_{C\sim G}\max_{j\in\mathcal J(h,C)}Q_t^*(h,C_j)\ge0.
\tag{17}
$$

This is a theoretical quantity; the global optimal prompt over all language is usually unknown. It must not be estimated by labeling the best sampled candidate globally optimal.

### Theorem 8: coverage decomposition and finite-horizon bounds

For any candidate selector $\widehat\pi$ sharing $G$,

$$
\mathcal V^*-\mathcal V(\widehat\pi,G)=
\sum_tE_{\widehat\pi,G}c_t(H_t)+
\sum_tE_{\widehat\pi,G}\!\left[
\max_{j\in\mathcal J(H_t,C_t)}Q_t^*(H_t,C_{tj})-
\sum_{j\in\mathcal J(H_t,C_t)}\widehat\pi_t(j\mid H_t,C_t)Q_t^*(H_t,C_{tj})\right].
\tag{18}
$$

If the critic estimates the **restricted optimal** $Q_t^{*,G}$ with uniform error at most $\varepsilon _t$ over every relevant history, slate, and index in $\mathcal J(h,c)$, and $\widehat\pi$ greedily selects its largest prediction **within that same set**, then

$$
\mathcal V^*-\mathcal V(\widehat\pi,G)
\le \sum_t\sup_h c_t(h)+2\sum_t ε_t.
\tag{19}
$$

**Proof.** Telescope unrestricted optimal state values along trajectories of $\widehat\pi$: $\mathcal V^*-\mathcal V(\widehat\pi)=\sum _tE[V_t^*(H_t)-Q_t^*(H_t,A_t)]$. Add and subtract the best eligible supported slate value; conditioning on pre-slate history yields (18). Every maximum is over $\mathcal J$, so an unselectable high-value candidate cannot eliminate the coverage loss.

For (19), first compare $V_t^*$ with $V_t^{*,G}$. Their Bellman equations and $\max x-\max y\le \max(x-y)$ imply

$$
\sup_h(V_t^*-V_t^{*,G})
\le\sup_h c_t(h)+\sup_h(V_{t+1}^*-V_{t+1}^{*,G}).
$$

The terminal difference is zero, hence the unrestricted-versus-restricted gap is at most the sum of coverage suprema. Next, for any slate, let $j*$ maximize the true restricted optimal Q over $\mathcal J(h,c)$ and $\widehat j$ maximize its estimate over that same set. Then

$$
Q^{*,G}(j*)-Q^{*,G}(\widehat j)
\le |Q^{*,G}(j*)-\widehat Q(j*)|
 +|\widehat Q(\widehat j)-Q^{*,G}(\widehat j)|\le2ε_t,
$$

because $\widehat Q(j*)\le \widehat Q(\widehat j)$. Telescope $V^{*,G}$ along the greedy estimated policy; each conditional stage gap is at most $2\varepsilon _t$. Add the two bounds. ∎

Do not apply (19) to a critic of an arbitrary baseline continuation. Such a critic supports Theorem 7's improvement analysis, not a global near-optimality claim.

**Coverage corollary.** Suppose a protocol starts with $K$ independent proposals conditional on history. Each proposal has probability at least $p_t(h)$ of simultaneously (i) having $Q_t^*(h,A)\ge V_t^*(h)-\eta _t$ and (ii) meeting a proposal-wise admissibility criterion that guarantees at least one corresponding index remains eligible and selectable with positive logging probability after the complete protocol. Assume $0\le \eta _t\le B_t$, where $B_t$ bounds the Q range. Then

$$
c_t(h)\le η_t+B_t\{1-p_t(h)\}^{K}.
\tag{20}
$$

**Proof.** The qualifying near-optimal-proposal events are independent because they are functions of independent original draws and the fixed history. The probability of none is at most $(1-p)^K$. If at least one occurs, the preservation condition puts an $\eta _t$-optimal index in the final selectable set $\mathcal J$, so the gap is at most $\eta _t$; otherwise it is at most $B_t$. If $r$ is the actual failure probability, the expected gap is at most $\eta _t+(B_t-\eta _t)r$. Since $0\le \eta _t\le B_t$ and $r\le (1-p)^K$, this is at most $\eta _t[1-(1-p)^K]+B_t(1-p)^K$, which implies (20). ∎

Here $K$ counts the **original independent draws**, not a random post-filter count or the final number of unique candidates. Deduplication that preserves one selectable copy of every qualifying proposal preserves the maximum event and does not invalidate the bound. Correlated beams, globally dependent eligibility filtering, or removing qualifying candidates can invalidate the independent-event or preservation premises; derive their coverage separately. An unsupported candidate has no qualifying probability for this corollary regardless of its oracle quality. More proposals can raise generation cost, so (20) for quality alone does not establish improved net utility as $K$ grows.

## 9. Training a generative policy and a dynamic skill

An implementable cycle is: freeze generator and receiver; generate and randomize supported slates; fit Q/blip models; learn a selector on training roots; evaluate the frozen selector on new roots; only then use high-value evidence to update the generator and repeat collection. The learned controller is a dynamic skill only in the operational sense of an adaptive policy with a declared model/environment scope.

For a differentiable stochastic generator-selector law $d_\theta$, with parameter-independent transition law and dominated differentiation, the policy-gradient identity is

$$
\nabla_θ\mathcal V(d_θ)=
E_{d_θ}\sum_{t=1}^T
\nabla_θ\log d_{θt}(U_t\mid H_t)Q_t^{d_θ}(H_t,U_t).
\tag{21}
$$

**Derivation.** Differentiate the trajectory density product to obtain a sum of action log-density derivatives multiplied by total return. For a stage's score, rewards accumulated before that action have zero covariance with it because the conditional score mean is zero. Conditional expectation of subsequent return given history and action is $Q_t^{d_\theta }$. Substitute to get (21). Any history-only baseline can be subtracted by the same zero-mean argument. ∎

The identity uses on-policy history occupancy and the current policy's true Q. Maximizing $E_{H\sim \text{old logs},A\sim G_\theta } \widehat Q(H,A)$ is generally a surrogate; it omits changing history occupancy and can exploit critic error. Off-policy gradients require valid full likelihood ratios/occupancy correction and appropriate nuisance control. Distilling selected prompts, reward-weighted fine-tuning, direct preference objectives, and KL regularization are proposed optimization methods, not proved substitutes for (21) or randomized final evaluation.

A learned transition/world model can support planning only under identified transitions and sufficient state representation. Rollouts generated by that model are model predictions, not fresh counterfactual validation data. Longer simulated planning compounds transition error and can reward unrealistic states. Keep synthetic-world evaluation separate from actual frozen-receiver executions.

## 10. Honest inference, branch experiments, and transport

### 10.1 Shared prefixes and independent roots

A forked experiment restores the same declared receiver/tool snapshot and executes candidate continuations. Repeated rollouts estimate the conditional mean at that snapshot over receiver and continuation randomness. They do not reveal a unique user's latent joint counterfactual outcomes. If shared random seeds are used, the coupling can reduce variance but is an experimental design choice; it is not the naturally occurring cross-world coupling.

All continuations sharing root task, common prefix, user, template, or stochastic cached output must stay in the same independence cluster when those shared variables create dependence relevant to the target. Fit nuisance models and select policies on other clusters. Reporting the total number of branches as $n$ overstates independent information.

For $m$ independent roots with a prespecified within-root averaging rule, let $S_i$ be the root's averaged evaluation score, including any valid branch-selection correction. The root-average estimand is estimated by $\widehat V=m^{-1}\sum _iS_i$, with

$$
\widehat{\mathrm{Var}}(\widehat V)=
\frac{1}{m(m-1)}\sum_{i=1}^m(S_i-\overline S)^2.
\tag{22}
$$

**Justification.** Independence applies to root scores, not branch scores. The sample variance of independent root scores is unbiased for their variance when roots are identically sampled; dividing it by $m$ gives (22). A root-level central limit theorem or root bootstrap supports large-sample inference. Unequal/informative root sampling, adaptive branch allocation, or branch pruning needs explicit design weights; a convenience mean across all branches targets a branch-size-weighted distribution.

Branches must preserve the full system state. Restoring only visible text while tool files, caches, hidden conversation memory, or server model versions change violates the branch experiment's consistency assumption. A behavioral simulator supplies exact counterfactuals only within its own specified simulator law.

### 10.2 Learned policies and nonregular optima

A conditional interval for a policy frozen after training is different from an interval for the population-optimal value. If different folds train different policies, the straightforward cross-fitted estimator targets an average of fold-trained policy values; it does not automatically evaluate the final all-data-trained policy. Evaluate that final policy on fresh roots. At ties or near ties, the maximum-value functional can be nonregular. Ordinary plug-in Wald intervals for an estimated argmax require extra conditions; the fixed-policy results above do not supply them.

Calibration reports should separately assess policy-value error, supported candidate ranking, blip sign, conditional mean calibration across predeclared history groups, uncertainty coverage, and realized deployment utility. A single global value interval does not establish individualized calibration.

### 10.3 New users and environment transport

A new user from the same target population is covered only to the extent that the relevant history is supported. For a different baseline-history distribution $q(H_1)$ with unchanged conditional mechanisms, known or estimable baseline density ratio $w=q/p$ can transport the value by weighting the initial distribution and scores. New receiver versions or different latent user preferences change conditional mechanisms and require stronger assumptions or new experiments. Logging version metadata enables auditing; it does not by itself prove invariance.

### 10.4 Historical logs versus prospective trials

Historical logs are useful for initialization, candidate proposal, and hypothesis development. Their causal use depends on measured confounders, treatment versions, stopping/missingness definitions, and support. A deliberately confounded simulation can demonstrate failure of a marginal reward model, but it should also include correctly adjusted sequential regression as a comparator. Prospective within-slate randomization removes selection confounding at that decision by design, provided the receiver continuation and outcome recording obey the protocol.

## 11. Research claims that remain conditional or open

1. **New free-form prompt performance:** not identified by the finite-slate randomization alone. Needs covered generation, structural generalization, or fresh trials.
2. **Uniform neural confidence bands:** assumed in Theorem 7, not constructed or validated here. Independent policy-level holdouts are the immediate defensible alternative.
3. **Universal representation sufficiency:** not established. Evaluate history/text compression through controlled ablations and conditional calibration; failure to detect bias does not prove sufficiency.
4. **Generator improvement after distillation:** requires new frozen-generator evaluation or valid full-generator ratios. Winner distillation can amplify noise and erase exploration.
5. **Prompt-level causal attribution to latent semantic factors:** requires explicitly defined semantic interventions and treatment-version assumptions. A latent vector coordinate is not automatically a manipulable treatment.
6. **Unmeasured confounding in human logs:** randomized selection evidence does not retroactively identify unsupported historical interventions. Sensitivity analysis can quantify assumptions but is not a proof they hold.
7. **Human personalization and preferences:** one frozen automatic evaluator estimates that evaluator's outcome; it does not establish a user's satisfaction, trust, or welfare.
8. **Joint receiver/generator adaptation:** outside the frozen-environment theorems unless adaptation state and intervention protocol are modeled. Changing both players is a different target.
9. **Multivariate win outcomes:** can be studied with a specified pairwise functional and coupled/independent policy draws, but do not inherit the scalar Bellman recursion without a defined scalar utility or augmented-state target.
10. **Novelty and practical superiority:** no theorem here establishes that the combined method is new or outperforms current prompt optimizers. Those are literature and empirical questions.

## 12. Source grounding

The proofs in this document are supplied explicitly for this project's notation and assumptions; the underlying longitudinal DR and efficiency principles are established. Primary sources used to check those boundaries:

* Jiang, N. and Li, L. (2016). [Doubly Robust Off-policy Value Evaluation for Reinforcement Learning](https://proceedings.mlr.press/v48/jiang16.html). Sequential DR evaluation and its policy-evaluation context.
* Bang, H. and Robins, J. M. (2005). [Doubly Robust Estimation in Missing Data and Causal Inference Models](https://doi.org/10.1111/j.1541-0420.2005.00377.x). Longitudinal and missing-data DR foundations; [author-hosted full text](https://www.math.mcgill.ca/dstephens/PSMMA/Articles/bang_robins_2005.pdf).
* Kallus, N. and Uehara, M. (2020). [Double Reinforcement Learning in Markov Decision Processes](https://jmlr.org/papers/volume21/19-827/19-827.pdf). Distinguishes efficiency models, non-Markov history ratios, and Markov structure. This project does not claim every history-weighted estimator is efficient under Markov restrictions.
* Luedtke, A. R. and van der Laan, M. J. (2016). [Statistical inference for the mean outcome under a possibly non-unique optimal treatment strategy](https://pmc.ncbi.nlm.nih.gov/articles/PMC6338452/). Nonregularity and inference for optimal versus learned policies.
* van der Laan, M. J. and Luedtke, A. R. (2015). [Targeted Learning of the Mean Outcome under an Optimal Dynamic Treatment Rule](https://pmc.ncbi.nlm.nih.gov/articles/PMC4517487/). Dynamic-rule learning and data-adaptive targets.

Longitudinal human–LM causal analysis, language-valued DTR learning, and contextual off-policy prompt optimization have close predecessors. This project studies supported next-prompt selection for a fixed receiver and continuation, using established identification and estimation principles. Novelty of the specific design and practical policy improvement remain unestablished. The [literature recheck](literature_recheck_20260920.md) supersedes contrary claims in the historical audit; the [subsequent methods and code review](literature_guided_design_20260921.md) informs the prospective experiment. The attachment's recent paper titles, venue claims and assertions of an unoccupied research area are leads, not assumptions or verified novelty evidence.


## Operational landmark design: next-prompt personalization

The [landmark theory supplement](landmark_prompt_theory.md) specializes this general framework to the next bounded experiment. It proves the distinction between zero average arm contrast and positive personalization headroom, separates public-information/checkpoint/sample-max oracles, gives a conditional-mean error bound for greedy policy regret, and derives paired-root variance with repeated branches. Its transport discussion limits a one-decision result to the declared prefix and continuation law. These are scoped applications of established ideas, not claims of new foundational DTR theory. Exact checks and the separately frozen known-truth premise simulation accompany the supplement; neither establishes natural-language prompt efficacy.
