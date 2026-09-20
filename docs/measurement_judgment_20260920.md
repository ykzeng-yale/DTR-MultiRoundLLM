# Measurement judgment: what the coding outcomes actually establish

Independent internal review by Codex subagent `/root/evidence`, 2026-09-20. This review inspects the project's protocol/scorer, the sibling routing protocol/scorer, the frozen visible-test artifact, and all 4,488 existing randomized-log episodes. It performs arithmetic and static text/AST inspection only. **No candidate program, reference program, new probe, model call, or regrading was executed.** Machine-readable counts, definitions, and source hashes are in `results/measurement_judgment_20260920.json`.

**Judgment:** recorded success is a narrow, useful benchmark endpoint. It is not gold semantic correctness, a newly hidden-only grade, or evidence that individualized prompt effects have been identified. The original research design did not adequately separate those claims. In addition, a large share of the observed stopping discrepancies occurs on tasks with an empty validation instrument: 90 of the 561 logged tasks have no substantive visible checks. These findings require corrections to the scientific interpretation, not just additional performance tuning.

## 1. Endpoint reconstruction and provenance

The reconstructed canonical task file at sibling `work/restoration_reconstruction_13bad73/tasks.json` has SHA-256 `23727895971fa4a040198d8770173a4f0c3263a63a9cb1479abc4203bb01c2ce`, matching every episode's frozen task hash. Reconstructing the initial request from the inspected source functions and this file reproduces **all 4,488 initial transcript hashes**. The visible-test artifact hash also matches every episode. All logged check counts agree with that artifact. There are 561 roots, eight episodes per root, four initially assigned to each receiver; no mock or infrastructure-error episode appears in this completed file.

The frozen design reserves 30 of the 591 canonical tasks for a separate pilot; its 231 training plus 330 confirmatory task IDs define these 561 logged roots. This audit combines the latter two sets as already-inspected development data and does not relabel them a fresh holdout.

The operative definitions come from sibling `experiments/code_routing/agent.py` (`validate`, `verify_hidden`, `run_episode`) and `experiments/common/verify.py` (`build_program`, `verify`):

| Quantity | What the existing log measures |
|---|---|
| `validation.passed` | Candidate/harness loads and all frozen generated visible checks pass. With zero checks, successful loading suffices. |
| `success_first_candidate` | Whether the first answer passes the **entire original benchmark verifier**. If the episode stops after one decision, this is copied from final success. Otherwise the first answer is reverified after the episode; only its scalar success is retained. |
| `success` | Whether the final submitted code passes that original verifier under sandbox limits and produces the nonce sentinel appended after the tests. |
| `utility` | Final success minus the source's assigned call penalties, 0.01/0.03 for small/large. These are unitless choices, not token prices or money. |

The verifier executes all MBPP `test_list` assertions plus any challenge tests, or the full HumanEval `check` function. A sentinel rejects some early-exit tricks. Static hack flags are diagnostic and do not determine the source label. The label combines test behavior with execution/harness conditions; it does not prove functional correctness for all inputs, specification compliance, or resistance to unenumerated exploits.

The randomized treatment in this source is **receiver identity**, with a fixed repair prompt and fixed tool/stopping kernel. Final results grouped by initial receiver include later randomized switches. They are not estimates of the effect of alternative prompt wording.

## 2. The visible and graded information sets differ across projects

The sibling asks the 7B model to generate checks, removes vacuous checks and syntactically matching benchmark-test inputs, and retains checks passed by the reference implementation. Across the original 591-task artifact, 2,977 written checks became 1,627 certified checks: 38 were removed as vacuous, 514 for detected benchmark-input overlap, and 798 after reference failure. These figures describe the constructed tool, not model-independent proof that its remaining checks characterize correctness.

Reproducing the inspected AST argument-key rule finds **zero remaining detected overlaps** between certified visible checks and original benchmark-test calls. This is evidence that the specified filter was applied. It cannot establish semantic disjointness: aliases, variable expressions, equivalent inputs, shared prompt examples, and benchmark familiarity are outside that comparison.

Crucially, the source's MBPP initial prompt uses the task description and a reference-derived function signature. **None of the 427 initial MBPP prompts contains `test_list[0]` verbatim.** The existence of a `signature_example` field equal to that assertion does not mean this particular source prompt exposed it. Our later `verify.split_tests` and `scoring.split_assertions` designate that first assertion as visible for a different proposed environment. Our source-cohort discussion must not conflate the two.

