> **Status: revised per MRL-15 lead rulings 1–5 (COORDINATION.md, 2026-09-22T02:07:07Z and 02:07:58Z).
> Pending lead review. Not an analysis plan, not a collection authorization, and not a budget grant.**
> Supersedes the MRL-14 draft (see [MRL-15 decisions](mrl14_review_mrl15_20260922.md)). The changes are listed at the end.

# Next development sampling design (proposal; NOT authorized for execution)

2026-09-22. Proposal only. No collection, generator development, regrading or policy validation is released
by this note. Every number is planning arithmetic under stated assumptions. None is a power certification or
an efficacy claim.

## 1. What E11 established (ruling 1)

- **E11 is a valid descriptive null.** S1−N1 = 0 on the 7 reused development roots. The 2 missing secondary
  grades do not invalidate that primary result.
- **Separate mechanisms, none claimed as the cause:**
  - *Limited repair opportunity.* 6 of 7 roots succeeded at STOP, so few roots had room to improve. This limits
    what E11 could show. It is **not** an established causal explanation of the null.
  - *Damage.* Initially correct roots can still be damaged by the continuation prompt. E11 measures this too.
  - *Format/fence failures.* Under the frozen complete-answer endpoint these **are** failures, and informative
    ones (e.g. root 402 and the two S0 module-level returns). Report them as their own mechanism. Never drop
    them from the contrast.
- Replacing roots because of E11 outcomes would be cherry-picking. It is excluded.

## 2. Default design: uniform family sampling, no outcome screen (ruling 3)

- **Starting point: the frame review** [`docs/frame_review_mrl15_20260922.md`](frame_review_mrl15_20260922.md),
  produced alongside this revision. It is a manifest-backed review of at most 20 deterministically ordered
  candidate records from the 396-candidate screened frame (`results/pool_screen_20260921T131231Z/`,
  contract `docs/pool_screen_contract.md`). Each record carries its inclusion/exclusion reasons, family label
  and uncertainty. That review is preparation only. It does not authorize collection or certify that
  families are independent.
- **Verify before sampling:** the 396-screened frame and the fixed source-only exclusions, applied in this
  order:
  1. prior-seen: task ids and text hashes used in E1–E11, the v1/v1c slates, the pilots, and the 7 E11 roots;
  2. family/duplicate clustering, with families as the sampling unit and m ≤ 3 roots per family (MRL-05 ρ_F);
  3. specification review under a rule written before sampling, with every exclusion or rewrite logged.
- **Sampling.** Draw families by a seeded uniform draw from the post-exclusion frame, then roots within each
  family. Publish the seed, the frame hash and the draw order.
- **No outcome-based screen.** Selection never uses receiver outputs, E11 grades or private initial grades.
  There is no root substitution based on receiver outcomes. If the frame falls short of the planned G, report
  the shortfall and do not top up from outside the frame.
- **Frame size is unknown.** "About 115" was an unverified extrapolation, not the eligible-frame size. The
  eligible-frame size is whatever the verified review yields.
- **Arms (as in E11):** STOP, N0, S0, N1, S1, R1, with S1−N1 primary. One shared initial prefix per root, and
  R = 2 coupled continuations per continuation arm (MRL-05).
- **Reporting.** Private initial grades may describe results, for example as a room-to-improve stratum. They
  never select roots or feed a policy.

## 3. Optional, separate proposal: failure enrichment (ruling 4; NOT the default)

This option is out of scope until all of the following are fully specified and frozen before any
π_r/Horvitz–Thompson claim:

- **Unspecified parts of the draft.** The draft left five pieces undefined:
  - the U/F overlap, i.e. how a root in both the uniform subsample and the screen-positive set is counted;
  - the screen-negative retention f_N, which was never defined;
  - the family-level selection law;
  - the within-family selection law;
  - the random screening law that yields π_r for every frame root.
- **Two different targets:**
  - *Screening-seed failure.* A failing draw on a separate seed stream predicts a root's **propensity** to
    fail. It is not failure of the study's actual initial prefix. Regression to the mean means many
    screen-positive roots may still succeed at STOP, so the ceiling can persist.
  - *Branching at an observed failing history.* Continuing from an initial prefix that actually failed is a
    different estimand, conditional on observed failure. It must not be conflated with the screened-root
    target.
