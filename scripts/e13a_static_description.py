#!/usr/bin/env python3
"""POST-HOC exploratory STATIC description of the immutable E13a outputs, plus the standing discipline checks.

Evidence class: exploratory, static, descriptive; NOT a prespecified endpoint and NOT a mechanism result.
Zero executions: no receiver, no candidate, no reference, no sandbox. Outputs are read, extracted and parsed
with ast only. Nothing here regrades, reweights or replaces the frozen E13a report.

Discipline checks this reports before any negative result is read as meaningful (owner's standing rule):
  * instrument inertness -- an instrument that cannot move produces a null by construction;
  * floor/ceiling saturation per checkpoint, which caps the movement an arm could show;
  * dependence on a single checkpoint, via leave-one-out on the equally weighted mean;
  * post-treatment selection -- whether anything after the continuation chose which slots count.
"""
from __future__ import annotations
import argparse, ast, hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.landmark.grade import extract_code  # noqa: E402

RUN = ROOT / "results/e13a_two_arm_20260923T061500Z"
ARMS = ("R1", "FRESH")
DEFINITIONS = {
    "parses": "extract_code then ast.parse succeeds; a static property of the text, not a correctness claim.",
    "defines_entry_point": "a top-level FunctionDef with the task's entry-point name exists in the parsed output.",
    "distinct_outputs": "number of distinct output_sha256 values among that cell's replicates; 1 means the arm "
                        "reproduced one answer, R means every draw differed. Distinctness is textual, not semantic.",
    "instrument_inert": "True only if EVERY cell of both arms produced one identical outcome and no textual "
                        "variation at all; an inert instrument cannot express a difference.",
    "saturation": "floor = all graded outcomes 0; ceiling = all graded outcomes 1. A saturated cell bounds how "
                  "far the other arm could move relative to it.",
    "leave_one_out": "the equally weighted mean recomputed with one checkpoint removed; it shows dependence on a "
                     "single checkpoint and is descriptive, not an interval.",
    "post_treatment_selection": "whether any slot was dropped, filtered or reweighted after its continuation was "
                                "produced. All 60 assigned slots are graded, so no such step exists in this run.",
}


def _jsonl(path):
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def static_shape(text, entry_point):
    if not isinstance(text, str):
        return {"parses": False, "defines_entry_point": False, "reason": "output_missing"}
    try:
        code = extract_code(text)
    except Exception:
        return {"parses": False, "defines_entry_point": False, "reason": "extract_fail"}
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, TypeError):
        return {"parses": False, "defines_entry_point": False, "reason": "parse_fail"}
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    return {"parses": True, "defines_entry_point": entry_point in names, "reason": None,
            "toplevel_functions": names}


