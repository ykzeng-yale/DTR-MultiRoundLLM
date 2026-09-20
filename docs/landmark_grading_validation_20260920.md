# Private landmark grading: implementation validated, execution blocked

**20 September 2026.** The offline adapter is implemented and passes 23 mocked tests. Host containment has **not** passed. No benchmark reference, negative-control program, generated candidate, or receiver inference was executed. The adapter emits missing outcomes when execution is unavailable; it does not convert infrastructure failure into wrong-answer labels.

## What was actually attempted

The existing common sandbox denies execution under `/opt`, which includes this environment's Homebrew Python 3.14 interpreter. All nine controlled canary launches failed at `sandbox-exec` with exit code 71 before their Python payloads started. Static inspection also found that its default-allow filesystem policy does not deny every user-writable location outside HOME and the selected temporary directories. The planned `/Users/Shared` marker check **did not execute**, so this latter concern remains a static finding, not a demonstrated write escape. The common runner was left unchanged.

A separate `experiments/landmark/sandbox.py` uses a default-deny profile with explicit interpreter/runtime/run-directory reads, exact interpreter execution, own-directory writes, network denial and fork denial. Its controlled startup attempts aborted with signal 6 and no payload marker. Removing the attempted address-space limit did not resolve startup. The same profile was also tried with the available system Python 3.9.6 and Homebrew Python 3.12.10 and 3.13.11, resolving each interpreter path; all three failed before payload execution. No broader permissions were granted to obtain a passing result. The new helper is therefore **an unvalidated restricted-runner implementation**, not a certified usable sandbox.

| Preserved check | Runner launch attempts | Python payloads started | Summed runner wall time |
|---|---:|---:|---:|
| Existing common sandbox | 9 | 0 | .075793 s |
| Initial strict canary suite | 9 | 0 | .163824 s |
| Strict startup follow-up | 1 | 0 | .020480 s |
| Three alternate interpreters | 3 | 0 | .037660 s |
| Final strict canary suite | 9 | 0 | .123184 s |
| **Total** | **31** | **0** | **.420941 s** |

These are elapsed runner durations, not direct CPU measurements. The old runner calls its subprocess launch `executed=True`; that does not mean the canary program started. `results/landmark_grading_validation_20260920/execution_accounting.json` makes this distinction explicit. Harmless host-created marker directories were removed. Loopback listener setup used no external endpoint. External spend was $0.

Because startup failed, the requested runtime write/read/network/process/fork/timeout/cleanup properties remain **unvalidated**. They must not be inferred from absent output. Even a future passing suite would demonstrate only the controlled cases, not a general escape proof, resource-exhaustion defense, kernel isolation, or immunity to changes in the runtime. The timeout test verifies that its launched process has been reaped; when fork is denied, it does not independently validate cleanup of a descendant that was never created.

## Adapter contract and failure semantics

`experiments/landmark/grade.py` is entirely separate from collection. It imports no model client, does not modify the collection, and writes private execution diagnostics only to a new grading directory. The scientific endpoint is private-test quality of each prescribed continuation under reliable execution of the frozen receiver/decoding law. It is not deployment reliability and is not a mean conditional on outputs being observed. Missing/unattempted receiver continuations and unavailable grading retain unknown outcomes. The analyzer's missing-outcome bounds must be interpreted under that target; they are not, by themselves, population confidence limits.

Before grading, the adapter checks immutable collection checksums and assignment accounting, recomputes each artifact's output hash, and binds every output to root, arm, replicate and the exact grading-contract hash. Emitted grade JSONL is validated with the existing analyzer. Missing output remains `outcome: null` with its reason. A malformed or empty *produced* program may receive zero under the frozen format contract; genuine executed test rejection and an executed candidate timeout receive zero. A sandbox startup failure without a randomized program-start marker receives a missing outcome, even after an earlier reference happened to run successfully.

The accepted extraction format is raw Python or exactly one Python/untyped code fence. **That format must be stated in the public task instructions before any real collection.** The seven source-audit candidates do not yet satisfy this frozen public-format contract. Multiple valid-looking blocks must not be penalized under an unstated formatting rule. This is a declared parser/test endpoint, not universal semantic correctness.

Each private task spec has exactly:

