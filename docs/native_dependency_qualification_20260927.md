# Numerical dependency qualification — 27 September2026

Codex direct implementation. This resolves the specific inability to import plotting/numerical dependencies under the strict sandbox. It is runtime qualification, not a benchmark measurement or receiver release. Original common/landmark runners and all historical environments remain unchanged.

## Implemented boundary

The new [bundle validator](../experiments/prompt_choice/dependency_bundle_v1.py) inventories regular files only, refuses symlinks and `.pth` site hooks, caps the tree at512MiB/20,000 files and hashes paths, sizes and contents. The [versioned sandbox adapter](../experiments/prompt_choice/dependency_sandbox_v1.py) verifies the expected tree before and after execution, adds only a read allowance for that tree to the unchanged default-deny profile, and explicitly inserts that path under `-I -S`. It does not run site hooks or enable the project repository. It requests one numerical thread, noninteractive Agg plots and a run-local font/config location; candidate code can change environment variables, so the thread request is not a hard adversarial thread cap.

Before/after hashing detects persistent mutation but is not a snapshot or an OS barrier against another privileged/same-user parent process mutating and restoring files during execution. The execution contract must prohibit concurrent bundle edits. Candidate writes to the bundle are denied by Seatbelt in the controlled probe. No broad home or repository access was added.

Limits: at most1MiB source,10 wall seconds,5 CPU seconds,256KiB per captured stream and2GiB requested memory, with lower defaults. Memory is best effort and file size is per-file, not a total disk quota. The adapter retains completed_ungraded/output_limit/timeout/process_error distinctions and never interprets candidate output as a test grade.

## Actual bundle and probes

The bundle was copied from already installed distributions, without a new package download. [Complete file/version/licence inventory](../results/native_dependency_bundle_20260927.json):2,172 files,74,177,316 bytes, tree SHA256 `cf6526cb5d51da93c9181f7fbeeaf438b0f9815db5abb2aa0bbe56df0a5ece85`. It contains NumPy2.5.3, Matplotlib3.11.2 and their listed dependencies. This is a **new prospective numerical environment**, not the benchmark publisher's older dependency stack or evidence of version equivalence. Other benchmark dependencies, including pandas, are not supplied by this bundle. Tasks are not excluded for that reason.

[Import/object probe](../results/native_dependency_import_probe_20260927.json): a harmless NumPy array sum and Matplotlib figure/title complete inside Seatbelt in2.797seconds. Matplotlib reports that its font cache cannot be written because of the per-file cap; retain that warning. No reference, wrong control, benchmark assertion or model-written program was executed.

[Initial controlled containment probe](../results/native_dependency_containment_probe_20260927.json): own-run file access succeeds; repository read, dependency write and system-subprocess attempts are denied. **The five-check program exits1:** socket creation succeeds, contrary to that probe's overly strong expectation. Creating a socket is not evidence of network transmission. Do not erase this failed check or call the whole initial probe passing.

[Corrected network probe](../results/native_dependency_network_probe_20260927.json): an actual connection to a parent-owned listening loopback socket is denied with PermissionError in0.0235seconds. This verifies the intended network boundary for that operation; it does not prove every networking path is blocked. Each probe leaves the bundle hash unchanged. Three synthetic starts total; zero benchmark or receiver calls.

## Validation and next scientific action

The full suite passes2,281 tests plus8 subtests in38.32seconds; fifty-three focused source tests pass across bundle validation, execution classification and feedback serialization. They cover mutations, site hooks, symlinks, caps, read-only profile construction, output saturation and pre-dispatch refusal. Runtime probes supplement rather than replace these tests. General grade integrity, test secrecy and full benchmark compatibility remain unestablished.

Next: freeze a bounded reference/wrong-control measurement audit for the already identified task628 test weakness using this exact environment, retaining both the original native suite and a separately defined semantic control. This is a measurement-development target, not an independent task sample, task-population adoption or receiver experiment. Its protocol, code/config/source hashes, prediction table, resource limits and new output directory must be committed before benchmark execution. Do not broaden dependencies or task selection based on its outcomes.

Full-project readiness **60%, change0 percentage points**. Population/measurement, full prospective freeze, independent policy evaluation and final manuscript/raw reproduction remain incomplete. Goal active, Codex-only implementation.
