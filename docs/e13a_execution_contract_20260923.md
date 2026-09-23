# E13a execution contract after connected-path review

This contract describes one prospective development run. Execution authority comes
from the coordinating lead's MRL-20 decision in
[mrl19_review_mrl20_20260923.md](mrl19_review_mrl20_20260923.md), conditional on its
source, runtime and shared-host gates. The release manifest supplies bindings; its
zero-authority fields correctly do not grant permission by themselves. No E13a
model or candidate execution is claimed by this document.

## Scientific target and fixed inputs

Compare the diagnostic-plus-R1-instruction restart package with bare task
resampling (`FRESH`) at five fixed E12 public-fail checkpoints: `mbpp/842`,
`mbpp/288`, `mbpp/863`, `mbpp/966`, `mbpp/652`. Each receives six new draws per arm:
R1 replicates 2–7, FRESH replicates 0–5, with distinct seed keys and no E12 seed
collision. Both branches are included with probability one; the 12 balanced
five-root blocks determine scheduling, not randomized treatment assignment.

The descriptor `experiments/landmark/e13a_stage.json`, request plan
`results/e13a_request_plan_20260922.json`, and five-root `e13a_release` package
are binding. Task/specification rows and assertions are unchanged E12 bytes;
configuration hashes and caps are rebound to the five-root stage. Dispatch uses
only the frozen public diagnostic to select checkpoints, not private outcomes.
There is no new initial-answer or public-diagnostic phase and no fitting or split
selection. These are previously examined development roots with unresolved family
independence; no untouched test-set or population-policy claim is possible.

The endpoint remains the frozen private-suite-plus-format score. No favorable
block selection, alternate extraction, additional public scoring, pooling with
E12, replacement seeds, new roots or outcome-based stopping is allowed. Report
five root contrasts and their equally weighted finite-checkpoint mean. Any missing
assigned primary grade suppresses the primary point contrast; finite binary
completion bounds are reported, with available-case summaries secondary. The
bounds are not confidence intervals. A tie or six uncertain draws does not prove
futility. This follow-up neither isolates diagnostic information from instruction
nor validates a selected prompt policy against the project's five-point useful-gain
threshold; that requires the separate independent-policy design.
The precision/stopping rule here is fixed collection of six draws per arm at each
checkpoint, with no interim efficacy/futility test and no claim of achieving a
confidence-width target. Even a descriptive contrast above 0.05 does not authorize
policy or generator advancement; the five-point useful-gain rule remains a gate
for separately frozen independent validation.

## One numerical allowance

| Resource | Maximum for this one run |
|---|---:|
| Receiver generation attempts | 60, no retries |
| Reserved completion tokens | 30,720 (512 per attempt) |
| Setup metadata/template HTTP attempts | 50, at most 10 seconds each; 42 renders; no retries |
| Collection metadata HTTP attempts | 31, at most 10 seconds each, further clipped by remaining time |
| Generation smoke calls | 0 |
| Containment payload starts | 9 |
| Private reference/control starts | 10 |
| Private candidate starts | 60 |
| Total isolated starts | 79, including containment |
| Public-check starts | 0 |
| Setup through refreeze | 600 seconds |
| Collection | 480 seconds |
| Private grading | 300 seconds |
| Analysis/report preparation | 300 seconds |
| Contiguous outer limit | 2,700 seconds from setup initialization |
| Paid services, installations or downloads | $0; none |

Counters are maxima, not expected counts. Caching and pre-execution format
rejection can reduce candidate starts without dropping assigned slots. Count
failed starts, unknown usage and missing grades explicitly. Nine attestation
starts are charged once to the total; the grader imports their receipt rather than
rerunning them. Historical ledger 333/412 is preserved: the new allowance is
explicit and does not borrow unused E12 capacity.

The same Qwen2.5-3B Q4_K_M receiver, model SHA256
`626b4a6678b86442240e33df819e00132d3ba7dddfe1cdc4fbb18e0a9615c62d`,
26 pinned build files, sampler and state remain required. Launch shape is
`-ngl 99 -np 4 -c 32768 --jinja`, loopback port 8193, with the frozen media marker.
Receiver guards run at collection preflight, before each balanced block and at
postflight. This answers the worker's guard-frequency question: preserve the 12
block checks; no new per-call metadata sweep. Guards detect deviations at those
checks, not arbitrary undetected changes between them. Exclusive ownership and
the fixed request law remain required.

## Actual window and freeze

The old E12 window and attestation are expired. The unagreed September 24 placeholder
has no standing. Obtain the earliest feasible mutually accepted fresh window and
an explicit prior-job release; verify current resources on the actual worker host.
No lease follows from silence, an idle port or historical peer reports. Preserve
other projects' valid jobs. The existing launcher still requires at least 60 minutes
remaining at readiness; a 70-minute window can accommodate that gate but is not itself
a reservation. The 45-minute stage limit remains independently binding.

Commit a reservation under `docs/` with actual UTC start/end, acceptance/release
references and the **current** launcher hash. Do not reuse the historical launcher
hash: the new helper records process identity and verifies observed shutdown.
After launch, commit a separate collector ownership record under `docs/` with its
actual PID/start, receiver URL and accepted window using `validate_ownership`'s
schema. Keeping these files outside `e13a_release/` preserves its exact rebuildable
file set. Commit fresh attestation, launch and preflight/diff evidence before
dispatch. Record the resulting clean freeze SHA and check it before subsequent
phases; no mid-batch pull or source/config edits. Setup commits do not re-anchor
the stage clock or renew its 600-second budget.

