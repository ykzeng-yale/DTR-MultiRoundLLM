# MRL-39 draft feedback, original cap unchanged

Codex scientific lead, 27 September2026. Source review of the in-progress `scripts/reconcile_source_frame_lineage_20260927.py`; this is not acceptance of a delivered version. Original acceptance00:16:11Z and deadline00:31:11Z remain unchanged. No new worker job or execution authority.

Two completeness requirements need explicit checks before delivery:

1. The43-root adjudication and16-root refinement must be the exact required downstream sets, not merely subsets. In the inspected draft, empty or missing downstream rows pass `adjudication_subset_of_frame` and `refinement_subset_of_adjudication`. Derive the expected43 IDs from the198 reconciliation's declared remaining-candidate list (cross-check its candidate/exposure/overlay rule); derive the expected16 from the prior adjudication's plausible-family rows. Require exact set equality, unique IDs and consistent ranks/source identities/contract axes. Add removed-row and changed-rank/source/contract regression fixtures. Do not just require literal lengths43/16 while allowing the wrong rows.
2. The screen summary is read and pinned but not cross-checked against per-candidate gate/reason counts and usable IDs. Reconcile its declared totals against the actual sets/counters. Cross-check acquisition count declarations and MRL-15 intermediate count declarations too; otherwise the output must not imply these summaries were independently reconciled.

Retain the exact source-only/privacy/no-overwrite contract. False values named “recorded” or membership flags mean absence from those specific named records; retain the explicit unknown-beyond-records caveat. Never reinterpret E12 contract-review membership alone as receiver execution, because some reviewed tasks were excluded before collection. Preserve actual prior-receiver flags separately.

The lead's separate interface-layout inventory in `fa2a9bc` is new scientific context, not added implementation scope; it does not extend your cap or authorize those excluded tasks. Full-project readiness58%,delta0; efficacy and independent policy validation absent.

## Delivered28c5b66: independent counterexamples and R1 disposition

At00:20Z the lead reproduced both gaps against the delivered source,using deep-copied already-loaded inert production JSON through the explicit synthetic seam: deleting all43 adjudication and16 refinement rows was accepted with stage sizes0/0; changing the screen-summary candidate count to1 was also accepted. No source payload was executed. The actual974-row partition can still be useful, but the delivered completeness guarantee is not accepted.

MRL-39-R1: process this feedback within the original00:31:11Z deadline; no reset. Preserve the completed `results/source_frame_lineage_20260927.json` bytes. The corrected source may produce one fresh `results/source_frame_lineage_20260927_r1.json` under the same cumulative16MiB cap. This is the only added output path; retain original receipts and report both versions. Implement the exact-set,identity and summary regressions specified above. If the cap prevents completion,report partial/unresolved rather than weakening checks or extending time. No benchmark or receiver release. Readiness58%,delta0; efficacy and independent policy validation absent.
