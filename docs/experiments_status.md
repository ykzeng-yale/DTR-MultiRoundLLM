# Experiments status — live, for the theory workstream to judge

**Owner: experiments workstream. Published every 30 minutes** by an in-session job (the earlier
durable scheduled task stalled on a permission prompt after one run and has been disabled — the
~9-hour silence from 2026-09-20T23:20Z was that failure, not a pause in intent). Purpose: publish
results and intended designs often enough to catch a wrong direction before it costs GPU time.

**Last updated: 2026-09-25T12:45:44Z** — **Heartbeat (watcher tick 2026-09-25T12:45:44Z).** Last lead commit processed: `37d1b692a8df2f76d9b957b3c84bd9313ccb871b`. No new lead work since LEAD-POLICY-10 (accepted 10:13:51Z in 855727d); issue #3 still at 73 comments. Nothing is released, and nothing was started. Watcher: **running**, re-armed each tick, wakes on every lead commit and at most every 30 min while this desktop session is open; the separate half-hourly scheduler has not fired since 2026-09-23T08:10:19Z. Run/lease: **none**. E14 N1/S1 batch: **NO-GO accepted** (LEAD-POLICY-06); source/mock kept as an instrument artifact with no execution allowance. Next bounded action: none open on the worker side; **blocker** for any experiment work is a new lead-owned development design: action class, family frame, comparators, endpoint, inference and finite local cap.

**Scheduler, reported honestly.** The session poller wakes this worker when `origin/main` gets a new commit, or after 30 minutes. Evidenced wakes so far:

| time (UTC) | trigger | what happened |
|---|---|---|
| 18:32:24 | lead commit `ad1d061` | read it |
| 19:05:59 | half-hour tick | nothing new |
| 19:08:14 | lead commit `5f02823` | MRL-09 started 19:08:53, delivered 19:23 as `e1660b2` |
| 19:39:05 | half-hour tick | no new lead commit; waiting on the lead's MRL-09 review and preflight/freeze authorization |
| 19:42:21 | lead commit `9be5edd` | MRL-10 run 19:43–19:54, delivered as `0bb2388` |
| 20:13:16 | half-hour tick | no new lead commit; manuscript fact-check published while waiting for the MRL-10 review |
| 20:15:57 | lead commit `02bf71a` | MRL-11 run 20:16:42–20:18:12; E1–E8 all PASS (`b73054e`) |
| 20:49:14 | half-hour tick | no new lead commit; waiting on the MRL-11 review, the E11 release and the CLI allowance |
| 20:52:28 | lead commit `d1a0ba9` | MRL-12 run 20:52:58–21:00; delivered `3f56ec6` |
| **21:23:12** | half-hour tick | no new lead commit; E11 held on the owner's window (at least 45 minutes) and the lead's release |

It runs only while this session is alive.

## 1. Executing now

| job | state | bound | started |
|---|---|---|---|
| **MRL-05**: correct sizing/status claims; root/family precision plan against the 5 pp useful-gain null | **completed** | source-only; 0 model/reference/candidate/sandbox executions; $0 | 2026-09-21T14:51Z |
| **MRL-06**: receiver configuration/drift guards (`landmark-v2`) plus source/mock tests | **completed** (260 tests pass) | as above, plus one read-only `/props` and one `/slots` GET, no generation | 2026-09-21T14:51Z |
| **MRL-07**: implementation plan for the public-diagnostic proposal, and its missing freeze fields | **completed**: plan, 15 freeze fields, executor table ≤ 137 starts; one design issue raised (section 1 of the plan) | source + static prediction only; 0 executions; $0 | 2026-09-21T15:00Z |

No frozen batch is running and no lease is held. `/slots` showed 4/4 slots idle at 14:55Z.

Receiver: **no generation load from this workstream.** The sibling `DTR-AgentEvals` completed every stage (log, live,
branch; errors 0). Its two servers remain resident and idle. **Memory is the binding constraint —
swap 25.3/26.6 GB used.** See `docs/receiver_runtime_spec_20260921.md`.

## 2. Results standing

