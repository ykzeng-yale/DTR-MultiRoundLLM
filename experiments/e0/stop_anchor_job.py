"""One fixed STOP-study dataset -> 12 Q sequences -> 24 reporting records.

evaluate_job(plan, job, data=None, on_event=None) returns data/provenance, records
and resource counters; it neither persists outputs nor authorizes execution.
job is exactly {replicate:int, data_seed:str, fold_seed:str}. Decimal seed strings
are preserved in identities and JSON; only RNG construction parses Python ints.
The ENTIRE accepted plan and all 96 seed rows are verified before any sampler.

Events all include identity: prepared(provenance, arrays); variant_started
(variant, estimator_ids, data/fold hashes, dependency); variant(two records,
root_means, observed/structural support, fit counts, timing); job_failed(all24
failed records if preparation fails). The outer journal marks shared-job slots
attempted; variant starts and actual fit attempts are separate. Callback failures
propagate outside scientific exception handling. No persistence, timeout, resume,
release, full-job completion, or coverage guarantee is supplied by this module.

Each original variant finishes three folds before its terminal event. Its direct
mode reuses those exact fits and scores, never scalar STOP fallback for scoring.
Recursive mode independently fits all three folds. A failed original fit creates
an explicit direct-mode dependency failure, without preventing later recursive
or other variants. Exceptions preserve terminal results already returned/events.

Only minimal estimator arrays are archived, not latent e/z or simulator extras.
They are copied before fitting, fingerprinted by exact C-order bytes/dtype/shape,
and included as JSON dtype/shape/values in prepared['arrays']. Nonfinite padding
is rejected rather than silently normalized. Handcrafted injection keeps the full
230x40/T3/logging/payoff contract and is conspicuously labeled in provenance.
"""
from __future__ import annotations

from collections import Counter
import csv
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import time

import numpy as np

import regularization_job as legacy
import stop_anchor_estimators as core
import simulator as sim

ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = "experiments/e0/stop_anchor_comparison_plan_v1.json"
PLAN_FILE_SHA256 = "05de997cb4ddb20d8c7a6699ff314dcd8545825a6e5c42be8bcd235bc46c95b5"
SEED_PATH = "experiments/e0/stop_anchor_seed_plan_v1.csv"
SEED_SHA256 = "4585c96be1f3cdaa8c8a7f4d64c5665fc0bba480196e314cfef8976ed7c00e9c"
ARRAY_NAMES = ("task", "S", "A", "B", "elig", "Y")
SOURCE_PATHS = tuple("experiments/e0/" + name + ".py" for name in (
    "stop_anchor_job", "stop_anchor_estimators", "stop_anchor_journal", "stop_anchor_report", "regularization_job",
    "regularization_report", "regularized_history_estimators", "history_estimators",
    "estimators", "simulator")) + (PLAN_PATH, SEED_PATH)
ESTIMATORS = core.ESTIMATORS
anchored = core  # Explicit public alias used by the separately owned journal adapter.

_digest = legacy._digest
_json_safe = legacy._json_safe
_fingerprint = legacy._fingerprint
_root_means = legacy._root_means
_point_record = legacy._point_record


def _seed(kind, replicate):
    raw = f"DTR-MultiRoundLLM:LEAD-E0-STOP-01:v1:{kind}:{replicate}".encode("ascii")
    return str(int.from_bytes(hashlib.sha256(raw).digest()[:16], "big"))


def expected_job_identity(plan, job):
    """Strict complete plan/seed validation and pre-outcome identity; no draw."""
    raw_plan = (ROOT / PLAN_PATH).read_bytes()
    if hashlib.sha256(raw_plan).hexdigest() != PLAN_FILE_SHA256:
        raise ValueError("accepted full plan file differs from source pin")
    accepted = json.loads(raw_plan)
    if not isinstance(plan, dict) or _digest(plan) != _digest(accepted):
        raise ValueError("supplied full plan differs from accepted plan")
    if (plan["variant_order"] != list(core.VARIANTS)
            or plan["estimator_order"] != list(ESTIMATORS)
            or plan["seed_table_sha256"] != SEED_SHA256):
        raise ValueError("core estimator identities or seed pin differ from plan")
    if (not isinstance(job, dict) or set(job) != {"replicate", "data_seed", "fold_seed"}
            or type(job["replicate"]) is not int or not 0 <= job["replicate"] < 96
            or any(type(job[k]) is not str for k in ("data_seed", "fold_seed"))):
        raise ValueError("job needs replicate integer and exact decimal seed strings")
    raw_seeds = (ROOT / SEED_PATH).read_bytes()
    if hashlib.sha256(raw_seeds).hexdigest() != SEED_SHA256:
        raise ValueError("seed table differs from source pin")
    rows = list(csv.DictReader(raw_seeds.decode("ascii").splitlines()))
    if len(rows) != 96:
        raise ValueError("expected all 96 seed rows")
    for rep, row in enumerate(rows):
        expected = dict(replicate=str(rep), data_seed=_seed("data", rep), fold_seed=_seed("fold", rep))
        if row != expected:
            raise ValueError("seed table violates fixed complete row/order/namespace")
    if rows[job["replicate"]] != {k: str(v) for k, v in job.items()}:
        raise ValueError("job differs from its fixed seed-table row")
    plan_sha = _digest(plan)
    job_id = _digest(dict(schema="e0-stop-anchor-job-identity-v1", plan_sha256=plan_sha, job=job))
    return dict(job_id=job_id, plan_sha256=plan_sha, job=dict(job),
                planned_job=dict(cell_id="weak_overlap", replicate=job["replicate"], pairing_id=job_id))


