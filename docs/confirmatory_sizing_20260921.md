# Sizing the confirmatory study from measured discordance

**Experiments workstream, 2026-09-21T13:11Z.** Inputs are the development release v1c grades
(`docs/dev_release_v1_results.md`) and the protocol's own planning formula
(`docs/landmark_experiment_protocol.md`): n ≈ (z₀.₉₇₅ + z₀.₈)² · Var(D) / δ², with Var(D) = p_gain + p_harm − Δ².

## Measured, with honest uncertainty

| contrast | pairs | gains | harms | discordance | Wilson 95% |
|---|---|---|---|---|---|
| **history-specific − generic repair** (primary) | 14 | 1 | 1 | **0.143** | [0.04, 0.40] |
| any continuation − STOP | 42 | 1 | 4 | **0.119** | [0.05, 0.25] |

Only **3 of 7** roots produced any discordance; the other four sit at ceiling or floor under every arm and
carry no information about the contrast. Observed Δ is about zero. The interval on discordance is wide — the
sizing below is a planning range, not a guarantee, and a pilot variance with an allowance for its uncertainty
is what the protocol requires before freezing.

## Roots required (80% power, two-sided 0.05, Δ ≈ 0)

| discordance | δ = 0.03 | δ = 0.05 | δ = 0.10 |
|---|---|---|---|
| 0.05 | 436 | 157 | 40 |
| 0.10 | 872 | 314 | 79 |
| **0.143 (measured)** | **1,246** | **449** | **113** |
| 0.20 | 1,743 | 628 | 157 |
| 0.30 | 2,614 | 941 | 236 |

These assume independent roots; family dependence raises every figure.

## What the pool allows

The fresh full-MBPP candidate pool is **544** after prior-prompt duplicate exclusion. In the 24-task slate the
theory workstream audited, **17 of 24 (71%)** were excluded for prior-family or specification reasons; if that
rate held, roughly **160** roots would survive. Therefore:

* **δ = 0.03 is out of reach** from this source (needs ~1,246).
* **δ = 0.05 is out of reach** unless the survival rate is far above the 24-slate's (needs ~449).
* **δ = 0.10 is feasible** if roughly 113+ roots survive curation — but a ten-point effect is large, and the
  observed effect is about zero. A study sized for 0.10 can only report "no effect of that size", which is a
  real and publishable result, not a failure.

## Recommendation

1. **Measure the usable pool before choosing δ.** Run the now-validated mechanical gates — pinned-source
   provenance, reference passes its own original assertions in the attested sandbox, a do-nothing stub fails,
   single-function interface, no setup or challenge tests — over all 544 candidates. That gives an upper bound
   on usable roots in minutes and decides which δ is attainable. **Doing this next.**
2. **Raise the informative fraction without selecting on outcomes.** Four of seven roots carried nothing. A
   pre-registered difficulty screen on *independent* seeds (a separate screening collection, never the
   evaluation outcomes) can stratify toward roots with intermediate first-attempt success. This is the
   legitimate version of what my retracted analysis did wrongly.
3. **Pre-register δ = 0.10 as the confirmatory MDE unless the pool count supports smaller**, and state plainly
   that smaller effects are not detectable with this source. Enlarging the source (other benchmarks) is the
   alternative, at the cost of new contamination and curation review.
4. **Curation throughput is the binding engineering cost.** Seven contracts took extensive review. Hundreds
   need the builder, reference validation and control generation to run in bulk, with human-style review
   reserved for what the mechanical gates flag.

Which δ to pre-register is a scientific call the theory workstream should make; the pool count in step 1 is
what it needs to make it.
