<!-- Seeded by the experiments workstream, 2026-09-19. NOT YET FROZEN. -->

> **Historical snapshot; conclusions require the 2026-09-20 corrections.** Read [continuation report](continuation_report_20260920.md), [theory reconciliation](theory_reconciliation_20260920.md), [experiment audit](experiment_recheck_20260920.md), and [literature recheck](literature_recheck_20260920.md) before using this document. Earlier universal impossibility, optimality, matched-cost kill, and feature-no-signal claims are superseded. Original text remains for provenance.

# Experimental program (draft, not frozen)

> **Status.** Produced by a 21-agent design workflow (six design specs, three
> feasibility analyses, a five-lens adversarial artifact hunt, then synthesis), and
> already reconciled against this project's own audits in two places noted inline.
> It is a **draft**: the freeze checklist in section 3 has not been executed, ten
> theory questions in section 9 are open, and the pilot in `docs/pilot_findings.md`
> landed after this was written and invalidates two of its cost claims. Read it with
> `docs/positioning.md`, `docs/premise_findings.md`, `docs/audits.md` and
> `docs/pilot_findings.md`.
>
> **Two reconciliations the experiments workstream has already applied since:**
>
> 1. **The confirmatory pool is 561 tasks, not 478.** This draft derives the pool by
>    intersecting with "tasks where a visible verdict is definable", and takes that to
>    need a `>>>` doctest, giving ~73 of 164 HumanEval tasks. Audit A4
>    (`experiments/common/scoring.py`) makes a visible verdict definable for **156 of
>    164** by splitting `check` at assertion level and holding out the first
>    assertion, exactly as MBPP does. POOL A intersected with scoring-usable is
>    **561**; the informative band inside it is **230**.
> 2. **The three "incompatible" repair rates are not incompatible — they are three
>    different interventions.** This draft's G0f flags 0.104, 0.239 and 0.249 as a
>    contradiction. They are not: **0.239** (audit A3) is the sibling project's repair
>    loop, which pastes *execution output* from failing visible checks; **0.110**
>    (`docs/pilot_findings.md`) is A1, a content-free retry; **0.066** is A3 as a
>    *structural* AST-span pointer with no execution evidence. Read in order, they say
>    the information that matters is **execution output, not structural pointing** —
>    which is why this draft is right to redefine P3's A3 as execution-grounded, and
>    why the pilot's negative contrast tested the weaker variant. G0f should reconcile
>    them as a definitional table, not treat them as a defect.

---

# EXPERIMENTAL PROGRAM — DTR-MultiRoundLLM

**Single authoritative experimental program document. Experiments lead. 2026-09-19.**
**Repo HEAD at writing: `6f95ffdce9c6852076028c3228f2d254bf7ecc03`. `work/data/tasks.json` sha256 `23727895971fa4a040198d8770173a4f0c3263a63a9cb1479abc4203bb01c2ce`, 591 tasks (427 MBPP + 164 HumanEval).**
**Status of every row below: PLANNED. Nothing in this program has been run confirmatorily.**

Every number is tagged **(M)** measured on this machine, **(M\*)** measured from the sibling's completed 4,488-episode log, **(D)** design choice with its reason, **(A)** assumption with the named measurement that pins it, or **(C)** an explicit written concession. Nothing is recalled and presented as fact.

---

## 0. The restructuring, stated first

The adversarial review returned 24 fatal and major findings. They do not decompose into 24 independent patches. They converge on one sentence:

> **The program as specified spends 58–61 GPU-hours resolving contrasts *between* feedback classes while the question of whether feedback beats an independent resample at all is unmeasured, costs ~5 GPU-hours, and is signed negative by the project's own data.**

Four measurements force this, all from our own files:

1. **(M\*)** The only multi-turn pipeline that exists here already loses to the dumbest comparator. Re-analysed over 561 tasks with ≥4 independent runs on the 3B: multi-turn final success 0.6569 at 118.6 completion tokens; oracle best-of-2 0.6887 at ~133. Paired difference **−0.0318, 95% CI [−0.0461, −0.0175]**, discordant on 30.1% of tasks. Against best-of-3, −0.0753.
2. **(M)** The comparator was priced wrong in the one way that decides the paper. Best-of-N with *early stopping on the visible check* has the identical outcome law as non-adaptive visible-check selection and strictly dominates it on cost. At the measured P(U₁=1)=0.674 it needs 1.33/1.43/1.47 expected draws for N=2/3/4, so adaptive best-of-4 reaches 0.7287 at **97.1** completion tokens against the multi-turn loop's 0.6954 at 87.3. E4's gatekept non-inferiority test fails on E4's own numbers with a lower bound ≈ −0.055.
3. **(M)** The prize for adaptivity is smaller than every instrument in the program. In E0's own exact DP: V(always LOCALIZE, never STOP) = 0.6970; the exhaustive optimum over all 5⁶ deterministic U-only rules = 0.7180. **The entire value of adaptivity available to any deployable rule is 0.0210** — below E1 MEDIUM's MDE (0.041, and 0.055 once its variance constant is corrected), below E2's repair MDE (0.058), below E4's non-inferiority margin (0.030), and below the taxonomy's own seed-noise floor (0.028).
4. **(M)** The one pilot that measures the program's primary proximal contrast measures it with the **opposite sign** to the value every power calculation assumes: ρ(A1) = 0.104, ρ(A2) = 0.146, **ρ(A3) = 0.042**. E2 is powered at an assumed true ρ_A3 − ρ_A1 = **+0.10**. E0's DGP hard-codes θ_LOCALIZE > θ_RETRY as a design choice and then congratulates the estimators for recovering it.

So the program is restructured into three gates, and the expensive artifacts are conditional on the cheap ones:

- **Gate 0 — 0 GPU-hours.** Repair the outcome variable, build the harness, pin the engine, extend E0 to the geometries that will actually run and to the baselines it currently cannot express, build the P-suite, re-analyse the existing log under correct baseline pricing, reconcile the calibration constants, and freeze the multiplicity plan. Startable today, beside the foreign load. ~20 CPU-hours plus ~2 developer-days.
- **Gate 1 — 12.6 GPU-hours, 13,244 rollouts.** One decisive stage that delivers **five of the six program primary outcomes** and fires four of the twelve kill criteria. It replaces the 22.8→27.6 GPU-hour branch tree as the first GPU spend.
- **Gate 2 — 35.0 GPU-hours.** The tree, the sequential factorial, the MRT and the stopping design, run **only if Gate 1 passes**, and sized from Gate 1's *realised* variance rather than from a pilot of n=4.
- **Gate 3 — 25.2 GPU-hours.** Critic, transfer, observational slice. Each a clean stopping point.

Minimum publishable: **47.6 GPU-h** (71 with contingency). Comprehensive: **72.8 GPU-h** (109 with contingency). If Gate 1 kills the program, total spend is **12.6 GPU-h** and the paper is the negative plus the methods.

---

## 1. The experiment ladder

Cost constants, all **(M)** end-to-end on this machine under the live foreign load, attaching to the siblings' existing `llama-server` on port 8193 at `-np 4` (so the program needs zero additional GPU memory and starts no server of its own): **root/depth-1 call 2.89 effective GPU-s** (1,246 calls/h), **depth-2 4.05 s** (888/h), **depth-3 4.88 s** (738/h), 7B = 1.47× per call. These supersede the brief's 116/67 tok/s (2.3×/2.6× optimistic) and `measured_calibration.md`'s 4,500 calls/h (not reproduced). Per-call cost is **not flat** — it rises ~70% from turn 1 to turn 3 — which is the primary structural error in every prior cost line. Wall-clock ≈ **2× GPU-h** at the 2 effective slots available under foreign load.

