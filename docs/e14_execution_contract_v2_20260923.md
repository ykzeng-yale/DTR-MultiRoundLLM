# E14 execution contract v2 — status corrections under MRL-24 criterion 4 (grants nothing)

Experiments workstream, 23 September 2026, processed lead decision `45f7aa72ad75de4fe3dbd8fb4ccbb0b6b605246d`.
**This document authorizes no instrument, receiver or model execution.** The future 130 model attempts, 66,560
reserved completion tokens and 228 isolated starts remain planning values; only a separate explicit release can
make them authority. `docs/e14_execution_contract_20260923.md` is preserved unchanged; where the two conflict on
what exists or runs, this file governs.

## 1. What exists now, and what still does not

v1's section 0 said "the E14 executables do not exist yet". That is now **partly stale**, so it is replaced by
this exact status:

| Component | Status | Evidence |
|---|---|---|
| v1 package builder and `--verify` | **exists** | `scripts/build_e14_release.py`; v1 package preserved byte-for-byte |
| v2 package builder and `--verify` | **exists** | `scripts/build_e14_release_v2.py`; builds identically from both cache locations |
| Connected **mock** path: plan, dispatch, public check, private scoring, analysis | **exists, mock only** | `scripts/e14_connected_mock.py`; 24 tests with injected fakes |
| Receiver guard, byte limit, phase and outer limits, 228-start ledger | **exists, mock only** | same module; exercised with fakes |
| A **real** E14 collector bound to the real receiver adapter (`collect.LlamaServer`) | **does not exist** | the connected path takes an injected transport; nothing binds it to a live server |
| A **real** E14 grading path through the isolated sandbox | **does not exist** | `score_private` takes an injected scorer only |
| `study_adapter` allowlist entry for `e14_release_v2` | **does not exist** | `COMMITTED_RELEASE_MANIFESTS` still lists v2/v3/e13a only |
| E14 instrument-validation script (references + both controls per root) | **does not exist** | no script validates the ten references and twenty controls |
| An E14 stage clock with this design's phase names | **does not exist** | `e13a_stage_clock.py` is five-root/E13a-bound |

## 2. Commands that are runnable today

Only these. Every one is source/mock and executes no program under test:

```sh
.venv/bin/python scripts/build_e14_release.py --verify
.venv/bin/python scripts/build_e14_release_v2.py --verify
.venv/bin/python -m pytest -q tests/test_e14_connected_mock.py tests/test_build_e14_release_v2.py tests/test_build_e14_release.py
```

Measured on this host: each `--verify` completes in about 0.05 s wall and prints `"verified": true`.

## 3. Commands and flags withdrawn as unsupported

Every command in v1's sections 2–6 that invokes an **E14** collector, grader, instrument validator, clock or
analyzer flag (including `--phase`, the E14 `--release` binding for grading, and any E14 stage-clock phase name)
is **not runnable** and is withdrawn as an executable command. Those lines describe interfaces a future E14
adapter would need to provide; they are dependencies, not instructions. v1's references to the E13a scripts'
existing flags remain accurate as descriptions of E13a, which enforces five roots and 60 calls and is **not** an
E14 path.

## 4. The limits that govern each phase (planning, not authority)

| Phase | Governing limit | Where it is recorded |
|---|---:|---|
| Setup | 600 s | `e14_release_v2/config.json` → `e14.phase_limits_seconds.setup` |
| Collection | 480 s | same, and `config.max_seconds` = 480 |
| Private grading | 300 s | same, and `release_manifest.grading_limits.grading_seconds` = 300 |
| Analysis | 300 s | same |
| Outer | 2,700 s | same |

v1 carried an inherited 1,560 s `max_seconds` and a 600 s `grading_seconds`, both contradicting this table; v2
replaces them. The connected mock enforces the collection and outer limits through an injected clock and stops on
exhaustion with every slot retained.

**Starts, planning only:** 18 containment + 40 instrument + 30 grader rechecks + 140 candidate = **228**. Every
attempted or uncertain start counts; no cache saving renews a cap. The mock's start ledger enforces these caps
with fake boundary events, and **actual program starts remain zero**.
