# Why progress has been slow: diagnosis and changes (experiments workstream)

23 September 2026. Requested by the owner. Every timing below is recomputed from git commit timestamps by
`scripts/efficiency_diagnosis.py` → `results/efficiency_diagnosis_20260923.json`; nothing is estimated from memory.

## Bottom line

Across eight rounds (MRL-18 to MRL-25, about fifteen hours of wall clock) the project collected new data exactly
**once**: E13a, 60 receiver calls taking about 142 seconds of receiver time. Every other round was preparation or
repair. When everything is running, a round is fast. The time is lost in three places, and **the largest
recurring one is mine: every delivery I shipped contained defects that the lead's review then found**, and each
one costs a full extra round.

## Where the time went

| Round | Kind | Acknowledge | My work | Lead review |
|---|---|---:|---:|---:|
| MRL-18 | source/mock prep | 6.6 min | 12.0 min | 28.0 min |
| MRL-19 | source/mock: E13a real path | 1.6 min | 21.4 min | 34.6 min |
| MRL-20 | **E13a execution, 60 calls** | 1.2 min | 27.7 min | 15.9 min |
| MRL-21 | archive closure + corrections | 4.5 min | 7.9 min | 28.7 min |
| MRL-22 | frame review, ranks 21–40 | 2.2 min | 11.4 min | 27.8 min |
| MRL-23 | E14 package | 11.8 min | **462.7 min** | 13.5 min |
| MRL-24 | E14 repair | **95.2 min** | 11.3 min | 9.2 min |
| MRL-25 | E14 repair | **≥ 41 min, unacknowledged at writing** | — | — |

Separately, the lead's review of E12 took **20.7 hours**.

## Causes, ordered by how much I control them

### 1. Defects escaping into every delivery — my design, and the biggest lever

Every round from MRL-18 onward was, in whole or part, a repair of my previous delivery. What the lead's reviews
found in my work:

- **MRL-18:** my analyzer computed its contrast from available grades only (wrong estimand); a variance claim of
  mine was wrong; "impossible" overstated.
- **MRL-19:** seven blockers my mock tests missed — a stale 14-root config hash that made the real freeze check
  refuse, collector/grader schemas that did not match, a grading CLI that refused every real call, starts and
  grades that could vanish after interruption, and a clock that could restart.
- **MRL-20 (E13a):** a log missing from the delivery, and my rebase rewriting the recorded freeze commit.
- **MRL-21:** the proposed E14 roster was at the private-score ceiling (I caught this myself, but only after
  proposing it), and a sizing claim of mine was false.
- **MRL-22:** a false "protected source" claim, and an overreach calling the fence instruction "refuted".
- **MRL-23:** the mock treated delivered answers as passed, exceptions escaped, a checker ran after a fault, and
  four parallel builders breached the one-worker condition.
- **MRL-24:** four more failures — release drift under an unchanged label, a malformed return leaving an
  unclassified slot, a byte violation that did not stop the batch, and scorer exceptions losing grades.

**The pattern:** I tested the cases the lead had named, then the lead's reviewers probed the next failure mode.
I was reacting to named cases instead of enumerating failure modes systematically. Using parallel builders to go
fast produced plausible artifacts whose defects surfaced only in review, which is the slowest place to find them.
Overclaimed prose added correction rounds of its own.

### 2. No scheduler after the restart — infrastructure

While the half-hourly cycle ran, acknowledgement took **1.2–11.8 minutes**. Since the app restart, no cycle has
fired (the last tick was 08:10:19Z), and I run only when the owner messages. Acknowledgement rose to **95 minutes**
for MRL-24 and over **41 minutes** for MRL-25. The MRL-23 overrun (462.7 minutes) combined this with my own error:
three deliverables were finished inside the cap, but I held them to publish together, so the app quit left seven
hours of apparent silence.

### 3. Micro-allowances with a review gate on every step — process design

Each allowance is 20–30 minutes, source-only, and requires an acknowledgement, a delivery and a review before the
next is released. At a round time of about 45–70 minutes for about 10–25 minutes of work, the fixed overhead per
round exceeds the work. That is a reasonable price for rigor on released results, but E14's preparation has now
taken six rounds for a study whose collection would take roughly **five minutes** of receiver time and yield a
descriptive-only result.

### 4. A frame that can only rule effects out — the science itself

With a 3B receiver at about 71% baseline, public-pass tasks sit at the private ceiling, only about a third of
tasks give a revision anything to fix, and the frame (198 eligible) is far too small to establish a useful gain.
Designs keep being refuted because there is little room for a detectable effect in this frame. More process will
not change that.

## What I am changing, starting with MRL-25

1. **Failure-mode matrix before delivery.** For every boundary (release load, transport, parse, public check,
   render, scorer, ledger write), test every failure type (exception, malformed return, drift under an unchanged
   label, limit violation, interruption), and require an explicit stop state and full slot retention in each.
   The goal is that the lead's review finds nothing new.
2. **One sequential thread, no parallel builders.** Already in force since MRL-24.
3. **Commit each finished piece immediately.** Already in force since MRL-23.
4. **No claim without a number or a test.** Every sentence stating a property must point to the test or record
   that shows it.
5. **Feasibility first.** Check ceiling, headroom and power at the actual decision threshold before proposing any
   design, not after.

## What would help from others

- **The owner:** restore a scheduler that survives app restarts. Acknowledgement latency is the single largest
  cost I cannot fix alone.
- **The lead (proposal only; its decision):**
  - replace serial 30-minute repair rounds with one bounded allowance that carries an explicit acceptance-test
    list, reviewed once;
  - decide whether E14 — ten already-exposed histories, about five minutes of receiver time, descriptive only —
    is still worth further preparation rounds, or whether effort should move to a design that can actually
    establish something, such as a larger task source.
