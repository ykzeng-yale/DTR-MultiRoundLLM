"""Bounded source-only recording/reconciliation for the STOP mechanism adapter.

No scheduler, wall-clock supervisor, execution freeze or sampling release lives
here. record_job requires supplied data; it is a connected fixture boundary.
All24 estimator slots become operationally attempted at shared job start, before
preparation. variant_started records actual processing separately; neither status
implies a fitted model. One writer, exclusive new directory, no resume or retry.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import stop_anchor_job as adapter
import stop_anchor_report as reporting
from regularization_job import _digest, _fingerprint, _point_record

ARRAYS = ("task", "S", "A", "B", "elig", "Y")
FOLDS = ("task_labels", "task_index", "task_fold_ids", "episode_fold_ids")


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)+"\n").encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def planned_identities(plan):
    raw = (adapter.ROOT / plan["seed_table_path"]).read_bytes()
    if sha(raw) != plan["seed_table_sha256"]:
        raise ValueError("seed table hash mismatch")
    jobs = [{"replicate": int(r["replicate"]), "data_seed": r["data_seed"], "fold_seed": r["fold_seed"]}
            for r in csv.DictReader(raw.decode().splitlines())]
    if [j["replicate"] for j in jobs] != list(range(96)):
        raise ValueError("complete ordered96-job plan required")
    return [adapter.expected_job_identity(plan, j) for j in jobs]


class OutputCap(RuntimeError):
    pass


class Recorder:
    def __init__(self, root, plan, *, output_bytes=268435456):
        if type(output_bytes) is not int or not 1 <= output_bytes <= 268435456:
            raise ValueError("byte ceiling must be1..268435456")
        self.identities = planned_identities(plan)
        self.sources = {p: sha((adapter.ROOT/p).read_bytes()) for p in adapter.SOURCE_PATHS}
        self.root = Path(root)
        self.root.mkdir(parents=False, exist_ok=False)
        self.limit = output_bytes
        self.events = []
        self._write("manifest.json", encoded({"schema_version": "e0-stop-recording-v1", "plan": plan,
            "identities": self.identities, "source_sha256": self.sources,
            "output_bytes_cap": self.limit, "execution_released": False,
            "classification": "source recording component; not a supervised execution release"}))

    def _reserve(self, size):
        used = sum(p.stat().st_size for p in self.root.iterdir() if p.is_file())
        if used+size > self.limit:
            raise OutputCap("recording byte ceiling exhausted")

    def _write(self, name, raw):
        path = self.root / name
        if path.parent != self.root or path.exists() or path.is_symlink():
            raise ValueError("artifact must be a new direct child")
        self._reserve(len(raw))
        temp = self.root / (name+".tmp")
        with temp.open("xb") as f:
            f.write(raw); f.flush(); os.fsync(f.fileno())
        # link is exclusive; a concurrent target can never be overwritten.
        os.link(temp, path)
        temp.unlink()
        fd = os.open(self.root, os.O_RDONLY)
        try: os.fsync(fd)
        finally: os.close(fd)

    def _append(self, event):
        event = json.loads(encoded({**event, "utc": datetime.now(timezone.utc).isoformat()}))
        # Validate each state transition before persisting it.
        _reconcile(self.events+[event], self.identities, self.sources)
        raw = encoded(event)
        self._reserve(len(raw))
        path = self.root / "events.jsonl"
        if path.is_symlink():
            raise ValueError("symlink journal refused")
        first = not path.exists()
        with path.open("ab") as f:
            f.write(raw); f.flush(); os.fsync(f.fileno())
        if first:
            fd = os.open(self.root, os.O_RDONLY)
            try: os.fsync(fd)
            finally: os.close(fd)
        self.events.append(event)

    def start(self, job):
        if (not isinstance(job, dict) or set(job) != {"replicate", "data_seed", "fold_seed"}
                or type(job["replicate"]) is not int or not 0 <= job["replicate"] < 96
                or any(type(job[k]) is not str for k in ("data_seed", "fold_seed"))):
            raise ValueError("job requires typed replicate and exact seed strings")
        identity = self.identities[job["replicate"]]
        if identity["job"] != job:
            raise ValueError("unbound job")
        self._append({"event": "job_started", "identity": identity,
                      "estimator_ids": list(reporting.ESTIMATORS)})

    def retain(self, event):
        if event.get("event") == "prepared":
            payload = event.get("arrays")
            if not isinstance(payload, dict) or set(payload) != set(ARRAYS):
                raise ValueError("missing exact minimal arrays")
            arrays = {}
            for name, desc in payload.items():
                if set(desc) != {"dtype", "shape", "values"}:
                    raise ValueError("invalid array descriptor")
                dtype = np.dtype(desc["dtype"])
                if dtype.hasobject or dtype.kind not in "biuf":
                    raise ValueError("unsafe array dtype")
                value = np.asarray(desc["values"], dtype=dtype)
                if list(value.shape) != desc["shape"] or not np.isfinite(value).all():
                    raise ValueError("nonfinite or misaligned array")
                arrays[name] = value
            prov = event["provenance"]
            if _fingerprint(arrays) != prov["dataset"]:
                raise ValueError("actual minimal arrays do not match fingerprint")
            folds = prov["folds"]
            if _digest({k: folds[k] for k in FOLDS}) != folds["sha256"]:
                raise ValueError("actual fold hash mismatch")
            for name in FOLDS:
                value = np.asarray(folds[name])
                if value.dtype.kind not in "iu":
                    raise ValueError("integer numbered-root fold payload required")
                arrays["fold_"+name] = value
            _validate_archive(arrays, prov)
            clean = {k:v for k,v in event.items() if k != "arrays"}
            # Refuse bad identity/order/source before writing an orphan archive.
            _reconcile(self.events+[{**clean, "archive": {}}], self.identities, self.sources)
            output = io.BytesIO()
            np.savez(output, **arrays)
            raw = output.getvalue()
            name = f"dataset_{event['identity']['job']['replicate']:03d}.npz"
            self._write(name, raw)
            clean["archive"] = {"path": name, "bytes": len(raw), "sha256": sha(raw)}
            self._append(clean)
        else:
            self._append(event)

    def finish(self, job, resources):
        self._append({"event": "job_complete", "identity": self.identities[job["replicate"]],
                      "resources": resources})


def record_job(recorder, job, *, data):
    """Connected supplied-data fixture; no sampler invocation is permitted here."""
    if data is None:
        raise ValueError("supplied data required; no sampling release")
    recorder.start(job)
    result = adapter.evaluate_job(recorder_plan(recorder), job, data=data, on_event=recorder.retain)
    recorder.finish(job, result["resources"])
    return result


def recorder_plan(recorder):
    return json.loads((recorder.root/"manifest.json").read_bytes())["plan"]


def _validate_archive(arrays, prov):
    minimal = {k:arrays[k] for k in ARRAYS}
    if _fingerprint(minimal) != prov["dataset"]:
        raise ValueError("archive data fingerprint mismatch")
    fold = {k:arrays["fold_"+k].tolist() for k in FOLDS}
    if any(fold[k] != prov["folds"][k] for k in FOLDS) or _digest(fold) != prov["folds"]["sha256"]:
        raise ValueError("archive fold payload mismatch")
    # Revalidate actual grouping, not just self-consistent hashes.
    validated, _ = adapter.anchored._validated(minimal, 3, np.array([.2]*5))
    tasks = np.asarray(validated["task"], dtype=int)
    if tasks.shape != (9200,) or not np.array_equal(np.unique(tasks), np.arange(230)) or not np.all(np.bincount(tasks) == 40):
        raise ValueError("archive violates230-root/40-trajectory contract")
    behavior = adapter.sim.make_beh(2.5, .02, gz=0.)
    active = validated["elig"]
    if not np.allclose(validated["B"][active], behavior[0, validated["S"][active], validated["A"][active]], rtol=0, atol=1e-14):
        raise ValueError("archive active propensity differs from fixed logger")
    assignment = adapter.anchored._fold_assignment(validated["task"], 3, 0, np.array(fold["episode_fold_ids"]))
    for k in FOLDS:
        if assignment[k].tolist() != fold[k]:
            raise ValueError("fold payload does not describe actual root partition")


def _reconcile(events, identities, sources):
    records, states = {}, {}
    active, next_rep = None, 0
    for event in events:
        ident = event.get("identity")
        if not isinstance(ident, dict) or type(ident.get("job", {}).get("replicate")) is not int:
            raise ValueError("missing bound identity")
        rep = ident["job"]["replicate"]
        if not 0 <= rep < 96 or ident != identities[rep]:
            raise ValueError("event identity mismatch")
        job = ident["planned_job"]
        kind = event.get("event")
        if kind == "job_started":
            if active is not None or rep != next_rep or event.get("estimator_ids") != list(reporting.ESTIMATORS):
                raise ValueError("out-of-order or duplicate shared job start")
            states[rep] = {"prepared": None, "started": [], "returned": [], "complete": False, "preparation_failed": False}
            active = rep
            for e in reporting.ESTIMATORS:
                records[rep,e] = {**job, "estimator": e, "status": "attempted", "reason": "shared_job_started_no_terminal_record"}
            continue
        if active != rep:
            raise ValueError("event lacks active shared job")
        state = states[rep]
        if kind in {"prepared", "job_failed"}:
            if state["prepared"] is not None or state["started"] or state["returned"] or state["preparation_failed"]:
                raise ValueError("duplicate or late preparation")
            if event.get("provenance", {}).get("source_sha256") != sources:
                raise ValueError("source binding mismatch")
            if kind == "prepared":
                if event.get("records") or "arrays" in event or "archive" not in event:
                    raise ValueError("prepared requires archived data, no point records")
                state["prepared"] = (event["provenance"]["dataset"]["sha256"],event["provenance"]["folds"]["sha256"])
                state["root_labels"] = event["provenance"]["folds"]["task_labels"]
                continue
            state["preparation_failed"] = True
            if event.get("failure_phase") != "preparation":
                raise ValueError("job failure must identify preparation phase")
            expected = list(reporting.ESTIMATORS)
        elif kind in {"variant_started", "variant"}:
            if state["prepared"] is None or state["preparation_failed"] or (event.get("dataset_sha256"),event.get("fold_sha256")) != state["prepared"]:
                raise ValueError("missing or mismatched data/fold binding")
            variants = list(adapter.anchored.VARIANTS)
            variant = event.get("variant")
            expected = [f"{variant}:{method}" for method in ("plugin", "dr")]
            if kind == "variant_started":
                if len(state["started"]) != len(state["returned"])//2 or len(state["started"]) >= 12 or variant != variants[len(state["started"])] or event.get("estimator_ids") != expected:
                    raise ValueError("variant start order or identity mismatch")
                state["started"].append(variant)
                continue
            if not state["started"] or variant != state["started"][-1] or any(e in state["returned"] for e in expected):
                raise ValueError("terminal variant missing start or duplicated")
        elif kind == "job_complete":
            if set(state["returned"]) != set(reporting.ESTIMATORS):
                raise ValueError("job completion lacks24 terminal slots")
            state["complete"] = True
            active = None; next_rep += 1
            continue
        else:
            raise ValueError("unknown event")
        rows = event.get("records", [])
        if [r.get("estimator") for r in rows] != expected:
            raise ValueError("terminal event estimator set mismatch")
        if kind == "variant" and event.get("root_labels") != state["root_labels"]:
            raise ValueError("terminal root means use wrong root-label order")
        for row in rows:
            reporting._record(row, {rep:job})
            if {k:row.get(k) for k in job} != job or row.get("status") not in {"completed", "failed"}:
                raise ValueError("terminal record binding/status mismatch")
            if kind == "job_failed" and row["status"] != "failed":
                raise ValueError("preparation failure cannot complete point estimate")
            if row["estimator"] in state["returned"]:
                raise ValueError("duplicate terminal estimator")
            if row["status"] == "completed":
                method = row["estimator"].split(":")[-1]
                means = np.asarray(event.get("root_means", {}).get(method), dtype=float)
                if means.shape != (230,) or not np.isfinite(means).all():
                    raise ValueError("completed point requires230 finite root means")
                recomputed = _point_record(ident, row["estimator"], means)
                if recomputed["estimate"] != row["estimate"] or (row.get("interval", {}).get("status") == "valid" and recomputed.get("interval") != row["interval"]):
                    raise ValueError("point or interval does not reconcile with saved root means")
            records[rep,row["estimator"]] = row
            state["returned"].append(row["estimator"])
    return list(records.values()), states


def reconcile_recording(root):
    """Read a byte snapshot; writer exit is unverified. Count, do not use, a torn tail."""
    root = Path(root)
    manifest = json.loads((root/"manifest.json").read_bytes())
    identities = planned_identities(manifest["plan"])
    if manifest["identities"] != identities:
        raise ValueError("manifest identity mismatch")
    sources = {p: sha((adapter.ROOT/p).read_bytes()) for p in adapter.SOURCE_PATHS}
    if sources != manifest["source_sha256"]:
        raise ValueError("recorded source differs from current review source")
    raw = (root/"events.jsonl").read_bytes() if (root/"events.jsonl").exists() else b""
    pieces = raw.splitlines(keepends=True)
    ignored = 0
    if pieces and not pieces[-1].endswith(b"\n"):
        ignored = len(pieces.pop())
    events = [json.loads(line) for line in pieces]
    records, states = _reconcile(events, identities, sources)
    for event in events:
        if event["event"] != "prepared": continue
        archive = event["archive"]
        expected = f"dataset_{event['identity']['job']['replicate']:03d}.npz"
        if archive["path"] != expected or (root/expected).is_symlink():
            raise ValueError("archive path mismatch")
        raw_archive = (root/expected).read_bytes()
        if len(raw_archive) != archive["bytes"] or sha(raw_archive) != archive["sha256"]:
            raise ValueError("archive bytes mismatch")
        with np.load(io.BytesIO(raw_archive), allow_pickle=False) as data:
            if set(data.files) != set(ARRAYS)|{"fold_"+k for k in FOLDS}:
                raise ValueError("archive field mismatch")
            _validate_archive(dict(data), event["provenance"])
    complete = len(states) == 96 and all(s["complete"] for s in states.values()) and ignored == 0
    summary = reporting.summarize_stop_anchor([i["planned_job"] for i in identities],records,
        manifest["plan"]["deterministic_truth_reference"],truncated=not complete)
    used = sum(p.stat().st_size for p in root.iterdir() if p.is_file())
    if used > manifest["output_bytes_cap"]:
        raise ValueError("saved output exceeds recorded ceiling")
    return {"summary":summary,"audit":{"ignored_trailing_bytes":ignored,"job_states":states,
        "recorded_jobs_complete":complete,"total_retained_bytes":used,"model_calls":0,
        "writer_exit_verified":False,"supervised_run_verified":False,
        "interrupted_actual_fit_counts":"unknown for any started variant without terminal fit counters",
        "scope":"No source-only recording establishes an executed supervised study. Attempted means shared job entered, not fit completed. Missing starts in a truncated final line are unknowable."}}
