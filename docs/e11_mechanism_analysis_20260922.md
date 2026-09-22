# E11 post-hoc output analysis: structural differences despite tied grades

**Evidence class: post-hoc, exploratory, descriptive.** Corrected after independent lead review of worker delivery `08d63b7`. This uses immutable E11 outputs from seven reused development roots, changes no grade and performs no candidate or receiver execution. The original result remains `results/e11_mechanism_analysis_20260922.json`; the corrected tri-state result is `results/e11_mechanism_analysis_v2_20260922.json`. See [the lead judgment](e11_mechanism_lead_review_20260922.md) for the corrections and E12 reporting decision.

## What the saved outputs show

Each arm has 14 saved continuation records. Identity refers to the ordered list of **all top-level function-definition ASTs**, ignoring source locations. It excludes imports and other module-level statements. Consequently, equality is not semantic equivalence, and inequality does not necessarily mean that the task function changed: helpers or duplicate definitions can differ too. An extraction or parsing failure is unassessable, not a measured rewrite.

| Arm | Same function-definition AST | Different assessable AST | Unassessable | Additional module-level statements | Mean completion tokens, rounded |
|---|---:|---:|---:|---:|---:|
| N0 | 10 | 4 | 0 | 0 | 34 |
| S0 | 8 | 6 | 0 | 7 | 110 |
| N1 | 9 | 5 | 0 | 1 | 42 |
| S1 | 12 | 0 | 2 | 0 | 79 |
| R1 | 6 | 7 | 1 | 0 | 67 |

All 70 completion-token counts are known, totaling 4,636 continuation tokens. The initial answers contain no module-level statements beyond functions/imports. Six contain one function; root402 contains two functions and an import. The original statement that all seven were single functions was incorrect.

- S1 preserved the function-definition AST on both continuations of each of the six public-all-pass roots. Those roots were also privately correct. This is an observed structural pattern, not evidence that the instruction generally causes conservation or suppresses repair.
- Both S1 outputs on402 violated the frozen single-block extraction rule. **Format rejection does not establish a correct attempted repair.** In fact, both displayed implementations return1 when `r=0`, including the already public input `(n,r,p)=(3,0,1)` whose required value is0. This counterexample follows by reading the source; no code was executed and no alternate block was regraded. The original “format, not a wrong repair” interpretation is withdrawn.
- Seven S0 outputs contain additional self-test-like statements. Two include invalid module-level returns (378/replicate1 and489/replicate1). In489/replicate0 the comparison calls the function on both sides and is tautological. Presence of scaffolding does not demonstrate discriminating or successful verification. The underlying generic metric counts additional non-function/import statements, not successful tests.
- R1 has seven assessably different function-definition ASTs and one unassessable non-code response. Its two recorded damages are the non-code response on378 and a wrong formula on509. The comparison does not identify rewriting as their cause. R1 changes a context/instruction package and retains the public diagnostic.

## Exploratory questions, not established mechanisms

The failing402 initial answer received two public program-exception statuses and one wrong value. E11 therefore has **zero initial public-all-pass/private-fail roots**. It cannot substantiate the hypothesis that the all-pass preservation instruction suppresses repair in that stratum. The possibility remains an exploratory question for future observations, not a reason to revise the frozen S1 rule or enrich E12 after seeing outcomes.

Static output descriptors may accompany E12 only as a separately labeled **E11-informed exploratory supplement** after the frozen batch and primary report. They must retain assigned roots, report absent/noncomparable outputs separately and preserve unknown costs. They neither replace primary outcomes nor justify filtering, tuning, unplanned stopping or policy promotion. The primary E12 release and its resource conditions are unchanged.