`build_e13a_release.py --verify` must reproduce the release; its manifest pins the
collector, grader, analyzer, request builder, clock, launcher, preflight, diff and
containment/instrument sources. Collection requires committed byte-identical
stage/plan/package/source bindings; grading verifies the same release and the
actual collection artifacts. An independently self-consistent manifest made from
different inputs is insufficient. No `UNRESOLVED`, bypass or substituted adapter
is permitted in real mode.

## Exact phase interfaces

Run from the repository with the worker's existing `.venv/bin/python`. Below,
`RUN` denotes one new `work/e13a_<actualUTC>` directory, `RESERVATION` the actual
committed reservation under `docs/`, and `OWNERSHIP` the separate committed
post-launch PID record. Set these to the real values before execution; placeholders
are not runnable authorization. Every failure stops further dispatch; retain all
records and perform owner-specific cleanup.

Initialize once immediately before the first setup action:

```sh
.venv/bin/python scripts/e13a_stage_clock.py --run-dir "$RUN" --init --stage experiments/landmark/e13a_stage.json
```

The setup supervisor is used separately for the following commands, with the same
clock and reservation. Its form is:

```sh
.venv/bin/python scripts/e13a_stage_clock.py --run-dir "$RUN" --stage experiments/landmark/e13a_stage.json --ownership "$RESERVATION" --supervise setup -- COMMAND ARGUMENTS
```

The setup commands, in order, are:

```sh
.venv/bin/python scripts/check_landmark_sandbox.py --runner landmark --output "$RUN/attestation"
.venv/bin/python -c 'import sys; from experiments.landmark.grade import verify_attestation; verify_attestation(sys.argv[1])' "$RUN/attestation/attestation.json"
.venv/bin/python scripts/launch_own_receiver_v31.py --ownership "$RESERVATION" --out "$RUN/receiver"
.venv/bin/python scripts/receiver_preflight_mrl10.py --tasks experiments/landmark/dev_release_v2/tasks.jsonl --examples docs/public_diagnostic_examples_v1.json --base-url http://127.0.0.1:8193 --out "$RUN/preflight"
.venv/bin/python scripts/diff_receiver_snapshot_v31.py --new-preflight "$RUN/preflight" --out "$RUN/receiver_diff.json"
```

For the launch command, add `--owned-receiver-dir "$RUN/receiver"` and
`--cleanup-helper-sha256 "$LAUNCHER_SHA"` to the supervisor before `--supervise`.
`LAUNCHER_SHA` must be the `scripts/launch_own_receiver_v31.py` entry in the
committed release's `execution_source_hashes`, also pinned by the reservation.
The directory must not already exist. This allows
bounded owner-specific cleanup on a failed/timed-out launch. `--output` for the
containment checker is a **directory**, not the attestation filename. A zero exit
from the old checker/preflight does not establish success: verify the attestation
and require the diff's `passed: true` and zero validation errors. The 42 renders
use the seven historical public fixtures, not synthetic E13 outcomes.

After the actual ownership/evidence commit and freeze, collection and grading
load the existing run/stage-bound clock and enforce their own phase limits:

```sh
.venv/bin/python scripts/e13a_collect.py --real --out "$RUN" --stage experiments/landmark/e13a_stage.json --plan results/e13a_request_plan_20260922.json --release-dir experiments/landmark/e13a_release --ownership "$OWNERSHIP"
.venv/bin/python scripts/e13a_grade.py --real --collect "$RUN/collect" --release experiments/landmark/e13a_release --out "$RUN" --stage experiments/landmark/e13a_stage.json --plan results/e13a_request_plan_20260922.json --attestation "$RUN/attestation/attestation.json"
```

Analyze through the deadline-enforcing supervisor, not a check before and an
unbounded charge after the command:

```sh
.venv/bin/python scripts/e13a_stage_clock.py --run-dir "$RUN" --stage experiments/landmark/e13a_stage.json --supervise analysis -- .venv/bin/python scripts/e13a_analyze.py --grades "$RUN/grade/grades.jsonl" --stage experiments/landmark/e13a_stage.json --out "$RUN/analysis_report.json"
```

The shared clock rejects missing/wrong-run/wrong-stage clocks, widened caps,
overlapping phases, and an unfinished phase receipt from an interrupted process.
It preserves the original outer anchor and phase consumption. There is no implicit
resume/reset allowance. The `--check` and `--charge` commands remain bookkeeping;
they are not an execution supervisor.

## Shutdown, failure evidence and delivery

Stop the owned receiver as soon as collection is finished, and on every failure,
using its new launch record:

```sh
.venv/bin/python scripts/launch_own_receiver_v31.py --out "$RUN/receiver" --stop
```

The helper compares the recorded process birth/command identity before signalling,
uses bounded TERM/KILL only for that identity, and records observed disappearance.
It does not invent an unavailable exit code. Never signal another project's
process or infer shutdown from a stop-request timestamp. The generic supervisor
controls its child process group; a detached receiver requires this separate
cleanup. An abrupt host failure or SIGKILL before a launch receipt can still leave
execution state unverified. Report that state and reconcile the owned process;
do not start another receiver or reset a clock. Safety cleanup remains necessary
even after a cap failure; report any cleanup overrun as a deviation, never as a
renewed work allowance.

Deliver the immutable 60-slot assignment/call/grade records, durable prestart and
result ledgers, all output checksums, phase clock, attestation, source/config/model
and ownership pins, launch/preflight/diff, analysis and observed shutdown receipt.
Report attempted/completed/failed/missing separately; actual prompt/completion
usage including unknowns; reserved tokens; containment/control/candidate starts;
setup/collection/grading/analysis/cleanup runtime; metadata requests and $0 spend.
A failure or interruption is retained evidence, not an invitation to retry.
Publication, worker acknowledgement, actual execution and lead validation are
separate states. E13b, any public-score supplement and larger generators remain
outside this contract.
