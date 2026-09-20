# Rules for agents working in this repository

This repository studies **multi-round human–LLM interaction as a dynamic
treatment regime**: the user-side message at each turn is a time-varying
treatment, the conversation is the time-varying confounder, and task quality is
the outcome. Read `COORDINATION.md` first — it holds the ownership map and the
open questions between workstreams.

## Scientific discipline

* Do not present classical results (g-formula, sequential ignorability, IPW,
  MSM, SNMM/blip functions, Q- and A-learning, DR/Neyman-orthogonal estimation,
  SMART design) as novel. Cite them. State plainly which parts of a claim are
  new *in this setting*.
* Attach assumptions to every mathematical claim, and say which of them hold
  **by construction of a design** versus which are **assumed**.
* Positivity is the crux here: language actions can have absent or practically
  negligible support. Formal positive probability for a string does not ensure
  useful finite-sample overlap. Define the supported intervention explicitly.
* Distinguish, in every document: synthetic simulation, pilot, confirmatory
  result, and planned-but-not-run. A proposed extension is not an experiment.
* Report null and negative results plainly. "H1 not supported" is a result.

## Scientific ownership and advancement decisions

The coordinating scientific agent owns the research question, estimand, design,
measurement contract, comparator fairness and integrated judgment. Delegating
execution does not transfer that responsibility. Review negative findings as tests
of the scientific chain, not merely as implementation failures.

Before advancing, distinguish identification, estimability, conditional ranking,
policy improvement and total-cost benefit. A theorem or passing code check at one
link is not evidence for the later links. Preserve valid negative conclusions.
Treat changes in population, permitted information, bank size, generator, endpoint
or budget as new scientific targets unless they restore the declared original
contract. Do not select splits, benchmarks or thresholds to rescue a narrative.
The current governing judgment is `docs/scientific_judgment_20260920.md`.

## Experiment discipline

* **Pre-register.** Before any model call: freeze and commit the protocol, the
  config, the intervention taxonomy with exemplars, the seeded assignment table,
  the estimator code and the analysis script; record the freeze commit id; stamp
  every episode with the config hash.
* Never overwrite a completed run. New run directory, new manifest (seed,
  config hash, code hash, model digest, decoding parameters).
* Use the *actual* randomization or generator probabilities in any weight. An
  unsupported policy is not rescued by a fitted outcome model.
* Split and infer at the task/task-family level; keep branches and repeated
  seeds for the same task together.
* Pin model digests, server build, and decoding parameters. Record third-party
  licences.
* Do not execute model-written code outside the isolated sandbox
  (`experiments/common/sandbox.py` pattern from the sibling repo).
* **Audit the data, not only the code.** The sibling project found that
  model-written visible tests rejected correct references in 57% of tasks, and
  that some checks leaked hidden-test inputs and answers because a 7B model had
  memorised the benchmark. Run the analogous audits here before trusting a
  number.
* Keep tokens, latency, money and energy separate. Do not let a token count
  stand in for a dollar cost.

## Two threats specific to this project

1. **Information leakage in the treatment.** A feedback message can contain part
   of the answer. Then "more informative feedback works better" is trivially
   true and confounds the intervention with answer transfer. Every intervention
   class must have its information content bounded, measured and reported.
2. **Simulated users.** The intervener in any feasible design is an LLM or a
   script. Claims transfer to *automated interveners*, which is the deployment
   target; transfer to real humans must be argued, not assumed.

## Mechanics

* `git pull --rebase origin main` before every push. Never force-push.
* Commit as `ykzeng-yale <yukang.zeng@yale.edu>` (no global git identity is set;
  pass it with `git -c`).
* Raw third-party data and large artifacts stay in gitignored `work/`.
* Never commit credentials, private datasets, or personal messages. Inspect
  staged files before pushing.
* Add tests when changing estimators, randomization, task validation or
  inference. Run the documented suite plus a small deterministic simulation.
* After each run, append an attributed section to `docs/experiment_results.md`
  and reproducible next steps to `docs/experiment_handoff.md`.

## Progress reporting

Every user-facing progress summary and every scheduled repo update states the
estimated readiness of the **full project** for a paper submission, the change
since the previous checkpoint, and the largest remaining milestones —
distinguishing reported from independently validated results. A finished local
task is not full-project readiness.

## Theory-package integration rules (Codex, 2026-09-19)


This project studies **user-side prompt/feedback interventions** in repeated interaction with a fixed receiver LLM. Model routing is a separate project.

1. Read `README.md`, `docs/theory.md`, `docs/experiment_protocol.md`, and the assigned GitHub issue before editing. Claim the issue with a comment that states scope, branch, compute budget, and expected outputs. An unclaimed issue is a handoff, not evidence that another agent has started.
2. Preserve the initial scientific target, original task, receiver version, candidate-generator version, continuation policy, and measurement rules. Changes require a new manifest and a clearly labeled estimand.
3. Keep established results, newly proved propositions, numerical checks, synthetic simulations, feasibility pilots, prospective validation, and unsupported conjectures separate. Never fabricate readiness or results.
4. A literal individual treatment effect is not identified from one observed conversation. A supported history-conditional mean contrast is the primary personalization target.
5. Candidate generation precedes randomized selection. Log the whole slate and all selection probabilities. Selection propensities do not identify the value of an arbitrary changed generator. Semantic embeddings are not automatically causally sufficient.
6. STOP is an absorbing intervention; missing logs, service failures, and user dropout are separate events. Account for all assigned trajectories. Hidden final evaluation answers are never policy inputs.
7. Split training, tuning, and testing by root task/family. All branches of a root task remain together. Audit state restoration and independence before causal branch comparisons.
8. Use a branch and pull request for experiment implementation. Preserve immutable raw logs and checksums, pin code/config/model/data versions, and return scripts plus results, not only narrative. Do not overwrite baselines or force-push other agents' changes.
9. Run the relevant tests and budget checks. No paid API, cloud purchase, or unbounded GPU run is authorized by the supplied default protocol. The local reference budget is $0. Record actual calls, tokens, and runtime.
10. Report failed runs, overlap failures, missing outcomes, uncertainty limitations, and negative results. Do not choose a policy on its confirmatory test set.
