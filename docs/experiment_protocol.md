# Experiment protocol v0.1

> **Current prioritization:** the [scientific self-audit](scientific_judgment_20260920.md) narrows the next experiment to a frozen landmark prompt-choice test with fixed continuation and a competent same-target baseline. The broader S0–S5 plan below is a development roadmap, not authorization to advance without demonstrating useful, predictable prompt differences. The five-point power example is not a retrospectively binding advancement threshold. No fresh confirmatory protocol is frozen merely by this prioritization note.

Status: prespecified development plan; confirmatory claims remain pending. The default budget is **$0 paid API spend**. Local runs require an explicit call/time cap. Hardware-intensive training belongs to a separately budgeted issue. The root task/family, not each branch or turn, is the independent sampling unit.

The concrete next study is now the [landmark prompt-choice protocol](landmark_experiment_protocol.md), supported by [landmark theory](landmark_prompt_theory.md) and the [personalization premise simulation](landmark_premise_results_20260920.md). It is not yet a frozen real-model trial. A zero marginal arm effect is not a personalization futility gate; evaluate a frozen public-history selector on independent roots instead of selecting the best observed branch.

## Questions, estimands, and decision criteria

| Study | Question | Primary target | Criterion / interpretation |
|---|---|---|---|
| S0 mathematical unit checks | Do weights, continuation, STOP, and robustness agree with exact truth? | Fixed-policy value in a finite DGP | Exact identities pass within numerical tolerance |
| S1 simulation | What protects inference from nuisance error, and when does overlap fail? | Bias/RMSE/coverage of value and contrasts | Report Monte Carlo uncertainty and failures; no selected best scenario |
| S2 fitted history–prompt critic | Can a learned critic rank interventions and calibrate conditional means? | Branch-specific mean value and prespecified subgroup effects | Out-of-task error/calibration/ranking versus strong sequential-regression baseline |
| S3 randomized LLM feedback | Do supported feedback choices have heterogeneous downstream effects? | Fixed-generator policy value and history-conditional contrasts | Prospectively collected known assignment; no hidden-answer inputs |
| S4 autonomous prompting | Does causal-critic selection improve quality or cost? | New-task policy value difference | Independent locked test; equal total inference budget; confidence interval |
| S5 generator updates | Does training the prompt generator add value beyond candidate ranking? | Value of each frozen joint generator/selector | Fresh randomization for each generator version; isolate generator and selector changes |

### S0–S1: known-truth simulation

Use a finite horizon with baseline task difficulty, evolving answer quality affected by prior prompts, history-dependent feedback assignment, and absorbing STOP. Exact enumeration/dynamic programming provides truth. The implemented reference suite documents its configuration and distinguishes oracle/fixed-nuisance experiments from fitted nuisance estimation.

Required full grid for the next agent: horizon 1/3/6; sample size 250/1,000/4,000 independent tasks; strong/weak overlap; observed versus deliberately omitted difficulty; equal and unequal branch counts; both nuisance models correct, only propensity correct, only all continuation-Q functions correct, and both wrong. Add history compression aliasing, changed candidate generator, hidden confounding, informative missingness, and generator overoptimization as failure studies. A failure setting is not an estimator defect when its identification assumptions were intentionally violated.

Compare unadjusted action groups, correctly specified sequential regression, misspecified sequential regression, ordinary IPW, longitudinal DR, clipped-weight sensitivity, and an oracle. Log bias, RMSE, empirical standard deviation, mean estimated standard error, 95% coverage, interval length, ESS by stage, maximum cumulative weight, zero-support rate, and stopping distribution. For 1,000 Monte Carlo replicates, nominal-coverage Monte Carlo SE is approximately 0.0069. Development runs may use fewer replicates, with their actual Monte Carlo uncertainty shown.

### S2: fitted conditional value learning

Split root task families into 60% training, 20% development, and 20% final test; use a deterministic hash of family ID and a recorded seed. Cross-fit nuisances within training at the same root unit. Hyperparameters, prompt generators, stopping thresholds, and utility conversions use training/development only. Encode only information available before selection. Every critic checkpoint names its continuation policy and generator.

Fit at least (a) a history-aware sequential outcome regression, (b) a longitudinal DR pseudo-outcome critic, and (c) a history-ablated associational critic. The third baseline diagnoses confounding but cannot be the only comparator. Use the same encoder, capacity, training data, and optimization budget for (a) and (b). Additional DRQ/DeepBlip adaptations must respect each method's assumptions and compare using its actual published objective, not an arbitrary reimplementation with the name attached.

Report value mean-squared error, calibration slope/intercept and bins, candidate ranking regret, pairwise sign accuracy only for non-negligible true contrasts, and downstream policy value. Evaluate pointwise error only where repeated branches provide a usable conditional-mean reference; bootstrap entire root tasks when aggregating. Branch mean noise must be included in error analysis or reduced with independent replicate groups. Literal individual effects are unavailable even with repeated independent model seeds.

### S3: randomized multi-round LLM interactions

Freeze a receiver by content digest and a manifest containing tokenizer, template, system message, quantization, temperature, sampling parameters, context limit and truncation rules, tool access, and service version. Freeze generator and evaluator separately. Use three feedback decisions after an initial answer, with a maximum context budget and explicit STOP.

