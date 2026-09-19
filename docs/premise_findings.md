# Premise checks P1–P3 — what the project's central claim survives

**Status: exploratory, not pre-registered.** These are hand-built tabular
simulations with known laws, run before the confirmatory simulation study (E0) is
designed. Their purpose is to test the *logic* of the project's central claim
before any model is called. They are **not** evidence about real LLMs, the
data-generating processes were chosen by the author, replicate counts are small,
and nothing here should be reported as a result about LLM interaction. They are
reported because two of them came out against the claim as originally stated.

Scripts: `experiments/premise/premise_check{,2,3}.py`.
Outputs: `results/premise/`.

## The claim as originally stated

> Prior output quality is a time-varying confounder affected by prior treatment,
> so a naive reward model fit on interaction logs learns the wrong effect of
> feedback types, and a causal critic is needed instead.

Split into four testable pieces, with what happened to each.

| # | Claim | Verdict |
|---|---|---|
| C1 | An **unadjusted** comparison of intervention classes reverses the true ordering | **Confirmed, large** |
| C2 | Conditioning on the intermediate state when valuing the **first** intervention destroys the effect | **Confirmed, large** |
| C3 | A correlational critic conditioning on the **full observed state** makes worse **decisions** | **Refuted as stated** |
| C4 | IPW, g-computation and DR recover the truth with covering intervals | **Confirmed** |

## C1 — unadjusted comparisons invert the ranking (confirmed)

P1, `n = 3000` per replicate, 40 replicates. Behaviour policy: a wrong answer
provokes "locate the error" (L), a right answer gets a perfunctory "try again"
(U).

| quantity | value |
|---|---|
| observed `E[Y | A₂ = U]` | 0.813 |
| observed `E[Y | A₂ = V]` | 0.648 |
| observed `E[Y | A₂ = L]` | 0.468 |
| **true** blip of L over U in the wrong state (easy / hard) | **+0.30 / +0.20** |
| replicates in which the marginal comparison got the L-vs-U sign right | **0 / 40** |

P2 makes it starker. There, "restructure the answer" (S) is the optimal first
intervention from the far-wrong state, and in the logged condition it had the
**lowest** observed mean outcome of all four classes — 0.186, against 0.637 for a
perfunctory retry. Under sequential randomization the same comparison on the same
law ranks the classes correctly (L 0.471 highest, S 0.310).

This is the robust finding, and it is a claim about **how logs must not be read**.
It is also the claim most of the multi-turn LLM literature is exposed to, since
turn-level feedback types are routinely compared descriptively.

## C2 — conditioning on the intermediate state destroys the first-turn effect (confirmed)

The intermediate state is a *mediator* of the first intervention as well as a
*confounder* of the second, so "adjust for everything observed" is not a safe
default.

| quantity | value |
|---|---|
| true turn-1 blip of L over U from the wrong state, optimal continuation (easy / hard) | +0.156 / +0.132 |
| `E[Y | X₂, A₁]` averaged over X₂, by A₁: U / L / V | 0.658 / 0.661 / 0.663 |

A true effect of +0.16 is reported as +0.005.

## C3 — refuted as stated: a state-conditioned critic's *decisions* were barely harmed

This is the finding that changes the project.

In P1 a correlational critic — fit `Ê[Y | state, difficulty, action]` on the
logged data, act greedily — recovered the **exact optimal regime in 39 of 40
replicates**, mean regret 0.0010 against an optimum of 0.751. With a fully
observed, low-dimensional state, adjustment is sufficient and there is no bias
left for causal machinery to remove.

P2 added a latent feature (the error is subtle) that both shifts outcomes and
drives the user's choice, on the hypothesis that an unobservable would restore the
bias. It did not, at the decision level:

| critic | regret, logged | regret, randomized |
|---|---|---|
| correlational, state-conditioned | 0.0126 | 0.0148 |
| Q-learning, same conditioning set | 0.0071 | 0.0043 |

P3 swept the coupling γ between the user's choice and the latent error type, over
a law in which the *best* intervention flips with that latent type — the structure
most hostile to a state-conditioned critic. Logged-minus-randomized regret gap for
the correlational critic reached at most **0.030**, and known-propensity IPW on
the same conditioning set repaired it only partly and non-monotonically
(γ = 0.25: regret 0.046 → 0.033; γ = 0.5: 0.028 → 0.028; γ = 0.75: 0.017 → 0.019).

## What the dominant decision-level error actually was

In every condition of P2 and P3, the critic that looked **ahead** beat the critic
that did not, and by more than randomization-versus-logging moved anything.

In P3 the optimal state-only regime is *restructure first, then locate*
(`t1 = S,S,V`; `t2 = L,L,V`), value 0.659. But the population-average chance of
being correct at the **next** step from the far-wrong state is higher for L
(0.2625) than for S (0.204). Restructuring is the right first move precisely
because it is *not* the best immediate move: it puts the answer in the
"wrong-but-close" state, from which locating the error repairs it with probability
0.67. A critic scoring immediate improvement therefore picks L and loses, and it
loses **under randomization too** — this is not a confounding failure at all.

So, on the evidence so far, the value of the dynamic-treatment-regime framing here
is mostly in **sequential credit assignment and horizon-aware valuation**, plus
**a design whose assignment probabilities are known**; and the
confounding-adjustment machinery matters chiefly for **reporting effects**, which
is a different contribution from **choosing actions**.

## C4 — the estimators are correct (confirmed)

P1, value of the true optimal regime (truth 0.75098), 40 replicates of n = 3000:

| estimator | mean | bias | sd | 95% coverage |
|---|---|---|---|---|
| per-decision IPW (Hájek, known propensities) | 0.7475 | −0.0034 | 0.0233 | — |
| iterated-Q g-computation | 0.7513 | +0.0003 | 0.0112 | — |
| cross-fitted doubly robust | 0.7503 | −0.0007 | 0.0197 | 0.90 |

Coverage 0.90 over 40 replicates has a Monte Carlo standard error of about 0.047,
so it is not distinguishable from nominal; E0 must re-check it with enough
replicates to say anything.

## Consequences for the experimental program

1. **Reprioritize.** The sequentially randomized design and the horizon-aware
   critic move to the front; "causal correction of a confounded log improves
   decisions" drops to a secondary, scoped claim.
2. **Split the contribution in two.** Effect *estimation* from logs (where the
   failure is dramatic and robust) is a different deliverable from action
   *selection* (where it is small). Do not let one borrow the other's evidence.
3. **The headline comparison must isolate lookahead from adjustment**, with a
   per-turn non-myopic correlational critic as a baseline. Otherwise a win is
   attributed to causal inference when it came from looking one step further.
4. **E0 must include conditions where the causal estimators lose**, and must
   report the boundary in γ and in effect-modification strength at which
   adjustment starts to change decisions, rather than exhibiting one favourable
   cell.
5. **A negative result is publishable here** and should be pre-specified as such:
   "adjusting a confounded interaction log changes reported effects by a large
   margin and decisions by a small one" is a useful, citable finding.

## Limitations

Tabular states, two decision points, hand-chosen transition laws, 15–40
replicates, one latent binary confounder, no text, no receiver model, no cost
outcome, no stopping action. The C3 refutation is a refutation *of the claim as
stated in general terms*; it does not prove that no realistic LLM setting exhibits
decision-level confounding bias. The correlational critic in P3 pools turns, which
conflates myopia with turn-structure error; E0 must separate them.
