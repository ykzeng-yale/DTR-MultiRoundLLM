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

## Current requests — stable IDs, no duplicate queue

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
milestone after every check, even unchanged. Current baseline is **49%, delta 0**.
Changing coordination frequency earns no research-completion credit. No new
efficacy evidence is supplied here; the full project remains not submission-ready.
Measurement/receiver release, fresh prompt data and independent policy validation
remain the principal milestones. The fixed rubric and scientific gates are unchanged.
