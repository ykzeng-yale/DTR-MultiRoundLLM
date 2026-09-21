# Development release v1 — frozen before any receiver call

**What it is.** The first real collection for the project's primary question — does the content of a
next message, given the same conversation prefix, change task success? — run as the bounded
**development** batch the theory workstream's protocol defines. It is not confirmatory. Seven roots
cannot support a population claim, and the protocol says so; this batch establishes that the pipeline
works end to end on a real receiver and gives a first look at receiver noise and arm behaviour.

**Design (the protocol's, unchanged).** For each root: one initial answer from the pinned system message
and public task. That exact prefix is then continued three ways, each with two independent seeds:
`generic_repair`, `history_specific_repair`, and `independent_restart` (the same public task without the
old answer — a resampling control). STOP is the initial answer with no continuation. Every arm is run
for every root with inclusion probability one; seeded order is scheduling, not treatment assignment.
7 roots × (1 + 3 × 2) = **49 receiver calls**, within the 168-call development ceiling.

**Frozen here:** `config.json` (receiver digest `626b4a66…`, build `b1-4fea119`, temperature 0.7,
top_p 0.95, per-slot context 8192, 512 tokens per call, 20-minute and 49-call caps, $0),
`tasks.jsonl` (public definitions only), `private_specs.json` and `grading_contract.json` (graded after
collection by `grade.py` in the attested sandbox; never shown to the receiver). All seven specs cleared
reference/control validation (`docs/landmark_reference_validation_results.md`).

**Outcome.** Private-suite pass of each continuation's output, and of the initial answer for STOP.
Missing outputs stay missing; the analyzer reports all-assigned completion bounds.

**Reported regardless of result.** Per-arm pass rates, the paired contrasts history-specific vs generic
repair and each arm vs STOP, receiver noise across the two seeds, every failure and missing outcome,
and calls, tokens and wall time. A null or a reversal is reported exactly as found; nothing is
re-run, re-seeded or re-scored to change it.

## Re-freeze before any grading (recorded honestly)

The first collection, frozen at , is **superseded and was never graded**. I froze its
 as the SHA-256 of the contract *file*, but  binds a collection to
, which also covers the grader, sandbox and integrity sources — so the grader
correctly refused it. **No outcome of that collection was observed**: grading stopped before executing
anything, so re-collecting is not selection on outcomes. The corrected freeze changes only that hash and
stores the specs as JSONL, the format the grader reads (the builder emits a JSON array — an interface
mismatch between the two). Seeds derive from the unchanged  and root IDs, so the re-collection uses
identical seeds, which also measures whether the receiver is reproducible run to run. The superseded run
directory is kept, not deleted.  makes the error unrepeatable.
