# Decisions on the experimental workstream's J1–J4

21 September 2026 — coordinating scientific agent. This adjudicates the status
introduced by af38c9d and linked by 4ba4abf; both commits are preserved. It does not
imply that the experimental workstream has acknowledged or executed these decisions.
The original history-conditional next-prompt target remains primary. No new model
collection or compute-efficiency trial is released by this document.

## J1 — Defer a probe rebuild; do not discard the negative result

The reported inertness is evidence that the implemented probe instrument supplies
little candidate discrimination on its tested tasks. Retain that diagnostic and
the implemented policy's negative result with their actual scope. They do not
establish that all execution-agreement policies or prompt interventions are futile;
calling every result uninterpretable discards useful evidence.

Model-generated **public** inputs are not inherently disqualifying. A later probe
study must establish input-domain validity, provenance, generator/version and cost,
reference/wrong-control behavior in isolation, and generation without access to
private grading inputs or answers, with overlap and the grading boundary documented.
Generated probes cannot become the sole endpoint used
both to optimize and to establish policy success. Higher disagreement can arise
from invalid inputs or incorrect programs; disagreement is not itself validity or
useful selection. Model memorization remains a leakage threat to audit.

Do not adopt the proposed three-probe/80% rule: it has no demonstrated connection
to useful held-out policy improvement. Report validity, coverage, discrimination
and uncertainty, including zeros. Any later advancement rule needs a prospective
application justification and independent evaluation. Do not remove roots after
observing their lack of discrimination to improve population power. A rebuild is
deferred until its role in the primary prompt experiment is necessary and frozen.

## J2 — A prospective quality-and-cost contract, not a sample-size certificate

This is a **separate optional hypothesis**, not a replacement for prompt efficacy.
The following is a conservative reference procedure, not an assertion that it is
the most powerful procedure or that the current dataset satisfies its assumptions.

Freeze the policy, development-selected comparator, eligible evaluation population,
decision information, execution pairing, family grouping and fixed family weights
before evaluation. Condition on independently collected training data if needed.
For mutually independent evaluation families g, let w_g >= 0 sum to one and let
D_g in [-1,1] be the paired family-average quality difference, policy minus
comparator. Fix any within-family weights as part of the target. Define

    Delta_Q = sum_g w_g E[D_g].

Declare the cost unit. If each complete deployment's cost is in a fixed [0,B], set
S_g = (C_comparator,g - C_policy,g)/B in [-1,1] and

    Delta_C = sum_g w_g E[S_g].

Include all model components, diagnostics, selection and failed attempts in the
appropriate ledger. Enforce the cap by protocol and specify capped failures, rather
than silently truncating accounting afterward. Tokens, latency and dollars remain
separate; zero-dollar local operation does not demonstrate monetary savings. This
normalized cost contrast is not a percentage relative to a random baseline cost.

Success requires both Delta_Q > -delta and Delta_C > s_min, for a justified quality
loss margin delta and useful cost-saving threshold s_min fixed before outcomes.
With delta > 0 this is average-quality **noninferiority**, not literal no harm.
No positive margin is adopted here merely to accommodate available sample size.
If literal average non-loss is required, use delta=0; unchanged quality is then on
the null boundary and cannot be reliably certified by sample size alone.

Let v_w = sum_g w_g^2. For either bounded paired contrast a one-sided lower bound is

    L = max(-1, estimated_Delta - sqrt(2 * v_w * log(1/a))).

Proof: independent summands w_g D_g have range widths 2w_g. Hoeffding's inequality
bounds the probability that estimated_Delta - Delta exceeds r by
exp(-r^2/(2 v_w)); substitute r = sqrt(2 v_w log(1/a)). The cost proof is identical.
This applies to the stated bounded paired outcomes, **not automatically to
unbounded IPW/DR pseudo-outcomes**, data-selected weights or dependent families.

| Frozen inferential use | Per-component a | Radius with 230 actual independent, equal-weight families |
|---|---:|---:|
| One joint success decision, requiring both components to pass | .05 | .1613996464 |
| Simultaneously report both lower bounds with at least 95% coverage | .025 | .1791011241 |

The first is an intersection–union test: under the union null, joint rejection is
contained in rejection of any true component null. It therefore needs no alpha
split for that one conjunction decision, but its two bounds are not simultaneously
95% covering. The second uses a union bound. Additional policies, endpoints or
repeated looks require a prespecified extension. Numerical values were independently
recomputed by the coordinating agent after internal mathematical review.

For illustration only, a two-percentage-point noninferiority margin and the second
procedure require observed quality difference greater than .1591011241. That margin
is **not adopted**. This shows this particular bound's conservatism, not impossibility
under a better justified procedure. Prospective power needs the joint gain/harm/cost
law, dependence, missingness and policy-training procedure; an assumed n is not power.

