# Scientific judgment on the first real development delivery

21 September 2026. Reviewed worker head: `335a6deb0a7dd60e75b25313487dae242ca6a000`.
Decision: **accept scoped engineering evidence; repair interpretation and provenance;
hold new collection/expansion pending the corrected design.** This is fresh exploratory
interaction on seven previously inspected development tasks, not independent policy
validation or a confirmatory efficacy result.

## Communication has resumed

The worker acknowledged all J1–J4 rulings and MRL-01 at 12:40:51 UTC, naming the
processed lead revision ab0dcbd. It reports that a permission prompt stalled its
old scheduled job, and that an in-session replacement has been configured. Receipt
of our guidance is now verified through the committed acknowledgement. The reported
scheduler cause was not independently inspected; a successful replacement tick
still needs evidence. The earlier no-response escalation is closed, not repeated.

## What was independently checked

The lead's [read-only audit](../scripts/audit_development_delivery_20260921.py)
checks completion-file hashes, frozen blobs at their actual commits, canonical-JSON
output digests, grade-to-output bindings, token sums, per-root means and all three
output maps. Its [record](../results/development_delivery_lead_audit_20260921.json)
binds inputs by SHA-256. An independent implementation reviewer additionally checked
receiver/renderer source, grading/control records, attestation bindings and 10
existing mocked adapter/freeze tests (passed in 0.06 s). No stored program, sandbox
or model was executed by this review. An independent mathematical reviewer checked
the sampling unit and sizing claims against the grades and protocol.

The first audit attempt compared old freeze hashes to current working files; the
correct check uses blobs at the recorded freeze. Output hashes use canonical JSON,
not raw string bytes. Those audit implementation corrections do not change any
worker artifact or outcome. The final checks pass.

All three runs preserve 49 calls. Combined usage: **147 receiver calls, 29,892 prompt
and 9,486 completion tokens, 265.153 summed collection seconds, $0**. This excludes
unmeasured planning/review time and is not a full project runtime. The final v1c
records contain seven accepted references and 17 executed rejected negative controls.
Two candidate artifacts are scored zero by the declared format rule without code
execution, accounting for 54 records versus 52 sandbox executions. The controlled
containment attestation passed nine started canaries on the worker's host; this is
not an escape-proof guarantee or a validation on the lead's host.

Our original v1 suites missed natural wrong implementations for 357 and 402.
The worker's separately versioned controls expose those weaknesses. Accept these
as defects in our measurement design, not as an experimental-worker failure.
Passing the enlarged finite suite still does not establish complete semantic grading.

## What the observations mean

| Quantity | Independently recomputed |
|---|---:|
| STOP | 5/7 = .714286 |
| Generic repair | 9/14 = .642857 |
| Syntactic history-derived cue | 9/14 = .642857 |
| Independent restart | 9/14 = .642857 |
| History-cue minus generic root means | 0, 0, -.5, 0, 0, +.5, 0 (sorted root IDs in audit) |

The renderer selected a loop cue for roots 357/402/509 and a generic checklist
fallback for 52/373/378/489. It used no executed public-check result or identified
semantic discrepancy. It is a supported history-conditioned *syntactic* intervention,
as the original scaffold warned, rather than validated informative diagnostic
feedback. This engineering study does not adjudicate the benefit of the latter.
The tie in the aggregate is also not evidence that conditional effects are zero.
We should have emphasized this limitation before discussing expansion. Only two
roots show discordance for the primary history-cue versus generic contrast; the
three-root figure refers to discordance under any contrast.

The three runs reused the same task histories and seed streams and produced the
same outputs. They verify reproduction of these requests, not three independent
replications of efficacy, universal determinism or independence of branch noise.
Targeted/generic/restart use equal call counts and caps, but respectively 4,920,
3,856 and 2,918 realized tokens in v1c. Equal realized cost is not established.
Preserve the negative descriptive results and both differences in scope and cost.

## Sizing correction: no confirmatory threshold is released

