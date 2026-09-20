# Positioning — what this project can honestly claim

> **Historical snapshot; conclusions require the 2026-09-20 corrections.** Read [continuation report](continuation_report_20260920.md), [theory reconciliation](theory_reconciliation_20260920.md), [experiment audit](experiment_recheck_20260920.md), and [literature recheck](literature_recheck_20260920.md) before using this document. Earlier universal impossibility, optimality, matched-cost kill, and feature-no-signal claims are superseded. Original text remains for provenance.

Written by the experiments workstream, 2026-09-19, after three independent lines of
work converged on the same answer. The theory workstream owns the final framing;
this is the evidence it should frame against.

## Three lines, one conclusion

**1. The premise checks** (`docs/premise_findings.md`). Unadjusted comparisons of
intervention classes on logged data invert the true ordering — dramatically, 0/40
replicates recovering the sign. But a critic conditioning on the full observed state
recovered the *exact optimal regime* 39/40 times, and three attempts to break that
with unmeasured confounding moved regret by at most 0.030. What did move decisions
was the **horizon**: in one law the optimal first intervention is the one with the
*worse* immediate success probability, and a myopic critic loses there even under
randomization, where there is nothing to confound.

**2. The measured audits** (`docs/audits.md`), from a sibling project's completed
4,488-episode run on the identical task pool, at zero GPU cost. Iterating repairs
23.9% of failures [21.0, 27.0] but **destroys 16.2% of already-correct answers**
[10.5, 24.2], and a self-check-based stopping rule stopped on **50.4% of all
failures**. Holding feedback content completely fixed, oracle stopping decisions
alone are worth **+4.6 percentage points** of final success.

**3. The literature audit** (`docs/literature_audit.md`). An agent playing hostile
area chair was asked to reject the brief's claim and then name the one reframing
that would survive its own attack. Without seeing either of the above, it landed on:
coarsen the action to a small finite move set (and treat the coarsening as the
technical content, not a compromise); **randomize it prospectively and log the
propensities**; use the existing orthogonal estimators rather than re-deriving them;
and use the estimated effects for one narrow purpose — **deciding when to
intervene**, not generating the next string.

Three methods, three directions, same paper. That is the strongest signal available
this early, and it is worth more than any of the three alone.

## What we must concede

The audit is unambiguous that the following are not ours, and several are papers the
brief never mentions:

| Concede | To |
|---|---|
| "prompt / instruction as a treatment" as a framing | Wang et al., **AAAI-25** (peer-reviewed, verbatim in the abstract); Frauen et al., **KDD 2026**; CPO (arXiv:2602.01711) |
| DTR / Q-learning over a natural-language action space | Zhang, Wang & Dhillon, **arXiv:2502.17538** — including embedding-space gradient ascent and decoding back to text |
| longitudinal causal inference over sequences of text features | Nakamura & Imai, **arXiv:2605.07834** (marginal structural model, per-feature deconfounder, valid semiparametric CIs) |
| single-period identification for text-valued treatments | Imai & Nakamura, **arXiv:2410.00903** |
| per-context off-policy prompt policy learning | Kiyohara, Cao, Saito & Joachims, **arXiv:2504.02646** |
| estimands for causal effects in AI-mediated conversation | **arXiv:2607.03597** — already plants the flag on our vocabulary |
| user-side text as a time-varying treatment in human–LM collaboration | CausalCollab, **arXiv:2404.00207** (same group as 2502.17538) |
| neural SNMM / blip estimation | DeepBlip, **arXiv:2511.14545** (ICML 2026) — extend, do not re-derive |
| doubly robust orthogonal Q-learning | DRQ-learner, **arXiv:2509.26429** (ICLR 2026) |
| a learned, cost-penalized stop rule for interaction | arXiv:2512.04068, arXiv:2510.25441 |
| auditing which turns or edits mattered | arXiv:2605.26655, arXiv:2609.05882 |

So "we are the first to formulate multi-turn prompting as a DTR" is false, and
"causal critic instead of a correlational reward model" is CPO's published rhetorical
position, not ours.

## What survives, and why it is real

**The design.** Nobody has prospectively sequentially randomized an intervention
inside a multi-turn LLM interaction and logged the propensities. The audit checked
this as a direct question and found it "a genuine and currently clean gap as of
2026-09-19". The closest real attempt (arXiv:2510.17173) had to *reconstruct*
propensities post hoc with calibrated classifiers on 7 users and concedes the
calibration is only moderate; another (arXiv:2606.05558) calls exact propensities
"privileged and unavailable in deployment"; CollabLLM, FACA, ROSA and T-POP are all
on-policy with no propensities at all.