| id | question | design | unit | n | GPU-h | CPU | depends on | status |
|---|---|---|---|---|---|---|---|---|
| **E0a** | Do the estimators recover truth under a known law, **at the geometries that will actually run**? | 17-cell grid **+ 6 new cells**: 9 arms at ε ∈ {1/9, 0.05, 0.03}; verdict-stratified 4/3 option sets with E2's exact structure; **F2 (coarsening) and F4 (misclassification) actually piloted** | replicate | R=1000 × 23 cells | **0.00** | 16 CPU-h | — | planned |
| **E0b** | How big is the prize? | Exact backward induction with **three new rows** — V(best fixed class, never STOP), V(best fixed class + STOP-on-U), V\*(U-only optimum by exhaustive 5⁶ enumeration) — and a **new RESAMPLE arm** whose kernel is the marginal P(S₁\|E), which makes V(adaptive best-of-N) computable in the DP | exact | n/a | **0.00** | <1 CPU-min | E0a | planned |
| **E0c** | Re-anchor E0 | Re-solve MU against the reconciled first-attempt and repair rates from G0f; re-run the power grid | exact | n/a | **0.00** | 20 CPU-min | G0f | planned |
| **G0a** | **Is Y a function of the code?** | CPU-time-limited verifier (RLIMIT_CPU binding, wall ≥60 s as liveness only); G-HACK AST gate; canary wired into the **grading path**; **three-valued outcome** pass/fail/indeterminate; verdict invariance across {1,4,8,16} verification concurrency × canary on/off × all 591 references | task × config | 591 × 8 | **0.00** | 1.5 CPU-h | — | planned |
| **G0b** | Which tasks have an undefined or fragile outcome? | 8-stub trivial-pass battery; 7-mutation kill discrimination; prompt-literal assert drop; **per-task timeout quarantine list** | task | 591 | **0.00** | 0.6 CPU-h | G0a | planned |
| **G0c** | Does the harness survive a shared GPU? | Write the receiver client, runner, tree store, chunked-resume layer; drive end-to-end against a **mock server**; 13-test suite incl. crash-mid-write, torn tail, content-hash `state_id`, persisted selection records | n/a | — | **0.00** | ~2 dev-days | — | planned |
| **G0d** | Is the environment pinned? | Copy llama.cpp source + binary out of the foreign disposable scratchpad; pin commit, binary sha256, **every GGUF shard** sha256; freeze an **explicit system message**; assert `/props` `build_info` and **per-slot `n_ctx`** at every chunk | n/a | — | **0.00** | 1 CPU-h | — | planned |
| **G0e** | Does multi-turn beat **adaptive** best-of-N on the only completed log? | Re-analysis of the 4,488-episode log with adaptive-BoN pricing, all five cost ledgers, oracle and visible pickers, paired over 561 tasks, unbiased 1−C(r−s,k)/C(r,k) | task | 561 | **0.00** | 0.2 CPU-h | G0a | planned |
| **G0f** | Reconcile the four incompatible first-attempt rates and three repair rates | Definitional audit + re-grading of all existing logs under the repaired verifier; one table naming each prior number's pool/format/grading difference | task | 591 | **0.00** | 0.5 CPU-h | G0a | planned |
| **G0g** | Build and certify the P-suite | AST-only opaque rename, L1/L2/L3; reference re-certification against renamed hidden tests | task | 591 | **0.00** | 40 CPU-s | G0b | planned |
| **G0h** | Freeze the multiplicity plan | 6 program primaries under Holm over the union; sup-t band calibration; single permutation test for the ordering claim; one pre-declared scalar per estimator | n/a | — | **0.00** | 2 CPU-h | all G0 | planned |
| **G1a** | What is the state population, the U/V joint, the difficulty law, **v̄ and SIG on our own format**? | 478 tasks × **8 independent seeds**, visible and hidden checks run separately; also yields σ_k and adaptive-BoN for every k ≤ 8 free, and the independent-redraw arm for G1b | task | 3,824 rollouts | **3.07** | 0.1 | G0a–G0h | planned |
| **G1b** | **γ_cond: does conditioning on O₁ beat an independent redraw?** | Paired within state: P(∃ correct in {O₁, O₂^fb}) vs P(∃ correct in {O₁, O₂^iid}); the iid arm costs nothing, drawn from G1a's spare seeds | state | 300 states | **0.00** | — | G1a, G1c | planned |
| **G1c** | ρ and β for the four weight-bearing classes, with the length and verdict controls | 300 states (150 V₁=0, 150 V₁=1; 4 balanced benchmark × verdict cells of 75) × {A0 free, A1, **A1-PAD**, A2, **A3-traceback**} × S=4; arm order randomised from the frozen seed table; shared-prefix warm-up call per state | state | 4,800 rollouts | **5.40** | 0.2 | G1a | planned |
| **G1d** | Does any repair effect survive semantics-preserving perturbation? | P-suite L2 twins of 150 of G1c's tasks: 600 roots + 150 states × {A1, A2} × S=4, paired at task level | state | 1,800 rollouts | **1.83** | 0.1 | G0g, G1c | planned |
| **G1e** | Contamination gate | Δ_perturb (300 tasks, P-suite arm only, k=2) + elicited hidden-test probe (300 × 2) scored on **entry-point-anchored AST call-keys** against a within-benchmark 1,000-fold permutation null | task | 1,200 rollouts | **0.96** | 0.1 | G0g | planned |
| **G1f** | Does any class transfer the answer? | Blind-receiver probe, 300 messages/class × {A1, A1-PAD, A2, A3, A8}; **exact one-sided 95% upper bound** on the lift vs 0.02, not a point estimate | message | 1,500 | **1.20** | 0.1 | G1c | planned |
| **G1g** | Compliance, and A6's extraction confound | A6 fenced-block-rate probe on real t=1 outputs; diff locality (A3), overlap collapse (A2), trace presence (A4), patch adoption (A8) on G1c's realised outputs | rollout | 120 new | **0.14** | 0.1 | G1c | planned |
| **G2a** | The 8-class ladder | Extend to N=600 states: {A1, A1-PAD, A2, A3} on 300 new states × S=4; {A4, A5, A6} on 600 × S=3; {A7, A8} on 200 × S=3 (design-only) | state | 11,400 | **12.83** | 0.4 | Gate 1 PASS | planned |
| **G2b** | Sequential estimands — the only reason this is longitudinal | Depth-2 **factorial**: 150 states × F₁{A1,A2,A3} × 2 carried depth-1 rollouts × F₂{A0 free, A1, A3} × S=3 | state | 5,400 | **7.32** | 0.2 | G2a | planned |
| **G2c** | Design-identified turn-level effects and regime values under a real sequentially randomised history | Verdict-adaptive MRT, option sets of 4 and 3 at floors 0.25/0.333, difficulty-stratified 24/10 allocation, **adaptive-BoN regimes R0a–R0c added to the confirmatory set** | episode | 3,870 ep / 9,850 calls | **9.43** | 0.3 | Gate 1 PASS | planned |
| **G2d** | Stopping and cost, against the adaptive-BoN **frontier** at matched total tokens **and** matched per-call latency | Stage-C continuations net of tree overlap; both return rules (return-last, ratchet) read off the same recorded paths; all five ledgers | state / path | 4,400 | **5.46** | 0.2 | G2a | planned |
| **G3a** | Does causal machinery change decisions? | 73% of in-class baselines evaluated by **tree branch selection** (exact, not approximate); **B4p** prediction-only baseline added; σ_k and best-fixed-class added; live Self-Refine arms; 3rd seed on the fit/eval subset | unit | 6,463 | **7.50** | 0.3 | G2a, G2c | planned |
| **G3b** | Receiver transfer | 7B, Coder-7B, granite-8B, **sequenced one at a time** (they cannot co-reside); 200 states × 7 arms × 2 seeds each | state | 10,600 | **17.09** | 0.4 | G3a | planned |
| **G3c** | Task-family transfer (MBPP ↔ HumanEval) | Fit on one stratum's states, evaluate on the other's, same tree | state | 0 new | **0.00** | 0.2 | G2a | planned |
| **G3d** | Intervener transfer | I2 = 3B paraphraser, I3 = granite paraphraser, cached one paraphrase per (state, class), **every paraphrase re-cleared through G1–G5, round-trip, the 8–16 word band, and the blind probe**; rejection rate per class is itself a primary of this arm | state | in G3b line | **—** | 0.2 | G3b | planned |
| **G3e** | Observational slice | ω on DevGPT (CC-BY-4.0, Zenodo 16392320) with multinomial CIs and the abstention rate; adoption-proxy association, labelled *descriptive, not causal*; per-turn MSM with Λ^τ; two negative controls; 200-turn replay probe | turn | 400 labelled | **0.57** | 1 CPU-h | IRB (Q8) | planned |

