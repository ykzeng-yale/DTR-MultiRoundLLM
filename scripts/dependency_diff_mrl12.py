#!/usr/bin/env python3
"""MRL-12 freeze hygiene: which validated evidence does a source change affect? Source-only; executes nothing.

Compares measurement-relevant files at the MRL-11 validated freeze (default 0bb2388) with the working tree, and
recomputes the attestation binding (sandbox source, profile, interpreter, host) the way scripts/check_landmark_sandbox.py
does, WITHOUT running any canary. Output: per-file old/new sha256, the gates whose evidence depends on each file, and
whether that evidence still applies unchanged.
"""
from __future__ import annotations
import argparse, hashlib, json, platform, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.landmark import sandbox  # noqa: E402  (imports only; sandbox_info() inspects, runs no payload)

DEPENDS = {  # file -> gates whose MRL-11 evidence relies on its exact bytes
    "experiments/landmark/sandbox.py": ["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8"],
    "scripts/check_landmark_sandbox.py": ["E1"],
    "experiments/landmark/public_check.py": ["E2", "E3", "E4", "E5", "E6", "E7"],
    "experiments/landmark/diagnostic.py": ["E3", "E4", "E5"],
    "experiments/landmark/public_instrument_validation.py": ["E2", "E6", "E7"],
    "experiments/landmark/public_instrument_items_v1.json": ["E2", "E6", "E7"],
    "experiments/landmark/validation_canaries.py": ["E3", "E4", "E5"],
    "experiments/landmark/validation_canaries_v1.json": ["E3", "E4", "E5"],
    "experiments/landmark/grade.py": ["E8"],
    "experiments/common/integrity.py": ["E3", "E8"],
    "experiments/landmark/validate_rebound_references.py": ["E8"],
    "experiments/landmark/dev_release_v2/private_specs.jsonl": ["E2", "E8"],
    # not measured by E1-E8; used only by E11 phases
    "experiments/landmark/collect.py": [], "experiments/landmark/collect_diagnostic.py": [],
    "experiments/landmark/public_phase.py": [], "experiments/landmark/study_adapter.py": [],
    "experiments/landmark/analyze_diagnostic.py": [],
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="0bb2388")
    ap.add_argument("--attestation", default="results/validation_bundle_v2_20260921T201642Z/attestation/attestation.json")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit("Refusing to overwrite")
    rows, affected = [], set()
    for f, gates in DEPENDS.items():
        old = subprocess.run(["git", "show", f"{a.base}:{f}"], cwd=ROOT, capture_output=True)
        old_sha = sha(old.stdout) if old.returncode == 0 else None
        new_sha = sha((ROOT / f).read_bytes()) if (ROOT / f).exists() else None
        changed = old_sha != new_sha
        if changed:
            affected.update(gates)
        rows.append({"file": f, "sha256_at_base": old_sha, "sha256_now": new_sha, "changed": changed, "evidence_gates": gates})
    att = json.loads((ROOT / a.attestation).read_text())
    info = sandbox.sandbox_info()
    now = {"sandbox_sha256": sha((ROOT / "experiments/landmark/sandbox.py").read_bytes()), "profile_sha256": info["profile_sha256"],
           "python": info["python"], "python_sha256": sha(info["python"].encode()) if isinstance(info["python"], str) else None,
           "host_sha256": sha(platform.node().encode()), "platform": platform.platform(), "sandbox_kind": info["kind"]}
    recorded = att["binding"]
    binding_match = {k: recorded.get(k) == v for k, v in now.items() if k != "python_sha256"}
    out = {"schema": "mrl12-dependency-diff-v1", "base": a.base, "files": rows,
           "gates_whose_evidence_is_affected": sorted(affected),
           "attestation": {"path": a.attestation, "checked_at": att.get("checked_at"), "binding_recorded": recorded,
                           "binding_now": now, "binding_fields_match": binding_match,
                           "reusable_if_unexpired": all(binding_match.values())},
           "evidence_class": "source hash comparison; no canary, reference, candidate or model executed"}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"changed": [r["file"] for r in rows if r["changed"]], "affected_gates": sorted(affected),
                      "attestation_binding_match": binding_match}, indent=1))


if __name__ == "__main__":
    main()
