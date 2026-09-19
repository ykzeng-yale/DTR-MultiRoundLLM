# Project status and claims ledger

Updated 2026-09-19. This is an initial theory and experimental-development release.

## Delivered and checked

- Full theory with eight numbered results/propositions and explicit proofs, plus conditional-label, support, generator-shift, stopping, representation, policy-improvement, and clustered-inference boundaries.
- Literature audit and a 38-entry bibliography. The audit corrects overly broad novelty claims in the supplied discussion and labels venue/access limits.
- Critic/generator training specification; randomized feedback and locked evaluation protocols; logging contract; bounded local collector; four experimental work packages.
- **30 passing tests** from `uv run --extra dev pytest -q` after integration. Tests cover exact DR/IPW identities, target-policy numerators, continuation labels, support, STOP, task clustering, and collector failure/leakage behavior.
- **400 synthetic replications**, each 800 independent root tasks and 2 continuations per task, horizon 3. All numerical/configuration/report files reproduced byte-for-byte in an independent invocation; timestamps/runtime were excluded from that equality check. See [reproduction evidence](../results/reproduction_check.json).
- A separate random-slate exact-enumeration check covers same and changed generators, both-correct and singly/mixed-correct nuisance configurations, and both-wrong product bias. Eight cases passed with maximum identity discrepancy `2.5e-16`; see [machine-readable check](../results/random_slate_remainder.json).
- A dry-run collector smoke test completed four synthetic fixture tasks and 14 mocked requests. It made **zero actual model calls**. Its zero token counts are mocked transport values, not measurements of receiver efficiency.
- A separate internal review found and verified repairs to the coverage theorem's support set, candidate-specific positivity, the coverage proof's parameter range, and the training reward convention. See [review](independent_review.md). This is not external peer review or machine-checked formal verification.

The local test runner explicitly imports `src/` through pytest configuration. This avoids a host-specific Python 3.14 issue where hidden editable-install `.pth` files were skipped. It is an environment/import fix; no statistical result depends on it.

## What the synthetic study establishes

The exact adaptive-policy utility is 0.798750 in the specified finite process. DR empirical 95% coverage is 0.950 when both nuisances are correct, 0.9525 with only propensity correct, and 0.950 with only Q correct (coverage Monte Carlo SE about 0.011). Exact expectation calculations establish the corresponding zero-bias identities. Both-wrong exact bias is +0.631259. The deliberately confounded stage-2 observed correction-minus-retry contrast is -0.2683, while the standardized causal immediate-quality contrast is +0.1680.

These are known-truth, fixed-nuisance statistical diagnostics. They do not measure learned nuisance performance, neural calibration, natural-language treatment effects, or real receiver improvement. Correct oracle Q regression is a strong benchmark here and is not disadvantaged to favor DR.

## Still pending

| Claim / implementation | Current evidence | Required next evidence |
|---|---|---|
| Trained history–prompt critic | Training specification and finite-state label identities | Task-cross-fitted fitted models; held-out conditional calibration |
| Generated free-form treatment slates | Identification theory; fixed-slate collector | Actual generator adapter; frozen versions; randomized collected trajectories |
| Better autonomous prompting | No real-model outcome evidence | Cost/information-matched locked prospective trial |
| Improved learned generator | Proposed objectives only | Generator-only and selector-only ablations with fresh data |
| Individualized valid confidence intervals | Conditions and limits stated | An actual conditional inference method and coverage study |
| Universal prompt optimality or novel foundational DTR theory | Not claimed | Different assumptions/results; unsupported by this package |

## GitHub coordination

The experiments workstream seeded main and committed a task-pool audit while the theory package was being developed. Those files are preserved. The theory package is integrated on `theory/causal-prompt-package`, with direct answers to Q1–Q10 appended to `COORDINATION.md`. Its generated-slate probability design awaits experimental-agent acknowledgement before a freeze. PR/issue links are recorded when posted; publication alone is not acknowledgement or execution. No recurring monitor is configured by this release.

## Usage ledger (this theory/reference workstream only)

Actual paid API spend: **$0**. Actual LLM inference calls: **0**. Training GPU hours: **0**. Synthetic reference runs used local CPU. Literature retrieval and repository communication are separate from model-evaluation usage. No cloud purchase or unbounded run was launched.