**Pool (D).** POOL A = 591 − 22 trivial-stub-passable − 5 HumanEval left with <2 scored asserts = **564** (M). Intersect with {U_t is definable}: MBPP 405, HumanEval-with-doctest ~73 → **confirmatory pool 478 tasks**, minus the G0b timeout quarantine list (`mbpp/123` is on it today at 8.05 s of a 10 s limit with canary on). The 86 HumanEval tasks with no `>>>` doctest become an explicitly labelled `u_source="exec_only"` exploratory stratum, never pooled. Benchmark is a **blocking factor**, never a pooled nuisance.

---

## 2. The ordered critical path

CPU-only steps are marked **[CPU]** and are startable **now**, beside the foreign 4,488-episode run (PIDs 63657/63658 from `ICLR-WinRatioAgentEvals`, load average 11.98 at writing, 3,808 free pages).

1. **[CPU] G0a — repair the outcome variable.** This is first because it is fatal and everything depends on it. Y is currently **not** a function of the code: the mandatory anti-hack canary re-runs one hidden assert with a corrupted expected value, doubling runtime, and `mbpp/123`'s *reference* solution then crosses the 10 s wall-clock timeout at **3 concurrent verifications** — below the 4 the throughput budget requires — and is graded Y=0. Fix: CPU-time as the only binding limit, wall ≥60 s as liveness, a **three-valued** outcome with timeouts mapped to *indeterminate and never to 0*, per-task calibration at the run's real concurrency, and a quarantine list.
2. **[CPU] G0b — audit the data, not only the code.** The trivial-pass battery raises the passable-by-stub count from the 1 task `docs/audits.md` reports to **22** non-`__eq__` stubs and **557/591 (0.942)** for a universal-`__eq__` object. Mutation-kill discrimination: 0.8656 overall [0.8490, 0.8820], with 47 tasks at ≤0.50 and 2 at 0.00.
3. **[CPU] G0c — build the harness.** There is no receiver client, no runner, no tree store, no resume layer anywhere in the project: 3,936 implemented lines, all of it E0, audits, premise checks and `common/`, and `experiments/env/` holds one JSON file and no Python. Every abort condition in every design presupposes machinery that does not exist. Drive it end-to-end against a mock server; make `state_id = sha256(task_uid, root_seed_index, config_sha256, design_sha256)` so it is stable whether or not the rollout reproduces.
4. **[CPU] G0d — pin the environment.** The inference engine is a 33,472-byte binary in a *different project's* disposable session scratchpad under `/private/tmp`. Copy it, pin the commit (`b1-4fea119`), hash every GGUF shard (the 7B is split, two parts), freeze an explicit system message (the `--jinja` template silently injects 29 tokens of *"You are Qwen, created by Alibaba Cloud…"* in front of every rollout), and correct the per-slot context: `-c 32768` sizes the **total** KV pool, so at `-np 4` the real per-conversation budget is **8192**.
5. **[CPU] G0e — re-analyse the existing log under correct baseline pricing.** Zero GPU, 0.2 CPU-hours, and it fires kill criterion K1 or clears it before a single new token is generated.
6. **[CPU] G0f — reconcile the calibration constants.** MBPP first-attempt is reported at 0.812, 0.435 and 0.6186; repair under a content-free retry at 0.104, 0.239 and 0.249. E0's own hard abort A4 fires if realised repair leaves [0.210, 0.270], and 0.104 is outside it — so E0's sizing authority is running off its anchors by its own stopping rule.
7. **[CPU] G0g — build the P-suite.** 590/591 certify in 38 CPU-seconds.
8. **[CPU] E0a/E0b/E0c — extend and re-anchor the reference simulator.** E0b is the cheapest decisive number in the program: it prices the prize.
9. **[CPU] G0h — freeze the multiplicity plan.**
10. **FREEZE v1** (§3). Record the commit id. Nothing after this point may change without a new run directory.
11. **[GPU] G1a — roots.** The first GPU spend, and also the variance-calibration stage: v̄ and SIG are measured from 3,824 real rollouts *before* the continuation budget is committed.
12. **[GPU] G1e / G1f — contamination and leakage gates.** Both before the core contrast, because a contaminated pool or a leaking class must never consume confirmatory budget.
13. **[GPU] G1c / G1b / G1d / G1g — the core contrast.** Resumable in chunks of ≤2 GPU-hours; the resumable unit is one state (20 calls ≈ 81 GPU-s), so a 10-minute foreign gap is ~7 states of useful work.
14. **GATE 1 DECISION.** Evaluate K1–K11 in writing, against the pre-registered thresholds, before looking at anything else.
15. **[GPU] G2a → G2b → G2c → G2d**, sized from Gate 1's realised v̄ and SIG.
16. **[GPU] G3a → G3b/G3d → G3c → G3e**, each a clean stopping point.

**Scheduling reality (M).** One GPU. Two resident foreign servers cost memory, not throughput — they share the single M5. Wired memory is ~14.5 GB of 32 GB and swap is 18.7 of 19.5 GB used; a third 8–9 GB receiver **cannot** be created by reclaiming inactive pages, because GPU-resident weights and KV are non-pageable. Consequences: attach, never launch; sequence receivers with an explicit run boundary per swap; launch at `-c 8192 -np 4` so the flag states the real per-slot budget and frees ~1.5 GB of wired KV; and enforce **one global concurrency budget** shared by E0's CPU grid, the verification workers and the GPU stages — because E0's six spawn workers at 85% CPU are precisely the load at which the verification timeout cliff flips Y.

---

## 3. Pre-registration freeze checklist

Committed and hashed **before the first model call**. The freeze commit id is recorded in `design.json`, and every episode, decision and tree node carries the hash set.

**Protocol and configuration**
1. This document, as `docs/program.md`, with the freeze commit id filled in.
2. `config.json` per stage, with every decoding parameter sent **explicitly on every request** (temperature, top_p, top_k, min_p, repeat_penalty, max_tokens, seed, cache_prompt) — the server's own `/props` defaults include `min_p 0.05`, so leaving anything implicit makes it a silent unrecorded parameter. `_config_sha256` attached from the raw bytes.
3. The **explicit system message text** and its sha256.
4. Verification concurrency, worker count, CPU-time limit, wall liveness limit, and the global concurrency budget.

**Frozen pre-registration payload (hashed separately from the harness)**
5. `frozen/taxonomy.py` — promoted from `work/taxonomy_proto/`, with the import-time 14,184-message audit moved behind a `__main__` guard (it currently runs on import, and on macOS `spawn` every pool worker would re-run it) and the dead `if False` branch in the A7 arm removed.
6. `frozen/lexicons.json` — REQ_LEX, PROC_LEX, DIVERT_LEX, and the new **A1-PAD** 13-word filler bank, lifted out of code.
7. The **redefined A3**: the span is the line reported by the visible assert's traceback (from the smoke run), not an arbitrary AST node. Its information cap is re-measured and reported.
8. `frozen/leakgates.py` — G1 (novel-reference 4-grams, `ngrams₄(ref) − ngrams₄(prompt)`; the subtraction is mandatory — a median 70.5% of HumanEval reference 4-grams are already public), G2 (structural), G3 (hidden-input AST call-keys), **G6 (expected-output literal multiset at ≥2-gram granularity)**, **G7 (targeting-channel mutual information)**, and G4/G5 computed-and-reported-but-never-gating.
9. `frozen/families.json` — the family partition **as a file**, plus the generating code, the stop list, the tokenizer regex and the minimum token length. The stated rule is not reproducible from the spec today (176 families vs 169 on re-implementation) and it is both the cross-fitting unit and the bootstrap unit.
10. `frozen/pool.json` — the 478 confirmatory uids, the 86 exec-only uids, the exclusion list with a reason string per task, the per-task mutation-kill score, the per-task hidden-assert count after prompt-literal drops, and the timeout quarantine list.
11. The A3-admissibility indicator and the A3/A7 byte-identity indicator, per task.

**Design**
12. `design.json` + `design.sha256`, written once by code that **refuses to overwrite**: master seed, per-task family-level split into 5 folds, the pre-drawn uniform vector per episode per turn, the per-state option sets and the exact `p_vec` with its floor, T_max, the state-selection table with **selection probabilities stored per state**, and `freeze_commit`.
13. The arm-order randomisation table (so cache state cannot correlate with class).

