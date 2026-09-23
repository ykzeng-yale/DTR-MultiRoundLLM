#!/usr/bin/env python3
"""E13a release bindings builder. EVIDENCE CLASS: none - this script produces BINDINGS ONLY.

It copies the five E13a checkpoint rows out of the frozen dev_release_v3 package and writes
experiments/landmark/e13a_release/. Nothing is executed and nothing is measured here: no receiver or model
call, no benchmark/reference/candidate/control/containment execution, no network. The release manifest it
writes authorizes none of those either (authorization.receiver_calls_authorized == 0,
authorization.candidate_executions_authorized == 0).

Copy rule (no new task-frame review, no private-assertion edit):
  * tasks.jsonl and private_specs.jsonl rows are the dev_release_v3 LINE BYTES, unchanged, reordered only
    into the stage's assignment order;
  * public_examples_v3.json and controls_rationale.json keep the source records unchanged (the selected
    records are written back verbatim; per-record canonical digests are pinned in the manifest);
  * config.json preserves the frozen receiver request law, but binds the five-root dataset, its private
    grading contract, current executable sources and E13a's smaller call/token/time limits.

Every input is sha256-verified before it is used: the dev_release_v3 package hashes come from that frozen
release's own manifest, and the E12 artifacts this stage conditions on are checked against both the E12 run's
ARTIFACT_SHA256SUMS.json and the verified E13a request plan. Refuses to overwrite an existing output
directory; --verify rebuilds into a temporary directory and diffs against the committed bytes. Unknown or
unresolved values are refusals, never zero-fills.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.landmark.collect import digest, file_sha, source_hashes  # noqa: E402

MANIFEST_ID = "e13a-two-arm-release"
RELEASE_DIRNAME = "e13a_release"
DEFAULT_OUT = "experiments/landmark/e13a_release"
DEFAULT_SOURCE = "experiments/landmark/dev_release_v3"
DEFAULT_STAGE = "experiments/landmark/e13a_stage.json"
DEFAULT_PLAN = "results/e13a_request_plan_20260922.json"
DEFAULT_RUN = "results/e12_dev_v3_20260922T030255Z"

COPIED_ROW_FILES = ("tasks.jsonl", "private_specs.jsonl")
COPIED_RECORD_FILES = ("public_examples_v3.json", "controls_rationale.json")
PACKAGE_FILES = COPIED_ROW_FILES + COPIED_RECORD_FILES + ("config.json",)
EXECUTION_SOURCES = ("scripts/e13a_collect.py", "scripts/e13a_grade.py", "scripts/e13a_stage_clock.py",
                     "scripts/e13a_analyze.py", "scripts/build_e13a_request_plan.py", "scripts/build_e13a_release.py",
                     "scripts/launch_own_receiver_v31.py", "scripts/receiver_preflight_mrl10.py",
                     "scripts/diff_receiver_snapshot_v31.py", "scripts/check_landmark_sandbox.py",
                     "experiments/landmark/grade.py", "experiments/landmark/sandbox.py",
                     "experiments/common/integrity.py")
RECORD_LIST_KEY = {"public_examples_v3.json": "cases", "controls_rationale.json": "controls"}
E12_CONDITIONING_FILES = ("A/roots.jsonl", "B/diagnostics.json")

# E13a bookkeeping limits. artifact_starts = 5 roots x 2 arms x 6 replicates; recheck_starts = 2 per root
# (reference + negative control); containment_starts = the containment-gate starts budgeted separately.
GRADING_LIMITS = {"n_roots": 5, "artifact_starts": 60, "recheck_starts": 10, "containment_starts": 9,
                  "max_private_starts": 79, "grading_seconds": 300}
AUTHORIZATION_STATEMENT = (
    "This manifest binds inputs, identities and bookkeeping limits only. It authorizes NO receiver or model "
    "call and NO candidate, reference, negative-control or containment execution. E13a execution remains held "
    "pending a separate release decision by the coordinating lead."
)
COPY_RULE = (
    "tasks.jsonl and private_specs.jsonl rows are the dev_release_v3 line bytes unchanged (assignment order "
    "only); public_examples_v3.json cases and controls_rationale.json controls are the source records "
    "unchanged; config.json rebinds dataset/contract/source hashes and resource caps while preserving the "
    "receiver request law. No private assertion, control or task frame was edited "
    "and no new task-frame review was performed."
)
DIAGNOSTIC_SCHEMA = "public-diagnostic-v2"


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _dump(obj):
    return json.dumps(obj, indent=1) + "\n"


def _rows_by_root(path):
    """{root_id: (line_bytes, record)} preserving each source line exactly as written."""
    out = {}
    for raw in Path(path).read_bytes().split(b"\n"):
        if not raw.strip():
            continue
        rec = json.loads(raw.decode("utf-8"))
        root = rec["root_id"]
        if root in out:
            raise ValueError(f"duplicate row for {root} in {path}")
        out[root] = (raw, rec)
    return out


def _records_by_root(path, key):
    data = _read_json(path)
    if key not in data or not isinstance(data[key], list):
        raise ValueError(f"{path} has no {key} list")
    by_root = {}
    for rec in data[key]:
        root = rec["root_id"]
        if root in by_root:
            raise ValueError(f"duplicate {key} record for {root} in {path}")
        by_root[root] = rec
    return data, by_root


def _verify_source_package(source_dir):
    """The frozen release's own manifest hashes gate every byte we copy."""
    src_manifest = _read_json(source_dir / "release_manifest.json")
    pkg = src_manifest.get("package")
    if not isinstance(pkg, dict):
        raise ValueError("dev_release_v3 manifest has no package hashes")
    for name in PACKAGE_FILES:
        if name not in pkg:
            raise ValueError(f"dev_release_v3 manifest does not pin {name}")
        actual = file_sha(source_dir / name)
        if actual != pkg[name]:
            raise ValueError(f"frozen source file changed on disk: {name} ({actual} != {pkg[name]})")
    return src_manifest


