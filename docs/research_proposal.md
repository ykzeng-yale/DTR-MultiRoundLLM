# Causal value models for adaptive prompting

## Scientific question

For a new task and a fixed receiver model, which next prompt or feedback intervention improves the final task outcome, given the conversation so far and a specified future interaction policy? Can a model learn these conditional values, use them to rank newly generated prompts, and eventually serve as an autonomous adaptive user?

The initial request defines the task. An initial receiver answer is observed before the first feedback decision. Prompt rewriting before the initial answer is a separate, optional decision at time zero. Neither formulation identifies the effect of the task's semantic content merely by comparing unrelated requests.

The proposed system has four components: a history encoder; a prompt generator that proposes exact natural-language interventions; a continuation-specific causal value model; and a selector that decides among candidates and STOP. The receiver weights, tools, system instruction, decoding, and context rules are frozen within a study. The first paper focuses on prompt-only feedback. Tool availability, model switching, and external information provision change the intervention and are extensions.

## What a personalized prediction means

For history $h$, generated slate $c$, candidate $j$, and continuation policy $\pi$, the model estimates $Q_t^\pi(h,c,j)$, the expected final utility if that candidate is selected now and $\pi$ governs later choices. Contrasts between two candidates give a history-conditional causal effect. The prediction averages over future receiver randomness and relevant unobserved variation; it is not the realized counterfactual effect for one person or one exact trajectory.

Three outputs should be displayed separately:

| Output | Meaning | Validation |
|---|---|---|
| Predicted final quality under candidate $j$ | A conditional expected outcome with a named continuation policy | Fresh branch outcomes, calibration, prediction error |
| Difference from a reference candidate or STOP | Expected improvement for comparable supported histories | Randomized contrasts; repeated branches estimate conditional means |
| Estimated policy value | Average utility of the complete adaptive strategy in a target task population | Independent prospective trial and task-cluster uncertainty |

For an unseen history the prediction is a generalization claim. For an unsupported prompt it is extrapolation. An uncertainty estimate for average policy value does not supply a valid interval for every prompt in every history. The first system reports support flags and calibration bins, with explicit abstention when support is poor; it does not attach unproved pointwise causal confidence intervals.

## Contribution and its boundary

The contribution under development is a **design and estimation framework for sequential language-valued interventions**: generate a slate, randomize the actual intervention, retain the complete assignment mechanism, estimate continuation-specific values, and evaluate an adaptive prompting policy prospectively. The slate design allows free-form text candidates without pretending that every possible string has usable observational support. It also makes clear when changing the generator changes the target distribution.

DTR identification, g-computation, longitudinal doubly robust estimation, actor–critic optimization, and automatic iterative feedback are established foundations. Correctly specified sequential outcome regression can identify these targets under the same causal assumptions; a conventional critic is not automatically noncausal. Orthogonal or doubly robust learning protects against specified nuisance errors, not unmeasured confounding, omitted history, arbitrary model shift, or an unsupported action space. The literature audit records which closely related methods already exist.

The intended methodological claims are (i) an explicit language-action estimand and experimentally identifiable design; (ii) proofs connecting selection-only versus joint generator/selection policy evaluation; (iii) error decompositions separating candidate availability from ranking and continuation error; and (iv) a calibrated empirical comparison of value learning and autonomous feedback. The current package does not establish that this combination is unprecedented, that a new neural architecture is statistically optimal, or that it improves real LLM outcomes.

## From evaluation to a trainable dynamic skill

1. Collect randomized multi-round interaction data from frozen candidate generators, preserving histories, all candidates, selection probabilities, STOP, and objective outcomes.
2. Train a history–prompt critic using backward fitted evaluation and conditional orthogonal pseudo-outcomes. Name the continuation policy in every checkpoint. Use task-level cross-fitting and a final held-out evaluation set.
3. Rank generated candidates by estimated net downstream utility; apply a support screen and a separately calibrated improvement threshold over a reference policy.
4. Train a prompt generator from high-value candidates or a score-function objective on a frozen critic. This is a proposal mechanism; it can exploit critic error and needs fresh randomized data after updates.
5. Freeze the generator and selector, then compare full adaptive trajectories against cost-matched baselines on new tasks. Iterate training only between declared collection batches.

An initial implementation can use a frozen text encoder and small critic head. A sequence model and generator fine-tuning are subsequent implementations of the same contract. A learned world model is optional and is not substituted for external validation. The dynamic skill is the versioned mapping from history to intervention, with stopping and cost accounting, rather than a fixed sequence of textual instructions.

## Outcomes and application choice

The primary scientific outcome is independently verifiable final task success. Secondary outcomes are terminal quality on a fixed rubric, regressions from correct to incorrect, total receiver/generator/critic tokens, wall-clock time, and intervention count. Report the quality–cost frontier; a scalar utility is useful for policy training only after a cost conversion is declared. Added information and oracle error labels form separate, explicitly privileged treatment arms.

The first real application should be a competent open-weight model on verifiable reasoning or constrained structured-output tasks, followed by isolated code-repair tasks if a secure runner is available. Synthetic arithmetic is a harness check, not the substantive application. The experimental protocol requires a pilot to avoid both floor and ceiling performance before freezing a benchmark.

## Relation to the earlier projects

The earlier routing project intervenes on the agent's internal model/tool choice. This project intervenes on what the user or virtual user says next while the receiver is fixed. Prioritized multivariate outcome comparisons can be added later, but their pairwise sampling and estimand require their own analysis. The first version preserves correctness and cost as separate endpoints and does not import a win-ratio estimator without a derivation.

## Evidence required for a paper

The proof document and reference simulations support mathematical and implementation checks. A credible empirical paper also needs fitted-critic validation, repeated-prefix branch calibration, a generator-update experiment, and an independent cost-matched policy trial. Until those exist, this is a theory and experiment development package, not a submission-ready empirical manuscript.
