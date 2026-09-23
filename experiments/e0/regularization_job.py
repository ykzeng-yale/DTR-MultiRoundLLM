"""One frozen E0 dataset -> four matched Q fits -> eight reporting records.

evaluate_job(plan, job, *, data=None, on_event=None) returns an artifact, never
writes files. job has the six typed CSV fields below. expected_job_identity()
validates them before sampling and supplies the runner's durable attempt identity.
The report pairing_id is this predeclared config/seed identity; actual data/fold
hashes are supplemental, shared by every variant. They are not independence proof.

Production uses simulate with Generator(PCG64(SeedSequence(data_seed))). Fold
assignment independently uses the existing make_task_folds(fold_seed) helper.
data= is an explicitly labelled handcrafted-data test boundary; it cannot relax
the 230 roots x40 episodes, T3 or logging/STOP contracts. No injected sampler is
accepted; tests may patch the simulate boundary without calling the real sampler.

Callbacks: prepared (identity/provenance), variant (two records, root means and
support), job_failed (eight failed records if data preparation fails). Each event
is JSON-safe. Callback exceptions propagate, allowing the outer runner to enforce
budgets. The runner journals all eight slots attempted before entry and durably
saves each variant event; a killed job's unreturned slots are interrupted attempts.
No retry, timeout enforcement, release authorization or persistence is supplied
here. No private/oracle Q enters fitting. Root-score normal DR intervals are the
procedure under numerical investigation, not a claimed coverage guarantee.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import json
import math
import platform
import time
from pathlib import Path

import numpy as np

import history_estimators as history
import regularization_report as reporting
import regularized_history_estimators as fitted
import simulator as sim

ROOT = Path(__file__).resolve().parents[2]
JOB_FIELDS = ("job_index", "cell_index", "cell", "replicate", "data_seed", "fold_seed")
CELLS = [(0, "uniform", 0, .2), (1, "base", 1, .1), (2, "weak_overlap", 2.5, .02)]
SOURCE_PATHS = ("experiments/e0/regularization_job.py", "experiments/e0/simulator.py",
                "experiments/e0/history_estimators.py", "experiments/e0/estimators.py",
                "experiments/e0/regularized_history_estimators.py", "experiments/e0/regularization_report.py")


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def expected_job_identity(plan, job):
    """Validate frozen scientific fields and the committed seed-table row, no draw."""
    fixed = dict(schema_version="e0-regularization-prospective-plan-v1", n_tasks=230,
                 trajectories_per_root=40, horizon=3, effect_multiplier=1.0, gz=0,
                 mislabel=0, template_sd=0, target_policy=[.2]*5, folds=3,
                 replicates_per_cell=200, total_planned_datasets=600,
                 representations=["compressed", "history"], shrinkage_lambdas=[0, 5],
                 score_methods=["plugin", "dr"], same_dataset_and_folds_for_every_variant=True,
                 distinct_training_roots_for_shrinkage_support=True,
                 cell_pool_means_episode_weighted=True, score_summary_equal_root_means=True,
                 deterministic_truth=.6459770061744536,
                 seed_table_path="experiments/e0/regularization_comparison_seed_plan_v1.csv")
    for name, value in fixed.items():
        if plan.get(name) != value or (isinstance(value, bool) and type(plan[name]) is not bool):
            raise ValueError(f"plan changes fixed field {name}")
    expected_cells = [dict(cell_index=i, name=name, kappa=kappa, action_floor=floor)
                      for i, name, kappa, floor in CELLS]
    if plan.get("cells") != expected_cells:
        raise ValueError("plan changes frozen logger cells")
    if not isinstance(job, dict) or set(job) != set(JOB_FIELDS):
        raise ValueError("job must contain the six typed seed-table fields")
    if any(type(job[k]) is not int for k in JOB_FIELDS if k != "cell"):
        raise ValueError("CSV integer fields must be parsed to integers")
    c, rep = job["cell_index"], job["replicate"]
    if not 0 <= c < 3 or not 0 <= rep < 200:
        raise ValueError("job outside frozen cell/replicate range")
    expected = dict(job_index=3*rep+c, cell_index=c, cell=CELLS[c][1], replicate=rep,
                    data_seed=202609220000+1000*c+rep, fold_seed=202609320000+1000*c+rep)
    if job != expected:
        raise ValueError("job violates frozen seeds or interleaved order")
    table_path = ROOT / fixed["seed_table_path"]
    raw = table_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != plan.get("seed_table_sha256"):
        raise ValueError("seed table bytes differ from plan pin")
    rows = list(csv.DictReader(raw.decode().splitlines()))
    if len(rows) != 600 or rows[job["job_index"]] != {k: str(job[k]) for k in JOB_FIELDS}:
        raise ValueError("job not present at its pinned seed-table position")
    plan_sha = _digest(plan)
    job_id = _digest({"schema": "e0-regularization-job-identity-v1", "plan_sha256": plan_sha, "job": job})
    return {"job_id": job_id, "plan_sha256": plan_sha, "job": dict(job),
            "planned_job": {"cell_id": job["cell"], "replicate": rep, "pairing_id": job_id}}


def _fingerprint(data):
    """Exact C-order array bytes plus shape/dtype; hash every delivered data field."""
    fields = {}
    for name, value in sorted(data.items()):
        if isinstance(value, np.ndarray):
            if value.dtype.hasobject:
                raise ValueError("dataset fingerprint refuses object-pointer array bytes")
            fields[name] = {"shape": list(value.shape), "dtype": value.dtype.str,
                            "sha256": hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()}
        else:
            fields[name] = {"json_value": value}
    return {"sha256": _digest(fields), "fields": fields,
            "encoding": "sha256 of canonical field descriptors; arrays use exact C-order bytes, dtype and shape"}


def _json_safe(value):
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("nonfinite artifact value")
    return value


def _support(fit):
    stages = []
    for train, heldout in zip(fit["training_support"], fit["heldout_support"]):
        stages.append({"stage": train["stage"], "training_roots": train["root_count"],
                       "training_trajectories": train["trajectory_count"],
                       "action_columns": ["action", "roots", "trajectories"],
                       "actions": [[a, c["root_count"], c["trajectory_count"]] for a, c in train["actions"].items()],
                       "cell_columns": ["key", "action", "roots", "trajectories"],
                       "cells": [[key, action, c["root_count"], c["trajectory_count"]]
                                 for (key, action), c in train["cells"].items()],
                       "heldout": heldout})
    return {"fold": fit["fold"], "stages": _json_safe(stages)}


def _root_means(scores, task_index):
    scores = np.asarray(scores, dtype=float)
    if scores.shape != task_index.shape or not np.isfinite(scores).all():
        raise ValueError("nonfinite or misaligned episode scores")
    return np.bincount(task_index, weights=scores) / np.bincount(task_index)


def _point_record(identity, estimator, means):
    row = {**identity["planned_job"], "estimator": estimator}
    estimate = float(np.mean(means))
    if not math.isfinite(estimate) or not math.isfinite((estimate - .6459770061744536) ** 2):
        raise ValueError("nonfinite point/squared-error arithmetic")
    row.update(status="completed", estimate=estimate)
    if estimator.endswith(":dr"):
        try:
            se = float(np.std(means, ddof=1) / math.sqrt(len(means)))
            lo, hi = estimate - 1.96*se, estimate + 1.96*se
            if not all(math.isfinite(x) for x in (se, lo, hi, hi-lo)) or se < 0:
                raise ValueError("nonfinite DR interval arithmetic")
            row["interval"] = dict(status="valid", se=se, lo=lo, hi=hi)
        except Exception as exc:
            row["interval"] = dict(status="failed", reason=f"{type(exc).__name__}: {exc}")
    return row


def evaluate_job(plan, job, *, data=None, on_event=None):
    """Sample once (unless injected), fit independently by variant, retain failures."""
    started, cpu = time.perf_counter(), time.process_time()
    identity = expected_job_identity(plan, job)  # refusal before any attempted draw
    provenance = {"source_sha256": {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCE_PATHS},
                  "python": platform.python_version(), "numpy": np.__version__,
                  "scipy": importlib.metadata.version("scipy"),
                  "data_mode": "handcrafted_injection" if data is not None else "production_sampler",
                  "data_rng": "numpy.Generator(numpy.PCG64(numpy.SeedSequence(data_seed)))",
                  "fold_rng": "history.make_task_folds: numpy.default_rng(fold_seed).permutation",
                  "data_seed": job["data_seed"], "fold_seed": job["fold_seed"],
                  "dataset": None, "folds": None}
    records, variants = [], {}
    calls = 0
    def emit(event):
        if on_event is not None:
            on_event(_json_safe({"identity": identity, **event}))
    def failed(estimator, exc):
        return {**identity["planned_job"], "estimator": estimator, "status": "failed",
                "reason": f"{type(exc).__name__}: {exc}"}
    try:
        _, _, kappa, floor = CELLS[job["cell_index"]]
        kernel, behavior = sim.kernel(1.), sim.make_beh(kappa, floor, gz=0.)
        if data is None:
            rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(job["data_seed"])))
            provenance["data_rng_initial_state_sha256"] = _digest(rng.bit_generator.state)
            calls = 1
            data = sim.simulate(230, 40, 3, kernel, behavior, rng,
                                mislabel=0., template_sd=0., cmult=1.)
        validated, policy = history._validated_data(data, 3, np.asarray(plan["target_policy"]))
        tasks = validated["task"]
        if len(tasks) != 9200 or set(tasks) != set(range(230)) or any(np.sum(tasks == r) != 40 for r in range(230)):
            raise ValueError("dataset must contain230 distinct numbered roots and40 episodes each")
        if not np.isin(validated["Y"], [0., 1.]).all():
            raise ValueError("synthetic endpoint must be binary")
        active = validated["elig"]
        expected_b = behavior[0, validated["S"][active], validated["A"][active]]
        if not np.allclose(validated["B"][active], expected_b, rtol=0, atol=1e-14):
            raise ValueError("recorded active propensity differs from frozen logger")
        for t in range(3):
            stop = active[:, t] & (validated["A"][:, t] == 0)
            if not np.array_equal(validated["Y"][stop], (validated["S"][stop, t] == 3).astype(float)):
                raise ValueError("STOP must seal current synthetic quality")
        provenance["dataset"] = _fingerprint(data)
        assignment = history.make_task_folds(tasks, folds=3, seed=job["fold_seed"])
        fold_payload = {k: _json_safe(v) for k, v in assignment.items()}
        provenance["folds"] = {**fold_payload, "sha256": _digest(fold_payload)}
    except Exception as exc:
        records = [failed(e, exc) for e in reporting.ESTIMATORS]
        emit({"event": "job_failed", "records": records, "provenance": provenance})
    else:
        emit({"event": "prepared", "provenance": provenance})
        fa, task_index = assignment["episode_fold_ids"], assignment["task_index"]
        for variant, (representation, penalty) in fitted.VARIANTS.items():
            phase_start = time.perf_counter()
            support, root_means, variant_records = [], {}, []
            try:
                plugin, dr = np.empty(len(tasks)), np.empty(len(tasks))
                for fold in range(3):
                    train, test = np.flatnonzero(fa != fold), np.flatnonzero(fa == fold)
                    fit = fitted.fit_regularized_q(validated, 3, policy, representation=representation,
                                                  shrinkage=penalty, idx=train)
                    plugin[test] = fit["v0"][test]
                    dr[test] = fitted.base.dr_scores(validated, 3, policy, fit["Q"], fit["fallback"], key=fit["key"])[test]
                    fit.update(fold=fold, heldout_support=fitted._heldout_support(validated, 3, policy, test, fit))
                    support.append(_support(fit))
                for method, scores in (("plugin", plugin), ("dr", dr)):
                    estimator = f"{variant}:{method}"
                    try:
                        means = _root_means(scores, task_index)
                        variant_records.append(_point_record(identity, estimator, means))
                        root_means[method] = means.tolist()
                    except Exception as exc:
                        variant_records.append(failed(estimator, exc))
            except Exception as exc:
                variant_records = [failed(f"{variant}:{method}", exc) for method in ("plugin", "dr")]
            result = {"variant": variant, "records": variant_records, "root_means": root_means,
                      "root_labels": _json_safe(assignment["task_labels"]), "support": support,
                      "dataset_sha256": provenance["dataset"]["sha256"],
                      "fold_sha256": provenance["folds"]["sha256"],
                      "wall_seconds": time.perf_counter()-phase_start}
            records.extend(variant_records)
            variants[variant] = result
            emit({"event": "variant", **result})  # callback failures must propagate
    artifact = {"schema_version": "e0-regularization-job-v1", "identity": identity,
                "planned_job": identity["planned_job"], "provenance": provenance,
                "records": records, "variants": variants,
                "resources": {"wall_seconds": time.perf_counter()-started,
                              "cpu_seconds": time.process_time()-cpu, "sampler_attempts": calls,
                              "model_calls": 0, "benchmark_executions": 0, "paid_usd": 0},
                "all_points_completed": all(x["status"] == "completed" for x in records)}
    # Validate the exact reporting schema before returning; it does not generate data.
    reporting.summarize_regularization([identity["planned_job"]], records, plan["deterministic_truth"])
    return _json_safe(artifact)
