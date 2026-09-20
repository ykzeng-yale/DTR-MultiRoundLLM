# E3 — causal critic and generative policy

`docs/design_e3_critic_policy.md` · DTR-MultiRoundLLM experiments workstream · **not frozen**; §14 lists the gates that must pass first.

Every number below is marked **M** (measured on this machine, today, with provenance) or **A** (assumption, with the pilot that pins it). Nothing is recalled and presented as fact. Measurement scripts used for this document are in the session scratchpad and must be promoted to `experiments/e3/` before the freeze (§15).

---

## 0. Scope, and four changes E3 requires in the frozen taxonomy

E3 trains **(a)** a critic `hat_gamma_k(S_k, a)` mapping an intervener-observable conversation state and a candidate next intervention to a causal blip estimate against STOP, and **(b)** a policy that emits the next intervention. It consumes the E2 branch tree; it does **not** build one.

**What E3 does not do.** It does not estimate free-form human intervention effects, does not establish transfer to human interveners, does not transfer across receivers, and does not license any claim about the environment channel (tool grants, attachments, added visible tests). Its claim is about *interventions deliverable by an automated intervener on a frozen 3B receiver over this coding task family* — which is also the deployment target.

The frozen taxonomy (8 classes + STOP) is **adequate for E3's estimand**, but four things must be added to the freeze before any critic is fit, because a critic cannot be fit to a representation that is chosen afterwards.

**0.1 — A factorial action encoding must be frozen alongside the class codebook.** The taxonomy separates classes by *mechanism channel* and orders them by *information content*. If the critic sees only a 9-way one-hot, it treats the classes as unrelated atoms and cannot borrow strength across them, which at 400 tree states is the difference between a usable and an unusable critic. The factorial code in §5 must be frozen as data, not re-derived.

**0.2 — A3 must be removed from the admissible action set on states where it degenerates.** `|spans(O)| = 1` on 75 of 591 tasks (12.7%) (M, taxonomy §8.4), where A3's information cap collapses to 0 bits and A3 is A1-plus-prose. The policy's admissible set is state-dependent: `A_adm(s)` excludes A3 when `n_spans(O_{t-1}) == 1`. Frozen as a rule, not decided at analysis time.

**0.3 — Template choice is a nuisance, never a policy action.** The policy chooses a **class**; the template index for A3–A8 is then drawn uniformly from the 3 frozen templates with the episode seed. Otherwise the policy acts at a finer granularity than the estimand and E2's coarsening-sufficiency test does not cover it.

**0.4 — `signature_example` must be stripped from every record E3 touches.** It is byte-identical to `test_list[0]` for 427/427 MBPP tasks (M, taxonomy §4). It is the *visible* assert, so it is not itself hidden, but it is one slot-filling accident away from A8 and it must not be reachable from the feature builder or the generator.

**Policy-admissible classes: `{A0, A1, A2, A3, A4, A5}`.** A6 (DIVERT), A7 (MISDIAGNOSE) and A8 (PATCH) are in the critic's *training* data — they are informative about the resampling, targeting and answer-transfer channels — but are **barred from the policy**. A8 is leaky by construction; A7 is a placebo; A6 is a reference action that a sane deployed policy must never emit. The value of the policy that *would* be allowed A8 is reported as the leakage upper anchor and never as the effect of feedback.

---

## 1. Dependencies (E3 cannot start until these exist)

| # | Artifact | Source | Blocking? |
|---|---|---|---|
| D1 | Frozen taxonomy v1 + factorial encoding (§0.1) + freeze commit id | E1 | yes |
| D2 | E2 depth-1 branch tree: 400 states × 8 non-STOP classes × seeds, with hidden verdict `V` per branch and `Y` per continuation | E2 | yes |
| D3 | E2 pre-freeze gates passed, including verifier determinism (0/597 disagreements over 1,954 replicate verifications, M) | E1/E2 | yes |
| D4 | E2 coarsening-sufficiency test result | E2 | no — but it decides whether the best-of-K arm runs (§9.2) |
| D5 | `experiments/common/{sandbox,verify}.py` (present, M) | ported | yes |
| D6 | `estimators_absorbing.py` from the sibling — eligibility padding with task-level folds, tested against the unpadded form: `/Users/yukangzengcmac/DTR-AgentEvals/experiments/code_routing/estimators_absorbing.py` | reuse, do not rewrite | yes |
| D7 | A2 difficulty pools: `results/audits/difficulty/20260919T215634Z/pool_informative.json` (240 uids, M) | present | yes |

---

## 2. The estimand the critic targets

Turns `t = 1..T_max` with **`T_max = 3`**: one initial attempt and up to two interventions. Decision points `k ∈ {1, 2}` (at turns `t = 2, 3`). Action set `A = {A0,…,A8}`, `|A| = 9`, A0 = STOP and absorbing. Horizon is the stopping time `tau = min{k : A_k = A0} ∧ 2`.

* `S_k` — the **intervener-observable** state vector (§4). Contains no hidden-test information, enforced by a whitelist test (§4.4).
* `V_k ∈ {0,1}` — the **hidden** verdict of the code in hand at decision `k`. **Analyst-only. A training label, never a feature.**
* `U_k ∈ {0,1,absent}` — the **visible** verdict (MBPP: `test_list[0]`; HumanEval: the prompt doctests). Intervener-observable, therefore a feature.
* `Y = V_{tau+1} ∈ {0,1}` — hidden-test pass of the final code. MBPP grades on `test_list[1:]`, HumanEval on the whole hidden `check`.

**Critic target.** The blip against STOP under an optimal continuation:

```
gamma_k(S_k, a) = Q_k(S_k, a) - Q_k(S_k, A0),     Q_k(s, A0) = V_k   (degenerate)
Q_k(s, a) = E[ V_{k+1} + max_{a' in A_adm(S_{k+1})} gamma_{k+1}(S_{k+1}, a')  |  S_k = s, A_k = a ]
```

with `gamma_3 ≡ 0` (no decision after turn 3).

Three properties of `A0` are load-bearing and are taken from the taxonomy document, where they are measured, not assumed:

1. `Y(A0 at k) = V_k` is `H_k`-measurable, so **STOP's potential outcome is known, has zero Monte Carlo variance, needs no nuisance model, and consumes zero GPU.** This rests on verifier determinism, which is measured: 1,954 replicate verifications of 597 repeated `(task_uid, sha256(final_code))` pairs, 0 disagreements (M).
2. Positivity for A0 is free.
3. Consequently every pseudo-outcome below has an *exact* reference arm, and the blip's variance comes entirely from the treated arm.