Start with a slate of STOP, generic retry, verification, and a generated task-specific feedback prompt. These are experimental candidates, not a claim that language has four treatment classes. Later slates may contain four distinct generated texts plus STOP. The generator sees the current public conversation and public tests/constraints only. The primary information-parity comparison excludes hidden solutions, hidden test failures, and post-selection outputs. A separate oracle-feedback arm measures a different intervention and must be labeled.

For a four-candidate development slate, assign $b(j\mid h,c)=0.25$ initially. An observed-history adaptive logger can initially use $0.8/K+0.2\,\mathrm{softmax}(s(h,c))$, giving a .20 floor with four candidates. A separately declared stronger-imbalance stress arm may use $0.2/K+0.8\,\mathrm{softmax}(s(h,c))$, whose floor is .05 at K=4. Publish the score function and full vector, not only the selected probability. Changes to the logger within a run require batch index in history and a suitable design analysis; the main study freezes it per batch.

A feasibility batch of 60 root tasks, one trajectory each, uses at most 7 model calls per task with one generator call and one receiver call per feedback decision plus one initial receiver call: 420 calls before STOP savings. Set a 60-minute cap and 1,024 new tokens per call. This batch chooses a competent benchmark and measures runtime/variance; it is not a test of superiority. A repeated-prefix calibration study starts with 80 held-out prefixes × 4 candidates × 4 independent continuations = 1,280 branches. At a maximum of 3 remaining rounds, budget up to 8,240 receiver/generator calls (1,280 × 6 continuation calls plus 80 × 7 prefix calls), then replace this estimate with an exact plan before launching. Keep all branches of each root together.

The supplied `experiments/collect_ollama.py` is a bounded **collector smoke-test harness** for fixed slates of STOP/retry/verification/decomposition. It records exact requests, outputs, hashes, probabilities, token counts, failures, and a dry-run mode. It is not the trained generator, neural critic, or complete S3 study. Its arithmetic fixtures validate transport and parsing only. The handoff issue extends it with generator slates and benchmark adapters.

### S4: locked prospective evaluation

Choose at most two primary policy comparisons before opening test outcomes: causal-critic adaptive selection versus history-aware fitted-regression selection, and versus a strong iterative-feedback baseline. For every policy, include initial receiver, generator, critic, reranking, and extra answer-sampling costs. Report quality at fixed total token/call budgets and the full quality–cost frontier. Giving one method hidden verifier feedback or extra calls creates a separate arm.

Baselines: initial answer/STOP; fixed generic retry; fixed verification; Self-Refine-style adaptive feedback; uniform/random candidate selection; history-aware fitted Q; DR critic; and a generated-slate best-of-K selector. OPRO/GEPA/PromptAgent are useful additional baselines if adapted faithfully to the same train/test split and total compute. They optimize different objects in some original settings, so label adaptations and include an unmodified reference where feasible. Do not require every literature method for a minimal first result.

Use task-matched execution of all frozen policies on independently restored environments, with several receiver seeds if affordable. Analyze one prespecified average per task, then paired task/family contrasts. A family bootstrap or cluster influence-function interval may be appropriate with enough independent clusters. Task IDs sampled from one benchmark do not establish generalization to all users or all LLMs.

Power is based on the root-task contrast $D_i$. For two-sided alpha .05 and 80% power, a planning approximation is $n\approx(1.96+0.84)^2\sigma_D^2/\delta^2$. Estimate variance on the feasibility sample and lock the test sample size before final outcomes. For binary paired outcomes with discordance .30 and a target difference .05, $\sigma_D^2\approx .30-.05^2$ gives approximately 933 tasks, not 60 or 100. With two prespecified comparisons, use Holm or conservative planning with alpha .025 (approximately 1,131 tasks under the same illustration). These are planning examples, not observed power or guaranteed coverage. Use task-family design effects or a cluster-based simulation when tasks within families are dependent.

### S5: learned generative interventions

Train a generator on training histories using advantage-weighted text likelihood or a critic-guided score-function objective with a frozen critic and a reference-policy penalty. Clip/normalize training weights and tune on development data. Evaluate generator-only updates with a fixed selector and selector-only updates with a fixed generator, plus their combination. A generator can merely learn to exploit critic errors; report critic-predicted improvement against fresh-execution improvement and track diversity and unsupported-candidate rates.

Each new generator has a new version and collection batch. Candidate-selection propensities from the old generator do not evaluate its new language distribution. If a tractable joint slate-density ratio is unavailable, collect new randomized trajectories or use a prospective policy trial. A KL penalty does not create empirical support or guarantee causal calibration.

## Stopping, failures, missingness, and transport

STOP preserves the current answer and incurs no later generation costs. Timeouts/service failures consume realized cost and yield a prespecified observable failure outcome for the deployment endpoint. A missing outcome is not converted to STOP. Record the reason, retain the assigned trajectory, and either use a justified missingness analysis or report worst/best bounds. Report both application robustness and quality conditional on successful service only if the latter is explicitly a secondary selected-population endpoint.

Separate receiver shift, task-distribution shift, evaluator shift, and generator shift. Reuse of a critic under a different receiver is a transport experiment requiring recalibration and fresh checks. Human logs add unmeasured intent, expertise, and external-information confounding; observational analyses must state these assumptions and include a sensitivity study rather than claiming that text encoders solve them.

## Required release bundle

Return source revision; frozen manifests; dataset sources/licenses/splits; raw immutable JSONL or an access statement; checksums; deterministic collection and analysis commands; branch lineage; failures; total compute; estimator diagnostics; all prespecified endpoints; and a claims ledger. Record independent reviewer findings before promoting a development result to validated evidence.
