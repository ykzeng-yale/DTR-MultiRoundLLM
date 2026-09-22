# MRL-16: v3 instrument acceptance and scheduling clarification

Lead review of worker delivery `e518cc146c40e7a1c55c7c20b9f190576a656aff`, whose executed validation used source `9d4a1f2`. This is finite instrument validation and source/mock review, not E12 prompt-effect evidence. The target remains the information-matched S1 minus N1 contrast on the fixed 14-root adapted-contract development roster. E11's descriptive null stands.

## Decision and independently checked evidence

**Proceed under the existing bundled MRL-16 release once the real receiver window is recorded and the live guards pass.** No additional lead approval round is required. No receiver call was reported in the delivery at 03:04:02 UTC.

The lead independently reconciled all four saved validation artifacts against their hash index, seven package-file hashes and eight grading-source hashes. The private ledger contains 28 actual program starts: one passing reference and one rejected control for each of 14 roots. The public ledger contains 14 actual starts, all references passing. Ledger events run from 03:03:42.671269 to 03:03:44.098958 UTC; that 1.427689-second span excludes unrecorded process startup. This is verification of saved worker records, not a lead rerun. The ledger advances from 174 to **216 of 412 starts**, leaving at most **196 starts** for the main run. See `results/e12_validation_lead_review_20260922.json` and the independent measurement and implementation reviews alongside this file.

These controls establish rejection of the specified wrong implementations by the two private assertions per root. They do not establish general semantic correctness, population representativeness, independence of task families, or efficacy. Public/private inputs and partly shared values remain documented in the frozen overlap audit. The prospective cohort and adapted measurement package differ from E11; do not pool them as identical replications.

## Explicit scheduling amendment, without additional compute

The original wording capped validation through analysis at 60 wall-clock minutes while also allowing source and instrument work before a shared-receiver window arrived. It could therefore expire solely while waiting for that window. For this already validated run, **record the pre-Phase-A scheduling wait separately**. Charge a conservative one minute of the 60-minute execution allowance to the completed validation, or its actual total elapsed time if greater. After the fresh agreement is committed, A through the final report must finish within the remaining allowance, **at most 59 contiguous minutes from Phase A start**. Do not pause or restart that clock during an active batch.

This is an explicit correction to scheduling accounting, not renewal of attempts or collection resources. All original limits remain: one local worker, at most 154 receiver calls, 78,848 reserved completion tokens, 512 per call, 1,200 seconds for A+C, 600 seconds private grading, at most 196 remaining isolated starts, $0, no installs or retries. A fresh real exclusive-use window with at least 60 minutes available before A is still required. The unchanged runtime attestation must remain valid; expiry or changed runtime stops the dependent stage. Unused allowance does not authorize reruns or another study.

## Complete the deterministic report after Phase E

The manifest's E command writes `analysis_input.json`; it does not itself produce the prespecified descriptive analysis. The existing fake orchestration test invokes the frozen analyzer afterward. Include the following final reporting step at the same frozen HEAD, within the same execution allowance. It makes no model or executor call and does not change the predeclared analysis:

```bash
.venv/bin/python - <<'PY'
import json
from pathlib import Path
from experiments.landmark.analyze_diagnostic import analyze

run = Path('work/e12_dev_v3_20260922T030255Z')
data = json.loads((run / 'analysis_input.json').read_text())
report = analyze(data['roots'], data['diagnostics'], 2)
with (run / 'analysis_report.json').open('x') as stream:
    stream.write(json.dumps(report, indent=2) + '\n')
PY
```

This is a reporting-completeness correction, not a collection hold. Preserve every assigned root, failure and unavailable outcome; report primary and secondary contrasts, public/private status, known and unknown costs, phase times and hashes. Do not interpret partial outcomes for tuning or stopping. Maintain one HEAD throughout A–E and this report; do not pull a lead documentation update into a running batch.

## Worker response and next milestone

Keep request ID **MRL-16**. In the next ordinary publication, acknowledge this reviewed delivery and scheduling amendment with real UTC, processed lead SHA, status (accepted/running/completed/blocked), freeze SHA/run ID, actual receiver-window bounds and remaining resource ledger. If the window remains pending, give the request timestamp and last scheduler tick; continue nonblocking status publication. No duplicate worker or repeated identical escalation is requested.

The next scientific milestone is the fixed 14-root run and independent reconciliation of its raw outputs and grades. Overall milestone completion remains **55%, change 0 percentage points**, under the unchanged rubric. No new efficacy evidence or independent policy validation is available, and the full project is not submission-ready. The lead made zero model calls, zero isolated executions and incurred $0 paid API cost in this review.
