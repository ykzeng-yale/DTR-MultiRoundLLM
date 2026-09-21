# Research-completion rubric and historical checkpoints

> Historical work-planning scores are preserved after the current reporting contract below. The [current scientific judgment](scientific_judgment_20260920.md) controls advancement: the original prompt-choice benefit is untested and the project is not submission-ready. Additional proofs, files or simulations do not establish practical utility or raise a scientific probability of success.

`AGENTS.md` requires every user-facing progress summary and every scheduled repo
update to state the estimated readiness of the **full project** for a paper
submission, its change since the previous checkpoint, and the largest remaining
milestones. This file fixes the rubric so the number is comparable across
checkpoints rather than re-invented each time.

It is a **planning estimate of work completed against work required**. It is not an
acceptance probability, not a quality judgement, and not a time estimate.

## Current reporting contract — 21 September 2026, 00:25 UTC

The owner requested a percentage after **every** hourly check, including unchanged
checks. The current estimate is **49% milestone completion**, with **0 percentage
points of newly earned credit this hour**. This is the first checkpoint in the
resumed hourly percentage series. Applying the rubric below retrospectively to the
previous inspected head `5c6ef13` also gives 49%; that baseline reconstruction is
explicit, not a claim that 49% was reported last hour. The historical 48% checkpoint
used different credit judgments and must not be described as a one-point gain in
this hour. Its eight component weights are retained unchanged.

The number is a subjective planning estimate, rounded to the nearest whole
percentage point, not a measured fraction of scientific truth, acceptance chance,
time remaining or submission readiness. Completion credit requires concrete
reviewed artifacts or evidence. A well-executed negative trial can earn full credit;
a favorable unvalidated result cannot. Proof/test counts and GitHub integration do
not automatically increase a component. Reported-only empirical findings earn at
most half credit until independently checked. Lost validity can decrease credit.

| Component | Fixed weight | Current component completion | Contribution | Evidence earning credit; what remains |
|---|---:|---:|---:|---|
| Positioning and literature | 10% | 80% | 8 points | Primary-source correction audit exists; reconcile broader novelty/claim ledger and final bibliography. |
| Theory and proofs | 20% | 80% | 16 points | Scoped longitudinal/landmark results, independent reviews and exact checks; integrate the remaining broad-draft claims and final assumption-to-result audit. |
| Experiment and measurement design | 15% | 60% | 9 points | Exact arms, curation and versioned public/private proposals; no valid receiver/evaluator/family/assignment release freeze yet. |
| Implemented measurement and collection | 10% | 60% | 6 points | Collector, analyzer, private grader and provenance guards tested; containment, reference/control execution and receiver validation remain open. |
| Known-truth statistical validation | 10% | 60% | 6 points | Corrected fitted-estimator diagnostics and prespecified personalization simulation; adequate-history matched baselines, final MC precision and consolidated validation remain open. |
| Fresh supported-prompt experiment | 15% | 0% | 0 points | No validated fresh landmark prompt collection. Historical routing/reused-bank diagnostics earn no credit in this specifically fresh-data component. |
| Independent policy validation | 10% | 0% | 0 points | No frozen public-history rule/comparator evaluated on untouched root/family information. Fixed-bank exploratory selection earns no completion credit here. |
| Manuscript and reproducibility integration | 10% | 40% | 4 points | Theory draft, methods supplement and reproducible audit scripts exist; integrated current manuscript, empirical figures, final reproduction and claim audit remain open. |
| **Total** | **100%** | | **49 points** | **Not submission-ready; personalized-prompt efficacy unestablished.** |

The last five columns of evidence are judgments, not automatically generated
scores. Keep these eight weights and component meanings fixed for subsequent
updates. A change must identify the component, specific newly completed or
invalidated milestone, old/new credit and weighted difference. Do not reward
repeated checks or additional documentation with automatic increments. If scope
changes, publish old and new calculations and the reason; do not silently shrink
the denominator to obtain a higher percentage.

This operational rubric explicitly restores fresh prompt and independent policy
validation as the experimental targets. It stops crediting the old routing/bank
studies as completion of those targets while retaining their scientific value as
diagnostics. The weighted increases from newly developed theory/design/software
and the withdrawn experimental credits are already incorporated in the 49%
retrospective baseline; they are not new gains for this check.

