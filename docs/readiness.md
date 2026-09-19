# Full-project readiness rubric

`AGENTS.md` requires every user-facing progress summary and every scheduled repo
update to state the estimated readiness of the **full project** for a paper
submission, its change since the previous checkpoint, and the largest remaining
milestones. This file fixes the rubric so the number is comparable across
checkpoints rather than re-invented each time.

It is a **planning estimate of work completed against work required**. It is not an
acceptance probability, not a quality judgement, and not a time estimate.

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