**Analysis, frozen before any data exists**
14. `dtr/estimators.py` (multi-arm generalisation with the two-arm regression test against `estimators_absorbing.py`), `dtr/truth.py` (with **seed-split argmax**), and the per-stage `analysis.py` producing only the pre-specified outputs.
15. The primary/secondary outcome list of §5, verbatim.
16. The multiplicity plan: 6 program primaries, Holm over the union, the sup-t band construction, the permutation reference for max-over-classes, the single Kendall-τ permutation test for the ordering claim, and the one pre-declared scalar per estimator.
17. The kill criteria of §6, verbatim, with their thresholds.
18. The bootstrap seed (20260919) and B.

**Environment and hygiene**
19. `experiments/env/` — llama.cpp source + binary copy, upstream commit, binary sha256, build script, every GGUF shard sha256, `/props` snapshot with `total_slots`, per-slot `n_ctx`, `build_info`, `model_path`, chat-template name, and `props_sha256`.
20. The manifest schema, and the per-rollout record schema including `prompt_n`, `cache_n`, `cached_tokens`, `finish_reason`, `system_fingerprint`, `canary_built`, `canary_survived`, `gate_hits`, `verification_concurrency`, `loadavg_at_start`, foreign server PIDs and aliases, and `nondeterministic_replay`.
21. The 13-test suite, green, plus a mock-server end-to-end run written under `work/`, never `results/`.
22. `tests/test_e0.py` abort checks A1–A3 passing.

---

## 4. Pool and instrument decisions that the freeze settles

| decision | resolution | evidence |
|---|---|---|
| Visible verdict on HumanEval | **Exclude** the 88 tasks with no `>>>` doctest from the confirmatory pool; carry them as `u_source="exec_only"` | `split_tests()` returns `visible=[]` for HumanEval (M); only 76/164 have a doctest |
| HumanEval hidden granularity | Assert-level AST surgery: splittable for 157/164, indivisible conjunction with `splittable=False` for 7 | (M) |
| Prompt-literal collisions | Drop every assert all of whose `candidate(...)` literals appear in the public prompt: 205/1,176 asserts, 84/164 tasks affected, **only 5 tasks** fall below 2 scored asserts | (M) |
| `signature_example` | Byte-identical to `test_list[0]` for **427/427** MBPP. Stripped from every record the intervener path can reach. Any template filling a slot from it is A8 in disguise | (M) |
| `challenge_test_list` | Empty for 427/427 — there is no reserved hidden layer | (M) |
| Arm count vs positivity floor | 9 × 0.20 = 1.80 is impossible. Live randomised stages use **4/3 verdict-stratified option sets** at floors 0.25/0.333. In the tree, positivity is 1.0 by construction and the floor binds only the *simulated* log, where ε ∈ {1/9, 0.08, 0.05, 0.03} with 0.02 as a stress cell | arithmetic + (M) |
| The informativeness screen | **Abolished (D).** Select states on a *task-level covariate* (the K=8 root pass count, informative band 1 ≤ k ≤ 7) plus explicit V₁-stratified oversampling, with selection probabilities stored and carried as known weights | see §7 |

---

## 5. Primary and secondary outcomes, fixed in advance

### 5.1 Program-level primary outcomes — six, under Holm over the union

α = 0.05 two-sided across the **union** of the six, so every pointwise MDE is multiplied by **1.24** (z = 2.638 rather than 1.96). This is not a formality: the program as it stood declared ~15 primaries and reported on the order of **2,000** inferential quantities (E1 ≈1,460, E2 ≈152, E4 ≈117, E5 ≈270), with Holm applied only within each design's own families and **not one simultaneous MDE anywhere**.

| # | outcome | definition | stage | pointwise MDE | α-split MDE |
|---|---|---|---|---|---|
| **P1** | **γ_cond** | P(∃ correct in {O₁, O₂^feedback}) − P(∃ correct in {O₁, O₂^iid}), paired within state, over the 300 Gate-1 states | G1b | 0.057 | 0.071 |
| **P2** | ρ(A2) − ρ(A1) | repair on the V₁=0 stratum; A2's entire content is a frozen 14-word discard instruction with no task literal, so this is the one contrast no leakage critique can dissolve | G1c | 0.057 | 0.071 |
| **P3** | ρ(A3-traceback) − ρ(A1) | the content-of-feedback contrast, at the **redefined, execution-grounded** A3 | G1c | 0.057 | 0.071 |
| **P4** | β(A1), β(A2), β(A3) | breakage **levels** on the V₁=1 stratum, tested as a **max-over-classes statistic against a permutation family-wise threshold**, not as three independent levels. β is primary because it is the number that decides whether a class belongs in a deployed policy | G1c | ±0.030 half-width | ±0.037 |
| **P5** | Δ_dominance | V(best in-class multi-turn regime) − V(adaptive best-of-N) at matched **total** tokens (prompt+completion, price ratio swept 1:1/1:3/1:10) **and** at matched per-call wall latency with the receiver's 4 parallel slots | G0e descriptive → G2d confirmatory | 0.041 | 0.051 |
| **P6** | Sign preservation | agreement in sign of P2 and P3 between the original tasks and their P-suite L2 twins, paired at task level | G1d | sign test, n=150 | — |

Five of the six are delivered by Gate 1. Only P5's confirmatory half needs Gate 2, and its descriptive half is available today at zero GPU cost.

**The ρ/β decomposition is the reporting unit, not the marginal blip.** For binary Y with STOP as reference, γ_t(a, STOP) = P(V_t=0)·ρ_t(a) − P(V_t=1)·β_t(a). The weights are nuisance mixture proportions, so reporting the marginal blip alone is close to reporting P(already correct). A pooled logistic blip model is **misspecified** — it cannot enforce γ ≤ 0 where P(V_t=0) = 0 — so the specification is two-part and stratified throughout.

### 5.2 Secondary outcomes

Every secondary is reported with its **realised n, its realised half-width, and its MDE**. A null from a design with no stated MDE is nothing.

| # | outcome |
|---|---|
| S1 | ρ(A1-PAD) − ρ(A1) — the length and verdict-weight control (fires K5) |
| S2 | The information ladder A0 < A6 < A1 < A1-PAD < A2 < A4/A5 < A3 < A8, tested as **one** permutation test on Kendall τ against the pre-registered ordering — not 21 pairwise comparisons — with the ~0.028 seed-noise floor shaded |
| S3 | Blind-receiver leakage lift per class: exact one-sided 95% upper bound vs the 0.02 ceiling, with A8 as the detector's positive control (A8 **must** fail; a metric that does not flag A8 is not a leakage metric) |
| S4 | Monte Carlo blip truth at the branched depth, per benchmark × U_t stratum, with **sup-t simultaneous bands** over exactly the quantities plotted, and argmax/value computed on **disjoint seeds** |
| S5 | Estimator grading: **one** pre-declared scalar per estimator (max\|bias\| over the λ × ε grid), plus the remaining cells as a monotonicity display carrying no p-values |
| S6 | Two-stage sequence contrasts on the depth-2 factorial, and a g-formula consistency check against the tree's own two-stage means |
| S7 | V(π̂) − V(**best fixed class**) with a pre-registered ±0.02 equivalence band; a learned policy that cannot be shown to beat a constant is not a policy |
| S8 | V(π_oracle-on-V) − V(π_U) — the value of knowing you are already right — reported as a headline pair with V(π_U) itself |
| S9 | D(π) degradation per regime × return rule (return-last vs ratchet), **with adaptive best-of-N's own degradation in the same table** |
| S10 | Five cost ledgers for every arm; the break-even frontier Λ_λ over the frozen λ grid; `tier_decided` and `tier_contribution` beside every win statistic |
| S11 | Compliance manipulation checks per class, ≥0.70 gate: diff locality (A3), trace presence (A4), output-overlap collapse (A2), patch adoption (A8), fenced-block rate (A6) |
| S12 | Δ stratified by per-task mutation-kill score (≤0.5 vs >0.5), with a sensitivity excluding ≤0.5 |
| S13 | Determinism audit **conditional on `prompt_n`**, plus the unconditional rate and the `nondeterministic_replay` rate, reported separately |
| S14 | Transfer regret with the **oracle-regret scale reference** on the same tree, and the disagreement-rate factor of the decomposition as co-primary of the transfer arm |
| S15 | ω on DevGPT with multinomial CIs and the **abstention rate**; the adoption association in a table headed *descriptive, not causal*; the MSM Λ-value at τ=1 and τ=2; the two negative controls |

