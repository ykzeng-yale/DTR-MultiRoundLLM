# E11 proposed runbook: the 77-call development collection (NOT RELEASED)

**Experiments workstream proposal, for the lead's release decision.** Nothing here is authorized, and nothing
has been run. It turns the MRL-08–11 machinery into one ordered command sequence, so a release can be
reviewed and executed exactly. It also names the **one source gap** that blocks an end-to-end run.

## Preconditions (all must hold; otherwise BLOCKED with zero dispatch)

1. **Lead release** of E11, with a cap, after reviewing MRL-11 (`b73054e`).
2. **Receiver ownership record.** `experiments/landmark/dev_release_v2/ownership.observed.json` must be
   completed with a real exclusive-use window and agreement reference from the receiver's owner (the :8193
   server was launched by the ICLR-WinRatioAgentEvals session). The collector refuses any `UNRESOLVED:`
   value, placeholder text, or a window shorter than `max_seconds` (1,200 s). **This cannot be invented.**
3. **Attestation age.** A containment attestation less than 24 h old from this host. The MRL-11 attestation
   dates from 2026-09-21T20:17:03Z and is valid until 2026-09-22T20:17Z; after that, E1 is re-run (9 starts).
4. **Freeze.** The collector's `verify_freeze` passes at HEAD (config, tasks and sources committed and
   byte-identical). The receiver state digest must equal `1b8bf998…`, which the collector checks live
   before the run, before every root and after it.

## Ordered commands (`RUN=work/e11_dev_v2_<UTC>`, which must not exist)

| phase | command | cap | stop condition |
|---|---|---|---|
| A: initial | `.venv/bin/python -m experiments.landmark.collect_diagnostic --phase initial --config experiments/landmark/dev_release_v2/config.json --tasks experiments/landmark/dev_release_v2/tasks.jsonl --output $RUN/A --real --ownership <completed ownership record>` | 7 calls | any receiver drift, busy slot, window expiry or freeze failure stops dispatch; outputs are kept; the run is marked not interpretable |
| B: public diagnostics | `.venv/bin/python -m experiments.landmark.public_phase --initial-dir $RUN/A --examples docs/public_diagnostic_examples_v1.json --out $RUN/B --attestation <attestation.json> --real` | ≤ 7 starts (format errors start nothing) | INCOMPLETE ledger → stop; no rerun into `$RUN/B` |
| C: continuation | `.venv/bin/python -m experiments.landmark.collect_diagnostic --phase continue --config … --tasks … --initial-dir $RUN/A --diagnostics $RUN/B/diagnostics.json --diagnostics-sha256 <from $RUN/B/manifest.json> --public-examples docs/public_diagnostic_examples_v1.json --output $RUN/C --real --ownership <same record>` | 70 calls (study total 77; 39,424 reserved completion tokens; 1,200 s) | as phase A; a real continue refuses a mock or different-freeze initial phase |
| D: grading | **GAP: no CLI.** `study_adapter.to_grading_view` → `grade_study(…, runner=sandbox.run_program, attestation_path=…, frozen_tasks_path/sha, expected_contract_sha256, expected_config_sha256, expected_source_hashes from release_manifest.json)` | 77 artifacts + ≤ 24 reference/control rechecks = ≤ 101 starts | any J7 binding mismatch refuses before any start |
| E: analysis | `study_adapter.to_analysis_input(…)` (**GAP: no CLI**), then `.venv/bin/python -m experiments.landmark.analyze_diagnostic --roots <adapter output> --diagnostics $RUN/B/diagnostics.json --output $RUN/analysis.json` | 0 starts | descriptive only: S1−N1 primary; no intervals; the field-15 cross-tab |

**Start budget.** E11 needs at most 7 + 101 = 108 isolated starts. Within the 200-start ledger, MRL-11 used 77,
leaving 123.

## Source gap that blocks an end-to-end run (needs a bounded allowance)

`experiments/landmark/study_adapter.py` has **no command-line entry point** for phase D (grading) or the
analysis adapter. `analyze_diagnostic` also receives no Phase B executor cost unless it is supplied (the
Phase B manifest records starts but not the diagnostic cost fed to the analyzer). The proposed repair is
source/mock only:

- `python -m experiments.landmark.study_adapter grade …` and `… analysis-input …`, reading every J7 binding
  from `dev_release_v2/release_manifest.json`;
- refuse on any mismatch;
- opt-in `--real` with the attestation checked first;
- a durable ledger;
- mock tests.

I estimate one CPU and at most 20 minutes. It can be authorized now as preparation or bundled into the E11
release.