| result | number | status / where |
|---|---|---|
| Task pool after integrity, mutation and scoring gates | 561 usable | `docs/audits.md` — **230 is a difficulty-selected subset, not an independent-family count** (ruling J2) |
| Historical reference checks (original endpoint) | 591/591 | original endpoint only — **not** validation of the v1 contracts |
| Enumerated exploit flags on real episodes | 0/4,488 | absence of enumerated flags ≠ zero bias from all exploits |
| Iteration repair / degradation, source loop | 0.239 / 0.162 | **conditional descriptive** — conditional on first-candidate status and that loop taking another turn |
| E0 | see corrected docs | `docs/e0_corrected_results_20260920.md`, `docs/history_compression_results_20260921.md`; my original interpretation is superseded |
| Opportunity mass, probe-free, full corpus, `validation.passed` | 0.0695 [0.0513, 0.0936] 3B | descriptive fixed-bank quantity; **not** a sample size for population power |
| Strict consensus-trap mass | 0.0428 [0.0289, 0.0629] 3B | descriptive |
| Receiver/runtime inventory | built | `docs/receiver_runtime_spec_20260921.md` |
| Contract review | 5 clear, **357 and 402 non-discriminating in v1 → fixed in v2**; 402 repair holds | `docs/landmark_contract_review_20260921.md`, `experiments/landmark/task_contracts_v2.json` |
| Receiver adapter | llama-server adapter added; live digest == independent hash; no generation | `experiments/env/receiver_freeze_v1.json` |
| **Containment** | **passes 9/9 for the first time** — one missing profile line made every launch abort (SIGABRT) | `results/landmark_containment_*` |
| **Pool screen** | 544 fresh candidates → **396 pass the mechanical gates**. That is a mechanical count, **not** eligible independent families; the 24-slate exclusion fraction does not transport; interface relaxation is deferred | `docs/confirmatory_sizing_20260921.md` |
| ~~Confirmatory sizing~~ **withdrawn** (MRL-05) | Wilson intervals on nested pairs and categorical feasibility claims withdrawn. The lead set a **0.05 useful-gain null** with 0.10 as the planning alternative. The replacement is a conditional root/family scenario plan: 114–1,086 roots under a Wald bound, 617–2,038 families under empirical Bernstein, **≥ 2,952 families under J2 Hoeffding even at zero variance**. The uncertainty procedure is the largest lever | `docs/precision_plan_mrl05_20260921.md` |
| **Development release v1c (all 7 roots graded)** | 49/49 matched v1 — **reproduction of the same requests, not independent replication**; 0 missing grades; STOP 0.714 vs every continuation 0.643; the **syntactic history-derived cue** fixed 0/8 on wrong roots, restart 1/4; continuing broke 4/30 correct replicates; descriptive only | `docs/dev_release_v1_results.md` |
| **Receiver law, reconciled** (MRL-06) | The v1–v1c requests pinned only temperature/top_p; **server defaults top_k = 40 and min_p = 0.05 were active and unrecorded**. The same receiver process ran through all three collections and `POST /props` is disabled, so those defaults were most plausibly in force. `landmark-v2` now pins them and checks the full `/props` state before, per root and after | `docs/receiver_guard_mrl06_20260921.md` |
| **Development release v1 (first real graded collection)** | 49/49 calls, 0 missing, 49/49 matched on re-run (same requests); 6 roots graded (402 blocked by design); STOP 0.833 vs every continuation 0.750; continuing broke 4/30 correct replicates; descriptive only, one conservatively assigned unresolved family. All three runs are charged: 147 calls, 39,378 tokens | `docs/dev_release_v1_results.md` |
| **Reference/control validation** | **7/7 roots cleared, 25/25 outcomes as pre-registered**; 402 defect confirmed by execution, repair passes | `docs/landmark_reference_validation_results.md` |

**Withdrawn, not to be cited:** STOP; the critic/prompt/generator cut-list; "five lines converged";
the double-counted ceiling; `W = 1` as stated; ESS lower bound as ESS; G0e as budget-general; v2
sections 4–5 (outcome-selected power counts, no-harm from *n*).

## 3. JUDGEMENT REQUESTED

**J5 (MRL-07, defect-class exposure).** The 21 public examples reject 18/19 known wrong behaviours by
prediction. They include last-element max (357), prime-only Lucas (402) and the original 402 reference bug,
which are exactly the classes the v2 *private* boundary cases were written to catch. Every arm sees them, so
contrasts stay fair, but hidden discrimination shrinks and initial correctness probably rises.

My recommendation: keep the cases (no reselection) and add a descriptive **private-only failure** endpoint.
Your call.

**J6 (MRL-05).** Which prespecified uncertainty procedure to use. Within any one scenario it multiplies
the required family count relative to a Wald bound:

- by 2.9–16× for empirical Bernstein;
- by 5.5–83× for J2 Hoeffding.

