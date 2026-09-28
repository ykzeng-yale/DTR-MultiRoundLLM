# Matched complete-strategy development results

Codex lead,28September2026. Both frozen stages completed: jobs27757218/27760747,102+101=203returned calls,51+40=91allocated GPU seconds,zero generation error/state drift. All162assigned branches retained,61stopped/101horizon; prior stopped states unchanged. Lead recomputed all1152raw private-case aggregates (51.681seconds); no independent review is claimed. No extra generation or endpoint changes.

| Strategy | PASS | FAIL | INCOMPLETE | Additional calls | Completion tokens | Difference vs resampling (pp) |
|---|---:|---:|---:|---:|---:|---:|
| STOP | 14 | 4 | 0 | 0 | 0 | [-11.11, -11.11] |
| PATCH2 | 14 | 4 | 0 | 36 | 2184 | [-11.11, -11.11] |
| RETHINK2 | 14 | 4 | 0 | 36 | 2470 | [-11.11, -11.11] |
| GATED_PATCH | 14 | 3 | 1 | 8 | 932 | [-11.11, -5.56] |
| GATED_RETHINK | 14 | 4 | 0 | 7 | 1120 | [-11.11, -11.11] |
| PUBLIC_SWITCH | 14 | 4 | 0 | 8 | 1207 | [-11.11, -11.11] |
| RESAMPLE_SELECT | 16 | 2 | 0 | 36 | 1859 | reference |
| SELF_REFINE_ADAPT | 12 | 3 | 3 | 36 | 4782 | [-22.22, -5.56] |
| REFLEXION_ADAPT | 16 | 1 | 1 | 36 | 4151 | [0.00, 5.56] |

All strategies have18starts on the same9reused roots; average over18 equals equal-root mean because each root has exactly2starts. Bounds are missing-outcome bounds, NOT confidence intervals. Repeats do not add independent roots. Initial logical deployment cost adds1806prompt/1092completion tokens and18initial generations to each strategy; these starts were physically reused. All continuation prompt tokens, times, public checks and per-root outcomes are in results/strategy_terminal_grading_20260928.json and results/strategy_terminal_reconciliation_20260928.json. Energy unmeasured, paid cost$0. No token→dollar conversion.

The fixed PATCH2/RETHINK2 and public gating do not improve the observed pass count over STOP. Resampling has16passes versus14for STOP but the panel cannot support population superiority. Reflexion adaptation has16passes and one missing, so its conservative difference from resampling is[0,5.56]pp; this is neither a statistically established gain nor grounds for selecting it. Self-Refine adaptation has a negative upper missingness bound versus resampling. Do not promote the apparent best arm, fit on these outcomes or repeat seeds to rescue ranking.

Missing observations are preserved under the frozen taxonomy: GATED_PATCH slot48 raised a modular-inverse exception; SELF_REFINE slots52/133 had entry-point/set-method runtime errors, SELF_REFINE slot61 emitted extra stdout and invalidated4supplement observations; REFLEXION slot53 had the same entry-point NameError. Candidate stdout can invalidate the strict observation channel even when process exit is zero; no retrospective parser repair or regrading is allowed. Original-private diagnostic outcomes remain separate in the saved row table.

Scientific next step: close this reused-panel comparison. Implement non-oracle full-history/STOP learning and qualify it under a predeclared synthetic law, while keeping real population/measurement and independent evaluation prerequisites open. A synthetic finite-cell learner is not a completed text controller or evidence for LLM efficacy. Prior checkpoint negatives remain valid.

Full-project readiness60%,delta0. Population/measurement, actual full-history learned policy and DR-training comparator, independent freeze/evaluation and manuscript/raw reproduction remain incomplete.
