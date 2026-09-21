# Literature-guided experimental redesign and open-source reuse

21 September 2026. **Source review and prospective design decisions; no new
receiver experiment or reproduction of another paper.** This responds to the
owner's request to learn from related experimental designs and use open-source
implementations. It supplements, rather than replaces, the [scientific
judgment](scientific_judgment_20260920.md) and [landmark
protocol](landmark_experiment_protocol.md). The original seven coding roots,
their holds, and all negative findings remain unchanged.

## Scientific conclusion

There is a plausible application in selecting a repair or context-management
instruction using reliable, deployment-available diagnostics. Existing research
supports investigating that mechanism; it does not establish our learned
prompt-policy benefit. The central question remains whether **public history
predicts differences between supported next-prompt effects well enough to improve
a frozen policy on independent tasks**, beyond a competent fixed strategy.

Our DTR formulation gives a disciplined definition of that question and a way to
identify supported effects under stated assumptions. Classical identification,
IPW and DR theory are not our novelty, and DR need not beat a well-specified
history-adjusted regression. A single landmark is the first discriminating test,
not a validated long-horizon policy. A marginal null, weak syntactic prompt, or
fixed-bank ceiling does not refute semantic prompt personalization.

## What the close experiments actually test

Paper findings below are **author-reported**. The code observations were checked
against pinned official sources; a later repository head is not necessarily the
commit used in its paper. None of these studies was rerun here. Metadata and
source hashes are in the accompanying [source manifest](literature/source_inventory_20260921.json).