**This hour's advance:** PR #6 is verified merged on main; the direct-main workflow
is acknowledged; 14 planning scenarios and six precision thresholds are checked
and independently reviewed. The [precision report](landmark_precision_plan_20260921.md)
clarifies what the development batch can establish. These improve the existing
design package but do not complete another scored milestone, hence Δ=0 points.
The largest blockers remain valid containment/measurement, receiver and task
freeze, fresh supported prompt data, and independent policy evaluation. Full
manuscript integration remains required.

The following weights and checkpoints are retained as historical context. Their
original interpretations and now-superseded pivot do not override this contract.

## Weights

| # | Component | Weight | Counts as complete when |
|---|---|---|---|
| 1 | Positioning and verified literature | 10% | every cited claim traced to a real primary source, closest prior art tabulated, novelty claim written and survivable |
| 2 | Theory: identification, estimands, estimators, guarantees | 20% | numbered assumptions and results, proofs, design ladder stating what holds by construction versus by assumption, scope and limitations |
| 3 | Experimental design and pre-registration | 15% | protocol, config, taxonomy with exemplars, seeded assignment, analysis script and outcome list frozen and committed, freeze commit recorded |
| 4 | Harness implemented and tested | 10% | runner, intervener, receiver client, verifier, branch store, manifests, resume, contention guard, test suite green |
| 5 | Confirmatory simulation study (E0) executed | 10% | pre-registered grid run, including conditions where the estimators should fail; coverage checked with enough replicates |
| 6 | Real-model experiments executed | 15% | the anchor randomized/branch experiment run to its pre-registered size, audits passed, results written |
| 7 | Critic and policy results, including stopping | 10% | primary comparison run at matched budget against the pre-specified baselines |
| 8 | Manuscript | 10% | full draft with figures, limitations, and reproduction instructions |

Partial credit is allowed per component and must be justified in the checkpoint.
Reported-but-not-independently-validated results earn at most half credit for their
component.

## Checkpoints

### 2026-09-19, checkpoint 1 — **13%** (baseline; no previous checkpoint)

| # | Component | Credit | Basis |
|---|---|---|---|
| 1 | Positioning / literature | 0.25 | a ten-cluster citation verification and a five-angle prior-art sweep are in flight; nothing adjudicated yet, and several citations in the originating brief are suspected fabrications pending check |
| 2 | Theory | 0.15 | five independent identification routes drafted and under review; premise checks P1–P3 have already changed which claims the theory should carry, but no identification document exists yet |
| 3 | Design / pre-registration | 0.25 | taxonomy merge and six design specs in flight; audits A1–A3, which are prerequisites for sizing and for outcome validity, are complete |
| 4 | Harness | 0.15 | sandbox and hidden-test verifier ported with the visible/hidden split; three audit scripts; estimator prototypes exist inside the premise checks but not as a tested module |
| 5 | Simulation study | 0.15 | P1–P3 exist and are informative but are explicitly exploratory, not the pre-registered grid |
| 6 | Real-model experiments | 0.05 | none run; cost and difficulty calibration obtained at zero GPU cost from a sibling project's completed run |
| 7 | Critic / policy | 0.00 | not started |
| 8 | Manuscript | 0.00 | not started |

**Largest remaining milestones**, in order: (i) the theory workstream answering Q1–Q11
in `COORDINATION.md`, above all Q11, which decides whether the paper leads with
identification-and-reporting or with horizon-aware valuation; (ii) freezing the
intervention taxonomy, which is the most expensive artifact to change afterwards;
(iii) the pre-registered freeze; (iv) measuring first-attempt success and the
degradation rate on this project's own prompt format, the first GPU work; (v) the
anchor randomized experiment.

**Largest risks to the number:** the effective task sample is ~230, not 590 (A2);
the sibling projects contend for the only GPU; and the decision-level version of the
project's central claim is currently unsupported (`docs/premise_findings.md`), so
component 7 may have to be redefined before it can be earned.

### 2026-09-19, checkpoint 2 — **19%** (+6 since checkpoint 1)

