> **Lead review: proposal requires correction; not an accepted analysis plan.** See [MRL-15 decisions](mrl14_review_mrl15_20260922.md). In particular, categorical sample-size impossibility claims and exclusion of format-driven effects below are not endorsed. Default preparation is uniform family sampling, without outcome screening. Original proposal is preserved below for traceability.

# Next discriminating sampling design (MRL-14 proposal; NOT authorized for execution)

2026-09-22. Proposal only. No collection, generator development, regrading or policy validation is released by
this note. Every number below is planning arithmetic, not a power certification or an efficacy claim.

## Why a new frame

E11 used seven reused development roots with their public examples; 6/7 were initially correct, so S1–N1 = 0
on all 7 roots is mostly a ceiling: few roots had room to improve. The lead owns that limitation. The fix is a
frame fixed before any collection. Replacing roots by looking at E11 outcomes would be cherry-picking and is
excluded.

## (a) Prospective root/family frame

- **Source.** The 396 mechanically usable fresh MBPP candidates from the committed pool screen
  (`scripts/screen_landmark_pool.py`, contract `docs/pool_screen_contract.md`, run
  `results/pool_screen_20260921T131231Z/`, source SHA `ccf64cea…a92a9f`). Decide before any outcome whether
  the interface rule is relaxed toward ~538; the default is to keep 396.
- **Exclusions, fixed and hashed before any receiver call, in this order:**
  1. prior-seen: every task id or text-hash used in E1–E11, the v1/v1c slates and the pilots, plus the seven E11
     development roots;
  2. family/duplicate screen: near-duplicate specifications and shared-function families, clustered into
     families. Families are the sampling unit; m ≤ 3 roots per family (MRL-05 ρ_F);
  3. specification review: ambiguous or under-specified prompts, or tests inconsistent with the prompt. Exclude
     or rewrite by a rule written before sampling, and log every rewrite.
- **Sampling.** Draw families by a seeded uniform draw from the post-exclusion frame, then roots within
  families. Publish the seed, the frame hash and the draw order. Expected post-review size is about 115
  (confirmatory_sizing extrapolation, unmeasured). If it falls below the planned G, report the shortfall.
  Do not top up from outside the frame.
- **Forbidden inputs to selection:** E11 grades, any private initial grade, any receiver output.

## (b) Optional initial-failure screen (frozen public rule only)

- **Rule (frozen before the screen runs).** For each sampled root, take one screening draw from the receiver
  with a seed stream **separate** from the study's seeds. Screen positive = that draw fails **at least one
  public example**. Only the public examples are used. The private suite is never consulted at decision time.
- **Two strata, both retained.** U = unscreened: a uniform subsample of all sampled roots, taken regardless of
  the screen result. F = screen-positive roots, sampled at a fixed fraction f_F. Screen-negative roots outside
  U are dropped with probability 1 − f_N. Record π_r = P(root r included | frame) for every root.
- **Two targets, stated separately.**
  - T_all: Δ over the full post-exclusion frame. Estimate it from U alone, or from U ∪ F with Horvitz–Thompson
    weights 1/π_r.
  - T_fail: Δ over roots whose frozen public screen fails. Estimate it from F, together with U roots that
    screened positive.
  - A T_fail result is a statement about failure-enriched roots only. It never transfers to T_all without
    weighting.
- **Private initial grades** (the study-seed initial attempt, graded privately) may describe results, for
  example as a room-to-improve stratum in reporting. They never select roots, set π_r or feed a deployed
  policy.

## (c) Arms, R and budget (planning arithmetic)

- **Arms (as in E11):** STOP, N0, S0, N1, S1, R1. The primary contrast is S1−N1. N1−N0, S0−N0 and R1−N1 are
  secondary. One shared initial prefix per root. R = 2 seeded continuations per continuation arm, with the
  same seed stream across arms (MRL-05 coupling).
- **E11 per-root cost:** 1 + 5·2 = **11 receiver calls/root** (77/7). Grading starts were 66/7 ≈ **9.4 isolated
  starts/root**, including rechecks. The screen, if used, adds 1 call and 1 public-only start per screened
  root.

| roots graded | receiver calls (11/root) | grading starts (≈9.4/root) | screen cost if all 396 screened |
|---|---|---|---|
| 30 | 330 | ≈283 | +396 calls, +396 public starts |
| 60 | 660 | ≈566 | same |
| 115 (≈ frame after review) | 1,265 | ≈1,084 | same |

- **Precision framework (MRL-05).** Var(Δ̂) = [σ²_B(ρ_F + (1−ρ_F)/m) + σ²_W/(mR)]/G. The E11 contrast gives no
  usable τ² (all D = 0), so use the MRL-05 grid.
  - Example (τ² = 0.15, s = 0.2, ρ_F = 0, R = 2): a Wald bound for the 0.05-versus-0.10 question needs ≈283
    roots, more than the frame can supply. Finite-sample procedures need far more (empirical Bernstein ≈1,200
    families; J2 Hoeffding ≥ 2,952).
  - So the frame cannot certify "Δ > 0.05". At most it can support a **development-scale discriminating check**:
    does S1−N1 depart from 0 on roots with room to improve?
  - Choosing the uncertainty procedure remains the lead's decision.

## (d) What would and would not count as informative

- **Informative:** on T_fail, or on the room-to-improve reporting stratum, a prespecified family-clustered
  interval for S1−N1 that excludes 0 in either direction. Also informative: a T_fail interval narrow enough to
  bound |S1−N1| below a prespecified margin, stated as a bound and not as equivalence, together with the S0/S1
  damage counts among initially correct roots with unknowns listed separately.
- **Not informative:**
  - another zero contrast on a mostly initially-correct sample;
  - any result on roots chosen after seeing outcomes;
  - T_fail results reported as T_all;
  - contrasts where format or fence failures, rather than semantic changes, drive the difference (report
    these separately, as for root 402 in E11);
  - any "futility" or "equivalence" language from a small G.

## (e) Preconditions

1. **Grader compile repair (MRL-14) landed and validated first.** Candidate compile-validity checks go in the
   private and public static gates, and a candidate SyntaxError is told apart from harness or infrastructure
   faults. The versioned grader hash is recorded in the freeze. E11's two S0 module-level returns show that
   ast.parse alone misclassifies. A study graded by the old gate would repeat that defect.
2. Frame, exclusions, seeds, screen rule, π_r and analysis procedure are frozen and hashed before any receiver
   call.
3. Explicit lead authorization of budget (calls, starts, wall time); this document grants none.