def _archive_data(data):
    """Copy numeric minimal arrays; retain exact dtype/shape/value descriptors."""
    arrays = {key: np.array(data[key], copy=True, order="C") for key in ARRAY_NAMES}
    tasks = arrays["task"]
    if not np.issubdtype(tasks.dtype, np.integer) or tasks.dtype == np.dtype(bool):
        raise ValueError("task identifiers must be nonobject integer root IDs")
    arrays["task"] = tasks.astype(np.int64)
    for name, array in arrays.items():
        if array.dtype.hasobject or not np.isfinite(array).all():
            raise ValueError(f"minimal array {name} requires finite numeric values, including padding")
    descriptors = {name: dict(dtype=a.dtype.str, shape=list(a.shape), values=a.tolist())
                   for name, a in arrays.items()}
    return arrays, descriptors, legacy._fingerprint(arrays)


def _support(fit):
    """Serialize observed cells with Q diagnostics; structural values add no cells."""
    stages = []
    for train, heldout in zip(fit["training_support"], fit["heldout_support"]):
        cells = []
        for (key, action), c in train["cells"].items():
            state = key[0] if fit["representation"] == "compressed" else key[0][-1]
            structural = action == 0 and fit["mode"] != "original"
            effective = float(state == 3) if structural else c["q_fitted"]
            cells.append([key, action, c["root_count"], c["trajectory_count"], c["q_cell"],
                          c["q_pool"], c["q_fitted"], effective, structural])
        stages.append(dict(stage=train["stage"], training_roots=train["root_count"],
            training_trajectories=train["trajectory_count"], stage_mean=train["stage_mean"],
            action_columns=["action", "roots", "trajectories"],
            actions=[[a, c["root_count"], c["trajectory_count"]] for a, c in train["actions"].items()],
            cell_columns=["key", "action", "roots", "trajectories", "q_cell", "q_pool",
                          "q_table", "q_effective_query", "structural_override"],
            cells=cells, heldout=heldout))
    return _json_safe(dict(fold=fit["fold"], mode=fit["mode"], stages=stages,
        support_scope="Observed training support and query-source partitions; neither ESS nor target occupancy"))


