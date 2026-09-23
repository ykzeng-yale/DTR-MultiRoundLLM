#!/usr/bin/env python3
"""LEAD-CORRECTED post-hoc STATIC description of the immutable E13a outputs (v2).

Evidence class: post-hoc, static, descriptive. Zero executions -- no receiver, no candidate, no reference,
no containment. Saved output text is read, passed through the frozen extraction rule and `ast.parse`, and
counted. Nothing here regrades, reweights or replaces the frozen E13a endpoint, and the v1 script and its
v1 JSON are preserved untouched as evidence (their hashes are recorded below).

This version exists to correct three v1 overreads, per the lead's binding judgment
(docs/e13a_lead_judgment_20260923.md):

  1. v1 reported a single lumped count of 13 "static failures" for R1, which the prose then read as
     "13 extractor rejections". The correct split is ONE extraction rejection PLUS 12 Python-AST
     failures; this version separates EXTRACTION from AST per cell and in total.
  2. v1 labelled all-0 and all-1 cells "floor" and "ceiling", which the prose then read as structural
     limits (including that mbpp/652 "can express nothing"). These are OBSERVED saturation only.
  3. v1's inertness evidence counted cells with more than one distinct output text, which the prose then
     read as a discriminating semantic instrument. Distinct texts are not varying binary outcomes.

What this file still does NOT do, by construction: it identifies no mediation, recovers no latent semantic
success, quantifies no share of the -0.100 observed difference as format-caused, and computes no
parseability-conditioned contrast (that would condition on a property realised after the continuation --
post-treatment selection, not a causal contrast).
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.landmark.grade import extract_code  # noqa: E402

RUN = ROOT / "results/e13a_two_arm_20260923T061500Z"
V1_JSON = ROOT / "results/e13a_static_description_20260923.json"
V1_SCRIPT = ROOT / "scripts/e13a_static_description.py"
LEAD_JUDGMENT = ROOT / "docs/e13a_lead_judgment_20260923.md"
ARMS = ("R1", "FRESH")
VERSION = "e13a-static-description-v2-lead-corrected"
INPUT_FILES = ("collect/calls.jsonl", "grade/grades.jsonl", "analysis_report.json")

# A saved output that echoes the public diagnostic report back instead of emitting a program. Detected
# textually so the claim "the saved failures include diagnostic-report echoes" is checkable, not asserted.
ECHO_MARKERS = ("public diagnostic report", "public-diagnostic-v")

CHANGELOG = [
    {
        "v1_claim": "R1 had 13 'static failures' under the frozen extraction rule (one lumped count).",
        "correction": ("ONE extraction rejection plus 12 Python-AST failures. Extraction and ast.parse are "
                       "reported separately here, per cell and in total."),
        "why_it_mattered": ("the lumped count was read in prose as '13 extractor rejections', which suggests "
                            "correct programs rejected cosmetically. The saved failures include "
                            "diagnostic-report echoes and are not shown to be correct solutions."),
    },
    {
        "v1_claim": "cells were labelled saturation 'floor' / 'ceiling'.",
        "correction": ("observed saturation only: 'all observed scores 0' / 'all observed scores 1'. No "
                       "structural floor or ceiling is claimed. In particular mbpp/652's observed tie does "
                       "NOT imply that checkpoint can never express a difference."),
        "why_it_mattered": "the prose read the labels as limits on what the checkpoint could ever show.",
    },
    {
        "v1_claim": ("instrument evidence counted 10 cells with more than one distinct output text, reported "
                     "alongside 'the instrument is not inert'."),
        "correction": ("distinct output TEXTS are not varying binary outcomes and do not establish a "
                       "discriminating semantic instrument. Cells whose observed SCORES vary are counted "
                       "separately, and the only claim made is that the saved score is not constant on all "
                       "outputs."),
        "why_it_mattered": "text distinctness was overread as semantic discrimination.",
    },
]

DEFINITIONS = {
    "extraction_rejection": ("the frozen extraction rule (experiments.landmark.grade.extract_code) raised on "
                             "the saved output text, so no candidate program was recovered."),
    "ast_failure": ("extraction returned text but ast.parse rejected it: no parseable Python module. Counted "
                    "separately from extraction rejections."),
    "extractable_and_parseable": "extract_code returned text AND ast.parse accepted it. A static property of the text only.",
    "observed_saturation": ("all observed scores in that cell are 0, or all are 1. OBSERVED only: this is not a "
                            "structural floor or ceiling and does not bound what the checkpoint could express."),
    "cells_with_varying_observed_score": ("cells whose six observed binary scores are not all equal. This is the "
                                          "only instrument statement supported: the saved score is not constant "
                                          "on all outputs."),
    "distinct_output_texts": ("count of distinct output_sha256 values in the cell. TEXTUAL distinctness; it does "
                              "NOT imply a varying binary outcome or a discriminating semantic instrument."),
    "leave_one_out": ("the equally weighted mean recomputed with one checkpoint removed. Dropping a checkpoint "
                      "CHANGES THE TARGET; it is not a corrected estimate of the declared five-checkpoint target."),
}

NO_MEDIATION = ("This description identifies no mediation. It locates where the observed zeros occur and "
                "quantifies no share of the -0.100 observed equally weighted difference as caused by output "
                "format. It recovers no latent semantic success: the extraction/AST failures are not shown to "
                "be correct solutions rejected cosmetically.")

NO_STRUCTURAL_CLAIM = ("Saturation reported here is OBSERVED saturation over six draws. No structural floor or "
                       "ceiling is claimed for any checkpoint or arm; mbpp/652's observed tie does not imply it "
                       "can never express a difference.")

CONDITIONAL_CONTRAST_REFUSED = ("A pass rate computed among extractable-and-parseable outputs only would "
                                "condition on a property realised AFTER the continuation was produced. That is "
                                "post-treatment selection, not a causal contrast, so it is deliberately not "
                                "computed here -- in v1 and again in v2.")


def _jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def classify_output(text):
    """Static validity class of one saved output: extraction rejection, AST failure, or parseable."""
    if not isinstance(text, str):
        return {"validity": "output_missing", "echoes_diagnostic_report": False, "toplevel_functions": []}
    echo = any(marker in text.lower() for marker in ECHO_MARKERS)
    try:
        code = extract_code(text)
    except Exception:
        return {"validity": "extraction_rejection", "echoes_diagnostic_report": echo, "toplevel_functions": []}
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, TypeError):
        return {"validity": "ast_failure", "echoes_diagnostic_report": echo, "toplevel_functions": []}
    return {
        "validity": "extractable_and_parseable",
        "echoes_diagnostic_report": echo,
        "toplevel_functions": [n.name for n in tree.body if isinstance(n, ast.FunctionDef)],
    }


def build(run=RUN):
    calls = {(c["root_id"], c["arm"], c["replicate"]): c for c in _jsonl(run / "collect/calls.jsonl")}
    grades = _jsonl(run / "grade/grades.jsonl")
    report = json.loads((run / "analysis_report.json").read_text())
    checkpoints = report["finite_checkpoint_contrast"]["checkpoints"]
    roots = [c["root_id"] if isinstance(c, dict) else c for c in checkpoints]
    entries = {c["root_id"]: c["entry_point"] for c in json.loads(
        (ROOT / "experiments/landmark/e13a_release/public_examples_v3.json").read_text())["cases"]}

    cells, per_root_diff = {}, {}
    partition = {arm: {"primary_score_success": 0, "extraction_or_ast_failure": 0,
                       "extractable_parseable_primary_score_failure": 0} for arm in ARMS}
    totals = {arm: {"outputs": 0, "extraction_rejections": 0, "ast_failures": 0, "output_missing": 0,
                    "extractable_and_parseable": 0, "failures_echoing_diagnostic_report": 0} for arm in ARMS}

    for root in roots:
        entry = entries[root]
        cells[root] = {}
        for arm in ARMS:
            rows = sorted((g for g in grades if g["root_id"] == root and g["arm"] == arm),
                          key=lambda g: g["replicate"])
            outcomes = [g["outcome"] for g in rows if g["outcome"] is not None]
            counts = {"extraction_rejection": 0, "ast_failure": 0, "output_missing": 0,
                      "extractable_and_parseable": 0}
            echoing, digests, defines_entry = 0, set(), 0
            for g in rows:
                call = calls[(root, arm, g["replicate"])]
                digests.add(call.get("output_sha256"))
                info = classify_output(call.get("output"))
                counts[info["validity"]] += 1
                if info["validity"] == "extractable_and_parseable":
                    defines_entry += entry in info["toplevel_functions"]
                else:
                    echoing += info["echoes_diagnostic_report"]
                    # a non-recoverable output cannot have earned a passing score
                    assert g["outcome"] == 0, (root, arm, g["replicate"], g["outcome"])
                    partition[arm]["extraction_or_ast_failure"] += 1
                    continue
                if g["outcome"] == 1:
                    partition[arm]["primary_score_success"] += 1
                else:
                    partition[arm]["extractable_parseable_primary_score_failure"] += 1
            totals[arm]["outputs"] += len(rows)
            totals[arm]["extraction_rejections"] += counts["extraction_rejection"]
            totals[arm]["ast_failures"] += counts["ast_failure"]
            totals[arm]["output_missing"] += counts["output_missing"]
            totals[arm]["extractable_and_parseable"] += counts["extractable_and_parseable"]
            totals[arm]["failures_echoing_diagnostic_report"] += echoing
            cells[root][arm] = {
                "entry_point": entry,
                "assigned": len(rows),
                "graded": len(outcomes),
                "passes": sum(outcomes),
                "observed_mean": (sum(outcomes) / len(outcomes)) if outcomes else None,
                "extraction_rejections": counts["extraction_rejection"],
                "ast_failures": counts["ast_failure"],
                "output_missing": counts["output_missing"],
                "extractable_and_parseable": counts["extractable_and_parseable"],
                "defines_entry_point": defines_entry,
                "failures_echoing_diagnostic_report": echoing,
                "distinct_output_texts": len(digests),
                "observed_saturation": ("all_observed_scores_0" if outcomes and not any(outcomes)
                                        else "all_observed_scores_1" if outcomes and all(outcomes)
                                        else "not_saturated"),
                "observed_score_varies": bool(outcomes) and len(set(outcomes)) > 1,
            }
        per_root_diff[root] = cells[root]["R1"]["observed_mean"] - cells[root]["FRESH"]["observed_mean"]

    mean = sum(per_root_diff.values()) / len(per_root_diff)
    loo = {drop: (sum(v for r, v in per_root_diff.items() if r != drop) / (len(per_root_diff) - 1))
           for drop in per_root_diff}

    # internal invariants: the partition must be mutually exclusive and exhaustive over all 30 slots per arm
    for arm in ARMS:
        assert sum(partition[arm].values()) == 30, (arm, partition[arm])
        assert totals[arm]["outputs"] == 30, (arm, totals[arm])
        assert (partition[arm]["extraction_or_ast_failure"]
                == totals[arm]["extraction_rejections"] + totals[arm]["ast_failures"]
                + totals[arm]["output_missing"]), (arm, partition[arm], totals[arm])
    assert sum(p["primary_score_success"] for p in partition.values()) == 21

    all_outcomes = [g["outcome"] for g in grades if g["outcome"] is not None]
    return {
        "analysis_version": VERSION,
        "supersedes": {
            "analysis_version": "e13a-static-description-v1",
            "json": str(V1_JSON.relative_to(ROOT)),
            "script": str(V1_SCRIPT.relative_to(ROOT)),
            "note": ("v1 output and script are PRESERVED unedited as evidence; this file is an additive "
                     "derivative, not a regeneration."),
        },
        "evidence_class": ("post-hoc static description of immutable E13a saved outputs; 0 executions; not a "
                           "prespecified endpoint, not a regrade, not a mechanism or mediation result"),
        "authority": ("corrections required by the lead's binding judgment, "
                      + str(LEAD_JUDGMENT.relative_to(ROOT))),
        "run": Path(run).name,
        "inputs": {p: _sha256(Path(run) / p) for p in INPUT_FILES},
        "preserved_v1_inputs": {
            str(V1_JSON.relative_to(ROOT)): _sha256(V1_JSON),
            str(V1_SCRIPT.relative_to(ROOT)): _sha256(V1_SCRIPT),
            str(LEAD_JUDGMENT.relative_to(ROOT)): _sha256(LEAD_JUDGMENT),
        },
        "changelog_against_v1": CHANGELOG,
        "metric_definitions": DEFINITIONS,
        "output_validity_by_arm": totals,
        "output_validity_split_statement": (
            "R1: {er} extraction rejection(s) plus {af} Python-AST failure(s). "
            "FRESH: {fer} extraction rejection(s) plus {faf} Python-AST failure(s). These are distinct "
            "classes and were lumped as one count in v1."
        ).format(er=totals["R1"]["extraction_rejections"], af=totals["R1"]["ast_failures"],
                 fer=totals["FRESH"]["extraction_rejections"], faf=totals["FRESH"]["ast_failures"]),
        "all_assigned_partition": {
            "rows": [
                {"joint_recorded_outcome": "primary-score success",
                 "R1": partition["R1"]["primary_score_success"],
                 "FRESH": partition["FRESH"]["primary_score_success"]},
                {"joint_recorded_outcome": "extraction or AST failure",
                 "R1": partition["R1"]["extraction_or_ast_failure"],
                 "FRESH": partition["FRESH"]["extraction_or_ast_failure"]},
                {"joint_recorded_outcome": "extractable, AST-parseable primary-score failure",
                 "R1": partition["R1"]["extractable_parseable_primary_score_failure"],
                 "FRESH": partition["FRESH"]["extractable_parseable_primary_score_failure"]},
            ],
            "denominator_per_arm": 30,
            "mutually_exclusive_and_exhaustive": True,
            "disclaimer": NO_MEDIATION,
        },
        "per_checkpoint": cells,
        "per_checkpoint_observed_difference": per_root_diff,
        "equally_weighted_mean_observed_difference": mean,
        "leave_one_out": {
            "mean_with_one_checkpoint_removed": loo,
            "sign_differs_from_declared_target": [r for r, v in loo.items() if (v >= 0) != (mean >= 0)],
            "statement": ("Dropping a checkpoint CHANGES THE TARGET. The declared target is the equally "
                          "weighted contrast at exactly the five fixed checkpoints; a four-checkpoint mean is a "
                          "different quantity, not a corrected estimate of the declared one. Six draws do not "
                          "establish the sign of any checkpoint's response-mean difference."),
        },
        "observed_saturation": {
            "cells": {f"{r}:{a}": cells[r][a]["observed_saturation"] for r in cells for a in ARMS
                      if cells[r][a]["observed_saturation"] != "not_saturated"},
            "statement": NO_STRUCTURAL_CLAIM,
        },
        "instrument_statement": {
            "distinct_observed_scores": sorted(set(all_outcomes)),
            "cells_with_varying_observed_score": sum(1 for r in cells for a in ARMS
                                                     if cells[r][a]["observed_score_varies"]),
            "cells_with_more_than_one_distinct_output_text": sum(
                1 for r in cells for a in ARMS if cells[r][a]["distinct_output_texts"] > 1),
            "statement": ("Nonconstant observed scores establish only that the saved score is not constant on "
                          "all outputs. Cells with distinct output TEXTS do not imply varying binary-outcome "
                          "cells or a discriminating semantic instrument, and no such instrument is claimed."),
        },
        "post_treatment_selection": {
            "slots_assigned": sum(cells[r][a]["assigned"] for r in cells for a in ARMS),
            "slots_graded": sum(cells[r][a]["graded"] for r in cells for a in ARMS),
            "slots_dropped_after_continuation": 0,
            "conditional_contrast_refused": CONDITIONAL_CONTRAST_REFUSED,
        },
        "limits": [
            NO_MEDIATION,
            NO_STRUCTURAL_CLAIM,
            ("Thin private tests remain the endpoint; mbpp/863's known public defect is missed by its private "
             "assertions, so a passing score is not complete semantic correctness."),
            ("Costs are unequal across arms and no cost-efficiency advantage is established; see the lead "
             "judgment for the recorded token and second totals."),
        ],
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", type=Path, default=RUN)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.out.exists():
        raise SystemExit("Refusing to overwrite an existing description file")
    if args.out.resolve() == V1_JSON.resolve():
        raise SystemExit("Refusing to write over the preserved v1 description")
    out = build(args.run)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({
        "analysis_version": out["analysis_version"],
        "output_validity_split_statement": out["output_validity_split_statement"],
        "all_assigned_partition": out["all_assigned_partition"]["rows"],
        "equally_weighted_mean_observed_difference": out["equally_weighted_mean_observed_difference"],
        "observed_saturation": out["observed_saturation"]["cells"],
    }, indent=1))


if __name__ == "__main__":
    main()
