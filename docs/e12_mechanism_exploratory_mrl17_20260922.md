# MRL-17: exploratory static descriptions of E12 outputs (after the frozen report)

> Lead review, 23 September: The 140 descriptions reproduce, but the saved JSON incorrectly labels its inputs E11/seven roots. It actually analyzes E12/14 roots. The base prompt already imposed a single-answer format. See the [independent interpretation](e12_lead_judgment_20260923.md); original evidence is unchanged.

**Evidence class: exploratory, static, descriptive.** This was produced after the frozen E12 report
([e12_results_20260922.md](e12_results_20260922.md)), which it does not alter. It uses the lead-corrected
`scripts/e11_mechanism_analysis.py` on the immutable `results/e12_dev_v3_20260922T030255Z/`, with **0 model,
compiler, candidate, reference or sandbox executions**, and `grade.extract_code` + `ast.parse` only.
Output: `results/e12_mechanism_exploratory_mrl17_20260922.json` (sha256 `1561bbc7…`).

**How to read the measures:**

- **AST identity of the top-level functions is not semantic equality.** It ignores imports and module state.
- **Extraction or parse failure is *unassessable*, not "changed".**

Denominators reconcile: all **140 of 140** assigned continuation slots, 14 roots × 5 arms × 2. All 14 initial
answers were clean single-function extractions.

| arm | same function as initial | changed | unassessable | extra top-level code | mean completion tokens |
|---|---|---|---|---|---|
| N0 | 22 | 6 | 0 | 0 | 43 |
| S0 | 18 | 10 | 0 | 7 | 80 |
| N1 | 17 | 11 | 0 | 0 | 51 |
| S1 | 16 | 5 | **7** | 2 | **153** |
| R1 | 9 | 15 | 4 | 8 | 87 |

## Observations (not conclusions)

- **S1 has 7 unassessable outputs, all multi-block.** Each has 3–13 fence markers; 3 hit the 512-token cap.
  All 7 occur on roots whose initial public diagnostic reported a failure (288 ×2, 863 ×2, 966, 652 ×2), which
  is 7 of the 10 S1 continuations on those 5 roots. Under the frozen complete-answer endpoint these are real
  failures (lead ruling 1). The receiver answered the directive with several code blocks rather than one
  corrected answer.
- **R1's 4 unassessable outputs are unfenced text that does not parse** (966 ×2, 652 ×2).
- **N1 versus N0.** Showing the diagnostic under the neutral instruction changed the extracted function more
  often (11 versus 6) **without changing any grade**: N1 − N0 = 0 on every root.
- **On the 4 initially wrong roots,** the only graded repairs are S1 on 842 (replicate 1, changed function),
  R1 on 842 (replicate 0) and R1 on 288 (replicate 0). No arm repaired 966 or 652.

## Hypotheses for the lead (not tested here)

1. Diagnostic-directed repair on failing roots may primarily trigger **multi-block formatting**. If so, a
   single-answer format constraint would be a distinct, declared intervention change and would need its own
   freeze.
2. The same diagnostic-directed branch damaged root 863, where the public example failed but the private suite
   passed. This is a measurement-and-contract interaction to examine.

Neither hypothesis supports a policy claim, and no roots were filtered, tuned or stopped.

**Usage:** 1 CPU, under 1 minute, $0.
