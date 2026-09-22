# E12 v3 independent implementation review

Reviewed `e518cc146c40e7a1c55c7c20b9f190576a656aff`, with v3 source introduced at `9d4a1f2`, against `docs/e12_bundled_release_20260922.md`. Scope: new diagnostic serialization, committed package guards, missing/failure accounting, limits and mocked orchestration. This review performed no model, receiver, sandbox payload, reference, candidate or control execution and made no implementation changes.

**Decision: accept the reviewed implementation for the existing conditional E12 release.** No new collection blocker was found. The existing ownership, runtime, frozen-source and budget gates still govern; passing those gates does not require another approval round.

## Verified behavior

- `diagnostic.py:74–128,191–240` preserves bounded strings, booleans, tuples and nested lists/tuples as canonical Python-literal strings. Boolean and integer representations stay distinct; pass/fail deliberately follows the frozen Python `==` endpoint, including `True == 1`. `public_check.py:294–342,368–432` uses the same display rule in the generated harness and parent-side checks. No candidate object is evaluated by this source review.
- Independently exercised **154 pure serialization controls** across all fourteen released public examples, including their expected values, wrong values, None, booleans, tuples, nested values and bounded ASCII/Unicode/backslash strings. Canonical JSON round-trips and public-case binding checks passed. The largest resulting complete diagnostic message was **1,264 bytes**, below the 2,048-byte cap. These are synthetic serializer checks, not receiver observations.
- All committed package hashes, grading source hashes, config digest, grading-contract digest and retained root order match. The actual v3 manifest passes the committed-path/HEAD-byte guard. The verified manifest bytes supply the grading limits and diagnostic schema (`study_adapter.py:413–540,611–635`), rather than a subsequently re-read manifest supplying different limits.
- The v3 mocked A→B→C→D→E path passes using the real fourteen-task package. It checks 154 cumulative receiver-call slots, 78,848 reserved completion tokens, fourteen public-executor slots and the **182-start / 600-second** private-grading ceiling. The generic private ceiling remains 200 starts. The released total is 42 validation + 14 Phase B + 182 Phase D = 238 additional starts; cumulative authority is 412.
- Continuation records remain bound to initial artifact hashes and the exact public cases rendered in the initial prompt. N1 and S1 share diagnostic bytes. Initial-output failures retain every assigned continuation as unavailable, without dispatch or conversion to a quality zero (`collect_diagnostic.py:451–497,516–540`). Mixed diagnostic schemas are refused; the final input adapter enforces the release's declared schema.

## Tests and limits

The focused ten-file source/mock suite completed with **411 passed and 2 failed in 2.20 seconds**. Both failures are the previously identified legacy E2 fixture's worker-specific absolute paths: deterministic fixture reconstruction on this checkout differs, and its worker private-spec path does not exist here. They are not failures of the new v3 schema/orchestration tests and do not justify rebuilding the immutable worker fixture or repeating E2. No real executor was invoked by the tests.

The suite covers missing outputs, interrupted grading records, changed or untracked manifests, wrong bindings, schema mixing and budget limits, alongside the new v3 path. Mocked orchestration validates data flow and guards; it does not independently witness the saved remote validation or demonstrate an E12 treatment effect. This review did not repeat the 42-start validation.

## One completion item within the existing release

`dev_release_v3/release_manifest.json:1023` names `study_adapter analysis-input` as command E. That command writes `analysis_input.json`; it does **not** run the contrast analyzer or save the final descriptive report. The v3 orchestration test performs an additional `analyze_diagnostic.analyze(data["roots"], data["diagnostics"], replicates=2)` call after command E.

Include that already-authorized deterministic analysis step and save its result to a new report artifact before calling the run complete. This is an output-completion item, not a collection blocker, source redesign or additional approval gate. Preserve all assigned roots, missing-outcome bounds and the released descriptive-only scope.

The lead has accepted this reporting-completeness fix and will supply the invocation in the handoff: load `analysis_input.json`, call the existing analyzer with two replicates, and exclusively create `analysis_report.json`. No collector/source edit or additional review gate is needed.

No new efficacy evidence or project-readiness credit follows from this implementation review.
