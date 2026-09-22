#!/usr/bin/env python3
"""MRL-15: derive the separately versioned dev_release_v2_1 package from the immutable dev_release_v2.

Tasks and private specs are copied byte-for-byte (asserted). Only bindings that the grader/collector source
changes invalidate are recomputed: grading-contract digest, collector source hash, config digest and the J7
grading bindings. dev_release_v2 and the E11 evidence are never modified. Source-only; executes nothing.
"""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.landmark import collect, diagnostic, grade, study_adapter  # noqa: E402

V2 = ROOT / "experiments/landmark/dev_release_v2"
V21 = ROOT / "experiments/landmark/dev_release_v2_1"


def fsha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=V21)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit("Refusing to overwrite an existing package directory")
    a.out.mkdir(parents=True)
    for name in ("tasks.jsonl", "private_specs.jsonl"):
        (a.out / name).write_bytes((V2 / name).read_bytes())
        assert fsha(a.out / name) == fsha(V2 / name)
    tasks = [diagnostic.strict_json_loads(l) for l in (a.out / "tasks.jsonl").read_text().splitlines() if l.strip()]
    specs = [diagnostic.strict_json_loads(l) for l in (a.out / "private_specs.jsonl").read_text().splitlines() if l.strip()]
    grade.validate_specs(tasks, specs)
    cfg = json.loads((V2 / "config.json").read_text())
    old = {k: cfg[k] for k in ("protocol_version", "grading_contract_sha256", "source_code_sha256")}
    cfg["protocol_version"] = ("landmark-development-release-v2.1-diagnostic (v2 tasks/specs unchanged; grader "
                               f"{grade.GRADER_VERSION}; compile-validity gates with fault attribution)")
    cfg["grading_contract_sha256"] = grade.digest(grade.contract(specs))
    cfg["source_code_sha256"] = collect.digest(collect.source_hashes())
    collect.validate(cfg, tasks, real=True)
    (a.out / "config.json").write_text(json.dumps(cfg, indent=2) + "\n")
    v2m = json.loads((V2 / "release_manifest.json").read_text())
    m = {"manifest": "dev-release-v2.1-diagnostic", "status": "PREPARATION: v2.1 package; the 31-start targeted "
         "instrument check (MRL-15 conditional) runs against it; no model collection authorized",
         "derived_from": {"package": "experiments/landmark/dev_release_v2", "release_manifest_sha256": fsha(V2 / "release_manifest.json"),
                          "unchanged_bytes": ["tasks.jsonl", "private_specs.jsonl"]},
         "grader_version": grade.GRADER_VERSION, "changed_bindings": {"before": old,
         "after": {k: cfg[k] for k in old}},
         "roots": v2m["roots"],
         "package": {"tasks.jsonl": fsha(a.out / "tasks.jsonl"), "private_specs.jsonl": fsha(a.out / "private_specs.jsonl"),
                     "config.json": fsha(a.out / "config.json")},
         "grading_bindings": {"frozen_tasks_path": str((a.out / "tasks.jsonl").relative_to(ROOT)),
                              "frozen_tasks_sha256": fsha(a.out / "tasks.jsonl"),
                              "expected_contract_sha256": cfg["grading_contract_sha256"],
                              "expected_config_sha256": collect.digest(cfg),
                              "expected_source_hashes": study_adapter.grading_source_hashes()},
         "receiver": v2m["receiver"], "ownership": {"status": "a new, current owner agreement is required before any collection"},
         "e11_evidence": "bound to dev_release_v2 and grader v1 contract 0b49177c...; immutable; not rebound"}
    (a.out / "release_manifest.json").write_text(json.dumps(m, indent=1) + "\n")
    print(json.dumps({"out": str(a.out.relative_to(ROOT)), **m["changed_bindings"]["after"]}, indent=1))


if __name__ == "__main__":
    main()
