#!/usr/bin/env python3
"""Run the frozen, source-free paired-family interval operating-characteristics study."""
from __future__ import annotations

import argparse
from decimal import Context, Decimal, ROUND_CEILING
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import random
import resource
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.prompt_choice.paired_inference import kl_interval


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def frac(value):
    return Fraction(value["num"], value["den"])


def exact_means(scenario):
    d1 = d2 = 0
    for row in scenario["support"]:
        yd, yb1, yb2 = row["outcomes"]
        d1 += row["mass"] * (yd - yb1)
        d2 += row["mass"] * (yd - yb2)
    if sum(row["mass"] for row in scenario["support"]) > 1000:
        raise ValueError("scenario support mass exceeds 1000")
    return Fraction(d1, 1000), Fraction(d2, 1000)


def prepare_support(scenario):
    rows = [(tuple(row["outcomes"]), row["mass"]) for row in scenario["support"]]
    used = sum(m for _, m in rows)
    if used < 1000:
        rows.append(((0, 0, 0), 1000 - used))
    if sum(m for _, m in rows) != 1000 or any(m <= 0 for _, m in rows):
        raise ValueError("invalid integer scenario masses")
    cumulative, acc = [], 0
    for outcomes, mass in rows:
        if len(outcomes) != 3 or any(type(y) is not int or y not in (0, 1) for y in outcomes):
            raise ValueError("outcomes must be binary triples")
        acc += mass
        cumulative.append((acc, outcomes))
    return cumulative


def draw_counts(rng, cumulative, n):
    p1 = q1 = p2 = q2 = 0
    for _ in range(n):
        x = rng.randrange(1000)
        for limit, (yd, yb1, yb2) in cumulative:
            if x < limit:
                d1, d2 = yd - yb1, yd - yb2
                p1 += d1 == 1
                q1 += d1 == -1
                p2 += d2 == 1
                q2 += d2 == -1
                break
    return p1, q1, p2, q2


def sign_split_interval(positive_count, negative_count, n, alpha, kl_cache):
    """Exact count-form of the paired_inference sign-split interval on {-1,0,1} data."""
    lp, up = kl_cache[(positive_count, n, alpha)]
    ln, un = kl_cache[(negative_count, n, alpha)]
    return max(Fraction(-1), lp - un), min(Fraction(1), up - ln)


def rate(successes, reps):
    p = successes / reps
    return {"estimate": p, "mcse": math.sqrt(p * (1 - p) / reps)}


def hoeffding_radius(n):
    """Outward 100-digit Decimal enclosure of sqrt(2*ln(80)/n), returned as an exact Fraction."""
    ctx = Context(prec=100, rounding=ROUND_CEILING)
    ln_hi = ctx.next_plus(ctx.ln(Decimal(80)))
    v_hi = ctx.divide(ctx.multiply(Decimal(2), ln_hi), Decimal(n), rounding=ROUND_CEILING)
    root_hi = ctx.next_plus(ctx.sqrt(v_hi))
    return Fraction(root_hi)


def summarize_cell(scenario, n, reps, base_seed, kl_cache):
    index = scenario["scenario_index"]
    seed = base_seed + 10000 * index + n
    rng = random.Random(seed)
    cumulative = prepare_support(scenario)
    truth1, truth2 = exact_means(scenario)
    alpha = Fraction(1, 20)
    for count in range(n + 1):
        key = (count, n, alpha)
        if key not in kl_cache:
            kl_cache[key] = kl_interval(Fraction(count, n), n, alpha)[:2]
    k_cover = h_cover = 0
    sums = {"kl_w1": 0.0, "kl_w2": 0.0, "h_w1": 0.0, "h_w2": 0.0}
    keys = ("useful1", "futile1", "superior2", "inferior2")
    decisions = {f"{method}_{key}": 0 for method in ("kl", "h") for key in keys}
    r_exact = hoeffding_radius(n)
    radius = float(r_exact)
    threshold = Fraction(1, 20)
    for _ in range(reps):
        p1, q1, p2, q2 = draw_counts(rng, cumulative, n)
        kl_l1, kl_u1 = sign_split_interval(p1, q1, n, alpha, kl_cache)
        kl_l2, kl_u2 = sign_split_interval(p2, q2, n, alpha, kl_cache)
        m1, m2 = Fraction(p1 - q1, n), Fraction(p2 - q2, n)
        h_l1, h_u1 = max(Fraction(-1), m1-r_exact), min(Fraction(1), m1+r_exact)
        h_l2, h_u2 = max(Fraction(-1), m2-r_exact), min(Fraction(1), m2+r_exact)
        k_cover += kl_l1 <= truth1 <= kl_u1 and kl_l2 <= truth2 <= kl_u2
        h_cover += h_l1 <= truth1 <= h_u1 and h_l2 <= truth2 <= h_u2
        sums["kl_w1"] += float(kl_u1-kl_l1)
        sums["kl_w2"] += float(kl_u2-kl_l2)
        sums["h_w1"] += float(h_u1-h_l1)
        sums["h_w2"] += float(h_u2-h_l2)
        decisions["kl_useful1"] += kl_l1 > threshold
        decisions["kl_futile1"] += kl_u1 < threshold
        decisions["kl_superior2"] += kl_l2 > 0
        decisions["kl_inferior2"] += kl_u2 < 0
        decisions["h_useful1"] += h_l1 > threshold
        decisions["h_futile1"] += h_u1 < threshold
        decisions["h_superior2"] += h_l2 > 0
        decisions["h_inferior2"] += h_u2 < 0
    return {
        "scenario": scenario["name"], "scenario_index": index, "n_families": n,
        "replicates": reps, "seed": seed,
        "truth": {"d_minus_b1": {"num": truth1.numerator, "den": truth1.denominator},
                  "d_minus_b2": {"num": truth2.numerator, "den": truth2.denominator}},
        "sign_split_kl": {
            "simultaneous_coverage": rate(k_cover, reps),
            "mean_width": {"d_minus_b1": sums["kl_w1"]/reps, "d_minus_b2": sums["kl_w2"]/reps},
            "decisions": {k.removeprefix("kl_"): rate(v, reps) for k,v in decisions.items() if k.startswith("kl_")},
        },
        "hoeffding_sensitivity": {
            "radius_before_clipping": radius,
            "simultaneous_coverage": rate(h_cover, reps),
            "mean_width": {"d_minus_b1": sums["h_w1"]/reps, "d_minus_b2": sums["h_w2"]/reps},
            "decisions": {k.removeprefix("h_"): rate(v, reps) for k,v in decisions.items() if k.startswith("h_")},
        },
    }


