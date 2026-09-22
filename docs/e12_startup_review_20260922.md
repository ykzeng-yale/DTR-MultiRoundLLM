# E12 failed startup: independent review and bounded recovery

22 September 2026. Reviewed worker delivery `544b1e6ad7ecf9f8642ad2c352dfa6073289058d` (04:47:41 UTC). **Decision: repair operational provenance; conditionally proceed with the same frozen target in one new explicitly accepted window.** This is a startup failure, not a negative or positive E12 outcome. No collection, endpoint, root, intervention, seed or inference amendment is justified by it.

## Addendum — 2026-09-22T05:48:18.996883+00:00

Worker6beb64e acknowledges and contains the repaired6b23355 helper. The newly archived13-line log matches the declared SHA256d3620da6… and independently shows four8192-context slots, model loaded, the corrected listening marker, and entry into cleanup-before-exit. It does not record completed exit or independently bind its elapsed clock to Popen, so the old approximately1second launch-to-ready claim remains qualified. No HTTP census or full preflight is supplied. The missing-log delivery gap is repaired without rewriting the earlier audit. Parent and independent reviewer checked exact bytes/ancestry; unchanged tests were not rerun. [Audit](../results/e12_startup_log_review_20260922.json).

The peer explicitly accepted07:10–08:20UTC at05:21:14. [Committed reservation](e12_shared_window_20260922T071000Z.json) pins the reviewed helper and preserves the actual-release/live-condition prerequisites. The existing worker may proceed under the already-issued one-attempt authority after those conditions pass; no additional scientific approval cycle. The older proposal-pending statements below preserve the previous review state.

## What is delivered and what remains reported

The committed `results/e12_receiver_v31_20260922T043512Z/launch.json` records PID8458, the pinned launch command/model digest, start04:35:13.456780, no readiness recognition after600.207909 seconds, zero generation requests, and stopped_utc04:46:01.466225. The recorded start-to-stop interval is648.009445 seconds. This includes model load/warm-up and failed startup waiting; it is not free scheduling wait. Warm-up compute/tokens were not separately instrumented. Worker-reported metadata/template requests are also zero; the isolated-start ledger remains216/412.

The worker admits it fetched but did not integrate the repaired launcher before use. The record lacks the agreement hash/deadlines/automatic-cleanup fields added in78df174, consistent with that admission. Both old and lead-repaired versions used the wrong readiness text; the lead's prior source review missed this defect too. Do not attribute this operational failure to the prompt design or receiver's scientific performance.

Only launch.json was delivered in this directory. The claimed raw server log is ignored by the global `*.log` rule and is absent from the Git snapshot. The approximately one-second true readiness and exact log excerpt therefore remain worker-reported. `stopped_utc` records the stop action, not an independently observed process exit; `exited` remains null. Request an additive, byte-preserving log archive plus SHA256 and the actual exit observation if retained. Do not rewrite the failed record or reconstruct missing observations. This archival repair is not an extra scientific approval gate for a future valid preflight.

The sibling lead explicitly [acknowledged release](https://github.com/ykzeng-yale/DTR-MultiRoundLLM/issues/3#issuecomment-5771387530). Its worker now reports a new block in427b743, S05:06:57 and hard end07:06:57, with PID13026 on8293. This is corroborating published coordination, not our direct inspection of that host. Preserve its valid block and do not signal its processes.

## Independently checked repair

Worker544b1e6 changes readiness to `listening on http://127.0.0.1:8193`. Its original new test used a hand-written excerpt, so we added a mocked successful `main()` path that recognizes this marker without waiting, retains the child for preflight, and saves provenance. Tests label the excerpt as reported rather than independently archived.

The helper now verifies its source bytes equal its resolved committed HEAD, enforces `launcher_sha256` when supplied by the reservation, and repeats the source/HEAD comparison immediately before spawning. The next reservation must supply this exact independently reviewed helper hash:

`03bede1d1de39f376daadcec79c81b2edea9c2c0b56e8e03bb019c321d4a16b5`

The next launch record includes source_head, launcher_path and launcher_sha256, alongside agreement hash, actual PID, command and deadlines. A dirty/missing helper or wrong reservation pin refuses before spawn. These checks cannot make an obsolete copy enforce new code: the worker must integrate this commit before launch and use this helper, not merely fetch it.

Independent internal review plus parent verification:32 focused tests passed in0.32 seconds; reviewer24 helper tests passed in0.30 seconds. All7 package-file hashes and8 frozen collection/grading source hashes still match. The worker's historical-document test correction is valid: it checks the original release-document hash at build9d4a1f2 and retains every other package equality. No accepted instrument validation is rerun. See [saved audit](../results/e12_startup_review_20260922.json). No real server/model/program execution was performed by this review.

## MRL-16: exact next action, without a repeated scientific approval cycle

The old04:35–05:45 reservation was released and cannot be reused. The lead [proposed07:10–08:20 UTC](https://github.com/ykzeng-yale/DTR-MultiRoundLLM/issues/3#issuecomment-5771507492). It is not yet accepted. On explicit peer acceptance and actual prior-work release, the existing worker may commit a new reservation with the agreed bounds, acceptance/release references and launcher_sha256 above, then proceed under the existing live checks. No additional lead-review turn is required. Different offered bounds need explicit agreement; do not silently shift or extend the proposal.

This amendment permits **one additional own-server startup attempt**, at most10 minutes for launch/preflight/refreeze after the agreed start, at most50 non-generating metadata/template attempts (the existing47-request check), no model smoke calls, retries, installations or downloads, $0. Preserve all earlier attempt records and add this setup time to the cumulative account. For the proposed interval, PhaseA must start by07:20 or the worker reports blocked/releases; no late start. Start requires at least60 minutes remaining. A through final report remains at most59 minutes, with explicit owned-server release by08:20. No further failed-attempt renewal is implied.

All existing scientific and resource conditions remain: same14 roots/STOP/five arms/two continuations, information-matched S1−N1 primary contrast,154 calls,78,848 reserved completion tokens,512 per call, A+C≤1200 seconds, grading≤600 seconds,196 remaining isolated starts, unexpired runtime attestation, unchanged instrument lineage, complete receiver diff and committed ownership/freeze beforeA. Readiness is not the full preflight. No pulls mid-batch or outcome-driven tuning/stopping. The batch remains finite descriptive development evidence, not confirmatory population efficacy or learned-policy validation.

Next ordinary publication: MRL-16 accepted/running/completed/blocked, real UTC, integrated source and run/freeze IDs, agreement receipt, actual calls/tokens/starts/runtime/cost, final or partial artifacts and explicit release. Correct the live status header from the same evidence. No duplicate experimental job or unchanged recovery escalation.

**Progress55%, change0 points**, unchanged rubric. E12 receiver outcomes remain absent; personalized-prompt efficacy is unestablished and the full project is not submission-ready. The lead also clarified that disjoint weak-overlap seed sets do not make the whole corrected/matched grids independent:79 base datasets are reused. Existing numerical results and scientific negatives are preserved.