def evaluate_job(plan, job, *, data=None, on_event=None):
    """Return one dataset artifact with incremental variant events; no writes."""
    started, cpu = time.perf_counter(), time.process_time()
    identity = expected_job_identity(plan, job)  # Must precede RNG or sampler construction.
    provenance = dict(source_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCE_PATHS},
        python=platform.python_version(), numpy=np.__version__, scipy=importlib.metadata.version("scipy"),
        data_mode="handcrafted_injection" if data is not None else "production_sampler",
        data_rng="numpy.Generator(numpy.PCG64(numpy.SeedSequence(int(data_seed))))",
        fold_rng="history.make_task_folds: numpy.default_rng(int(fold_seed)).permutation",
        data_seed=job["data_seed"], fold_seed=job["fold_seed"], dataset=None, folds=None)
    records, variants, cache = [], {}, {}
    sampler_attempts = fit_attempts = fit_completed = 0
    archived = None

    def emit(event):
        # Deliberately never called inside a scientific try/except.
        if on_event is not None:
            on_event(_json_safe(dict(identity=identity, **event)))

    def failed(estimator, exc):
        return dict(identity["planned_job"], estimator=estimator, status="failed",
                    reason=f"{type(exc).__name__}: {exc}")

    preparation_error = None
    try:
        behavior = sim.make_beh(2.5, .02, gz=0.)
        if data is None:
            rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(int(job["data_seed"]))))
            provenance["data_rng_initial_state_sha256"] = _digest(rng.bit_generator.state)
            sampler_attempts = 1
            data = sim.simulate(230, 40, 3, sim.kernel(1.), behavior, rng,
                                mislabel=0., template_sd=0., cmult=1.)
        minimal, archived, fingerprint = _archive_data(data)
        validated, policy = core._validated(minimal, 3, np.asarray(plan["target_policy"]))
        tasks = minimal["task"]
        if tasks.shape != (9200,) or Counter(tasks.tolist()) != {i: 40 for i in range(230)}:
            raise ValueError("dataset must contain230 numbered roots and40 episodes per root")
        active = validated["elig"]
        expected_b = behavior[0, validated["S"][active], validated["A"][active]]
        if not np.allclose(validated["B"][active], expected_b, rtol=0, atol=1e-14):
            raise ValueError("active recorded propensity differs from fixed weak-overlap logger")
        assignment = core.history.make_task_folds(tasks, folds=3, seed=int(job["fold_seed"]))
        fold_payload = _json_safe(assignment)
        provenance.update(dataset=fingerprint, folds={**fold_payload, "sha256": _digest(fold_payload)})
        _json_safe(archived)  # Detect serialization failures before declaring preparation complete.
    except Exception as exc:
        preparation_error = exc

    if preparation_error is not None:
        records = [failed(e, preparation_error) for e in ESTIMATORS]
        # Invalid/partial payloads are not advertised as usable archived datasets.
        archived = None
        emit(dict(event="job_failed", failure_phase="preparation", records=records,
                  provenance=provenance, backward_fit_attempts=0, backward_fits_completed=0))
    else:
        emit(dict(event="prepared", provenance=provenance, arrays=archived))
        fa, task_index = assignment["episode_fold_ids"], assignment["task_index"]
        for variant, (representation, penalty, mode) in core.VARIANTS.items():
            prefix = f"{representation}_lambda{penalty}"
            dependency = prefix + "_original" if mode == "evaluation_only" else None
            bindings = dict(variant=variant, dataset_sha256=provenance["dataset"]["sha256"],
                            fold_sha256=provenance["folds"]["sha256"])
            emit(dict(event="variant_started", **bindings,
                      estimator_ids=[f"{variant}:{m}" for m in ("plugin", "dr")],
                      depends_on_variant=dependency, planned_backward_fits=0 if dependency else 3))
            phase_wall, phase_cpu = time.perf_counter(), time.process_time()
            support, root_means, variant_records = [], {}, []
            attempted = completed = 0
            dependency_failure = False
            fits = []
            try:
                plugin, dr = np.empty(9200), np.empty(9200)
                if dependency and dependency not in cache:
                    dependency_failure = True
                    raise RuntimeError(f"dependency_unavailable: {dependency} did not produce all three original fits/scores")
                for fold in range(3):
                    train, test = np.flatnonzero(fa != fold), np.flatnonzero(fa == fold)
                    if mode == "evaluation_only":
                        original_fit = cache[dependency]["fits"][fold]
                        fit = core._evaluation_view(validated, policy, original_fit)
                        fold_dr = (cache[dependency]["dr"] +
                                   core.direct_stop_increment(validated, 3, policy, original_fit["query"]))
                    else:
                        attempted += 1
                        fit_attempts += 1
                        fit = core.fit_stop_anchor_q(validated, 3, policy, representation=representation,
                                                     shrinkage=penalty, mode=mode, idx=train)
                        completed += 1
                        fit_completed += 1
                        # Structural query is authoritative; only original uses frozen table scorer.
                        fold_dr = (core.base.dr_scores(validated, 3, policy, fit["Q"], fit["fallback"], key=fit["key"])
                                   if mode == "original" else core.query_dr_scores(validated, 3, policy, fit["query"]))
                    plugin[test], dr[test] = fit["v0"][test], fold_dr[test]
                    fit.update(fold=fold, train_indices=train, test_indices=test,
                               heldout_support=core.heldout_support(validated, 3, test, fit))
                    support.append(_support(fit))
                    fits.append(fit)
                if mode == "original":
                    cache[variant] = dict(fits=fits, dr=dr.copy())
                for method, scores in (("plugin", plugin), ("dr", dr)):
                    estimator = f"{variant}:{method}"
                    try:
                        means = _root_means(scores, task_index)
                        variant_records.append(_point_record(identity, estimator, means))
                        root_means[method] = means.tolist()
                    except Exception as exc:
                        variant_records.append(failed(estimator, exc))
            except Exception as exc:
                variant_records = [failed(f"{variant}:{m}", exc) for m in ("plugin", "dr")]
            result = dict(**bindings, records=variant_records, root_means=root_means,
                root_labels=_json_safe(assignment["task_labels"]), support=support,
                depends_on_variant=dependency, dependency_failure=dependency_failure,
                backward_fit_attempts=attempted, backward_fits_completed=completed,
                wall_seconds=time.perf_counter()-phase_wall, cpu_seconds=time.process_time()-phase_cpu)
            records.extend(variant_records)
            variants[variant] = result
            emit(dict(event="variant", **result))
    return _json_safe(dict(schema_version="e0-stop-anchor-job-v1", identity=identity,
        planned_job=identity["planned_job"], provenance=provenance, arrays=archived,
        records=records, variants=variants,
        resources=dict(wall_seconds=time.perf_counter()-started, cpu_seconds=time.process_time()-cpu,
            sampler_attempts=sampler_attempts, backward_fit_attempts=fit_attempts,
            backward_fits_completed=fit_completed, model_calls=0, benchmark_executions=0, paid_usd=0),
        all_points_completed=len(records) == 24 and all(r["status"] == "completed" for r in records)))
