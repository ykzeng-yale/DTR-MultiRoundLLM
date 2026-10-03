# Reproducing the current manuscript evidence

Codex scientific lead, 27 September 2026. This guide covers saved-record arithmetic, not new model generation, benchmark execution, regrading or a full clean-host reproduction. No experiment is released by these commands. The manuscript remains a working draft.

## Verified public-record layer

The [reproduction receipt](../results/manuscript_reproduction_20260927.json), SHA256 `4b684b2ac0f317aa6070198eece8637d27cc4ac44ac5be2240b5f6e37986ffcb`, binds47 inputs to committed Git blobs at `77fa58eff797433d6080d1875f3be96bd40c8db2`. The new recount script also records its executed source hash because that source was added after the input revision. Input identity and arithmetic were checked; raw private grading was not repeated.

| Evidence | Reproduced result | Starting layer and limit |
|---|---|---|
| Historical repair, selector split sensitivity and matched-estimator diagnostics | Existing reconciler passes5,792 arithmetic/consistency checks | Committed derived root scores, fit outputs and replication records; no original corpus extraction, fit or simulation replay |
| E11 | N1 andS1 each12/14; every primary root difference0; context-removal difference−1/7; two S0 grades remain missing | Committed grade rows; new read-only recount avoids the historical script's hardcoded receipt overwrite |
| E12 | N1 20/28,S1 19/28,primary difference−1/28; all154 assigned grades retained;33 archived files checked | Existing reconciler binds calls,grades,assignment keys and saved analysis; no regrading |
| E13a | R1 9/30,FRESH12/30,equal-root difference−1/10 | Committed request plan and grade rows; selected five-checkpoint development target unchanged |
| Two-root endpoint audit | Public9/12,original-private4/12,supplement2/12 | Committed36-slot projection,not private sandbox-log replay |
| Nine-root endpoint audit | Public34/54,original-private21/54,supplement9/54 | Committed162-slot projection,not private sandbox-log replay |

The historical source-audit counts and67-root information bound have their own [hash-bound inventory](../results/reviewed_panel_information_bound_20260927.json). They are planning/source judgments,not receiver data. No rows or contrasts from different targets are pooled here.

## Commands

Run from the repository root with Python3 and Git. These scripts use the standard library and do not import a receiver,collector or benchmark program. Use a fresh output directory; outputs refuse overwrite. The first two commands read working-tree inputs and record their hashes,so compare them with the receipt before claiming the same evidence version. The third reads the specified committed Git blobs directly.

```sh
repro_out=$(mktemp -d)
python3 scripts/reconcile_manuscript_evidence.py --output "$repro_out/saved_diagnostics.json"
python3 scripts/reconcile_e12_20260923.py --output "$repro_out/e12.json"
python3 scripts/reproduce_development_counts.py --revision 77fa58eff797433d6080d1875f3be96bd40c8db2 --output "$repro_out/development_counts.json"
```

The new recount validates unique/exact assigned grade keys,retains explicit missing grades,and rejects Boolean/nonbinary outcomes and duplicate endpoint slot IDs. Six focused checks confirmed duplicate/missing-assignment/Boolean/nonbinary refusal,retention of an explicit missing grade,and refusal to overwrite an existing output without mutating it. These checks validate the recount's finite input handling; they do not certify historical assignment,measurement quality or all possible corruptions. The main diagnostic replay took0.031seconds and the E12 replay0.011seconds on this host; these are analysis runtimes,not model latency or total project cost. No model calls,payload execution or paid experimental services were used.

Do not rerun `scripts/reconcile_e11_20260922.py` in place merely to reproduce this table: it writes directly to the historical receipt path. Its original source is preserved for provenance; use the new recount's separate output instead. The new tool does not rerun that script's static candidate-compilation checks.

## Clean-checkout verification