```text
root_id
public_task_sha256
entry_point
public_assertions
private_assertions
preamble
reference_code
negative_controls = [{code, rationale}, ...]
```

The public-task hash binds the exact collector task record, including family, prompt and public context. The private assertions must be nonempty standalone assertions that exercise the named entry point. Duplicate assertions, normalized public/private overlap, and verbatim private assertion exposure in public information fail validation. These syntactic checks cannot establish semantic non-leakage, benchmark independence, specification validity, or discriminatory power; task review remains necessary. The adapter never silently constructs a new public test from an old hidden test or changes the scoring split.

Each root must first have a passing positive reference and at least one explicitly frozen known-wrong control with a rationale. Every negative control must actually execute and yield zero; a parse rejection, timeout before payload start, unavailable canary, or unavailable environment cannot stand in for demonstrated test discrimination. Candidate grading is blocked for that root if these measurement checks fail. Passing selected wrong controls would still not prove adversarial integrity or general test coverage.

The existing static integrity gate can flag legitimate constructs such as `__iter__`, `__eq__` or `setattr`. Its non-parse flags therefore produce `integrity_review_required` and a missing outcome rather than an automatic zero. No unannounced restriction to top-level function definitions is imposed: an assigned callable such as a lambda proceeds to execution, where the declared interface is tested. The common integrity module and historical outcomes remain unchanged.

A private sentinel, static checks and a corruption canary provide limited endpoint checks. Candidate code and assertions still execute in one Python process, and code can potentially inspect or manipulate its execution environment. **Containment and grading integrity are separate questions.** Neither sentinel visibility nor rejection of ordinary wrong controls proves resistance to malicious verifier exploitation. The contract hashes the private specs, grader, sandbox and integrity sources. Deterministic behavior is an assumption, with one grade reused for identical artifacts within a root; stochastic grading needs a separately declared contract.

## Fail-closed gate and executable checks

Execution is off by default. `--execute` additionally requires a successful canary attestation from the preceding 24 hours, bound to the current host, OS, exact interpreter binary, runner source, profile and checker source. Every required check must have actually started and passed. Missing, stale, mismatched, incomplete and failed attestations block grading. A nonexistent attestation still yields complete missing-grade rows instead of crashing after partially writing results.

The final adapter unit suite has **23 passing tests** (`final_grader_tests.xml`). It covers separation/bindings, empty/overlapping/vacuous tests, required wrong controls, correct reference gates, accepted wrong-control detection, unavailable outcomes, startup failure, static-flag review, callable interfaces, budgets, identical-artifact caching and collection corruption. An earlier integration run with the collector passed 42 tests; that preceded the final callable-interface test. These tests mock the runner and make **no program-execution or benchmark-quality claim**.

A separate internal reviewer inspected final grader source SHA-256 `289447c007916ba2938c6681d75ecd1da61b584608665a46f2d47925abed7f36`, reran the 23 mocked grading tests and found no blocking scientific grading defect. The coordinating agent independently ran the integrated project suite: 121 tests and two subtests passed in 1.53 seconds. These checks do not establish semantic evaluator accuracy or runtime containment availability.

The final blocked smoke artifact is `blocked_grade_mock_collection_v2/`, with `blocked_grade_mock_outputs_v2/` and `blocked_grade_mock_analysis_v2.json`. One synthetic root has four mocked outputs; all four grades remain missing because the real containment attestation failed. There are zero grading executions, quality bounds [0,1], and contrast bounds [−1,1]. Earlier diagnostic artifacts are retained, not overwritten.

Reproduce the non-executing tests:

```sh
uv run --extra dev pytest -q tests/test_landmark_grader.py
```

Repeat the controlled host check into a new directory only:

```sh
uv run python scripts/check_landmark_sandbox.py --runner landmark --output results/NEW_HOST_CANARIES
```

An eventual private grading run first freezes the contract hash into the collector configuration, then supplies separately stored private specs and a valid attestation. No model run or candidate execution is authorized by the existence of this adapter. Current blockers are a working verified isolation backend, a reviewed public format and private endpoint, source/family adjudication, and positive/negative-control validation. The source-audit workstream's seven retained candidates remain **unfrozen and unevaluated**.
