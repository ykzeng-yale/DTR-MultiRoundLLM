# Independent review of the seven landmark contracts, and the 402 repair

**Experiments workstream, 2026-09-21T12:55Z.** Nine read-only agents (workflow `wf_4b8bab05-55e`, 14.6 minutes,
inside the 30-minute cap): one per root, a 402 repair proposer and an adversarial refuter. **Zero
executions** of reference, candidate, control or assertion text; expected values checked only against
standard-library oracles; zero model calls; zero installs.

## Provenance: resolved

The pinned full MBPP source was missing from this workspace (these seven roots are not in the
sanitized split), so four reviewers could not check provenance. I re-fetched it from the contract's
`source_url`: SHA-256 **matches `ccf64cea…` exactly**, 974 records, and all seven entry points appear
in their reference definitions and in all three original assertions.

## Verdicts

| root | verdict | finding |
|---|---|---|
| 52 | clear | clean; added a triangle-area control (`b*h//2`) no v1 control exercised |
| **357** | **defect → fixed in v2** | `max(t[-1] for t in test_list)` — the maximum of each tuple's *last* element — **passed all six v1 private assertions**. The suite could not tell a natural bug from a correct answer. v2 adds `[(1, 2), (8, 3)] -> 8`, which also catches the first-tuple-only control, and adds the last-element program as a control. |
| 373 | clear | clean |
| 378 | clear | no v1 control exercised the empty list the domain was widened to include; v2 adds `[test_list[-1]] + test_list[:-1]`, which raises on `[]` |
| **402** | **defect → fixed in v2 + repair proposed** | beyond the known r = 0, p = 1 defect: **a prime-only Lucas implementation passed the entire suite** despite the public claim "the modulus need not be prime". v1's only composite case, (6,3,4), happens to coincide with Lucas. v2 adds `(4,2,4) -> 2` and `(6,2,6) -> 3`, where Lucas returns 0, plus `(5,2,1) -> 0`. |
| 489 | clear | in all three v1 boundary cases `arr[0]` is the maximum, so the `count(arr[0])` control was caught only by the originals; v2 adds `(4, [1,3,3,2]) -> 2` |
| 509 | clear | the "hold" was provenance only, now resolved |

## 402 reference repair (reference-repair-v1), p = 1 retained

`return C[r]` → **`return C[r] % p`**, a four-character change with CRLF and trailing whitespace
preserved. Original canonical-JSON digest `60c271e5…` independently **matches the report**. Repaired
raw SHA-256 `50fafebe…`, canonical `ec650500…`.

**Static proof.** `C[0]` is set to 1 and never rewritten, because the inner range stops before
`j = 0`. So `r = 0` returned an unreduced 1, which is wrong only when `p = 1`; the added `% p` makes it
0. For `j ≥ 1` every write is reduced mod p, so `C[r]` already lies in `[0, p−1]` and the extra `% p`
is a no-op. For `r = 0, p ≥ 2`, `1 % p = 1`. Pascal's recurrence holds modulo any m ≥ 1, so primality is
not needed. **The repair changes exactly the p = 1, r = 0 outputs and nothing else in the domain.**
The adversarial refuter returned **REPAIR_HOLDS** after eight attacks: p = 1 with r = 0 and with r ≥ 1,
composite p, r = n, n = 0, and the original three assertions.

## Artifacts

* `experiments/landmark/task_contracts_v2.json` — separately versioned; v1 untouched. Eight additions,
  each with its reason.
* `tests/test_landmark_task_contracts_v2.py` — re-derives **every** boundary value, v1's included, from
  a specification oracle; checks v2 ⊇ v1, no duplicates, that each named wrong program is now separated,
  and that the repair is minimal and keeps p = 1. Full suite: **247 passed**.

## Next

Isolated sandbox execution of the references (original and repaired 402) and all controls against the
v2 private suites, under a committed validation contract. That is the step that clears these holds.
