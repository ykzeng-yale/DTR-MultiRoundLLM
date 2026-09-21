# Lead resolution of the worker's implementation and study-design issues

21 September 2026. The owner supplied the worker's detailed account and requested
that every issue be addressed on GitHub. This response consolidates the reviewed
335a6de delivery, current corrections and concrete scientific decisions. It does
not imply every remaining implementation item is already completed. Preserve the
original runs and source versions; do not recollect merely to repair documentation.

## Decision on the requested effect size

**Adopt a working useful-gain threshold of 0.05 absolute probability** for the future
frozen public-history policy versus the frozen development-selected fixed arm.
The endpoint is the final artifact passing its declared private suite. The practical
working criterion is five additional suite-passing final answers per 100 evaluated
tasks under the same declared one-continuation-call ceiling. This is a lead-selected
research target, not measured user utility, complete semantic correctness, a prior
preregistration or a benefit estimated from the seven-task pilot. Initial-answer,
checker and selector costs still count; matching call ceilings does not match tokens,
latency or dollars. A practical efficiency claim needs its separate cost contract.

Do **not** replace this usefulness threshold by 0.10 to accommodate the current pool.
For prospective power sensitivity analysis, use an alternative gain of 0.10 against
the usefulness null Delta<=0.05: the separation is 0.05. Target 80% power at a
prespecified final analysis with one-sided alpha 0.025 (the lower end of a valid
central 95% interval). These are design targets, not a certified sample size. The
comparator is selected on development data and frozen independently of evaluation;
it is not assumed to be the population-optimal fixed arm.

With valid prespecified bounds [L,U], classify useful benefit by L>0.05, useful-gain
futility by U<0.05, and otherwise inconclusive about the threshold. Equality does
not pass either strict rule. Superiority over zero is an additional label when
L>0; it can coexist with useful-gain futility if 0<L<U<0.05. Do not infer absence
of a ten-point effect from nonsignificance. No repeated outcome-driven looks are
permitted by this final-analysis rule. Report all outcomes, including costs and
failures, irrespective of the decision.

This is a **new prospective design decision informed by development**, requiring
untouched evaluation roots/families and a complete locked analysis. It does not
release a full trial. The immediate seven-root diagnostic stage remains descriptive
engineering development, with no effect-size-based early stop or policy claim.
Before a full freeze, resolve the target population, sampling/weights, family
structure, repetition count, actual variance scenarios, uncertainty procedure and
numerical resource ceiling. If those cannot support a useful decision, report
inconclusive feasibility rather than raising the threshold to obtain a convenient n.
Independent internal mathematical review supports these decision distinctions.

## Disposition of every issue raised