For HumanEval, the original source prompt retains the benchmark docstring/examples. Our later splitting heuristic flags 193 benchmark assertions across 76 of 164 tasks as having inputs reflected in the prompt. These are **heuristic flags**, not an independently verified census of semantically revealed answers. That later splitter also exposes a formerly graded assertion as a new visible check and changes the graded set. Existing stored full-test outcomes were not regraded after these changes.

Reference certification is acceptable for constructing a benchmark tool if disclosed and held fixed across arms. It is additional information/infrastructure that an ordinary user may not have. It does not justify claiming a deployment-ready verifier built without privileged reference access. Likewise, adding known tests is a legitimate information intervention; the earlier prose that it is “not an intervention” or guarantees improvement “by construction” is too strong. The relevant concern is whether the target is success on exposed examples or generalization to a separate evaluation set.

## 3. Initial visible-versus-recorded-success confusion

`V` denotes the source visible-check result and `Y` the recorded full-test result. The table reports exact counts. Percentages are conditional disagreement rates, **not** sensitivity or specificity against gold semantic truth.

| Initial receiver / benchmark | Episodes | V+ Y+ | V+ Y− | V− Y+ | V− Y− | Y− among V+ | Y+ among V− |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 3B / MBPP | 1,628 | 907 | 352 | 52 | 317 | 27.96% | 14.09% |
| 3B / HumanEval | 616 | 383 | 87 | 5 | 141 | 18.51% | 3.42% |
| 3B / combined | 2,244 | 1,290 | 439 | 57 | 458 | 25.39% | 11.07% |
| 7B / MBPP | 1,628 | 1,044 | 292 | 49 | 243 | 21.86% | 16.78% |
| 7B / HumanEval | 616 | 492 | 50 | 5 | 69 | 9.23% | 6.76% |
| 7B / combined | 2,244 | 1,536 | 342 | 54 | 312 | 18.21% | 14.75% |
| All | 4,488 | 2,826 | 781 | 111 | 770 | 21.65% | 12.60% |

For each row, equal numbers of initial candidates per root mean that episode-weighted joint proportions and equally task-weighted joint proportions are identical. The JSON supplies both calculations, including benchmark-only rows. It also supplies terminal confusion by benchmark and initial receiver, and a supplementary last-receiver grouping explicitly labeled as a post-assignment descriptive grouping with potentially unequal root weights.

At the terminal answer, the overall matrix is `(V+Y+, V+Y−, V−Y+, V−Y−) = (3063, 839, 40, 546)`. Thus final visible pass is 86.94%, recorded success is 69.14%, and 21.50% of terminal visible passes fail the original full tests. This remains an assay disagreement, not proof of which assay is semantically correct on every discordant case.

## 4. Most initial false reassurance occurs on zero-check tasks

| Universe | Zero-check MBPP roots | Zero-check HumanEval roots | Total |
|---|---:|---:|---:|
| Original frozen 591-task artifact | 69 / 427 | 25 / 164 | 94 / 591 |
| Logged 561-task cohort | 66 / 407 | 24 / 154 | 90 / 561 |

The 90 logged roots generate 720 initial candidates. **714 pass the empty check and therefore stop immediately; 424 of these fail the recorded full tests.** The remaining six fail loading/harness validation and continue. Hence 424/781 = **54.29% of all initial visible-pass/full-test-fail cases occur with no substantive check at all**. The 424/781 allocation is descriptive; it does not estimate how many failures adding an informative checker would prevent. Conditional on empty-check pass, recorded failure is 59.38%; it is 234/357 = 65.55% for 3B and 190/357 = 53.22% for 7B.

This is a major design defect if a claim depends on having informative per-round evidence. It is an explicitly defined, but weak, stopping mechanism. Calling these observations failed “self-assessment” blurs the distinction between an LLM's introspective judgment, an externally generated test suite, and an empty load-only test. It also means the apparent opportunity for a selector can partly be an opportunity to repair the verifier. That is scientifically interesting, but a different mechanism from identifying which feedback wording causes improvement.

