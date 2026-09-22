# E11 post-hoc mechanism analysis: behaviour changed even where grades tied

**Evidence class: post-hoc, exploratory, descriptive.** This is not a prespecified endpoint. It uses the immutable
E11 outputs (7 reused development roots) and changes no grade or E11 result. It is static only
(`grade.extract_code` and `ast.parse`), with **no execution and no receiver request**. Reproduce with
`scripts/e11_mechanism_analysis.py`; the results are in `results/e11_mechanism_analysis_20260922.json`.

## What the saved outputs show (14 continuations per arm)

| arm | kept the initial function (AST-identical) | added top-level test code | extraction/parse failure | mean completion tokens |
|---|---|---|---|---|
| N0: neutral, no diagnostic | 10 | 0 | 0 | 34 |
| S0: syntactic cue | 8 | **7** | 0 | **110** |
| N1: neutral + diagnostic | 9 | 1 | 0 | 42 |
| S1: diagnostic-directed | **12** | 0 | 2 | 79 |
| R1: context removal | **6** | 0 | 1 | 67 |

All 7 initial answers were clean single functions.

- **S1 is the most conservative arm.** On the six all-pass roots its instruction reads "passes the listed
  public examples … preserve correct behavior", and the receiver kept the function in 12 of 14 outputs.
  The tie with N1 is therefore partly *no change*, not *changed but still correct*.
- **On the only failing root (402), S1 failed by format, not by a wrong repair.** Both S1 outputs contained
  multiple code blocks (4 and 5 fence markers; one hit the 512-token cap), and the grader's single-block
  rule could not extract an answer. Every other arm changed 402's function (except N0 replicate 0, which
  returned it unchanged), and none became correct.
- **S0 induces self-test scaffolding.** 7 of 14 outputs appended top-level test code. These are the longest
  outputs, and they are the source of the two module-level-`return` compile failures.
- **R1 rewrites most** (8 of 14 changed), and its two damages come from that: 378 is non-code text, and 509
  is a wrong formula.

## Why it matters

Equal pass rates hid strongly different behavioural effects: conservation (S1), scaffolding (S0), rewriting
(R1) and multi-block formatting on the failing root (S1). Under the complete-answer endpoint these format
effects are real failures, per lead ruling 1, not noise to remove.

For E12, whose prespecified analysis is frozen, the same static measures can be reported **as labelled
exploratory secondary descriptions** next to the frozen report, never in place of it. Two questions follow:

1. Does the S1 instruction's "preserve" branch suppress repair when the single public example passes but the
   private suite fails?
2. Does S1's multi-block formatting recur on failing roots?

These are hypotheses for the lead, not conclusions from 7 roots.
