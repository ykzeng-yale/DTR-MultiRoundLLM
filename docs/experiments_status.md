# Experiments status — live, for the theory workstream to judge

**Owner: experiments workstream. Published every 30 minutes** by an in-session job (the earlier
durable scheduled task stalled on a permission prompt after one run and has been disabled — the
~9-hour silence from 2026-09-20T23:20Z was that failure, not a pause in intent). Purpose: publish
results and intended designs often enough to catch a wrong direction before it costs GPU time.

**Last updated: 2026-09-21T12:55Z**

## 1. Executing now

| job | state | bound | started |
|---|---|---|---|
| Independent static review of the 7 landmark contracts + versioned 402 reference repair (J4 item 2) | **completed** — 2 suite defects fixed in v2, 402 repair holds | zero executions of reference/candidate/control code; stdlib oracle arithmetic only; no model calls; no installs | 2026-09-21T12:40Z |

GPU: **free of generation load.** The sibling `DTR-AgentEvals` completed every stage (log, live,
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

**Withdrawn, not to be cited:** STOP; the critic/prompt/generator cut-list; "five lines converged";
the double-counted ceiling; `W = 1` as stated; ESS lower bound as ESS; G0e as budget-general; v2
sections 4–5 (outcome-selected power counts, no-harm from *n*).

## 3. JUDGEMENT REQUESTED

None open. J1–J4 were ruled on (section 4). New questions arising from the contract review will be
posted here when it completes.

## 4. Rulings and requests received, with disposition

| item | ruling (`docs/experimental_status_rulings_20260921.md`) | disposition |
|---|---|---|
| **J1** probe rebuild | Defer. Keep the inert-probe diagnostic and the implemented policy's negative result **with their actual scope** — not "uninterpretable". Model-generated *public* inputs are not inherently disqualifying. **My 3-probe/80% rule is rejected** (no demonstrated link to held-out improvement). No removing roots after seeing low discrimination. | **Accepted.** My "calling every result uninterpretable" overcorrected; the negative result stands with its scope. No rebuild until its role in the primary experiment is frozen. |
| **J2** power contract | Separate optional hypothesis. Prospective quality-and-cost contract with frozen family weights, ΔQ > −δ and ΔC > s_min, conservative Hoeffding bound (radius .1614 for one joint decision at 230 equal-weight independent families). Sample size is not a certificate. **Correct the v2 wording before proposing a run.** | **Accepted and applied** — v2 sections 4–5 withdrawn with a correction banner. |
| **J3** g1a fit/eval split | **Do not discard G1a** for my stated reason: task-level folds, training-only fitting and no evaluation-root outcome labels in fitting. Decision-time features are not automatically leakage. Real limits remain (future-routing filter, `n_fail==0` proxy, variable banks, reused labels). | **Accepted — my reading was wrong.** G1a is kept as a qualified historical diagnostic; `scripts/recheck_selection.py` is authoritative. |
| **J4** task curation | Bounded existing curation, not a new pool search. Jaccard is a duplicate screen, not an independence certificate. Order: (1) acknowledge + correct wording, (2) inspect the 7 contracts and propose a versioned 402 repair without excluding p = 1, (3) runtime spec. Bound: one CPU worker, 30 min, zero model calls/executions/installs, $0. | **(1) done** this cycle; **(3) done** (`docs/receiver_runtime_spec_20260921.md`); **(2) running.** |
| Corrections to live status | real ISO timestamp; point E0 to corrected docs; A3 as conditional descriptive; historical checks ≠ contract validation; enumerated-flag absence ≠ zero bias | **All applied** — `docs/audits.md`, `docs/e0_results.md`, `docs/selection_decision_v2.md`, this file. |
| Earlier: post-treatment selection, `validation.passed`, probe provenance, G1c picker, closest≠matched cost, personalization value, fixed-bank ceiling scope | — | Accepted (`docs/selection_decision_RETRACTED.md`). |

## 5. Next, in order

1. **[CPU, done]** 7-contract review and versioned 402 repair — see `docs/landmark_contract_review_20260921.md`.
2. **[CPU, next bounded job]** Hash every GGUF shard and freeze an explicit system message, per
   `docs/receiver_runtime_spec_20260921.md`.
3. **[CPU, after a committed validation contract + containment check]** Isolated reference and
   negative-control execution for the 7 contracts, including original-vs-repaired 402.
4. **[GPU, needs a complete freeze]** The frozen same-prefix prompt study named by the rulings as the
   next empirical milestone — not proposed until 1–3 pass.
