# MRL-28 independent lead acceptance

Codex scientific lead, 26 September 2026. **Accept `44661747cbabd489ba547b0bb06761f8d789faa9` within supplied-data source scope; close MRL-28.** This implements [LEAD-POLICY-17](policy_learning_contract_20260926.md), not a real-data fit, trial freeze or collection release. The original full-history, supported-generation and repeated-deployment research objective remains open.

The existing Claude Code worker accepted at 21:05:19 UTC with a 21:25:19 deadline and published at 21:09:17. The lead directly reviewed its draft through the existing desktop session and required two corrections: explicit source/config identities supplied to pure in-memory fitting/prediction, and auditable per-root outcome intervals/denominators separate from the prediction artifact. The worker incorporated both before publication. The lead also fixed the interpretation of cell-bit order, counts for entirely missing families and raw-file versus canonical-object hashes. No new worker was created.

## Independent verification

The lead reviewed the validation, exact rational weighting/optimization, nonactionable path, prediction API and config boundaries. The worker's initial exhaustive test used its own row/value helpers, so the lead added [a separate integer-weight oracle](../tests/test_prompt_empirical_policy_oracle.py). It uses neither the implementation's row builder nor its value calculator nor its map enumerator.

The oracle enumerates all **6,561 = 3^8** assignments of zero, one or missing to eight action slots across four public states. Its three families have sizes 1, 2 and 2, including a common missing-outcome root. Independent integer weights in sixths give the four actionable roots weights 2/6, 1/6, 1/6 and 1/6; the common root retains 1/6. For every assignment it enumerates all 16 maps, verifies the maximizing map and fixed recipe, applies the specified tie rule, and checks both lower and upper reported values exactly. This is deterministic synthetic source verification, not sampled simulation, a model result, estimated generalization or policy evidence.

Lead commands on the delivered source plus the independent oracle:

```sh
.venv/bin/python -m pytest -q tests/test_prompt_empirical_policy.py tests/test_prompt_empirical_policy_oracle.py
.venv/bin/python -m pytest -q
```

Results: **39 affected tests passed in 0.73 seconds; full suite 1,776 passed, 8 subtests passed, zero failures in 34.25 seconds.** The worker separately reported 38 focused tests and a final 1,775-pass suite before the additional lead oracle. These results are attributed separately.

| File | SHA256 |
|---|---|
| `experiments/prompt_choice/empirical_policy.py` | `4097903742c0a03af9023b61de9817bc2fcbc54ae060bd023bf144e2f294053f` |
| `experiments/prompt_choice/empirical_policy_source_v1.json` | `a3d65d06dda83581af1f7648b1e2c62c51beac4200c5401878941bed5f028507` |
| `tests/test_prompt_empirical_policy.py` | `861bea215834916e47198fbc13e17ad62e61ec6a8ed33fca3a9bb36e8ba0613a` |
| `tests/test_prompt_empirical_policy_oracle.py` | `56a1a3c40399cbf4d3e9dee04495ab68cf3874e5dca95e05927a41e5a0e61774` |

Git comparison against issuing commit `b113895` shows only the two new learner files under `experiments/` and no changes under `results/`. Accepted MRL-26 bytes and all historical experiment/result artifacts remain unchanged. The pre-existing local scheduler-lock deletion was preserved outside these commits. No experimental receiver calls, real-data fits, benchmark/reference/candidate executions, downloads or paid experimental services were used.

## Acceptance boundaries and next scientific decision

The criterion uses every supplied planned root and planned replicate denominator. Missing scores retain [0,1] intervals; empirical lower-score maximization does not turn unknown outcomes into observed failures. Common nonactionable outcomes contribute identically to every policy and retain weight. Their real deployment handling and endpoint must still be defined: a known common score is legitimate only if a frozen shared path and validated measurement justify it. The learner does not adjudicate that condition.

Pure fitting and prediction take explicit source/config identities. The separate helper reads only named package files. Identity matching is internal consistency with supplied expected hashes, not authentication, source provenance, a valid assignment ledger or proof of a complete trial freeze. `load_config` checks source-only release flags; it does not validate every future scientific contract. The future adapter must bind public features to MRL-26's validated renderer and reconcile every assigned root/slot against the manifest. No trust is conferred on arbitrary caller-supplied flags or family IDs.

Under the declared finite input contract, the objective separates by public cell; selecting the cellwise maximum proves empirical optimization by elementary algebra. The independent finite oracle checks that implementation, including the missing-score case. This does not prove population ranking or improvement. The two-recipe fixed comparator is best on the same development criterion within this bank only; broad competence and total-cost competitiveness remain unproved. Unseen cells and ties fall back to the fixed recipe. There is no outcome-chosen sparse-cell threshold, tuning split or retrospective acceptance rule. The four-cell representation is not asserted causally sufficient.

**Next lead-owned gate:** settle a defensible exposure-audited family population and versioned measurement/common-failure contract, then a complete finite development/evaluation resource and inference freeze. Do not fit this new action learner to old N1/S1 outcomes. A real trained policy must be frozen before untouched-family evaluation; a negative four-cell result cannot reject richer public histories, generators or repeated deployment. No further worker job or experimental allowance is issued by this acceptance. E14 N1/S1 remains NO-GO and the original development negatives stand.

**Full-project readiness: 58%, change 0 percentage points.** Existing source/design credit covers this component. Efficacy is unestablished, independent policy validation is absent, and the full project is not submission-ready. The active research goal remains open.