### 5.3 Explicitly not outcomes

Whether causal adjustment improves *decisions* in the repair stratum (reported as a finding, not tested as a hypothesis — the premise checks already refute the general claim). Per-state effect recovery at any S. Off-policy evaluation of a win statistic. Any claim about free-form human messages, any receiver other than the frozen one, or the environment channel (tool grants, attachments, added visible tests), which is an *unmeasured* treatment rather than a noisy one.

---

## 6. KILL CRITERIA

Pre-specified, numeric, and written so that we cannot wriggle out later. Each is evaluated in writing, in order, at its named gate, **before** any other analysis of that gate's data. Each names the response.

**K1 — Baseline dominance.** If the upper 95% bound on P5 (Δ_dominance) is **below +0.01** at matched total tokens *or* at matched per-call latency → the multi-turn claim is dead. Do not run G2a, G2b, G2d, G3a, G3b. Report the negative.
*Standing evidence, already against us:* paired multi-turn − oracle best-of-2 = **−0.0318 [−0.0461, −0.0175]** on 561 tasks (M\*); adaptive best-of-4 = 0.7287 at 97.1 tokens vs the loop's 0.6954 at 87.3 (M). Evaluated at **G0e (0 GPU-hours)** and again confirmatorily at G2d.

**K2 — γ_cond.** If the upper 95% bound on P1 is **below +0.02** → conditioning on the prior output does not beat an independent redraw. Cancel Gate 2 and Gate 3. Evaluated at **Gate 1**.
*Standing evidence:* γ_cond computed from our own four measured repair rates against the measured oracle best-of-2 (0.6887) is **−0.062** at ρ=0.066, **−0.044** at ρ=0.110, **+0.007** at ρ=0.239, **+0.030** at ρ=0.297. At its most favourable it is inside Gate 1's MDE.

**K3 — Repair headroom.** If ρ(A1) < **0.05** over ≥120 failing states → every blip is bounded below the α-split MDE. Report as a precision result; do not add seeds. Evaluated at **Gate 1**.

**K4 — Content of feedback.** If the 95% CIs for both P2 and P3 lie **entirely below +0.02** → the pre-registered finding is *"the fact of another turn matters; its content does not, on this receiver and this task family."* That goes in the abstract. **Prohibited response:** adding classes, seeds, templates, or states to chase it.

**K5 — Length confound.** If ρ(A1-PAD) − ρ(A1) accounts for **≥50%** of ρ(A3) − ρ(A1) in point estimate → the "content" effect is a length-and-verdict-weight effect. Reframe; P3 becomes descriptive.

**K6 — Contamination.** If Δ_perturb > **0.15** in either benchmark stratum, **or** π_regurg exceeds the within-benchmark permutation p95, the P-suite becomes the primary pool and every prior number is demoted to secondary. If additionally the **sign** of P2 flips between original and P-suite twins → the effect is recall-unlocking, not repair; the A2 leakage-proof claim is withdrawn. Evaluated at **G1e/G1d**.
*Standing evidence:* 3B/HumanEval anchored own-task hidden-key regurgitation **9/26 = 0.346** against a permutation p95 of 0.050 and max of 0.101 (M) — and E1 puts the entire repair signal on HumanEval.

**K7 — Outcome integrity.** If, after the G-HACK AST gate + canary + CPU-time limits, the attack battery still passes **>0.5%** of the pool, **or** the per-task verdict-invariance test fails at any of {1, 4, 8, 16} verification concurrency → halt. Y is not a function of the code and no estimand is defined. Evaluated at **G0a**, and re-checked continuously.

**K8 — Adaptivity prize.** If E0b's exact DP shows V\*(U-only optimum) − V(best fixed class) < **2× the realised Gate-1 MDE** → the optimal-regime workstream is unpowered by construction; V(π) and optimal-regime claims drop to descriptive before any GPU is spent on them. *This criterion fires on E0's current law:* 0.7180 − 0.6970 = **0.0210** against a Gate-1 MDE of 0.057. It must be re-run against reconciled anchors at **E0c**, and if it still fires, the drop is automatic.

**K9 — Variance and selection.** If the realised post-selection v̄ from G1a exceeds **0.20**, or realised SIG exceeds **0.35** → Gate-1 MDE exceeds 0.075; Gate 2 is re-sized from the pre-registered N→MDE ladder, or the program narrows to non-adjacent class contrasts. No improvisation.

**K10 — Environment drift.** If `system_fingerprint` or `/props.build_info` changes mid-run, or conditional-on-`prompt_n` re-execution agreement on Y falls below **98%** → halt, new run directory, never a resume.

**K11 — Stopping rule harm.** If V(π_U) < V(always-continue with the best fixed class) on the tree's own ȳ table with the CI excluding 0 → the headline stopping claim is false. Reframe around harm avoidance versus best-of-N, or drop it.
*Standing evidence:* in E0's own DP, "A3 while U=0, STOP while U=1" is worth **0.6364** against 0.6970 for never stopping with the same class — the stopping rule destroys 6.1 points, because it forfeits the +0.509 blip at the visible-pass/hidden-fail state (P=0.205). E2 reports the same contrast at **+0.208**. The two simulators disagree by 6× on the program's headline number and neither cross-checks the other. **E0c must reconcile them before Gate 2c freezes.**

**K12 — The no-wriggle clause.** After any confirmatory data is seen, the following are **prohibited**: adding arms, seeds, templates or states; changing the non-inferiority margin δ or the matching ledger; changing the pool; re-defining or promoting an outcome; dropping a failure cell because it failed; re-running a pilot; increasing R; or conditioning a go/no-go or a sample size on the primary effect estimate. Any such change opens a **new run directory**, is labelled exploratory, and cannot support a confirmatory claim. No completed run is ever overwritten.

---

## 7. Controls added in response to the artifact hunt

Every fatal and major finding is answered by a design change, an added control, or an explicit written concession. Concessions are marked **(C)** and are stated in §10.

### 7.1 Answered by a design change

