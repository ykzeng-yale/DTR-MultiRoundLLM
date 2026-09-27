# Source-separated measurement decision and qualification

Codex lead, 27 September2026. ACT-01/02 development; no evaluation population adopted.

## Settled decisions

Use the Complete prompt variant for the proposed BigCodeBench source contract because its code prefix/signature is part of the original task. Do not silently supply imports from tests. A contradiction among signature, prose and examples is an unresolved specification, not a rule to prefer whichever passes the reference. Any explicit resolution requires a new task-contract version and complete admission ledger before receiver outcomes. Instruct variants remain separately recorded; this choice is a proposed versioned target, not retrospective relabeling of prior experiments.

The original native-test score Z remains a descriptive benchmark outcome. It is not semantic correctness Y, and the first-test-public split remains unreleased. A native same-process Python test suite cannot supply the claimed source separation: arbitrary candidate code can inspect the interpreter and change test state. A distinct process around the whole suite protects the host but not the grader from the candidate. A random success marker in candidate-visible code does not authenticate the verdict. These are architectural limits, not measured benchmark-wide hacking rates.

The new development boundary keeps expected values and comparison code in the supervisor. The candidate process receives only its own source, entry point and invocation inputs. Its output is an untrusted observation; the supervisor checks syntax, type, bounded size and the frozen expectation. It never imports candidate objects, unpickles them or runs model code. JSON-only output with an added `passed` field does not count as success. Missing/malformed output, abnormal process exit, output saturation and timeout remain INCOMPLETE in this prototype, not automatically incorrect semantic outcomes. A valid observation unequal to the frozen expectation is FAIL. Any policy feedback integration must bind an explicitly public case and emit only the existing status-only strings; this prototype is not yet wired to collection.

This resolves verdict authority for a restricted observation interface, **not** arbitrary native unittest compatibility. JSON values cover scalars and structured lists/mappings, but do not certify class identity, matplotlib objects, side effects, mocked I/O, stochastic laws or generic semantic correctness. A candidate can forge a serialized observation; it must still match the external expected value, but that does not prove an internal object or operation existed. Do not admit only JSON-compatible tasks and call them the original whole-source population. Broad task-specific observation adapters and a versioned endpoint decision remain required. The historical same-process grader and all prior outcomes stay unchanged.

## Frozen synthetic qualification

Eight lead-authored synthetic cases, no third-party benchmark source or receiver calls: correct and wrong arithmetic; forged PASS JSON; exit0 without observation; stack search for expected values; read of a harmless parent-private canary; saturated stdout; infinite loop. Expected statuses: PASS, FAIL, INCOMPLETE, INCOMPLETE, FAIL, FAIL, INCOMPLETE, INCOMPLETE. One fresh existing Seatbelt sandbox per slot, CPU1second, wall2seconds, requested best-effort memory256MiB, stdout/stderr caps64KiB each, total qualification30seconds, one CPU process at a time, $0 paid services. Existing runner's file-size cap is per file and memory limit is best-effort; this is not qualification against all adversarial disk/memory exhaustion.

Freeze the plan, observation module, runner and source dependencies in Git before these starts. Refuse reused output directories. Preserve every failure; no retry/replacement or extension within this run. `scripts/qualify_observation_boundary_20260927.py --freeze <commit> --out <new directory>` records process evidence and statuses. Focused mocked tests are preparation, not evidence that OS isolation worked. The live qualification tests its finite declared controls only.

ACT-01 now has an explicit specification and outcome decision; broad native measurement remains unresolved rather than hidden behind code tests. ACT-02 proceeds with the frozen qualification and the independently needed pinned-receiver resource calibration. Population/family and grading-validity work remains necessary before an efficacy trial.

Full-project readiness60%,delta0; population/measurement, full freeze, independent policy evaluation and final manuscript/raw reproduction remain incomplete. No efficacy claim follows.

## Executed qualification outcome

Freeze5e44768 completed all8 slots in1.285seconds; all predicted statuses matched. Correct observation passed, wrong observation failed, forged verdict and exit0-without-observation remained INCOMPLETE. Stack and parent-private-file controls returned the wrong fallback, not the hidden expected value. Saturated output was incomplete; the infinite loop ended on SIGXCPU(-24), so it is a CPU-limit observation rather than a wall-time timeout. The saved raw records were reconciled by the lead without a rerun; this is not an independent reviewer claim.64 focused affected tests pass. No receiver calls or benchmark tasks in this qualification, and no claim that all possible attacks are covered.