Component 1 (positioning and verified literature) rises from 0.25 to **0.85**: 141
citations verified with live lookups, 96 prior-art items swept and adjudicated, the
closest prior art tabulated with what each has and lacks, a novelty claim written
that survived an adversarial area-chair review, and a concession table naming what we
give up and to whom (`docs/literature_audit.md`, `docs/positioning.md`). Not 1.0
because three verification verdicts remain UNCLEAR, and because the design-novelty
claim rests on a negative search that must be re-run before submission.

No other component moved: the identification document is still in synthesis and the
six design specs are still being drafted.

**What this checkpoint changed about the project, not just its readiness.** The
brief's novelty claim did not survive, so the paper is smaller than planned. The
surviving contribution — prospective sequential randomization with logged
propensities, coarsening as the identification argument, branch-sampled validation,
and spending the effects on when to intervene — is now supported by three
independent lines of evidence that were produced without sight of each other. That is
a better position to be in than an unexamined large claim, but it does mean
components 2 and 7 will need redefining against `docs/positioning.md` before they can
be earned.

### 2026-09-19, checkpoint 3 — **37%** (+18 since checkpoint 2)

| # | Component | Credit | Δ | Basis |
|---|---|---|---|---|
| 1 | Positioning / literature | 0.85 | — | unchanged |
| 2 | Theory | 0.40 | +0.25 | a 92,000-character synthesis with 22 numbered assumptions and 32 results exists, has been adversarially reviewed by five independent reviewers (90 findings, 20 fatal), and is being repaired section by section against a binding spec. Not higher because the repaired document does not exist yet and several results will be withdrawn. |
| 3 | Design / pre-registration | 0.55 | +0.30 | 9-class taxonomy merged with provable per-class information caps and script-checkable audit gates; six design specs with numeric parameters; harness architecture, cost model and audit gate specified; audits A1–A4 complete; the task pool is settled at 230 by three independent routes. Not higher because nothing is frozen and the pilot has just invalidated two cost claims. |
| 4 | Harness | 0.35 | +0.20 | sandbox, hidden-test verifier, integrity gates, assertion-level scoring, four audit scripts, the E0 code, and a hashed inference-build manifest. No episode runner, intervener or branch store yet. |
| 5 | Simulation study | 0.70 | +0.55 | E0 promoted to first-class code, exact dynamic program verified against a 2,000,000-episode Monte Carlo to 0.00 MC SE, four pre-registered failure cells implemented, and the 17-cell grid running at the pre-registered R = 1000. |
| 6 | Real-model experiments | 0.10 | +0.05 | pilots only, but they are informative: the first real measurement of the headline content contrast, plus a corrected throughput figure. |
| 7 | Critic / policy | 0.00 | — | not started |
| 8 | Manuscript | 0.00 | — | not started |

**Largest remaining milestones:** the theory repair landing; the Program phase folding
the adversarial findings into a single experimental program; the freeze; then the
confirmatory runs.

**Risks that grew this checkpoint.** The content contrast measured −0.044
(95% CI [−0.114, +0.026]) in the first real pilot, so the effect the project was built
around may be null. Detecting 0.05 needs 273 states against a pool of 230. Common
random numbers deliver 25% rather than the order of magnitude the branch-tree cost
assumed, and multi-turn calls cost 2.4× the planning figure. None of these is fatal, and
all of them argue for the same reframing the premise checks and the literature audit
already pointed at.

### 2026-09-19, checkpoint 4 — **45%** (+8 since checkpoint 3)

| # | Component | Credit | Δ | Basis |
|---|---|---|---|---|
| 1 | Positioning / literature | 0.85 | — | unchanged |
| 2 | Theory | 0.55 | +0.15 | 17 of 18 repair agents complete, all repaired sections on disk against a binding cross-cutting spec; errata outstanding |
| 3 | Design / pre-registration | 0.70 | +0.15 | the full program exists: 27 arms in four gates, 12 kill criteria including a no-wriggle clause, a freeze checklist, and 10 named theory blockers. Still not frozen. |
| 4 | Harness | 0.40 | +0.05 | G0e's analysis code added; still no episode runner, intervener or tree store |
| 5 | Simulation study | 0.90 | +0.20 | E0 executed at the pre-registered R = 1000 across all 17 cells, written up, failure cells failing exactly as designed |
| 6 | Real-model experiments | 0.15 | +0.05 | K1 tested and fired at zero GPU cost on existing data — a gate cleared in the sense that matters, by being failed early |
| 7 | Critic / policy | 0.00 | — | and its target has changed: selection and stopping, not message generation |
| 8 | Manuscript | 0.00 | — | not started |