| finding | change |
|---|---|
| E3's headline Δ vs B4 isolates nothing causal — it is state-conditional prediction of V plus an extra CPU-side program execution | **B4p** added ("stop iff p̂(V=1) < c, else A1"; same features, same folds, no blip model, no lookahead, 957 rollouts / 0.21 GPU-h) **plus** a smoke-feature ablation and a B4+smoke variant. The success criterion becomes the **second** term of Δ(P\*,B4) = [Δ(B4p,B4): prediction + information] + [Δ(P\*,B4p): blip estimation and lookahead] |
| No self-consistency comparator anywhere in E2 or E3; E4's is priced non-adaptively | Adaptive best-of-N is added as a **confirmatory comparator in every design** (R0a–R0c in the MRT; σ_k in E3; the full frontier N ∈ {1,2,3,4,6,8} in the stopping design), with the dominance argument proved in one paragraph. **Zero new GPU** — G1a's 8 root seeds per task supply it by construction |
| No estimand asks whether feedback beats an independent redraw | **P1 = γ_cond**, promoted to the program's first primary and first kill criterion. The independent-redraw arm is free from G1a's spare seeds |
| Y is not deterministic (canary × wall-clock × concurrency) | CPU-time as the only binding limit; wall ≥60 s as liveness; **three-valued outcome** with timeouts never mapped to 0; per-task calibration at the run's real concurrency; quarantine list; `test_reference_verdict_invariance` across {1,4,8,16} concurrency with canary on |
| Seeded rollouts do not reproduce; cold/warm cache boundary confounded with arm order | `prompt_n`/`cache_n`/`cached_tokens` recorded on **every** rollout (no design records any of them today); **arm order randomised** from the frozen table; one shared-prefix **warm-up call per state** before any arm; determinism audit redefined as **conditional on `prompt_n`**; the JSONL declared the sole artifact of record and every verification-re-execution path removed |
| No GPU harness exists; `state_id` stability unsolved | Harness enters the freeze. Mock-server end-to-end tests. `state_id` = content hash of **frozen inputs**, not of the output. Selection decisions persisted append-only and fsync'd **before** any continuation rollout |
| The screen's keep rate was measured at S0=8 and budgeted at S0=3 (f ≈ 0.10–0.15, at or below its own abort) | **The informativeness screen is abolished.** State selection moves to a task-level covariate (K=8 root pass count) with V₁-stratified oversampling and stored selection probabilities. This also removes the outcome-dependent selection that forbade reweighting and distorted the estimand |
| v̄ = 0.0339 measured unscreened, applied to a screened population (true value 0.1235–0.1548) | **G1a is the variance-calibration stage.** v̄ and SIG are measured from 3,824 real rollouts on the *actual* state population, on our own prompt format, before the continuation budget is committed. Gate 2 is sized from those numbers, not from n=4 |
| Winner's curse: max over 8 arms at S=3 inflates V\* by +0.32 on a 0–1 scale | **Seed-split argmax** is mandatory: select the arg-max on seeds 1..S−1, value it on the held-out seed. The winner's-curse magnitude at the realised (v̄, S) is reported as a diagnostic beside every regret |
| ~2,000 reported quantities, ~15 declared primaries, no simultaneous MDE | **Six** program primaries under Holm over the union (every MDE ×1.24); the ordering claim becomes **one** Kendall-τ permutation test; the 1,344-cell grading grid collapses to **one** pre-declared scalar per estimator; class × stratum panels get a **sup-t band**; E5's 63 sign agreements become one exact binomial count |
| A3 is an arbitrary-span attention manipulation, not a localisation; A7 is byte-identical to it in 25.4% of cells | **A3 redefined** to the line reported by the visible assert's traceback (from the smoke run), with its information cap re-measured. **A7 demoted (C)** to a design-only descriptive arm at 200 states; the A3-vs-A7 placebo contrast is withdrawn |
| No length-matched zero-information arm; A1 is 23 words against A3's 36 | **A1-PAD** added: byte-identical preamble + a frozen 13-word task-irrelevant sentence from DIVERT_LEX (which already trips G1/G2/G3/G5 at 0.000). One arm length-matches A3/A7, preamble-matches A6, and fills the ladder's missing cell. S1 and K5 report it |
| Contamination gated once at suite level and absent from every primary | **P6** (sign preservation across P-suite twins) is a program primary; **K6** can withdraw the A2 claim; G1d runs the paired replication at 1.83 GPU-h instead of a second 12.9 GPU-h tree |
| P\* and B4 matched on max calls and mean tokens, never mean calls | Mean-receiver-call cap with a paired CI added to the criterion; **B4-τ** budget-transplant baseline added (free, A1 continuations from existing states); Δ reported against B4, B4p, B4-τ and σ_k in one table |
| E3's confirmatory run gated on δ̂ from an overlapping pilot | Pilot tasks drawn **disjoint** from the confirmatory pool; the R rule restricted to nuisance quantities (φ, catch rate, tokens, compliance); **K12** forbids conditioning R or go/no-go on the primary |
| E3's "report both, treat neither as primary" escape hatch | Boosted critic is primary **unconditionally**; >25% argmax disagreement becomes an instability report, not a licence. A2 named in advance as a single secondary hypothesis with its own α |
| E5 transfer not identified (screened source vs unscreened target) | Resolved by abolishing the screen; the oracle-regret scale reference and the disagreement-rate factor become co-primary of the transfer arm |
| E4's depth-2 "policy-fixed continuations" cannot exhibit A₁→O₁→A₂ | **G2b is a genuine factorial at both stages** — otherwise nothing in the program is longitudinal and the g-formula is never exercised |

### 7.2 Answered by an added control or instrument