def _stage_roots(stage):
    roots = stage["roots"]
    if len(roots) != len(set(roots)) or len(roots) != GRADING_LIMITS["n_roots"]:
        raise ValueError(f"stage descriptor must name {GRADING_LIMITS['n_roots']} distinct roots")
    arms = stage["arms"]
    if set(arms) != {"R1", "FRESH"} or arms["R1"] != [2, 3, 4, 5, 6, 7] or arms["FRESH"] != [0, 1, 2, 3, 4, 5]:
        raise ValueError("stage descriptor arms are not the E13a two-arm design")
    return roots, arms


def _plan_pins(plan, roots, arms):
    """The verified request plan must cover exactly these roots, arms and replicates (60 requests)."""
    plan_roots = [r["root_id"] for r in plan["roots"]]
    if plan_roots != roots:
        raise ValueError(f"request plan roots {plan_roots} are not the stage roots {roots}")
    want = sorted((a, rep) for a, reps in arms.items() for rep in reps)
    total = 0
    for row in plan["roots"]:
        got = sorted((q["arm"], q["replicate"]) for q in row["requests"])
        if got != want:
            raise ValueError(f"request plan arm/replicate set for {row['root_id']} is not the stage design")
        total += len(got)
    if total != len(roots) * sum(len(v) for v in arms.values()):
        raise ValueError("request plan does not carry 60 requests")
    inputs = plan.get("inputs") or {}
    for name in E12_CONDITIONING_FILES:
        if not isinstance(inputs.get(name), str):
            raise ValueError(f"request plan does not pin {name}")
    return total, inputs


def _e12_pins(run_dir, plan_inputs):
    sums = _read_json(run_dir / "ARTIFACT_SHA256SUMS.json")
    files = sums.get("files")
    if not isinstance(files, dict):
        raise ValueError("E12 ARTIFACT_SHA256SUMS.json has no files map")
    pins = {}
    for name in E12_CONDITIONING_FILES:
        actual = file_sha(run_dir / name)
        if files.get(name) != actual:
            raise ValueError(f"E12 artifact {name} does not match ARTIFACT_SHA256SUMS.json")
        if plan_inputs[name] != actual:
            raise ValueError(f"E12 artifact {name} does not match the request plan pin")
        pins[name] = actual
    return {"run_id": sums.get("run", run_dir.name), "run_dir": str(run_dir.relative_to(ROOT)),
            "artifacts": pins, "sums_sha256": file_sha(run_dir / "ARTIFACT_SHA256SUMS.json")}


