#!/usr/bin/env python3
"""Post-result saved-score/weight/support diagnosis; no draws, fits or new CIs.

Streams one pinned journal and reads its96 hash-bound numeric NPZ archives.
Only stdlib and NumPy are imported. This is descriptive reused-data arithmetic,
not a causal attribution of undercoverage or a validation of root independence.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import statistics
import time
import zipfile

import numpy as np

TRUTH = .6459770061744536
EVENTS_SHA256 = "980de970926ed17a819eb9c87fbf9db164d39af94fb1b333e6877117630f0928"
EVENTS_BYTES = 101897293
N_DATASETS, N_ROOTS, RUNS, T = 96, 230, 40, 3
MAX_OUTPUT_BYTES = 10*1024*1024
VARIANTS = tuple(f"{r}_lambda{p}_{m}" for r in ("compressed", "history")
                 for p in (0, 5) for m in ("original", "evaluation_only", "recursive"))
ARRAYS = ("task", "S", "A", "B", "elig", "Y")
FOLDS = ("task_labels", "task_index", "task_fold_ids", "episode_fold_ids")
PRESENCE = ("observed_training_cell", "unseen_training_cell")
SOURCES = ("structural", "cell", "action_pool", "stage_pool", "zero")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode())


def finite(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("finite numeric value required")
    return float(value)


def strict_json(raw):
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ValueError("duplicate JSON key")
            result[k] = v
        return result
    def invalid(value):
        raise ValueError("nonfinite JSON constant: "+value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid,
                      parse_float=lambda x: finite(float(x)))


def file_hash(path):
    h, size = hashlib.sha256(), 0
    with Path(path).open("rb") as handle:
        for raw in iter(lambda: handle.read(1024*1024), b""):
            h.update(raw); size += len(raw)
    return dict(sha256=h.hexdigest(), bytes=size)


def mean(values):
    return finite(math.fsum(values)/len(values)) if values else None


def correlation(left, right):
    if len(left) != len(right):
        raise ValueError("unaligned correlation vectors")
    pairs = [(finite(a), finite(b)) for a, b in zip(left, right) if a is not None and b is not None]
    if len(pairs) < 2:
        return dict(n=len(pairs), excluded=len(left)-len(pairs), r=None)
    a, b = zip(*pairs)
    ma, mb = mean(a), mean(b)
    x, y = [v-ma for v in a], [v-mb for v in b]
    sx, sy = max(map(abs, x)), max(map(abs, y))
    r = None
    if sx and sy:
        x, y = [v/sx for v in x], [v/sy for v in y]
        r = finite(math.fsum(u*v for u, v in zip(x, y))/
                   math.sqrt(math.fsum(u*u for u in x)*math.fsum(v*v for v in y)))
    return dict(n=len(pairs), excluded=len(left)-len(pairs), r=r)


def concentration(dr, plugin, exposure, root_labels):
    """Root-ID tie-breaking; S=0 concentration fractions/skewness are undefined."""
    n = len(root_labels)
    if n < 2 or len(set(root_labels)) != n or any(len(x) != n for x in (dr, plugin, exposure)):
        raise ValueError("aligned distinct root IDs and >=2 root scores required")
    dr, plugin, exposure = ([finite(v) for v in x] for x in (dr, plugin, exposure))
    if any(v < 0 for v in exposure):
        raise ValueError("exposure must be nonnegative")
    center = mean(dr)
    delta = [finite(v-center) for v in dr]
    squares = [finite(v*v) for v in delta]
    total = finite(math.fsum(squares))
    order = sorted(range(n), key=lambda i: (-squares[i], root_labels[i]))
    correction = [finite(a-b) for a, b in zip(dr, plugin)]
    skew = None
    if total:
        scale = max(map(abs, delta))
        u = [v/scale for v in delta]
        skew = finite(mean([v**3 for v in u])/mean([v*v for v in u])**1.5)
    def share(indices):
        return finite(math.fsum(squares[i] for i in indices)/total) if total else None
    top = [dict(root_id=root_labels[i], dr=dr[i], plugin=plugin[i], centered_dr=delta[i],
                squared_deviation=squares[i], squared_deviation_share=squares[i]/total if total else None,
                dr_minus_plugin=correction[i], exposure_L=exposure[i]) for i in order[:5]]
    return dict(mean_dr=center, centered_sum_squares=total, sample_root_variance=total/(n-1),
        top1_square_share=share(order[:1]), top5_square_share=share(order[:5]),
        positive_square_share=share([i for i, d in enumerate(delta) if d > 0]),
        root_moment_skewness=skew, top_roots=top,
        correlation_correction_L=correlation(correction, exposure)["r"],
        correlation_centered_dr_L=correlation(delta, exposure)["r"],
        saved_correction_envelope=dict(
            roots_checked=n, tolerance=1e-10,
            violations=sum(abs(v)>l+1e-10 for v, l in zip(correction, exposure)),
            max_abs_correction_minus_L=max(abs(v)-l for v, l in zip(correction, exposure)),
            scope="Observed saved-root |DR-plugin|<=L check only; no general bound or refit is established"))


def weight_exposures(arrays, *, n_roots=N_ROOTS, runs=RUNS, horizon=T):
    """Active cumulative target/logging weights; padding contributes no exposure."""
    task, b, active = (np.asarray(arrays[k]) for k in ("task", "B", "elig"))
    if (task.dtype.kind not in "iu" or task.shape != (n_roots*runs,)
            or b.shape != (len(task), horizon) or active.shape != b.shape or active.dtype.kind != "b"
            or not np.array_equal(np.unique(task), np.arange(n_roots))
            or not np.all(np.bincount(task) == runs)
            or not active[:, 0].all() or np.any(active[:, 1:] & ~active[:, :-1])):
        raise ValueError("invalid fixed root grouping or absorbing active mask")
    if not np.isfinite(b[active]).all() or np.any(b[active] <= 0) or np.any(b[active] > 1):
        raise ValueError("active behavior probabilities must be finite in(0,1]")
    weights, trajectory_exposure = np.ones(len(task)), np.zeros(len(task))
    stages = []
    for t in range(horizon):
        alive = active[:, t]
        weights[alive] *= .2/b[alive, t]
        if not np.isfinite(weights).all():
            raise ValueError("nonfinite cumulative weights")
        observed = weights[alive]
        trajectory_exposure[alive] += observed
        stages.append(dict(stage=t, active_denominator=int(alive.sum()),
            max_weight=float(observed.max()) if len(observed) else None,
            count_gt10=int((observed>10).sum()), count_gt100=int((observed>100).sum())))
    exposure = np.bincount(task, weights=trajectory_exposure, minlength=n_roots)/runs
    return dict(root_labels=list(range(n_roots)), exposure_L=exposure.tolist(), stages=stages,
                definition="L_g=(sum over its active trajectory/stage cumulative(.2/B))/40; padding factor1 and excluded")


def aggregate_support(support, *, horizon=T, folds=3):
    """Both partitions sum separately to queries; never add their seven counts."""
    if len(support) != folds or [f.get("fold") for f in support] != list(range(folds)):
        raise ValueError("exact ordered fold support required")
    totals = [dict(stage=t, active_heldout_trajectories=0,
                   groups={g: dict(queries=0, counts={k:0 for k in PRESENCE+SOURCES}) for g in ("stop", "nonstop")})
              for t in range(horizon)]
    for fold in support:
        stages = fold["stages"]
        if len(stages) != horizon or [s.get("stage") for s in stages] != list(range(horizon)):
            raise ValueError("exact ordered stage support required")
        for t, stage in enumerate(stages):
            held = stage["heldout"]
            active = held.get("active_heldout_trajectories")
            if held.get("stage") != t or type(active) is not int or active < 0 or set(held["groups"]) != {"stop", "nonstop"}:
                raise ValueError("invalid stage heldout support")
            totals[t]["active_heldout_trajectories"] += active
            for group, multiplier in (("stop", 1), ("nonstop", 4)):
                row = held["groups"][group]
                q, counts = row.get("queries"), row.get("counts", {})
                if (type(q) is not int or q != multiplier*active or set(counts) != set(PRESENCE+SOURCES)
                        or any(type(v) is not int or v < 0 for v in counts.values())
                        or sum(counts[k] for k in PRESENCE) != q or sum(counts[k] for k in SOURCES) != q):
                    raise ValueError("support partitions must each separately sum to queries")
                fallback = sum(counts[k] for k in ("action_pool", "stage_pool", "zero"))
                if row.get("fallback_queries") != fallback or row.get("fallback_frequency") != (fallback/q if q else None):
                    raise ValueError("saved fallback accounting mismatch")
                out = totals[t]["groups"][group]
                out["queries"] += q
                for k, v in counts.items(): out["counts"][k] += v
    for stage in totals:
        for row in stage["groups"].values():
            q, c = row["queries"], row["counts"]
            row["unseen_frequency"] = c["unseen_training_cell"]/q if q else None
            row["fallback_frequency"] = sum(c[k] for k in ("action_pool", "stage_pool", "zero"))/q if q else None
    return totals


def read_archive(root, event):
    """Validate exact saved bytes, minimal-array descriptors and root-fold binding."""
    rep, ref, prov = event["identity"]["job"]["replicate"], event["archive"], event["provenance"]
    if ref.get("path") != f"dataset_{rep:03d}.npz" or set(ref) != {"path", "bytes", "sha256"}:
        raise ValueError("invalid archive reference")
    path = root/"records"/ref["path"]
    raw = path.read_bytes()
    if len(raw) != ref["bytes"] or sha(raw) != ref["sha256"]:
        raise ValueError("archive hash/length mismatch")
    fields = set(ARRAYS) | {"fold_"+k for k in FOLDS}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = archive.infolist()
        if (len(members) != len(fields) or {m.filename for m in members} != {k+".npy" for k in fields}
                or any(m.compress_type != zipfile.ZIP_STORED for m in members)
                or sum(m.file_size for m in members) > 8*1024*1024):
            raise ValueError("unexpected archive member/compression/size")
    with np.load(io.BytesIO(raw), allow_pickle=False) as loaded:
        arrays = {k: loaded[k] for k in loaded.files}
    descriptors = {k:dict(dtype=arrays[k].dtype.str, shape=list(arrays[k].shape),
                          sha256=sha(np.ascontiguousarray(arrays[k]).tobytes())) for k in ARRAYS}
    if descriptors != prov["dataset"]["fields"] or digest(descriptors) != prov["dataset"]["sha256"]:
        raise ValueError("dataset descriptor hash mismatch")
    fold = {k: arrays["fold_"+k].tolist() for k in FOLDS}
    if any(fold[k] != prov["folds"][k] for k in FOLDS) or digest(fold) != prov["folds"]["sha256"]:
        raise ValueError("fold descriptor hash mismatch")
    task = arrays["task"]
    if (fold["task_labels"] != list(range(N_ROOTS)) or fold["task_index"] != task.tolist()
            or arrays["fold_task_fold_ids"].shape != (N_ROOTS,)
            or set(fold["task_fold_ids"]) != {0, 1, 2}
            or not np.array_equal(arrays["fold_episode_fold_ids"], arrays["fold_task_fold_ids"][task])):
        raise ValueError("root/fold alignment mismatch")
    if sha(path.read_bytes()) != ref["sha256"]:
        raise ValueError("archive changed during reading")
    return arrays


def validate_identity(identity, replicate):
    job, planned = identity.get("job", {}), identity.get("planned_job", {})
    if (type(job.get("replicate")) is not int or job["replicate"] != replicate
            or set(job) != {"replicate", "data_seed", "fold_seed"}
            or any(type(job[k]) is not str or not job[k].isdigit() for k in ("data_seed", "fold_seed"))
            or planned != dict(cell_id="weak_overlap", replicate=replicate, pairing_id=identity.get("job_id"))
            or identity.get("job_id") != digest(dict(schema="e0-stop-anchor-job-identity-v1",
                                                    plan_sha256=identity.get("plan_sha256"), job=job))):
        raise ValueError("invalid job identity")


def variant_row(event, prepared, exposure):
    if (event["identity"] != prepared["identity"] or event.get("dataset_sha256") != prepared["provenance"]["dataset"]["sha256"]
            or event.get("fold_sha256") != prepared["provenance"]["folds"]["sha256"]
            or event.get("root_labels") != exposure["root_labels"]):
        raise ValueError("variant data/fold/root identity mismatch")
    variant, records = event["variant"], event["records"]
    if [r.get("estimator") for r in records] != [variant+":plugin", variant+":dr"]:
        raise ValueError("exact paired plugin/DR records required")
    for row in records:
        if row.get("status") != "completed" or any(row.get(k) != v for k, v in event["identity"]["planned_job"].items()):
            raise ValueError("complete bound point records required")
    metrics = concentration(event["root_means"]["dr"], event["root_means"]["plugin"],
                            exposure["exposure_L"], exposure["root_labels"])
    for row, method in zip(records, ("plugin", "dr")):
        if not math.isclose(finite(row["estimate"]), mean(event["root_means"][method]), rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("saved root mean mismatch")
    row = records[1]
    ci = row.get("interval", {})
    if ci.get("status") != "valid" or finite(ci.get("se")) <= 0:
        raise ValueError("valid positive DR SE required for this complete fixed run")
    estimate, se = finite(row["estimate"]), finite(ci["se"])
    for actual, expected in ((ci["lo"], estimate-1.96*se), (ci["hi"], estimate+1.96*se),
                             (se, math.sqrt(metrics["sample_root_variance"]/N_ROOTS))):
        if not math.isclose(finite(actual), expected, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("saved DR interval arithmetic mismatch")
    heldout = aggregate_support(event["support"])
    if [s["active_heldout_trajectories"] for s in heldout] != [s["active_denominator"] for s in exposure["stages"]]:
        raise ValueError("heldout query denominators differ from archived active trajectories")
    for group in ("stop", "nonstop"):
        q = sum(s["groups"][group]["queries"] for s in heldout)
        for metric, keys in (("unseen", ("unseen_training_cell",)), ("fallback", ("action_pool", "stage_pool", "zero"))):
            metrics[group+"_"+metric+"_frequency"] = sum(s["groups"][group]["counts"][k] for s in heldout for k in keys)/q if q else None
    return dict(replicate=event["identity"]["job"]["replicate"], estimator=variant+":dr",
        pairing_id=event["identity"]["job_id"], dataset_sha256=event["dataset_sha256"], fold_sha256=event["fold_sha256"],
        estimate=estimate, error=estimate-TRUTH, se=se, z=(estimate-TRUTH)/se,
        interval_category="below" if ci["hi"] < TRUTH else "above" if ci["lo"] > TRUTH else "covered",
        metrics=metrics, heldout_support=heldout)


METRICS = ("top1_square_share", "top5_square_share", "positive_square_share", "root_moment_skewness",
           "correlation_correction_L", "correlation_centered_dr_L", "stop_unseen_frequency",
           "nonstop_unseen_frequency", "stop_fallback_frequency", "nonstop_fallback_frequency")


def summaries(rows):
    output = []
    def describe(values):
        valid = [finite(v) for v in values if v is not None]
        return dict(n=len(valid), undefined=len(values)-len(valid), mean=mean(valid),
                    median=statistics.median(valid) if valid else None)
    for variant in VARIANTS:
        selected = [r for r in rows if r["estimator"] == variant+":dr"]
        if [r["replicate"] for r in selected] != list(range(N_DATASETS)):
            raise ValueError("each method must retain all96 ordered datasets")
        groups = {}
        for name in ("all", "below", "covered", "above"):
            group = selected if name == "all" else [r for r in selected if r["interval_category"] == name]
            groups[name] = dict(n=len(group), metrics={k:describe([r["metrics"][k] for r in group]) for k in METRICS})
        associations = {k:{outcome:correlation([r["metrics"][k] for r in selected], [r[outcome] for r in selected])
                           for outcome in ("error", "se", "z")} for k in METRICS}
        output.append(dict(estimator=variant+":dr", groups=groups, correlations_with_saved_dataset_results=associations))
    return output


def analyze_run(run_dir):
    started, cpu = time.perf_counter(), time.process_time()
    root = Path(run_dir).resolve()
    journal = root/"records/events.jsonl"
    expected = dict(sha256=EVENTS_SHA256, bytes=EVENTS_BYTES)
    if file_hash(journal) != expected:
        raise ValueError("journal differs from exact closed-run pin")
    rows, weights, archives, sources = [], [], [], None
    current, prepared, exposure, awaiting, returned, complete = None, None, None, None, 0, 0
    streamed = hashlib.sha256()
    with journal.open("rb") as handle:
        for raw in handle:
            streamed.update(raw)
            if not raw.endswith(b"\n"):
                raise ValueError("complete fixed study must not have a torn journal tail")
            event = strict_json(raw)
            if not isinstance(event, dict): raise ValueError("journal object required")
            kind = event.get("event")
            if kind == "job_started":
                if current is not None or complete >= N_DATASETS: raise ValueError("duplicate/out-of-order job")
                validate_identity(event["identity"], complete)
                current, prepared, exposure, awaiting, returned = event["identity"], None, None, None, 0
                continue
            if current is None or event.get("identity") != current:
                raise ValueError("event outside matching active job")
            if kind == "prepared":
                if prepared is not None or returned: raise ValueError("duplicate preparation")
                prov = event["provenance"]
                if sources is None: sources = prov["source_sha256"]
                if prov["source_sha256"] != sources or prov.get("data_mode") != "production_sampler":
                    raise ValueError("source or production identity mismatch")
                arrays = read_archive(root, event)
                exposure = weight_exposures(arrays)
                weights.append(dict(replicate=complete, dataset_sha256=prov["dataset"]["sha256"],
                                    fold_sha256=prov["folds"]["sha256"], **exposure))
                archives.append(dict(replicate=complete, **event["archive"]))
                prepared = event
            elif kind == "variant_started":
                if prepared is None or awaiting is not None or returned >= 12 or event.get("variant") != VARIANTS[returned]:
                    raise ValueError("variant start order mismatch")
                awaiting = event["variant"]
            elif kind == "variant":
                if awaiting is None or event.get("variant") != awaiting: raise ValueError("terminal variant lacks matching start")
                rows.append(variant_row(event, prepared, exposure))
                returned += 1; awaiting = None
            elif kind == "job_complete":
                if returned != 12 or awaiting is not None: raise ValueError("job lacks all12 terminal variants")
                complete += 1; current = None
            else:
                raise ValueError("unexpected event in complete fixed run")
    if current is not None or complete != N_DATASETS or len(rows) != 1152 or streamed.hexdigest() != EVENTS_SHA256:
        raise ValueError("incomplete or changed journal")
    # A second hash detects changes after an early archive was read, without reloading arrays.
    for ref in archives:
        if file_hash(root/"records"/ref["path"]) != {k:ref[k] for k in ("bytes", "sha256")}:
            raise ValueError("archive changed during analysis")
    if file_hash(journal) != expected: raise ValueError("journal changed during analysis")
    output = dict(schema_version="e0-stop-anchor-concentration-v1", classification="Post-result descriptive saved-artifact diagnosis",
        checked_utc=datetime.now(timezone.utc).isoformat(), utility_sha256=sha(Path(__file__).read_bytes()),
        run_directory=str(root), truth=TRUTH, journal=expected, archives=archives,
        source_sha256_in_pinned_journal=sources, input_bytes_stable=True,
        dataset_method_rows=rows, shared_weight_rows=weights, method_summaries=summaries(rows),
        definitions=dict(centered_score="d_g=DR_g-mean_g(DR_g); S=sum_g d_g²",
            top_shares="Largest1/largest5 d_g² divided by S; ties ascending numeric rootID",
            positive_share="sum_{d_g>0}d_g²/S; zero deviations contribute nothing",
            skewness="m3/m2^1.5 with m_k=mean_g(d_g^k); constant root scores give null",
            support="Observed/unseen and structural/cell/action_pool/stage_pool/zero are separate partitions, each summing to queries",
            active_weights="W_it=product_{s<=t,active}(.2/B_is); inactive factors1; only active W enter stage counts/L",
            root_exposure="L_g=sum_{its40trajectories,tactive}W_it/40",
            weight_thresholds="Strict W>10 and W>100; denominators are active trajectories at each stage",
            correlations="Centered-sum Pearson r; null for insufficient/constant vectors, with dataset pair counts"),
        limitations=["All12 methods and96 datasets retained; no p-values, new intervals, method selection or tuning.",
            "Root scores are saved, not regenerated; no estimator/sampler imports, draws or refits.",
            "Source identity is inherited from the exact pinned journal; current Git/source/receiver state is not reverified.",
            "Concentration and correlations describe reused scores, weights and support; they do not identify a causal source of undercoverage.",
            "Support queries are not independent observations, ESS, or target-occupancy mass; structural queries are not observed training support.",
            "Top roots retain current scores/deviations; all230 root vectors remain in the pinned journal rather than duplicated here.",
            "Positive and negative DR extremes remain possible; saved envelope checks are descriptive, not a universal guarantee.",
            "The external parent enforces oneCPU/60seconds; this reader reports internal elapsed time without claiming process supervision."],
        resources=dict(wall_seconds=time.perf_counter()-started, cpu_seconds=time.process_time()-cpu,
                       sampled_datasets=0, estimator_fits=0, model_calls=0, benchmark_executions=0, paid_usd=0))
    return output


def write_diagnostic(run_dir, out):
    root, target = Path(run_dir).resolve(), Path(out).resolve()
    if target == root or root in target.parents: raise ValueError("output must be outside immutable raw run")
    if target.exists(): raise FileExistsError(target)
    result = analyze_run(root)
    raw = (json.dumps(result, sort_keys=True, indent=1, allow_nan=False)+"\n").encode()
    if len(raw) > MAX_OUTPUT_BYTES: raise ValueError("derived output exceeds10MiB cap")
    with target.open("xb") as handle: handle.write(raw)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    write_diagnostic(args.run_dir, args.out)
