#!/usr/bin/env python3
"""Single-child bounded STOP study; source availability is not a sampling release.

The supervisor imports only stdlib. A committed release, matching pinned sources,
exact environment and fresh operator resource/lease inspection are required.
All child imports, exact truth, sampling, fits, recording and reporting share one
600-second clock. Cooperative writes include headers, archives, temporaries and
summary under a total 256MiB ceiling, with 4096 bytes reserved for the supervisor.
The monitor detects uncooperative output drift; this is not a filesystem sandbox.
No resume, retry, replacement seed, alternate run ID or overwrite is implemented.
"""
from __future__ import annotations

import time
STARTED = time.monotonic()
STARTED_UTC = None
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import re
import resource
import secrets
import signal
import subprocess
import sys

STARTED_UTC = datetime.now(timezone.utc).isoformat()
_BOUND_OUTPUT = None
ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "e0_stop_anchor_20260923_lead01"
RESERVE = 4096
TRUTH = .6459770061744536
CAPS = dict(cpu_workers=1, outer_seconds=600, output_bytes=268435456, paid_usd=0,
            model_calls=0, benchmark_executions=0, prompt_tokens=0, completion_tokens=0)
THREAD_ENV = {k: "1" for k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                                "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")}
REQUIRED_SOURCES = tuple("experiments/e0/" + name + ".py" for name in (
    "stop_anchor_job", "stop_anchor_estimators", "stop_anchor_journal", "stop_anchor_report",
    "regularization_job", "regularization_report", "regularized_history_estimators",
    "history_estimators", "estimators", "simulator")) + (
    "experiments/e0/stop_anchor_comparison_plan_v1.json", "experiments/e0/stop_anchor_seed_plan_v1.csv",
    "scripts/run_stop_anchor_comparison.py", "scripts/check_regularization_truth.py",
    "scripts/reconcile_stop_anchor_run.py")


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)+"\n").encode()


def load_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    def invalid(value):
        raise ValueError("nonfinite JSON constant: "+value)
    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("nonfinite JSON number")
        return number
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid, parse_float=finite_float)
    if not isinstance(value, dict):
        raise ValueError("JSON object required")
    return value


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _environment():
    return dict(python=platform.python_version(), numpy=importlib.metadata.version("numpy"),
                scipy=importlib.metadata.version("scipy"), bit_generator="PCG64")


def _git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], timeout=5)


class OutputCap(RuntimeError):
    pass


class Deadline(RuntimeError):
    pass


class ByteBudget:
    """Root writes count every descendant file, including archive/orphan/temp bytes."""
    def __init__(self, root, limit):
        self.root, self.limit = Path(root), limit

    def used(self):
        total = 0
        for p in self.root.rglob("*"):
            if p.is_symlink():
                raise ValueError("symlink artifact refused")
            if p.is_file():
                try:
                    total += p.stat().st_size
                except FileNotFoundError:
                    pass  # Writer may exclusively link then remove a temporary name.
        return total

    def write_bytes(self, name, raw):
        path = self.root/name
        if path.parent != self.root or name in ("", ".", "..", "supervisor.json"):
            raise ValueError("only new direct root artifact names are allowed")
        temp = self.root/(name+".tmp")
        if path.exists() or path.is_symlink() or temp.exists() or temp.is_symlink():
            raise FileExistsError(path)
        # During link/unlink both names are counted by a summed-file-size monitor.
        if self.used()+2*len(raw) > self.limit:
            raise OutputCap("total output payload ceiling exhausted")
        with temp.open("xb") as f:
            f.write(raw); f.flush(); os.fsync(f.fileno())
        os.link(temp, path)
        temp.unlink()
        _sync_directory(self.root)

    def write_json(self, name, value):
        self.write_bytes(name, encoded(value))