**The finding that moved this checkpoint is negative.** Kill criterion K1 fired: adaptive
best-of-N beats the multi-turn loop at lower cost on both receivers. That is progress —
the cheapest possible test of the project's most dangerous comparator ran before any
confirmatory budget was spent, and it redirected the programme rather than embarrassing it
later. Readiness rose because the programme is better specified and better evidenced, not
because the original hypothesis survived.

**Largest remaining milestones:** assemble the repaired theory; re-scope Gate 1 around
selection and stopping; answer the 10 theory blockers; freeze; then Gate 1's GPU work.

### 2026-09-19, checkpoint 5 — **49%** (+4 since checkpoint 4)

| # | Component | Credit | Δ | Basis |
|---|---|---|---|---|
| 1 | Positioning / literature | 0.85 | — | unchanged |
| 2 | Theory | 0.65 | +0.10 | the repaired document is assembled with its errata, and the 31 requirements it imposes are extracted. Not higher: 15 questions need a human theorist and 14 adversarial findings remain unresolved. |
| 3 | Design / pre-registration | 0.75 | +0.05 | Gate 1 re-scoped against the evidence, with the new primary costing 3.07 GPU-h instead of 12.60 and needing no intervention arms |
| 4 | Harness | 0.40 | — | unchanged; still the largest gap, and G1a′ showed the feature map is now load-bearing |
| 5 | Simulation study | 0.90 | — | unchanged |
| 6 | Real-model experiments | 0.20 | +0.05 | two decisive gates run at zero GPU cost, both returning negative |
| 7 | Critic / policy | 0.00 | — | target now selection and stopping; feasibility is an open question |
| 8 | Manuscript | 0.00 | — | not started |

**Two of this session's most valuable results are negative**, and both arrived before any
confirmatory budget was committed: adaptive best-of-N beats a real multi-turn loop, and
cheap policy-observable features recover none of the selection headroom. The project is
better off knowing both now.

**The single question that decides the project:** can cross-candidate execution agreement
recover the 3.5–7.4 points of selection headroom? It is well-posed, it has a measured
ceiling, it has a known-strong published comparator, and it requires probe-input
generation inside Gate 1. Everything else is downstream of the answer.

### 2026-09-20, checkpoint 6 — **48%** (−1 since the historical 49%)

This is a subjective work-planning estimate under the same weights, rounded from 48.0%; it is not an empirical probability of readiness or acceptance. The previous narrative overcredited flawed simulation targets and selected-cohort gates. The new proofs, corrected studies and audited selector pilot earn separate progress without treating them as prospective validation.

| Component | Credit | Weighted contribution | Basis |
|---|---:|---:|---|
| Literature | .80 | 8% | Ten key sources rechecked; materially incorrect novelty/possibility interpretations corrected; broader audit still needs integration |
| Theory | .75 | 15% | Original proofs plus ten scoped stopping/selection results, 14 reconciliations and exact checks; broader draft not fully independently validated |
| Design/freeze | .40 | 6% | Concrete protocols and handoff exist; conflicting intervention schemes and updated estimands still require one committed collection freeze |
| Harness | .50 | 5% | Fixed-slate collector, sandbox tooling and 51 tests; full generated-slate branch runner/measurement contract remains incomplete |
| Confirmatory simulation | .50 | 5% | 1,360 corrected diagnostic replications plus independent checks; final MC precision and fair fitted baselines pending |
| Real-model experiments | .20 | 3% | Existing 4,488-episode source independently audited; no new randomized prompt study |
| Critic/policy | .30 | 3% | Two fixed-bank learners evaluated on separate roots with a promising exploratory 7B signal; fresh matched-cost confirmation pending |
| Manuscript | .30 | 3% | Theory/research PDF and update report exist; final integrated evidence-backed manuscript absent |

The largest milestones are acceptance/integration of the corrections, one frozen intervention design, family/test-leakage audits, fresh selection validation, actual randomized prompt effects with named continuation, and an integrated manuscript with defensible novelty. The original personalized-prompt research goal is not replaced by a completed candidate-bank selection study.
