#!/usr/bin/env python3
"""Describe E12 N1/S1 grades by pre-continuation public status; no model or grader run."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results/e12_dev_v3_20260922T030255Z"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit("Refusing to overwrite saved audit")
    inputs = [BASE / "analysis_input.json", BASE / "B/diagnostics.json", BASE / "analysis_report.json"]
    input_sha256 = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    analysis, diagnostics, report = (json.loads(p.read_text()) for p in inputs)
    rows = []
    groups: dict[str, list[dict]] = defaultdict(list)
    for root in analysis["roots"]:
        rid = root["root_id"]
        cases = diagnostics[rid]["cases"]
        assert len(cases) == 1
        status = cases[0]["status"]
        arm = {}
        for name in ("N1", "S1"):
            grades = [rep["grade"] for rep in root["arms"][name]]
            assert len(grades) == 2 and all(type(x) is int and x in (0, 1) for x in grades)
            arm[name] = grades
        row = {"root_id": rid, "family_id": root["family_id"], "public_status": status,
               "N1_grades": arm["N1"], "S1_grades": arm["S1"],
               "S1_minus_N1_half_units": sum(arm["S1"]) - sum(arm["N1"])}
        rows.append(row)
        groups[status].append(row)
    assert len(rows) == 14 and len({r["root_id"] for r in rows}) == 14
    assert sum(r["S1_minus_N1_half_units"] for r in rows) == -1
    assert report["n_roots"] == 14 and report["n_families"] == 1
    report_differences = {r["root_id"]: r["value"] for r in report["contrasts"]["S1_minus_N1"]["per_root"]}
    assert all(r["S1_minus_N1_half_units"] / 2 == report_differences[r["root_id"]] for r in rows)
    summary = {}
    for status, group in sorted(groups.items()):
        diff = sum(r["S1_minus_N1_half_units"] for r in group)
        summary[status] = {"roots": len(group), "N1_passes": sum(sum(r["N1_grades"]) for r in group),
                           "S1_passes": sum(sum(r["S1_grades"]) for r in group),
                           "S1_minus_N1_half_units": diff,
                           "observed_mean_difference": diff / (2 * len(group))}
    assert report["initial_status"]["public_totals"] == {
        "all_pass": summary["pass"]["roots"], "any_fail": summary["wrong_value"]["roots"], "unknown": 0
    }
    result = {"audit_version": "e12-public-status-signal-v1",
              "evidence_class": "post-result reused E12 grades and public diagnostics; no new model or grader execution",
              "inputs_sha256": input_sha256, "rows": rows, "summary": summary,
              "overall_S1_minus_N1_half_units": -1, "overall_observed_mean_difference": -1 / 28,
              "family_limit": "All 14 roots carry one unresolved_development_family placeholder, not 14 independent families.",
              "interpretation_limit": "Public status is a pre-continuation feature; in-sample grouping is descriptive, with only two draws per arm and outcome-inspected development roots. No selector was fit or evaluated, and no conditional sign or policy benefit is established.",
              "model_calls": 0, "tokens": 0, "benchmark_program_executions": 0, "paid_usd": 0}
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"n_roots": len(rows), "summary": summary, "overall": -1 / 28}))


if __name__ == "__main__":
    main()