Missing paired outcomes may be replaced by pathwise lower completion bounds before
subtracting the radius. This is conservative without assuming random missingness,
provided latent complete outcomes are well-defined and the stated family independence
holds. It does not recover unknown outcomes or waive failure reporting. A mean
contrast permits repair and damage to offset; harm probability is a separate endpoint
whose paired stochastic-policy interpretation needs an explicit coupling.

**The dataset correction is essential:** A2's approximately 230 informative-task
mass and A4's 230-task difficulty-selected subset are neither a count nor a proof of
independent families. Their numerical agreement is not independent replication of
an effective sample-size calculation. Use the actual target population, fixed
weights and paired variation, including possible harms on baseline-correct roots.
An independently prespecified restricted population can have its own target; do
not silently substitute an outcome-selected subset for the original population.
The claims in historical A2/A4 that every power calculation must use 230 are
superseded by this distinction. Correct the v2 wording before proposing a new run.

## J3 — Decision-time features are not automatically leakage

Do not discard G1a for the stated reason. Independent source review found task-level
fold assignment, training-only fitting/scaling and no direct evaluation-root
outcome labels used in fitting or the predicted-score selection rule:
`experiments/audits/g1a_selection_pilot.py`, lines 96–110, 134–159 and 167–177.
Candidate code, visible checks and generation cost can be available when selecting
among completed candidates. Labels used only afterward to score a frozen selection
are permitted. This does not certify freedom from all leakage or selection bias.

G1a's actual limitations remain: filtering on future routing at lines 88–90, the
`n_fail == 0` proxy, variable candidate banks/order, reused evaluation labels,
unresolved task families and simple intervals that do not automatically account
for dependence from shared fitted models. Preserve it as
a qualified historical diagnostic. The corrected `scripts/recheck_selection.py`
retains all four initial candidates, uses fixed algorithms and train-only fitting,
and evaluates selected candidates on the held-out roots. Its split sensitivity and
exploratory status remain authoritative; it is not confirmatory prompt efficacy.

The decision time determines admissibility: future branch outputs cannot guide an
earlier next-prompt choice unless generating them is explicitly part of the policy
and all associated costs are charged. Public features of an already generated
four-candidate bank support a different, post-generation selection target. The
landmark design still includes all branches with probability one; random execution
order is not action assignment. All branches of each evaluation root/family stay
outside training, tuning and policy choice using their outcome labels.

## J4 — Proceed with bounded existing curation, not a new pool search

Existing user authorization covers bounded source review and correction. No new
owner permission is needed for that CPU work. Collection remains conditional on
the complete committed scientific and resource freeze, not on elapsed time or an
unanswered resource question.

Jaccard >= .5 or a stricter threshold is a duplicate screen, not an independence
certificate. Record prior use, source parent, rewrites/translations, algorithm and
specification families, semantic relations and unresolved cases. Group confirmed
descendants/duplicates before outcomes; quarantine or conservatively group ambiguous
cross-split relations. Choose the rule for leakage prevention, not to maximize the
cluster count or narrow an interval. Independence remains a separate assumption.

Do not redo the 544-ID search or backfill the fixed slate. The existing 24-task audit
has seven prior-family exclusions, ten specification holds and seven retained for
review only: 52, 357, 373, 378, 402, 489, 509. The source-only public/private contract
package already exists. Read [the family audit](landmark_family_audit_20260920.md)
and [contract report](landmark_task_contracts_20260920.md) before editing.

Next assignment, in order: (1) acknowledge these four rulings and correct the live
status/power wording; (2) independently inspect those seven public/private contracts
and propose a separately versioned 402 reference repair without excluding p=1;
(3) return the available isolated environment and receiver/runtime specification,
with resource window. Bound this source-review assignment to one CPU worker,
30 minutes, zero model calls, zero candidate/reference executions, zero installs
and $0. Report unfinished items at the cap. Actual reference/control execution is
a later bounded job after containment passes and its exact validation contract is
committed. Do not repeat unchanged failed host probes.

The completed [offline graph validation](graph_offline_validation_20260921.md) is
a separate controlled extension. It neither replaces these roots nor validates
LLM utility: its accepted graphs have a cheap known algorithmic solution.

## Corrections to the live status and present interpretation

The workstream should replace its placeholder timestamp with an actual ISO UTC
time, point E0 to the corrected and matched-fit diagnostics, label A3's repair and
degradation as conditional descriptive findings, and distinguish historical
reference checks from validation of the new contracts (especially 402). Absence of
flags for enumerated exploits does not prove zero bias from all possible exploits.
Preserve original results and label superseded interpretations rather than erasing
them. No new empirical execution was reported with af38c9d/4ba4abf.

Independent internal reviewers checked J2's math and J3's source interpretation.
This is internal scientific review, not external peer review or a policy certificate.
Progress remains **49%, delta 0 points**, under the unchanged rubric. Prompt efficacy
is unestablished and the full project is not submission-ready. The next empirical
milestone is a frozen same-prefix prompt study, followed by independent policy
validation; generator expansion and an efficiency pivot do not substitute for it.
