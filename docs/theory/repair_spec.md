# BINDING REPAIR SPECIFICATION — theory document, cross-cutting decisions

**Status: binding.** Eighteen section agents apply this. Where this spec and the existing section text conflict, this spec wins. Where this spec and `docs/audits.md`, `docs/measured_calibration.md`, `docs/design_e3_critic_policy.md`, `docs/positioning.md` or `docs/premise_findings.md` conflict, **those documents win and you must report the conflict rather than resolve it yourself**. Do not add a claim that is not either (i) already in the document, (ii) written verbatim here, or (iii) a measured number from those docs.

**Withdrawal convention (mandatory).** A retired result keeps its number and its position, and is rewritten as:

> **T20 (improvement certificate) — WITHDRAWN as a deliverable; retained as a scope statement.** *[what was claimed] [why it fails, in the reviewer's terms] [what replaces it].*

Never delete a broken claim silently, never renumber, never reuse a retired number.

---

## PART 0 — GLOBAL CONSTANTS (single source of truth)

Measured (M) or frozen design choice (F). **No agent may write a quantity that contradicts this table, or introduce a number not derivable from it.**

| symbol | value | source |
|---|---|---|
| action set $\mathcal K$ | $\{A_0,\dots,A_8\}$, $m=9$; $A_0=$ `STOP`, absorbing | F |
| randomized set $\mathcal K_G$ | $\{A_1,\dots,A_8\}$, $m_G=8$ | F |
| design propensity | $e_t(k\mid H_t)=1/8=0.125$ for all $k\in\mathcal K_G$, at every branched state | F, measured positivity 1.0 |
| **floor** | $\boxed{\delta=1/8=0.125}$, attained with equality ($m_G\delta=1.000$) | derived |
| policy-admissible $\mathcal A_{\rm adm}$ | $\{A_0,A_1,A_2,A_3,A_4,A_5\}$ | F |
| diagnostic-only | $\{A_6$ DIVERT, $A_7$ MISDIAGNOSE, $A_8$ PATCH$\}$ — barred from every $\pi$ and every reported baseline | F |
| turns / decision points | $T_{\max}=3$; $k\in\{1,2\}$; **$D=2$**; full override depth $d=D=2$ | F |
| $\delta^{-d}$ | $d=0\Rightarrow M=1$; $d=1\Rightarrow M=8$; $d=2\Rightarrow M=64$ | derived |
| **i.i.d. unit** | the **task instance (task text only)**; seeds, branches, turns, templates, paraphrases are *within*-cluster | audits A2 |
| $n_{\rm clusters}$ | **176 task families** (from 190 tasks); pool ceiling **≈230** (3B), **≈100** (7B) | M |
| paired units | 1,520 = 190 × 8 root seeds sharing one saved root $O_1$ — **within-cluster** | F |
| $n_{\rm eff}\ge n_{\rm clusters}\delta^{d}$ | at 176: **176 / 22 / 2.75**; at 230: **230 / 28.75 / 3.59** | derived |
| available gap | **+0.046** (oracle stopping — the only measured headroom); vs B4 **+0.015 to +0.030**; vs B2 **+0.07 to +0.12** | M |
| measured precision | paired family-clustered bootstrap half-width **±0.019** at $R=8$; **MDE 0.027** at 80% power | M |
| $\lambda$ | **0.01 per turn**, pre-registered; grid $\{0,0.005,0.01,0.02\}$ with a union bound if more than one is reported | F |
| repair / degradation | **0.239** [0.210,0.270] / **0.162** [0.105,0.242] | M |
| self-check stopping | stopped on **0.504** [0.479,0.528] of all failures | M |
| null-blip mass (3B) | **0.156** below 0.05 success, **0.334** above 0.95, **0.406** informative | M |
| receiver cost | **3.2 s**/call (3B), **6.4 s** (7B), 4 slots contended; **≈2,150 calls/hour** | M |
| **affordability ceiling** | **20,000 receiver calls ≈ 9.3 h**. A prescription over it must be cut or marked unaffordable | M |
| branch replicates | frozen **$n_b=3$**; per-state MC SE up to **0.29**; $\hat v\approx0.08$ | M |
| $\lvert\Pi\rvert$ | the **pre-registered candidate count declared in §16**. `100` is forbidden. Arithmetic printed at $\lvert\Pi\rvert=8$ ($L=6.461$) and $100$ ($L=8.987$), $L=\log(4\lvert\Pi\rvert/\alpha)$, $\alpha=0.05$ | derived |

---

## PART I — THE EIGHT MANDATED DECISIONS

### R1. The positivity floor — $\delta=1/8$, `STOP` exempt, feasibility stated

**Defect.** A uniform floor over $m$ arms requires $m\delta\le1$, so $\delta\le1/m$: $\delta\ge0.25$ is feasible only for $m\le4$, against the mandated 5–6 classes plus `STOP` and the frozen 9-action taxonomy. Every headline number is computed at an unattainable floor.

**Decision, two parts, matching the frozen design.**

(i) **`STOP` ($A_0$) is exempt from A6.** $Y(A_0\text{ at }k)=V_k$ is $H_k^A$-measurable (verifier determinism measured: 1,954 replicate verifications of 597 repeated `(task_uid, sha256(final_code))` pairs, 0 disagreements), so it needs **no randomization, no nuisance model, zero GPU**; positivity holds **by degeneracy**. The harness runs every trajectory to $T_{\max}$ and grades $\psi$ at every turn, so every "stop at $k$" value is *observed*, not weighted.

(ii) The floor applies to the $m_G=8$ randomized non-`STOP` arms, **uniform**: $\delta=1/8=0.125$, attained with equality; $c=1$ in $\delta=c/m_G$.

**A6 replacement (§2 table).**

> | A6 | Randomization floor on the **randomized** coordinate: $e_t(k\mid H_t)=\delta$ for all $k\in\mathcal K_G$, with the feasibility constraint $m_G\delta\le1$ stated as part of the assumption. `STOP` is exempt: its potential outcome is $H_t^A$-measurable, so positivity for `STOP` holds by degeneracy. Frozen: $m_G=8$, $\delta=1/8=0.125$, $m_G\delta=1.000$. | BC ($\delta=1/8$; $\delta\ge0.25$ is **infeasible** for $m_G>4$ and is withdrawn) |

**§4 P5 "Bounded case" replacement.**

> $\delta=1/8$, $d=1\Rightarrow E[W^2]\le8$; $d=2\Rightarrow E[W^2]\le64$. Since the frozen design has $D=2$ decision points, $d=2$ **is** full depth, so 64 is the worst case over $\Pi_{\rm cp}$, not a knob setting. In cluster units $n_{\rm eff}\ge n_{\rm clusters}\delta^{d}$: **176, 22 and 2.75 clusters** at $d=0,1,2$. A depth-2 off-policy evaluation on this pool has an effective sample size of **under three clusters**, which is why on-policy paired rollout is primary (R9, E0).

**§16 item 3 replacement.**

> 3. Cap the taxonomy: the frozen action set is $m=9$ ($A_0$ `STOP` plus 8 generator classes), randomized uniformly over the 8 non-`STOP` classes at $e=1/8$, so the feasible floor is $\delta=1/8=0.125$ and $m_G\delta\le1$ binds with equality. A floor of 0.25 would cap the action set at four arms including `STOP` and is not compatible with this taxonomy. Policy-admissible arms are $\{A_0,\dots,A_5\}$; $A_6,A_7,A_8$ are diagnostic and barred from every reported policy and baseline. Override depth is **not a free knob** (R2): declare each reported regime's entitlement class. One primary randomized axis.

**Recomputed dependents — all of them.**
- $E[W^2]\le\delta^{-d}$: 8 at $d=1$, 64 at $d=2$. (Was 16.)
- $n_{\rm eff}$: 176 / 22 / 2.75 at $n=176$; 230 / 28.75 / 3.59 at $n=230$.
- Certificate sample sizes: R4. The figures $5\times10^4$ and $1.2\times10^4$ are withdrawn.
- §4 tilt budget, recomputed at $n_{\rm clusters}=176$, $n_{\rm eff}^{\min}=30$, $D=2$: $\sum_t\Delta_t^2\le\log(176/30)=1.769$, so $\Delta_t\le0.941$ within-history SD and $\mathrm{KL}_t\le0.442$ nats per turn (replaces "$n=10^4$, $T=5$, 0.96 SD / 0.46 nats").
- §4 P6: at $\bar\kappa=0.05$, $\bar m=400$, $n_{\rm eff}\le n e^{-20}=2.06\times10^{-9}n$, i.e. $\le3.6\times10^{-7}$ clusters. Conclusion unchanged.
- The simulated-log arm's "floor 0.2" is **not** a randomization floor ($8\times0.2=1.6>1$). It is a **weight-truncation level** ($\hat e$ clipped below at 0.2, so $w\le5$), it introduces clipping bias, A6 does **not** hold in that arm (the logging policy is confounded by construction), and the truncation rate must be reported. State this wherever the simulated-log arm appears.

**Sections.** §2 (A6, A4), §4 (P5, P6, tilt budget), §6 (T20a–d), §10 (ladder A6 and D1 rows), §13(b) item 1, §16 item 3, §12.

---

### R2. Override depth — a defined entitlement split, not a knob

**Defect.** $d$ is the number of turns at which $\pi$ differs from $e$; the optimal regime deviates at every decision point, so $d=D$ for it and the bound is $\delta^{-D}$. Every sample size is quoted at the small-$d$ figure while the advertised deliverable needs the large-$d$ one.

**Decision.** Override depth counts **only decision points at which the regime overrides the generator-class distribution**. The stopping coordinate contributes **no weight** in D1, because the harness runs to $T_{\max}$ and records $\psi(H_k)$ at every $k$, so a stopping regime's value is an *unweighted* mean. Three declared classes; every claim must name which one it is about.

| class | definition | bound | $n_{\rm eff}$ at 176 | how its value is obtained |
|---|---|---|---|---|
| $\Pi_0$ | stopping-only: $\pi_k$ on $\mathcal K_G$ equals $e_k$; only `STOP`/`CONT` is chosen | $W\equiv1$, $M=1$ | 176 | **unweighted means** on recorded trajectories; no importance weighting anywhere |
| $\Pi_1$ | depth-1 class override | $W\le8$, $M=8$ | 22 | off-policy estimable; report ESS and $\hat D_2$ with every number |
| $\Pi_2=\Pi_{\rm cp}$ | full depth ($d=D=2$), including $\hat\pi$ from backward induction | $W\le64$, $M=64$ | **2.75** | **on-policy rollout (E7) or re-logged policy iteration only**; off-policy certification explicitly disclaimed |

**§10 ladder D1 row replacement** (the `$W\le\delta^{-d}$` cell):

> $W\equiv1$ for stopping-only regimes $\Pi_0$; $W\le\delta^{-1}=8$ for depth-1 class overrides $\Pi_1$; $W\le\delta^{-D}=64$ for full-depth regimes $\Pi_2=\Pi_{\rm cp}$, whose effective sample size on this pool is **2.75 clusters** and whose values must therefore be obtained by on-policy rollout, not off-policy weighting.

**T19 replacement** for "the history-shift factor is bounded here **by design**":

> the history-shift factor is bounded by $\delta^{-d}$ with $d$ the override depth of the regime whose history law is used. For $\hat\pi$ and every full-depth member of $\Pi_{\rm cp}$, $d=D=2$ and the bound is 64; "bounded by design" is an advantage over *unbounded* ratios, not a small constant. At $n_{\rm clusters}=176$ a factor of 64 leaves 2.75 effective clusters, so the propagation bound is a structural statement, not a basis for inference.

**Where the flagship claim lives — every section that advertises the off-policy machinery must say this.** The measured headroom is entirely in stopping (+4.6 pp), and stopping-only regimes sit in $\Pi_0$ with $W\equiv1$: **the deliverable the evidence supports needs no importance weights at all.** The exponential-in-$T$ blow-up is bounded at $8^2=64$ *only* because the frozen design has two decision points; `T = 5` must not appear anywhere.

**Sections.** §0.2 items 3 and 6, §0.3, §4 (P5, T7), §6 (T19, T20), §10 (D1 row), §16 item 3, §12, verdict.

---

### R3. The two histories — $H_t^A$ and $H_t^O$ — and the split of T8

**Defect.** "$Q_t(H_t,\texttt{STOP})$ is known" equivocates between the harness, which grades the artifact against hidden tests, and the **policy**, which must not see that grade. Read the first way, T8 contradicts A11(d) and §16 item 6 and manufactures P24(ii) optimism; read the second way, the advertised asymmetry evaporates.

**§1 insertion, immediately after `Trajectory`.**

> **Two histories.** $H_t^A$, the **analyst/harness history**, is everything recorded, including the programmatic grade $\psi(H_s)$ of every artifact in hand for $s\le t$. $H_t^O=\varphi_t(H_t)$, the **policy-observable history**, is the pre-registered frozen decision-time signal: task text, emitted messages, receiver outputs, the *visible* assertion verdict, and the cost channel. $\varphi_t$ **excludes $\psi$ and everything derived from the hidden tests**, and `signature_example` is stripped from every record it can reach. $\mathcal F_t^O:=\sigma(\varphi_t(H_t))\subsetneq\sigma(H_t^A)$. Every regime in $\Pi_{\rm cp}$ is $\mathcal F_t^O$-measurable (R8); every nuisance the analyst fits may use $H_t^A$. A quantity that is $H_t^A$-measurable but not $\mathcal F_t^O$-measurable is available to the *estimator* and unavailable to the *policy*, and this document states which of the two it means every time it says "known".

**T8 replacement (§4), first paragraph.**

> ### T8 (backward induction; the `STOP` arm in two information sets)
>
> **T8a (analyst version).** Under A4, A15, A21 and a programmatic $\psi$ graded at every turn, $Q_t(H_t^A,\texttt{STOP})=\psi(H_t)$ **exactly**: the `STOP` arm carries no causal nuisance, has zero Monte Carlo variance, needs no nuisance model, consumes zero GPU, and requires no positivity (R1). This is the correct reading of the degeneracy $Y(A_0\text{ at }k)=V_k$, and it is what makes the stop coordinate weight-free (R2).
>
> **T8b (policy version).** For $\pi\in\Pi_{\rm cp}$ the implementable stop value is $E[\psi(H_t)\mid\varphi_t(H_t)]$ — an **unknown regression**, the deployable policy's whole handle on "am I already right", a supervised calibration problem with no causal content but with first-order estimation error. It is not a known functional of anything the policy sees. The measured difficulty is on record: the visible verdict is one bit and is absent on 20.8% of the informative pool, and the sibling loop's own self-check stopped on **50.4%** [0.479, 0.528] of all failures. The **+4.6 pp** of headroom is the value of the **oracle** $V$, which is not available to any real rule.
>
> Restated asymmetry: *the `STOP` arm's causal nuisance is nil and its prediction problem is the hardest estimation problem in the design.* "The endogenous horizon costs nothing extra" is **withdrawn** — it costs the calibration of $E[\psi\mid\varphi]$ — and "no medical analogue" is deleted, since the medical analogue of T8b is ordinary prognostic modelling.
>
> **Mandatory reporting.** Report the oracle-$V$ minus $\hat p$-rule value gap as a headline pair, never the oracle value alone.

**Resolution of T8 vs A11(d).** A11(d) becomes an **information-set restriction, not a two-instrument requirement**:

> | A11 | Outcome validity: (a) programmatic $\psi$; (b) judge + PPI *only* for secondary outcomes; (c) horizon-invariant scorer — see R19; (d) **the stopping signal is $\varphi$-measurable and $\varphi$ excludes $\psi$ and every hidden-test-derived quantity, enforced by feature-builder assertion.** | **A** for (a)–(c); (d) **BC** by construction of $\varphi$ |

With a programmatic primary outcome, $\sigma=0$ for the primary number, P24(ii) does not bite on it, and §16 item 6's "two prespecified independent measurement channels" is **replaced** by the $\varphi$-exclusion assertion. If a judge is ever used for a secondary outcome, T8b applies with R20's inflation term.

**Strings to delete.** "the stopping decision is a scalar blip with a **known** stop-arm value"; "the endogenous horizon costs nothing extra"; "no medical analogue"; unqualified "the only causal nuisance is the continuation value". Keep the prediction reading; stop calling it costless.

**Sections.** §1, §2 (A11), §4 (T8, nuisance-asymmetry paragraph), §0.2 item 5, §0.3, §7 (P23's "decision-time observables" → $\mathcal F_t^O$), §8 (P24), §10 (D1 row), §12 item 7, §16 items 5 and 6, verdict.

---

### R4. The improvement certificate — withdrawn as a deliverable

**Defect (four, all real).** (i) The arithmetic drops a factor of ≈8: the Bernstein term is $\sqrt{2\hat\sigma^2L/n}$, T20(c)'s union with the baseline UCB gives each side at most gap/2, and $L$ must be $\log(4|\Pi|/\alpha)$. (ii) The unit is "conversations", contradicting §1 and §5's fold rule, manufacturing unlimited units from a ~230-element pool whose task text is the dominant variance component. (iii) $V(e)$ averages over $A_6$, $A_7$ and $A_8$, so the certified gap is **monotone in the number of deliberately degraded arms** and manufacturable with zero learning. (iv) No simple untuned protocol is required as a comparator.

**Corrected formula — the only form that may appear.**

$$n_{\rm clusters}\ \ge\ \frac{8\,M\,\log(4|\Pi|/\alpha)}{\mathrm{gap}^2},\qquad M=\delta^{-d},\quad\alpha=0.05 .$$

At $|\Pi|=8$, $L=\log(640)=6.461$ (at $|\Pi|=100$, $L=\log(8000)=8.987$; multiply by 1.39). Clustering is legitimate: averaging the weighted terms within a task can only reduce the second moment, so $E[\min(W,M)^2]\le M$ survives at the cluster level.

**Required $n_{\rm clusters}$ by gap ($|\Pi|=8$).**

| gap | $M=1$ ($\Pi_0$) | $M=8$ ($\Pi_1$) | $M=64$ ($\Pi_2$) |
|---|---|---|---|
| 0.015 | $2.3\times10^5$ | $1.8\times10^6$ | $1.5\times10^7$ |
| 0.030 | $5.7\times10^4$ | $4.6\times10^5$ | $3.7\times10^6$ |
| **0.046 (only measured headroom)** | $\mathbf{2.4\times10^4}$ | $\mathbf{2.0\times10^5}$ | $\mathbf{1.6\times10^6}$ |
| 0.10 | $5.2\times10^3$ | $4.1\times10^4$ | $3.3\times10^5$ |
| 0.20 | $1.3\times10^3$ | $1.0\times10^4$ | $8.3\times10^4$ |

**Evaluated at this project's numbers ($n_{\rm clusters}=176$; ceiling 230).**

| | $M=1$ | $M=8$ | $M=64$ |
|---|---|---|---|
| required / available at gap 0.046 | 24,429/176 = **139×** short | 195,432/176 = **1,110×** | 1,563,455/176 = **8,884×** |
| same against the 230 ceiling | **106×** | **850×** | **6,798×** |
| **smallest certifiable gap at $n=176$** | **0.542** | **1.533** (exceeds the outcome range — impossible at any gap) | **4.336** (impossible) |
| smallest certifiable gap at $n=230$ | 0.474 | 1.341 (impossible) | 3.793 (impossible) |
| LCB half-width at $n=176$, single policy | **0.254** | 0.973 | 4.786 |
| ratio to the 0.046 gap | **5.5×** | 21× | 104× |

**Verdict, in these words.** The smallest gap this certificate can resolve on this task pool is **0.542** for an unweighted comparison against **0.046** of available headroom — a shortfall of **11.8×** — and it is *arithmetically impossible* for any weighted regime, because the required gap (1.53 at $M=8$) exceeds the range of $Y-\lambda C\in[0,1]$. A one-sided LCB that is always negative certifies nothing. Compute, for completeness: at 3 receiver generation calls per unit and 2,150 calls/hour, $2.4\times10^4$ units is **34 GPU-hours** and $2.0\times10^5$ units is **273 GPU-hours** against the **9.3-hour / 20,000-call** ceiling — 3.7× and 29× over. The "roughly what a stratified A/B test over the $m$ arms costs" sentence is **deleted**; the honest multiple is **50–120×**.

**§6 T20 replacement.**

> ### T20 (finite-sample improvement certificate) — **WITHDRAWN as a deliverable; retained as a scope statement**
>
> We claimed a finite-sample certificate of strict improvement over the logging policy as a headline deliverable. It is **numerically vacuous on this task pool and unaffordable at any gap worth certifying**, and the baseline it certified against was an artifact of the design's own composition. A certificate is available in principle; at the honest inference unit it is uninformative, and we report a paired, family-clustered bootstrap interval instead (E0, R9).
>
> **(a) The bound, correctly written.** With $Y-\lambda C\in[0,1]$, $\hat V_M(\pi)=n^{-1}\sum_i\min(W_i,M)(Y_i-\lambda C_i)$ and $n$ the number of **independent task clusters**, the empirical-Bernstein LCB holds with probability $\ge1-\alpha$ at $L=\log(4|\Pi|/\alpha)$ (union over the pre-registered candidate set **and** over the two one-sided bounds of (c)), giving $n\ge8ML/\mathrm{gap}^2$. Clipping bias is sign-definite, and at the recommended $M=\delta^{-d}$ **clipping never binds and the bias is identically zero**, since $W\le\delta^{-d}$ almost surely in D1 — so (a) is not load-bearing here and the $E[W^2]/M$ bound is vacuous rather than alarming. For the prioritized pseudo-outcome $\tilde Y\in[-1,1]$, certify on $(\tilde Y+1)/2\in[0,1]$; sign-definiteness does not hold on $[-1,1]$.
>
> **(b) The three numbers.** [insert both tables above verbatim]
>
> **(c) Why the baseline was not a baseline.** $V(e)$ is the harness's own $\delta$-floored mixture over eight arms **including** $A_6$ (negative control), $A_7$ (placebo) and $A_8$ (leaky). Each sits at probability 1/8 and drags $V(e)$ down, so $V(\pi)-V(e)$ is **monotone in the number of deliberately degraded arms** and manufacturable with zero learning. In D1 there is also no *natural* policy in the data — the harness replaced the user — so "natural/logging policy" fused two different objects and the word "natural" is deleted. $V(e)$ is a diagnostic denominator only, computed on the **evaluated** stratum $\{A_0,\dots,A_5\}$ with the diagnostic arms excluded.
>
> **(d) What replaces it.** The primary comparison is against a **pre-registered named baseline**, with four denominators in one table: (a) single-shot no-feedback; (b) **B2**, fixed unary retry to $T_{\max}$ with no stopping rule — the zero-information arm `positioning.md` constraint 2 makes mandatory; (c) **B4**, the strong pre-registered baseline the design is powered against; (d) the truncated prophet bound (P22, R21) and $V(e)$ as diagnostics. **The headline gap is against B4**, which strictly dominates the reviewers' demand for a fixed-string denominator: B2 breaks one already-correct answer in six (degradation 0.162), so beating B2 is nearly free and proves nothing — sizing against B2 gives +0.07 to +0.12, against B4 +0.015 to +0.030.
>
> **(e) Never use a self-normalized estimator inside a certificate** — retained as written.

**The library split (mandatory; already in the frozen design).** Add to A5 and §16: the library is partitioned into an **evaluated set** $\{A_0,\dots,A_5\}$ and a **diagnostic set** $\{A_6,A_7,A_8\}$. Diagnostic arms appear in the critic's training data and the leakage/placebo tables; they are barred from every $\pi$, from $\mathcal A_{\rm adm}$, and from every reported baseline value. The value of the policy that *would* be allowed $A_8$ is the **leakage upper anchor**, never the effect of feedback.

**Sections.** §6 (T20 wholesale), §0.2 items 3 and 4, §0.3, §2 (A5, A10), §5 (E4; add E0), §10 (D1 row — delete "a **certified** strict improvement over the logging policy"), §12, §13(b) item 12 (**withdrawn**), §16 items 3 and 14, verdict.

---

### R5. Leakage is post-treatment — build it into the library

**Defect.** The treatment is the selector and the message is drawn *after* it, so $\Lambda(\tilde A_t,H_t)$ is a **descendant of the treatment** and a plausible mediator. Within-$\Lambda$-bin contrasts are mediator-stratified and collider-exposed, not T3 contrasts; "stratify randomization on the bin" is **not implementable** (the bin is unknown until after $K_t$ is drawn); and capping $\Lambda$ is rejection sampling that replaces $q_k$ by a truncated kernel with an unknown normalizer — the D2 catalogue's own failure mode. "Pre-receiver-response" is not "pre-treatment"; the correct word is **pre-outcome**, and it licenses nothing.

**Decision.**

1. **The action is the pair.** Define pinned generators $q_{(g,\lambda)}$ *built* to a target leakage level by construction of their prompts, verified offline against the pinned library before the freeze. The selector is the pair $(g,\lambda)$, jointly randomized at $e=1/8$. The frozen taxonomy already enumerates these: the graded redaction series and $A_8$ (`info_cap_bits` 12, uncapped) are library members at declared levels, and `info_cap_bits` is a frozen **action feature**, not a measured covariate.
2. **$\hat\Lambda$ is a fidelity measurement, never a stratifier and never a filter.** Report the observed $\hat\Lambda$ distribution per arm against the declared level.
3. **Rejection sampling on realized $\Lambda$ is prohibited confirmatorily.** If run, it is a separate arm, labelled a redefinition of the generator with an uncomputable density, excluded from P4, reported as ITT over the *unfiltered* generator with the rejection rate.
4. **Redefine $\Lambda$ as conditional information:** the log-likelihood gain of a fixed reference receiver on the reference solution given $(H_t,\tilde A_t)$ relative to given $(H_t,\text{null message})$ — condition on task and prior output, withhold nothing but the message. The task-blind placebo solver is withdrawn: "you forgot the base case" carries near-zero information to a solver that has not seen the task, so leakage here is almost entirely task-conditional and a task-blind scorer has no dynamic range over exactly the messages that matter. The old caveat "unsigned" is **wrong in a known direction**: $\hat\Lambda$ *understates* leakage, which makes the leakage-controlled contrast look **larger**. Validate dynamic range on a planted set (messages that literally state the fix score at the top; pure-affect messages at the bottom).
5. **Answer-withholding is promoted from an arm to an architectural invariant.** Generators receive a redacted view $X^-$ with reference solution and tests removed, enforced by prompt-hash assertion in §16 item 1. Answer-visible ($A_8$) runs only as a declared positive control.

**What is identified.** Contrasts across $(g,\lambda)$ pairs — "assign generator $g$ at built-in leakage level $\lambda$" — by T3 with **no conditioning**. The $\lambda$ main effect and the $g\times\lambda$ interaction are identified by design at the same cost as any other class contrast.

**What is not identified.** The effect of $g$ *holding realized $\Lambda$ fixed* (a mediator-controlled direct effect); any contrast conditioning on $\hat\Lambda$; natural direct/indirect leakage effects (§12 item 6, keep it). Under the restricted-kernel reading a new condition $P_{q_g}(\Lambda\in b\mid h)\ge\delta_\Lambda$ would be required at every history and will fail exactly where it matters — a maximally severe generator may never emit a low-leakage message. We do not take that route.

**A12 replacement (§2 table).**

> | A12 | **Leakage is a coordinate of the randomized action space, not a covariate.** Pinned generators are built to declared leakage levels $\lambda$, the pair $(g,\lambda)$ is randomized, and $\hat\Lambda$ — the conditional-information score above — is a fidelity measurement that is never conditioned on, stratified on, or filtered by. Generators see the redacted view $X^-$, enforced by prompt-hash assertion. | **BC** for the design coordinate; **A** for scorer dynamic range, with the bias direction stated: $\hat\Lambda$ understates leakage, which inflates leakage-controlled contrasts |

**Strings to delete.** T16's "involves **no post-treatment conditioning**"; "bin it; stratify randomization on the bin"; §13(c)'s "**Leakage is a pre-treatment design coordinate**, not a mediator" → "**Leakage level is a coordinate of the randomized action space; the realized leakage score is post-treatment and is never conditioned on.**"

**The same defect, same fix, for length and position — do not skip.** Severity and specificity classes differ systematically in token count, and the feedback message is always the most recent context, so a long message pushes the task specification further from the generation point. Both are **caused by the randomized selector**, hence mediators, and the offered remedy ("within a $\Lambda$ bin, message length no longer predicts $Y$") is a low-power observational regression on post-treatment variables. A positive "severity helps" result is fully explained by "longer prompt, task spec re-anchored closer to the generation point". Decision, affordable: **(a) harness requirement, all arms** — re-render the task specification at a **fixed token distance** from the generation point in every arm, padding with inert filler verified at $\hat\Lambda=0$ (prompt geometry; costs nothing; removes the position channel). **(b) a separate pre-registered length-calibration block**, not a second primary axis: each class at 2 pre-registered token budgets plus a **filler-only arm** (pure context-length increase, no semantic content) — 190 tasks × 3 arms × 1 turn ≈ **570 calls ≈ 0.27 h**. **(c)** the class effect is reported **net of the measured length main effect** from that block, and the document states that without the block the class effect is confounded with length by design-mediation. `suffix_words` is a frozen action feature — a design covariate of the arm, not a measured covariate of the message.

**Sections.** §2 (A12, A5), §8 (T16 wholesale), §13(c), §16 items 2 and 7, §12 item 6, §15 item 15.

---

### R6. The prioritized outcome — freeze $G_0$ on an independent, already-existing log

**Defect.** "Prespecified $\pi_0$" pins the *regime*, not the *functional* $G_0$, the mid-rank CDF of $u(Z)$ under $\pi_0$ — an unknown feature of $P$ that must be estimated, off-policy, from the same data. With $\hat G_0$ plugged in: $\tilde Y_i$ is not a fixed function of $Z_i$ and the $\tilde Y_i$ are dependent, so the martingale-difference argument fails; $Q_t(\cdot,\texttt{STOP})$ needs $G_0$ and is no longer known even in the T8a sense; and T9(i)'s exact unbiasedness is lost. The document then displays the two-term EIF $\varphi_\pi[G_0^-]+\varphi_{\pi_0}[\bar G_\pi]$, which **is** the statement that T9 does not apply verbatim.

**Decision — option (i), and take the free one.** $G_0$ is computed from the **sibling project's completed 4,488-episode log** (`ykzeng-yale/DTR-AgentEvals`, identical `tasks_sha256`, verified not assumed; same machine, inference server and quantizations), hashed and frozen **before any outcome of this run is examined**. Zero GPU time, zero clusters, genuinely independent of this run's outcomes.

**Consequences, all to be stated.** $\tilde Y=2G_0(u(Z))-1$ is a **fixed known measurable transform**, so T8a and T9 do apply verbatim, exact unbiasedness survives, and the stop-arm value is known in the T8a sense. **The price:** the win-probability semantics are relative to the **frozen sibling reference distribution**, not a concurrent $\pi_0$; the sibling's prompt format and grading are its own, so $G_0$ is a reference from a related but not identical regime. That is acceptable because $G_0$'s only job is to be a fixed monotone transform, but it must be said: "the reported win probability is against the frozen sibling log, and $\pi^\star$ is reference-dependent." Option (ii) — $\hat G_0$ as a nuisance with the two-term EIF and the bilinear remainder in $(\hat G_0-G_0,\hat Q-Q)$ — is **not used confirmatorily**; retain the two-term EIF in §7 as what *would* be required, noting that exact unbiasedness would not survive and the claim would degrade to "doubly robust with a second-order remainder". Add $G_0$ to §15 item 6.

**Replacement for "Then T8 and T9 apply verbatim with $Y$ replaced by $\tilde Y$; the stop arm's value remains known".**

> With $G_0$ **frozen on an independent pre-registered reference sample** — here the sibling project's completed 4,488-episode log on the identical task pool, hashed before any outcome of this run is examined — $\tilde Y$ is a fixed known measurable transform of the unit's own terminal record, and T8a and T9 apply verbatim with $Y$ replaced by $\tilde Y$; the stop arm's value remains known in the T8a sense. Were $G_0$ instead estimated on the analysis sample, none of that would hold: $\tilde Y$ would carry an outcome-law nuisance, the units would be dependent, the two-term influence function $\varphi_\pi[G_0^-]+\varphi_{\pi_0}[\bar G_\pi]$ displayed below would be the correct expansion, exact unbiasedness would be replaced by double robustness with a second-order remainder, and $Q_t(\cdot,\texttt{STOP})$ would become an estimated nuisance. The freeze is what buys the verbatim reuse, and its price is that the win probability is reference-dependent on a *frozen* reference.

**Additional decision: T13/T14 are demoted to a secondary reporting device.** The primary objective is $E[Y^\pi-\lambda C^\pi]$ at $\lambda=0.01$/turn read off the measured budget (R13), with **degradation reported separately** as audits A3 requires. Reason to state: $Y$ is a binary hidden-test verdict, $N\in\{1,2,3\}$, and cost is monotone in $N$ up to token noise, so with tolerances the ordered quotient has ~6 cells and the tie mass is the majority of pairs — the win-probability estimand is a coarse monotone re-expression of a $2\times3$ table whose variance is dominated by tie handling, and it *shrinks* an effect already at 0.015–0.030. Report the tie mass. Scope T13 to outcomes with a continuous or many-valued primary component.

**Sections.** §7 (T13/T14, P12), §2 (A17), §0.2 item 6, §5 (E5), §13(b) item 5, §15 item 6, §16 item 2.

---

### R7. The density cancellation requires stateless generators

**Defect.** T3's proof requires $q_k$ to be a kernel in the recorded $H_t$ alone and conditionally independent of $K_{1:t-1}$ given $H_t$. Any carried KV cache, persona or scratchpad memory, surviving reasoning tokens, persistent tool/retrieval handle or server-side conversation id gives $q_{K_t}(\cdot\mid H_t,U_t)$ with $U_t$ a function of $K_{1:t-1}$: $U_t$ is then **post-treatment with respect to earlier selectors and mediates them**, the $q$ factors differ between the $e$-law and the $\pi$-law, and **they do not cancel**. P2 collapses at the same point — "assign generator $k$" no longer names a fixed kernel. This is the default implementation of a multi-turn LLM user, so it must be barred, not assumed away.

**A5 replacement (§2 table).**

> | A5 | Pinned, pre-registered, version-hashed generator library, invoked **statelessly**: every generator call at turn $t$ is issued in a fresh process from a context constructed **deterministically from the recorded $H_t$** and the redacted view $X^-$ — no carried KV cache, no persona or scratchpad memory, no cross-turn hidden state, no reasoning tokens surviving the call, no tool or retrieval handle persisting across turns, no server-side conversation id. The library is partitioned into an **evaluated** set $\{A_0,\dots,A_5\}$ and a **diagnostic** set $\{A_6,A_7,A_8\}$ (R4). | **BC** for the frozen template library (deterministic renders with a seeded uniform template index); **A, and verified** for any LM-generator arm |

**Verification — §16 item 1 sub-items; each must be reported.**

> (a) **Input-provenance hash.** SHA-256 of the fully rendered generator prompt is logged per call and must equal the hash recomputed offline from the recorded $H_t$ and $X^-$ alone, **byte-exact**. Any mismatch is a hard failure of A5.
> (b) **Fresh-context assertion.** A new server session per call with prompt caching disabled and an explicit cache reset, asserted and logged per call.
> (c) **Out-of-order replay test.** Re-issue a random 2% sample of generator calls out of chronological order from the same recorded $H_t$ with the same seed and require **byte-identical** output. (CPU-side for the frozen template library, so effectively free.)
> (d) **On failure of (a)–(c):** the history is redefined to include the carried state ($H_t$ must contain $U_t$), and A9's $\varphi$-measurability and every "no text critic" claim must be restated on the enlarged history. State this consequence in the text.

**Also correct the D2 catalogue (§10).** "Discarded chain-of-thought is *pre-treatment generation randomness*, not a mediator, so ignorability survives and only computability fails" is **true for a within-turn scratchpad discarded before the next call and false for any state carried across turns**. Rewrite with that qualification, cross-referencing A5.

**Consequence for P4 (state it there).** In the frozen design the generators are deterministic template renders with a uniformly drawn index over 3 frozen templates using the episode seed, so $q_k$ is a point mass given the recorded index and distinct $k$ produce distinct texts: numerator and denominator each collapse to one term, **the marginal weight equals the selector ratio exactly, and the Rao–Blackwell variance reduction is identically zero**. For LM generators, computing $q_k$ for the $m_G-1$ untaken arms costs $m_G$ teacher-forced scoring passes per turn on the realized message, using the *sampling-time truncated* distribution — a cost that competes directly with the branch budget and must be priced before P4 is used. P4 is therefore **an identity with no gain in the primary design and non-free in the only design where it bites**.

**Sections.** §2 (A5), §3 (T3 proof, P2, P4), §10 (D2 row and catalogue), §16 item 1, §13(b) item 6.

---

### R8. The policy class, defined as a $\sigma$-algebra

**Defect.** "Choke-point-measurable" is never defined. On verbatim text histories every $Q_t$ sits at atoms of probability $e^{-\Theta(mt)}$ visited once, and the max over such a class has optimism equal to the outcome's full range. On $\varphi$-measurable rules **T8's Bellman recursion is invalid**: the optimum over a restricted, non-sufficient class does not satisfy a Bellman equation, and backward induction returns the greedy-in-restricted-class rule. T9's robustness is a property of *evaluating* a fixed $\pi$, not of *optimizing*. And $|\Pi|=100$ is a finite candidate count while $\Pi_{\rm cp}$ as used is infinite.

**§1 replacement for the $\pi^\star$ bullet.**

> **The policy class.** Let $\varphi_k$ be the pre-registered, frozen, finite-dimensional feature map of R3 (the 87-coordinate state code, frozen as data before any fit, with $\psi$ and every hidden-test-derived quantity excluded), and $\mathcal F_k^O:=\sigma(\varphi_k(H_k))$. Then
> $$\Pi_{\rm cp}:=\Big\{\pi=(\pi_1,\pi_2):\ \pi_k\ \text{is }\mathcal F_k^O\text{-measurable, valued in the simplex over }\mathcal A_{\rm adm}=\{A_0,\dots,A_5\}\Big\},$$
> with the depth-graded subclasses $\Pi_0\subset\Pi_1\subset\Pi_2=\Pi_{\rm cp}$ of R2. Because $\mathcal F_k^O\subsetneq\sigma(H_k^A)$, **$\varphi$ is not sufficient**, so the restricted optimum does **not** satisfy a Bellman equation on $\varphi$-measurable value functions: backward induction on $\hat Q_k(\varphi_k,a)$ returns $\pi^{\rm greedy}\in\Pi_{\rm cp}$, which is in general $\ne\arg\max_{\Pi_{\rm cp}}V$. **A19b (state-representation sufficiency) is NOT assumed by the primary route.** Accordingly the reported object is
> $$\hat\pi:=\arg\max_{\pi\in\Pi}\widehat V(\pi)$$
> over a **pre-registered finite candidate set $\Pi$** whose count is declared in §16, with $\pi^{\rm greedy}$ entered as one member labelled "greedy-in-$\varphi$". $\hat\pi$ is evaluated out-of-fold (5 folds over the 176 families; all seeds, branches and turns of a family in one fold), the winner's value is re-estimated on the held-out half, and the selection inflation is reported (R16). The phrase "the optimal regime" is reserved for $\arg\max_{\Pi_{\rm cp}}V$, which this design does **not** report.

**T8 consequential insertion, after the $V_t^\star$ display.**

> This recursion targets the **unrestricted-class** optimum. Under the $\varphi$-measurable class of §1 it returns $\pi^{\rm greedy}$, not $\arg\max_{\Pi_{\rm cp}}V$, unless A19b is assumed — which the primary route does not assume. The reported object is $\hat\pi$, the best member of the pre-registered candidate set.

Replace every "$|\Pi|=100$" with "the pre-registered candidate count declared in §16", and print the certificate arithmetic at $|\Pi|=8$ and $|\Pi|=100$ so the sensitivity is visible ($L=6.461$ vs $8.987$, factor 1.39). Where a covering-number bound would be needed for an infinite class, say so and say we do not have one.

**Sections.** §1, §4 (T8), §5 (State representation → A19b), §6 (T19, T20), §10 (D1 row), §16, §12, verdict.

---

## PART II — FURTHER CROSS-CUTTING DECISIONS THE FINDINGS FORCE

As binding as Part I. Each resolved once, here.

### R9. The inference unit, and the reordering of primary and secondary routes

**Defect.** The certificate and §4's arithmetic are in "conversations" while §1 declares the task instance and §5 requires all branches, seeds and turns of one task to share a fold; (task × seed) manufactures unlimited units from a ~230-element population whose task text is the dominant variance component (per-task first-attempt success is Beta(0.348, 0.230), strongly U-shaped). Separately, the only affordable experiment is a **paired, common-random-number, on-policy** head-to-head, and no formula in the document contains the between-task variance that pairing removes.

**Decision.**
1. **The i.i.d. unit is the task instance (task text only).** Seeds, branches, turns, templates and paraphrase variants are within-cluster. $n_{\rm clusters}=176$ families; pool ceiling ≈230. Replace "conversations" with "task clusters" and state $n_{\rm clusters}$ wherever $n$ appears in a bound.
2. **Add E0 (additive; do not renumber E1–E7).**

> **E0. Paired common-random-number on-policy contrast (primary).** All arms branch from the **same saved root output $O_1$** per (task, seed) unit; the paired difference $D_i\in[-1,1]$ is formed within unit; the statistic is the mean over the 176 task families of the family-mean paired difference, with a **paired cluster bootstrap over families, $B=10{,}000$, percentile 95% CI**. It **cancels the between-task difficulty variance**, the dominant component here. Measured at $R=8$: **half-width ±0.019**, **MDE 0.027** at 80% power; unpaired power at $\delta=0.05$ is 0.31 against $\ge0.95$ paired. No importance weights appear.
> *Against the withdrawn certificate (R4):* the best-case finite-sample LCB half-width at $M=1$, $n=176$ is **0.254** — **13×** wider. Even a *paired* empirical-Bernstein bound on $D_i\in[-1,1]$ at the measured $s_D\approx0.129$ has half-width **0.125** — still **2.7×** the 0.046 of headroom and **6.6×** E0's. **At $n_{\rm clusters}=176$ no nonasymptotic bound of any kind resolves the effect: finite-sample validity costs more than the entire prize.** The primary inference is therefore asymptotic, and the document says so plainly.

3. **§0.1 replacement.** "**We adopt as PRIMARY: on-policy paired rollout in a resettable harness, over a finite, pre-registered prompt-generator choke point with logged propensities.** The design-based off-policy apparatus is retained for the three jobs it genuinely does: reusing one expensive branch tree across many candidate policies, the shallow-deviation scope statement of R2/R4, and the observational extensions. Where the environment is resettable, off-policy evaluation must justify itself (§12 item 15, E7); for the primary comparison it does not, and we run the policy."

**Sections.** §0.1, §0.2 item 1, §1 (Units), §4, §5 (add E0; cross-fitting), §6, §12, §16 items 3 and 8.

### R10. The confounding narrative must carry the project's own refutation

**Decision.** Rewrite §1's last paragraph and §0.2's framing:

> The claim splits, and the halves have different evidence. **Reported effects:** an unadjusted comparison of intervention classes on logged data inverts the true ordering — **0/40** replicates recovered the L-vs-U sign; in P2 the optimal first intervention had the *lowest* observed mean (**0.186** against **0.637** for a perfunctory retry) and sequential randomization on the same law ranked the classes correctly. This is robust and it is a claim about **how logs must not be read**. **Decisions:** the corresponding claim is *refuted as stated*. A correlational critic conditioning on the full observed state recovered the exact optimal regime in **39/40** replicates, mean regret **0.0010**; adding a latent confounder and sweeping the coupling moved the logged-minus-randomized regret gap by at most **0.030**; and known-propensity IPW repaired that residual only partly and **non-monotonically** ($0.046\to0.033$, $0.028\to0.028$, $0.017\to0.019$ — one cell got worse). The dominant decision-level error was **myopia**, which loses under randomization too, so it is not a confounding failure at all. The motivation for the critic is therefore **horizon-aware valuation under known propensities**, not confounding correction, and the framework's baseline is a **pre-registered non-myopic correlational critic** it must beat.

Also apply R22(a) to §1's closing sentence; add the premise numbers and the non-monotone IPW repair to §12; §13(c) keeps the framing bullets and loses the decision-level claim. The design already pre-registers S1 (causal vs matched correlational critic) with **expected value: null** and S2 (lookahead vs myopic) as positive and larger — claim no more than that. **Sections:** §1, §0.1, §0.2, §12, §13(c).

### R11. Novelty, positioning and the contribution list

**Decision.** §13 and §15 **cite, not re-derive**: prompt-as-treatment (Wang AAAI-25; Frauen KDD 2026; CPO arXiv:2602.01711); DTR/Q-learning over a natural-language action space (**arXiv:2502.17538**); longitudinal causal inference over sequences of text features (**arXiv:2605.07834**); single-period text-treatment identification (**arXiv:2410.00903**); per-context off-policy prompt policy learning (**arXiv:2504.02646**); neural SNMM/blip estimation (DeepBlip **arXiv:2511.14545**); orthogonal DR Q-learning (DRQ-learner **arXiv:2509.26429**); plus **arXiv:2607.03597**, **arXiv:2404.00207**, **arXiv:2512.04068**, **arXiv:2510.25441**. Add: "we are the first to formulate multi-turn prompting as a DTR" is **false**, and "causal critic instead of a correlational reward model" is CPO's published position, not ours. **Demote §13(b) items 1, 2 and 9** to "useful accounting identities" in §4 (the tower rule plus a one-line change of measure; monotonicity of Rényi divergences composed with the autoregressive KL chain rule, whose conclusion is folklore in the OPE/RLHF literature; a textbook needle-in-a-haystack). **Withdraw §13(b) item 12** (R4). Lead §13(b) with the claim `positioning.md` says survives: **prospective sequential randomization of an in-conversation intervention with logged propensities, plus branch-sampled validation (T27)**. **Sections:** §13(a)–(c), §15, §0.2, verdict.

### R12. A2, drift, and A1's status

**Defect.** §5 clusters SEs by **model-version epoch** and "balances" drift, while A2 says a version change makes the estimand **undefined, not noisy** and §12.9 says SEs covering version generalization would be misleading. Both cannot hold, and few-cluster cluster-robust inference is invalid anyway. A1 is graded BC while the receiver runs `llama-server -np 4` under **foreign GPU load from a sibling project** (`ICLR-WinRatioAgentEvals`, not `DTR-AgentEvals` as COORDINATION states — correct that line) and llama.cpp is not bit-deterministic across batches at a fixed seed.

**Decision.** (1) **Delete "model-version epoch" as a clustering level.** Cluster by **task family** only, plus time block for within-epoch nuisances (load, latency). Replace "balance the drift" with a **tripwire-and-discard rule**: a fixed canary prompt battery replayed at the start of every block, compared by the P18(c) two-sample next-token log-probability test with pre-registered multiplicity control; on detection the affected blocks are **excluded** and the run is reported as two separate receiver-conditional analyses. State that time blocking is **not** a remedy for a version change. (2) **Downgrade A1:**

> | A1 | Task-level units, no cross-trajectory interference | **A (assumed)**, with randomized batch composition, per-task budget pools, a canary battery per block, and a pre-registered drift diagnostic (arm × time-block interaction, with `foreign_gpu_load_at_start` and `yielded_seconds_before_start` as covariates). Not BC: the receiver runs at `-np 4` under uncontrolled foreign GPU load and is not bit-deterministic across batches at a fixed seed. |

Same wording in the §10 ladder A1 row for D0/D1/D2. "Verify caching changes latency and not tokens" is **withdrawn as powerless** — prefix caching changes kernels and numerics, not token counts — and replaced by the canary battery plus R7(c). (3) **Deep-slice hygiene:** interleave branch expansions across task instances with a cooldown rather than expanding a node's arms back to back; randomize expansion order; power the P18(c) duplicate-arm check on the deep slice and report the duplicate-arm discrepancy alongside $\hat v$; **if the discrepancy exceeds $\hat v$, declare $\hat v$ and $\hat R$ unusable.** **Sections:** §2 (A1, A2), §5, §9 (P18c), §10, §12 items 9 and 13, §16 item 12.

### R13. $\lambda$ is pre-registered, not selected by duality on the analysis sample

**Decision.** $\lambda$ is **pre-registered at 0.01 per turn**, with the grid $\{0,0.005,0.01,0.02\}$; if any interval is reported at more than one $\lambda$, a union bound over the 4 points is applied and stated. T8 replacement:

> A budget-constrained optimum equals the unpenalized optimum of $E[Y^\pi-\lambda C^\pi]$ for some $\lambda\ge0$ by LP duality over the convex hull of attainable (value, cost) pairs. That is an **interpretation** of a pre-registered $\lambda$, not a licence to select $\lambda$ on the analysis sample: the dual multiplier is a functional of $P$, so an interval computed at a data-chosen $\hat\lambda$ is not valid at its stated level and the influence contribution of $\hat\lambda$ is omitted from the displayed EIF. We therefore pre-register $\lambda=0.01$ per turn from the measured budget and report the grid with a union bound.

Also correct E2's residual to $U_{it}(\beta)=(Y_i-\lambda C_i)-\sum_{s\ge t}\gamma_s(\cdot)$. **Sections:** §4 (T8), §5 (E2), §6, §7, §2 (A10), §16 item 13.

### R14. A18 splits; "exactly unbiased" is restricted to the estimator that has it

**Defect.** A18 is marked "vacuous in D1" because $e$ is known, collapsing two conditions. The *rate* condition is vacuous; the **sample-splitting** condition is not — without cross-fitting $E[\hat\psi]\ne\psi$ even with $e$ exact. The TMLE listed as co-primary in E1 fits its fluctuation on the data it evaluates, so it is **not** finite-sample exact; neither are clipped IPW or any self-normalized variant.

**Decision.** Split A18, keeping the number:

> | A18a | **Cross-fitting / sample splitting**: $\hat Q$ fold-independent of the evaluation fold | **required in every design, including D1** |
> | A18b | Corrected cross-term product rate on $(\hat e,\hat Q)$ | **vacuous in D1** (only here); required where $e$ is estimated |

Restate T9(i):

> **(i) Exact unbiasedness.** For any $\hat Q$ that is **fixed conditional on the evaluation fold** (A18a) and **internally consistent**, $\hat V_t(h)=\sum_k\pi_t(k\mid h)\hat Q_t(h,k)$, and with $e$ known, $E[\hat\psi]=\psi$ **exactly**. This holds for the cross-fitted one-step / AIPW form. It does **not** hold for TMLE (fluctuation fit on the data it evaluates — asymptotically equivalent, $O(1/n)$ finite-sample bias), clipped IPW (biased by construction), or any self-normalized variant. A critic emitting $\hat V$ directly, or independently fitted $\hat V$ and $\hat Q$, destroys the telescoping; P10's branch-augmented version survives because the two rollout estimates agree **in expectation**.

Amend §0.2 item 3: "a cheap badly-calibrated LLM critic carries **zero bias risk for the value estimate under A18a; its error enters the learned regime at first order through T19 and supplies the stop decision through T8b**, and those are the deliverables." Replace T9(ii)'s $E[W^2\hat Q^2]<\infty$ (vacuous under $W\le\delta^{-d}$ and bounded $\hat Q$) with $\|\hat Q_t-Q_t^\infty\|_{L_2(W_{1:t}\cdot P)}=o_P(1)$, $\hat Q$ fold-independent. **Sections:** §2 (A18), §5 (T9(i),(ii); E1), §0.2 item 3, §10, verdict.

### R15. Design allocation: the wide-shallow prescription is inverted

**Defect.** Substituting $n=B/(c_0+n_b)$ gives $f(n_b)=(\sigma_e^2/n_b+\sigma_m^2)(c_0+n_b)$ with derivative $\sigma_m^2-\sigma_e^2c_0/n_b^2$: **decreasing** at $n_b=1$ whenever $\sigma_e^2c_0>\sigma_m^2$, with an interior optimum.

**§16 item 4 replacement.**

> 4. Make it possible to draw several messages from the same history. The budget-optimal replicate count is $n_b^\star=\max(1,\sigma_e\sqrt{c_0}/\sigma_m)\approx\mathbf7$ at the measured $(\sigma_e,c_0,\sigma_m)=(0.5,2,0.10)$ — $\sigma_e\approx0.29\sqrt3$ from the measured per-state SE — re-estimated in the pilot; $n_b=1$ is optimal only when $c_0\le\sigma_m^2/\sigma_e^2$. The **frozen design uses $n_b=3$**, **budget-constrained below $n_b^\star$**: $n_b=7$ at 400 states × 8 classes is 22,400 nodes, above the 20,000-call ceiling. State the consequence: at $n_b=3$ the per-state Monte Carlo SE is up to **0.29** and $\hat v\approx p(1-p)/3\approx0.08$, so ground truth is usable **pooled or on strata, never per state**, and T27 is a **ranking** device only (R16). The prescriptions "$n_b=1$ wide" and "$n_b\ge8$ deep" are both **withdrawn** — the first is the inverted optimum, the second is 25,600 nodes and unaffordable.

**Sections:** §5 (P5b), §9 (T27), §16 item 4, §13(b) item 7.

### R16. T27 is a ranking device; selection inflation applies to it too

**Defect.** (i) $E[\hat v]$ must average over the **same** history law as the squared-error term, but the deep slice is deliberately narrow and selected while the wide slice cannot estimate $v$ at all; (ii) at $n_b=3$ the offset $\hat v\approx0.08$ is **2–8× the estimand** $E[(\hat\gamma-\gamma)^2]\approx0.01$–$0.04$; (iii) the tree's depth-2 continuations are **policy-fixed** while the critic's target is the blip under an optimal continuation, so T27 is unbiased for the wrong target by construction; (iv) selecting the minimum over $L$ learners on one noisy criterion computed on the smallest sample in the study reproduces the winner's curse P11 and P24(ii) quantify elsewhere and §13(a) cites Andrews–Kitagawa–McCloskey for.

**Decision.**
> **T27 — restated as a ranking device.** Report the **paired difference of squared errors** between candidates on the same oracle labels with its family-clustered bootstrap interval; the offset cancels and no variance estimate is needed. The **absolute** risk requires the matched-slice condition (the deep slice a uniform random subsample of the wide slice's histories) **and** an $n_b$ making $\hat v$ small relative to the risk; at $n_b=3$, $\hat v\approx0.08$ against a risk of 0.01–0.04, so the absolute number is **not reported**. Scope restriction, not caveat: $\tilde\gamma$ is the blip under the **fixed continuation regime** the tree ran, so every claim is "validated against the fixed-continuation blip", and the depth-2 supplement (200 states × 8 classes × 2 seeds = 3,200 rollouts) is too small to repair the mismatch. Split the deep slice into a **ranking half and a reporting half**, report the winner on the held-out half, and report $L$, the spread of $\hat R$ across candidates, and an AKM- or Bonferroni-corrected interval. Pre-registered validation targets: the class **ordering** of pooled $\gamma$, the pooled $\rho$ and $\beta$ per class, and the sign and rank correlation of $\hat\gamma$ against the state-level Monte Carlo values.

Apply R12(3)'s deep-slice hygiene and duplicate-arm kill switch here. **Sections:** §9 (T27), §5 (P5b, P11), §16 item 4, §13(b) item 8.

### R17. T19's value-loss bound is true and vacuous at achievable precision

**Decision.** Keep the $L_1$ bound, add the margin form, print the measured scale:
> $V(\pi^\star)-V(\hat\pi)\le E\big[|\gamma|\mathbf1\{|\hat\gamma-\gamma|\ge|\gamma|\}\big]\le E|\hat\gamma-\gamma|$. The $L_1$ form is **vacuous at achievable critic precision here**: label noise on the blip pseudo-outcome is Bernoulli, the per-state MC SE at 3 seeds is up to 0.29 and the pooled per-row noise SD of a paired binary contrast is $\approx0.5$, so at ~9.6k rows and 87 features an honest $E|\hat\gamma-\gamma|$ is $O(0.1)$ — **2–4× the entire 0.046 of available headroom** and larger than the true blips themselves (repair 0.239 and breakage 0.162 imply $|\gamma|$ mostly below 0.25 and often below 0.05). "You lose at most 0.1–0.2 of value" is not a guarantee on a scale where the total prize is 0.046. We therefore report the **measured distribution of $|\gamma|$ and of the critic's per-state error** so the reader can see whether the margin form bites, rather than quoting the $L_1$ bound as a result.

**One sentence, verbatim, in §0.3 and §12:**
> A trained free-form **generative** prompt policy leaves the pinned library and is therefore **outside every guarantee in this document**: by T26(b) and §12 item 2 its value is neither identified nor certified, and T19 does not apply to it. §0.2's "every treatment is a shippable mechanism" does not extend to it.

**Sections:** §6 (T19), §0.2 item 4, §0.3, §12, §11.

### R18. Falsification: two controls with a known truth, and the closing sentence rewritten

**Defect.** P18(d)'s negative control has **no valid null in the document's own framework**: §2 ("LLMs are paraphrase-sensitive") and §11.1 assert that a frozen receiver responds differently to stylistic variants, so a non-zero politeness effect is a *true* effect, not an indictment — precisely the error §11.2 prohibits. And (a) has no power with degenerate weights, (b) is not exact under an adaptive design, (c)'s power against state leakage is OPEN. No item has both a valid null and demonstrated power, which inverts §9's closing sentence.

**Decision.**
> **(d1) Guaranteed null.** An arm perturbing only text rendered to the user-side channel and **provably withheld from the receiver's context** (the receiver-side half of T25(d), verifiable by inspecting the rendered prompt): a software-verifiable **zero** on $Y$. A non-zero effect is a harness bug, full stop.
> **(d2) Guaranteed positive.** An arm appending the reference fix ($A_8$, the leakage upper anchor), whose effect must be large. Report it as the design's **measured ceiling** and the scale against which every other arm is read; never as the effect of feedback.
>
> Closing sentence, replacing "A run that does not report (a)–(d) is not an experiment": "(a) detects tokenizer/template mismatch, undisclosed retries and sampler drift, **and has no power when $E[W^2]/n$ is not small**; it must be run in the stopped/indicator form of R22(f) on bounded prefix weights at small $t$. (b) is **not exact** under a history-adaptive design and requires a non-adaptive schedule or a sharp null on the whole output path. (c) has high power against version drift, prefix and template mismatch, and its power against subtle state leakage is **OPEN**; its multiplicity control must be stated. (d1) has a software-verifiable null and (d2) a known-large truth. A run that does not report (a), (b), (c), (d1) and (d2) **with the power of each stated** is not an experiment; a run that reports a politeness null as evidence of design validity has tested a hypothesis that is a priori false."

**Sections:** §9 (P18), §7 (T25(d) — R22(h)), §11.2, §16 items 10 and 11.

### R19. The horizon-invariance test has zero power; replace it

**Decision.**
> **WITHDRAWN: the horizon-invariance calibration test** (§8, §16 item 5) had **exactly zero power** under P15(f), because with the judge shown only the final artifact the two presentations feed it **byte-identical input**. The channel that produces the P24(iii) threshold shift is the mediated one P15(f) does not cut: longer conversations produce stylistically different artifacts (longer, more hedged, more commented) and the judge rewards those. Replaced by: within strata of identical programmatic content signature, regress the judge score on artifact length and style features and estimate $\beta$ directly; report the induced threshold shift $\beta/\lambda$ in cost units as a **mandatory number**; and report the **artifact length distribution by horizon arm**, since a length imbalance across arms is by itself sufficient to generate the whole horizon result.

**Also compress §8.** The primary outcome is programmatic with the audited visible/hidden split, so the judge machinery governs **no primary number**. Keep: R3's $\varphi$-exclusion (replacing channel separation), selection/evaluation splitting, the replacement test above, P15(d)'s corrected variance (R22(o)), and a one-line pointer for a judge used as a secondary outcome. Cut the rest to a paragraph. **Sections:** §8, §2 (A11(c)), §12 item 7, §16 item 5.

### R20. Contamination inflates the stop-arm advantage; P24(ii)'s $\sigma$ is defined

**Contamination.** §12.10's attenuation-only reading is **withdrawn**: on a memorized task the receiver is already correct at turn 1, so the `STOP` blip is *inflated* (stopping immediately is genuinely optimal there), the cost-priced value of any early-stopping regime rises relative to a talkative mixture that keeps paying $c_t$, and the learned horizon is biased short. Contamination therefore **inflates** the certified and cost-priced gaps: the headline is **anti-conservative** under the document's own primary objective. It also distorts $G_0$ through the $C$ and $N$ components. Amend §12.10 to "contamination attenuates **content** blips and **inflates** stop-arm advantages and cost-priced gaps"; report the primary comparison and the prioritized net benefit **within the pre-registered uncontaminated stratum** with the contaminated stratum separate; and require a **per-task contamination score** — turn-1 pass rate under a single-shot no-feedback arm — as a **stratification variable in §16 item 3** (affordable: that arm is already a required denominator under R4(d)).

**P24(ii).** Define $\sigma$ as the **standard error of the value estimate at the analysis $n$** and write the selection inflation as $\Theta\big(\sigma\sqrt{\log\bar K/n_h}\big)$, $n_h$ the number of independent scorings per decision node ($n_h=1$ for a per-trajectory argmax, $n_h=n$ for a global rule). At the measured paired SE $\approx0.010$ and $\bar K\approx5$ the global-rule inflation is $\approx0.013$ — real, below the 0.027 MDE, removable by the selection/evaluation split P11 already recommends. Present **P24(i)'s within-unit bias $E[\varepsilon_\tau]$ separately** as the part that does **not** average away, and keep "comparable to real effects" **only** for $n_h=1$. Justify the channel requirement from P15(a)'s differential-bias argument plus P24(iii). **Sections:** §12 items 7 and 10, §8, §16 items 3 and 5, §15 item 7.

### R21. P22 restricted; prophet constant deleted; target-trial claim narrowed

**Decision.**
> Reporting device: "at most $X$ points of quality are recoverable by any rule **that never continues past the natural horizon**; our learned rule recovers $Y$ of them", **under A21 and the T8a stop-arm structure** (equating the observed $\psi(H_{\tau'})$ with the truncated regime's value requires both). Regimes that force continuation past the natural stop — the point of P23 and Ext-E — are **not** bounded by this benchmark and require P23's weights. The unrestricted claim over all implementable rules is false, by the document's own counterexample. **The i.i.d. prophet constant $\approx0.745$ is deleted**: $\psi(H_1),\dots,\psi(H_T)$ is a dependent, non-stationary adapted process with a random endogenous horizon, and no constant-factor prophet guarantee holds for dependent sequences (the independent non-identical case gives only 1/2). If a competitive ratio is wanted, compute it in the simulator for the actual process.

**Same class of over-claim, §0.2 item 4.** In D1 the treatment is a generator of the **user's** messages executed by a simulated user, and no product ships a mechanism that writes its users' turns (§12 item 3 concedes this; P31 concedes the human analogue is ITT). Restrict shippability and the target-trial framing **by name** to the product-side coordinates — `STOP`/continuation, interface and rendering variants, suggestion policies — and state in §0.1 that **message-generator arms are a measurement device for blips, not a deployable protocol**. Those are also the only coordinates the measured evidence values (+4.6 pp from stopping alone). In §0.4's Ext-E row replace "the strongest possible identification position" with "the **weakest positivity requirement**" (the exchangeability burden is unchanged), and restate the identified-set width for the cost-priced objective as $\kappa_0\cdot\mathrm{range}(Y-\lambda C)$ with $C$ bounded by the cap. **Sections:** §7 (P22, P21, P23), §0.2 items 4 and 5, §0.4, §12 item 4, §10, §15 item 8.

### R22. The correction bundle — mandatory, applied wherever the result appears

Each keeps its number. Not optional polish; each is a reviewer finding.

**(a) §1 closing sentence.** Replace with: "and **nonparametric within-stratum** adjustment is available only once the treatment has been coarsened, because at the fine level no treatment level has positive probability within a history stratum, so the standardized mean is not estimable. **Model-based** adjustment does not require coarsening — which is why the fine level needs either a critic (D1) or a scalar feature (Ext-B) — and at the fine level the adjusted contrast is **identified but has effective sample size $n\,e^{-\Theta(m)}$ (T29)**." The numerical example ($+0.125$ average benefit, $-0.13$ marginal) checks exactly and stays.

**(b) T29 / §12 item 1 / §14 Route A.** "Not regularly estimable" is **withdrawn**. Under the document's own conditions $E[Y(a)]$ has the ordinary AIPW influence function with variance bounded by $E[1/g(a\mid X)]$, finite whenever $g>0$ a.s. and $E[1/g]<\infty$: it is **regularly estimable at $\sqrt n$ with an efficiency bound of order $e^{\Theta(m)}$** — a catastrophic constant, not an irregularity. Add $E[1/g(a\mid X)]=\infty$ as the separate checkable condition for genuine (Khan–Tamer) irregularity. Relabel the $T\rho$ object a **finite-sample variance band**. Fix §12 item 1's "never estimable" to "not estimable at any feasible $n$".

**(c) T9(v) / §15 item 1 — the OPEN flag closes.** Write $\varphi=V_1(H_1)-\psi+\sum_tW_{1:t}(V_{t+1}-Q_t)$; its projection onto the turn-$t$ treatment tangent space is $E[\varphi\mid H_t,K_t]-E[\varphi\mid H_t]$; the turn-$t$ residual has conditional mean zero given $(H_t,K_t)$, later residuals have conditional mean zero, and earlier terms plus $V_1$ are $H_t$-measurable, so the difference is identically 0. Hence $\varphi$ has zero component in $\oplus_tT_{A_t}$; removing that subspace (what knowing $e$ does) leaves $\varphi$ an influence function in the reduced tangent space, so $\varphi$ is the EIF in both models: **knowing $e$ does not lower the longitudinal bound for $V(\pi)$ at fixed $\pi$** (the Hahn 1998 analogue holds). Prove it in two lines and narrow §15 item 1 to MSM parameters indexed by $e$, $V(\pi^\star)$ under exceptional laws, and T30's $P$-dependent tilt. Keep the correct conclusion: knowing $e$ buys **exact unbiasedness and finite-sample validity, not asymptotic efficiency**.

**(d) P12 / §15 item 6 — reinstate the closed form.** Non-supermodularity of $\mathbf1\{v>w\}$ rules out the comonotone maximizer but **not** a closed form. Sharp bounds on $P(V>W)$ with fixed marginals are Makarov (1981) / Rüschendorf (1982), attained at explicitly constructible shuffle couplings: $\sup=1-\sup_t\{F_V(t)-F_W(t)\}^+$, $\inf=\sup_t\{F_W(t)-F_V(t)\}^+$ (up to one-sided limits). Both are already in §13(a), and T13 reduces the comparison to a **scalar** $u(Z)$, so the bound applies directly. Rewrite: "the extrema are not attained at the comonotone/antimonotone couplings, so the naive Fréchet–Hoeffding substitution fails; the sharp bounds are nonetheless closed-form via Makarov–Rüschendorf for a scalar comparison, and require an optimal-transport LP only for the multi-level, non-scalarizable comparison." Delete "closed-form sharp transport bounds for three-level lexicographic comparisons" from §15 item 6, keeping the vector-valued case.

**(e) P4 — four restrictions, all required.** (i) Opt-in **per generator**, conditional on that generator satisfying the D2 conditions (plain autoregressive sampling, sampling-time truncated distribution, fully recorded randomness) **and** A5's statelessness (R7); the **selector weight is the default**, the decision is pre-registered before outcomes are seen, and **both weights are reported**. (ii) $\rho^{\rm mar}$ is **undefined on stop turns** (no emitted message, no $q_{\texttt{STOP}}$): write $w_t=\pi(\texttt{STOP}\mid h)/e(\texttt{STOP}\mid h)$ on stop turns and $\big[(1-\pi(\texttt{STOP}))/(1-e(\texttt{STOP}))\big]\times\big[\sum_{k\ne\texttt{STOP}}\pi q_k/\sum_{k\ne\texttt{STOP}}e\,q_k\big]$ on continuation turns, and re-derive the Jensen and $1/\delta$ claims for that form. (iii) P4 and T9(iii) are **incompatible as an estimator**: $\rho^{\rm mar}_t$ is $\sigma(H_t,\tilde A_t)$-measurable while $\hat Q_t(H_t,K_t)$ is $K$-measurable, so the telescoping delivering T9(i) breaks and restoring it needs $E[V_{t+1}\mid H_t,\tilde A_t]$ — exactly the summation over text T9(iii) advertises as avoided. Restrict P4 to **E4 / the IPW forms** and state that **E1 must use the selector-level weight** to retain exact unbiasedness. (iv) State R7's zero-gain identity and the $m_G$-scoring-passes cost. The rule "marginalize over every recorded latent randomization whose density you can compute" is **withdrawn** as stated.

**(f) P18(a) — the stopped form.** Under an endogenous horizon $W_{1:t}$ and $H_t$ are undefined on $\{T<t\}$, so the naive identity flags false positives exactly where the paper cares. Replace with $E\big[W_{1:t}\mathbf1\{T\ge t\}g(H_t)\big]=E^\pi\big[\mathbf1\{T^\pi\ge t\}g(H_t)\big]$ (or the version stopped at $t\wedge T$), state which is computed, and compute the right-hand side from the same indicator.

**(g) T7 and P10 — the reach factor and the shared-rollout cross term.** (i) Insert $P(T\ge s)$: the turn-$s$ blip ESS is of order $n\delta P(T\ge s)/D$, **not** $n\delta/D$, and the omitted factor is smallest exactly at the turns of interest (P21: satisfied users stop). Require $\hat P(T\ge s)$ to be reported. (ii) In P10 write $\mathrm{Var}\approx\sum_tP(T\ge t)\big[E[W_{1:t}^2]\sigma^2_{Q,t}/m_t+E[W_{1:t-1}^2]\sigma^2_{V,t}/m'_t\big]+V_0$ with budget $\sum_t(c_0t+c_t)m_tP(T\ge t)\le B$. (iii) **Mandate disjoint rollout sets** for $\hat Q_t(H_t,K_t)$ and $\hat V_t(H_t)$, which makes the additive display exact and the allocations separable; with shared rollouts there is an omitted cross term of order $-2\pi_t(K_t\mid H_t)E[W_{1:t-1}W_{1:t}]\sigma^2_{Q,t}/m_t$ and the display is neither exact nor a bound. (iv) **"Spend the branching budget late" is withdrawn**: $\alpha_t=E[W_{1:t}^2]\sigma^2_{Q,t}$ need not grow — under shallow deviations $E[W_{1:t}^2]$ is flat for $t>d$ while $\sigma^2_{Q,t}$ typically shrinks late and $P(T\ge t)$ decays. Replace with: estimate $\alpha_t$, $c_t$ and $P(T\ge t)$ in the pilot and allocate by the formula; "spend late" holds only when the growth in $E[W_{1:t}^2]$ outruns the decay in $P(T\ge t)$ — a measurable condition, not a theorem.

**(h) T25(d) — code discharges only the receiver-side half.** Withholding $A_D$ from the receiver's context guarantees $A_D$ does not enter $M$ directly. The dismissibility condition — that $A_D$ affects $Y$ only through the continuation event — is a claim about the **user's behavioural kernel**, and with a simulated user $A_D$ enters that user's prompt, so an LLM conditioning on its whole context will in general alter both its stop head and its message content. Restate: interface construction discharges the receiver-side condition **by construction**; the remainder is a single named assumption — **A22b: $A_D$ does not affect the message distribution given continuation** — labelled assumed, with the available falsification (branch on $A_D$ at fixed $A_Y$ and test invariance of the next message's conditional distribution). Delete "in medicine the decomposition is hypothetical; here it is code", or restrict it explicitly to the receiver-side half. Same edit in §13(c).

**(i) T26 and §0.3.** T26(a)'s "no positivity assumption" is contradicted two lines later by T26(b); rewrite as "**positivity holds by construction on the expanded action set at every design-reached node, and fails precisely off-tree (T26(b))**". In §0.3, "$\Omega(K^T)$ rollouts … which is the formal reason a learned blip estimator is **mandatory** rather than convenient" is **withdrawn**: the bound is on leaf queries needed to **search** under a needle construction with no state abstraction, and a learned blip estimator does not evade it — it substitutes an **extrapolation assumption** for the query budget, which §5 and T7 already require to be labelled as an identifying assumption. Replace with: "exhaustive history-indexed search is infeasible, therefore structure must be imposed, and **every guarantee downstream is conditional on that structure**." Move T26(c) to a remark; it changes no design decision.

**(j) T30 / §13(b) item 3.** "The action-level text critic disappears" is **withdrawn** — the residual involves $\tilde Q_{t+1}(H_{t+1})$ and $H_{t+1}$ contains the realized message, so the critic is action-dependent. Restate as "**no integration of the critic over the action space is required: the critic is evaluated only at observed history–action pairs**", keeping the existing concession about the soft-optimal recursion as the limit of the claim.

**(k) §0.4 Ext-B price column.** Add: "$\sqrt n$ inference requires a **product rate on two text-history nuisances** (the conditional normalizer $Z_t$ and the tilted critic), unverifiable per §12.12, with **no known-propensity fallback**: if $\hat Z$ is inconsistent the estimator is inconsistent, $E[w_t\mid H_t]=Z_t/\hat Z_t\ne1$ so both the exact $P$-martingale property and the $E[w\mid H]=1$ check fail, and the Ville-type anytime-valid certificate of §15.3 is unavailable." State whether $Z_t$ is cross-fitted.

**(l) T28.** (i) Relabel term 1 "estimable **only under a stated smoothness/pooling model** for $U_t(\cdot\mid h)$" — real-user logs contain each text history once, so the per-history $L_1$ distance is not estimable at $h$ — and give the model and its diagnostic or demote it alongside the transport term. (ii) Split $\rho_t$ into $\rho^U_t$ (real-user law, only partially replayable) and $\rho^{\hat U}_t$ (simulator law, branchable), with separate estimability statuses. (iii) Display the exact identity and the bound as **two separate equations**, so the history-shift term's origin (the change of measure from $P^U$ to $P^{\hat U}$) is visible. (iv) Per P14b, restate term 3 as "estimable by **replaying logged human prefixes** into the harness under A13, up to replay fidelity and up to histories outside the logs' support; unestimable only for $\pi$-reachable real histories the logs never visit", and move the sensitivity parameter to that residual.

**(m) E2 with `STOP` in the treatment set.** `STOP` changes the **number of subsequent turns**, so the additive representation's index set depends on the treatments being blipped down. Fix the reference as a **continuation** regime defined to $\bar K$ (never `STOP`); state the convention $\gamma_s(H_s,\texttt{STOP}):=E[Y^{(\text{ref from }s)}\mid H_s]-\psi(H_s)$ (the full remaining-turn effect); write $U_{it}(\beta)=(Y_i-\lambda C_i)-\sum_{s\in\{t,\dots,\min(T_i,\bar K)\}}\gamma_s(\cdot)$ with an explicit `STOP` term; and re-check the conditional mean-zero property turn by turn. Add one sentence on inference under **active isotonic constraints** (boundary / cube-root-type asymptotics): report the unconstrained fit alongside, or use a projection-based interval.

**(n) P5 small fixes.** The obstruction to factoring is $\mathrm{Cov}(w_t^2,\Gamma_{t+1}(H_{t+1})\mid H_t)$, **not** $\mathrm{Cov}(w_t^2,\chi^2_{t+1})$ — $\Gamma_{t+1}$ is the forward second-moment factor and the stated reason must match the displayed recursion. State the convention $\Gamma_{t+1}:=1$ on $\{K_t=\texttt{STOP}\}$, and write the tilted display as $E_{\tilde P}\big[\prod_{t=1}^{\tilde T}(1+\chi_t^2(H_t))\big]$ with $\tilde T$ the horizon under $\tilde P$, noting that $\tilde\pi\propto\pi^2/e$ also tilts the stopping probability. In T29 write $\delta^{-d}$ (a product over $t$), not $\delta^{-1}$.

**(o) P15(d) PPI variance.** The display treats the two terms as independent, which holds only if $V$ is drawn separately from the $n$ units. Under §16's arm-by-arm validation $V\subset n$, so either sample $V$ **disjointly** and say so, or add the covariance term and the $(1-|V|/n)$ finite-population factor. Cross-fitting $w_i$ removes nuisance-induced dependence but not the overlap.

**(p) Null-blip mass — add to §12 as a numbered limitation.** "The exceptional set is not a corner: the measured task mass with hidden-test success below 0.05 is **0.156** (blip exactly 0 for every class) and above 0.95 is **0.334**, with only **0.406** informative, so inference on $V(\pi^\star)$ is non-regular over a **large fraction** of the population and any marginal blip is attenuated by the null mass. The primary estimand is therefore defined **conditional on the first attempt failing**, with the already-correct stratum analysed separately for **harm** (degradation 0.162 [0.105, 0.242]). The states where a learned critic can beat the trivial rule 'stop iff visible pass' are essentially the false-pass states, whose rate is **unmeasured** and assumed at 0.10–0.25, which is why power swings from 0.35 to 0.91 across that assumption." Make the non-regularity remedy ($m$-out-of-$n$ bootstrap or adaptive intervals) a **requirement in §16**, not a suggestion.

**(q) §0.2 item 1.** "The only route that removes the central obstacle without an untestable assumption" is **withdrawn**. Replace with: "it removes the exclusion restriction A19 and the positivity obstacle **by construction**; the remaining untestable assumptions are **A11** (outcome validity), **A12** (leakage-scorer dynamic range), **A1/A2** (the hygiene channels of §12.13, now graded A per R12), and **A22/A22b** where humans or interface splits appear."

**(r) P21 / §15.8.** State P21 as "**under A7 for the continuation coordinate**, the sharp set has width $\kappa_0$", and add that the same behavioural mechanism creating the support failure ("satisfied users stop") also threatens A7 whenever the user's perceived quality exceeds what $H_t$ records — so $\kappa_0$ is a **lower bound** on the true ambiguity and no computation of it will reveal the excess. Cross-reference §15.8.

---

## PART III — GLOBAL EDITORIAL RULES

### III.1 Forbidden strings — none may survive anywhere

| forbidden | replace with | rule |
|---|---|---|
| `δ ≥ 0.25` | `δ = 1/8 = 0.125` | R1 |
| `5–6 effective classes` | `8 randomized non-STOP classes (m = 9 with STOP)` | R1 |
| `M = 16`, `E[W²] ≤ 16` | `M = 8 (d=1) / 64 (d=2)` | R1 |
| `5×10⁴ conversations`, `1.2×10⁴` | the R4 tables | R4 |
| `roughly what a stratified A/B test costs` | delete; the honest multiple is 50–120× | R4 |
| `conversations` as an inference unit | `task clusters`, with $n_{\rm clusters}$ stated | R9 |
| `T = 5` | `T_max = 3 turns, D = 2 decision points` | R1/R2 |
| `\|Π\| = 100` | the pre-registered candidate count declared in §16 | R8 |
| `n_b = 1`, `n_b ≥ 8` | `n_b = 3 (frozen), n_b* ≈ 7` | R15 |
| unqualified `known` stop-arm value | T8a / T8b with the history named | R3 |
| `the endogenous horizon costs nothing extra` | delete | R3 |
| `no medical analogue` | delete | R3 |
| `certified strict improvement over the logging policy` | delete; T20 withdrawn | R4 |
| `natural/logging policy` | `the design's own randomizer e` | R4 |
| `T8 and T9 apply verbatim` | the R6 replacement | R6 |
| `exactly unbiased for any outcome model whatsoever` (unqualified) | the R14 restatement | R14 |
| `zero bias risk` | the R14 qualification | R14 |
| `no post-treatment conditioning` | delete | R5 |
| `Leakage is a pre-treatment design coordinate` | the R5 replacement | R5 |
| `bin it; stratify randomization on the bin` | delete | R5 |
| `not regularly estimable` | `regularly estimable with an e^{Θ(m)} efficiency bound` | R22(b) |
| `0.745` | delete | R21 |
| `any implementable stopping rule` (P22 device) | `any rule that never continues past the natural horizon` | R21 |
| `mandatory rather than convenient` | the R22(i) replacement | R22(i) |
| `the only route that removes the central obstacle without an untestable assumption` | the R22(q) replacement | R22(q) |
| `spend the branching budget late` | the R22(g)(iv) replacement | R22(g) |
| `A run that does not report (a)–(d) is not an experiment.` | the R18 closing paragraph | R18 |
| `vacuous in D1` for A18 | A18a required / A18b vacuous | R14 |
| `in medicine the decomposition is hypothetical; here it is code` | receiver-side half only | R22(h) |
| `the action-level text critic disappears` | `no integration over the action space is required` | R22(j) |
| `model-version epoch` as a clustering level | delete; canary tripwire | R12 |
| `verify caching changes latency and not tokens` | canary battery + out-of-order replay | R12 |
| `override depth d ≤ 2` as a chosen knob | the R2 entitlement table | R2 |
| `π* = argmax over Π_cp` as the reported object | `π̂`, best member of the pre-registered Π | R8 |
| unqualified `the optimal regime read off the argmax` | add the R8 φ-sufficiency caveat | R8 |
| `λ is a budget price, not a hyperparameter` | the R13 replacement | R13 |
| `marginalize over every recorded latent randomization whose density you can compute` | the R22(e) restriction | R22(e) |

### III.2 Rules that bind every section

1. **Numbering is frozen.** A1–A22, T/P/E numbers, §13(b) items and ladder rows keep their identifiers. New material attaches as a lettered sub-part of an existing number (A18a/A18b, A19b, A22b, T8a/T8b, E0) — never as a renumbering. E0 is additive.
2. **Withdrawal is explicit and in place**, using the Part-0 template. If you weaken a theorem, say so where it stood, in the reviewer's terms.
3. **No new unproven claims.** Prefer a smaller true statement to a larger shaky one. If a repair would need a result the document does not have, concede and say what is missing.
4. **Every quantity is in Part 0 or derived from it with the arithmetic shown.** Flag missing numbers; do not invent them.
5. **Every depth-dependent claim names its entitlement class** ($\Pi_0$, $\Pi_1$, $\Pi_2$) — R2.
6. **Every "known" names its history** ($H_t^A$ or $H_t^O=\varphi_t(H_t)$) — R3.
7. **Every sample-size or precision claim is in clusters**, states $n_{\rm clusters}$, and is checked against 176 and ≈230 — R9.
8. **Every prescription is checked against the 20,000-call / 9.3-hour ceiling**, with the call count shown; over-ceiling prescriptions are cut or marked unaffordable and not required.
9. **Do not claim novelty for anything in R11's list.** Cite it.
10. **Programmatic vs judge outcome is stated per result**, because T8a, A11(d) and all of §8 turn on it — R3, R19.

---

## PART IV — PER-SECTION CHANGE MANIFEST

| file | items that bind it |
|---|---|
| `02_0_verdict_and_the_choice_of_primary_rout.md` | R1, R2, R3, R4, R6, **R9 (reorder §0.1)**, R10, R11, R17, R21 (item 4), R22(i)(q); verdict paragraph rewritten under R2/R3/R4/R8/R14 |
| `03_1_setup_and_notation.md` | **R3 (insert the two histories)**, **R8 (define $\Pi_{\rm cp}$, $\Pi_0/\Pi_1/\Pi_2$, $\hat\pi$, A19b)**, R9 (Units), R10, R22(a) |
| `04_2_assumptions_a1_a22.md` | **R1 (A6, A4)**, **R3 (A11)**, **R5 (A12)**, **R7 (A5)**, **R14 (A18a/A18b)**, R12 (A1, A2), R13 (A10), R6 (A17), R22(h) (A22b); the two "notes worth making loudly" updated — A19's absence still holds, but add A19b as a *named non-assumption* and state that A21 plus T8a is what the P22 device rests on |
| `05_3_identification.md` | **R7 (T3 proof, P2)**, **R22(e) (P4)**, R5 (the $(g,\lambda)$ action space enters T3 here) |
| `06_4_estimability_positivity_weights_horizo.md` | **R1 (P5 bounded case, P6, tilt budget)**, **R2 (override depth)**, **R3 (T8 → T8a/T8b)**, R8 (T8 Bellman caveat), R13 (well-posedness), R22(g)(i) (T7 reach factor), R22(n), R9 |
| `07_5_estimators_we_will_implement.md` | **R9 (add E0)**, **R14 (T9(i),(ii); E1)**, **R15 (P5b)**, R12 (cross-fitting, drift), R22(c) (T9(v) closed), R22(e) (E1 selector weight), R22(g)(ii)(iii)(iv) (P10), R22(m) (E2), R13, R8 (State representation), R16 (P11) |
| `08_6_policy_learning_and_the_improvement_ce.md` | **R4 (T20 wholesale)**, **R17 (T19)**, R2 (history-shift), R8 ($|\Pi|$), R9 (E0 as replacement) |
| `09_7_endogenous_horizon_and_prioritized_out.md` | **R6 (T13/T14, frozen $G_0$; demote to secondary)**, **R21 (P22, P21, P23)**, R22(d) (P12), R22(h) (T25(d)), R13, R3 (P23 → $\mathcal F_t^O$), R22(r) |
| `10_8_measurement_threats.md` | **R5 (T16 wholesale; length/position)**, **R19 (replace the horizon test; compress §8)**, R20 (P24(ii) $\sigma$), R22(o) (P15(d)) |
| `11_9_falsification_hygiene_and_the_oracle.md` | **R18 (P18(d) → d1/d2; closing sentence)**, **R16 (T27 → ranking device)**, R22(f) (P18(a)), R22(i) (T26), R22(l) (T28), R12 (P18(c), deep-slice hygiene), R15 |
| `12_10_the_design_ladder.md` | **R1 (A6 row)**, **R2 (D1 row bounds)**, R4 (delete "certified"; add the evaluated/diagnostic split), R7 (D2 row, chain-of-thought entry), R12 (A1/A2 rows), R14 (A18 row), R21 (Ext-E, Real-humans rows), R8 ($\hat\pi$ not $\pi^\star$) |
| `13_11_extensions_stated_precisely.md` | R22(j) (T30), R22(k) (Ext-B price), R22(b) (T29), R17 (free-form generator outside all guarantees) |
| `14_12_scope_and_limitations.md` | **R4 (certificate vacuity as a numbered limitation)**, **R22(p) (null-blip mass)**, R10, R12 (items 9, 13), R17, R20 (items 7, 10), R22(b) (item 1), R3 (item 7), R21 (item 4) |
| `15_13_what_is_actually_new_here.md` | **R11 (cite; demote 1/2/9; withdraw 12; lead with the design claim)**, R5 (§13(c) leakage bullet), R22(h) (separable-effects bullet), R10, R2, R4 |
| `16_14_errata_reviewer_findings_and_their_re.md` | one line per repair, keyed by R-number, in the existing route format; mark R4, R6, R19, R22(b)(d)(e)(i)(j) as **withdrawals** and R22(c)(d) as **OPEN flags closed** |
| `17_15_open_problems.md` | **R22(c) (item 1 closed and narrowed)**, **R22(d) (item 6's scalar case closed)**, R6 (add $G_0$ to item 6), R20 (item 7), R22(r) (item 8), R2 (item 4: note $d=2$ is full depth here) |
| `18_16_what_an_experiment_must_do.md` | **R1 (item 3)**, **R15 (item 4)**, **R19 (item 5)**, **R3 (item 6 → the $\varphi$-exclusion assertion)**, **R5 (items 2, 7)**, **R7 (item 1 sub-items a–d)**, R12 (item 12), R13 (item 13), R4 (item 14: four denominators), R18 (items 10, 11), R20 (item 3: contamination stratifier), R22(p), R8 (declare $|\Pi|$) |
| `00_header.md`, `01_a_unified_theory_document_design_based_i.md` | Part III only; if the title or abstract asserts a certificate, the optimal regime, or novelty in R11's list, repair it |

---

## PART V — WITHDRAWN-RESULTS REGISTER

Numbers retained, marked withdrawn in place, reason in the reviewer's terms.

1. **T20** — withdrawn as a deliverable, retained as a scope statement: vacuous at the honest inference unit (smallest certifiable gap 0.542 vs 0.046 available), impossible for $M\ge8$, 20–400× over budget, certified against a baseline manufacturable by adding placebo arms.
2. **§13(b) item 12** (the certificate as a contribution) — withdrawn with T20.
3. **T8's unqualified "known stop-arm value"**, **§0.2 item 5's "costs nothing extra"**, **"no medical analogue"** — withdrawn; T8 split into T8a/T8b.
4. **T16's "no post-treatment conditioning"** and "stratify randomization on the [leakage] bin" — withdrawn; leakage rebuilt into the library.
5. **§13(c)'s "Leakage is a pre-treatment design coordinate, not a mediator"** — withdrawn.
6. **T13/T14's "T8 and T9 apply verbatim"** — withdrawn as stated; restored only under the frozen $G_0$, with reference-dependence priced.
7. **T13/T14 as a primary objective** — demoted to a secondary reporting device (a $2\times3$ table with majority tie mass on this outcome).
8. **P22's unrestricted reporting device** and **the 0.745 prophet constant** — withdrawn.
9. **P5b's $n_b=1$ conclusion** and **§16's $n_b\ge8$** — both withdrawn; interior optimum $n_b^\star\approx7$, frozen at 3 under the call ceiling.
10. **P10's "spend the branching budget late"** — withdrawn; unverified monotonicity, and the additive variance display is not a bound under shared rollouts.
11. **P18(d)'s negative-control-must-return-zero** — withdrawn; no valid null in the document's own framework. Replaced by a guaranteed null and a guaranteed positive.
12. **§9's closing sentence** — withdrawn as inverted; rewritten with the power of each item stated.
13. **The horizon-invariance calibration test** (§8, §16 item 5) — withdrawn; exactly zero power under P15(f).
14. **T29's "not regularly estimable"** and **§12 item 1's "never estimable"** — withdrawn; replaced by an $e^{\Theta(m)}$ efficiency bound, with $E[1/g]=\infty$ as the separate irregularity condition.
15. **§15 item 1** (efficiency bound with known $e$) — withdrawn as OPEN; resolved by tangent-space orthogonality and narrowed.
16. **§15 item 6's "closed-form sharp transport bounds for lexicographic comparisons"** — partially withdrawn; the scalar case is Makarov–Rüschendorf, and P12's "no closed form in general" is corrected.
17. **§0.2 item 1's "the only route … without an untestable assumption"** — withdrawn.
18. **§0.2 item 4's unrestricted shippability / target-trial claim** — withdrawn for message-generator arms; restricted to product-side coordinates by name.
19. **P4's universal rule** — withdrawn; opt-in per generator, undefined on stop turns, incompatible with E1's exactness, and an identity with zero gain in the frozen template design.
20. **A18's "vacuous in D1"** — withdrawn; A18a (sample splitting) is required in every design.
21. **T9(i)'s "for any $\hat Q$ whatsoever"** as applied to TMLE, clipped IPW and self-normalized forms — withdrawn; restricted to the cross-fitted one-step/AIPW form under A18a and internal consistency.
22. **T26(a)'s "no positivity assumption"** — withdrawn; relocated to the expanded action set at design-reached nodes.
23. **§0.3's "a learned blip estimator is mandatory"** — withdrawn; structure is an assumption, not a theorem.
24. **T30's "the action-level text critic disappears"** — withdrawn; restated as no integration over the action space.
25. **T25(d)'s "in medicine hypothetical, here code"** — withdrawn for the user-side half; the remainder is the named behavioural assumption A22b.
26. **A1's "BC with hygiene"** — withdrawn; graded **A** with a canary tripwire and a drift diagnostic. **"Verify caching changes latency and not tokens"** withdrawn as powerless.
27. **§5's clustering by model-version epoch** and "balance the drift" — withdrawn; tripwire and discard, cluster by task family only.
28. **§12 item 10's attenuation-only reading of contamination** — withdrawn; contamination **inflates** stop-arm advantages and cost-priced gaps.
29. **§13(b) items 1, 2 and 9** — demoted to accounting identities (not withdrawn, but no longer claimed as contributions).
30. **T19's $L_1$ bound as a headline guarantee** — retained as a true statement, withdrawn as a guarantee: vacuous at $O(0.1)$ critic precision against 0.046 of headroom.