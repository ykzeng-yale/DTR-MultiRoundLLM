# Development release v1 — first graded real collection


> **Lead resolution, 21 September:** [consolidated decisions and required corrections](worker_issues_resolution_20260921.md) govern use of this historical report. Preserve original records. In particular, the pilot does not establish population efficacy, complete receiver-law verification or categorical sample-size feasibility. The working useful-gain threshold is now five percentage points for a future frozen policy comparison; no new trial is released.

**2026-09-21T13:06Z.** Frozen at `3e70c0a` (`experiments/landmark/dev_release_v1/`), collected against the pinned
Qwen2.5-3B, graded in the attested sandbox, analysed with `analyze.py`. Run `results/landmark_dev_release_v1b_20260921T130349Z/`, grades
`results/landmark_dev_release_v1b_20260921T130349Z_grades/`, analysis `results/landmark_dev_release_v1b_20260921T130349Z_analysis.json`.

## What this establishes

**The pipeline works end to end on a real receiver, and it is exactly reproducible.** 49/49 calls, 0
missing, 0 preflight or fatal errors, 86 s, 9,964 prompt and 3,162 completion tokens, $0. The receiver's
weight digest and build were verified before and after collection. A second, independent collection with
the same seeds produced **49/49 byte-identical outputs** — with prompt caching disabled the seeded
receiver is fully deterministic, so the only noise is genuine seed-to-seed variation within a run.

## What it does not establish

**Anything about prompt efficacy.** Seven roots in one unresolved family is effectively one independent
unit; the analyzer suppresses every interval (Hoeffding radius 1.73, effective families 1.0) and reports
only completion bounds for the realised roots. Read the table below as a description of what happened on
these six roots, not as evidence about any population.

## Outcomes (private-suite pass; two seeds per continuation arm)

| root | STOP | generic repair | history-specific repair | independent restart |
|---|---|---|---|---|
| 52 | 1 | 1, 1 | 1, 1 | 1, 1 |
| 357 | 1 | 1, 1 | 1, 1 | 1, 1 |
| 373 | 1 | 1, 1 | 1, 1 | 1, 1 |
| 378 | 1 | 1, 1 | **0**, 1 | **0**, 1 |
| 402 | — | — | — | — |
| 489 | 0 | 0, 0 | 0, 0 | 0, **1** |
| 509 | 1 | 1, **0** | 1, 1 | **0**, 1 |

Arm means over the six graded roots: STOP **0.833**, generic repair 0.750, history-specific repair
0.750, independent restart 0.750. Completion bounds for each continuation minus STOP over all seven
assigned roots: [−0.214, +0.071].

**402 is ungraded by design, not by outcome.** The grader refuses to grade a root whose frozen reference
fails, and the builder places the *original* benchmark reference in the spec — which for 402 is the
defective one. None of 402's outputs was executed. Including it needs a spec that carries the validated
repair (below).

## Descriptive observations, consistent with earlier measurements

* **Continuing damaged correct answers.** On the five roots correct at STOP, 4 of 30 continuation
  replicates turned a correct answer incorrect (13%), close to the 16.2% degradation audit A3 measured on
  a different loop.
* **Feedback did not repair; resampling sometimes did.** On the one root wrong at STOP (489), generic and
  history-specific repair fixed it 0 of 4 times; independent restart fixed it 1 of 2.
* **No visible effect of feedback content.** History-specific and generic repair tie in aggregate.

These are six roots. They motivate a properly sized study; they do not constitute one.

## Next

1. Release v1c: the same freeze with the validated 402 repair in the spec, so all seven roots are graded.
   The receiver is deterministic, so re-collection reproduces these outputs exactly and only adds 402.
2. The confirmatory design needs many more independent families; the protocol's planning figures
   (roughly 864–4,348 roots at δ = 0.03) are the reference for sizing it.

---

## Release v1c — all seven roots graded (2026-09-21T13:09Z)

Frozen at `d5efcd8`; run `results/landmark_dev_release_v1c_20260921T130757Z/`, grades `results/landmark_dev_release_v1c_20260921T130757Z_grades/`, analysis `results/landmark_dev_release_v1c_20260921T130757Z_analysis.json`. Identical to v1 in everything that
reaches the receiver; 402's private spec carries the hash-verified repair. **49/49 outputs byte-identical to
release v1** — the third independent confirmation that the seeded receiver is deterministic. 52 sandbox
executions, **0 missing grades**.

| root | STOP | generic repair | history-specific repair | independent restart |
|---|---|---|---|---|
| 52 | 1 | 1, 1 | 1, 1 | 1, 1 |
| 357 | 1 | 1, 1 | 1, 1 | 1, 1 |
| 373 | 1 | 1, 1 | 1, 1 | 1, 1 |
| 378 | 1 | 1, 1 | **0**, 1 | **0**, 1 |
| **402** | **0** | 0, 0 | 0, 0 | 0, 0 |
| 489 | 0 | 0, 0 | 0, 0 | 0, **1** |
| 509 | 1 | 1, **0** | 1, 1 | **0**, 1 |

Arm means over seven roots: **STOP 0.714; generic, history-specific and restart each 0.643.** Intervals are
suppressed — one effective family.

* **Continuing broke correct answers**: 4 of 30 continuation replicates on the five roots correct at STOP (13%).
* **Feedback repair fixed nothing**: 0 of 8 attempts across the two roots wrong at STOP (402 and 489).
  Independent restart fixed 1 of 4.
* **402 is simply hard for this receiver**: wrong at STOP and under all six continuations. Its grade was
  blocked in v1 by the defective reference, not by anything about the receiver.
* **History-specific and generic repair tie** at 0.643.

**Same caveat, stated again because it matters most:** seven roots, one effective family. This is a working,
reproducible pipeline and a description of seven tasks — not evidence that feedback content, continuation or
restart has any population-level effect. Sizing a confirmatory study is the next scientific decision.
