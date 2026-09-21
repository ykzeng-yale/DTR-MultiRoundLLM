# MRL-06: receiver configuration and drift guards

> Lead audit: [MRL-05–08 decisions](lead_review_mrl05_08_20260921.md) supersede conflicting validity, guard and freeze claims below. Implementation acceptance is distinct from execution authorization.

> **MRL-08 correction (experiments workstream, 2026-09-21, processed `6b88f68`).** Original text is kept below.
> The lead's independent review reproduced guard failures on fake inputs, and those failures are repaired in
> the MRL-08 code (see `docs/mrl08_delivery_20260921.md`). These statements below are withdrawn or narrowed:
>
> - **"Defaults cannot move the law between checks".** Eleven explicit request fields plus sampled snapshots
>   do not pin every setting per request. Sampler order and other implicit settings (dry_base, xtc_threshold,
>   mirostat_tau/eta, …) can change between checks.
> - **"All checks pass → `receiver_state_verified_pre_interim_post`, `efficacy_interpretable: true`".**
>   Replaced by the narrow status `receiver_guard_checks_passed`. The guard never grants efficacy
>   interpretation; that requires the complete release evidence. Failures still mark runs not interpretable,
>   and outputs are retained.
> - **Validation gaps, now repaired.**
>   - Type and range checks were missing: `min_p = 2` and fractional `top_k` passed.
>   - Empty or malformed `/slots` counted as idle.
>   - Null generation settings passed.
>   - A snapshot with `top_k = 40` alongside a request with `top_k = 20` was "verified".
>
>   The fix is a required `sampler_law`. Under `server_defaults_pinned`, the requested sampler must equal the
>   snapshot after float32 rounding. Under `declared_override`, the difference is recorded as a different
>   frozen law.
> - **"Lease check".** Sampled idle slots are not an exclusive lease. Ownership of the process and resources
>   must be evidenced separately at freeze (field 12).
> - **The historical reconciliation** is inferred, not retroactively observed.

**Experiments workstream, 2026-09-21 (processed `e7eb925`).** Work was source and mock only. One read-only
`GET /props` and one `GET /slots` were made on :8193 at 14:55:13Z. No generation, no reference, candidate or
sandbox execution, no install, $0.

## Finding: two active sampler defaults were never recorded

The v1/v1b/v1c requests override five fields: `temperature` 0.7, `top_p` 0.95, `max_tokens`, `seed` and
`num_ctx`. Every other sampler setting came from the server's launch defaults. `/props` on build `b1-4fea119`
shows two defaults that truncate the distribution:

- **`top_k = 40`**
- **`min_p = 0.05`**

The remaining settings are inactive: typical_p 1, repeat_penalty 1, presence/frequency penalties 0, DRY 0,
XTC 0, mirostat 0 and top_n_sigma −1. The sampler order is penalties → dry → top_n_sigma → top_k → typ_p →
top_p → min_p → xtc → temperature.

`receiver_freeze_v1.json` and the release configs record only temperature and top_p. Its `per_chunk_guard`
text says build, model path and n_ctx are recorded "at the start and end of every run … halt on any change".
**That was not true of the v1 code.** The v1 code checks:

| when | what the v1 code checks |
|---|---|
| before the run | weight digest and build |
| each request | `num_ctx` against a cached `/props` |
| after the run | weight digest only |

**Reconciling the historical runs.** The linked derived record is
[`results/receiver_state_reconciliation_20260921.json`](../results/receiver_state_reconciliation_20260921.json),
built by [`scripts/reconcile_receiver_state_20260921.py`](../scripts/reconcile_receiver_state_20260921.py) from
the preserved run records and the [snapshot](../results/receiver_props_snapshot_8193.json).

- The 3B server process started at 2026-09-19T17:41:11Z, before all three collections, and is still running.
- `POST /props` is disabled (`endpoint_props: false`).
- In every run, the recorded build, template, per-slot n_ctx, slot count and model path match the snapshot.

The snapshot's defaults were therefore most plausibly in force during all three runs. The effective law was:
temperature 0.7, top_p 0.95, top_k 40, min_p 0.05, everything else off. This relies on llama-server
semantics that I have not independently proven. It does not turn v1–v1c into receiver-verified efficacy
evidence; they remain descriptive development data. No original record was changed.