- **Public statuses.** Each public check records exactly one status:

  | status | meaning | counted as candidate failure? |
  |---|---|---|
  | `pass` | the candidate compiles and passes the public examples | no |
  | `fail` | the candidate compiles and fails ≥1 public example | yes |
  | `format_error` | the candidate itself is invalid: no complete fenced function, or a genuine candidate SyntaxError | yes |
  | `error` | an infrastructure fault: a harness, sandbox or compiler resource/internal fault (MemoryError, RecursionError, …) or a timeout of the harness itself | **no**, reported separately |
  | `unknown` | not attempted, record missing or unreadable | **no**, reported separately |

  `error` and `unknown` are never counted as task difficulty or as screen-positive. A root whose screen is
  `error` or `unknown` needs a prespecified π_r rule, for example that it enters only through the uniform
  stratum.

## 4. Precision: planning results under stated assumptions (ruling 2)

- Var(Δ̂) = [σ²_B(ρ_F + (1−ρ_F)/m) + σ²_W/(mR)]/G (MRL-05). E11 yields no usable τ² because every D = 0, so
  the MRL-05 grid applies.
- **Scenario τ² = 0.15, s = 0.2, ρ_F = 0, R = 2.** The normal-approximation Wald calculation for the
  0.05-versus-0.10 question gives ≈283 roots. The particular concentration-bound scenarios computed in MRL-05
  gave larger figures (empirical Bernstein ≈1,200 families; J2 Hoeffding ≥2,952).
- These are **planning results under those assumptions**, not impossibility results or minimum-sample
  theorems. A larger observed effect, or smaller realized variance, changes the attainable bounds (MRL-05
  ruling). The uncertainty procedure is the lead's decision.
- The realistic target for 10–20 roots is a development-scale check: does S1−N1 depart from 0, with
  prespecified family-clustered intervals, damage counts among initially correct roots, and format failures
  and unknowns listed separately? Small G never supports "futility" or "equivalence" language.

## 5. Budget: worst-case authorized isolated starts (ruling 5)

The budget uses worst-case authorized counts, not the E11 cached average. The 66 total E11 starts are not
relabeled as private grading starts.

**Per root, with no caching and no retries:**

| component | isolated starts | receiver calls |
|---|---|---|
| public diagnostic on the initial artifact | 1 | – |
| private grades on all artifacts: 1 STOP/initial + 5 continuation arms × R = 2 | 11 | – |
| per-root reference check + do-nothing-stub control check | 2 | – |
| receiver: 1 initial + 10 continuations | – | 11 |
| **total per root** | **14** | **11** |

**Formula.** For G roots, with S roots screened (S = 0 under the default design) and k authorized reruns:

- starts(G) = G·(1 + 11 + 2) + S·1 + k = **14G** + S + k
- calls(G) = 11G + S
- runtime ≈ calls × t_call + starts × t_start, run serially on one CPU. t_call and t_start are taken from the
  attested host record, not assumed here.

If public diagnostics are also required on each continuation, add 10 starts per root (24G).

| G roots | isolated starts (14G) | receiver calls (11G) | ledger if added to 174 (143 spent + 31 conditional) | ledger if added to 143 |
|---|---|---|---|---|
| 10 | 140 | 110 | 314 / 200 | 283 / 200 |
| 20 | 280 | 220 | 454 / 200 | 423 / 200 |

- **Both sizes exceed the existing 200-start ledger.** 26 starts remain if the conditional 31-start check
  runs, or 57 if it does not. Even G = 10 does not fit.
- Any collection at these sizes, and any screening, failures, reruns or model calls, needs an **explicit new
  budget** from the lead. Nothing above 200 is granted by extrapolation, and this document grants none.

## 6. Preconditions

1. The v2.1 grader (MRL-15 compile-fault repair) is committed and validated. A candidate SyntaxError is
   distinguished from infrastructure faults at the public and private entry points, and the versioned grader
   hash is recorded in the freeze.
2. The frame review is verified. Frame, exclusions, seeds, draw order and analysis procedure are frozen and
   hashed before any receiver call.
3. The lead explicitly authorizes the budget: starts, calls and wall time.

## Changes from the MRL-14 draft

- Removed "mostly a ceiling" as an explanation. Format/fence failures are now counted as informative.
- Removed the categorical claims "frame cannot certify Δ>0.05" and "finite-sample procedures need far more".
- The default is uniform family sampling with no screen, starting from the frame review. "About 115" is
  marked as unverified.
- Failure enrichment is now an optional separate proposal. Its open specifications and public statuses are
  listed.
- The budget is rebuilt on worst-case isolated starts per root (14G). The table based on the E11 average of
  about 9.4 starts per root is dropped.