def _sync_directory(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _freeze_binding(freeze_path, *, commit=None):
    """Bind the exact freeze blob to a retained, reachable Git revision."""
    freeze_path = Path(freeze_path).resolve()
    relative = freeze_path.relative_to(ROOT).as_posix()
    revision = _git("rev-parse", "HEAD").decode().strip() if commit is None else commit
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("full committed freeze revision required")
    if _git("show", revision+":"+relative) != freeze_path.read_bytes():
        raise ValueError("execution freeze must be committed and unchanged")
    _git("merge-base", "--is-ancestor", revision, "HEAD")
    return dict(freeze_repository_path=relative, freeze_commit=revision)


def validate_release(freeze_path, receipt_path, *, return_binding=False):
    """Check bytes and declared local availability, not the truth of an operator claim."""
    freeze_path = Path(freeze_path).resolve()
    binding = _freeze_binding(freeze_path)
    raw = freeze_path.read_bytes()
    freeze = load_json(raw)
    if (freeze.get("schema_version") != "e0-stop-anchor-execution-freeze-v1"
            or freeze.get("execution_released") is not True
            or freeze.get("decision_id") != "LEAD-E0-STOP-01"
            or freeze.get("planned_run_id") != RUN_ID
            or freeze.get("deterministic_truth") != TRUTH
            or encoded(freeze.get("caps")) != encoded(CAPS)):
        raise ValueError("missing release or changed run/truth/resource contract")
    sources, revision = freeze.get("source_sha256", {}), freeze.get("source_commit", "")
    if (set(sources) != set(REQUIRED_SOURCES) or not re.fullmatch(r"[0-9a-f]{40}", revision)
            or any(not isinstance(v, str) or not re.fullmatch(r"[0-9a-f]{64}", v) for v in sources.values())):
        raise ValueError("exact source identity/hash set required")
    _git("merge-base", "--is-ancestor", revision, binding["freeze_commit"])
    for path, expected in sources.items():
        if sha(ROOT/path) != expected or hashlib.sha256(_git("show", revision+":"+path)).hexdigest() != expected:
            raise ValueError("source differs from committed freeze: "+path)
    if freeze.get("environment") != _environment():
        raise ValueError("environment differs from frozen versions")
    receipt = load_json(Path(receipt_path).read_bytes())
    checked = datetime.fromisoformat(receipt["checked_utc"].replace("Z", "+00:00"))
    if checked.tzinfo is None:
        raise ValueError("resource timestamp must specify timezone")
    age = (datetime.now(timezone.utc)-checked).total_seconds()
    if (not 0 <= age <= 300 or receipt.get("planned_run_id") != RUN_ID
            or receipt.get("no_active_conflicting_lease") is not True
            or receipt.get("one_cpu_available") is not True
            or receipt.get("host") != platform.node()
            or receipt.get("freeze_sha256") != hashlib.sha256(raw).hexdigest()
            or not isinstance(receipt.get("inspection"), dict) or not receipt["inspection"]
            or any(not isinstance(receipt.get(k), str) or not receipt[k].strip() for k in ("evidence", "lease_scope"))):
        raise ValueError("fresh bound host/resource/lease inspection required")
    return (freeze, receipt, binding) if return_binding else (freeze, receipt)


def _children_cpu():
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return usage.ru_utime + usage.ru_stime


def _kill_and_observe(child, deadline):
    """Report signaling failures separately; only wait/poll establishes exit."""
    errors = []
    if child.poll() is not None:
        return True, errors
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except OSError as exc:
        errors.append(f"killpg: {type(exc).__name__}: {exc}"[:250])
        # This Popen owns the direct child. A refused group signal may still
        # permit killing that child; neither success nor failure proves exit.
        if child.poll() is None:
            try:
                child.kill()
            except OSError as direct_exc:
                errors.append(f"child.kill: {type(direct_exc).__name__}: {direct_exc}"[:250])
    try:
        child.wait(timeout=max(.001, deadline-time.monotonic()))
    except subprocess.TimeoutExpired:
        return child.poll() is not None, errors
    except OSError as exc:
        errors.append(f"wait: {type(exc).__name__}: {exc}"[:250])
        return child.poll() is not None, errors
    return child.poll() is not None, errors


def _supervise(output, command, *, total_seconds, output_bytes, manifest,
               started_monotonic=None, header_bytes=None):
    """One owned child/session; small caps and tiny nonnumeric children are test seams."""
    started = STARTED if started_monotonic is None else started_monotonic
    if (isinstance(total_seconds, bool) or not math.isfinite(total_seconds) or total_seconds <= 0
            or type(output_bytes) is not int or output_bytes <= RESERVE):
        raise ValueError("invalid supervision limits")
    output = Path(output).resolve()
    deadline, cleanup = started+total_seconds, min(2., total_seconds/4)
    token = secrets.token_hex(16)
    bound = dict(manifest, supervisor_pid=os.getpid(), supervisor_token=token,
                 started_monotonic=started, deadline_monotonic=deadline, cleanup_seconds=cleanup,
                 output_directory=str(output), output_bytes_cap=output_bytes,
                 payload_bytes_cap=output_bytes-RESERVE)
    headers = {} if header_bytes is None else dict(header_bytes)
    if any(name not in ("execution_freeze.json", "resource_receipt.json") for name in headers):
        raise ValueError("unknown root header artifact")
    root_raw = encoded(bound)
    if 2*(len(root_raw)+sum(len(b) for b in headers.values())) > output_bytes-RESERVE:
        raise OutputCap("root headers exceed reserved payload budget")
    output.mkdir(parents=True, exist_ok=False)
    budget = ByteBudget(output, output_bytes-RESERVE)
    child, reason, error, cpu_start = None, "startup_failure", None, _children_cpu()
    try:
        budget.write_bytes("run_manifest.json", root_raw)
        for name, raw in headers.items():
            budget.write_bytes(name, raw)
        if time.monotonic() >= deadline-cleanup:
            reason = "startup_deadline"
        else:
            env = os.environ.copy()
            env.update(THREAD_ENV)
            env.update(E0_STOP_SUPERVISOR_PID=str(os.getpid()), E0_STOP_SUPERVISOR_TOKEN=token,
                       E0_STOP_OUTPUT_PAYLOAD_CAP=str(output_bytes-RESERVE))
            argv = [str(a).replace("{output}", str(output)) for a in command]
            child = subprocess.Popen(argv, cwd=ROOT, env=env, start_new_session=True,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            while child.poll() is None:
                if budget.used() > budget.limit:
                    reason = "output_cap_violation"
                    break
                if time.monotonic() >= deadline-cleanup:
                    reason = "outer_time_cap"
                    break
                time.sleep(min(.02, max(0., deadline-cleanup-time.monotonic())))
            else:
                reason = ("child_complete" if child.returncode == 0 else
                          "output_cap_reached" if child.returncode == 3 else
                          "outer_time_cap" if child.returncode == 4 else "child_failed")
    except BaseException as exc:
        error = exc
        reason = "startup_failure" if child is None else "supervisor_error"
    finally:
        observed, signaling_errors = _kill_and_observe(child, deadline) if child is not None else (False, [])
        if child is not None and not observed:
            reason = "cleanup_unconfirmed"
        payload_bytes = budget.used()
        if payload_bytes > budget.limit:
            reason = "output_cap_violation"
        wall = time.monotonic()-started
        if wall > total_seconds and reason == "child_complete":
            reason = "outer_time_cap"
        final = dict(schema_version="e0-stop-anchor-supervisor-v1", stop_reason=reason,
            child_started=child is not None, child_pid=child.pid if child else None,
            child_returncode=child.returncode if child else None, child_exit_observed=observed,
            signaling_errors=signaling_errors,
            wall_seconds=wall, outer_seconds_cap=total_seconds,
            wall_seconds_scope="Module monotonic start through observed child cleanup/output accounting; final receipt serialization and fsync excluded",
            owned_child_cpu_seconds=max(0., _children_cpu()-cpu_start) if observed else None,
            payload_bytes=payload_bytes, output_bytes_cap=output_bytes,
            within_wall_cap=wall <= total_seconds, within_output_cap=False, total_bytes=0,
            completed_artifacts_retained=True, error=f"{type(error).__name__}: {error}"[:300] if error else None,
            note="No retry/resume. Partial job records remain incomplete. Exit observed is distinct from kill sent.")
        # Fixed-point size includes this final receipt; it is the only reserve user.
        for _ in range(8):
            final["total_bytes"] = payload_bytes+len(encoded(final))
            final["within_output_cap"] = final["total_bytes"] <= output_bytes
        raw = encoded(final)
        if len(raw) > RESERVE:
            raise OutputCap("supervisor receipt exceeds reserve")
        with (output/"supervisor.json").open("xb") as f:
            f.write(raw); f.flush(); os.fsync(f.fileno())
        _sync_directory(output)
    if error is not None:
        raise error
    return final


def _worker(freeze_path, output, receipt_path):
    """Actual guarded path. Tests replace the adapter boundary, never a sampler."""
    global _BOUND_OUTPUT
    _BOUND_OUTPUT = None
    output = Path(output).resolve()
    if output != (ROOT/"work"/RUN_ID).resolve():
        raise ValueError("only the fixed repository work/run-ID path is authorized")
    freeze, receipt = validate_release(freeze_path, receipt_path)
    manifest = load_json((output/"run_manifest.json").read_bytes())
    binding = _freeze_binding(freeze_path, commit=manifest.get("freeze_commit", ""))
    if manifest.get("freeze_repository_path") != binding["freeze_repository_path"]:
        raise ValueError("original committed freeze path differs from run manifest")
    _git("merge-base", "--is-ancestor", freeze["source_commit"], binding["freeze_commit"])
    deadline, started = manifest.get("deadline_monotonic", 0), manifest.get("started_monotonic", 0)
    token = manifest.get("supervisor_token", "")
    if (set(p.name for p in output.iterdir()) != {"run_manifest.json", "execution_freeze.json", "resource_receipt.json"}
            or manifest.get("schema_version") != "e0-stop-anchor-run-v1" or manifest.get("run_id") != RUN_ID
            or manifest.get("source_commit") != freeze["source_commit"] or manifest.get("freeze") != freeze
            or manifest.get("resource_receipt") != receipt
            or manifest.get("output_directory") != str(output)
            or manifest.get("freeze_sha256") != sha(freeze_path)
            or manifest.get("resource_receipt_sha256") != sha(receipt_path)
            or manifest.get("freeze_path") != "execution_freeze.json"
            or manifest.get("resource_receipt_path") != "resource_receipt.json"
            or (output/"execution_freeze.json").read_bytes() != Path(freeze_path).read_bytes()
            or (output/"resource_receipt.json").read_bytes() != Path(receipt_path).read_bytes()
            or manifest.get("supervisor_pid") != os.getppid()
            or os.environ.get("E0_STOP_SUPERVISOR_PID") != str(os.getppid())
            or not isinstance(token, str) or not re.fullmatch(r"[0-9a-f]{32}", token)
            or os.environ.get("E0_STOP_SUPERVISOR_TOKEN") != token
            or any(os.environ.get(k) != v for k, v in THREAD_ENV.items())
            or manifest.get("output_bytes_cap") != CAPS["output_bytes"]
            or manifest.get("payload_bytes_cap") != CAPS["output_bytes"]-RESERVE
            or os.environ.get("E0_STOP_OUTPUT_PAYLOAD_CAP") != str(CAPS["output_bytes"]-RESERVE)
            or type(deadline) not in (int, float) or type(started) not in (int, float)
            or not math.isfinite(deadline) or not math.isfinite(started)
            or abs((deadline-started)-600) > 1e-6 or manifest.get("cleanup_seconds") != 2.
            or time.monotonic() >= deadline-2.):
        raise ValueError("worker lacks matching live parent/run/deadline/release binding")
    os.kill(os.getppid(), 0)  # Existence/permission probe, not a termination signal.
    _BOUND_OUTPUT = output
    import numpy as np
    import scipy
    if freeze["environment"] != dict(python=platform.python_version(), numpy=np.__version__,
                                      scipy=scipy.__version__, bit_generator="PCG64"):
        raise ValueError("actual imported environment differs from freeze")
    sys.path.insert(0, str(ROOT/"experiments/e0"))
    sys.path.insert(0, str(ROOT/"scripts"))
    import stop_anchor_job as adapter
    import stop_anchor_journal as journal
    import stop_anchor_report as reporting
    from check_regularization_truth import forward_value, EXPECTED
    budget = ByteBudget(output, CAPS["output_bytes"]-RESERVE)
    budget.write_json("worker_receipt.json", dict(schema_version="e0-stop-anchor-worker-v1",
        worker_pid=os.getpid(), supervisor_pid=os.getppid(), imports_verified_utc=datetime.now(timezone.utc).isoformat(),
        freeze_sha256=sha(freeze_path), resource_receipt_sha256=sha(receipt_path), environment=freeze["environment"]))
    plan = load_json((ROOT/adapter.PLAN_PATH).read_bytes())
    truth, _, _ = forward_value()
    if truth != TRUTH or EXPECTED != TRUTH or plan["deterministic_truth_reference"] != TRUTH:
        raise ValueError("exact reference truth binding mismatch")
    writer = journal.Recorder(output/"records", plan, output_bytes=budget.limit-budget.used())
    if writer.sources != {p: freeze["source_sha256"][p] for p in adapter.SOURCE_PATHS}:
        raise ValueError("recording sources differ from execution freeze")
    def checkpoint():
        if time.monotonic() >= deadline-2.:
            raise Deadline("outer deadline reached; no resume")
        if budget.used() > budget.limit:
            raise OutputCap("total output payload cap exceeded")
    def retain(event):
        checkpoint()
        writer.retain(event)
    for identity in writer.identities:
        checkpoint()
        job = identity["job"]
        writer.start(job)
        artifact = adapter.evaluate_job(plan, job, data=None, on_event=retain)
        checkpoint()
        writer.finish(job, artifact["resources"])
    checkpoint()
    summary = reporting.summarize_stop_anchor([i["planned_job"] for i in writer.identities],
        writer.snapshot_records(), truth, truncated=False)
    checkpoint()
    writer._write("summary.json", journal.encoded(summary))
    checkpoint()


def main(argv=None):
    global _BOUND_OUTPUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resource-receipt", type=Path, required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.output.resolve() != (ROOT/"work"/RUN_ID).resolve():
        raise ValueError("only the fixed repository work/run-ID path is authorized")
    if args.worker:
        _BOUND_OUTPUT = None
        try:
            _worker(args.freeze.resolve(), args.output.resolve(), args.resource_receipt.resolve())
        except Deadline:
            return 4
        except Exception as exc:
            # The journal's cap exception is imported only on the worker branch.
            code = 3 if isinstance(exc, OutputCap) or (type(exc).__name__ == "OutputCap" and
                        type(exc).__module__ == "stop_anchor_journal") else 2
            try:
                if _BOUND_OUTPUT == args.output.resolve():
                    ByteBudget(args.output, CAPS["output_bytes"]-RESERVE).write_json("worker_failure.json",
                        dict(error_type=type(exc).__name__, reason=str(exc)[:1000], utc=datetime.now(timezone.utc).isoformat()))
            except Exception:
                pass  # Supervisor exit/bytes remain the authoritative incomplete-run evidence.
            return code
        return 0
    freeze, receipt, binding = validate_release(args.freeze, args.resource_receipt, return_binding=True)
    manifest = dict(schema_version="e0-stop-anchor-run-v1", run_id=RUN_ID,
        **binding,
        source_commit=freeze["source_commit"], freeze=freeze, freeze_sha256=sha(args.freeze),
        freeze_path="execution_freeze.json", resource_receipt=receipt,
        resource_receipt_sha256=sha(args.resource_receipt), resource_receipt_path="resource_receipt.json",
        started_utc=STARTED_UTC, model_calls=0, benchmark_executions=0,
        prompt_tokens=0, completion_tokens=0, paid_usd=0)
    command = [sys.executable, str(Path(__file__).resolve()), "--worker", "--freeze", str(args.freeze.resolve()),
               "--resource-receipt", str(args.resource_receipt.resolve()), "--output", "{output}"]
    final = _supervise(args.output, command, total_seconds=600, output_bytes=CAPS["output_bytes"], manifest=manifest,
        header_bytes={"execution_freeze.json": args.freeze.read_bytes(), "resource_receipt.json": args.resource_receipt.read_bytes()})
    return 0 if final["stop_reason"] == "child_complete" and final["child_exit_observed"] and final["within_output_cap"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