**The correctness-ceiling decomposition (taxonomy §5) is carried into E3 unchanged and is reported, not averaged away:**

```
gamma_k(a, A0) = P(V_k = 0) * rho_k(a)  -  P(V_k = 1) * beta_k(a)
   rho_k(a)  = P(Y = 1 | V_k = 0, A_k = a)   repair rate
   beta_k(a) = P(Y = 0 | V_k = 1, A_k = a)   breakage rate
```

`rho` and `beta` are the **primary reported pair** for every class. A pooled logistic blip model is misspecified (it cannot enforce `gamma ≤ 0` when `P(V_k=0)=0`), so the critic is fit in the two-part form of §6.4.

---

## 3. Populations and splits

**E3 primary pool = 190 tasks** (M, computed today): the A2 informative pool (240 uids, 3B posterior mass in 0.1–0.9) **intersected with "has a visible check"**, i.e. dropping the 50 HumanEval tasks whose prompt has no `>>>` doctest. Composition: 163 MBPP + 27 HumanEval (M). The 50 dropped tasks are a *reported* secondary stratum, not a silent exclusion: on them `U_k = absent` and the critic's single most informative feature is missing, so their policy value is estimated separately and never pooled.

Why this matters and was not previously stated: **the visible verdict, on which the whole deployable stopping rule rests, does not exist for 20.8% of the informative pool** (50/240, M). MBPP has exactly one visible assert (`test_list[0]`, 427/427, M), so `U_k` is *binary* there — the intervener's observable signal is one bit, not a pass fraction. Any feature named "first-attempt test pass fraction" is, on 163 of 190 tasks, that one bit. E3 therefore adds the always-computable smoke-run features of §4.2 so the state is informative even where `U_k` is absent or coarse.

`mbpp/794` is excluded (a `return None` stub passes its hidden-only program; M, audit A1).

**Task families.** Single-link clustering of the 190 prompts on stop-word-filtered token Jaccard ≥ 0.5 gives **176 families**, largest of size 3 (M; at threshold 0.4, 164 families, largest 7). Families, not tasks, are the cross-fitting and bootstrap unit. Frozen as a file before any fit; the threshold 0.5 is pre-registered and the 0.4/0.6/0.7 variants are a robustness row.

**Cross-fitted deployment (the split that keeps `n = 190`).** The E2 tree's 400 states are drawn from the same informative pool as the live evaluation, so a naive "train on the tree, evaluate live" design would let the critic see the evaluation tasks. Rather than halve the live pool (which drops power at `delta = 0.03` from ≈0.90 to ≈0.64, M §12), E3 extends cross-fitting to the live run:

> Partition the 176 families into **5 folds**. Fit 5 critic instances, each on the tree states from 4 folds. At live evaluation, each unit is scored by the single critic whose training folds exclude that unit's family. The "policy" is therefore a fold-indexed family of policies, and every live decision is out-of-family.

Cost of this: 5 critic fits instead of 1, which is 5 × ~5 s (M, §13). It is also a free stability diagnostic: the **fold-to-fold argmax agreement rate** is reported and is an abort trigger (§14.4).

---

## 4. State features `S_k` — the exact list

All features are functions of `(public task text, the receiver's own outputs, the visible check, the intervention history)`. 36 base columns + 9 error-class dummies + optional 64 text dimensions.

### 4.1 Task level (5)
`benchmark_is_humaneval`; `prompt_tokens`; `prompt_lines`; `visible_check_absent` (0/1); `n_visible_asserts` (1 for MBPP, count of doctest lines for HumanEval).

