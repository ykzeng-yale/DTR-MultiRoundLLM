# Measurement gate for the broad task-family target

Codex scientific lead, 30 September 2026. This resolves how measurement failures must be represented in a future broad equal-family study. It is a design decision, not an adopted task frame, run, policy fit, or efficacy result. The five-point usefulness rule and original broad target are unchanged.

## Decision: separate target definition, observation, and validity

The study must not collapse three different states into a single PASS/FAIL/INCOMPLETE label:

1. **Undefined target outcome.** Before treatment, the task contract does not determine what counts as a successful answer. There is no well-defined binary semantic outcome for that family under the current target. Calling this ordinary missingness is incorrect: a missingness interval cannot repair an undefined estimand. Resolve the contract prospectively under a uniform, source-blind rule, or report that this family cannot support the declared outcome. Do not infer a convenient contract from the reference implementation or observed policy outputs.
2. **Defined outcome, unavailable observation.** The task contract defines success, but the frozen observer fails, times out, or returns an unusable record. Keep the assigned family and policy rows in the target denominator. Record the reason and apply the prespecified pathwise outcome bounds; do not convert the event to FAIL, STOP, or a complete-case exclusion unless the deployment endpoint prospectively defines that exact event as failure.
3. **Observed grade with unresolved semantic error.** A test or adapter returns a grade, but its false-positive/false-negative mass for the target population is not justified. Report the grade as an implementation-specific `Z`, not semantic `Y`. To make a semantic claim, use independently justified simultaneous bounds on the unconditional policy-specific error masses and propagate them with `measurement_sensitivity_v1.py`. Handpicked references and wrong controls are useful falsification cases but do not bound those masses.

These distinctions follow the existing outcome contract, the source-separated observation decision, the paired missingness interval, and the measurement-error identity. They add no new identification theorem. Missingness bounds apply only when `Y` is defined; sensitivity correction applies only when a defensible `Y` and valid error-mass bounds exist.

## Required design for any future target-preserving collection

The population/frame and family grouping must be determined before treatment or outcome information. All sampled families stay in the denominator regardless of whether their observer is easy to run. Task-contract resolution and observer validation must be blind to policy assignments and outputs. An adapter may be task-specific, but its semantic comparison rule, version, trusted inputs, output schema, and failure mapping are frozen before the relevant outcomes.

For each assigned policy/family row, retain separate fields for: contract disposition; latent target definition/version; observed grade and observer version; observation availability/reason; any independently justified false-positive/false-negative bounds; public feedback actually exposed; and resource costs. Public status remains the frozen status-only alphabet. Private outcomes, validation labels, and future suffixes are never policy inputs. Costs remain separately reported rather than silently converted into quality utility.

If a defined `Y` is unavailable, use the already reviewed pathwise bounds on the full family contrast and preserve the assigned row. If `Y` is observed only through an imperfect `Z`, use the existing joint-mass sensitivity interval with simultaneous error coverage. If the contract leaves `Y` undefined, do not manufacture an interval or claim that missingness adjustment solved it. If an entire family has no usable semantic observation, its contrast remains in `[-1,1]`, which may make the five-point decision inconclusive; that is an honest design outcome, not grounds for replacement.

No candidate/reference/benchmark execution is released by this gate. The native observer v1–v3 failures remain terminal; this decision does not reopen that repair line, relax containment, or claim the JSON adapter covers arbitrary native objects.

## Current lead disposition

This gate makes the measurement decision explicit, but it does not supply the missing broad family-generating/sampling law, globally resolved family/exposure frame, independently validated task contracts, a released trusted observer for the intended task types, or eligible randomized development data. Therefore there is still no valid model/task experiment to submit. Compute is not the current blocker. Do not substitute MBPP, BigCodeBench, the historical 591-task pool, or another finite source for the broad target; do not fit the exposed nine-root pilot.

Next substantive acceptance criterion: produce a target-aligned family sampling mechanism and a prospective, outcome-blind route to resolve `Y` for its frame. Then freeze disjoint development/tuning/evaluation families and the complete logging, policy, comparator, cost, missingness, source/runtime, and resource protocol before any model calls. Readiness remains **60%, delta 0**; population/measurement admission, practical policy fit, independent evaluation, and manuscript/raw reproduction remain incomplete.
