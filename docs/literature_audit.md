# Literature audit — verified citations, prior art, and a much smaller surviving claim

**Method.** Ten parallel verification agents checked every citation in the
originating brief plus the backbone references the experiments workstream intended
to build on, with live web lookups (141 citation records, 586 tool calls). Five
further agents swept for prior art down deliberately different routes: by estimand,
by method transfer, by application, by venue recency, and adversarially — one agent
was told to find the papers a hostile reviewer would use to say "this is just X with
causal language bolted on". A synthesis agent adjudicated, and a separate agent
played area chair and wrote the rejection. Run 2026-09-19.

**Headline: 132 of 141 claimed citations are real and accurately described.** The
brief's bibliography was largely sound. One citation string was corrupted —
`arcxiv.org/abs/2608.17499` — but the arXiv id and title are genuine; `arcxiv.org`
simply does not exist. Five "not found" verdicts are all *gap checks* the experiments
workstream asked for, and they came back genuinely open.

**Headline: the novelty claim in the brief does not survive.** The sweep found
prior art occupying most of the proposed contribution, including work the brief
never mentions. The structured records are in `docs/literature/`:
`citation_records.json` (141 verifications), `prior_art_sweep.json` (96 prior-art
hits with threat levels), `adjudication.json`, `hostile_review.json`.

# Literature Audit — DTR for Multi-Round LLM Interaction

**Adjudicated:** 2026-09-19 · **Basis:** six independent verification passes (arXiv API, Crossref, ar5iv, local PDF text extraction, conference virtual sites, PMLR/OpenReview/ACL Anthology)
**Rule applied:** only ids returned CONFIRMED are usable below. Everything UNCLEAR, NOT_FOUND or search-snippet-only is quarantined in §1.

> **Audit limitation.** The evidence bundle is truncated mid-record in its final item (RealUserSim, arXiv:2605.20204). That record's second failure mode ("Directive Amplification") is described but the paper's method and results are cut off. Re-verify before citing it on anything beyond the two named failure modes.

---

## 1. REFUTED / UNVERIFIED — do not use

Headline: **no citation in the audited set was hallucinated.** Every claimed arXiv id resolved to its claimed title. The defects are of four other kinds, and in a related-work section they cost just as much: a **fabricated hostname**, **inflated venues**, **overstated claims about what a paper proves**, and one **premise that has no paper behind it at all**.

### 1.1 Hard defects

| Claimed | Verdict | Replacement |
|---|---|---|
| `arcxiv.org/abs/2608.17499` | **REFUTED (host).** `arcxiv.org` is not a preprint server. The paper is real. | `arXiv:2608.17499` — *Towards Better Agents for Multi-Turn User Interaction: The Next User Turn Is More Than Context* (FACA), 18 Aug 2026. **A fabricated hostname is a characteristic generation artifact — re-verify every other entry in whatever list produced this one.** |
| "Work on stochastic interventions / MTPs where the action space is TEXT" | **NOT_FOUND.** Searched across arXiv full text and the web on several phrasings (modified treatment policy / stochastic intervention × text, prompt, natural language, LLM, infinite-dimensional action space). No such paper exists. | **None.** Nearest: `arXiv:2606.27518` (function-valued *numeric* treatments) and `arXiv:2502.17538` (language action space, no identification theory). This is our whitespace — but it is a negative search result and must be re-checked before it is written as novelty. |
| Robins (1994) SNMM, DOI `10.1080/03610928408831393` | **REFUTED.** Does not resolve (digit transposition). | DOI `10.1080/03610929408831393`, *Commun. Stat. Theory Methods* 23(8):2379-2412. |
| ShareGPT, cited as a dataset alongside WildChat / PRISM | **UNCLEAR.** No paper, no DOI, no authoritative release, no consent framework. Mirror is nominally Apache-2.0 but the uploader had no right to license OpenAI output or user content. Self-selected toward showcase and jailbreak chats. No labels. | Use `arXiv:2405.01470` (WildChat-1M) and `arXiv:2404.16019` (PRISM). ShareGPT for smoke tests only. |
| "Frauen et al. 2025" orthogonal meta-learners over time; `2510.19643`; `2405.21012`; `2606.13156`; `2605.14553` | **UNVERIFIED.** Search hits or uncited references only; no id individually confirmed. | None. Fetch and confirm each before it enters a bibliography. |

### 1.2 Inflated venues

