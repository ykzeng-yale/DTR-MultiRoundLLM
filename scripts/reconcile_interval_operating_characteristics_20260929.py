#!/usr/bin/env python3
"""Lead reconciliation of the frozen synthetic interval operating-characteristics run."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def audit(plan_path, summary_path, cells_path):
    plan_path, summary_path, cells_path = map(Path, (plan_path, summary_path, cells_path))
    plan, summary = json.loads(plan_path.read_text()), json.loads(summary_path.read_text())
    cells = [json.loads(line) for line in cells_path.read_text().splitlines() if line]
    assert summary["plan_sha256"] == sha(plan_path)
    assert summary["runner_sha256"] == plan["runner_sha256"] == sha(plan["runner"])
    assert summary["inference_sha256"] == plan["inference_sha256"] == sha(plan["inference_module"])
    if "parent_plan_sha256" in plan:
        assert plan["parent_plan_sha256"] == sha("experiments/prompt_choice/interval_operating_characteristics_plan_20260929.json")
    assert summary["cells_sha256"] == sha(cells_path)
    assert cells == summary["rows"]
    expected = [(s, n) for s in plan["scenarios"] for n in plan["family_counts"]]
    assert len(cells) == len(expected) == summary["completed_cells"] == 42
    assert len({(r["scenario_index"],r["n_families"]) for r in cells}) == len(cells)
    assert sum(r["replicates"] for r in cells) == plan["total_assigned_replicates"] == 840000
    max_mcse_error = 0.0
    for row, (scenario, n) in zip(cells, expected):
        assert row["scenario"] == scenario["name"]
        assert row["scenario_index"] == scenario["scenario_index"] and row["n_families"] == n
        assert row["truth"]["d_minus_b1"] == scenario["truth_d_minus_b1"]
        assert row["truth"]["d_minus_b2"] == scenario["truth_d_minus_b2"]
        assert row["replicates"] == plan["replicates_per_cell"] == 20000
        assert row["seed"] == plan["base_seed"] + 10000*scenario["scenario_index"] + n
        for method in ("sign_split_kl", "hoeffding_sensitivity"):
            obj = row[method]
            for rate in [obj["simultaneous_coverage"], *obj["decisions"].values()]:
                p = rate["estimate"]
                assert 0 <= p <= 1
                count_float = p * row["replicates"]
                count = round(count_float)
                assert abs(count_float-count) < 1e-7
                mcse = math.sqrt((count/row["replicates"])*(1-count/row["replicates"])/row["replicates"])
                max_mcse_error = max(max_mcse_error, abs(mcse-rate["mcse"]))
        assert all(row["sign_split_kl"]["mean_width"][j] < row["hoeffding_sensitivity"]["mean_width"][j]
                   for j in ("d_minus_b1", "d_minus_b2"))
    assert max_mcse_error < 1e-14
    min_kl = min(r["sign_split_kl"]["simultaneous_coverage"]["estimate"] for r in cells)
    min_h = min(r["hoeffding_sensitivity"]["simultaneous_coverage"]["estimate"] for r in cells)
    gain = next(r for r in cells if r["scenario"] == "gain-010" and r["n_families"] == 198)
    loss = next(r for r in cells if r["scenario"] == "loss-005" and r["n_families"] == 198)
    boundary = [r for r in cells if r["scenario"].startswith("gain-005-")]
    audit_doc = {
        "evidence_class": "lead reconciliation of synthetic Monte Carlo aggregates; not independent review",
        "plan_sha256": sha(plan_path), "summary_sha256": sha(summary_path), "cell_journal_sha256": sha(cells_path),
        "runner_sha256": sha(plan["runner"]), "inference_sha256": sha(plan["inference_module"]),
        "assigned_replicates": plan["total_assigned_replicates"], "reconciled_replicates": sum(r["replicates"] for r in cells),
        "cells_expected_completed": [42, len(cells)], "unique_scenario_size_cells": len(set((r["scenario_index"],r["n_families"]) for r in cells)),
        "maximum_mcse_recalculation_error": max_mcse_error,
        "all_42_cells_kl_narrower_than_hoeffding_on_both_contrasts": True,
        "simultaneous_coverage": {
            "sign_split_kl_minimum": min_kl,
            "sign_split_kl_minimum_cell_mcse": max(r["sign_split_kl"]["simultaneous_coverage"]["mcse"] for r in cells if r["sign_split_kl"]["simultaneous_coverage"]["estimate"] == min_kl),
            "hoeffding_minimum": min_h
        },
        "conditional_decision_examples": {
            "gain_010_at_n198": {"truth": gain["truth"], "probability_KL_L1_gt_005": gain["sign_split_kl"]["decisions"]["useful1"]},
            "loss_005_at_n198": {"truth": loss["truth"], "probability_KL_U1_lt_005": loss["sign_split_kl"]["decisions"]["futile1"]},
            "gain_005_boundary_all_sizes": [{"n": r["n_families"], "probability_KL_L1_gt_005": r["sign_split_kl"]["decisions"]["useful1"]} for r in boundary]
        },
        "run_accounting": summary["accounting"],
        "limits": ["coverage estimates are Monte Carlo checks under the stipulated IID laws, not theorem proof", "no actual task-family law or MBPP population is represented", "do not call decision rates power or use them to select a sample size", "no efficacy or policy comparison was run"]
    }
    return audit_doc


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan", required=True, type=Path)
    p.add_argument("--summary", required=True, type=Path)
    p.add_argument("--cells", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError("reconciliation output must be new")
    result = audit(a.plan,a.summary,a.cells)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"replicates":result["reconciled_replicates"],"cells":result["unique_scenario_size_cells"],
                      "min_kl_coverage":result["simultaneous_coverage"]["sign_split_kl_minimum"]},sort_keys=True))


if __name__ == "__main__":
    main()