def run(plan_path: Path, out: Path):
    started = time.monotonic()
    plan = json.loads(plan_path.read_text())
    this_script = Path(__file__).resolve()
    inference = ROOT / plan["inference_module"]
    if sha(this_script) != plan["runner_sha256"]:
        raise ValueError("runner source hash differs from frozen plan")
    if sha(inference) != plan["inference_sha256"]:
        raise ValueError("inference module hash differs from frozen plan")
    if plan["status"] != "frozen_synthetic_operating_characteristics" or plan["model_calls"] != 0:
        raise ValueError("plan status or zero-call restriction invalid")
    if plan["alpha"] != "1/20" or plan["useful_gain_threshold"] != "1/20":
        raise ValueError("alpha or useful-gain threshold differs from the frozen contract")
    if plan["resource_caps"]["cpu_processes"] != 1 or plan["resource_caps"]["cpu_seconds"] != 590:
        raise ValueError("CPU envelope differs from frozen hard limit")
    if out.exists():
        raise FileExistsError("choose a fresh output directory; completed runs are immutable")
    out.mkdir(parents=True)
    scenarios = plan["scenarios"]
    for i, scenario in enumerate(scenarios):
        if scenario["scenario_index"] != i:
            raise ValueError("scenario order/index drift")
        means = exact_means(scenario)
        stated = (frac(scenario["truth_d_minus_b1"]), frac(scenario["truth_d_minus_b2"]))
        if means != stated:
            raise ValueError(f"scenario {scenario['name']} truth does not match support")
    assigned = len(scenarios) * len(plan["family_counts"]) * plan["replicates_per_cell"]
    cache, rows = {}, []
    journal = out / "cells.jsonl"
    with journal.open("x", encoding="utf-8") as jf:
        for scenario in scenarios:
            for n in plan["family_counts"]:
                if time.monotonic()-started > plan["internal_wall_cap_seconds"]:
                    raise TimeoutError("internal global cap reached; complete-cell journal preserved")
                row = summarize_cell(scenario, n, plan["replicates_per_cell"], plan["base_seed"], cache)
                rows.append(row)
                jf.write(json.dumps(row, sort_keys=True, separators=(",", ":"))+"\n")
                jf.flush()
    expected_cells = len(scenarios)*len(plan["family_counts"])
    if len(rows) != expected_cells or sum(r["replicates"] for r in rows) != assigned:
        raise ValueError("assignment coverage mismatch")
    elapsed = time.monotonic()-started
    summary = {
        "evidence_class": "lead-generated Monte Carlo under frozen hypothetical IID family laws",
        "plan_sha256": sha(plan_path), "runner_sha256": sha(this_script),
        "inference_sha256": sha(inference), "cells_sha256": sha(journal),
        "scenario_count": len(scenarios), "family_counts": plan["family_counts"],
        "replicates_per_cell": plan["replicates_per_cell"], "expected_replicates": assigned,
        "completed_cells": len(rows), "rows": rows,
        "accounting": {"model_calls": 0, "task_or_candidate_executions": 0,
                       "external_spend_usd": 0, "wall_seconds": elapsed,
                       "retained_bytes": journal.stat().st_size},
        "interpretation": "conditional synthetic operating characteristics only; not empirical MBPP precision, efficacy, or proof of real-family assumptions"
    }
    tmp = out / "summary.json.tmp"
    tmp.write_text(json.dumps(summary, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    os.replace(tmp, out / "summary.json")
    out_size = journal.stat().st_size+(out / "summary.json").stat().st_size
    if out_size > plan["output_cap_bytes"]:
        raise ValueError("retained output cap exceeded")
    return {"cells": len(rows), "replicates": assigned, "wall_seconds": elapsed, "output_bytes": out_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CPU, (590, 600))
    print(json.dumps(run(args.plan.resolve(), args.out.resolve()), sort_keys=True))


if __name__ == "__main__":
    main()