| Claimed | Actual |
|---|---|
| ROSA2 / "Words and Weights", **ICML 2026** | **Unsupported by any primary source.** `arXiv:2603.01375` has one version, no Comments field, no journal-ref, no acceptance footnote (only the template's "Machine Learning, ICML" keywords). No `icml.cc/virtual/2026` page, no PMLR entry. The sole assertion is the first author's homepage. Title also uses **&**, not "and". Contrast T-POP (`arXiv:2509.24696`), whose v2 Comments field reads "Accepted to ICML 2026" — that is what evidence looks like. |
| ProRefine, **NeurIPS 2025** | NeurIPS 2025 **Workshop on Efficient Reasoning**. |
| Progressive-Hint Prompting, **ICML** | **ICML AI4MATH 2024 workshop.** Six arXiv versions over 18 months, never a main track. |
| TextGrad = `arXiv:2406.07496` | **Stale.** Canonical cite is **Nature 639(8055):609-616 (2025)**, DOI `10.1038/s41586-025-08661-4`. |
| GEPA = arXiv preprint | **Stale.** v2 header: "Accepted at **ICLR 2026 (Oral)**". |
| Self-Refine, Reflexion | Correct — both NeurIPS 2023 main. These two are solid. |
| Richardson & Robins (2013) SWIGs | **CSSS Working Paper 128, U. Washington** — real but unrefereed. Cite as a working paper. |
| *Lost in Simulation* | ACL 2026 Long, but also listed on the ICLR 2026 virtual site — venue listing is inconsistent across sources. Cite the ACL Anthology entry. |

### 1.3 Overstated claims — the paper is real, the sentence is not

- **CPO does not identify prompt effects.** DML is applied to prompt and query embeddings as nuisance features. No identification theorem, no overlap/positivity argument for a continuous embedding-valued treatment, unrefereed. Cite as *"DML-debiased offline reward model for query-specific prompt selection."*
- **SCIE is not rigorous identification.** The ATE is estimated on **LLM-self-generated** observational data with hand-chosen textual features and no unconfoundedness discussion. It is the right citation for *precedent of the framing*, nothing more.
- **Feldman et al. residualize the COVARIATES, not the treatment**, and the setting is a **randomized SAE-steered** experiment — so the bias is overcontrol / adjustment-set contamination, not classical confounding. Get both details right or a referee will catch it.
- **LMTP does not relax positivity for the static estimand.** It changes the estimand. The support-preservation condition on `d` is enforceable by construction, but the price is **strong sequential randomization** (Assumption 3: `U_{A,t}` independent of future covariate *and treatment* noise), and for the threshold shift the parameter is **not pathwise differentiable**, so no √n estimator exists. Say this plainly.
- **Kennedy's IPSIs are binary-treatment only.** The no-positivity result is genuine and stronger than LMTP's, but does not cover continuous, high-dimensional or text actions. The estimand is also defined *through the true propensity score*, so it moves when the observational mechanism moves.
- **The orthogonal MDP learner's "discrete or continuous" is about STATE spaces.** The construction is finite-action throughout (sum over `a ∈ A`, action propensities, a Dirac `δ(A'=a)`, overlap metric `Σ_a min(π_b,π_e)`, Taxi/Frozen Lake). It is also **OPE of a level** (a Q-function under fixed `π_e`), not a contrast and not policy optimization.
- **"CATE-accurate models are suboptimal for decisions" is conditional** on a *restricted* second-stage function class. With an unrestricted class, thresholding a correct CATE remains optimal. Static and binary.
- **DeepBlip's continuous treatments are aspirational.** Overlap is stated in discrete form, the blip needs a reference level 0, every experiment is binary.
- **Self-Refine's ~20% is not reasoning evidence.** It comes from preference-judged tasks (Dialogue Response 25.4→74.6, Sentiment Reversal 3.8→36.2). GSM8K: 64.1→64.1, 74.8→75.0, 92.9→93.1. The paper itself blames the model's inability to detect that an error exists.
- **"Nobody has applied causal thinking to prompt optimization" is dead.** `arXiv:2605.26655` (propensity-adjusted edit-level audit) and `arXiv:2504.02646` (off-policy prompt policy from logged bandit data) both exist.
- **Reflexion's 91% pass@1 is a verifier result**, not a self-reflection result. Unit tests are in the loop. If our design has no verifier, Reflexion is not a supporting precedent.

### 1.4 Citation hygiene

ProTeGi's real title puts "Gradient Descent" in scare quotes; "ProTeGi" appears only in the body. `A Simple "Try Again" Can Elicit Multi-Turn LLM Reasoning` carries the quotation marks. Shani et al.'s awkward *"from Preference Human Feedback"* is the genuine title. "Lin et al." (`2510.05921`) is a nine-author Gašić-group paper with a v3 of 17 May 2026 — pin the version. `eva` (PMLR v267 `ye25a`) is lowercase and absent from its own title. T2PAM is the *framing*; **ROSA** is the algorithm. RealUserSim's abs page says "7 Apr 2026" against a `2605` identifier — a metadata anomaly worth flagging.

---

## 2. CLOSEST PRIOR ART — ranked

| # | Paper (id) | What it has | What it lacks relative to us |
|---|---|---|---|
| 1 | **Prompt Optimization with Logged Bandit Data** — Kiyohara, Cao, Saito, Joachims (`arXiv:2504.02646`) | Genuinely causal **and** off-policy **and** per-context: logged bandit feedback, prompt selected per user context, kernel-based off-policy policy gradient exploiting sentence similarity to control variance over a huge prompt space. | Single-turn, immediate reward. No sequential regime, no backward induction, no time-varying confounding, no responding counterpart. Venue unconfirmed. **The biggest threat to a naive "first causal prompt policy" claim.** |
| 2 | **GenAI Powered Dynamic Causal Inference with Unstructured Data** — Nakamura & Imai (`arXiv:2605.07834`) | Causal effects of **sequences** of text treatment features; marginal structural model with a neural per-feature deconfounder; semiparametric inference with valid CIs; position effects demonstrated. | The sequence runs over positions *within a document*, not rounds of interaction. Estimates effects; does not optimize a policy or define policy value. No responding counterpart. **Absent from the original list — the audit's biggest gap.** |
| 3 | **Policy Learning with a Natural Language Action Space** — Zhang, Wang, Dhillon (`arXiv:2502.17538`) | Multi-stage decisions in a **natural-language action space**, outcome only after a sequence, Q-learning for a DTR, gradient ascent on embeddings, decoding back to coherent text. | **No identification layer whatsoever**: no exchangeability condition, no positivity analysis, no estimand, no estimator theory. No stochastic/modified policy, no OPE, no orthogonality. It owns our framing and leaves the statistics open. |
| 4 | **CPO** — Chen et al. (`arXiv:2602.01711`) | Prompt = treatment, query = covariate, reward = outcome, embeddings = adjustment representation; DML-debiased offline reward; query-specific search without online evaluation. | Static one-shot. No sequential prompts, no time-varying confounding, no policy-value guarantee. No identification theorem, no overlap argument. Unrefereed. Its joint DML on prompt **and** query embeddings is the exact conflation `2602.15730` shows induces bias. |
| 5 | **OPE of Multi-Turn LLM Health Coaching with Real Users** — Ozolcer & Bae (`arXiv:2510.17173`) | The only OPE on **real** multi-turn LLM logs; per-turn contextual bandit over factorized Tool/Style heads; SNIPS + AIPW; finds average-value gains hiding subgroup harm. | Propensities **reconstructed** post hoc via calibrated classifiers (authors concede moderate Tool-head calibration → IPS bias). N=7 pilot. Per-turn bandit, not a sequential estimand: no backward induction, no g-formula. Workshop. |
| 6 | **DeepBlip** — Ma, Frauen, Feuerriegel (`arXiv:2511.14545`) | First neural SNMM; blip decomposition → per-round incremental effects; double-optimization trick; Neyman-orthogonal second stage; offline policy evaluation without recomputation. ICML 2026. | No text, no LLM. Binary in practice. **App. C.2 error propagation grows like (1+C)^{τ−k}** — accuracy decays exponentially backwards under weak overlap, exactly the regime a long conversation lives in. |
| 7 | **Orthogonal Learner for Individualized Outcomes in MDPs** — Javurek et al. (`arXiv:2509.26429`) | DRQ-learner from the efficient influence function: doubly robust, Neyman-orthogonal, quasi-oracle efficient; **weak positivity** (`supp π_e ⊆ supp π_b`); built for low-overlap regimes. ICLR 2026. | Finite-action throughout. OPE of a **level**, not a contrast, not optimization. Markov assumption conditions on `S_t` alone — a real strengthening vs. the longitudinal papers. No text. |
| 8 | **LMTP** — Díaz, Williams, Hoffman, Schenck (`arXiv:2006.01366`, JASA 118(542):846-857) | Extended g-formula in sequential-regression form, EIF, TMLE + sequentially doubly robust estimator; continuous/multivariate exposures with time-varying confounding, censoring, survival; positivity → enforceable support preservation. | Nothing about text: **Assumption 1 is undefined for strings**, and there is no generalized propensity over text. Requires strong sequential randomization once the policy reads the natural value. Covers only natural value *at time t* (history-dependent → `2605.24167`). No per-round heterogeneity (→ `2509.22916`). |
| 9 | **FACA** — Zhao et al. (`arXiv:2608.17499`) | Per-stage credit assignment: U2U segments as decision stages, next user turn as temporally-local ternary evidence, z-normalized reaction advantage at λ=0.5 on top of verified terminal outcome. +5.91pp (8B) / +10.22pp (14B) vs. a matched outcome-only control. | Purely **on-policy** GRPO with standard clipping: no importance weighting, no propensities, no estimand. Credit signal comes from **privileged simulator-internal metadata** real users never emit. That pair is the clearest opening for a DTR/OPE contribution. |
| 10 | **TextGrad** — Yuksekgonul et al. (`arXiv:2406.07496` / Nature 639:609-616) | The one canonical prompt-optimization paper with a genuine **per-instance test-time** mode ("the only goal is to improve the solution for a given query at test time"). Nature 2025; radiotherapy-plan application already touches decision objects. | The object is a **static artifact** (answer, code, molecule, plan) refined against a **fixed query** — not a message into an ongoing interaction with a counterpart whose future behavior depends on it. **Zero** occurrences of "causal"/"counterfactual" in 41 pages. The "gradient" is the authors' own scare-quoted metaphor. |
| 11 | **CollabLLM** — Wu et al. (`arXiv:2502.00640`, ICML 2025 Outstanding Paper) | Multiturn-aware rewards: simulated forward rollouts of both sides give a long-horizon value for crediting a single response — the closest published model-based DTR analogue. **Validated with 201 human judges** (+17.6% satisfaction, −10.4% time). | Prompt-based simulator, not learned from logs — and the sim2real papers show such simulators are excessively cooperative with uniformly positive feedback, biasing simulator-derived value **upward**. Training-time device, not decision-time search. No estimand, no confounding adjustment. |
| 12 | **GPI** — Imai & Nakamura (`arXiv:2410.00903`) | The rigorous identification backbone for text-as-treatment: nonparametric ATE conditions, LLM-generated treatments with known true internal representation, estimation designed to **avoid overlap violations**, DML asymptotics, IV extension. | Strictly **point treatment**. No time-varying confounding, no g-formula, no MTP. Its overlap strategy (control the generating process) is a real alternative to ours — we must say why we do not simply do that across rounds. |
| 13 | **ROSA / ROSA2** — Wei et al. (`arXiv:2509.23166`, `arXiv:2603.01375`) | Explicit sequential framing over turns with per-turn feedback as reward; one-step closed-form-style update cheap enough to run mid-dialogue; ROSA2 co-optimizes text and weights and proves co-adaptation shrinks required parameter shift. | Greedy one-step rules, not backward-induction optima. No identification, no estimand, no OPE. Single author cluster (sequel to itself), self-reported best cases. ROSA2's ICML 2026 claim unsupported; both repos bare-bones. |
| 14 | **Latent Textual Treatments** — Feldman, Venugopal, Spiess, Feder (`arXiv:2602.15730`) | The sharpest warning for our design: characterizes the bias from adjusting on a text representation that conflates treatment and covariate information; fixes it with covariate residualization. econ.EM register. | Point treatment in a **randomized** SAE-steered design → overcontrol, not observational confounding. Nothing sequential. But the result transfers directly: any embedding of prompt **or history** that we adjust on contains the treatment. |
| 15 | **Functional Treatments with Stochastic Policies** — Barnard, Huling, Wolfson (`arXiv:2606.27518`) | Proof that positivity-free stochastic policies survive an **infinite-dimensional** treatment space: function-valued exposures, modification along one analyst-chosen basis function, continuous-time confounding, asymptotic normality, rate double robustness. | The space is real-valued functions and the method leans on **linear/basis structure text does not have**. Supports "not intrinsically scalar"; supports nothing about strings. |
| 16 | **Causal History Effects in Multi-Turn Interaction** — Li et al. (`arXiv:2609.05882`) | Step-level **counterfactual** interventions on dialogue history: Neutralization (~3000 conversations) and Turn Surgery, showing specific assistant turns selectively flip failure to success. | Audit only — no optimization, no estimand, no estimator. Cite as motivation; our differentiator is that we optimize. |

---

## 3. NOVELTY CLAIM

> We formulate the assistant's next message in an ongoing multi-round interaction as a sequential treatment and give the first identification-and-estimation framework for it: a dynamic treatment regime over a text-valued action space, with an explicit support-preservation condition in place of point-treatment positivity, sequential-ignorability conditions stated for history that the agent's own earlier actions generate, nuisances residualized so the adjustment representation does not contain the treatment, and a turn-level orthogonal off-policy estimator of the multi-round policy value from logged interactions.

### Weakest point 1 — "first" is a negative search result, and the claim is a conjunction of four things that each already belong to someone else

Nakamura & Imai (`2605.07834`) already estimate effects of **sequences** of text treatment features with an MSM, a per-feature deconfounder and valid semiparametric CIs. Kiyohara et al. (`2504.02646`) already learn a **per-context prompt policy off-policy** from logged bandit feedback with a variance-controlled estimator over a large text action space. Zhang, Wang & Dhillon (`2502.17538`) already do **Q-learning for an optimal DTR in a language action space**. Díaz et al. (`2006.01366`, `2605.24167`) already own the **support-preservation identification route**. The claim survives only as the conjunction, and a hostile reviewer will call that composition rather than contribution. The negative search ("no MTP/stochastic-intervention identification over text") was last run 2026-09-19 and is load-bearing — **re-run it before submission**.

### Weakest point 2 — the machinery we are promising does not exist for strings, and the obvious implementations are already known to fail

LMTP Assumption 1 (*if `(a_t,h_t)` is in the support then `(d(a_t,h_t),h_t)` is too*) has **no definition when the action is a string**, and nothing plays the role of a generalized propensity or conditional density over text. The nearest precedent (`2606.27518`) solves the infinite-dimensional case only by leaning on basis structure text lacks. On the estimation side, `2606.05558` fed **exact per-token behavior log-probabilities** to IS/WIS/DR and they still lost decisively to a learned world model, because ratios over horizon × vocabulary-scale action space degenerate — so our estimator depends on a coarsening (factorized per-turn heads, `2510.17173`; turn-level geometric-mean ratios, `2511.20718`) whose estimand is then **no longer the text policy we claimed to evaluate**. And `2602.15730` applies to us as much as to CPO: any prompt or history embedding we adjust on contains the treatment, and residualization in a sequential, non-randomized setting has not been shown to work by anyone.

---

## 4. MUST-CITE, by role

### 4.1 Causal-longitudinal backbone
`arXiv:2006.01366` / DOI `10.1080/01621459.2021.1955691` (LMTP, JASA) · DOI `10.1515/em-2012-0001` (Young, Hernán, Robins 2014 — **primary source of the support condition; cite alongside Díaz et al., not instead of**) · `arXiv:2605.24167` (**MTPs depending on the natural *history* — the case a multi-round intervention actually needs; the 2021/2023 paper does not cover it**) · `arXiv:1704.00211` (Kennedy IPSI, JASA 114:645-656) · `arXiv:2110.10532` (incremental effects review) · DOI `10.1080/03610929408831393` (Robins 1994 SNMM, corrected DOI) · `arXiv:2509.22916` (Shahn, SNMMs for MTPs — per-round heterogeneity) · `arXiv:2511.14545` (DeepBlip, ICML 2026) · `arXiv:2509.26429` (DRQ-learner, ICLR 2026) · `arXiv:2505.13092` (TEE for optimal decision-making, NeurIPS 2025) · PMLR v162 `melnychuk22a` / `arXiv:2204.07258` (Causal Transformer — the canonical C/SO/SI template) · `arXiv:2002.04083` (CRN, ICLR 2020) · `arXiv:2606.27518` (functional treatments) · `arXiv:2304.09460` (Hoffman et al. tutorial — best plain statement of the positivity logic, structural vs. practical violations) · DOI `10.1146/annurev-statistics-042424-110756` (Sarvet & Stensrud, *Annu. Rev. Stat. Appl.* 13:439-463, 2026 — **the synthesis a reviewer will measure our assumption set against; get it through the library**) · `arXiv:2502.11820` / DOI `10.1515/jci-2025-0007` (stochastic-positivity diagnostic — MTPs are **not** automatically safe) · `arXiv:2411.14285` (Levis et al., optimal transport — natural-value dependence is not a free lunch under confounding) · `arXiv:2206.12525` (Ying — measure-theoretic apparatus for non-finite-dimensional actions) · DOI `10.1002/sim.5907` (Haneuse & Rotnitzky 2013) · DOI `10.1111/j.1541-0420.2011.01685.x` (Muñoz & van der Laan 2012) · Richardson & Robins (2013), CSSS WP 128 — **cite as an unrefereed working paper**; Thm 31 is the source of LMTP's Assumption 3.

**Assumption table we should build** (positivity statements differ and must not be conflated): two-sided `0 < p < 1` in Causal Transformer; one-sided `> 0` in DeepBlip and CRN; policy-support coverage only (`supp π_e ⊆ supp π_b`) in the MDP paper; enforceable support preservation in LMTP; **none** in Kennedy's IPSIs. Conditioning sets differ too: CT on `{X̄_t, Ā_{t−1}, Ȳ_t, V}`, CRN on `{X̄_t, Ā_{t−1}, V}` (no past outcomes), DeepBlip on a generic `H_t`, the MDP paper on `S_t` alone.

### 4.2 Text-as-treatment / prompt-as-treatment
`arXiv:2410.00903` (GPI — the identification backbone the prompt preprints lack) · `arXiv:2605.07834` (**MANDATORY** — closest existing work to a DTR over text) · `arXiv:2602.15730` (covariate residualization; the bias our own nuisances risk) · DOI `10.1609/aaai.v39i14.33669` / `arXiv:2412.15314` (SCIE, AAAI-25 39(14):15212-15220 — peer-reviewed precedent for instructions-as-treatment) · `arXiv:2602.01711` (CPO — the T=1 baseline) · `arXiv:2605.25998` (**KDD 2026** — peer-reviewed legitimation of prompt-as-treatment + doubly-robust/orthogonal policy learning, and it explicitly leaves the sequential/agentic case open) · `arXiv:2609.01322` (SAE-based confounder adjustment, EMNLP 2026 Main) · `arXiv:2410.21474` (CausalDANN) · `arXiv:2403.02738` (front-door Causal Prompting, AAAI 2025 — **different estimand; name and dismiss**) · `arXiv:2609.05882` (causal history effects in multi-turn).

### 4.3 Prompt-optimization baselines (and the non-causality claim)
`arXiv:2310.16427` (PromptAgent, ICLR 2024 — **§3.2 treats instance-specificity as a failure mode to search away from**, a free gift for our framing) · `arXiv:2309.03409` (OPRO, ICLR 2024) · `arXiv:2305.03495` / `2023.emnlp-main.494` (ProTeGi — UCB/successive-rejects is an **A/B test**, not causal inference) · `arXiv:2406.07496` + Nature DOI `10.1038/s41586-025-08661-4` (TextGrad — our nearest neighbour) · `arXiv:2507.19457` (GEPA, ICLR 2026 Oral — **§5.1's inference-time mode still optimizes a shared prompt; it only drops the generalization requirement by putting target tasks into `D_train`**) · `arXiv:2504.02646` (**read before finalizing any novelty sentence**) · `arXiv:2605.26655` (edit-level propensity-adjusted analysis; authors hedge to "associational") · `arXiv:2506.05305` (ProRefine, workshop) · PMLR v267:71910-71937 `ye25a` (`eva` — train-time curriculum, **not** multi-turn).

**Verified fact worth stating once:** across the full texts of PromptAgent, OPRO, ProTeGi, TextGrad and GEPA there are **zero** occurrences of "causal" or "counterfactual" in the methods (OPRO's only hits are a BBH task named `causal_judgement`). None defines a causal estimand, computes a propensity, or does IPW/DR/off-policy estimation.

### 4.4 Multi-turn RL, multi-turn adaptation, and the self-correction constraint set
`arXiv:2405.14655` (Shani et al., trajectory-level preference over whole conversations) · `arXiv:2608.17499` (FACA — **main baseline to differentiate from**) · `arXiv:2502.00640` (CollabLLM, ICML 2025 Outstanding Paper) · `arXiv:2509.23166` (T2PAM/ROSA) · `arXiv:2603.01375` (ROSA2 — **cite as preprint, not ICML 2026**) · `arXiv:2509.24696` (T-POP, ICML 2026) · `arXiv:2502.19148` (**Amulet, ICLR 2025 — the de facto SOTA reference for test-time personalization, missing from the original list**) · `arXiv:2507.14295` (UFO — **the mandatory zero-information-feedback control**) · `arXiv:2510.05921` (prompt reinforcing; non-stationary behavior policy) · `arXiv:2310.01798` (Huang et al., ICLR 2024) · `arXiv:2406.01297` / TACL 2024 (**strongest single negative citation**) · `arXiv:2311.08516` (failure is **detection**, not repair — highest-leverage opening) · `arXiv:2310.12397` (critique **content** largely irrelevant) · `arXiv:2409.12917` (SCoRe, ICLR 2025 Oral — the fix is training, not prompting) · `arXiv:2303.17651` (Self-Refine — architecture only) · `arXiv:2303.11366` (Reflexion — positive, but it rests on a verifier) · `arXiv:2304.09797` (PHP, AI4MATH workshop — critic-free ablation target) · `arXiv:2601.00514` (illusion of insight; **uncertainty-gated** revision does help).

**Three confounds our experiments must survive.** (1) **No oracle stopping** — with ground-truth halting Huang et al.'s GPT-4 GSM8K flips from −6.5 to +2.0. Our termination rule must be computable at inference time. (2) **Matched compute** — self-consistency beats multi-agent debate at equal budget and the gap *widens* (83.2 vs 85.3 at 6 responses; 83.0 vs 88.2 at 9). Matched-token self-consistency is our real baseline, not greedy CoT. (3) **Critique-content ablation** — swap in random or adversarial feedback; without it we cannot show the critique carries information rather than merely inducing resampling.

### 4.5 Off-policy evaluation and logging design
`arXiv:2510.17173` (per-turn factorized heads, SNIPS+AIPW, reconstructed propensities) · `arXiv:2606.05558` (**the decisive negative result on token-level IS**) · `arXiv:2511.20718` (turn-level geometric-mean ratios — off-policy **training**, do not cite as OPE) · `arXiv:2406.10030` (single-turn reuse of logged human feedback; **its propensity description is the least firmly sourced item in the bundle — verify before citing on that point**) · `arXiv:2209.00876` (pre-LLM dialogue-policy evaluation from logs) · `arXiv:2605.15108` (logging-policy design — the theory for prospectively randomizing our own deployment; **no LLMs, do not cite as an LLM paper**) · `arXiv:2605.29500` (exact unordered slate propensities — **slate recommendation, NOT dialogue**; listed so it is not miscited).

### 4.6 Design / SMART — **this slot is empty**
The audited evidence contains **no verified SMART or micro-randomized-trial citation**. Do not write a SMART paragraph from memory. Commission a separate verification pass; the likely targets (Murphy 2005; Lavori & Dawson; Almirall / Nahum-Shani on MRTs) are all unverified here. In the interim, the design argument we *can* make from confirmed sources is prospective logging-policy design (`2605.15108`) plus the positivity diagnostic (`2502.11820`).

### 4.7 Benchmarks and logs
`arXiv:2406.12045` (τ-bench; `pass^k`) · `arXiv:2506.07982` (τ²-Bench — **user constrained by tools and observable state, the main existing fix for hallucinating simulators**) · `arXiv:2402.14762` / `2024.acl-long.401` (MT-Bench-101 — **scripted replay, not simulation; cannot evaluate a policy that changes the trajectory**) · `arXiv:2501.17399` / `2025.findings-acl.958` (MultiChallenge — failure taxonomy from real logs) · `arXiv:2405.01470` (WildChat-1M — **ODC-BY, not the paper's AI2 ImpACT**; no outcome labels) · `arXiv:2309.11998` (LMSYS-Chat-1M — **gated, no redistribution; ~2.0 turns mean, shallow for DTR**) · `arXiv:2404.16019` (**PRISM — best fit for DTR among public logs: covariates X, per-turn model choice A, per-turn ratings R, all linked to an individual id, so heterogeneity is identifiable**) · `arXiv:2601.17087` (Lost in Simulation — success swings up to 9 points on simulator identity alone; sim2real gap is itself subgroup-dependent, worse for AAVE and Indian English) · `arXiv:2603.11245` (Mind the Sim2Real Gap, COLM 2026 — 451 humans, 165 tasks, 31 simulators, User-Sim Index; simulators are excessively cooperative and give uniformly positive feedback; **model capability does not predict simulation faithfulness**) · `arXiv:2605.20204` (RealUserSim — Formalism Ceiling, Directive Amplification; flag the date anomaly).

---

## 5. ALREADY DONE — drop these from the plan

1. **"First to frame the prompt/instruction as a treatment."** Done three times, one peer-reviewed: SCIE (AAAI-25) puts it verbatim in its abstract; CPO builds on it; the KDD 2026 position paper states prompt-as-treatment with outcome-as-reward *and* says doubly-robust/orthogonal policy learning is directly relevant. Cite as established framing.
2. **"Per-instance / per-query prompt selection with a causal estimator."** Kiyohara et al. (`2504.02646`) did the off-policy version; TextGrad (Nature 2025) did the per-instance test-time version.
3. **Building a DML-debiased reward model over prompt+query embeddings.** CPO did it, and `2602.15730` shows joint DML on both embeddings is exactly the conflation that biases the estimate. Reimplementing reproduces a known defect. Use as baseline **and critique target**.
4. **"Q-learning for an optimal regime over a language action space."** `2502.17538` did it, embeddings and decoding included. Only the **identification and OPE layer** is still ours.
5. **Neural SNMM / blip machinery.** DeepBlip has simultaneous blip learning under a Neyman-orthogonal loss with transformer nuisances and offline policy evaluation. Extend it; do not re-derive it.
6. **Orthogonal doubly-robust Q-learner in MDPs.** `2509.26429` derived it from the EIF with double robustness, orthogonality and quasi-oracle efficiency under weak positivity. **The gap is the action space, not the estimator.**
7. **"Diagnose which prompt edits / which turns matter."** Both halves exist: `2605.26655` (edit-level propensity-adjusted audit, systematic edit×task interactions) and `2609.05882` (Neutralization + Turn Surgery, specific turns selectively flip outcomes). Auditing is motivation now, not contribution.
8. **Token-level importance weighting for multi-turn OPE.** `2606.05558` implemented it with exact log-probs (BPE-safe span matching) and it still lost to a learned world model; the authors call exact log-probs privileged and unavailable in deployment. Go coarse: factorized per-turn heads or turn-level geometric-mean ratios.
9. **Any component whose only signal is the model critiquing itself.** Five independent results close it (`2310.01798`, `2406.01297`, `2311.08516`, `2310.12397`, `2601.00514`). Mechanism: an unaided model cannot tell correct from incorrect, and since accuracy starts above 50% the expected effect of an uninformative revision is **negative** — which is why degradation is systematic, not noisy. Name the external signal in every round, or cut the round.
10. **"Jointly adapt prompt text and weights across turns."** ROSA2 owns it and even proves co-adaptation shrinks the required parameter shift. Differentiate on the decision-theoretic side or not at all.
11. **"Multi-turn-aware reward via simulated rollouts."** CollabLLM did it and validated with 201 humans. Our differentiator must be a **log-learned** user model with **decision-time** rollouts, not rollouts per se.
12. **Trusting a prompt-based user simulator.** `2601.17087` and `2603.11245` make the simulator an unmeasured nuisance parameter that shifts the estimand, with uniformly positive feedback biasing any simulator-derived value upward. Ground it in environment state (τ²-Bench) or validate against humans with the published protocol.
13. **Bandit best-arm identification over candidate prompts.** ProTeGi implemented and compared UCB, UCB-E, Successive Rejects, Successive Halving. Neither novel nor causal.
14. **"Extend MTPs to infinite-dimensional treatments."** `2606.27518` did it for function-valued exposures. Say instead, precisely, that **text has no basis structure** — that is the actual open problem.
15. **Building a new multi-turn benchmark.** τ-bench, τ²-Bench, MT-Bench-101 and MultiChallenge cover the space, and PRISM is the only public log with the X/A/R-per-person structure a DTR needs. Build on PRISM plus a human reference protocol.

---

## 6. What the evidence says our contribution should actually be

The surviving position is narrow and it is a conjunction. Everything that makes it defensible also makes it fragile, so state it in exactly this order and no wider:

1. **The unit of decision is the next message in a live interaction**, not a task-level prompt (all five canonical optimizers), not a static artifact against a fixed query (TextGrad), and not a single context-conditioned prompt with an immediate reward (Kiyohara et al.).
2. **The estimand is a policy value over rounds**, identified under stated sequential-ignorability and support-preservation conditions — which is precisely what `2502.17538` omits and what `2605.07834` supplies for feature sequences but not for interactive rounds.
3. **Nuisances are residualized** so the adjustment representation does not contain the treatment (`2602.15730`, with `2609.01322` as the practical counterpart) — and we must apply this to our *own* history embeddings, not only to CPO's.
4. **Estimation is turn-level and orthogonal**, not token-level (`2606.05558` forecloses tokens; `2511.20718` supplies the granularity; `2509.26429` and `2511.14545` supply the orthogonality).
5. **Propensities are logged prospectively, not reconstructed** (`2510.17173`'s stated limitation; `2605.15108`'s design theory). This is the one contribution nobody can take from us, because it is a property of how we deploy, not of what we derive.

Two things to add to the backbone before drafting: `arXiv:2605.24167` (history-dependent MTPs — the published LMTP paper does not cover the case we need) and the Sarvet & Stensrud 2026 *Annual Review* (the synthesis a reviewer will hold us to on what natural-value interventions do and do not deliver).

---

## Appendix — the area chair's surviving reframing

A separate agent was asked to write the rejection for a paper claiming to be
first to formulate multi-turn prompting as a longitudinal causal problem, to
estimate sequential blip/Q effects of language-valued interventions, and to train
a generative prompting policy against the causal critic — and then to state the
one reframing that would survive its own attack. Its answer, quoted in full
because it is the most useful single paragraph in this audit:

Drop all three "first" claims and drop the pretence of identifying effects of
language-valued interventions. What survives my own attack is a much smaller
paper whose contribution is a measurement instrument plus a coarsening-as-
identification argument, not a framing and not an estimator.

Concretely: (1) Define the round-t action not as the emitted string but as a
small, finite, analyst-specified set of prompt-move types — a factorized
decision head in the spirit of the Tool/Style heads of arXiv:2510.17173 (e.g.
ask-clarifying-question / decompose / request-verification / restate / no-move).
The coarsening is the technical content, not a compromise: it is the measurable
function of the string that makes the generalized propensity well defined,
restores a checkable positivity condition, and gives the blip decomposition a
non-arbitrary reference level (no-move). State it as such, and state plainly
that effects of the underlying string are NOT identified. (2) Randomize that
head prospectively at deployment and LOG the propensities, designing the
randomization for OPE error rather than accepting whatever the deployment gives
you (arXiv:2605.15108). This is the one thing nobody in this literature has:
arXiv:2510.17173 had to reconstruct propensities post hoc on N=7 users;
arXiv:2606.05558 calls exact propensities privileged and unavailable in
deployment; CollabLLM, FACA, ROSA and T-POP are all on-policy with no
propensities at all. (3) Estimate round-specific effects with the existing
orthogonal machinery, cited as such — DeepBlip for blips, the DRQ-learner for Q
— with history nuisances residualized per Feldman et al. (arXiv:2602.15730),
aggregation at turn level rather than token level (the geometric-mean ratio of
arXiv:2511.20718), and reported overlap diagnostics plus a sensitivity analysis
over the reference move. (4) Use the estimated effects for one narrow,
empirically checkable purpose: deciding WHEN to intervene — an uncertainty- or
position-gated policy over the finite move set — rather than generating the next
string. This is the only place the evidence says an effect estimate can pay:
Tyen et al. show repair is competent once localization is given, and
arXiv:2601.00514 finds triggering revision specifically at high model
uncertainty reliably helps. (5) Evaluate against budget-matched self-
consistency, the UFO zero-information control, answer-conditioned re-prompting,
and a critique-content ablation with randomized or adversarial critic outputs,
on real human counterparts (or, if simulated, with the User-Sim Index of
arXiv:2603.11245 reported and the simulator treated as a named nuisance with
sensitivity across simulator choices per arXiv:2601.17087). Report the negative
results.

The honest claim is then: "the first prospectively randomized, propensity-logged
multi-round human-LLM deployment with turn-level outcomes, a coarsened-action
positivity argument that makes round-specific blip/Q estimands well defined over
text, residualized history nuisances, and an uncertainty-gated intervention
policy that beats matched-budget self-consistency and a zero-information
feedback control." That is a dataset-plus-identification-argument-plus-honest-
benchmark paper. It concedes the framing to AAAI-25 and KDD 2026, the
sequential-text estimation to Nakamura and Imai, the language-action DTR to
Zhang et al., the estimators to DeepBlip and the DRQ-learner, and per-instance
causal prompt selection to Kiyohara et al. — and its remaining novelty is real,
because arXiv:2605.25998 explicitly leaves the sequential/agentic case open,
arXiv:2605.07834 is sequential within a document rather than against a
responding counterpart, and no one has logged propensities in a multi-turn LLM
deployment. I would not reject that paper.