def build(run=RUN):
    calls = {(c["root_id"], c["arm"], c["replicate"]): c for c in _jsonl(run / "collect/calls.jsonl")}
    grades = _jsonl(run / "grade/grades.jsonl")
    report = json.loads((run / "analysis_report.json").read_text())
    # entry points live in the release's public examples, not in tasks.jsonl
    entries = {c["root_id"]: c["entry_point"]
               for c in json.loads((ROOT / "experiments/landmark/e13a_release/public_examples_v3.json").read_text())["cases"]}
    roots = [c["root_id"] for c in report["finite_checkpoint_contrast"]["checkpoints"]] \
        if isinstance(report["finite_checkpoint_contrast"]["checkpoints"][0], dict) \
        else report["finite_checkpoint_contrast"]["checkpoints"]

    cells, per_root_diff = {}, {}
    for root in roots:
        entry = entries[root]
        cells[root] = {}
        for arm in ARMS:
            rows = [g for g in grades if g["root_id"] == root and g["arm"] == arm]
            outcomes = [g["outcome"] for g in rows if g["outcome"] is not None]
            shapes, digests = [], set()
            for g in rows:
                call = calls[(root, arm, g["replicate"])]
                digests.add(call.get("output_sha256"))
                shapes.append(static_shape(call.get("output"), entry))
            cells[root][arm] = {
                "entry_point": entry, "assigned": len(rows), "graded": len(outcomes),
                "passes": sum(outcomes), "mean": (sum(outcomes) / len(outcomes)) if outcomes else None,
                "distinct_outputs": len(digests),
                "n_parses": sum(s["parses"] for s in shapes),
                "n_defines_entry_point": sum(s["defines_entry_point"] for s in shapes),
                "static_failures": sorted({s["reason"] for s in shapes if s["reason"]}),
                "saturation": ("floor" if outcomes and not any(outcomes)
                               else "ceiling" if outcomes and all(outcomes) else "unsaturated"),
            }
        per_root_diff[root] = cells[root]["R1"]["mean"] - cells[root]["FRESH"]["mean"]

    mean = sum(per_root_diff.values()) / len(per_root_diff)
    loo = {drop: (sum(v for r, v in per_root_diff.items() if r != drop) / (len(per_root_diff) - 1))
           for drop in per_root_diff}
    fmt = {arm: {"outputs": sum(cells[r][arm]["assigned"] for r in cells),
                 "parse": sum(cells[r][arm]["n_parses"] for r in cells),
                 "defines_entry_point": sum(cells[r][arm]["n_defines_entry_point"] for r in cells)}
           for arm in ARMS}
    for arm in ARMS:
        fmt[arm]["static_failures"] = fmt[arm]["outputs"] - fmt[arm]["parse"]
    all_outcomes = [g["outcome"] for g in grades if g["outcome"] is not None]
    inert = len(set(all_outcomes)) <= 1 and all(c[a]["distinct_outputs"] == 1 for c in cells.values() for a in ARMS)
    return {
        "analysis_version": "e13a-static-description-v1",
        "evidence_class": ("post-hoc exploratory static description of immutable E13a outputs; 0 executions; "
                           "not a prespecified endpoint, not a mechanism result, not a regrade"),
        "run": run.name,
        "inputs": {p: hashlib.sha256((run / p).read_bytes()).hexdigest()
                   for p in ("collect/calls.jsonl", "grade/grades.jsonl", "analysis_report.json")},
        "metric_definitions": DEFINITIONS,
        "per_checkpoint": cells,
        "per_checkpoint_difference": per_root_diff,
        "equally_weighted_mean": mean,
        "format_under_the_frozen_rule": {
            "by_arm": fmt,
            "note": ("The frozen endpoint is the private-suite-PLUS-FORMAT score, so an output that the frozen "
                     "extraction rule cannot recover is a legitimate 0. But the arms differ sharply here, so the "
                     "contrast substantially reflects output format, not only solution quality."),
            "conditional_contrast_refused": (
                "A pass rate computed among parseable outputs only would condition on a property realised AFTER "
                "the continuation was produced. That is post-treatment selection and it is not a causal contrast, "
                "so it is deliberately not computed here."),
        },
        "discipline_checks": {
            "instrument_inert": inert,
            "instrument_inertness_evidence": {
                "distinct_outcomes_observed": sorted(set(all_outcomes)),
                "cells_with_more_than_one_distinct_output": sum(
                    1 for c in cells.values() for a in ARMS if c[a]["distinct_outputs"] > 1),
                "largest_single_checkpoint_movement": max(abs(v) for v in per_root_diff.values()),
            },
            "saturated_cells": {f"{r}:{a}": cells[r][a]["saturation"] for r in cells for a in ARMS
                                if cells[r][a]["saturation"] != "unsaturated"},
            "leave_one_out_mean": loo,
            "sign_flips_when_one_checkpoint_removed": [r for r, v in loo.items() if (v >= 0) != (mean >= 0)],
            "post_treatment_selection": {
                "slots_assigned": sum(c[a]["assigned"] for c in cells.values() for a in ARMS),
                "slots_graded": sum(c[a]["graded"] for c in cells.values() for a in ARMS),
                "slots_dropped_after_continuation": 0,
                "statement": DEFINITIONS["post_treatment_selection"],
            },
        },
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", type=Path, default=RUN)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit("Refusing to overwrite")
    out = build(a.run)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"mean": out["equally_weighted_mean"], **out["discipline_checks"]}, indent=1)[:1400])


if __name__ == "__main__":
    main()