def build(out_dir, source_dir=None, stage_path=None, plan_path=None, run_dir=None):
    """Write the five-root release into out_dir (which must not exist). Returns the manifest dict."""
    out_dir = Path(out_dir)
    source_dir = Path(source_dir or ROOT / DEFAULT_SOURCE)
    stage_path = Path(stage_path or ROOT / DEFAULT_STAGE)
    plan_path = Path(plan_path or ROOT / DEFAULT_PLAN)
    run_dir = Path(run_dir or ROOT / DEFAULT_RUN)
    if out_dir.exists():
        raise SystemExit(f"refusing to overwrite existing output: {out_dir}")

    src_manifest = _verify_source_package(source_dir)
    stage = _read_json(stage_path)
    roots, arms = _stage_roots(stage)
    plan = _read_json(plan_path)
    n_requests, plan_inputs = _plan_pins(plan, roots, arms)
    e12 = _e12_pins(run_dir, plan_inputs)

    src_rows = {name: _rows_by_root(source_dir / name) for name in COPIED_ROW_FILES}
    src_records = {name: _records_by_root(source_dir / name, RECORD_LIST_KEY[name]) for name in COPIED_RECORD_FILES}
    for name, table in [*((n, src_rows[n]) for n in COPIED_ROW_FILES),
                        *((n, src_records[n][1]) for n in COPIED_RECORD_FILES)]:
        absent = [r for r in roots if r not in table]
        if absent:
            raise ValueError(f"dev_release_v3 {name} does not carry every E13a root: {absent}")

    tasks = [src_rows["tasks.jsonl"][r][1] for r in roots]
    specs = [src_rows["private_specs.jsonl"][r][1] for r in roots]
    from experiments.landmark import grade  # lazy: import only, nothing is executed
    grade.validate_specs(tasks, specs)  # the copied five-root package must still satisfy the grading contract

    out_dir.mkdir(parents=True, exist_ok=False)
    for name in COPIED_ROW_FILES:
        payload = b"".join(src_rows[name][r][0] + b"\n" for r in roots)
        (out_dir / name).write_bytes(payload)
    for name in COPIED_RECORD_FILES:
        data, by_root = src_records[name]
        key = RECORD_LIST_KEY[name]
        (out_dir / name).write_text(_dump({**{k: v for k, v in data.items() if k != key},
                                           key: [by_root[r] for r in roots]}), encoding="utf-8")
    contract = grade.contract(specs)
    config = _read_json(source_dir / "config.json")
    config.update(dataset_sha256=digest(tasks), source_code_sha256=digest(source_hashes()),
                  grading_contract_sha256=digest(contract), max_calls=60, max_completion_tokens=30720,
                  max_seconds=480)
    # The underlying instrument's protocol_version describes the reused measurement/receiver contract.
    # The stage/manifest separately identifies E13a and its six draws; no request-shaping field changes.
    (out_dir / "config.json").write_text(_dump(config), encoding="utf-8")
    from experiments.landmark import study_adapter as sa  # lazy: source hashes only
    written = _rows_by_root(out_dir / "private_specs.jsonl")  # the written rows must be the source rows, byte for byte
    for r in roots:
        if written[r][0] != src_rows["private_specs.jsonl"][r][0]:
            raise ValueError(f"written private spec row for {r} is not the frozen source line")
        if written[r][1]["private_assertions"] != src_rows["private_specs.jsonl"][r][1]["private_assertions"]:
            raise ValueError(f"private assertions changed for {r}")
    provenance = {r: {"tasks_row_sha256": digest(src_rows["tasks.jsonl"][r][1]),
                      "private_spec_row_sha256": digest(src_rows["private_specs.jsonl"][r][1]),
                      "public_examples_record_sha256": digest(src_records["public_examples_v3.json"][1][r]),
                      "controls_record_sha256": digest(src_records["controls_rationale.json"][1][r]),
                      "provisional_family_id": (src_manifest.get("provisional_families") or {}).get(r, "unknown")}
                  for r in roots}
    manifest = {
        "manifest": MANIFEST_ID,
        "status": ("PROPOSED BINDINGS for E13a. Not a release decision and not an execution authorization; "
                   "MRL-19 source/mock work only."),
        "evidence_class": stage["evidence_class"],
        "stage": {
            "stage": stage["stage"], "arm_set": stage["arm_set"], "arms": arms,
            "replicates_per_arm": {a: len(reps) for a, reps in arms.items()},
            "requests": n_requests, "branch_inclusion_probability": stage["branch_inclusion_probability"],
            "order_role": stage["order_role"], "primary_endpoint": stage["primary_endpoint"],
            "contrast": stage["contrast"], "not_a_test_of": stage["not_a_test_of"],
            "interpretation_rules": stage["interpretation_rules"],
            "descriptor_path": str(stage_path.relative_to(ROOT)), "descriptor_sha256": file_sha(stage_path),
        },
        "roots": roots,
        "n_roots": len(roots),
        "roots_order_note": stage["roots_order_note"],
        "authorization": {"receiver_calls_authorized": 0, "candidate_executions_authorized": 0,
                          "benchmark_executions_authorized": 0, "paid_usd_authorized": 0,
                          "statement": AUTHORIZATION_STATEMENT},
        "grading_limits": dict(GRADING_LIMITS),
        "limits_note": ("artifact_starts = 5 roots x 2 arms x 6 replicates; recheck_starts = 2 per root "
                        "(reference + negative control); containment_starts are containment-gate starts, not "
                        "analysis slots; max_private_starts = artifact + recheck + containment. Read with "
                        "study_adapter.load_grading_limits."),
        "package": {name: file_sha(out_dir / name) for name in PACKAGE_FILES},
        "grading_bindings": {
            "frozen_tasks_path": f"experiments/landmark/{RELEASE_DIRNAME}/tasks.jsonl",
            "frozen_tasks_sha256": file_sha(out_dir / "tasks.jsonl"),
            "expected_contract_sha256": digest(contract),
            "expected_config_sha256": digest(sa._strict((out_dir / "config.json").read_bytes())),
            "expected_source_hashes": sa.grading_source_hashes(),
        },
        "execution_source_hashes": {name: file_sha(ROOT / name) for name in EXECUTION_SOURCES},
        "source_release": {
            "dir": str(source_dir.relative_to(ROOT)), "manifest": src_manifest["manifest"],
            "manifest_sha256": file_sha(source_dir / "release_manifest.json"),
            "assignment_table_sha256": src_manifest["assignment_table_sha256"],
            "files": {name: file_sha(source_dir / name) for name in PACKAGE_FILES},
            "copy_rule": COPY_RULE, "row_provenance": provenance,
            "contract_note": src_manifest["contract_note"], "frame_review": src_manifest["frame_review"],
        },
        "e12_conditioning": {
            **e12,
            "gating_rule": stage["gating"]["rule"],
            "gating_source": stage["gating"]["source"],
            "canonical_function": stage["gating"]["canonical_function"],
            "private_grades_are_an_input": stage["gating"]["private_grades_are_an_input"],
            "pooling": "no pooling with E12",
        },
        "request_plan": {"path": str(plan_path.relative_to(ROOT)), "sha256": file_sha(plan_path),
                         "plan_version": plan["plan_version"]},
        "model": src_manifest["model"],
        "evaluator": {"grader_version": grade.GRADER_VERSION, "endpoint": contract["version"],
                      "diagnostic_schema": DIAGNOSTIC_SCHEMA},
        "diagnostic_schema": DIAGNOSTIC_SCHEMA,
        "seed_schedule": {**src_manifest["seed_schedule"],
                          "e13a_seed_note": ("E13a seeds are the request plan's noncolliding seeds; no new seed "
                                             "equals any seed E12 used for the same root")},
        "builder": {"script": "scripts/build_e13a_release.py", "script_sha256": file_sha(__file__),
                    "deterministic": True,
                    "rebuild_command": ".venv/bin/python scripts/build_e13a_release.py --verify"},
    }
    (out_dir / "release_manifest.json").write_text(_dump(manifest), encoding="utf-8")
    return manifest


