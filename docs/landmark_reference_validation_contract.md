# Validation contract — reference and negative-control execution, v2 contracts

**Committed before execution.** Everything below is fixed before any reference or control runs. No
spec, case, control or clearing rule may change after an outcome is seen; an unexpected outcome is
reported as-is.

## Preconditions (all met at commit time)

* Containment attestation: the landmark sandbox passed all nine canaries with every payload started,
  in `results/landmark_containment_*` (see the containment commit). `validate_references.py` calls
  `grade.verify_attestation` and refuses to run on a missing, stale (>24 h), failed or unbound
  attestation.
* Specs: built by `scripts/build_landmark_task_contracts.py` from `task_contracts_v2.json` and the
  pinned full MBPP source (SHA-256 `ccf64cea…`): 7 roots, 48 private assertions, `ready_for_collection:
  false`.
* No model is called. Only benchmark references, the one repaired reference, and frozen controls
  execute.

## What executes

Per root: the original reference; for 402 also reference-repair-v1 (`return C[r]` → `return C[r] % p`,
nothing else — the runner refuses any other change); every frozen negative control. Each program runs
with the root's full private suite, an integrity canary and a sentinel, through `grade.evaluate`.

## Pre-registered expected outcomes

| program | expected | why |
|---|---|---|
| original reference, roots 52, 357, 373, 378, 489, 509 | **1** (passes every private assertion) | static review found no defect |
| original reference, 402 | **0** | known defect: returns 1 on (0,0,1) and (4,0,1) where 0 is correct |
| repaired reference, 402 | **1** | static proof + adversarial review: changes only the p = 1, r = 0 outputs |
| every negative control, all roots | **0** | each was shown statically to fail at least one private assertion |

## Clearing rule (unchanged from `docs/landmark_grading_validation_20260920.md`)

A root clears only if its positive reference passes **and** every negative control actually executes
and fails. For 402 the positive reference is the repaired one. A parse rejection, an environment
failure or a timeout before the payload starts is never counted as a demonstrated failure.

## What a clear does and does not mean

It means the measurement instrument discriminates the frozen wrong programs and admits a correct one
on this suite. It does **not** mean the tasks are independent families, that the suites catch every
wrong program, or that anything about prompt efficacy is known. Collection still requires the full
committed freeze.
