# E13 proposal: prospective test of a frozen public-diagnostic-gated rule (NOT RELEASED)

**Experiments workstream.** The finding below is **post-hoc and in-sample**: the rule was chosen after
inspecting E12, so E12 cannot validate it. This document proposes the smallest prospective test and releases
nothing.

## Exploratory motivation from E12 (14 roots; rule chosen on the same data)

Mean private success per root, averaging the two replicates:

| policy | E12 value |
|---|---|
| STOP; always N0; always N1 | 0.714 |
| always S0; always S1; always R1 | 0.679 |
| gate: N0, N1 or S0 if the public diagnostic fails, else STOP | 0.714 |
| gate: S1 if public fails, else STOP | 0.679 |
| **gate: R1 if public fails, else STOP** | **0.750** |

- **Only the public-gated R1 rule exceeded STOP**, by +0.036: half-repairs on 842 and 288, and no loss on the
  9 public-pass roots, because the rule keeps them.
- It still loses on 863, the one root that failed publicly but passed privately.
- This is the kind of history-conditional rule the project targets: the action depends on an observed,
  decision-time public signal.
- **It is selected, in-sample and based on 3 roots**, so it is a hypothesis only.

## Proposed E13 (frozen before any new outcome)

- **Policy under test**, frozen as written above: *if the initial answer fails any public example (the same
  v2 public checker), issue the R1 prompt (task + diagnostic, previous answer removed); otherwise STOP.*
- **Comparators:**
  - STOP;
  - the development-selected best fixed arm, which on E12 is STOP/N0/N1 tied. STOP is the cheapest, so it is
    the comparator.
- **Roots:** the next prospectively ordered records of the MRL-15 frame (seeded ranks 21 onward, no outcome
  use). They need contract review and wrong-control validation exactly as for E12, with no backfill.
- **Execution:** direct paired execution per root.
  - One initial call.
  - The public diagnostic, used for gating.
  - The policy's R1 continuations, R = 2, **only where the gate fires**, plus R1 on public-pass roots, as
    audit-only data (never used by the policy), to measure what the gate saves.
  - Primary descriptive contrast: gated rule minus STOP.

**Budget formula** (G = roots, f = fraction with public failure, about 0.36 in E12):

| item | cost |
|---|---|
| receiver calls | G · (1 + 2), when R1 also runs on public-pass roots for audit |
| isolated starts | 3G (validation) + G (public) + 3G (private grades) + 2G (rechecks) = 9G |

**G = 30:**

- 90 receiver calls, 46,080 reserved completion tokens, 270 starts;
- about 3 minutes of collection;
- a new start budget is needed (ledger 333 of 412);
- the contract review of about 30–40 fresh records is the main preparation cost.

## What would count as informative

- The gated rule's contrast with STOP on fresh roots, reported per root with the gate's hit rate and its
  false-gate rate (public fail but private pass, as on 863).
- Still development-scale. Confirmatory policy validation remains the lead's separate design
  (`docs/independent_prompt_policy_validation_design_20260922.md`).
- A null or negative result is equally reportable.
