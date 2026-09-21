# MRL-07: implementation plan and missing freeze fields for the public-diagnostic study

> Lead audit: [MRL-05–08 decisions](lead_review_mrl05_08_20260921.md) supersede conflicting validity, guard and freeze claims below. Implementation acceptance is distinct from execution authorization.

**Experiments workstream, 2026-09-21T15:00Z start (processed `e7eb925`; proposal `1e85541`).** Source review
and static prediction only: 0 model calls and 0 reference, candidate, control or sandbox executions, $0.
This does not accept or release any collection. The lead keeps the release decision.

## 1. Fixture review: one design issue for the lead

The lead's audit found 21/21 expected values correct and zero *literal* input overlap with the v1c private
suites. I agree with both. The overlap that matters is at the level of **defect class**. I predicted each
known wrong behaviour's output on the public inputs using my own stdlib re-implementations; no stored code
ran. Record: [`results/public_checker_static_discrimination_20260921.json`](../results/public_checker_static_discrimination_20260921.json).

| root | wrong behaviour | caught by the public cases? | private boundary case built to catch it |
|---|---|---|---|
| 357 | last-element max (the natural wrong program behind the v1 suite defect) | **yes**, 357-1 and 357-3 | `[(1,2),(8,3)] → 8` |
| 402 | prime-only Lucas (the natural wrong program behind the second defect) | **yes**, 402-2 (composite 6) and 402-3 (p = 1) | `[4,2,4] → 2`, `[6,2,6] → 3` |
| 402 | original reference bug, `C[r]` without `% p` | **yes**, 402-3 `[3,0,1] → 0` | `[0,0,1]`, `[4,0,1]` |
| 378 | correct on non-empty input, `IndexError` on `[]` | **no**, all three pass | `[[]] → []` |
| all others | the 15 remaining negative-control behaviours | yes, 15/15 | — |

Public rejection is **18/19** by prediction.

**What this means:**

- **Good for the checker.** The public checker can reject nearly every known wrong program. This is the
  proposal's own precondition for claiming an informative diagnostic, although only executed validation can
  establish it.
- **Changes what the endpoint measures.** The public examples, shown to *every* initial call, now reveal the
  defect classes the v2 private boundary cases were written to hide. For 357 and 402 the private endpoint
  partly becomes "did the answer follow the shown examples". Arm contrasts stay fair because all arms,
  including STOP, see the same examples. Two things change, though: less hidden discrimination is left
  beyond the public cases, and initial correctness probably rises, leaving fewer wrong roots to repair (the
  proposal already notes an all-pass batch is possible).

**My recommendation.** Keep the cases as proposed; do not reselect. Before the freeze, add a descriptive
endpoint: *private-only failures*, meaning assertions whose defect class is not represented in the public
cases. Report it alongside the full-suite endpoint. That keeps what remains hidden visible without moving any
test across the split. The choice is the lead's. Changing the cases now would come before any new outcome,
but they were designed after v1c outcomes were seen.

## 2. Implementation plan (source + mock; nothing runs until a validation contract is released)

Collection is split into **phases** so the collector never executes code and the private boundary is
auditable:

| phase | what runs | reads | writes |
|---|---|---|---|
| A | receiver: 7 initial calls (`landmark-v2` guard) | public tasks with examples | initial artifacts |
| B | **public executor**: sandbox, public cases only | initial artifacts + public cases file | canonical diagnostic JSON per root (+ digest) |
| C | receiver: 70 continuation calls, 5 arms × 2 replicates | public tasks, initial artifacts, diagnostics bound by digest | continuation artifacts |
| D | grader: private suites | all 77 artifacts + private specs | grades |

The v2 receiver-state digest is re-checked at the A/C boundary. B cannot read the private specs; see the
freeze field below.