**The coarsening as identification, stated as such.** Point-treatment positivity is
undefined for strings: LMTP's support-preservation condition has no meaning when the
action is a string, and there is no generalized propensity over text. Rather than
pretend otherwise, define the action as a small analyst-specified move set, make the
propensity well defined *by construction*, recover a checkable positivity condition,
give the blip a non-arbitrary reference level (no-move), **and state plainly that
effects of the underlying string are not identified.** The audit confirms nobody has
extended modified treatment policies to a text action space, and that the one
infinite-dimensional extension (arXiv:2606.27518) works only through linear basis
structure that text lacks.

**A validation asset no deployment paper has.** Our receiver is frozen and
resettable and our outcome is programmatic (hidden tests), so from a saved state we
can execute *every* arm and obtain Monte Carlo ground truth for the conditional blip
effects. Almost no applied causal paper can grade its own estimator against truth.
This is what our lack of real users buys us, and it should be claimed as a design
choice rather than apologised for.

**The boundary results, reported as results.** Where adjustment changes reported
effects a lot and decisions little; where horizon dominates confounding; repair
versus degradation; and the cost of a self-check stopping rule. These are negative
and quantitative, and the field currently reads turn-level feedback comparisons
straight off logs, which the premise checks show is invalid.

## The claim we should try to earn

> A prospectively and sequentially randomized, propensity-logged multi-round
> interaction experiment with a programmatically verifiable outcome, in which
> turn-level causal effects of a coarsened set of language interventions are
> identified by construction, validated against branch-sampled ground truth, and
> used for the one decision the evidence says they can pay for — **when to intervene
> and when to stop** — evaluated against budget-matched controls including a
> zero-information feedback arm.

Scope stated up front: the intervener is automated, so the effects are effects of
interventions *deliverable by an automated intervener*, which is the deployment
target for an agent skill. Transfer to human users is not claimed.

## Hard constraints the audit imposes on the design

1. **Every round must carry external evidence.** Five independent results close the
   door on model self-critique with no outside signal (arXiv:2310.01798 shows
   monotone degradation, GPT-4 on GSM8K 95.5 → 91.5 → 89.0; TACL 2024
   arXiv:2406.01297 finds no successful case with prompted-LLM feedback outside
   exceptionally suited tasks; arXiv:2311.08516 locates the failure at *detection*,
   not repair). Our interventions must be grounded in execution output, and any arm
   that is not must be named as the control it is.
2. **A zero-information feedback arm is mandatory**, not optional: UFO
   (arXiv:2507.14295) shows a bare "try again" elicits multi-turn gains, so any
   content effect must be measured against it.
3. **Budget-matched self-consistency is the comparator that matters.** It converts
   the same extra compute into quality with no multi-turn machinery at all.
4. **Do not do token-level importance weighting.** arXiv:2606.05558 implements it
   with exact per-token log-probs and reports that IS/WIS/DR still lose to a learned
   world model, because ratios over horizon × vocabulary-scale action spaces
   degenerate. Aggregate at turn level (arXiv:2511.20718) or use factorized per-turn
   decision heads (arXiv:2510.17173).
5. **Do not adjust on an embedding that contains the treatment.** arXiv:2602.15730
   characterizes that bias and fixes it by covariate residualization; our own
   nuisances would otherwise inherit exactly the defect we cite against CPO.
6. **Keep the horizon short.** DeepBlip's error propagation grows like
   `(1+C)^(tau-k)`, i.e. exponentially backwards along the horizon under weak
   overlap — the regime a long conversation lives in.
7. **If a simulated intervener is used, it is a named nuisance parameter**, with
   sensitivity across simulator choices. arXiv:2601.17087 reports agent success
   swinging up to 9 points on simulator identity alone; arXiv:2603.11245 (451
   humans, 31 simulators) finds simulators uniformly cooperative, never realistically
   frustrated, and that bigger models are not better simulators.
8. **Do not build a new benchmark.** tau-bench, tau²-Bench, MT-Bench-101 and
   MultiChallenge cover the space; PRISM (arXiv:2404.16019) is the only public log
   with the per-person covariate/action/rating structure a DTR needs.
9. **Re-run the negative search before submission.** "No such paper exists" is
   load-bearing for the design claim and was last checked 2026-09-19.