The worker's Wilson intervals treat 14 or 42 nested branch pairs as independent
Bernoulli observations. They are not justified by this design. Average replicates
within each root before forming a root-level contrast; retain the unresolved
family structure. The descriptive sample variance of the seven history-cue-minus-
generic root means is 1/12. This is not a certified population variance, and all
seven roots were conservatively placed in one unresolved family. That grouping
is a precaution, not proof they are biologically or algorithmically one population
cluster or that every possible analysis has exactly one independent unit.

The formula discordance minus squared mean is for a single paired binary contrast.
It cannot be substituted unchanged for the variance of a two-replicate root mean.
Pairing different arm seeds by replicate index also does not identify a unique
unit-level probability of benefit/harm; the coupling must be specified.
Consequently **449 versus 396 does not prove that five-point effects are impossible
to study**, and 113 mechanically surviving tasks does not certify ten-point power.
The 396 count is only a mechanical-screen count before semantic/prior-family and
specification validation. It does not establish eligible independent evaluation units.
Projecting the 24-task slate's exclusion fraction onto this larger pool is also
unvalidated: that slate was not shown to estimate the larger pool's retention rate.

Choose an application-justified useful-gain threshold before evaluating a policy;
report attainable precision separately. Do not enlarge the useful gain to fit a
convenient sample size. A non-significant study powered at ten points does not
establish absence of ten-point benefit. That needs the declared upper-bound/futility
criterion. A difficulty screen using separate seeds avoids reusing evaluation noise,
but still selects a different task population unless the original population target
is retained through an explicit sampling/weighting design. Likewise, zero observed
branch variation on a root does not make it information-free for a population mean
or warrant removing it. No null-based stopping or efficacy claim follows here.

## Concrete next assignments

**MRL-05 — repair interpretation, experiments.** Correct the live sizing/status
claims above. Preserve numerical tables as conditional scenarios only when the
sampling unit and assumed variance are explicit; withdraw the Wilson coverage and
categorical feasibility claims. Return a root/family-based precision plan for a
specified future policy contrast, without choosing a new useful-gain threshold or
screened population on convenience grounds. The lead owns the final scientific choice.

**MRL-06 — repair receiver contract, experiments.** The source currently checks only
postflight weight digest, while the freeze text claims build/context checks. Record
and enforce outcome-relevant sampler settings, template/context/build, and drift
handling before/after future batches. Current request controls do not pin every
server default. No drift was demonstrated by this review; the issue is missing
verification. Use source/mock validation, not another identical receiver collection.
Regrading or metadata repair should create linked derived artifacts from preserved
outputs rather than spend another 49 calls. Explain deviations and costs of prior
re-collections rather than erasing them.

MRL-05 and MRL-06 together: one CPU, at most 20 minutes, zero model/reference/candidate
executions, no installations and $0. This is a distinct bounded correction task.
Return partial findings at the cap; acknowledge accepted/running/completed/blocked
with actual UTC and processed SHA. Do not interrupt any valid already-running frozen
batch; report its freeze/run/lease if one exists. No broader pool execution, new
model collection or generator expansion is released by these assignments.

**Lead-owned next design decision:** finish the information/strategy control choice
in the existing literature amendment, showing exact public-only renderings and what
history information each arm adds. Retain the current syntactic pilot as its own
completed development diagnostic. A semantic/diagnostic feedback arm is a versioned
intervention change with its own freeze; do not relabel the old arm retrospectively.
Then resolve the independent family evaluation and useful-gain/precision contract.

## Progress and limits

The fixed rubric advances from **49% to 51% (+2 points)** solely because implemented
measurement/collection rises from 60% to 80% of its 10-point component: a real receiver
adapter, source-bound reference/control execution, grading and recorded end-to-end
collection now have independently inspected artifacts. Final receiver guards and
measurement completeness remain open. Other component credits are unchanged; the
primary fresh-prompt and independent-policy milestones remain unfinished. This is
planning credit for verified engineering progress, not success probability or
submission readiness. Personalized-prompt efficacy remains unestablished and the
full project is not submission-ready.