### 4.2 Current output `O_{t-1}` (13) — all AST/static, 0.043 ms per row (M)
`n_chars`; `n_lines`; `parses` (0/1); `n_for`; `n_while`; `n_if`; `n_return`; `n_def`; `n_try`; `n_calls`; `n_spans` (= `|spans(O)|`, which is also A3's positivity indicator and its information cap `log2(n_spans) + log2(6)`); `defines_entry_point`; `finish_truncated` (receiver `finish != 'stop'`).

### 4.3 Verdict and smoke run (2 + 9 dummies)
`visible_pass` (0/1, `absent` coded 0 with the §4.1 indicator); `smoke_seconds`; `smoke_error_class` one-hot over **9** levels `{none, SyntaxError, NameError/AttributeError, TypeError, ValueError, IndexError/KeyError, RecursionError, timeout, other}`.

The **smoke run** is a new, required harness addition and the reason the state is informative where `U_k` is absent: execute the candidate in the Seatbelt sandbox with **no assertions** (import + define + call on the visible example's input when one exists, otherwise import + define only), and read the exception class from `stderr`. `verify.py`/`sandbox.py` already return `stderr`, `returncode`, `timed_out` and `seconds`, so this is a second `run_program` call with a different program string, at the measured **0.03 s** per candidate on CPU (M) and **zero GPU**. This is the honest version of the assignment's "error type" feature.

### 4.4 History (7 + 9 dummies)
`k` (turn index); `n_interventions_so_far`; `prev_action_class` one-hot (9); `visible_pass_prev`; `code_change_ratio` = normalised Levenshtein between `O_{t-1}` and `O_{t-2}` (0 at `k=1`); `cum_completion_tokens`; `n_distinct_code_hashes` (a loop detector: the receiver re-emitting the same code is the dominant compliance failure mode to expect).

### 4.5 Optional text embedding (64) — measured, and torch is not needed for it
`TruncatedSVD(64)` of `TfidfVectorizer(analyzer='char_wb', ngram_range=(3,5), min_df=5, max_features=50000, lowercase=False)` on `O_{t-1}`. Measured on 24,000 real code strings from the sibling log: TF-IDF **4.91 s**, SVD-64 **7.45 s**, explained variance ratio **0.330** (M). Fit on training folds only, inside the cross-fitting loop.

**Escalation path if the primary critic's held-out AUC is below 0.60 with these features (A; pilot pins it):** mean-pooled hidden states from the already-cached Qwen2.5-3B via `llama-server --embeddings --pooling mean` as a **separate offline pass** over saved states. Measured constraint: `--embeddings` *restricts* the server to the embedding use case, so it needs its own process, and free+inactive memory is ≈3.6 GB against ~9.4 GB resident per server (M) — so this pass runs *after* the rollout phase, never concurrently. Cost ≈ **0.42 GPU-h** for 24,000 states (A: 0.25 s prompt-only per state at 4 slots; measured `server_prompt_ms` was 190 ms at 78 prompt tokens, so this carries a 2× margin). **This is the reason torch is not required for embeddings.**

### 4.6 Optional difficulty covariate (1), reported with and without
`beta_binomial_posterior_mean_3b` — the per-task first-attempt success posterior from audit A2. It is public information (it comes from a sibling run, not from hidden tests), so including it is legitimate, but it makes the critic depend on a foreign run. Pre-register both specifications; the primary is **without** it.

### 4.7 The firewall (mandatory unit test)
`build_features(record)` must accept a record whose keys are whitelisted to `{uid, benchmark, prompt, entry_point, visible_assert, history, smoke}` and must raise on any of `{test_list, test, challenge_test_list, reference, signature_example, V, Y}`. This mirrors `task_prompt()` in the sibling harness, whose docstring already carries the rule ("Only the task text and the signature. Never test_list / test (hidden)"). A test asserts the raise for each forbidden key. **`V_k` and `Y` are training labels only.**

---

## 5. Action features (the factorial code) — 22 columns, frozen

| block | columns | values |
|---|---|---|
| class one-hot | 9 | A0…A8 |
| channel one-hot | 8 | terminate, resample, de-anchor, attention, procedure, target, off-task, answer-transfer |
| `info_cap_bits` | 1 | A0 0, A1 0, A2 0, A3 `log2(n_spans)+log2(6)`, A4 0, A5 4, A6 0, A7 0 (0 *true* bits), A8 12 (uncapped, clipped at 12) |
| `has_preamble` | 1 | 1 for A1–A5, A7, A8; 0 for A0, A6 |
| `carries_verdict_bit` | 1 | identical to `has_preamble` — this is exactly what A6-vs-A1 isolates |
| `suffix_words` | 1 | A1 0, A5 9, A6 12, A4 12–16, A2 14, A3 13, A7 13 (M, taxonomy §2); A8 measured at render time |
| `template_index` | 1 | 0/1/2, **nuisance covariate only** (§0.3) |

`is_admissible_to_policy` is a mask applied at argmax time, not a feature.

Rationale, in one line: `channel` + `info_cap_bits` + `carries_verdict_bit` is what lets the critic say "procedural interventions help this state" from 3 seeds at 400 states, instead of needing 400 states per class.

---

## 6. The critic — primary implementation (scikit-learn 1.9.1, no torch)

### 6.1 Why sklearn is the primary and not a fallback
Measured today at the full design scale (n = 24,000 rows, d = 87, 5 folds grouped by family): cross-fitted `LogisticRegression` **0.16 s**; cross-fitted `HistGradientBoostingClassifier(max_iter=200)` **4.29 s**; the pseudo-outcome regression **1.02 s**; a 2,000-replicate cluster bootstrap over 190 clusters **0.009 s** (M). The entire critic pipeline is **seconds**. There is no compute argument for a neural critic at this data scale, and a 100-dimensional feature vector over 24,000 rows is squarely gradient-boosting territory.

### 6.2 Nuisance models (fixed, no tuning on the confirmatory data)
* Outcome regression `m_hat`: `HistGradientBoostingClassifier(max_iter=200, learning_rate=0.08, max_leaf_nodes=15, min_samples_leaf=40, l2_regularization=1.0, random_state=<fold seed>)` for binary targets; `HistGradientBoostingRegressor(max_iter=300, learning_rate=0.06, max_leaf_nodes=15, min_samples_leaf=40)` for the continuous stage-1 target.
* Propensity `e_hat`: **not estimated in the tree** — it is `1/8` by construction over the 8 non-STOP classes (positivity 1.0 at every branched state; taxonomy §6). It is estimated only in the simulated-log arm, by `LogisticRegression(multi_class='multinomial', C=1.0, max_iter=2000)` on `S_k`, with weights truncated at the pre-registered floor **0.2** (COORDINATION Q7) and the truncation rate reported.
* Critic regression: `HistGradientBoostingRegressor(max_iter=300, learning_rate=0.06, max_leaf_nodes=15, min_samples_leaf=40)`, fit on `(S_k, action_features(a))` with the pseudo-outcome as target, pooled over `a`.
* A pre-registered **linear-blip alternative** for interpretability and as a misspecification check: `RidgeCV` on `(S_k ⊗ channel, info_cap_bits, carries_verdict_bit)`. Reported alongside; the primary is the boosted critic.

Hyperparameters are frozen here and are **not** tuned on the confirmatory data. If tuning is wanted, it happens on the pilot's 40 tasks only, and the chosen values are written into the freeze.

### 6.3 The orthogonal, cross-fitted objective, written as pseudo-outcomes

Fold structure: 5 folds over the 176 families; all seeds, branches and turns of a family sit in one fold. Everything below is computed with nuisances fit on the complementary 4 folds.

**Stage 2 (last decision, turn 3).** For each state `i` and each `a ≠ A0`:

```
psi_2^a(i) = m_hat_2(S_2^i, a)
           + 1{A_2^i = a} / e_hat_2(a | S_2^i) * ( Y^i - m_hat_2(S_2^i, A_2^i) )

psi_2^{A0}(i) = V_2^i                                  # exact, zero variance, no nuisance

Psi_2^a(i) = psi_2^a(i) - V_2^i                        # the blip pseudo-outcome
```

Regress `Psi_2^a` on `(S_2, action_features(a))`, pooled over the 8 non-STOP `a`, to get `hat_gamma_2`. This is the DR-learner / orthogonal-statistical-learning construction (Kennedy, *Towards optimal doubly robust estimation of heterogeneous causal effects*, 2023; Foster & Syrgkanis, *Orthogonal statistical learning*, Ann. Statist. 2023; the sequential form is the structural-nested-mean / iterated-Q machinery of Robins 2004 and Chakraborty & Moodie 2013). **It is not novel and must not be described as novel.**

**A simplification specific to the branch tree, which must be stated because it changes what is being tested.** In the tree every `a` is executed at every state, so `1{A_2 = a}` is 1 for every `a` in its own branch and the AIPW term is available for all 8 actions simultaneously; with `e_hat = 1/8` known, `psi_2^a` collapses to the **measured branch mean** plus a mean-zero correction. In the tree the DR machinery therefore buys *robustness of implementation*, not identification — identification is by construction. The DR machinery earns its keep in exactly two places: the **simulated confounded log arm**, where one branch per state is subsampled with a known propensity, and **stage 1**, whose target `Ṽ_2` is itself estimated.

**Stage 1 (turn 2).**

```
V_tilde_2(i) = clip( V_2^i + max_{a in A_adm(S_2^i)} hat_gamma_2(S_2^i, a) , 0, 1 )

psi_1^a(i) = m_hat_1(S_1^i, a)
           + 1{A_1^i = a} / e_hat_1(a | S_1^i) * ( V_tilde_2(i) - m_hat_1(S_1^i, A_1^i) )

psi_1^{A0}(i) = V_1^i
Psi_1^a(i)    = psi_1^a(i) - V_1^i
```

with `m_hat_1(s,a) = E_hat[ V_tilde_2 | S_1 = s, A_1 = a ]`. Regress `Psi_1^a` on `(S_1, action_features(a))` → `hat_gamma_1`. `hat_gamma_2` used inside `V_tilde_2` is the *cross-fitted* one, so no observation contributes to its own target.

**Where the stage-1 data comes from.** The E2 tree branches at depth 1 and its depth-2 continuations are policy-fixed (taxonomy §6), so `V_tilde_2` needs states reached *after* an intervention with a spread of follow-on actions. E3 therefore buys a **depth-2 branch supplement**: **200** depth-1 outcome states (stratified on `visible_pass`, oversampling failures 3:1) × **8** non-STOP classes × **2** seeds = **3,200 rollouts** (§13). Without it the stage-1 critic is extrapolating and must be reported as such.

### 6.4 The two-part specification (required, not optional)
Because `gamma` is a mixture `P(V=0)*rho − P(V=1)*beta` with nuisance mixture weights, a single pooled model is misspecified. Fit two heads on the pooled data with `V_k` as the stratifier:

* `rho_hat_k(s, a) = P_hat(Y = 1 | S_k = s, V_k = 0, A_k = a)` — repair head, trained on `V_k = 0` rows.
* `beta_hat_k(s, a) = P_hat(Y = 0 | S_k = s, V_k = 1, A_k = a)` — breakage head, trained on `V_k = 1` rows.
* `p_hat_k(s) = P_hat(V_k = 1 | S_k = s)` — the **only** place a model of the hidden verdict from observables appears, and the deployable policy's whole handle on "am I already right".
* Deployable blip: `hat_gamma_k(s,a) = (1 - p_hat_k(s)) * rho_hat_k(s,a) - p_hat_k(s) * beta_hat_k(s,a)`.

`p_hat_k` is the interesting object: `V_k` is analyst-observable but not intervener-observable (taxonomy §5(d)), so the deployable policy conditions on `hat p` where the oracle conditions on `V`. **The gap between the deployable policy's value and the oracle-`V` policy's value is the value of knowing you are already right, and it is reported as a headline pair.** From audit A3, oracle stopping was worth **+4.6 points** of final success on the sibling log (M, with stated optimistic assumptions), so this gap is where the measured headroom actually lives.

Class-specific `beta` is also a detector: an over-prescriptive class that forces a rewrite of correct code shows high `beta` on already-correct states, and A2 and A8 are the expected offenders.

### 6.5 Secondary implementation if torch is installed — and the recommendation not to install it
**Recommendation: do not install torch for E3.** The justification is arithmetic, not taste.

* Timings in §6.1 show the critic is a ~6-second CPU job. A torch MLP on the same 87 features would not be more accurate at n = 24,000; it would be slower to write, slower to audit, and would add a large dependency to a pre-registered analysis script.
* The two things torch could genuinely buy are (i) a learned text encoder and (ii) generator fine-tuning. (i) is obtained without torch via the llama.cpp embedding pass in §4.5 at 0.42 GPU-h. (ii) is out of budget (§9.3).
* Installing torch (CPU/MPS) also perturbs a venv that currently reproduces a frozen analysis, and MPS competes for the same unified memory the receiver server needs — measured free+inactive ≈3.6 GB with the foreign load present (M).

**If torch is installed anyway** (e.g. because another workstream needs it), the pre-registered secondary critic is: a 2-hidden-layer MLP, widths 128 and 64, GELU, dropout 0.1, on the §4 features plus the §5 action code, two output heads (`rho`, `beta`) with a shared trunk, trained on the same cross-fitted pseudo-outcomes with `AdamW(lr=1e-3, weight_decay=1e-2)`, batch 256, 60 epochs, early stopping on the held-out fold. Predicted cost: **under 5 CPU-minutes** for all 5 folds at this scale (A; the sklearn HGB equivalent is 4.3 s measured, and an MLP of this size on 24,000 × 100 is the same order). It is reported as a robustness row, never as the primary, and it is **not** allowed to change the primary comparison.

---

## 7. The simulated confounded-log arm (where the causal correction is actually tested)

From the tree, subsample **exactly one branch per state** with a known propensity that depends on the current output quality:

```
e_conf(a | s) ∝ exp( kappa * w(a) * severity_signal(s) ),  floored at 0.2 after normalisation
severity_signal(s) = 1{visible_pass = 0}   (and, in a secondary sweep, smoke_error_class severity)
w(a) = the taxonomy's information-content rank of a, scaled to [-1, 1]
```

with **`kappa ∈ {0, 1, 2, 4}`** pre-registered. `kappa = 0` is randomization; higher `kappa` means severe interventions are sent more often from bad states, which is the confounding structure the project is about.

**Hard constraint (taxonomy §6):** `e_conf` may condition only on what a real user sees — the visible verdict and the code. Conditioning on `V` or `Y` manufactures a confounding strength no logging policy can exhibit and flatters every estimator that corrects for it. A test asserts that `severity_signal` is a function of whitelisted keys only.

This arm produces the paper's identification result — unadjusted class comparisons invert the ordering, the DR/blip estimator recovers it, validated against Monte Carlo truth from the full tree — at **zero additional GPU cost**. It also produces B5 (§10.6), the correlational critic, on the *same* data.

---

## 8. Ground truth, and what it does and does not license

At each tree state the measured branch means over seeds are Monte Carlo estimates of `gamma_2(S_2, a)` with standard error `sqrt(p(1-p)/n_seeds)`; at 3 seeds that is up to 0.29 per state, so **ground truth is usable pooled or on strata, not per state**. The pre-registered validation targets are (i) the class *ordering* of pooled `gamma_2`, (ii) the pooled `rho` and `beta` per class, (iii) the sign and rank correlation of `hat_gamma_2` against the state-level Monte Carlo values, Spearman over states.

Does not license: transfer to real users (the intervener is a template, more deterministic than an LLM intervener, let alone a human); transfer to other receivers; ground truth beyond the branched depth; reuse of one tree for fitting and evaluating without the family-level split of §3.

**The tree's own state-sampling probabilities are known weights and must be carried.** E2 stratifies state selection on the *visible* verdict with failure oversampling (because first-try pass is 0.654 overall, M). Those sampling probabilities enter every OPE as known weights, or `V(pi)` is biased by the tree's construction rather than by the logging policy it was built to simulate.

---

## 9. The policy

### 9.1 Primary: masked argmax over the finite class set
```
pi*(s):  g(a) = hat_gamma_k(s, a)  for a in A_adm(s)          # A_adm excludes A6,A7,A8 always,
         if max_a g(a) <= kappa_cost:  return A0              # and A3 when n_spans == 1
         else: return argmax_a g(a); draw template ~ Uniform{0,1,2}
```
`kappa_cost = 0` for the primary; `kappa_cost = 0.01` per turn for the cost-adjusted secondary (matching the sibling harness's turn penalty of 0.01, and the pre-registered value of `lambda` in COORDINATION Q5).

This is the primary because the estimand *is* defined over the finite class set, positivity is 1.0 there by construction, and the critic's resolution is exactly the class × state cell.

### 9.2 Conditional: best-of-K over generator proposals
Run **only if** E2's coarsening-sufficiency test **rejects** at `alpha = 0.05` — that is, only if within-class template differences are real. The reasoning is decisive and should be in the paper: if the coarsening is sufficient, then a free-form proposal is scored by the critic *only through its class label*, so best-of-K provably cannot beat argmax within the critic's resolution, and running it would be spending GPU to re-measure the same quantity with extra noise. E2's power against a within-class template SD of 0.08 is 92%, and 57% at 0.06 (M, taxonomy §8.2), so a non-rejection must be quoted as evidence against template effects of 0.08, not as evidence of exact sufficiency.

If it does run: `K = 4` proposals from the **7B** as intervener (`Qwen2.5-7B-Instruct`, so the intervener is not the receiver), each proposal labelled by the frozen labelling function; proposals labelled `OTHER` or tripping **G1/G2/G3** are discarded and the rejection rate reported; the surviving proposals are scored by `hat_gamma` via their class plus a text-similarity feature; argmax wins. Cost if run: 1,520 units × 4 proposals × ~0.63 active turns ≈ **3,800 rollouts ≈ 0.85 GPU-h** on the 7B this would be ≈1.7 GPU-h, so run the proposer on the 3B unless the 7B is idle. **A free-form arm voids the information-cap guarantee**, so every emitted message must pass the gates and the arm is reported with its own leakage table.

### 9.3 Declined: fine-tuning a generator
**Out of budget on this machine. Do not attempt in this paper.** The arithmetic: no CUDA; `mlx_lm` is **not importable in this repo's venv** (M, `ModuleNotFoundError`) and only `Qwen3-4B-Instruct-2507` has safetensors cached, so a LoRA run means a new dependency plus a model that is not the receiver; a 4B LoRA working set is roughly 8–12 GB against ~3.6 GB free with the foreign load present (M), so it requires the GPU *exclusively*; and the tuned generator would need its own family-disjoint training split, shrinking the 176 families further. Even granting all of that, the object it would produce — a generator emitting free-form text — is scored by a critic whose resolution is the frozen class set, so it inherits §9.2's problem *and* loses the information-cap guarantee. **The condition under which it becomes affordable:** foreign load gone, `mlx_lm` installed and pinned, a ≤4B safetensors proposer, and a rejection of coarsening sufficiency. Record the decision; do not re-litigate it mid-run.

---

## 10. Baselines — precise, and matched

All arms share the **same root output `O_1`** for each `(task, seed)` unit (the resettable-receiver pairing of §11), the same `T_max = 3`, the same template randomization, and the same cached draws where they choose the same message from the same state (§11.3).

| id | baseline | definition | extra receiver calls per unit |
|---|---|---|---|
| **B0** | single-shot | no intervention; `Y = V_1` | **0** (it *is* the shared root) |
| **B1** | oracle-STOP-only | stop iff `V_1 = 1` (hidden!), else always A1. Isolates the value of knowing you are right, holding content fixed. | **0** — it is a sub-trajectory of B2 and is read off B2's cached draws |
| **B2** | fixed unary retry | A1 at every turn to `T_max`, no stopping rule | 2.0 |
| **B2t** | token-matched retry | B2 given the same *completion-token* budget as `pi*` rather than the same call budget | 0.63 |
| **B3a** | Self-Refine, matched calls | receiver critiques its own output, then revises; **critique calls count against the call budget**, so B3a gets 1 revision | 2.0 |
| **B3b** | Self-Refine, matched revisions | 2 critique + 2 revise = 4 extra calls; **over budget, reported as such** | 2.0 (incremental over B3a) |
| **B4** | **strong heuristic — the PRIMARY COMPARATOR** | always the single class with the best *marginal* blip in the tree (computed on the training folds only), plus stop-iff-`visible_pass`. This is the fixed policy a competent engineer would ship. | 0.63 |
| **B5** | correlational reward-model critic | same features, same model family, same hyperparameters, trained on the **same** data — but on the `kappa = 2` simulated confounded log, by plain supervised regression of `Y` on `(S, A)`, **no** propensity correction, **no** cross-fitted pseudo-outcome, **no** STOP degeneracy, argmax of the fitted conditional mean | 0.63 |
| **B6** | myopic causal critic | identical construction to `pi*` but with `gamma_2 ≡ 0` inside `V_tilde_2`, i.e. one-step reward instead of lookahead | 0.63 |
| **B7** | oracle branch-value critic (ceiling) | at each state picks the argmax of the *measured* Monte Carlo branch means | tree-internal only; not run live |
| **P\*** | causal critic policy (§9.1) | | 0.63 |

**Fairness notes that must survive review.**
* B4 is deliberately strong. The weak baseline "always retry" (B2) breaks one already-correct answer in six (degradation 0.162, M, audit A3), so beating B2 is nearly free and proves nothing. Sizing against B2 gives an apparent effect of +0.07 to +0.12 (M, §12); sizing against B4 gives +0.015 to +0.030. **The design is powered against B4.**
* B5 is matched on features, model class, hyperparameters and sample size. The only difference is the objective. Anything less is a straw man.
* B7's live value is not measurable — the oracle needs all branches at the live states — so B7 is reported as a **tree-internal OPE upper bound**, explicitly labelled, and never printed in the same column as a live number.
* B3 is Self-Refine *style*: self-generated feedback from the receiver itself, no external verdict, no hidden tests. It must not be given the visible check, because then it is B4 with extra steps.

---

## 11. The live head-to-head

### 11.1 Unit and pairing
Unit = `(task, root_seed)`. **`n_tasks = 190`, `R = 8` root seeds → 1,520 units.** For each unit the root `O_1` is generated **once** and every arm branches from that same saved conversation state. This is the single most valuable move in E3 and it is free, because the receiver is resettable.

Why it matters, measured (§12): without common-`O_1` pairing, the U-shaped task difficulty (Beta(0.348, 0.230), M) dominates the variance and power at `delta = 0.05` against B2 is **0.31** at 190 × 6. With pairing, the same configuration reaches **≥0.95** (M). The design is not affordable without the pairing, and it is not honest without stating that pairing is why.

### 11.2 Matched budget — two definitions, both reported
1. **Matched receiver-generation calls (primary).** Every arm is capped at **3** receiver generation calls per unit, root included. Self-Refine's critique calls count. This is the right primary because generation calls are what cost wall time on this machine: 3.2 s per 3B call at 4 slots under contention (M).
2. **Matched completion tokens (secondary).** B2t receives `pi*`'s realized median completion-token budget, truncated at the turn boundary. Reported because a policy that wins by spending more tokens has not won.

Report per arm: mean receiver calls, mean completion tokens, mean wall seconds, mean turns to stop. If `pi*` exceeds B4's mean completion tokens by more than **10%**, the primary criterion is **not** met even if `delta > 0` (§12.3).

### 11.3 Draw caching, declared
Rollouts are keyed by `sha256(state_prefix || message || seed)`. When two arms send the same message from the same state with the same seed, the cached draw is reused. This is common random numbers: it induces positive correlation between arms, which *reduces* the variance of the paired difference and is exactly what the paired estimator of §12.2 assumes. It is pre-registered, and the GPU budget in §13 is computed **without** any caching credit, so any realized saving is margin. llama.cpp with `-np 4` is not bit-deterministic across batches even at a fixed seed, so caching is reuse of one sampled draw, not reproduction of it — stated, and it is the reason the estimator is paired rather than assuming independence.

### 11.4 Contention protocol
Receiver: `Qwen2.5-3B-Instruct q4_k_m`, `llama-server -ngl 99 -np 4 -c 32768 --jinja`, temperature and top-p frozen in the config, seeds per unit from the frozen assignment table. Do not launch if free+inactive memory `< 11 GB`. Record per episode: foreign `llama-server` PIDs and model aliases, 1-minute load average, `yielded_seconds_before_start`, `foreign_gpu_load_at_start` — the same fields the sibling harness already writes. The currently resident foreign servers belong to **`ICLR-WinRatioAgentEvals`** (PIDs 63658 7B and 63657 3B, M today), not to `DTR-AgentEvals` as `COORDINATION.md` states; that line needs correcting.

---

## 12. Sizing, power and precision (simulated today; inputs measured)

Generative model for the sizing simulation, all inputs measured: per-task success `q_i ~ Beta(0.34752, 0.23013)` (the A2 beta-binomial fit for the 3B); repair `P(Y=1 | V_1=0, another turn) = 0.239`; degradation `P(Y=0 | V_1=1, another turn) = 0.162` (both from audit A3, Wilson intervals `[0.210,0.270]` and `[0.105,0.242]`). Unit = `(task, seed)`, paired on `O_1`, clustered by task, `alpha = 0.05` two-sided.

### 12.1 Against the weak baseline B2 (for contrast only)
`190 × 4`, true delta +0.069 (stopping skill 0.7, no extra repair): power **0.955**. `95 × 4`: **0.713** (M).

### 12.2 Against the primary comparator B4 — the number the design is sized on
`phi = P(visible pass | hidden fail)` is an **assumption** pinned by the pilot; `r_extra` is `pi*`'s absolute repair gain over the best fixed class; `fp_catch` is the rate at which `pi*` correctly continues on a false-pass state.

| n | R | phi | r_extra | fp_catch | true delta | power |
|---|---|---|---|---|---|---|
| 190 | 8 | 0.10 | 0.03 | 0.5 | +0.0153 | 0.347 |
| 190 | 8 | 0.25 | 0.03 | 0.5 | +0.0210 | 0.646 |
| 190 | 8 | 0.10 | 0.06 | 0.5 | +0.0261 | **0.765** |
| 190 | 8 | 0.25 | 0.06 | 0.5 | +0.0300 | **0.906** |
| 190 | 12 | 0.10 | 0.06 | 0.5 | +0.0264 | 0.921 |
| 190 | 12 | 0.25 | 0.06 | 0.5 | +0.0299 | 0.978 |

(M, 1,200 replicates per cell.)

**MDE at 80% power, n = 190, R = 8: delta ≈ 0.027 absolute.** Precision, mean 95% half-width of the paired task-clustered difference (M): R = 4 → ±0.026; **R = 8 → ±0.019**; R = 12 → ±0.015; R = 16 → ±0.013.

**Pre-registered `R` rule, decided from the pilot and never from the confirmatory data.** After the pilot (§14.1) estimates `phi`, `r_extra` and `fp_catch`, compute the implied true delta. If `delta_hat ≥ 0.030` → `R = 8`. If `0.020 ≤ delta_hat < 0.030` → `R = 12` (+1.4 GPU-h). If `delta_hat < 0.020` → **do not run the confirmatory arm** (§14.2). `R` is fixed before the first confirmatory rollout; there is no interim look and no sequential testing.

### 12.3 Primary comparison and success criterion, pre-registered
**Primary outcome:** `Delta = E[Y | pi*] - E[Y | B4]`, final hidden-test pass, on the 1,520 paired units, estimated as the mean over the 176 task families of the family-mean paired difference, with a **paired cluster bootstrap over families, B = 10,000**, percentile 95% CI. Family-clustered, not task-clustered, because families are the cross-fitting unit.

**Success ⟺ all four hold:**
1. `Delta > 0` with the 95% CI excluding 0;
2. `Delta >= 0.030` absolute (the pre-registered practical threshold, set at the MDE rather than below it, so a "significant" result is never one the design could not have resolved);
3. matched budget: `pi*` uses ≤ 3 receiver generation calls per unit, and its mean completion tokens do not exceed B4's by more than 10%;
4. no leakage-gate failure anywhere in the run (§14.5), and `pi*`'s breakage rate `beta` on `V_1 = 1` states not exceeding B4's by more than 0.02 absolute — a policy that buys repair by destroying correct answers has not succeeded.

**Secondary outcomes, in this fixed order** (Holm-adjusted across the seven secondaries; the primary is not adjusted):
S1 `pi*` vs **B5** (causal vs correlational critic) — **pre-registered expected value: null.** S2 `pi*` vs **B6** (lookahead vs myopic) — pre-registered expected value: *positive*, and expected to exceed S1. S3 gap from `pi*` to **B1** (oracle-STOP) and to **B7** (oracle branch values), the "value of knowing you are already right" pair. S4 `pi*` vs B2 and vs B3a at matched calls. S5 per-class `rho` and `beta` with Wilson intervals, MBPP and HumanEval **never pooled** (headroom differs: MBPP reference median 16 words / 4 lines, HumanEval 84 words / 20 lines, M). S6 cost-adjusted value at `lambda = 0.01`/turn. S7 the 50-task no-visible-check stratum, reported separately.

**Why S1's expectation is null, stated in advance.** Premise checks P1–P3 (`docs/premise_findings.md`) found that a correlational critic conditioning on the full observed state recovered the exact optimal regime in 39/40 replicates, and that sweeping the confounding coupling moved the logged-minus-randomized regret gap by at most 0.030, while the *horizon* dominated in every condition. E3 must not be presented as a test the project expects to win. It is presented as a test the project expects to **lose**, with S2 as the effect the same evidence predicts.

---

## 13. Cost on this machine

Cost model, measured: **3.2 s wall per 3B receiver call** at `-np 4` under foreign load (n = 80 calls, `docs/measured_calibration.md`); 4 slots; sandbox verification **0.03 s** per candidate, CPU-side and off the GPU.

| stage | rollouts | GPU-h @4 slots |
|---|---|---|
| reuse of the E2 depth-1 tree (400 × 60) | 0 | **0.00** (E2 pays 24,000) |
| depth-2 branch supplement, 200 states × 8 classes × 2 seeds (§6.3) | 3,200 | 0.71 |
| E3 calibration pilot, 40 tasks × 4 seeds, all arms, own run dir, non-confirmatory | 1,523 | 0.34 |
| live: shared roots, 190 × 8 | 1,520 | 0.34 |
| live: policy continuations, 1,520 × 9.15 calls/unit (B2 2.0, B3a 2.0, B3b 2.0, and 0.63 each for B2t, B4, B5, B6, P\*) | 13,908 | 3.09 |
| **TOTAL E3 marginal** | **20,151** | **4.48 exclusive** |
| at 2 effective slots under foreign load | | **≈9.0 wall-hours**, resumable |

Contingency `R = 12`: 26,428 rollouts, **5.87 GPU-h**, ≈11.7 wall-hours. Conditional best-of-K arm (§9.2): +3,800 rollouts, +0.85 GPU-h on the 3B proposer. Embedding escalation (§4.5): +0.42 GPU-h, offline, after the rollout phase.

**CPU, all measured today on this machine:**

| item | cost |
|---|---|
| AST/static features | 0.043 ms/row → 1.04 s for 24,000 rows |
| char TF-IDF(3–5) + SVD-64 | 12.4 s for 24,000 rows (evr 0.330) |
| 5-fold family-grouped cross-fit, `LogisticRegression` | 0.16 s (n = 24,000, d = 87) |
| 5-fold family-grouped cross-fit, `HistGradientBoostingClassifier(200)` | 4.29 s |
| critic pseudo-outcome regression | 1.02 s |
| paired cluster bootstrap, B = 2,000 over 190 clusters | 0.009 s |
| smoke runs + hidden verification, 20,151 candidates × 2 × 0.03 s | **0.34 CPU-h** |
| full analysis script: 4 `kappa` levels × 5 folds × 3 specifications × B = 10,000 | **under 10 CPU-minutes** |

**The headline cost fact: E3's compute is entirely GPU rollouts. The statistics are free.** That is the argument against torch and against any neural critic here.

---

## 14. Abort and stopping conditions (pre-registered, with the response fixed in advance)

1. **Pilot, receiver level.** 40 tasks × 4 seeds, own run directory, non-confirmatory. If first-attempt success on the E3 pool under *this* prompt format falls outside **[0.30, 0.80]**, re-draw the pool from the A2 posterior to target 0.50 ± 0.10 and re-run the pilot once. If two pilots fail, abort E3 and report the pool as unusable for a policy comparison. (The sibling's 3B first-call rate was 0.600–0.667, M, so this is expected to pass.)
2. **Pilot, effect size.** If the implied `delta_hat < 0.020` (§12.2), **do not run the confirmatory arm.** Report the pilot as a precision result: the tree-internal OPE, the per-class `rho`/`beta` table, and a 95% CI around `Delta` from the pilot alone, framed as "no policy in this class beats the visible-pass stopping heuristic by more than X at this receiver". This saves ≈3.8 GPU-h and is a publishable negative (§15, N4).
3. **Noise floor.** If the E2 tree's within-class seed SD exceeds **0.12** (the design assumes ~0.028 at 3 seeds and 400 states, M, taxonomy §8.3), the critic cannot resolve classes. Report the noise floor and stop; do not fit a policy on top of it.
4. **Critic stability.** If the fold-to-fold argmax agreement of the 5 cross-fitted critics is **< 0.60** on the tree states, report the instability and do not run the live confirmatory arm. A policy that depends on which four-fifths of the families it saw is not a policy.
5. **Leakage, hard halt.** If any message emitted by any arm trips gate **G2** (any `assert` or `==`) or **G3** (hidden-input AST call-key overlap), halt immediately, quarantine the run directory, and record a protocol violation. Only reachable in the best-of-K arm; the template arms trip these at 0.000 by construction (M, taxonomy §3).
6. **Contention.** Do not launch a server if free+inactive memory `< 11 GB`. If a foreign 7B server appears mid-run, finish the current `(task, seed)` block and pause; do not degrade to fewer slots silently, because the cost model is calibrated at 4 slots.
7. **Wall clock.** If the live arm has not finished within **20 wall-hours**, stop at the nearest completed `(task, seed)` block boundary and analyse the completed blocks, reporting the realized `n` and the realized half-width. Blocks are complete across all arms simultaneously, so truncation is uninformative with respect to arm — this is the reason for blocking by unit rather than by arm.
8. **Never overwrite a completed run.** New directory, new manifest with seed, config hash, code hash, model digest, decoding parameters, tasks sha256, freeze commit id. Every episode stamped with the config hash.

---

## 15. What negative result is publishable, and how it is presented

All four of these are results, not failures, and three of them are what the evidence so far predicts.

**N1 — "Causal correction does not change decisions."** `pi*` ≈ B5 with the 95% CI for S1 inside ±0.015. This is a direct empirical test of the project's originating premise, on real model rollouts, agreeing with the tabular simulations P1–P3. Presentation: a paired per-task difference plot with the ±0.015 equivalence band drawn, beside the `kappa = 0,1,2,4` sweep showing that the *reported effects* from the confounded log are badly wrong (unadjusted ordering inverted) while the *chosen actions* are barely affected. The contribution then reads: **identification and honest reporting**, not decision improvement — which is COORDINATION Q11's framing (1). The paper must not quietly relabel this as a win.

**N2 — "The fact of a retry matters; its content does not."** Every between-class contrast lands inside A1's within-state seed noise floor while A1-vs-A0 is large. Presentation: the information ladder `A0 < A6 < A1 < A2 < A4/A5 < A3 < A8` with the noise floor as a shaded band, the A1-vs-A0 and A1-vs-A6 contrasts called out, and the explicit statement that a between-class difference below ~0.028 is inside the floor at 3 seeds and 400 states. Pre-registered as a reading, per taxonomy §8.3.

**N3 — "The horizon matters more than the confounding."** S2 (`pi*` vs the myopic critic B6) exceeds S1 (`pi*` vs the correlational critic B5). Presentation: a 2×2 of `{myopic, lookahead} × {correlational, causal}` policy values at matched budget, which isolates the two axes on the same data and costs one extra 0.63-call arm (957 rollouts, 0.21 GPU-h). This is COORDINATION Q11's framing (2), and E3 is deliberately built so that it is *measurable* rather than assumed.

**N4 — "No deployable policy beats stop-iff-visible-pass."** `Delta` CI covers 0 and excludes 0.03. Presentation: the deployable-versus-oracle pair. Audit A3 measured +4.6 points of final success available from oracle stopping alone (M, under stated optimistic assumptions); if `pi*` cannot capture it, the headline is that **the headroom is real but is gated on information the intervener does not have**, quantified by the `hat p_k` calibration curve and the B1/B7 gaps. That is a statement about the limits of automated intervention, and it is worth publishing.

In every case: report the realized `n`, the realized half-width, the MDE, and the ±0.019 precision the design was built for. A null from a design with a stated MDE is evidence; a null from a design with no stated MDE is nothing.

---

## 16. How this design is most likely wrong

1. **The design may be underpowered for the true effect.** The realistic gain over a fair stopping baseline may be ~0.015, and at `R = 8` power there is 0.35 (M). Abort condition 14.2 exists precisely so that 3.8 GPU-h are not spent discovering this. But if the pilot's `delta_hat` is noisy at 160 units, condition 14.2 may fire in the wrong direction. Mitigation: the pilot's `delta_hat` is reported with its CI and the `R` decision is recorded before the confirmatory run.
2. **`phi = P(visible pass | hidden fail)` is an assumption, and it is the hinge.** With a single visible assert on MBPP, `phi` could be anywhere from 0.05 to 0.40. If it is near 0.05, `pi*`'s only advantage over B4 is class choice, and §12.2 says that alone gives power 0.19–0.35. The pilot measures `phi` directly on 160 units; it is the first number to look at.
3. **The critic learns from 400 states and must generalize to 190 live tasks across 5 folds.** 400 states × 8 classes is 3,200 rows per stage — thin for a boosted model with ~100 features. The factorial encoding (§5) is the mitigation and the linear-blip alternative (§6.2) is the check. If the boosted and linear critics disagree on the argmax more than 25% of the time, report both policy values and treat neither as primary.
4. **A new leakage channel: the policy's action choice is itself an information channel about the hidden verdict.** The critic is trained on hidden-test labels, so a deployed `pi*` transmits at most `log2|A_adm|` ≈ **2.6 bits per turn** of hidden-verdict information into the conversation. This is bounded and tiny next to A8's full answer transfer, and the family-disjoint cross-fitting prevents task-specific memorization — but it is not zero, it is not mentioned in the taxonomy document's information ledger, and it must be stated in the paper. A reviewer will find it if we do not.
5. **The paired design measures a conditional-on-`O_1` contrast.** Sharing the root across arms is what makes E3 affordable, but the estimand is then "the effect of the policy given this receiver's first attempt", not the marginal effect of a deployed system that also influences the first attempt. Since the first attempt is untreated by construction here, these coincide — but only because `A_1` is the task itself.
6. **`hat p_k(s)` may be uncalibrated where it matters most.** It predicts the hidden verdict from observables; on states where the visible check passes but the hidden tests fail, it has to work against its most informative feature. Report its calibration curve restricted to `visible_pass = 1`, not only pooled.
7. **The template intervener is more deterministic than any real intervener.** Every effect here is an effect of a frozen template. Transfer to an LLM intervener is plausible and untested; transfer to humans must be argued, never assumed (taxonomy §8.8).
8. **The 3B is the primary receiver on the strength of audit A2's beta-binomial fit**, which was computed from a *different* prompt format on a sibling run. The task *ranking* should be stable; the *level* is a proxy. If this project's own first-attempt rate lands far from 0.60, the 190-task pool is the wrong pool and abort condition 14.1 fires.

---

## 17. Order of operations

1. Freeze: taxonomy v1 + the four additions of §0, feature builder with its firewall test, action encoding, the 176-family file, the E3 pool file (190 uids), critic and analysis code, seeded assignment table, primary/secondary outcome list. Record the freeze commit id.
2. CPU-only dry run of the whole pipeline on the sibling's 4,488-episode log as a mechanical smoke test — no receiver calls, no GPU. Confirms the analysis script runs end to end before it is allowed near real data.
3. Depth-2 branch supplement (0.71 GPU-h).
4. E3 pilot, own run directory, non-confirmatory (0.34 GPU-h). Pin `phi`, `r_extra`, `fp_catch`, the compliance and loop rates, and `pi*`'s token usage. Decide `R` by the §12.2 rule and write the decision to the manifest.
5. Gate check against §14. Abort or proceed.
6. Confirmatory live run, resumable, blocked by `(task, seed)`, foreign load stamped per episode (3.43 GPU-h at `R = 8`).
7. Analysis exactly as frozen. Report `rho` and `beta` before any pooled blip; report MBPP and HumanEval separately; report the realized MDE beside every null.
