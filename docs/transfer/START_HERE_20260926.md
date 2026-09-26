# DTR-MultiRoundLLM laptop transfer — 26 September 2026

This is the portable entry point for the original research idea, the user-visible conversation, the theory/manuscript, the experiment record and the next decisions. The repository is **public**. This handoff records what was published and what was actually executed; it does not turn a proposal, worker acknowledgement or source test into empirical validation.

## Restore and orient

```sh
git clone https://github.com/ykzeng-yale/DTR-MultiRoundLLM.git
cd DTR-MultiRoundLLM
git switch main
git pull --ff-only origin main
git config user.name "Yukang Zeng"
git config user.email "ykzeng2019@gmail.com"
git status --short --branch
```

The annotated tag `handoff-2026-09-26` identifies this transfer snapshot. Continue from the **current ancestry of `main`** after fetching; worker updates may have arrived since the tag. Never merge the old, rewritten September 20 ancestry or force-push. Read [AGENTS.md](../../AGENTS.md), [COORDINATION.md](../../COORDINATION.md), [the exchange rules](../coordination_30min.md), [worker experiment status](../experiments_status.md), [lead experiment status](../current_experiment_status_20260926.md), [scientific judgment](../scientific_judgment_20260920.md), and [latest checkpoint](../monitoring_checkpoint.md), in that order. Issue [#3](https://github.com/ykzeng-yale/DTR-MultiRoundLLM/issues/3) is the shared handoff; issues [#2](https://github.com/ykzeng-yale/DTR-MultiRoundLLM/issues/2), [#4](https://github.com/ykzeng-yale/DTR-MultiRoundLLM/issues/4), and [#5](https://github.com/ykzeng-yale/DTR-MultiRoundLLM/issues/5) track adjacent stages. There was no open PR at this transfer review.

The original supplied discussion is preserved byte-for-byte in [original_idea_and_prior_discussion_20260919.txt](original_idea_and_prior_discussion_20260919.txt) (SHA256 `cdfd745b49e14ff9950db5583016d7bf62baba32ab208e0cdfeb353fa8440d7e`). It includes prior conversational literature and design claims; treat those as **historical ideas, not independently verified citations or current scientific judgments**. The [user-visible chat export](user_visible_chat_through_20260926.jsonl) contains timestamped user text and assistant commentary/final responses from this Codex task through 20:26:06 UTC on 26 September; its [manifest](transfer_manifest.json) records 791 text messages, counts and hashes. It intentionally excludes system/developer instructions, hidden reasoning, tool invocations/outputs, attached binary files and local secrets. It includes repeated automation and environment-context messages because those appeared in the user-visible session stream. The live task, if available in the same account on the other laptop, may contain later messages. Repo code, manifests, results and the linked issue discussions remain the authoritative evidence.

## Scientific idea and limits

The fixed receiver/agent acts on an initial task. At each decision point, a user-side next message or `STOP` is the intervention, the publicly available conversation is the history, and later task quality is the outcome. The target is whether a **history-conditional same-prefix next-prompt policy** improves final quality over a competent development-selected fixed instruction, with a separately defined practical independent-sampling controller. The formal target is an expected policy contrast over a specified task/family population and continuation rule, not an observable individual causal effect for one conversation. Later training of a free-form prompt generator is conditional on this simpler question being answerable and useful.

The theory is in [the working manuscript](../../manuscript/current_paper_20260922.md), [landmark methods](../../manuscript/landmark_methods_20260920.md), [scientific judgment](../scientific_judgment_20260920.md), and [independent policy design](../independent_prompt_policy_validation_design_20260922.md). The older PDFs under `manuscript/` are dated historical assemblies; do not substitute them for the editable current sources. Classical DTR identification and DR estimation are not claimed as novel. Support for exact language actions, legitimate public information, task-family inference, measurement validity, comparator information/cost parity and transport remain explicit limits.

## Evidence at transfer

The lead-owned [all-experiment status](../current_experiment_status_20260926.md), [worker ledger](../experiments_status.md), and [readiness rubric](../readiness.md) give the detailed provenance. Key distinctions:

| Stream | Observed or executed state | Scientific interpretation |
|---|---|---|
| Theory, known-truth and historical routing | Theory/source tests and bounded synthetic/numerical diagnostics; a 4,488-episode, 561-root historical fixed-bank/repair reuse | Supports scoped mathematical/software checks. Historical routing and fixed-bank selection did **not** randomize the next user prompt. The favorable 7B split was selected among overlapping analyses; repair lost to independent redraw under the reviewed setting. |
| Development v1/v1b/v1c | 147 attempted receiver calls on the same seven roots across three engineering variants | One reused development setting, not three independent replications. v1b has missing grades. |
| E11 | 77 fresh development receiver calls on seven reused roots | Primary S1−N1 was zero on every root. Finite negative; no equivalence or population-policy claim. |
| E12 | 154 calls, 154 grades on 14 fixed development roots; N1 20/28, S1 19/28 | Same-prefix primary contrast −1/28 (−3.57 points); negative/inconclusive for usefulness, not a population futility bound. Extractor/format findings do not prove semantic damage or mediation. |
| E13a | 60 calls and 60 grades at five reused public-fail checkpoints; R1 9/30, FRESH 12/30 | Package-level development contrast −0.100; it does not isolate diagnostic content or measure the B2 controller. Preserve the negative. |
| E13b and E14 | E13b never released. E14 is source/mock only, **zero real E14 receiver calls**; proposed N1/S1 efficacy collection is **NO-GO** | No result may be inferred from E14's tests, source package or proposed budget. Do not run its held batch. |
| Independent prompt policy | No frozen selector `d`, competent fixed `b1`, untouched-family trial or confirmatory outcome | No independent policy efficacy evidence. |

The saved development call rows sum to **438 attempted calls, 134,340 prompt tokens and 32,949 completion tokens**, with $0 direct paid-service charges reported. These are archival arithmetic, not 438 independent subjects, total energy cost or a pooled effect. The [E11](../e11_lead_judgment_20260922.md), [E12](../e12_lead_judgment_20260923.md), and [E13a](../e13a_lead_judgment_20260923.md) judgments preserve the actual estimands and qualifications. No new model calls or candidate/reference execution were made to assemble this transfer.

The fixed [progress rubric](../progress_current.json) is **58% complete, change 0 percentage points** at the last three-hour check. This is a planning estimate of milestone completion, **not** a success probability. Prompt efficacy is unestablished; independent policy validation is absent; the complete project is not submission-ready. The denominator has not changed for this transfer.

## Latest design and worker exchange

The lead rejected a repeated format-only N1/S1 E14 stage as the next efficacy test. [LEAD-POLICY-13](../policy_patch_rethink_action_candidate_20260926.md) proposed provisional same-prefix `PATCH` versus `RETHINK` whole-recipe development actions; [LEAD-POLICY-14](../policy_patch_rethink_scope_correction_20260926.md) limited the claim to the total effect of whole instructions. After the worker identified a real empty-failure wording defect, the lead independently verified the pinned E12 renderer and saved diagnostics and replaced **both** unfrozen texts in [LEAD-POLICY-15](../policy_patch_rethink_failure_scope_20260926.md). The worker accepted that decision in `32e20b7` at 19:20:37 UTC and made a further valid **three-class** warning: `pass`, payload failure, and `INCOMPLETE` (`timeout`, `unavailable`, `output_limit`). E12's 14 diagnostics show nine pass, five `wrong_value`, and **zero incomplete**; they cannot validate an incomplete-case policy. I checked the class definitions and S1's separate incomplete branch in `experiments/landmark/diagnostic.py` (SHA256 `2a98bccf…`).

**Lead decision at transfer: hold and repair before freezing.** An incomplete diagnostic is neither proof of pass nor proof of a candidate error. The next protocol must explicitly say whether incomplete checkpoints are retried before assignment, included as a separate supported stratum, or excluded by a prespecified eligibility rule, with a missingness/cost consequence in each case. It must also decide whether public-pass histories take `STOP` by rule or enter recipe randomization. Do not silently fold incomplete into “no failure,” condition on post-assignment assessability, or tune this rule after outcomes. The candidate prompts remain **provisional**. E11/E12/E13a negatives remain unchanged. As of worker status commit `40e0650` at 20:21:31 UTC, the worker **reports** watcher running, no run/lease and E14 NO-GO; the lead has not independently observed live process health. The last independently reviewed E14 scientific implementation remains `4931cb9`. Worker acknowledgement, actual execution and independent outcome validation are separate states.

## Roadmap and release gates

1. **Resolve action support:** freeze exact byte-level PATCH/RETHINK and common output contract, map all three public diagnostic classes, and decide public-pass `STOP` versus randomization. Keep the initial public task, answer, diagnostic and receiver identical across same-prefix arms. These are new treatments; E12/E13a grades cannot select between them.
2. **Audit source and sampling:** fix or exclude known specification defects, define root/family groupings and untouched exposure-audited independent-family sampling. The 198-ID MRL-15 convenience frame is not an independent-family sample; four later-ranked roots have prior unresolved exclusions. Do not silently refill or reuse development families.
3. **Freeze measurement and comparators:** validate public-case and private endpoint versions, missing/format rules, receiver/evaluator digests and sources. Select competent fixed `b1` and train `d` only from development support. Keep B2-1R as a separate one-redraw practical controller with its public-case/seed/cost contract; do not replace the same-prefix estimand with compute savings.
4. **Before any fresh model call:** commit protocol/config, exact interventions, family split, seeded assignment probabilities, estimators/analysis, useful-gain threshold, prospective precision/futility rule, three cost ledgers, numerical local resource cap and verified shared-host lease. Confirm disk/memory and other jobs. No paid service or unbounded inference. E14 remains on HOLD until an explicit new scientific release, not merely an available host.
5. **Execute only a justified bounded development stage**, preserve every null/negative and immutable run, then freeze `d` and `b1`. If ranking is unstable or `d` collapses to `b1`, retain that finding rather than rescue it by changing the hypothesis.
6. **Independently validate** the frozen policy on sampled untouched families under the prespecified analysis. Interpret final efficacy and total-resource contrasts separately. Only then decide whether a larger free-form generator and full manuscript are warranted.

The manuscript remains an editable **working draft**; reconcile citations, notation, complete experiment tables, inference, limitations and reproducibility before claiming a full submission package. No journal submission, acceptance or independent policy success is recorded.

## Portable boundaries and scheduling

The committed code, documents, issue comments and `results/` archives are in GitHub. Gitignored `work/`, local model weights, source caches, live process state and application automations are **not** Git artifacts. In particular, a clean clone without the externally pinned MBPP source cannot reproduce the committed E14 package; explicit test skips and alternate-path projections are not original-byte reproduction or execution. Reacquire any external source only under its documented license and verified SHA, and do not run a model from this handoff alone.

The user's `dtr-multiroundllm-hourly-research-follow-up` three-hour recurring check was **deleted in the Codex app for this task** at transfer. It is not restored by cloning the repository. The separate `dtr-theory-and-github-coordination` automation targets **DTR-AgentEvals**, another repository, and was left unchanged. The existing experiment worker may continue to publish GitHub updates; a new laptop should read all commits since this handoff rather than assume a current receipt or live lease. Do not create a duplicate worker or job. For restart, check `git log`/issues, preserve concurrent changes, and record exact last-seen versus independently reviewed commits before deciding the next action.