## What `landmark-v2` enforces (implemented in `experiments/landmark/collect.py`)

| guard | v1 | v2 |
|---|---|---|
| Weight file digest | before + after | before + after |
| Build | before | inside the state digest, checked before, per root and after |
| Chat template, BOS/EOS, n_ctx, slots, model path | template recorded, not checked | inside the state digest |
| **All server sampler defaults and sampler order** | not recorded | inside the state digest |
| **Sampler settings in each request** | temperature, top_p | temperature, top_p **+ 11 pinned fields** (`PINNED_SAMPLER`), so defaults cannot move the law between checks |
| Frozen expectation | model digest, build | + `receiver_state_sha256` in the committed config |
| Lease/idle check | none | `/slots` must show 0 busy slots before the run and before every root |

The **receiver state** is the full `/props` object minus `is_sleeping`, its only volatile field. Any field a
server upgrade adds enters the state and changes the digest, so the check fails closed.

Drift handling, in `run()`:

1. **Preflight mismatch or busy receiver.** No request is dispatched; the status is
   `preflight_failed_no_dispatch`.
2. **Drift, contention or an unreadable `/props` before a root.** Future dispatch stops (`fatal`). Every
   output already collected is kept in `calls.jsonl` / `roots.jsonl`. The run is marked
   `receiver_not_verified_outputs_retained` with `efficacy_interpretable: false` and the drifted field names.
3. **Postflight state or weight digest changed, or postflight unverifiable.** The same marking applies.
   Nothing is deleted or imputed.
4. **All checks pass.** The status is `receiver_state_verified_pre_interim_post`. This covers the receiver law
   only: not task validity, grading or statistical adequacy.

A `landmark-v1` config now reports `v1_partial_guard, efficacy_interpretable: false`. **Its request bytes are
unchanged**; a test pins this.

**Freezing a v2 config.**

1. `collect.py --config C --tasks T --print-receiver-state` does a read-only snapshot and prints its digest.
2. Commit that digest as `receiver_state_sha256`.
3. Set `sampler` to the observed defaults. The v2 request law then equals the reconciled v1c law, with
   nothing left implicit.

For the snapshot above the state digest is `1b8bf998c5dd06a611f692bab9e802b285ae75164b8b389fd8b381c06a83f5c1`. It
is a fixture, not a freeze: the freeze takes its snapshot immediately before release.

## Tests (source/mock, `scripts/check_tests.sh`)

`tests/test_landmark_receiver_guard.py` has 8 tests on a fake server shaped like the real `/props`:

- the state digest ignores `is_sleeping` but catches min_p, template and new-field changes;
- a v2 config must pin all 11 sampler fields;
- the pinned fields appear in every request body;
- a frozen-state mismatch dispatches nothing;
- a busy slot fails the lease check;
- drift at root 2 stops dispatch after root 1 and keeps its outputs;
- an unreadable postflight marks the run not interpretable;
- a v1 config is reported as a partial guard and its request bytes are unchanged.

The historical freeze tests now resolve v1/v1c against the **Git blobs at their recorded freeze commits**
(`3e70c0a`, `d5efcd8`). They also assert that real-mode reuse of those configs on the changed checkout
**fails**: a changed runtime needs a new freeze, not a waiver. Full suite: **260 passed**.

## Limits that remain

- **Foreign requests between checks are not detected.** A sibling request arriving between two `/slots`
  checks shares the batch; that can change floating-point numerics, not the configured law. Exclusive use
  needs a lease the sibling honours, or a dedicated receiver.
- **Restarts may go undetected.** `/props` exposes no process identity. `media_marker` looks like a per-launch
  random nonce, and if it is, a restart changes the state digest. I have not verified that. A restart that
  reproduces the whole state is outcome-equivalent under the frozen law.
- **Explicit pins versus implicit defaults are untested.** Pinning the defaults explicitly should reproduce
  the v1c effective law. That v2 outputs are byte-identical to v1c under explicit pins is untested, because
  testing it needs a model call. Treat v2 as a new version and do not pool it with v1c.
- **The weight file is hashed only before and after.** Hashing 2.1 GB per root is too costly; the loaded
  weights are resident, and the state digest covers the path.