| finding | control |
|---|---|
| 94.2% of the suite winnable by a universal `__eq__`; `setattr`/`type()` routes miss the regex | G-HACK **AST** gate (0/591 false positives, 9/9 attacks stopped) + **canary wired into the grading path** (0/591 FP, kills the whole `__eq__` family). Both, always: neither suffices alone. Per-arm hack-flag and canary-kill rates reported as manipulation checks — a class that induces hacking is itself a finding |
| A6's blip confounded with code extraction (no preamble → prose → `extract_code` fallback → Y=0 mechanically) | 20-call fenced-block-rate probe on real t=1 outputs; the carry-forward rule pre-registered explicitly (no parseable code ⇒ `code_in_hand` **retained**, so the turn scores as STOP, not 0); per-arm fence and parse rates mandatory beside every blip |
| Engine in a foreign disposable scratchpad | Copy + commit pin + binary sha256 + all GGUF shard hashes + `system_fingerprint` per rollout + a halt-on-change abort |
| Injected vendor system persona (29 unrecorded tokens) | Explicit frozen system message per receiver; `sha256` of the **rendered** prompt per rollout; leak gates run on the rendered prompt, not only the authored suffix |
| `-c 32768` is the total KV pool; per-slot is 8192 | Per-slot `n_ctx` read from `/props` and recorded; client-side headroom assertion before every send; a 400 `exceed_context_size_error` recorded as a structural outcome with a pre-registered handling rule, never a retry loop and never Y=0 |
| E0's CPU grid competes for the cores that verify | One global concurrency budget (lock file) shared across all three projects; verification worker count and load average stamped **per verification**, not per episode; CPU cost a line item beside GPU-hours |
| Run-level abort thresholds cannot see a per-task cliff (1/591 = 0.17% vs a 5% gate) | Per-task gates beside every per-run gate: any task with non-zero timeout, context-400, or excess truncation rate halts and is quarantined with its measurements recorded |
| Single-literal leak gate fires on 33.7% of legitimate A3 | G4 computed, reported, and **rejected as a gate**. Added: **G6** (expected-output literal multiset at ≥2-gram granularity) and **G7** (targeting-channel mutual information with a permutation null), with the A4/A6-invariance-to-intervener-tier placebo |
| Blind probe at ~250/class cannot resolve a 0.02 ceiling as a difference | Restated as an **exact one-sided 95% upper bound** at 300 probes/class; if 0 pass, the bound is 0.0100 < 0.02 → PASS. Detecting a true 0.02 lift *as a difference* would need ~4,000/class = 35 GPU-h; we do not promise it |
| Canary not constructible for 27 `math.isclose` tasks | `canary_constructible` stamped per graded candidate and the rate reported; either hand-write comparison-form asserts or exclude and record |
| Mutation-kill weak subset not stratified | S12: Δ stratified by kill score with an exclusion sensitivity; the harness extended to the 29 tasks with no constructible mutant, which are **labelled and stratified, not silently pooled** |
| Family partition not reproducible (176 vs 169) | The partition file, its generating code and all its constants enter the freeze; the primary cluster bootstrap reported under all four thresholds 0.4/0.5/0.6/0.7 |
| Sandbox `rmtree(ignore_errors=True)`; `RLIMIT_NPROC` per-UID on macOS | Cleanup failures counted and logged; base-directory entry count asserted empty at chunk start and recorded at chunk end; `limits_applied` stored per verification |
| E0 cannot express the winning comparator | **RESAMPLE arm** added to E0's DGP (kernel = the marginal P(S₁\|E)); changes no calibration anchor and makes V(adaptive best-of-N) computable in the exact DP |
| E0 validates K=5/floor 0.2 while E1 runs 9 arms at ε=0.03 and E2 runs 4/3 option sets; F2 and F4 never piloted | Six new E0 cells at the live geometries; F2 and F4 run. E0 costs 1.2 wall-hours and no GPU; there is no excuse for validating at a geometry no experiment uses |
| E4's ledger choice subsidises multi-turn (prompt tokens 92/373/658) | Primary matching moves to **total** tokens with the price ratio swept {1:1, 1:3, 1:10}; all five ledgers reported for both arms in one table; stated explicitly that `C_prompt_incr` favours best-of-N by construction |
| The ratchet finding is best-of-N's selection rule, misattributed | Re-attributed in the text; adaptive best-of-N's own degradation reported in the same table as D(π); "harm avoidance" is not claimed as a multi-turn benefit unless ratcheted multi-turn degradation is shown **below** the baseline's, with a margin |
| The single-best-fixed-class arm is missing everywhere | Added to every regime table; free (read off the tree's ȳ table). **S7** makes V(π̂) − V(best fixed class) a named secondary with a ±0.02 equivalence band |
| Four incompatible first-attempt rates, three incompatible repair rates | **G0f** is a blocking CPU-only reconciliation with one table naming each prior number's definitional difference; E0's anchors re-solved against the result |
| 24/10 allocation weighting unpriced | Effective sample size 3,222/3,870 = 83%, so the MDE for any marginal or regime quantity is 0.064, not 0.058. Both numbers reported in the same table |
| E2's g-comp MDE 0.041 is a within-model sampling SD | Labelled as such and paired with the WR bound (0.107) in the same cell of the verdict table; the confirmatory run sized on **WR**; the pilot produces a real cluster-bootstrap SE (0.3–0.6 CPU-h) before the confirmatory stage |
| E2's 24-cell state gives ~46 observations per arm fully crossed (P(top arm correct) = 0.577) | Decision points reported per **fully crossed** cell; a minimum cell size below which a cell collapses to the pooled U_t × t decision is pre-registered; the expected P(top arm correct) and regret from the argmax-noise calculation are pre-registered so a near-random regime cannot be presented as "the optimal regime in the class" |
| E4's δ=0.03 margin consumes 53% of the achievable envelope | The fraction of the achievable envelope the margin consumes is a pre-registered secondary — one number that makes the non-inferiority claim interpretable |
| GGUF sizes ~2× overstated; the 7B is split | Table corrected; a sha256 per **shard** plus the shard count in `receiver_digest` |

---

## 8. Minimum publishable versus comprehensive package

### 8.1 Minimum publishable — 47.6 GPU-h, 44,294 rollouts

| component | rollouts / calls | GPU-h | what it buys |
|---|---|---|---|
| Gate 0 (all CPU) | 0 | **0.00** | A defined outcome variable; a working harness; a pinned environment; estimator validation at the live geometries; the priced prize; the baseline re-analysis; reconciled anchors; the P-suite; the multiplicity plan |
| Gate 1 (G1a–G1g) | 13,244 | **12.60** | **Five of six program primaries.** γ_cond; ρ and β for four classes with the length control; the contamination and leakage gates; the realised v̄, SIG and state population that size everything else |
| G2a — 8-class ladder to N=600 | 11,400 | **12.83** | The full information ladder as one permutation test; Monte Carlo blip truth per stratum with seed-split argmax; the reservoir for estimator grading |
| G2b — depth-2 factorial | 5,400 | **7.32** | The only sequential estimands in the program; the g-formula actually exercised; A₁→O₁→A₂ with O₁→Y |
| G2c — MRT confirmatory + pilot | 9,850 calls | **9.43** | Design-identified turn-level effects under a real randomised history; regime values including adaptive-BoN regimes; no misclassification, no propensity model |
| G2d — stopping and cost, net of overlap | 4,400 | **5.46** | P5 confirmatory; the five ledgers; both return rules; the degradation table with the baseline in it |
| **total** | **44,294** | **47.64** | |
| +50% contingency | | **71.5** | ≈143 wall-hours at 2 effective slots ≈ **18 eight-hour days** |
| CPU side | ~133,000 sandbox runs | — | ≈2.6 CPU-h verification + ~20 CPU-h audits/analysis + ~2 dev-days harness |

This package is a paper: a dynamic-treatment-regime formulation of multi-round interaction; estimator validation against exact truth at the geometries actually run; Monte Carlo ground truth for conditional blips at the branched depth (which almost no applied causal paper has); design-identified prospective estimates; the STOP-and-cost estimand with a correctly priced non-interactive comparator; and a measured information ledger with a positive control that the ledger catches.

### 8.2 Comprehensive — 72.8 GPU-h, 62,357 rollouts

Adds, in the order they should be taken, each a clean stopping point:

| component | rollouts | GPU-h |
|---|---|---|
| G3a — causal critic and policy (73% of baselines by tree selection; B4p; σ_k; best-fixed-class; live Self-Refine; 3rd seed on the fit/eval subset) | 6,463 | **7.50** |
| G3b + G3d — receiver transfer (7B, Coder-7B, granite-8B, **sequenced**) and intervener transfer (I2, I3, fully re-gated) | 10,600 | **17.09** |
| G3c — task-family transfer | 0 | **0.00** |
| G3e — observational slice (ω, adoption association, MSM, replay probe) | ~1,000 | **0.57** |
| **total** | **62,357** | **72.80** |
| +50% contingency | | **109** | ≈218 wall-hours ≈ **27 eight-hour days** |

### 8.3 If Gate 1 kills

Total spend **12.6 GPU-h** ≈ 25 wall-hours ≈ 3 days. G2 and G3 are never run.

### 8.4 The honest note on cost

The controls added in §7 cost roughly **11 GPU-hours** relative to the original ladder's 61.2 comprehensive figure (the A1-PAD arm, the P-suite paired replication, 8-seed roots, 4 seeds instead of 3, the larger leakage probe, seed-split argmax, and the abolition of the screen paid for in states). That is the price of a result a reviewer cannot dissolve, and it is cheap next to the 27.6 GPU-hours the original tree would have spent on contrasts it could not resolve.

---

## 9. What we report if the main hypothesis fails

The main hypothesis is that the content of a user-side message, delivered by an automated intervener, causally improves terminal task quality beyond what a budget-matched non-interactive baseline achieves. Four failure modes, each with its presentation fixed **now**.

**N1 — The baseline wins (K1/K2 fire).** Headline: *"On a frozen 3B receiver with a programmatic outcome, conditioning the next draw on the previous output does not beat an independent redraw at matched total tokens or matched latency; the observed multi-turn advantage in logs is a compute contrast."* Presentation: the adaptive best-of-N frontier over N ∈ {1,2,3,4,6,8} with the multi-turn arm plotted as a point on it and the crossing point in N reported as the headline number ("the pipeline is worth N_eff ≈ 2 independent samples"); all five cost ledgers; the paired CI; the discordant-pair share. Surviving contributions: the DTR formulation and its identification argument; E0's estimator validation under known truth, including the measured finding that a mediator-adjusted critic **converges to the wrong answer** (Kendall τ −0.050 at 40 runs/task → **−0.236** at 160); the outcome-integrity result (94.2% of a standard benchmark winnable by a 4-line stub, with two measured defences); and the correctly-priced-baseline result itself, which is a methodological warning the field needs.

**N2 — The turn matters, the content does not (K4 fires).** Headline: *"The fact of another turn matters; its content does not, on this receiver and this task family, at a resolution of ±0.071."* Presentation: the information ladder A0 < A6 < A1 < A1-PAD < A2 < A4/A5 < A3 < A8 with the seed-noise floor shaded and the α-split MDE stated on the figure; A1-vs-A0 shown large; every between-class difference shown inside the floor with its realised half-width. This is a publishable negative and it was pre-specified, not discovered.

**N3 — Causal correction changes reported effects a lot and decisions a little.** Headline: *"Adjusting a confounded interaction log changes reported effects by a large margin and decisions by a small one."* Presentation: the κ sweep showing naive-marginal rank recovery collapsing (mean Kendall τ **−0.511**, P(τ>0) = 0.007, P(top arm correct) = 0.028 — a complete reversal, the classes that work look worst) beside paired decision differences with a ±0.015 equivalence band; the breakage stratum shown as the one place adjustment matters (naive bias +0.028 on a truth of −0.10 to −0.15, a ~25% understatement of harm, which is the difference between shipping RESET and not). The surviving contribution is identification and honest reporting.

**N4 — No deployable policy beats stop-iff-visible-pass, or that rule is itself harmful (K8/K11 fire).** Headline: *"The oracle-stopping headroom is real and is gated on information the intervener does not have."* Presentation: V(π_U) against V(π_oracle) and against V(best fixed class) with the ±0.02 equivalence band; the exact DP prize (0.0210 in E0's law) beside the realised MDE; p̂ calibration restricted to visible_pass = 1; the U/V joint (P(V=1\|U=0) = 0.0816, P(V=0\|U=1) = 0.0877) as the quantitative basis.

**Rules that apply to all four.** Every null carries realised n, realised half-width, and MDE. No null is reported from a design with no stated MDE. No null is converted into a positive by post-hoc stratification, and no failure cell is dropped because it failed. If the harm result survives (degradation 0.144 → 0.043 under a ratchet, a 3.3× reduction for zero extra generation), it is reported as *"the non-interactive baseline's selection rule, retrofitted"* — with adaptive best-of-N's own degradation in the same table — not as a benefit of multi-turn interaction.

---

## 10. Explicit written concessions

These are findings we cannot fix. They are conceded in writing and will appear in the paper's limitations in these words.

**C1.** Relevance and provable innocence are entangled. A message cannot be both sharply targeted and provably answer-free. The redefined, traceback-grounded A3 has a non-zero measured information cap, so **A3's blip is not a leakage-proof result**. Only A2 and A1-PAD carry that property.

**C2.** **A7 as a placebo for A3 is abandoned.** It is not observationally identifiable (1,773/1,773 A7 messages label as A3), and at the redefined A3 it is not even form-matched. It survives only as a design-only descriptive arm at 200 states. The claim that the program separates information transfer from resampling at identical form and length is withdrawn.

**C3.** Abolishing the informativeness screen forfeits the 2.4× rollout efficiency the tree design claimed. We pay for it in states. In exchange, the estimand is the state population we actually intend, and no reweighting is forbidden.

**C4.** **We cannot power the A2 − A1 gap at its pilot magnitude (0.042) at any affordable size on this machine.** Gate 1 resolves \|effect\| ≥ 0.057 pointwise and ≥ 0.071 under α-splitting. If P2 lands inside that band, it is pre-registered as a precision result, not a null and not a rescue.

**C5.** Transfer to human interveners is **not established** and no experiment in this program establishes it. Every class is realised by a frozen template, which is *more* deterministic than an LLM intervener, let alone a person. The claim supported is about interventions deliverable by an **automated** intervener — which is also the deployment target. The replay probe tests transfer of the *treatment* (does the receiver respond mechanically to a real human A3 as it does to a template A3), never of the effect.

**C6.** Rollouts are **not reproducible**. Seeded output depends on the prompt-cache reuse boundary (`prompt_n`), which depends on slot assignment, which depends on what the foreign project's requests evicted. The JSONL tree is the sole artifact of record. Reproducibility is reported conditional on `prompt_n`; the unconditional rate is reported and is not a gate.

**C7.** Interactions among grid factors are not estimated. One-factor-at-a-time cannot see whether a tight positivity floor and a hidden effect modifier compound. A reader who needs the interaction needs a different grid.

**C8.** The receiver-transfer arm can only detect **ordering reversals** (shifts ≥ 0.10 on the blip scale, ~2.7× the true adjacent-class gap), not graded transfer. R → 0 both when transfer succeeds and when neither critic works, which is why the oracle-regret scale reference and the disagreement rate are reported beside it.

**C9.** Off-policy evaluation of a win statistic is out of scope. A win statistic has no additive decomposition over turns, so blip-based and iterated-Q estimators do not apply, and OPE would need weights for both members of every pair. Win statistics are computed only where both arms' outcomes are directly observed.

**C10.** If K8 still fires after re-anchoring, the entire optimal-regime workstream is **descriptive**: the prize for adaptivity in the reference law (0.0210) is smaller than the instrument's resolution, and no amount of causal machinery changes that.

**C11.** The critic is trained on hidden-test labels, so a deployed policy transmits up to **log₂\|A_adm\| ≈ 2.6 bits per turn** of hidden-verdict information into the conversation through its choice of action. Bounded, tiny next to A8, blocked from task-specific memorisation by family-disjoint cross-fitting — but not zero, and stated.

**C12.** Nothing is claimed about the **environment channel** (tool grants, attachments, added visible tests), which is structurally unlabellable in text logs and is therefore an *unmeasured* treatment rather than a noisy one. Every claim is restricted to the message channel.

**C13.** MBPP is never pooled with HumanEval in any quantity whose information cap depends on the visible/hidden split or on log₂\|spans\|. Y is coarse on MBPP: 396/427 tasks have exactly 2 scored asserts, so one leaked assert moves Y a long way.

---

## 11. Open questions the theory workstream must close, cross-referenced to what they block

| id | question | blocks | needed before |
|---|---|---|---|
| **T1** | The per-arm positivity floor, and therefore the arm count (COORD Q7). 9 × 0.20 = 1.80 is arithmetically impossible; at a floor of 1/9 the policy is forced uniform and λ becomes inert | `design.json`'s `p_vec`; G2c's option sets; E0's arm count; the simulated-log ε grid | **Gate 2c freeze** (E0a can proceed with the 4/3 and 9-arm cells as specified) |
| **T2** | The variance form: family-clustered sandwich versus family-mean paired bootstrap (COORD Q6) | **every CI in Gate 1**, hence P1–P4 and P6 | **Gate 1 freeze** |
| **T3** | Is the estimand a finite-population quantity over the tree's own states, or a superpopulation quantity over tasks? Defining it as the latter puts task-sampling variance into the truth, and the truth is then no tighter than the estimator | G2a's truth definition; S4; every transfer claim | **Gate 2a freeze** |
| **T4** | Does the ρ/β identity γ = P(V=0)·ρ − P(V=1)·β survive a **three-valued** outcome (pass/fail/indeterminate)? The identity assumes binary Y, and G0a makes Y three-valued | P2, P3, P4 specification; the two-part estimator | **Gate 1 freeze** |
| **T5** | Under what conditions is γ_cond identified as a causal contrast rather than a paired-potential-outcome functional of a joint law that a randomised trial does not identify? The tree identifies it under common random numbers; a live log does not | **P1**, the program's first primary and first kill criterion | **Gate 1 freeze** |
| **T6** | The debiased max: seed-split argmax versus a plug-in-debiased max for V\* on the tree. At S=3 and v̄=0.1356, E[max] − p = +0.324 over 8 arms | S4, S7, and every regret and critic-grading number | **Gate 2a freeze** |
| **T7** | The simultaneous-inference construction: a sup-t band over k quantities with family clusters, and the permutation reference for a max-over-classes statistic | **G0h**, hence the whole multiplicity plan, hence P4 and S2 | **Gate 1 freeze** |
| **T8** | Non-regular inference at the optimum: the m-out-of-n rule's adaptive m, and whether the cross-fitted value of the estimated regime is the only regular reportable quantity | G2c's optimal-regime section; S7 | **Gate 2c freeze** |
| **T9** | Transportability when the source state population was selected on anything the target's was not. Abolishing the screen may dissolve this; theory must confirm, and must say whether the K=8-band covariate selection is benign | G3b, G3c, G3d | **Gate 3 freeze** |
| **T10** | The marginal sensitivity model's Λ^τ compounding: what Λ-value is reportable at τ=2 when Λ=1.5 is already an odds-ratio budget of 2.25? | G3e's bound, and whether the observational slice can carry any bound at all | **Gate 3 freeze** |
| **T11** | Does STOP's free-outcome identity Y(STOP at t) = V_{t−1} survive (a) indeterminate outcomes and (b) a ratchet return rule, under which the returned object is not the last one? | P4; S8; S9; G2d's entire cost argument; the "STOP costs zero GPU" claim | **Gate 1 freeze** |
| **T12** | An estimand for "the content of feedback" that is not confounded with message length. Is A1-PAD the right reference, or does the estimand need a per-word decomposition? A1 is 23 words against A3's 36 | **P3**; S1; K5 | **Gate 1 freeze** |
| **T13** | Reconcile E0's DP and E2's simulation, which disagree by 6× on V(R3) − V(R1) (+0.036 vs +0.208) and disagree in *sign* on whether stop-on-visible-pass helps | K11; G2c's headline; E0c | **Gate 2c freeze** |

Seven of the thirteen block the **Gate 1 freeze**. They are the theory workstream's immediate queue, and Gate 1 cannot be frozen without them. The remaining six have Gate 0's CPU work in front of them, so they are not on the critical path today.

---

## 12. Run hygiene, non-negotiable

Never overwrite a completed run: new directory, new manifest carrying the seed table, config hash, code hash, taxonomy hash, lexicon hash, family hash, task hash, design hash, model digest per shard, engine commit, binary sha256, decoding parameters, verification concurrency, and the foreign GPU load (server PIDs, model aliases, load average, free+inactive memory) at start and end — recorded even for CPU-only stages, because contention affects the measured wall times and, as G0a shows, the outcome itself. Decisions are appended, flushed and `fsync`'d **before** the receiver is invoked, so an episode that dies mid-call is still intention-to-treat scorable. A stage refuses to resume if any input hash differs from an earlier invocation. `achieved_calls_per_hour` is recorded per invocation, so the planning constant is continuously re-measured rather than argued about — the three figures currently in circulation differ by **6×**. `V_t` is written only to the analyst file, which the intervener process cannot open. Raw human corpora live in gitignored `work/` only; only aggregate counts and **synthesised** exemplars enter the repository.