The three commands were also run from a clean managed checkout at `b7456e2`, using Python 3.9.6 with `-I` and a child environment containing only `PATH=/usr/bin:/bin`. Neither `work/` nor a project virtual environment existed in that checkout. No dependency installation was needed. Each command had a 60-second process timeout and wrote to a separate temporary output directory; all three returned zero, and the checkout remained clean.

The [new receipt](../results/manuscript_clean_checkout_20260927/receipt.json) records the interpreter, platform, source hashes, process times and output hashes. Its three adjacent JSON files retain the complete new outputs. All 47 input hashes match the earlier receipt. Diagnostic counts and all repair/selection/estimator summaries match exactly; the complete E12 reconciliation matches except its timestamp and runtime; the complete development/projection recount matches exactly. The reproduced diagnostic count is 5,792, and E12 verifies 33 saved files. No model, benchmark, fitting or simulation execution occurred.

For this verified variant, add `-I` after `python3` in each command above and use the scripts/working-tree inputs from `b7456e2`; retain the explicit older input revision in the Git-blob recount. Ordinary non-shallow Git history must contain that revision. This is a same-host clean-checkout check using the existing Git object store, not a fresh remote clone or independent-host reproduction. It establishes that these arithmetic commands do not require the primary checkout's ignored data; it does not establish reproducibility of the full experimental environment.

## What is still required for full reproduction

Git contains the cited projections and saved development outcomes. Private source/reference/control payloads and some raw sandbox evidence intentionally remain in ignored `work/` storage under their original manifests. Their availability and hashes must be checked separately before a grader replay. A successful public-record count does not substitute for that evidence,an external-source licence/acquisition check,a compatible verified sandbox,or pinned receiver/server/decoder state.

Historical synthetic studies have distinct freezes and missing/capped slots; rerunning their fits would be a new controlled reproduction rather than these arithmetic commands. No new sampling,task repair,endpoint change or policy training is authorized by this guide. Full environment/source availability and the integrated bibliography/claim audit remain incomplete. Independent evaluation of a frozen policy on a defensible untouched-family population is still absent; neither reproducible arithmetic nor a green test suite supplies it.

## Rendering the saved-evidence figure

From the repository root, with the declared project matplotlib/numpy dependencies:

```sh
.venv/bin/python scripts/render_manuscript_figures_20260927.py --out-dir /tmp/dtr_figures_new
```

The output directory must not exist. The renderer uses the committed clean-checkout diagnostic receipt and writes PDF, SVG, PNG and source/output hashes. It performs no model call, benchmark execution, statistical refit or new inference. The saved PNG was visually inspected for labels, clipping and separation of evidence layers. Library versions are recorded in the figure receipt; PDF timestamps may differ on rerendering, so output hashes identify an artifact rather than promise cross-run binary identity.

## Clean locked-package check (27 September, direct Codex execution)

The reusable clean worktree was advanced to`bc8cb0e`. Offline synchronization first failed because the locked SciPy wheel was absent from the cache (both the automatically selected Python3.13 and explicit3.12 attempts are retained in the receipt). Online `uv sync --frozen --extra dev` with Python3.12.13 then installed the unchanged lockfile. The full suite passed **2,170 tests plus8 subtests, with49 skips**, in52.59seconds. There was no ignored`work/` directory, and Git remained clean. This is a same-host clean-checkout package check, not a new-host reproduction, raw benchmark replay or validation of skipped checks. The ordinary pytest output did not retain individual skip reasons. [Receipt and complete logs](../results/clean_package_reproduction_20260927/receipt.json).

## Incomplete finite-source study, 3 October update

The fitted-artifact reproduction receipt is results/sprint_fit_lock_audit_20261001.json. Generation integrity for eval1 is recorded in results/sprint_eval1_generation_reconciliation_20261002.json; the full per-assignment audit and immutable raw archives remain in ignored work/sprint_terminal_20261002_v6. These receipts validate specified artifact identities and generation assignments, not held-out outcomes. The public-record reproduction commands above do not reproduce this new study or release missing generation/grading. Preserve all raw checkpoints and failed receipts; do not replay completed calls or select complete cases to manufacture an evaluation.
