# Reference and negative-control validation — results

**Executed 2026-09-21T12:59Z** under the contract committed beforehand at `c70cf83`
(`docs/landmark_reference_validation_contract.md`). Run directory `results/landmark_reference_validation_20260921T125829Z/`.

**All 7 roots cleared. All 25 outcomes matched their pre-registered expectations.** 25 programs, 0.6 s,
**0 model calls**, inside the attested landmark sandbox (containment 9/9 passed).

| root | original reference | repaired reference | controls executed and failed |
|---|---|---|---|
| 52 | passes | — | 3 / 3 |
| 357 | passes | — | 3 / 3 |
| 373 | passes | — | 2 / 2 |
| 378 | passes | — | 3 / 3 |
| **402** | **fails, as pre-registered** | **passes** | 2 / 2 |
| 489 | passes | — | 2 / 2 |
| 509 | passes | — | 2 / 2 |

**The 402 defect is now confirmed by execution**, not only by source inspection: the original
reference fails on exactly `assert ncr_modp(0, 0, 1) == 0` (AssertionError), and reference-repair-v1
(`return C[r] % p`) passes the full ten-assertion suite, p = 1 retained.

**Every control genuinely executed and failed a private assertion** (`executed_test_or_integrity_rejection`,
payload started). None counted as a failure through a parse rejection, a timeout before the payload, or
an environment failure — the clearing rule forbids those substituting for a demonstrated failure. That
includes the v2 additions: the last-element program for 357 and the empty-list program for 378.

## Scope

A clear means this instrument admits a correct program and rejects the frozen wrong ones on these
suites. It does not show that the suites catch every wrong program, that the seven roots are
independent families, or anything about prompt efficacy. The v2 contract file keeps its hold statuses
by design — the contract is the pre-execution artifact and this document is the evidence that clears
it; the builder still refuses to clear a hold by editing status alone.