def verify(out_dir, **kw):
    """Rebuild into a temporary directory and compare every byte with the committed release."""
    out_dir = Path(out_dir)
    if not out_dir.is_dir():
        raise SystemExit(f"nothing to verify: {out_dir} does not exist")
    with tempfile.TemporaryDirectory() as tmp:
        fresh = Path(tmp) / RELEASE_DIRNAME
        build(fresh, **kw)
        names = sorted(p.name for p in fresh.iterdir())
        committed = sorted(p.name for p in out_dir.iterdir())
        if names != committed:
            raise SystemExit(f"rebuild file set differs: rebuilt {names} vs committed {committed}")
        bad = [n for n in names if (fresh / n).read_bytes() != (out_dir / n).read_bytes()]
        if bad:
            raise SystemExit(f"rebuild differs from the committed bytes: {bad}")
    return {"verified": True, "dir": str(out_dir), "files": names}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", default=str(ROOT / DEFAULT_OUT))
    p.add_argument("--source", default=str(ROOT / DEFAULT_SOURCE))
    p.add_argument("--stage", default=str(ROOT / DEFAULT_STAGE))
    p.add_argument("--plan", default=str(ROOT / DEFAULT_PLAN))
    p.add_argument("--run", default=str(ROOT / DEFAULT_RUN))
    p.add_argument("--verify", action="store_true", help="rebuild into a temp dir and diff the committed bytes")
    a = p.parse_args(argv)
    kw = dict(source_dir=a.source, stage_path=a.stage, plan_path=a.plan, run_dir=a.run)
    result = verify(a.out, **kw) if a.verify else {"built": str(a.out), **{"roots": build(a.out, **kw)["roots"]}}
    print(json.dumps(result, indent=1))
    return result


if __name__ == "__main__":
    main()