| module | content | mock tests |
|---|---|---|
| `experiments/landmark/public_check.py` | static format/interface classification (the grader's own parser; no execution); one sandbox start per artifact running the 3 cases in order with a per-case alarm; fresh `literal_eval` arguments per case; status classifier; payload-versus-infrastructure distinction via a start marker printed before the candidate code, as `grade.prepare_program` already does with `STARTED` | injected fake-sandbox results for every one of the 8 statuses; crash mid-case leaves later cases `unavailable` with no retry; bool/float/oversized returns |
| `experiments/landmark/diagnostic.py` | canonical diagnostic JSON (bounded, sorted keys); S1 selector; renderers for N0/S0/N1/S1/R1/STOP | golden bytes per arm; N1 and S1 carry byte-identical diagnostic messages; S1 precedence; renderer signature takes only public objects |
| `collect.py` (`landmark-v2`) | `--phase initial` / `--phase continue --diagnostics F`; arm set `diagnostic-v1`; diagnostics bound by digest | fake server: 77 planned calls; the continuation refuses unbound or changed diagnostics |
| `analyze.py` | five-arm root means; S1−N1 primary; N1−N0, S0−N0, R1−N1, each arm versus STOP; tokens per arm; executor seconds; no intervals (one unresolved family) | synthetic grades |
| `scripts/build_dev_release_v2.py` | public tasks with the examples rendered in; **rebinds private specs to the new `public_task_sha256`**; new grading-contract digest | builder determinism; the private assertions are byte-identical to v1c's |

## 3. Missing freeze fields (none is in the proposal yet)

| # | field | my proposal |
|---|---|---|
| 1 | Exact rendering of the public examples in the initial prompt | `Public examples (inputs and required outputs):` followed by one line per case, `entry_point(args) == expected`, in fixed case order, with args printed by `repr` from `literal_eval` |
| 2 | Diagnostic message role, header, serialization | a `user` message; header `Public diagnostic: your previous answer was executed on the public examples.`; JSON `sort_keys`, `separators=(",",":")`, `ensure_ascii=False`; total cap 2,048 bytes |
| 3 | Returned-value policy | include only `int` (not `bool`) with \|v\| < 10¹⁸, or a list of ≤ 16 such ints; otherwise `returned: null`, `value_kind: "unsupported"` |
| 4 | Pass semantics | Python `==`, the same as the private `assert f(x) == y`, so `7.0` passes `7` here exactly as it does privately; an exception raised inside `==` counts as `program_exception` |
| 5 | Status definitions and precedence | artifact-level first: `format_error` (grader parser), then `interface_error` (entry point missing, or `inspect.signature().bind` fails); then per case: `timeout` > `program_exception` > `output_limit` > `wrong_value` > `pass`; `unavailable` only when the harness sentinel shows the payload never started |
| 6 | Exception exposure | status only. A class-name allowlist (IndexError, ZeroDivisionError, …) would add information to both repair arms; that is a lead choice, and I propose not |
| 7 | Limits | per-case alarm 2 s; process wall 10 s; the existing sandbox memory/output caps; stdout discarded |
| 8 | Private-access boundary | public executor read-allowlist excludes the release directory and `work/`; a canary tries to read the private spec path and must fail |
| 9 | Executor-start table (≤ 200) | see section 4: 137 starts with one start per artifact |
| 10 | S0 strings | `TARGETED` pinned by digest. Checked: the AST digests of `SYSTEM`, `GENERIC` and `TARGETED` are identical at `335a6de` and at HEAD |
| 11 | Seeds | independent per `arm:replicate`, as in v1. Common random numbers across *different* prompts do not couple outputs after the first differing token, so no coupling benefit is claimed |
| 12 | Receiver | `landmark-v2`: state digest snapshot immediately before release; `sampler` = the observed defaults |
| 13 | Consecutive user turns | N1/S1/R1 send the diagnostic and the instruction as two `user` messages; verify the rendering with `/apply-template` (no generation) at the freeze |
| 14 | New public-task binding | rebind specs, new contract digest, and re-run the overlap auditor (PASS/HOLD) on the final specs |
| 15 | Added descriptive endpoint | private-only failures (section 1), if the lead accepts it |

## 4. Isolated-executor start table (proposal ceiling 200)

| use | starts |
|---|---|
| Public-instrument validation: 7 references × 1 start (3 cases each) | 7 |
| Public-instrument validation: 17 negative controls × 1 start | 17 |
| Status-category fixtures (wrong value, exception, timeout, output limit, crash sentinel) | 5 |
| Private re-validation for the new binding: 7 references + 17 controls | 24 |
| Public diagnostics on the 7 initial artifacts (format/interface errors execute nothing) | ≤ 7 |
| Final grading: 7 STOP + 70 continuations | 77 |
| **Total** | **≤ 137** |

One start per *case* would need 199 and leave no margin. That is why I propose one start per artifact with
per-case alarms, matching the private grader's own one-process-per-candidate semantics.

## 5. Status

The plan is complete. The next step, implementing the modules above under mock tests, starts on the lead's
acceptance; no MRL-07 cap remains for it. No collection, execution or pool change is proposed. Progress is
unchanged: descriptive development only.