A zero-check state does not make a DTR undefined, and the absence of external evidence does not mathematically rule out beneficial prompting. The earlier categorical claim in `scoring.py` and `docs/audits.md` that self-correction literature “closes off” every such design is not warranted. A design can instead declare and test a no-substantive-check stratum, or exclude it **before** defining a new target population; it cannot drop these roots retrospectively while retaining the original population claim.

## 5. What can and cannot be regraded from saved artifacts

Saved logs contain initial/intermediate/final code, visible aggregate counts, failure traces, final sentinel/timeout indicators, and binary first/final full-test outcomes. The episode serializer deliberately omits visible `per_check` results. It stores no vector of benchmark assertion outcomes. First-candidate regrading after continuation retains only success, not separate timeout or sentinel details. Intermediate answers generally lack full-test outcomes.

The canonical tasks and code are now available with matching hashes, so a separately frozen, sandboxed regrading analysis is feasible. **It has not occurred in this audit.** Removing newly exposed assertions from an old scalar failure label cannot tell us whether the remaining assertions pass. Even the implication from full pass to subset pass requires unchanged deterministic harness semantics; the later HumanEval splitter changes statement placement and should be validated as an execution transformation. Reference-only checks and static prompt-substring heuristics do not fully validate candidate-level equivalence.

Accordingly, the corrected four-answer selection result remains a recorded **full-test** result. A later publicness convention or new grader-derived probes cannot retroactively turn it into hidden-only validation.

## 6. Original scientific judgments that need correction

These are errors in the project's own reasoning and oversight, not defects that can be assigned solely to the experimental worker.

1. **Endpoint validity was overstated.** Passing references and rejecting a trivial stub are useful harness checks, not validation of semantic correctness. The later mutation/hack audits themselves show this gap. `docs/audits.md` further claims that zero heuristic hack flags give an upward-bias upper bound of exactly zero. That implication is false: undetected exploits and ordinary inadequacy of the test set remain possible. Zero flags only establish zero *flagged* candidates.
2. **Our measurement rule was allowed to drift.** The initial MBPP split, later HumanEval assertion split, sibling generated-check environment, and reused full-test labels are different measurement systems. They should have had separate versioned endpoint names and eligibility rules before results were compared or pooled.
3. **The “effective sample is 230 tasks” interpretation is invalid as stated.** A pool selected using noisy observed success rates defines an outcome-selected population. Its size is not a universal effective sample size for power. Marginal power depends on task-level contrast variance and clustering; the same reused outcome data do not provide independent confirmations of the number 230.
4. **Observed continuation does not identify stopping headroom.** The 184 repairs and 18 losses among continued trajectories describe selected histories. The earlier +4.6-point “oracle headroom” calculation extrapolates an observed repair rate to stopped failures without identifying that counterfactual. It is a scenario under an assumption, not an empirically established upper bound. Episode-level Wilson intervals also do not account for repeated task roots.
5. **The practical target changed before the original one was tested.** Receiver routing and post-generation selection are useful adjacent studies. Neither supplies randomized contrasts among next-prompt texts. A positive selector result cannot stand in for a validated history–prompt causal critic, and a negative routing result cannot terminate all prompt-intervention research.

## 7. Consequence for the original prompt-quality estimand

The intended causal quantity can be stated narrowly as the change in the conditional probability that the final artifact passes a frozen, separately specified evaluator after choosing one supported feedback prompt rather than another, under a named continuation policy and fixed receiver. A prospective randomized prompt study could identify that benchmark estimand under the usual design assumptions. Measurement validity beyond that endpoint would remain a separate argument.

The current 4,488-episode source cannot answer that prompt contrast because prompt wording was not randomized and the receiver changed. It can characterize this routing environment, motivate hypotheses about validation and stopping, and support exploratory fixed-bank selection analyses under the recorded endpoint. Four candidates per task cannot reveal a single conversation's realized individual effect. Public coding tasks, one model pair, and reference-certified checks do not establish generalization to individual users' goals, writing quality, research assistance, or open-ended multi-round interaction.

Before a new confirmatory claim, the coordinating author must freeze the exact endpoint and permitted information, resolve empty-check handling, keep tool construction and candidate scoring versions distinct, and specify fresh task/family separation. Any hidden-only regrading must preserve the original labels and report changes rather than silently replacing them. These are repairs to the scientific design; more simulations or a larger run under the old ambiguity cannot substitute for them.

