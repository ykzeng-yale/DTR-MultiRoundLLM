# E11 proposed runbook: the 77-call development collection (NOT RELEASED)

**Experiments workstream, revised under MRL-12.** Nothing here is authorized, and nothing has been run. Every
command is exact, with no ellipses. Shell variables are defined once and never invented mid-run.

## Preconditions (all must hold; otherwise BLOCKED with zero dispatch)

1. **Lead release** of E11, with its cap.
2. **A receiver ownership record** from the :8193 server's owner, written to a new file `$OWN` (the
   observed-facts template is `experiments/landmark/dev_release_v2/ownership.observed.json`). It needs a real
   exclusive window and an agreement reference. Nothing is invented.

   **The window must be at least 45 minutes, and here is why.** The collector checks
   `now + max_seconds (1,200 s) <= window end` at the start of **each** of phases A and C, and checks the
   window again before every request. So the window has to cover A's actual time, plus B's, plus the
   operator gap, plus a full 1,200 s for C.
3. **An attestation less than 24 h old.** The current one, `results/validation_bundle_v2_20260921T201642Z/attestation/attestation.json`
   (`checked_at` 2026-09-21T20:17:03Z), is valid until 2026-09-22T20:17Z. The dependency diff
   (`results/dependency_diff_mrl12_20260921T205917Z.json`) shows its whole binding is unchanged. After expiry, a refresh (E1) costs **9 more starts**,
   which must be accounted for explicitly and are not a free retry.
4. **Same committed freeze for A and C.** Record `FREEZE=$(git rev-parse HEAD)` before A, and require
   `git rev-parse HEAD` to equal `$FREEZE` before C, D and E. Do not pull between phases. The collector's
   `verify_freeze` also checks that the committed config, tasks and source bytes match.

## Exact commands

```bash
set -euo pipefail
cd /Users/yukangzengcmac/DTR-MultiRoundLLM
PY=.venv/bin/python
REL=experiments/landmark/dev_release_v2
RUN=work/e11_dev_v2_$(date -u +%Y%m%dT%H%M%SZ)          # must not exist
ATT=results/validation_bundle_v2_20260921T201642Z/attestation/attestation.json   # or a fresh E1 output (+9 starts)
OWN=$REL/ownership.agreed.json                          # the owner's completed record (not yet existing)
FREEZE=$(git rev-parse HEAD)
# A: initial answers (7 receiver calls)
$PY -m experiments.landmark.collect_diagnostic --phase initial --config $REL/config.json --tasks $REL/tasks.jsonl --output $RUN/A --real --ownership $OWN
# B: public diagnostics (at most 7 isolated starts; format errors start nothing)
test "$(git rev-parse HEAD)" = "$FREEZE"
$PY -m experiments.landmark.public_phase --initial-dir $RUN/A --examples docs/public_diagnostic_examples_v1.json --out $RUN/B --attestation $ATT --real
DIAG_SHA=$($PY -c "import json,sys;print(json.load(open(sys.argv[1]))['diagnostics_sha256'])" $RUN/B/manifest.json)
# C: continuations (70 receiver calls; study total 77 calls, 39,424 reserved completion tokens, 1,200 s)
test "$(git rev-parse HEAD)" = "$FREEZE"
$PY -m experiments.landmark.collect_diagnostic --phase continue --config $REL/config.json --tasks $REL/tasks.jsonl --initial-dir $RUN/A --diagnostics $RUN/B/diagnostics.json --diagnostics-sha256 $DIAG_SHA --public-examples docs/public_diagnostic_examples_v1.json --output $RUN/C --real --ownership $OWN
# D: private grading (at most 77 artifacts + 24 reference/control rechecks = 101 starts)
test "$(git rev-parse HEAD)" = "$FREEZE"
$PY -m experiments.landmark.study_adapter grade --release-manifest $REL/release_manifest.json --specs $REL/private_specs.jsonl --initial-dir $RUN/A --continue-dir $RUN/C --out $RUN/D --attestation $ATT --real
# E: analysis (0 starts; descriptive only; no intervals)
$PY -m experiments.landmark.study_adapter analysis-input --view $RUN/D/view --grades $RUN/D/grades.jsonl --phase-b-dir $RUN/B --expected-diagnostics-sha256 $DIAG_SHA --out $RUN/analysis_input.json
$PY -c "import json,sys;d=json.load(open(sys.argv[1]));open(sys.argv[2],'w').write(''.join(json.dumps(r)+chr(10) for r in d['roots']));json.dump(d['diagnostics'],open(sys.argv[3],'w'))" $RUN/analysis_input.json $RUN/roots_for_analysis.jsonl $RUN/diagnostics_for_analysis.json
$PY -m experiments.landmark.analyze_diagnostic --roots $RUN/roots_for_analysis.jsonl --diagnostics $RUN/diagnostics_for_analysis.json --output $RUN/analysis.json
```

**Bindings carried between phases.**

- `DIAG_SHA` is read from Phase B's own manifest. Phase C refuses diagnostics whose bytes differ, whose case
  content is not the fixed public cases, or whose artifact hashes differ from A.
- `analysis-input` refuses unless `DIAG_SHA` equals the digest the continue phase recorded, and the Phase B
  root set equals the view's.
- Grading loads every J7 binding from the **committed** `release_manifest.json`, which must be byte-equal
  to its version in the latest commit.

**Analysis cost mapping.** Per root:

- `diagnostic_cost = {executor_starts: Phase B runner_invocations, executor_seconds: Phase B measured seconds or null}`;
- receiver prompt and completion tokens per arm come from the `calls.jsonl` of A and C;
- grading starts and seconds come from `$RUN/D/grading_attempts.jsonl`, and are reported as measurement
  cost, not policy cost.

## Time and start accounting (reported separately)

| quantity | source | cap |
|---|---|---|
| Collection time (A + C) | `completion.json` `wall_seconds`, carried study-wide | 1,200 s |
| Diagnostic executor time (B) | Phase B manifest `executor_seconds` per root | ≤ 7 starts |
| Grading time (D) | `grading_attempts.jsonl` `elapsed_seconds` | ≤ 101 starts |
| End-to-end | first A request to the analysis file | must fit the ownership window |

**Isolated starts.** E11 uses at most 7 + 101 = 108 starts, bringing the ledger to 185 of 200 (MRL-11 used 77).
An attestation refresh adds 9, for 194.

## Stop conditions

- **Phases A and C:** any receiver drift, busy slot, ownership-window expiry, freeze failure or budget
  exhaustion stops future dispatch; outputs are kept and the run is marked not interpretable.
- **Phases B and D:** an INCOMPLETE ledger means stop, with no rerun into the same directory.
- **Any phase:** a changed HEAD between phases means stop.
- Incomplete is never reported as a pass.
