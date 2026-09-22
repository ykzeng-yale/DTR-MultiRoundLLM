# Half-hour experiment–theory exchange

Owner instruction, 21 September 2026: the experimental agent will publish results
and retrieve feedback every half hour; the coordinating scientific agent will
review on the same cadence. This updates the existing lead heartbeat, not a second
experimental job. Actual publication/review times can lag; inspect UTC timestamps
rather than assuming a scheduled run delivered evidence.

## Shared channel and ownership

Use [issue #3](https://github.com/ykzeng-yale/DTR-MultiRoundLLM/issues/3),
`COORDINATION.md`, and exact commit/run links. Experimental execution and
`docs/experiments_status.md` remain worker-owned. The lead owns scientific
decisions, integrated status and advancement. The lead should not start a duplicate
collection, overwrite a live worker report or require the owner to relay feedback.
Both workstreams commit as Yukang Zeng <ykzeng2019@gmail.com>, fetch before pushing,
preserve current ancestry/concurrent work, and integrate directly on main.

## What the worker should publish

For new work, give the request ID; actual UTC update time; accepted/running/
completed/blocked/superseded state; frozen protocol and code commit; immutable run
or partial-snapshot identifier; assigned/completed/failed/missing counts; actual
calls, tokens, runtime and cost against the cap; checks and deviations; one concrete
scientific question or blocker; and the next bounded action. Clearly label planned,
synthetic, reused-data, fresh exploratory and confirmatory evidence. A started job
is not a completed result. Do not expose credentials or private answer keys.

Publish completed batches and material failures promptly, without waiting for a
large polished report. For a running confirmatory batch, publish progress and
execution health; release outcome analyses only under the frozen analysis/stopping
rule. Frequent monitoring does not authorize outcome-driven tuning, repeated
significance testing, outcome-dependent enrollment or unplanned stopping. Preserve
every attempt and failure; use coherent immutable snapshots rather than half-written
files. Do not interrupt a valid frozen run just to make a status commit.

## What the lead returns

Prioritize new result batches and direct scientific questions. Record separately
the exact last-seen worker commit and the independently checked evidence version.
Main integration alone is not validation. Return one explicit decision:

| Decision | Meaning |
|---|---|
| Proceed | The named next bounded action satisfies its stated conditions. |
| Repair | Correct a specified implementation, measurement or interpretation defect, preserving original evidence. |
| Hold new stage | A named unresolved condition blocks a new stage; state what artifact would resolve it. |
| Inconclusive | Evidence does not distinguish the competing explanations; state the next justified discriminating check or retain the result. |

Each decision states target/hypothesis, evidence type, what was independently
checked, rationale, request ID, owner, concrete artifact and acceptance criteria.
Check support, information timing, measurement, matched comparators, total cost,
power and inference before assigning failures to theory or proposing a new target.
Publish material feedback in the current review cycle. An unchanged cycle needs
the requested user progress report, not a repeated issue comment or no-op commit.
Do bounded theory/manuscript work when useful, instead of rerunning passed tests.

## Initial request register — preserved history

These IDs organize the existing [J1–J4 decisions](experimental_status_rulings_20260921.md);
they do not reopen them or authorize extra inference. Worker acknowledgement is
pending as of lead review of main 630b6e4 and worker status 4ba4abf/af38c9d.

| ID | Priority / owner | Next action and acceptance criterion |
|---|---|---|
| MRL-01 | Now / experiments | Acknowledge J1–J4 and correct the live status timestamp, E0 links, 230-task interpretation and power/no-harm wording. Return the exact correction commit and disposition for each ruling. |
| MRL-02 | Now / experiments | Review the seven existing public/private contracts and propose a versioned 402 repair retaining p=1; preserve exclusions and return source bindings, unresolved defects and intended control outcomes. Source review is not executed validation. |
| MRL-03 | Now / experiments | Return an available isolated runtime and receiver specification, model/backend versions, shared-hardware availability and resource window; distinguish inspected resources from functioning validated services. |
| MRL-04 | After 02/03 / experiments + lead | Prepare the exact bounded same-prefix freeze and obtain a scientific release decision against the already declared gates. Independent policy validation is a later separate frozen stage. |

MRL-01–03 together retain the preceding assignment's cap: one CPU worker,
30 minutes, zero model or candidate/reference executions, no installations, $0.
This is not a renewed allowance each time the scheduler checks. Report unfinished
items at the cap and request a concrete continuation if needed. Existing user
authorization covers this source work; owner permission is not its blocker.
Actual reference execution/model collection needs its separate complete committed
protocol, runtime validation and numerical cap. Preserve shared-hardware jobs.

## Reporting contract

The lead's existing heartbeat is now active every 30 minutes. Read
`docs/readiness.md` and `docs/progress_current.json`; report overall milestone
completion, change, independently completed/checked work, blockers and next
milestone after every check, even unchanged. The September 21 baseline was 49%; current reviewed progress is **55%**, per the fixed rubric.
Changing coordination frequency earns no research-completion credit. No new
efficacy evidence is supplied here; the full project remains not submission-ready.
Measurement/receiver release, fresh prompt data and independent policy validation
remain the principal milestones. The fixed rubric and scientific gates are unchanged.

## Recovery rule for an unanswered exchange

After two consecutive checks without acknowledgement or a promised delivery, the
lead must issue one recovery escalation in issue #3 and COORDINATION.md using the
existing request IDs. Request the actual processed commit, scheduler tick, current
run/lease or unpublished artifact, and a concrete blocker. File-based replies are
sufficient; do not require an issue-comment token. Verify receipt at the next
actual review. If still unavailable, explicitly surface the delivery problem and
the missing worker routing detail to the owner instead of repeating only a stale
percentage. Do not resend unchanged escalations or create another worker.

Continue useful unblocked lead-owned work with explicit scope and validation;
worker silence does not block every manuscript or source-review task. Preserve
execution ownership, original caps, running batches and scientific release gates.
Publication, acknowledgement, execution and independently accepted evidence are
separate states. The September 21 recovery is recorded in COORDINATION.md.

## Historical queue after development review and diagnostic design

MRL-01 acknowledged at 12:40:51 UTC; the communication recovery is closed. MRL-02
measurement artifacts were reviewed; MRL-03 runtime was delivered with receiver
guard repairs now tracked under MRL-06. MRL-04 produced the preserved development
pilot, not a release for further collection. See the scientific ruling at 07fa225.

MRL-05/06 are the pending sizing/interpretation and receiver-contract repairs,
sharing one CPU, 20 minutes, source/mock work only, $0. MRL-07 follows them: inspect the
[exact public-diagnostic proposal](public_diagnostic_design_20260921.md) and fixtures,
return implementation plan and missing freeze fields; one CPU, 20 minutes, no model,
reference/candidate/sandbox execution or installs, $0. These are distinct bounded
source assignments, not recurring budget renewals. Record acknowledgement, UTC and
processed SHA. The lead owns the scientific release and independent policy design.

## Current queue after independent review of e8b10b0

MRL-05/06 deliveries were received and independently reviewed; source guard and interpretation repairs remain. MRL-07 plan was accepted with all15 fields and J5/J6 decided at89f6054. **MRL-08 source/mock implementation is authorized**, with its original one CPU/30-minute/$0 cap and no model or sandbox execution. Receipt of MRL-08 is verified by1b24e56 at18:26:06 UTC; the worker reports implementation running under the original cap until18:56:06 UTC. The single recovery is closed for receipt; completion and independent validation remain pending. The historical queue above must not be read as awaiting another acceptance of MRL-07. No cap is renewed by monitoring.

## Current queue after MRL-09 review

MRL-08/09 source/mock deliveries are received and reviewed. MRL-10 now authorizes the static release build, validation-plan repairs and bounded nongenerating preflight under the exact caps in docs/mrl09_independent_review_20260921.md. E1–E8 execution and E11 model collection remain unreleased. This supersedes the older current-queue paragraph; no further MRL-07/J7 decision is pending.

## Current queue after MRL-10 review

MRL-10 static package/preflight is reviewed. MRL-11 releases one ordered E1–E8 instrument-validation bundle on the intended host:77starts maximum,20minutes,oneCPU,$0,zero model calls. Exact conditions and stop rules are in docs/mrl10_review_mrl11_release_20260921.md. Earlier HOLD paragraphs are historical. E11 collection remains unreleased; no receiver ownership agreement exists yet.

## Current queue after MRL-12 review

MRL-12 source/mock integration is independently reviewed. MRL-13 conditionally releases one bounded E11 development run after the real receiver agreement is committed and existing live guards pass. Until then HOLD. See `docs/mrl12_review_mrl13_release_20260921.md` for exact bounds; earlier queue paragraphs are historical.

## Current queue after E11 delivery

MRL-13 completed and recovery closed. MRL-14 permits source/mock compilation-classification repair and prospective sampling proposal only; see `docs/e11_lead_judgment_20260922.md`. No new real collection or regrading is released.

## Current queue after MRL-15 review

MRL-15 accepted in scope. MRL-16 is the single bundled conditional preparation/validation/collection authority in `docs/e12_bundled_release_20260922.md`:14adapted roots,154calls,238new starts, fresh receiver window, exact committed gates, no backfill or retries. No additional lead-review round if all named conditions pass. Prior HOLD paragraphs are historical.