Across all variance scenarios the Wald count itself varies 18.6× (38–707 families). The Hoeffding floor of
2,952 exceeds every other requirement in the grid.

Previously: J1–J4 were ruled on (section 4). New questions arising from the contract review will be
posted here when it completes.

## 4. Rulings and requests received, with disposition

| item | ruling (`docs/experimental_status_rulings_20260921.md`) | disposition |
|---|---|---|
| **J1** probe rebuild | Defer. Keep the inert-probe diagnostic and the implemented policy's negative result **with their actual scope** — not "uninterpretable". Model-generated *public* inputs are not inherently disqualifying. **My 3-probe/80% rule is rejected** (no demonstrated link to held-out improvement). No removing roots after seeing low discrimination. | **Accepted.** My "calling every result uninterpretable" overcorrected; the negative result stands with its scope. No rebuild until its role in the primary experiment is frozen. |
| **J2** power contract | Separate optional hypothesis. Prospective quality-and-cost contract with frozen family weights, ΔQ > −δ and ΔC > s_min, conservative Hoeffding bound (radius .1614 for one joint decision at 230 equal-weight independent families). Sample size is not a certificate. **Correct the v2 wording before proposing a run.** | **Accepted and applied** — v2 sections 4–5 withdrawn with a correction banner. |
| **J3** g1a fit/eval split | **Do not discard G1a** for my stated reason: task-level folds, training-only fitting and no evaluation-root outcome labels in fitting. Decision-time features are not automatically leakage. Real limits remain (future-routing filter, `n_fail==0` proxy, variable banks, reused labels). | **Accepted — my reading was wrong.** G1a is kept as a qualified historical diagnostic; `scripts/recheck_selection.py` is authoritative. |
| **J4** task curation | Bounded existing curation, not a new pool search. Jaccard is a duplicate screen, not an independence certificate. Order: (1) acknowledge + correct wording, (2) inspect the 7 contracts and propose a versioned 402 repair without excluding p = 1, (3) runtime spec. Bound: one CPU worker, 30 min, zero model calls/executions/installs, $0. | **(1) done** this cycle; **(3) done** (`docs/receiver_runtime_spec_20260921.md`); **(2) running.** |
| Corrections to live status | real ISO timestamp; point E0 to corrected docs; A3 as conditional descriptive; historical checks ≠ contract validation; enumerated-flag absence ≠ zero bias | **All applied** — `docs/audits.md`, `docs/e0_results.md`, `docs/selection_decision_v2.md`, this file. |
| **Resolution `e7eb925`** (`docs/worker_issues_resolution_20260921.md`) | 5 pp working useful-gain threshold (a new prospective lead decision); no categorical feasibility; pilot claims narrowed; order MRL-05 → 06 → 07 | **Accepted in full.** MRL-05 and MRL-06 are completed this cycle; MRL-07 is running. |
| **Development judgment `07fa225`** (`docs/development_delivery_judgment_20260921.md`) | Wilson intervals and nested sizing wrong; "history-specific" is a syntactic cue; reproduction ≠ replication; the postflight check is digest-only | **Accepted.** All four are corrected in `docs/dev_release_v1_results.md` and `docs/confirmatory_sizing_20260921.md` (original text kept) and in this file. |
| **Public-diagnostic design `1e85541`** (`docs/public_diagnostic_design_20260921.md`) | Five arms N0/S0/N1/S1/R1, one shared executed public diagnostic, 77-call ceiling proposed, not released | MRL-07 is reviewing the plan and freeze fields; nothing will be collected. |
| Earlier: post-treatment selection, `validation.passed`, probe provenance, G1c picker, closest≠matched cost, personalization value, fixed-bank ceiling scope | — | Accepted (`docs/selection_decision_RETRACTED.md`). |

## 5. Next, in order

1. **[CPU, done] MRL-07.** See `docs/public_diagnostic_implementation_plan_mrl07_20260921.md`. It is
   waiting on the lead to accept the plan and to rule on the defect-class exposure issue.
2. **[CPU, after the lead accepts MRL-07]** Implement the public executor, diagnostic renderer and five-arm
   collector on `landmark-v2`, with mock tests. No execution until the lead releases a validation contract.
3. **[Lead decisions pending, not mine]**
   - uncertainty procedure (Wald, empirical Bernstein or Hoeffding);
   - R;
   - target population and weights;
   - resource ceiling.

   These dominate the precision plan.
4. **[CPU, bounded, when released]** Semantic, prior-family and specification review of screened candidates
   to count **eligible independent families**. This is the input the precision plan cannot assume.
