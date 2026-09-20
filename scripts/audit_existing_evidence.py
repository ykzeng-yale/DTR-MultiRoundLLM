#!/usr/bin/env python3
"""Independent, CPU-only audit of archived G0e/G1a/E0 evidence.

Never calls a model or changes archived results. Default output must be empty.
The paired IPW repair comparison is exploratory reuse of the routing log, not a
new randomized head-to-head trial or a restored confirmatory holdout.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
from itertools import permutations
import json
from pathlib import Path
import shutil
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def summarize(values):
    values = np.asarray(values, float)
    mean = float(values.mean())
    se = float(values.std(ddof=1) / np.sqrt(len(values)))
    return {"n_tasks": len(values), "mean": mean, "se": se,
            "ci95": [mean - 1.96 * se, mean + 1.96 * se]}


def paired_summary(rows, left, right):
    """Always report component means and their paired difference on identical rows."""
    a, b = [r[left] for r in rows], [r[right] for r in rows]
    return {"left": summarize(a), "right": summarize(b),
            "difference": summarize(np.asarray(a) - b)}


def ordered_baseline(records, k):
    """Exact U statistic over all ordered distinct first-generation candidates."""
    if k > len(records) or k < 1:
        raise ValueError("k must fit the candidate pool")
    outcomes, calls, tokens = [], [], []
    for order in permutations(range(len(records)), k):
        cost = 0
        for position, index in enumerate(order):
            candidate = records[index]
            cost += candidate["tokens"]
            if candidate["visible"] or position == k - 1:
                outcomes.append(candidate["hidden"])
                calls.append(position + 1)
                tokens.append(cost)
                break
    return dict(success=float(np.mean(outcomes)), calls=float(np.mean(calls)),
                tokens=float(np.mean(tokens)))


def fixed_receiver_weight(decisions):
    """Target always uses the initial model; condition on first-model assignment."""
    model = decisions[0]["model_alias"]
    weight = 1.0
    for decision in decisions[1:]:
        propensity = decision.get("b_obs")
        if not isinstance(propensity, (int, float)) or not 0 < propensity <= 1:
            raise ValueError("invalid logged routing propensity")
        if decision["model_alias"] != model:
            return 0.0
        weight /= propensity
    return weight


def routing_audit(path):
    episodes = [json.loads(line) for line in path.open()]
    groups = defaultdict(list)
    retained = defaultdict(list)
    hashes = defaultdict(set)
    switched_counts = Counter()
    first_success = defaultdict(list)
    for episode in episodes:
        ds = episode.get("decisions", [])
        if not ds:
            raise ValueError("episode without initial decision")
        first = ds[0]
        visible = first["validation"].get("n_fail")
        if visible is None:
            raise ValueError("missing first visible check; cannot silently discard")
        key = episode["task_uid"], first["model_alias"]
        switched = len({d["model_alias"] for d in ds}) > 1
        weight = fixed_receiver_weight(ds)
        row = {"hidden": int(episode["success_first_candidate"]), "visible": bool(first["validation"]["passed"]),
               "tokens": first.get("completion_tokens", 0), "success": episode["success"],
               "calls": episode["n_decisions"], "total_tokens": episode["completion_tokens"],
               "fixed_weight": weight, "split": episode["split"], "switched": switched,
               "seed": episode["seed"]}
        groups[key].append(row)
        if not switched:
            retained[key].append(row)
        hashes[key].add(first.get("transcript_sha256"))
        switched_counts[(key[1], switched)] += 1
        first_success[(key[1], switched)].append(row["hidden"])
    original = json.loads((ROOT / "results/audits/g0e/20260920T003221Z/summary.json").read_text())
    original_paired = []
    for model, block in original["receivers"].items():
        for k in block["adaptive_bon"]:
            rows = [r for r in block["_per_task"] if k in r["bon"]]
            rec = {"model": model, "k": int(k), "n_tasks": len(rows),
                   "matched_mt_success": float(np.mean([r["mt_success"] for r in rows])),
                   "matched_mt_calls": float(np.mean([r["mt_calls"] for r in rows])),
                   "bon_success": float(np.mean([r["bon"][k]["success"] for r in rows])),
                   "bon_calls": float(np.mean([r["bon"][k]["calls"] for r in rows])),
                   "all_retained_mt_success": block["multi_turn"]["mean"],
                   "reported_paired_delta": block["paired_vs_multi_turn"][k]["delta_success"]}
            rec["matched_delta"] = rec["matched_mt_success"] - rec["bon_success"]
            original_paired.append(rec)
    comparisons, per_task = [], []
    for model in sorted({k[1] for k in groups}):
        items = [(key[0], records) for key, records in groups.items() if key[1] == model]
        for k in (2, 3, 4):
            rows = []
            for uid, records in items:
                bon = ordered_baseline(records, k)
                row = {"uid": uid, "model": model, "k": k, "n_initial_draws": len(records),
                       "single": float(np.mean([r["hidden"] for r in records])),
                       "multi_turn_fixed_ipw": float(np.mean([r["fixed_weight"] * r["success"] for r in records])),
                       "multi_turn_fixed_calls_ipw": float(np.mean([r["fixed_weight"] * r["calls"] for r in records])),
                       "multi_turn_fixed_tokens_ipw": float(np.mean([r["fixed_weight"] * r["total_tokens"] for r in records])),
                       "weight_mean": float(np.mean([r["fixed_weight"] for r in records])),
                       "bon": bon["success"], "bon_calls": bon["calls"], "bon_tokens": bon["tokens"],
                       "oracle_any_all_first": int(any(r["hidden"] for r in records)),
                       "split": records[0]["split"]}
                rows.append(row)
            comparisons.append({"model": model, "k": k,
                                "success": paired_summary(rows, "multi_turn_fixed_ipw", "bon"),
                                "calls": paired_summary(rows, "multi_turn_fixed_calls_ipw", "bon_calls"),
                                "completion_tokens": paired_summary(rows, "multi_turn_fixed_tokens_ipw", "bon_tokens"),
                                "single": summarize([r["single"] for r in rows]),
                                "weight_mean": summarize([r["weight_mean"] for r in rows]),
                                "unadjusted_upper_below_point01": paired_summary(rows, "multi_turn_fixed_ipw", "bon")["difference"]["ci95"][1] < .01})
            per_task.extend(rows)
    all_decisions=[d for episode in episodes for d in episode["decisions"]]
    weight_diagnostics={}
    for model in sorted({k[1] for k in groups}):
        weights=np.array([r["fixed_weight"] for (_,m),rows in groups.items() if m==model for r in rows])
        weight_diagnostics[model]={"max_weight":float(weights.max()),"sum_weight":float(weights.sum()),
                                   "sum_squared_weight":float(np.sum(weights**2)),
                                   "episode_weight_ess_diagnostic":float(weights.sum()**2/np.sum(weights**2)),
                                   "independent_task_count":sum(m==model for (_,m) in groups),
                                   "note":"Episode weight ESS is not the number of independent tasks."}
    return {"source": str(path), "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "episodes": len(episodes), "unique_episode_ids": len({e["episode_id"] for e in episodes}),
            "task_model_draw_count_distribution": dict(Counter(len(x) for x in groups.values())),
            "first_prompt_hashes_per_task_model": dict(Counter(len(x) for x in hashes.values())),
            "repeated_seed_cells": sum(len({r["seed"] for r in rs}) != len(rs) for rs in groups.values()),
            "splits": dict(Counter(e["split"] for e in episodes)),
            "integrity":{"episode_errors":sum(e.get("error") is not None for e in episodes),
                         "incomplete_decisions":sum(not d.get("completed") for d in all_decisions),
                         "mock_episodes":sum(bool(e.get("mock")) for e in episodes),
                         "routing_propensities":dict(Counter(str(d.get("b_obs")) for d in all_decisions)),
                         "routing_sources":dict(Counter(d.get("source") for d in all_decisions)),
                         "zero_visible_assertion_episodes":sum(e["n_visible_checks"]==0 for e in episodes),
                         "first_check_nfzero_disagrees_with_passed":sum((e["decisions"][0]["validation"]["n_fail"]==0)!=e["decisions"][0]["validation"]["passed"] for e in episodes),
                         "all_checks_nfzero_disagrees_with_passed":sum((d["validation"]["n_fail"]==0)!=d["validation"]["passed"] for d in all_decisions),
                         "source_metadata_hashes":{key:sorted({e.get(key) for e in episodes}) for key in ("config_sha256","code_sha256","tasks_sha256","visible_tests_sha256")}},
            "weight_diagnostics":weight_diagnostics,
            "selection": [{"model": m, "switched": s, "n": count,
                           "first_success": float(np.mean(first_success[(m, s)]))}
                          for (m, s), count in sorted(switched_counts.items())],
            "original_matched_cohorts": original_paired,
            "all_initial_candidates_exploratory_ipw_comparisons": comparisons}, per_task


def behavior_values(sim, kernel, behavior, horizon):
    values = np.zeros((horizon + 2, sim.NE, 2, sim.NS))
    values[horizon + 1] = np.arange(sim.NS) == 3
    for t in range(horizon, 0, -1):
        for e in range(sim.NE):
            for z in (0, 1):
                for s in range(sim.NS):
                    values[t, e, z, s] = sum(behavior[z, s, a] * ((s == 3) if a == 0 else kernel[e, z, s, a] @ values[t + 1, e, z]) for a in range(sim.K))
    return values


def exact_blip_limits(sim, cfg):
    kernel = sim.kernel(cfg["cmult"])
    behavior = sim.make_beh(cfg["kappa"], cfg["floor"], cfg["gz"])
    behavior_value = behavior_values(sim, kernel, behavior, cfg["T"])
    uniform_value = sim.Vtab(kernel, sim.UNIF5, cfg["T"])
    s = 1
    posterior = np.array([[sim.P_E[e] * (sim.P_Z if z else 1-sim.P_Z) * sim.p_s1(e)[s] for z in (0,1)] for e in range(sim.NE)])
    posterior /= posterior.sum()
    out = []
    for a in range(1, sim.K):
        selected_posterior = posterior * behavior[:, s, a][None, :]
        selected_posterior /= selected_posterior.sum()
        qu = np.array([[kernel[e,z,s,a] @ uniform_value[2,e,z] for z in (0,1)] for e in range(sim.NE)])
        qb = np.array([[kernel[e,z,s,a] @ behavior_value[2,e,z] for z in (0,1)] for e in range(sim.NE)])
        out.append({"arm": sim.ARMS[a], "uniform_continuation_truth": float(np.sum(posterior*qu)),
                    "conditional_raw_Y_limit_behavior_continuation": float(np.sum(selected_posterior*qb)),
                    "archived_blip_ipw_limit_missing_stage1_weight": float(np.sum(selected_posterior*qu))})
    return out


def template_kernel(sim, cfg, offsets):
    kernel = sim.kernel(cfg["cmult"])
    if offsets is None:
        return kernel
    offsets = np.asarray(offsets)
    for e in range(sim.NE):
        for z in (0,1):
            for s in range(sim.NS):
                for a in range(1,sim.K):
                    kernel[e,z,s,a] = np.mean([sim.p_ord(sim.MU[s]+cfg["cmult"]*(sim.TH[(sim.ARMS[a],s,z)]+offset)+sim.LAM*(sim.EASE_MID[e]-.5)) for offset in offsets[a]],axis=0)
    return kernel


def e0_recheck(reps, snapshot):
    snapshot.mkdir()
    for name in ("simulator.py","estimators.py","run_grid.py"):
        shutil.copyfile(ROOT/"experiments/e0"/name,snapshot/name)
    sys.path.insert(0, str(snapshot))
    import simulator as sim
    import estimators as est
    import run_grid as grid
    rows, cells = [], {}
    for ci,name in enumerate(("base", "FAIL_latent", "FAIL_coarsening")):
        cfg = grid.CELLS[name]
        nominal = sim.true_value(sim.kernel(cfg["cmult"]),sim.UNIF5,cfg["T"])
        for rep in range(reps):
            seed = 2026092000 + 10000*ci + rep
            rng = np.random.default_rng(seed)
            d = sim.simulate(cfg["n_tasks"], cfg["runs"], cfg["T"], sim.kernel(cfg["cmult"]), sim.make_beh(cfg["kappa"],cfg["floor"],cfg["gz"]),rng,mislabel=cfg["mislabel"],template_sd=cfg["template_sd"],cmult=cfg["cmult"])
            correct_truth = sim.true_value(template_kernel(sim,cfg,d["template_offsets"]),sim.UNIF5,cfg["T"])
            value,se,lo,hi = est.value_dr(d,cfg["T"],rng=rng)
            rows.append({"cell":name,"rep":rep,"seed":seed,"estimate":value,"se":se,"lo":lo,"hi":hi,
                         "nominal_truth":nominal,"actual_replicate_truth":correct_truth,
                         "covered_nominal":bool(lo<=nominal<=hi),"covered_actual":bool(lo<=correct_truth<=hi),
                         "template_offsets":d["template_offsets"]})
        here = [r for r in rows if r["cell"]==name]
        actual_cov = np.mean([r["covered_actual"] for r in here])
        cells[name] = {"config":cfg,"n_reps":reps,
                       "mean_bias_actual":float(np.mean([r["estimate"]-r["actual_replicate_truth"] for r in here])),
                       "coverage_actual":float(actual_cov),"coverage_mcse":float(np.sqrt(actual_cov*(1-actual_cov)/reps)),
                       "coverage_nominal":float(np.mean([r["covered_nominal"] for r in here])),
                       "actual_truth_range":[min(r["actual_replicate_truth"] for r in here),max(r["actual_replicate_truth"] for r in here)],
                       "nominal_truth":nominal,"exact_first_stage_blip_limits":exact_blip_limits(sim,cfg)}
    return {"status":"bounded independent CPU recheck; small-R coverage exploratory",
            "nuisances":"Q genuinely fitted tabular and task-cross-fitted; assignment probabilities supplied by simulator, never fitted",
            "current_code_sha256":grid.code_sha256(),"cells":cells}, rows


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--episodes",type=Path,required=True)
    ap.add_argument("--output",type=Path,default=ROOT/"results/independent_audit_20260920")
    ap.add_argument("--e0-reps",type=int,default=24)
    args=ap.parse_args()
    if args.e0_reps<2:
        ap.error("at least two rechecks required")
    args.output.mkdir(parents=True,exist_ok=True)
    if any(args.output.iterdir()):
        ap.error("output must be empty to preserve prior evidence")
    started=time.monotonic()
    routing,task_rows=routing_audit(args.episodes)
    (args.output/"routing_audit.json").write_text(json.dumps(routing,indent=2)+"\n")
    (args.output/"routing_task_rows.jsonl").write_text("".join(json.dumps(r)+"\n" for r in task_rows))
    print("Routing audit saved",flush=True)
    e0,reps=e0_recheck(args.e0_reps,args.output/"e0_source_snapshot")
    (args.output/"e0_recheck.json").write_text(json.dumps(e0,indent=2)+"\n")
    (args.output/"e0_replicates.jsonl").write_text("".join(json.dumps(r)+"\n" for r in reps))
    (args.output/"manifest.json").write_text(json.dumps({"elapsed_seconds":time.monotonic()-started,"external_model_calls":0,"paid_spend_usd":0,"script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"e0_reps_per_cell":args.e0_reps},indent=2)+"\n")
    print(json.dumps({"output":str(args.output),"seconds":time.monotonic()-started},indent=2))


if __name__=="__main__":
    main()
