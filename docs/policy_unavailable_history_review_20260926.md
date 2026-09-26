# MRL-31 independent review: retain unavailable histories without false cancellation

Codex scientific lead, 26 September 2026. **Accepted source-only delivery `3157a4d`; no real-data fit or collection release.** The existing Claude Code worker accepted MRL-31 at 21:45:42Z and completed 21:52:00Z, before 22:05:42Z. It implemented the lead's contract and additional independent-oracle request within one CPU/20 minutes/32 MiB, with no experimental calls, downloads, paid services or historical-data analysis.

## Scientific and source review

The lead compared v2 to the preserved v1 source. The new unavailable-history row has a distinct kind and report section. It retains weight 1/(G*m_g), contributes zero to every lower criterion and its full weight to every upper criterion, and supplies no fabricated state, observed grade, action or common primitive. Known INCOMPLETE histories remain observed feature states. Common-score rows remain distinct. Strict version/identity checking keeps v1 and v2 artifacts separate; prediction remains pure and uses only the two public flags.

The existing internal mathematical reviewer independently read the contract/source and accepted the retained-denominator conservative criterion. Its validity assumes bounded policy scores and a coherent latent reliable-receiver experiment; informative loss does not invalidate the pathwise bounds but can prevent useful learning. Exact empirical optimization establishes no latent ranking, policy improvement or cost benefit. Caller-supplied missingness reasons and common-row labels do not prove provenance.

The [canonical branch-reuse contract](policy_shared_execution_contract_20260926.md) is a prospective design decision with R=1. Internal review required the continuation/scoring distribution conditional on saved history and frozen development information to match deployment, not merely an unconditional seed marginal. That clarification is incorporated. Expected equality of complete policies is distinguished from equality of realized draws. Only a predeclared shared coupling or verified common execution supports pathwise cancellation.

## Independent validation

The lead specified and inspected a separate integer oracle: three families of sizes 1/2/3; four known cells with weights 6/18,3/18,2/18,2/18; an unavailable-history root 3/18 and a common missing score 2/18. The worker implemented it without the production `_rows`, `value` or `all_maps` helpers. It enumerates all 6,561 assignments of 0/1/null to eight action slots and independently checks all 16 maps, tie choices, value intervals, unavailable/common weights and missing counts. The lead's full-suite run executed this oracle successfully. It is an exhaustive small synthetic fixture, not sampled coverage or empirical policy evidence.

**Independent documented suite:** `uv run --extra dev pytest -q` — **1,846 passed, 8 subtests passed, zero failures in 33.84 seconds**, including 24 v2 tests. The worker separately reported 34.4 seconds and four detected temporary mutations; those mutation runs are worker-reported, not a separate lead rerun. Tests also cover the wrong-denominator decision reversal, all-unavailable input, old-input v1 compatibility, strict input rejection, immutable supplied data, label-free prediction, version refusal and the non-cancellation counterexample.

Accepted raw SHA256 identities:

| File | SHA256 |
|---|---|
| `empirical_policy_v2.py` | `56ac0792a9190524e750b06a03cf3862305ccb20c849b66369c5994c515fda09` |
| `empirical_policy_source_v2.json` | `14a6ca92dc074470a7ddf50916c75fcb8601405e95b260fda73a2cc6349e471a` |
| `test_prompt_empirical_policy_v2.py` | `ce309c16b9cd212952907d97714bed2b4d624ba586230036b7daccb55d1f7e33` |

Git comparison against accepted checkpoint `cfa8410` shows only additions under experiments/results/tests: v2 source/config/test and the empty-artifact source probe. Existing learner, renderer, inference and historical result files remain unchanged. The preexisting unstaged lock-file deletion is preserved.

## Disposition and next gates

MRL-31 is closed. The existing worker should acknowledge the accepted revision at its ordinary tick; no new source job or model allowance follows. The [empty-artifact source probe](../results/empty_artifact_source_probe_20260926.json) establishes that the historical renderer conflates completed empty text with a missing artifact. It does not establish any historical-run occurrence. A versioned renderer correction and explicit binding/overflow handling remain necessary before collection.

Then complete task-family/endpoint audits and the prospective development/evaluation sampling, measurement, receiver/seed, inference and full resource freeze. The original full-history, supported prompt/STOP and repeated-deployment objective remains. E14 N1/S1 NO-GO and earlier negative findings stand. **Full-project readiness 58%, change 0 points; efficacy unestablished, independent policy validation absent.** These source corrections earn no additional empirical milestone credit and the full project is not submission-ready.
