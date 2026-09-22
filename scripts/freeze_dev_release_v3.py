#!/usr/bin/env python3
"""MRL-16: write dev_release_v3 config.json + release_manifest.json from the built package and the settled source.

Source-only; executes nothing. Run after every MRL-16 source edit has landed (the collector source hash and the
grading source hashes are frozen here). Refuses to overwrite.
"""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.landmark import collect, collect_diagnostic as cd, diagnostic, grade, study_adapter  # noqa: E402

D = ROOT / "experiments/landmark/dev_release_v3"
V2 = ROOT / "experiments/landmark/dev_release_v2"
ROSTER = [918, 825, 842, 816, 895, 868, 288, 154, 863, 966, 652, 651, 499, 974]
HOLDS = {31: "tie/order unspecified (review)", 847: "copy vs alias not distinguished (review)",
         907: "private answers recoverable from public prefix; print vs return (review)",
         963: "message strings unstated; invalid private classification (review)",
         359: "literal message strings unstated (MRL-15 frame review)", 349: "literal message strings unstated (MRL-15 frame review)"}


def fsha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--frame-review", type=Path, required=True)
    ap.add_argument("--run-id", required=True, help="fixed E12 output location work/<run-id>")
    a = ap.parse_args(argv)
    a.frame_review = a.frame_review.resolve()
    if (D / "config.json").exists() or (D / "release_manifest.json").exists():
        raise SystemExit("Refusing to overwrite config.json/release_manifest.json")
    tasks = [diagnostic.strict_json_loads(l) for l in (D / "tasks.jsonl").read_text().splitlines() if l.strip()]
    specs = [diagnostic.strict_json_loads(l) for l in (D / "private_specs.jsonl").read_text().splitlines() if l.strip()]
    ids = [int(t["root_id"].split("/")[1]) for t in tasks]
    if ids != ROSTER:
        raise SystemExit(f"Package roster {ids} differs from the released roster")
    grade.validate_specs(tasks, specs)
    n = len(tasks)
    cfg = json.loads((V2 / "config.json").read_text())
    cfg.update(protocol_version=f"landmark-development-release-v3-diagnostic (14 prospective fresh roots; adapted public contracts; 1 public / 2 private MBPP assertions; one wrong control per root; grader {grade.GRADER_VERSION}; public-diagnostic-v2)",
               dataset_sha256=collect.digest(tasks), grading_contract_sha256=grade.digest(grade.contract(specs)),
               source_code_sha256=collect.digest(collect.source_hashes()), max_calls=11 * n,
               max_completion_tokens=11 * n * cfg["max_tokens_per_call"], max_seconds=1200)
    collect.validate(cfg, tasks, real=True)
    (D / "config.json").write_text(json.dumps(cfg, indent=2) + "\n")
    frame = json.loads((a.frame_review / "records.json").read_text())
    recs = frame if isinstance(frame, list) else frame.get("records", [])
    fam = {int(r["task_id"]): r.get("provisional_family") or r.get("family_label") for r in recs if int(r["task_id"]) in ROSTER}
    plan = cd.assignments(cfg, tasks)
    run = f"work/{a.run_id}"
    py, rel, att = ".venv/bin/python", "experiments/landmark/dev_release_v3", "results/validation_bundle_v2_20260921T201642Z/attestation/attestation.json"
    own = f"{rel}/ownership.agreed.json"
    commands = {
        "validation_private": f"{py} -m experiments.landmark.validate_rebound_references --specs {rel}/private_specs.jsonl --specs-sha256 {fsha(D / 'private_specs.jsonl')} --tasks {rel}/tasks.jsonl --expected-starts {2 * n} --out {run}/validation/private --attestation {att} --real",
        "validation_public": f"{py} -m experiments.landmark.public_instrument_validation --gate E6v3 --package-dir {rel} --public-examples {rel}/public_examples_v3.json --display v2 --expected-n {n} --out {run}/validation/public --attestation {att} --real",
        "A": f"{py} -m experiments.landmark.collect_diagnostic --phase initial --config {rel}/config.json --tasks {rel}/tasks.jsonl --output {run}/A --real --ownership {own}",
        "B": f"{py} -m experiments.landmark.public_phase --initial-dir {run}/A --examples {rel}/public_examples_v3.json --out {run}/B --attestation {att} --display v2 --real",
        "C": f"{py} -m experiments.landmark.collect_diagnostic --phase continue --config {rel}/config.json --tasks {rel}/tasks.jsonl --initial-dir {run}/A --diagnostics {run}/B/diagnostics.json --diagnostics-sha256 $DIAG_SHA --public-examples {rel}/public_examples_v3.json --output {run}/C --real --ownership {own}",
        "D": f"{py} -m experiments.landmark.study_adapter grade --release-manifest {rel}/release_manifest.json --specs {rel}/private_specs.jsonl --initial-dir {run}/A --continue-dir {run}/C --out {run}/D --attestation {att} --real",
        "E": f"{py} -m experiments.landmark.study_adapter analysis-input --release-manifest {rel}/release_manifest.json --view {run}/D/view --grades {run}/D/grades.jsonl --phase-b-dir {run}/B --expected-diagnostics-sha256 $DIAG_SHA --out {run}/analysis_input.json",
        "DIAG_SHA": f"DIAG_SHA=$({py} -c \"import json,sys;print(json.load(open(sys.argv[1]))['diagnostics_sha256'])\" {run}/B/manifest.json)",
        "same_head_guard": "FREEZE=$(git rev-parse HEAD) before A; test \"$(git rev-parse HEAD)\" = \"$FREEZE\" before B, C, D and E; no pulls mid-batch",
    }
    m = {"manifest": "dev-release-v3-diagnostic", "status": "MRL-16 package; validation then collection only inside a fresh owner window",
         "roots": [f"mbpp/{i}" for i in ROSTER], "n_roots": n, "holds_no_backfill": {f"mbpp/{k}": v for k, v in HOLDS.items()},
         "prior_exposure": {"historical_prior_seen": "dev_release_v1c prior_seen_root_ids (598)", "inspected_development_roots": [f"mbpp/{i}" for i in (52, 357, 373, 378, 402, 489, 509)]},
         "provisional_families": {f"mbpp/{k}": v for k, v in fam.items()}, "family_note": "provisional duplicate screen only; min-member-hash representatives; NOT uniform family sampling; not independence",
         "contract_note": "adapted MBPP contracts (docs/e12_contract_review_20260922.md), incl. 288 general-modulus amendment; two private assertions per root; not a benchmark-wide correctness certificate",
         "frame_review": {"dir": str(a.frame_review.relative_to(ROOT)), "records_sha256": fsha(a.frame_review / "records.json")},
         "model": {"model": cfg["model"], "model_digest": cfg["model_digest"], "server_build": cfg["server_build"], "receiver_state_sha256_expected": cfg["receiver_state_sha256"], "sampler_law": cfg["sampler_law"]},
         "evaluator": {"grader_version": grade.GRADER_VERSION, "diagnostic_schema": diagnostic.SCHEMA_V2},
         "seed_schedule": {"derivation": "collect.seeded(config, root_id, label) = int(digest([seed, root_id, label])[:15],16) % 2**31; labels 'initial' and '<arm>:<replicate>'; independent streams, NOT common-random-number coupling", "seed": cfg["seed"]},
         "assignment_table": plan, "assignment_table_sha256": collect.digest(plan),
         "package": {f: fsha(D / f) for f in ("tasks.jsonl", "private_specs.jsonl", "public_examples_v3.json", "config.json", "controls_rationale.json", "exclusions.json", "overlap_audit.json")},
         "diagnostic_schema": diagnostic.SCHEMA_V2,
         "grading_limits": {"n_roots": n, "artifact_starts": 11 * n, "recheck_starts": 2 * n, "max_private_starts": 13 * n, "grading_seconds": 600},
         "grading_bindings": {"frozen_tasks_path": str((D / "tasks.jsonl").relative_to(ROOT)), "frozen_tasks_sha256": fsha(D / "tasks.jsonl"),
                              "expected_contract_sha256": cfg["grading_contract_sha256"], "expected_config_sha256": collect.digest(cfg),
                              "expected_source_hashes": study_adapter.grading_source_hashes()},
         "caps": {"receiver_calls": 11 * n, "reserved_completion_tokens": 11 * n * cfg["max_tokens_per_call"], "collection_seconds": 1200,
                  "grading_seconds": 600, "isolated_starts": {"validation": 3 * n, "phase_b": n, "phase_d": 13 * n, "total": 17 * n},
                  "ledger": {"spent_before": 174, "ceiling": 174 + 17 * n}, "outer_wall_minutes": 60, "paid_usd": 0},
         "run_id": a.run_id, "output_location": run, "commands": commands,
         "ownership": {"status": "a fresh, real 60-minute owner agreement must be committed at experiments/landmark/dev_release_v3/ownership.agreed.json before A"}}
    (D / "release_manifest.json").write_text(json.dumps(m, indent=1) + "\n")
    print(json.dumps({"n": n, "contract": cfg["grading_contract_sha256"][:16], "source": cfg["source_code_sha256"][:16], "calls": cfg["max_calls"], "tokens": cfg["max_completion_tokens"]}, indent=1))


if __name__ == "__main__":
    main()
