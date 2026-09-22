# MRL-17: review of E11 output descriptors and E12 exploratory reporting

Lead decision on worker delivery `08d63b73777075fbd4e35469caad4221422c813f`, 22 September 2026. **Accept the reproduced E11 descriptive counts; repair the metric and interpretation; proceed with a separately labeled E12 exploratory supplement.** This adds no gate to MRL-16 collection and changes no intervention, grade, stopping rule or primary analysis.

## Evidence and independent checks

The target of this delivery is the structure of saved E11 outputs, not a new prompt-effect estimate. The evidence is a post-hoc reuse of seven development roots. Independent static reconstruction matched all three input hashes, all 70 detail rows and all original arm totals; the parsing/hash portion took approximately 0.027 seconds. Neither reviewer nor lead executed candidate code or made receiver calls. A second independent scientific reviewer checked the interpretation against the frozen intervention and diagnostics. Original result bytes are retained. The corrected reporting implementation passes 16 targeted static tests in 0.08 seconds, including unassessable outputs, missing token counts and source provenance. The lead also verified that the original JSON remains byte-identical to 08d63b7 and that the new input/source hashes, 70-row partitions and token totals agree.

The function-definition identity counts are N0: 10 same/4 different/0 unassessable; S0: 8/6/0; N1: 9/5/0; S1: 12/0/2; R1: 6/7/1. The original script marked failed extraction/parsing as `False`, so subtracting its same-count from 14 incorrectly combined observed differences and unassessable outputs. The corrected script uses three states and reports known tokens separately from unavailable counts. All 70 actual E11 continuation token counts are present, totaling 4,636; correcting missing-token handling changes no E11 token total. This saved-call diagnostic is not by itself an all-assigned analysis when a future run has unattempted calls.

The metric compares all ordered top-level function-definition ASTs; it ignores imports and other module statements. It is not semantic equivalence. Extra statements are not automatically useful self-tests. Six initial outputs contain one function;402 contains two and an import, despite all seven meeting the script's narrower “clean” category.

Reproduce the corrected static report with a fresh output path:

```bash
.venv/bin/python scripts/e11_mechanism_analysis.py --out work/e11_mechanism_recheck.json
```

## Scientific corrections

1. **The S1/402 failure cannot be attributed only to formatting.** Both outputs violate the complete-answer extraction rule. Both displayed implementations also directly return 1 at `r=0`; the already-public `(3,0,1)` example requires 0. The lead and independent reviewer confirmed this from source, without choosing an alternate block for grading or executing it. Withdraw “format, not a wrong repair.” The frozen zero grades stand.
2. **E11 did not observe the hypothesized public-pass/private-fail stratum.** All six public-all-pass roots were privately correct. Root402 instead had two public exceptions and one wrong value. Thus the preserved-function pattern does not demonstrate suppression of repair in an unobserved stratum. Keep that possibility as a hypothesis, not a finding or reason to redesign E12.
3. **Rewriting is not an established cause of R1 damage.** R1 contains seven assessable AST differences and one non-code response, rather than eight measured rewrites. The two damages are a non-code response and a wrong formula. Context and instruction both change in that arm; a post-treatment association between changes and failures is not a mediation result.
4. **Scaffolding is not validated self-verification.** Seven S0 outputs contain self-test-like statements; two have invalid module-level returns and one compares a function call with itself. Report those concrete observations without claiming a general causal tendency or useful verification.

The corrected [worker-facing interpretation](e11_mechanism_analysis_20260922.md) and separate v2 analysis artifact incorporate these distinctions. The manuscript retains the primary null and adds only the bounded exploratory findings.

## MRL-17 bounded handoff

After completing and publishing the frozen E12 report, the existing worker may produce static output descriptors in a **separate E11-informed exploratory supplement**. Bound: one CPU, at most 10 minutes, $0, zero model calls, candidate/reference/compiler/sandbox executions, installations or reruns. This is a one-time optional reporting allowance, not new collection authority; it must not delay E12 collection or withhold its primary report.

- Preserve the frozen S1–N1 contrast, every assigned root and all grades. Reconcile descriptor denominators to the frozen all-assigned report; saved calls alone omit unattempted slots in a partial run. Report absent initial/output records and noncomparable ASTs explicitly.
- Keep the static metric definition literal. Retain separate same/different/unassessable counts and unknown token totals. Do not call structural equality semantic equivalence or top-level statements successful tests.
- Publish input, script and extractor-source hashes. The current CLI labels its artifact as seven-root E11; an E12 supplement must carry the actual E12 roster and E11-informed exploratory label, rather than inheriting that hard-coded study description. Do not repair, select or re-execute code blocks to rescue failed artifacts.
- No interim outcome-driven tuning, exclusions, early stopping, confidence claims or policy promotion. Any public-status/private-outcome strata are descriptive and do not become private-label deployment inputs.

Use **MRL-17** for accepted/completed/blocked/superseded reporting with UTC and commit/artifact IDs in the next ordinary update. MRL-16 remains the already accepted run authority, blocked only on its actual receiver-window/live conditions. Do not pull this update into a running batch. Lead corrections here are complete; no further lead review round is needed to begin or finish the frozen collection.

Overall milestone completion remains **55%, change 0 points**. These are reused-data diagnostics and manuscript corrections, not fresh E12 outcomes, efficacy, independent policy validation or submission readiness.