| Primary source inspected | Experiment or measurement lesson | Decision for this project |
|---|---|---|
| [Causal Inference for Human–Language Model Collaboration](https://aclanthology.org/2024.naacl-long.91/), [full text v1](https://arxiv.org/html/2404.00207v1) | Direct longitudinal causal predecessor. Its empirical construction rewrites conversations and changes labels/text correlations, testing robustness of counterfactual prediction. The inspected implementation uses conversation-level K-fold splits. | Preserve this close prior art. Separate synthetic-label robustness from fresh randomized receiver outcomes; split users/topics/families where they create dependence. |
| [Policy Learning with a Natural Language Action Space, v1](https://arxiv.org/html/2502.17538v1) | Uses two-stage language-action learning, generated intervention sequences and classifier rewards. It refines system outputs, rather than selecting a user's next instruction to a fixed receiver. No official code was verified in the inspected sources. | Reuse sequential experimental contrasts conceptually, but do not call classifier reward a validated task outcome or claim first language-valued DTR learning. |
| [Prompt Optimization with Logged Bandit Data, v1](https://arxiv.org/html/2504.02646v1) | A contextual prompt decision with auxiliary generated output and synthetic/learned rewards. Compares regression, importance-weighting and related policy learners. This is close personalization prior art, but not a multi-round regime. | Study many-to-one prompt-to-output mappings and misspecified representations; retain a matched fitted-Q baseline. Do not reuse a reward conditional on a sampled output as action-level truth. |
| [Self-Refine, v2](https://arxiv.org/pdf/2303.17651v2), §§3–4 and appendices | Compares specific, generic and absent feedback, with mixed task-specific outcomes. Its inspected GSM evaluator preserves success after the first correct attempt; that file measures cumulative correctness, not necessarily the final submitted answer. The code observation does not identify which published table used it. | Keep the feedback ablation; grade the actual final chosen artifact. Count critique generation separately from answer generation. |
| [Reflexion, v4](https://arxiv.org/html/2303.11366v4), §4 and Appendix B | HotpotQA exposes gold correctness feedback; coding can instead use generated tests. HumanEval improves while MBPP Python falls from 80.1% to 77.1%. An inspected pass-at-k=1 coding path keeps final grading outside reflection. | Specify feedback access per task. Compare public observations alone against the same observations plus reflection; evaluate verifier errors. Do not label every Reflexion variant oracle-informed. |
| [CRITIC, v2](https://arxiv.org/html/2305.11738v2), §§4.1–4.4 | Tool-free ablations change available evidence. The rejection-sampling comparison uses maximum gold score and is paired with an oracle-preserving variant. Tool and model operations can multiply within one correction. | Separate evidence acquisition from prompt presentation. Use a deployable resampling selector; retain oracle selection only as headroom. |
| [Large Language Models Cannot Self-Correct Reasoning Yet, v2](https://arxiv.org/pdf/2310.01798v2), §§3–5 | Measures both correction and degradation, and compares debate with same-response-budget self-consistency. Intrinsic refinement can damage correct answers; oracle stopping hides that damage. No official implementation was located in the bounded search. | Preserve a neutral reconsideration control, correct-to-wrong outcomes and complete initial instructions. The findings are not an impossibility theorem for external feedback. |
| [MINT, v2](https://arxiv.org/html/2309.10691v2), §2 and Appendix C | Varies turn budgets, feedback source and ground-truth access. Default textual feedback omits ground truth, but the environment still supplies binary correctness feedback. Tasks are partly curated using model performance. | Distinguish textual feedback from environment feedback, and declare the resulting selected task population. Its success-versus-budget slope is not a randomized marginal turn effect. |
| [LLMs Get Lost in Multi-Turn Conversation, v1](https://arxiv.org/html/2505.06120v1), §§3–5 and appendices | FULL, concatenated shards, progressive disclosure, recap and snowball conditions separate some wording and information-timing explanations. Ten conversations per instruction are nested repeats. The inspected sharded runner stops at verified correctness. | Add restart/consolidation controls, but do not call information-disclosure effects wording effects. Freeze final-output and stopping rules independently of the upstream runner. The inspected paper is v1, not a verified reproduction of its later conference version. |
| [C3 / Exact Is Easier, v2](https://arxiv.org/html/2603.06859v2), Appendix B | Restores histories and samples action continuations with a matched evaluator-call budget and multiple training seeds. Its treatment is cooperative-agent output, not our user prompt. | Reuse restoration/accounting ideas, not its causal target or entire training stack. Separate within-prefix Monte Carlo noise from task variation. |

Two particularly consequential source findings were independently reread by the
coordinator: the first-correct loop in Self-Refine's
[`gsm_selfref_eval.py`](https://github.com/madaan/self-refine/blob/9a206d41e5d2d0c241bb441f41eeadb945afaa55/src/gsm/gsm_selfref_eval.py#L86),
and the gold-maximum comparator in CRITIC's
[`qa/evaluate.py`](https://github.com/microsoft/ProphetNet/blob/5cf70eb41cdaa1d8faa3e1265d95ee5792d49a53/CRITIC/src/qa/evaluate.py#L9).
These are reasons to adapt components carefully, not allegations that every
result from those projects is invalid.

## Amendment to the prospective landmark design

This amendment defines requirements for the **next version**, not a retroactive
change to `task_contracts_v1.json` or the current collector. No new collection is
released by this document.

1. **Separate the source of information from its presentation.** For the primary
   same-prefix instruction-strategy comparison, compute any permissible public diagnostic once
   and place the exact same diagnostic in both repair contexts. Compare a neutral
   revision instruction with a frozen diagnostic-specific instruction. A separate
   no-diagnostic arm measures the added diagnostic package. Private outcomes,
   hidden failing inputs, reference answers and oracle initial correctness are
   never used to construct prompts or decide eligibility.
2. **Treat the intervention as an actual, inspectable policy.** Replace neither
   the existing loop/division scaffold nor its labels in place. A new renderer
   must explicitly map public observations to exact instruction strings and be
   versioned separately. Any negative finding applies to that renderer and
   receiver, not every possible semantic optimizer. Any richer LLM-generated
   critique incurs its own calls, tokens, failures and versioned generator law.
3. **Use five development branches only when the extension is frozen.** Proposed
   arms are neutral revision without diagnostic; targeted revision without
   diagnostic; neutral revision with the shared diagnostic; targeted revision
   with that same diagnostic; and restart with the complete original public task
   plus that diagnostic. STOP retains the initial artifact. This small factorial
   distinguishes diagnostic availability from instruction strategy; report the
   cell-specific contrasts and interaction, not a universal wording effect.
   Restart changes context and is a separate strategy. The no-diagnostic renderer
   is a frozen function of public history only, with no access to the computed
   diagnostic or diagnostic-dependent selection branches. Targeted prompts must
   not manufacture diagnostics in those cells. Both with-diagnostic arms receive
   identical diagnostic bytes. Diagnostic computation and deployment
   access are part of the treatment contract, even if a processor could derive
   the information from the public task and answer. Freeze what restart retains
   or discards: prior answer, messages, tool traces and mutable state. If a
   diagnostic refers to omitted code or text, specify the minimum public context
   needed to interpret it; otherwise that restart arm is not well defined.
4. **Keep causal opportunity and practical cost comparisons separate.** A common
   number of continuation calls addresses the effect of the specified instruction.
   A frozen total-budget comparison additionally charges feedback, tests, tools,
   selector and retries, including prompt and completion tokens. Compare against
   the best fixed arm chosen on development data and restart/resampling with a
   public-only selector. The hidden best branch is an unattainable diagnostic,
   not that comparator. Record shared-prefix cost once for collection, but charge
   it to each hypothetical deployed policy when comparing its total cost.
5. **Use the submitted answer as the endpoint.** Average the two final-artifact
   grades per arm; do not choose the better hidden-graded draw. A deployable
   between-draw selector is a separately specified policy with its own costs.
   Do not preserve prior correctness
   using hidden grades. Report unconditional paired quality first, then repair,
   damage, diagnostic confusion, missingness and cost. Private initial correctness
   may define an offline descriptive stratum. It cannot be a policy input. A
   public verifier may support stopping only under the declared deployment law.
6. **Keep roots, families and seeds distinct.** All translations, paraphrases,
   descendants and branches of a root stay together. Random seeds create fresh
   draws, not proof of new task families. State whether the target is a fixed
   benchmark roster, a task-generation law, or new families. Use untouched roots
   for policy evaluation and a separate family-shift test where feasible; do not
   imply the former proves the latter.
7. **Do not oversell a small development trial.** The extension ceiling is at most
   12 development roots × (1 initial + 5 arms × 2 draws) = **132 receiver calls**,
   **512 output tokens/call**, **67,584 reserved output tokens**, **20 minutes**,
   **one local worker**, **$0 external spend**. Input tokens and context fit must
   also be measured and frozen. There are no model-generated critiques in this
   ceiling. Unused capacity is not permission for extra arms, retries or backfill.
   The original seven-root protocol remains at its own 49-call ceiling. These
   are alternative scoped development plans, not additive authorization.

The primary comparison in the later independent trial is a frozen public-history
policy versus the development-selected best fixed strategy under the declared
budget. Prespecify one primary contrast, an application-justified useful gain,
uncertainty procedure, precision/futility rules and maximum sample/cost. Evaluate
candidate procedures on known-truth data **before** real test outcomes. The prior
Hoeffding calculation is a conservative procedure-specific bound; it is neither
a minimum required sample size nor a reason to switch intervals after seeing data.
No confirmatory sample size is claimed from the present seven roots.

## Reuse decisions and release blockers

| Official codebase | Reuse now or next | What must not be inherited blindly |
|---|---|---|
| [offline-prompts](https://github.com/aiueola/offline-prompts) | Synthetic output-mediated reward architecture and regression/IS/DR/POTEC comparison specification | Current release/title/configuration differs from the inspected arXiv v1. Re-derive the exact chosen DGP and integrate over receiver output for action values. |
| [CausalCollab / dtr-text](https://github.com/XMUBQ/dtr-text) | Inspect longitudinal representation and robustness design as a reference | No LICENSE was found at the inspected revision; do not vendor its code without clarifying permission. Conversation-level folds do not establish user/topic independence. |
| [EvalPlus](https://github.com/evalplus/evalplus) | Task/test provenance and a separately isolated, explicitly versioned code-evaluation adapter | `reliability_guard` is not a security sandbox. Expanded tests do not resolve our task specification or public/private boundary automatically. |
| [Multi-IF](https://github.com/facebookresearch/Multi-IF) | Candidate multi-turn constraint benchmark and selected strict deterministic checkers | Check code and dataset licenses separately; keep language variants together. Some checker exceptions can return success and the runner can skip invalid rows. The full scorer is not certified here. |
| [Reasoning Gym](https://github.com/open-thought/reasoning-gym) | Candidate bounded graph-coloring generator and declarative JSON verifier for a separate controlled extension | Validate exact keys/types/output size; upstream nonzero partial credit is not binary success. Bound generation retries and declare the greedy-success-conditioned task law. Avoid the whole package's eager imports. |
| [MINT](https://github.com/xingyaoww/mint-bench) | Feedback provenance and separate feedback/receiver usage fields | Oracle binary feedback, code execution, difficulty curation and external-service defaults change the experiment. |
| [Lost in Conversation](https://github.com/microsoft/lost_in_conversation) | FULL/concatenated/sharded/recap/snowball control definitions and trace schema | Ground-truth stopping, model-mediated answer extraction and different reasoning-token caps are not our fixed-prefix contract. |
| [C3](https://github.com/EIT-EAST-Lab/C3) | Snapshot fingerprints and evaluator-call accounting concepts | The inspected ledger suppresses write errors, unsuitable for mandatory accounting. Paper and current code differ: 512 generation tokens/evaluation every 5% versus 2,048/every 10% in the inspected protocol. Do not call the latest code the reproduced paper. |
| [Self-Refine](https://github.com/madaan/self-refine), [Reflexion](https://github.com/noahshinn/reflexion), [CRITIC](https://github.com/microsoft/ProphetNet/tree/master/CRITIC) | Specific/generic/no-feedback, observation-only and sampling baseline templates | Do not import their executors, hidden-grade selectors, skipped-failure handling or API defaults into our trial. |

**Benchmark decision:** retain the coding study; prepare Multi-IF as a separately
declared instruction-constraint application and graph coloring only as a controlled
measurement/feedback test. Neither replaces the seven roots or establishes semantic
answer quality on unconstrained tasks. A complete public graph verifier is a
different information regime from sparse coding tests, and a conventional graph
algorithm is a strong task baseline. Success there alone would not justify a
practical LLM use case. Multi-IF constraint satisfaction also is not a complete
measure of semantic usefulness. Selection of either extension precedes outcomes.

The immediate reusable deliverable is a pinned, hashed **source inventory and
[adaptation specification](opensource_adoption_20260921.md)**. No upstream runner has been installed, executed, or
claimed integrated. Before implementation, retain required license/attribution
files and verify data terms; before model collection, freeze exact task IDs,
checkers and negative controls, renderer, receiver/server/decoding versions, splits,
assignment/order, source hashes and resource ceiling. Existing sandbox and
reference/control failures remain blocking for code execution.

One source-level check illustrates why analytic truth must be independent of a
library field. In the inspected `offline-prompts` revision,
`TrigonometricAuxiliaryOutputGenerator._sample_auxiliary_output` forms a value `output`,
draws a normal variate with mean `output`, and returns their sum. Its conditional
mean is therefore twice that value. Separately, `synthetic.py` computes
`expected_reward` conditional on the sampled auxiliary output. The coordinator
independently checked both source passages. These are properties of that pinned
implementation, **not a verified error in a published result**; versions differ.
Our future action-value truth must average over the output law. See the
[simulation design amendment](literature_simulation_plan_20260921.md).

## Resources and next handoff

No API key is needed for this source review or the next offline contract checks.
The likely execution need is access to an existing competent open-weight receiver
and, for coding, a working isolated Linux/container evaluator. First inventory
existing capacity and coordinate with active jobs. Do not buy cloud compute,
download large weights or use a paid service on the basis of this document. If
local capacity is inadequate, return a specific provider/model, request count,
token cap and priced maximum for the owner's decision; credentials should be set
through the provider's normal secret configuration, not pasted into GitHub.

Issues #2–#5 retain their order: matched fitted-estimator checks; valid same-prefix
prompt data; frozen critic/policy evaluation; only then larger generator work.
This review narrows the next experiment rather than claiming another efficacy
result. Research completion remains **49%, Δ=0 percentage points** under the fixed
rubric; the full project is not submission-ready.