| Issue in the worker's account | Lead finding and concrete disposition |
|---|---|
| GitHub comments unavailable, while commits work | Accepted. Commit-based replies are sufficient. A brief result/blocker plus processed main revision closes receipt; no separate acknowledgement table or new credential is required. The lead can mirror decisions to issue #3. |
| Scheduled job stalled on an unattended permission prompt | Accepted as the worker's explanation; the underlying scheduler was not independently inspected. Publication resumed. Report the replacement's first successful tick or exact current blocker; configuring a schedule is not proof of successful execution. Do not create another experimental job. |
| Attach to idle 3B rather than start another server | Accept the resource strategy conditionally on a current idle/lease check. Do not stop sibling processes or load a third model under memory pressure. Historical idle status is not a current lease. |
| Explicit system message and template override | Preserve the explicit system and verified rendering artifact. Pin the template/build/context and outcome-relevant defaults in the next freeze; the stored observation alone is not a guard against later change. |
| Ollama-only collector could not reach the actual server | Real preparation defect accepted. Keep the llama-server adapter. The current focused mocked adapter/freeze suite passes 12 tests. This validates those software paths, not live receiver stability. |
| 32-token mock limit would truncate real code | Use the already proposed 512-token real-run cap. The 32-token value was a mock fixture, not an adequate real code budget. Track length termination; observed maxima below 512 do not guarantee future non-truncation. |
| Weight/shard hashing versus nominal labels | Retain actual file-hash verification. Matching weight/build labels does not automatically transfer calibration across prompts, hidden defaults, hardware or population. MRL-06 must reconcile the claimed complete postflight checks with digest-only current code. |
| Task 357 private tests admitted last-element maximum | Accept as a flaw in our original measurement design. Keep versioned v2 cases/controls and the executed control evidence; no rewriting v1 results. |
| Task 402 private tests admitted a prime-only method | Accept the additional discrimination defect. Keep composite-modulus cases and negative controls. Passing a finite suite does not certify the complete domain. |
| 402 reference p=1/r=0 bug | Adopt only the already validated, hash-bound `return C[r] % p` repair for the new grading contract; keep p=1. Preserve the original and its observed failure. No outcome-based exclusion of 402. |
| Full-MBPP provenance was missing | The recorded matching pinned source hash closes that source gap for the reviewed artifacts. Keep source version/license bindings and distinguish these IDs from untouched evaluation data. |
| Sandbox launcher failed and earlier explanation was wrong | Accept the diagnosed literal-root-read fix and 9/9 started controlled canaries on the worker host. Withdraw confidence in our earlier interpreter-location explanation. Nine checks do not prove that no escape exists or validate another host. |
| All 25 expected reference/control outcomes matched | Accept the inspected validation records for seven roots, including the failing original 402 and passing repair. The gate demonstrates rejection of specified wrong programs, not exhaustive measurement validity. |
| Seven roots described as fresh | They were not in the compared old corpus, but their definitions/specifications were inspected during development. Call this fresh interaction on development tasks; it is not untouched out-of-family policy evaluation. An unresolved-family label is not proof all seven share one true family. |
| Grading JSON-array/JSONL mismatch and wrong hash convention | Retain the corrected content and canonical grading-contract digest. Keep the original refused run. For future repairs, preserve receiver outputs and publish a linked derived grading record; do not automatically recollect. No unobserved original grade is imputed. |
| 402 ungraded because builder still used old reference | Accept the explicit hash-verified adoption flag and v1c records. Preserve earlier missing grades and their reason, rather than retrospectively pretending the initial release validated all roots. |
| Three same-seed replays described as full determinism | Accept 49/49 matching outputs for these recorded requests. They are reproducibility checks, not three independent efficacy studies or a universal determinism guarantee. Charge all 147 calls,39,378 tokens and 265.153 collection seconds. |
| STOP .714 versus each continuation .643; repair 0/8; damage 4/30 | Preserve these independently reconciled descriptions. They do not prove general harm, feedback futility or superiority of resampling. Restart repaired 1/4 on initially wrong roots; all three continuation means tie here. |
| “History-specific feedback” label | The actual renderer uses loop cues on 3 roots and checklist fallback on 4, without executed diagnostics. Keep that limited intervention's negative result. The next diagnostic proposal is a separately versioned information law, not a relabeling of old data. |
| 14/42 branch pairs used for sizing and Wilson intervals | Correct MRL-05: repetitions are nested within roots, and the 42 comparisons also reuse STOP and combine interventions. Use root means and justified family structure. The prior Wilson intervals do not have established coverage for this design. |
| 449 needed versus 396 available;113 makes 10 points feasible | Reject categorical feasibility/impossibility. These are conditional calculations from an inadequately transferred variance. The seven root-mean primary contrasts have descriptive sample variance 1/12; this is not a certified population variance or replacement sample-size estimate. Only 2 roots show primary-contrast discordance;3 concern any contrast. |
| Zero-discordance roots carry no information | Incorrect. They contribute to the unconditional mean, and two seeds do not establish a true ceiling/floor. Do not remove them on observed outcomes. Separate-seed difficulty selection changes the population unless a sampling/weighting design preserves the original target. |
| 396 pass the mechanical screen | Accept the saved mechanical count only. It is not 396 semantically validated independent evaluation units. A do-nothing control is weak evidence of discrimination; transport of the 24-task exclusion fraction to 396 is unvalidated. |
| Relax imports/interface rules or expand curation next | Defer expansion until the existing diagnostic/receiver corrections and design are resolved. Allowing imports changes evaluator/security and parser contracts; it is not only a counting adjustment. Preserve excluded cases; do not expand the pool to rescue a preferred result. |
| Test failures were hidden by `tail`, then committed | Added `scripts/check_tests.sh`, which directly returns pytest's exit status without a pipeline. Focused mocked tests pass; an intentionally missing test path returns exit 4. A test failure must stop the workflow before staging/commit. This validates the local wrapper, not a claim about the worker's shell configuration. |
| Helper file changed package source hashes | Keep standalone analysis helpers in `scripts/` when they are not runtime dependencies. Actual runtime code changes require a new freeze; historical manifests must resolve their original Git blobs. Do not waive hash failures to make a changed checkout look identical. |
| Backticks damaged a document; Lucas helper hung at p=1 | Use literal files/structured body arguments for documents, with diff checks before commit. Mathematical helpers need explicit domains and an external timeout; prime-only Lucas arithmetic is undefined for p=1. Retain the reported failure and do not treat helper success as reference validation. |

## Execution order and authority

1. **MRL-05:** apply the statistical wording corrections and this working 5-point
   usefulness decision. Return explicit root/family variance sensitivity assumptions;
   no new model or sandbox execution is needed.
2. **MRL-06:** complete the receiver configuration/drift guards and source/mock tests.
   Specify sampler defaults, template/system/context/build checks and how a changed
   or unverifiable postflight state prevents efficacy interpretation. Preserve all
   raw outputs if drift is detected; stopping future dispatch and marking affected
   evidence invalid is different from deleting outcomes.
3. **MRL-07:** review/implement a source/mock plan for the [exact diagnostic proposal](public_diagnostic_design_20260921.md).
   Both repair arms receive identical diagnostics; the diagnostic-retaining context
   removal arm is not a task-only independent restart. Do not reselect public cases
   after observing private or receiver outcomes. Report remaining release fields.

MRL-05/06 retain their existing combined one-CPU 20-minute source/mock cap; MRL-07
has its distinct one-CPU 20-minute source/mock planning cap. These are not renewed
by this response. No new reference/candidate/sandbox or model collection, downloads,
paid services, pool expansion or third receiver is released here. If a cap was
exhausted, publish the partial work and a specific bounded continuation need.
Proceed with already authorized work; do not send routine scientific choices back
to the owner. The lead owns the final scientific release and prospective policy
validation design. Record a concise result or blocker in a commit; that suffices
for communication. Current progress 51%, unchanged; no new efficacy evidence and
not submission-ready.
