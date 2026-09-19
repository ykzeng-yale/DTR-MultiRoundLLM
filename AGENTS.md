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
* Positivity is the crux here: the action space is natural language, so
  point-treatment positivity fails. Any identification claim must say how it
  avoids that, not assume it away.
* Distinguish, in every document: synthetic simulation, pilot, confirmatory
  result, and planned-but-not-run. A proposed extension is not an experiment.
* Report null and negative results plainly. "H1 not supported" is a result.

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
