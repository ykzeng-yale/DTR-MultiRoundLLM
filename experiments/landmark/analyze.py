#!/usr/bin/env python3
"""Analyze immutable landmark outputs plus separately supplied offline grades.

This module never imports a sandbox, opens a model connection, or executes outputs.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path

try:
    from .collect import ARMS, digest, file_sha
except ImportError:
    from collect import ARMS, digest, file_sha

ALL_ARMS = ("stop", *ARMS)
CONTRASTS = (("history_specific_repair", "generic_repair"),
             ("generic_repair", "independent_restart"),
             ("history_specific_repair", "independent_restart"),
             *((arm, "stop") for arm in ARMS))
REPORTED_ENDPOINTS = len(ALL_ARMS) + len(CONTRASTS)


def bounded_family_interval(lower, upper, families, support, alpha=.05, allow=True):
    """Hoeffding reference interval for a fixed-weight independent-family target.

    Bounds enclose each complete-data root outcome, including missing slots.
    Independence is required across the TRUE families; it is not verified by IDs.
    Within-family dependence and missingness may be arbitrary. Family sizes and
    weights must be fixed before outcomes. This is not a random-size population
    ratio interval or a distribution-free certificate of benchmark generalization.
    """
    if not 0 < alpha < 1 or len(lower) != len(upper) or len(lower) != len(families):
        raise ValueError("Invalid confidence level or family-bound dimensions")
    lo, hi = support
    if not math.isfinite(lo) or not math.isfinite(hi) or lo >= hi:
        raise ValueError("Invalid bounded-outcome support")
    if any(not math.isfinite(l) or not math.isfinite(u) or not lo <= l <= u <= hi
           for l, u in zip(lower, upper)):
        raise ValueError("Completion bounds must lie in the declared support")
    counts = Counter(families)
    n = len(lower)
    sum_weights_squared = sum((size/n)**2 for size in counts.values()) if n else None
    radius = ((hi-lo) * math.sqrt(.5 * sum_weights_squared * math.log(2/alpha))) if n else None
    interval = None if not n or not allow else [max(lo, sum(lower)/n-radius), min(hi, sum(upper)/n+radius)]
    return {"method": "Hoeffding with fixed family weights and missing-outcome completion bounds",
            "alpha": alpha, "interval": interval, "radius": radius,
            "effective_families": None if not n else 1/sum_weights_squared,
            "target": "Expected equal-root mean for these prespecified family sizes and weights",
            "assumptions": "Independent complete-data family outcomes, fixed family weights and policies, well-defined bounded outcomes and valid measurement; family IDs alone do not verify independence",
            "scope": "Conditional on the declared sampling design/training; not arbitrary task-population transport or a random-family-size ratio target",
            "suppression_reason": None if interval is not None else "No assigned roots or receiver/collection identity gate failed"}


def paired_summary(values, families, allow_ci=True):
    """Equal-root mean; family-cluster sandwich, not independent-branch SE."""
    n = len(values)
    if n == 0:
        return {"n_roots": 0, "n_families": 0, "mean": None, "se": None, "ci95": None}
    mean = sum(values) / n
    clusters = defaultdict(float)
    for value, family in zip(values, families):
        clusters[family] += (value - mean) / n
    g = len(clusters)
    se = math.sqrt(g / (g - 1) * sum(x*x for x in clusters.values())) if g >= 2 and allow_ci else None
    return {"n_roots": n, "n_families": g, "mean": mean, "se": se,
            "ci95": None if se is None else [mean - 1.96*se, mean + 1.96*se],
            "interval_note": "Exploratory unadjusted normal family-cluster approximation; small-cluster coverage is not guaranteed, including when the estimated SE is zero" if se is not None else "No interval: insufficient independent families, incomplete assigned grades, or measurement gate failed"}


def analyze(run_dir, grade_path=None, split="all"):
    run_dir = Path(run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text())
    completion = json.loads((run_dir / "completion.json").read_text())
    for name, expected in completion["checksums"].items():
        if file_sha(run_dir / name) != expected:
            raise ValueError(f"Collection checksum mismatch: {name}")
    if digest(manifest["config"]) != manifest["config_sha256"]:
        raise ValueError("Config hash mismatch")
    rows = [json.loads(line) for line in (run_dir / "roots.jsonl").read_text().splitlines()]
    plan = manifest["assignment_table"]
    if digest(plan) != manifest["assignment_table_sha256"] or len(rows) != len(plan) or {r["root_id"] for r in rows} != {r["root_id"] for r in plan}:
        raise ValueError("Assignment accounting mismatch")
    if len({r["root_id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate collected roots")
    plan_by_root = {p["root_id"]: p for p in plan}
    for row in rows:
        p = plan_by_root[row["root_id"]]
        if any(row[k] != p[k] for k in p) or row["config_sha256"] != manifest["config_sha256"]:
            raise ValueError("Collected root changed its assignment")
        if not row["excluded"]:
            if set(row["arms"]) != set(ALL_ARMS):
                raise ValueError("Missing assigned arm")
            for arm in ALL_ARMS:
                expected_r = 1 if arm == "stop" else manifest["config"]["branch_replicates"]
                if [a["replicate"] for a in row["arms"][arm]] != list(range(expected_r)):
                    raise ValueError("Missing assigned replicate")
    eligible = {r["root_id"]: r for r in rows if not r["excluded"]}
    grades = {}
    label_by_artifact = {}
    if grade_path is not None:
        for line in Path(grade_path).read_text().splitlines():
            if not line.strip():
                continue
            grade = json.loads(line)
            required = {"root_id", "arm", "replicate", "output_sha256", "outcome", "missing_reason", "grader_id", "grading_contract_sha256"}
            if set(grade) != required:
                raise ValueError("Grade rows need the exact offline grade contract")
            key = (grade["root_id"], grade["arm"], grade["replicate"])
            if key in grades or key[0] not in eligible or key[1] not in ALL_ARMS:
                raise ValueError("Duplicate or unassigned grade")
            if type(key[2]) is not int or not 0 <= key[2] < len(eligible[key[0]]["arms"][key[1]]):
                raise ValueError("Unassigned graded replicate")
            artifact = eligible[key[0]]["arms"][key[1]][key[2]]
            if grade["output_sha256"] != artifact["output_sha256"]:
                raise ValueError("Grade does not match collected artifact")
            if grade["grading_contract_sha256"] != manifest["config"]["grading_contract_sha256"] or not grade["grader_id"]:
                raise ValueError("Grading contract is not the frozen contract")
            value = grade["outcome"]
            if value is not None and (type(value) not in (int, float) or value not in (0, 1) or artifact["output"] is None or grade["missing_reason"] is not None):
                raise ValueError("Invalid binary grade or grade of unavailable output")
            if value is None and not grade["missing_reason"]:
                raise ValueError("Missing outcome requires a reason")
            if value is not None:
                artifact_key = (key[0], artifact["output_sha256"])
                if artifact_key in label_by_artifact and label_by_artifact[artifact_key] != value:
                    raise ValueError("Identical root artifact has inconsistent frozen deterministic grades")
                label_by_artifact[artifact_key] = value
            grades[key] = grade
    chosen = [r for r in eligible.values() if split == "all" or r["split"] == split]
    gate = completion["model_metadata"].get("digest_unchanged") is True and completion["fatal_error"] is None
    # Mock intervals are arithmetic checks only, and never empirical inference.
    report = {"analysis_version": "landmark-analysis-v2", "evidence_type": manifest["evidence_type"], "config_sha256": manifest["config_sha256"],
        "collection_manifest_sha256": file_sha(run_dir / "manifest.json"),
        "grades_sha256": file_sha(grade_path) if grade_path is not None else None,
        "split": split, "assigned_roots": len(chosen), "excluded_roots": sum(r["excluded"] for r in rows),
        "receiver_identity_gate": gate, "quality": {}, "contrasts": {}, "realized_cost": {},
        "interpretation": "Frozen finite-prompt landmark comparison; no learned policy or full DTR-value claim. Complete-case estimates select a population when outcomes are missing. Completion bounds concern this realized run, not population confidence. Mock outcomes are not empirical evidence.",
        "finite_sample_reference_family": {"overall_alpha": .05, "number_of_fixed_endpoints": REPORTED_ENDPOINTS,
            "per_endpoint_alpha": .05/REPORTED_ENDPOINTS,
            "scope": "Bonferroni simultaneous reference intervals across these four arms and six contrasts only, under each stated fixed-weight independent-family model; repeated looks, selected policies and changed endpoints are not covered"}}

    def outcomes(row, arm):
        return [grades.get((row["root_id"], arm, a["replicate"]), {}).get("outcome") for a in row["arms"][arm]]

    def outcome(row, arm):
        values = outcomes(row, arm)
        return None if any(x is None for x in values) else sum(values)/len(values)

    def bounds(row, arm):
        values = outcomes(row, arm)
        known_sum = sum(v for v in values if v is not None)
        return known_sum/len(values), (known_sum+sum(v is None for v in values))/len(values)

    def reference_interval(root_bounds, support):
        return bounded_family_interval([v[0] for v in root_bounds], [v[1] for v in root_bounds],
                                       [r["family_id"] for r in chosen], support,
                                       alpha=.05/REPORTED_ENDPOINTS, allow=gate)

    for arm in ALL_ARMS:
        observed = [r for r in chosen if outcome(r, arm) is not None]
        missing = Counter()
        for row in chosen:
            for artifact in row["arms"][arm]:
                grade = grades.get((row["root_id"], arm, artifact["replicate"]), {})
                if grade.get("outcome") is None:
                    reason = grade.get("missing_reason") or artifact["missing_reason"] or "not_yet_graded"
                    missing[reason] += 1
        n = len(chosen)
        report["quality"][arm] = {"observed": paired_summary([outcome(r, arm) for r in observed], [r["family_id"] for r in observed], gate and len(observed) == len(chosen)),
            "missing_replicate_reasons": dict(missing), "all_assigned_mean_bounds": None if n == 0 else [sum(bounds(r, arm)[k] for r in chosen)/n for k in (0, 1)],
            "all_assigned_mean_bounds_scope": "Completion bounds for the realized assigned-root mean; not a population confidence interval",
            "finite_sample_reference": reference_interval([bounds(r, arm) for r in chosen], (0, 1))}
        costs = []
        for row in chosen:
            initial, replicates = row["initial"], row["arms"][arm]
            components = [(initial, 1.0)] if arm == "stop" else [(initial, 1.0), *((a, 1/len(replicates)) for a in replicates)]
            entry = {"root_id": row["root_id"], "family_id": row["family_id"],
                     "attempted_calls": sum(w*int(c["attempted"]) for c, w in components),
                     "seconds": sum(w*c["seconds"] for c, w in components)}
            for key in ("prompt_tokens", "completion_tokens"):
                entry[key] = None if any(c["attempted"] and c[key] is None for c, _ in components) else sum(w*(c[key] or 0) for c, w in components)
            costs.append(entry)
        report["realized_cost"][arm] = {"interpretation": "Initial call plus mean cost of one continuation, averaging replicates within root; actual collection total separately pays for all replicates. Failure and partial-collection costs are not completed-policy costs."}
        for key in ("attempted_calls", "seconds", "prompt_tokens", "completion_tokens"):
            valid = [c for c in costs if c[key] is not None]
            report["realized_cost"][arm][key] = {"mean_observed": None if not valid else sum(c[key] for c in valid)/len(valid), "known_roots": len(valid), "unknown_roots": len(costs)-len(valid)}
    for a, b in CONTRASTS:
        complete = [r for r in chosen if outcome(r, a) is not None and outcome(r, b) is not None]
        values = [outcome(r, a)-outcome(r, b) for r in complete]
        lower = upper = 0
        root_bounds = []
        for r in chosen:
            la, ua = bounds(r, a)
            lb, ub = bounds(r, b)
            lower += la-ub
            upper += ua-lb
            root_bounds.append((la-ub, ua-lb))
        report["contrasts"][a + "_minus_" + b] = {"complete_pairs": paired_summary(values, [r["family_id"] for r in complete], gate and len(complete) == len(chosen)),
             "missing_pair_roots": len(chosen)-len(complete), "all_assigned_mean_bounds": None if not chosen else [lower/len(chosen), upper/len(chosen)],
             "all_assigned_mean_bounds_scope": "Completion bounds for the realized assigned-root contrast; not a population confidence interval",
             "finite_sample_reference": reference_interval(root_bounds, (-1, 1))}
    report["actual_collection_cost"] = {k: completion[k] for k in ("attempted_calls", "reserved_completion_tokens", "measured_prompt_tokens", "measured_completion_tokens", "attempted_calls_with_unknown_usage", "wall_seconds", "paid_api_spend_usd")}
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--grades", type=Path)
    p.add_argument("--split", choices=("all", "train", "development", "test"), default="all")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    result = analyze(args.run, args.grades, args.split)
    with args.output.open("x") as f:
        f.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"evidence_type": result["evidence_type"], "assigned_roots": result["assigned_roots"], "output": str(args.output)}))


if __name__ == "__main__":
    main()
