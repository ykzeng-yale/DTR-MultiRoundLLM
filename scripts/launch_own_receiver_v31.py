#!/usr/bin/env python3
"""MRL-16 receiver-restart amendment (v3.1): ONE bounded launch of this project's own pinned 3B llama-server.

Refuses unless a committed owner agreement (shared-hardware window covering setup + >=60 min) is supplied.
Verifies all 26 pinned build hashes and the exact model digest; requires :8193 free and no other llama-server.
Launches the recorded shape: -m <frozen model_path> --alias qwen2.5-3b-instruct --port 8193 -ngl 99 -np 4
-c 32768 --jinja --host 127.0.0.1, with LLAMA_MEDIA_MARKER pinned to the frozen snapshot's marker (source
4fea119 tools/server/server-common.cpp get_media_marker(): a per-process random string unless this env var is
set; used only to substitute image/audio/video parts and in ASR transcription, never for text-only chat).
Readiness is detected from the server log (no HTTP). No generation request is ever sent. It records PID, exact
command, start/ready times and memory pressure, and writes launch.json. It does NOT run the preflight/diff
(scripts/receiver_preflight_mrl10.py + scripts/diff_receiver_snapshot_v31.py) and does not stop the server
on success (`--stop` does, only for the PID it recorded). Failed or interrupted startup terminates
and reaps its own child. Readiness does not replace the remaining preflight/refreeze checks.
"""
from __future__ import annotations
import argparse, hashlib, json, os, signal, subprocess, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "work/bin"
MANIFEST = ROOT / "experiments/env/llama_server_manifest.json"
SNAPSHOT = ROOT / "results/receiver_props_snapshot_8193.json"
MODEL_SHA = "626b4a6678b86442240e33df819e00132d3ba7dddfe1cdc4fbb18e0a9615c62d"
PORT = 8193
READY_MARKER = f"listening on http://127.0.0.1:{PORT}"


def now():
    return datetime.now(timezone.utc).isoformat()


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout


def committed_agreement(path):
    """Require current bytes to exist identically in HEAD, not merely the index."""
    try:
        relative = path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise SystemExit("Ownership record must be inside this repository") from exc
    saved = subprocess.run(["git", "show", f"HEAD:{relative}"], cwd=ROOT, capture_output=True)
    data = path.read_bytes()
    if saved.returncode != 0 or saved.stdout != data:
        raise SystemExit("Ownership record bytes are not committed identically in HEAD")
    record = json.loads(data)
    if not isinstance(record, dict):
        raise SystemExit("Ownership record must be a JSON object")
    return record, hashlib.sha256(data).hexdigest()


def launcher_provenance(agreement):
    """Bind the executing helper to committed bytes and an optional reservation pin."""
    path = Path(__file__).resolve()
    relative = path.relative_to(ROOT.resolve()).as_posix()
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True)
    if revision.returncode != 0:
        raise SystemExit("Cannot resolve committed launcher revision")
    head = revision.stdout.decode().strip()
    saved = subprocess.run(["git", "show", f"{head}:{relative}"], cwd=ROOT, capture_output=True)
    data = path.read_bytes()
    if saved.returncode != 0 or saved.stdout != data:
        raise SystemExit("Launcher source bytes are not committed identically in HEAD")
    digest = hashlib.sha256(data).hexdigest()
    if "launcher_sha256" in agreement and agreement["launcher_sha256"] != digest:
        raise SystemExit("Launcher SHA256 differs from the reservation pin")
    return {"source_head": head, "launcher_path": relative, "launcher_sha256": digest}


def utc(value):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None or result.utcoffset() != timedelta(0):
            raise ValueError("UTC timezone required")
        return result
    except (AttributeError, TypeError, ValueError) as exc:
        raise SystemExit("Ownership window requires explicit UTC timestamps") from exc


def ready_deadline(record, current):
    """Accept the shared reservation or collector ownership schema; keep >=60 min for A."""
    generic = "start_utc" in record or "hard_end_utc" in record
    keys = ("start_utc", "hard_end_utc") if generic else ("exclusive_window_start_utc", "exclusive_window_end_utc")
    try:
        start, end = (utc(record[k]) for k in keys)
    except KeyError as exc:
        raise SystemExit("Ownership record has no complete shared window") from exc
    if generic and "exclusive_window_start_utc" in record:
        if (start, end) != (utc(record["exclusive_window_start_utc"]), utc(record.get("exclusive_window_end_utc"))):
            raise SystemExit("Conflicting ownership windows")
    latest = end - timedelta(seconds=3600)
    if "phase_a_latest_start_utc" in record:
        latest = min(latest, utc(record["phase_a_latest_start_utc"]))
    if not start <= current < end or current >= latest:
        raise SystemExit("Outside launch window or less than 60 minutes remain for Phase A onward")
    return min(current + timedelta(seconds=600), latest)


def terminate_owned_child(proc):
    """Signal only this Popen child, with bounded escalation and reaping."""
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
    else:
        proc.wait(timeout=5)


def process_identity(pid):
    """Read birth time and command without a shell; absence is distinct from an inspection error."""
    if type(pid) is not int or pid <= 1:
        raise SystemExit("Invalid recorded receiver PID")
    result = subprocess.run(["ps", "-p", str(pid), "-o", "lstart=", "-o", "command="],
                            capture_output=True, text=True, timeout=2)
    if result.returncode == 1 and not result.stdout.strip():
        return None
    if result.returncode != 0 or not result.stdout.strip():
        raise SystemExit("Cannot inspect recorded receiver identity; refusing to signal")
    return " ".join(result.stdout.split())


def stop_recorded_receiver(out):
    """Bounded shutdown of the exact process created by this launcher, with an observed-exit receipt.

    A different process at the PID is never signalled. This process is not necessarily our child,
    so disappearance can be observed but an exit code cannot be reconstructed.
    """
    path = Path(out) / "launch.json"
    rec = json.loads(path.read_text())
    pid, expected = rec.get("pid"), rec.get("process_identity")
    if not isinstance(expected, str) or not expected:
        raise SystemExit("Launch record lacks process identity; do not infer ownership from PID alone")
    actual = process_identity(pid)
    if actual is not None and actual != expected:
        raise SystemExit("Recorded PID now identifies another process; refusing to signal")
    rec["stop_requested_utc"] = now()
    rec["stop_signals"] = []
    for sig in (signal.SIGTERM, signal.SIGKILL):
        actual = process_identity(pid)
        if actual is None:
            break
        if actual != expected:
            rec["stop_error"] = "process identity changed during cleanup; no further signal"
            path.write_text(json.dumps(rec, indent=1) + "\n")
            raise SystemExit(rec["stop_error"])
        try:
            os.kill(pid, sig)
            rec["stop_signals"].append(int(sig))
        except ProcessLookupError:
            break
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            actual = process_identity(pid)
            if actual is None:
                break
            if actual != expected:
                rec["stop_error"] = "process identity changed during cleanup; no further signal"
                path.write_text(json.dumps(rec, indent=1) + "\n")
                raise SystemExit(rec["stop_error"])
            time.sleep(0.1)
        if actual is None:
            break
    rec["exit_observed"] = process_identity(pid) is None
    rec["stopped_utc"] = now() if rec["exit_observed"] else None
    rec["exit_observation_note"] = "PID absent after identity-checked cleanup; exit code unavailable"
    path.write_text(json.dumps(rec, indent=1) + "\n")
    if not rec["exit_observed"]:
        raise SystemExit("Owned receiver exit unverified after bounded cleanup; report blocked")
    print(json.dumps({"stopped_pid": pid, "utc": rec["stopped_utc"], "exit_observed": True}))
    return rec


def verify():
    m = json.loads(MANIFEST.read_text())
    bad = [n for n, rec in m["files"].items() if not (BIN / n).exists() or hashlib.sha256((BIN / n).read_bytes()).hexdigest() != rec["sha256"]]
    if bad:
        raise SystemExit(f"Pinned build hash mismatch/missing: {bad}")
    snap = json.loads(SNAPSHOT.read_text())
    mp = snap["model_path"]
    if hashlib.sha256(Path(mp).read_bytes()).hexdigest() != MODEL_SHA:
        raise SystemExit("Model digest mismatch")
    return snap, mp, len(m["files"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ownership", type=Path, help="committed owner agreement JSON (required to launch)")
    ap.add_argument("--out", type=Path, required=True, help="new receiver record directory")
    ap.add_argument("--stop", action="store_true", help="terminate ONLY the PID recorded in <out>/launch.json")
    a = ap.parse_args(argv)
    if a.stop:
        stop_recorded_receiver(a.out)
        return
    if a.ownership is None or not a.ownership.exists():
        raise SystemExit("Refusing to launch: no committed owner agreement (shared-hardware window) supplied")
    agreement, agreement_sha = committed_agreement(a.ownership)
    provenance = launcher_provenance(agreement)
    setup_deadline = ready_deadline(agreement, datetime.now(timezone.utc))
    if a.out.exists():
        raise SystemExit("Refusing to overwrite an existing receiver record")
    snap, mp, nfiles = verify()
    if sh(f"lsof -nP -iTCP:{PORT} -sTCP:LISTEN"):
        raise SystemExit(f"Port {PORT} is not free")
    if sh("ps -Ao command | grep -v grep | grep llama-server").strip():
        raise SystemExit("Another llama-server is running; refusing (one server at a time)")
    # Hashing can take time: recheck immediately before spawning, without extending setup.
    setup_deadline = min(setup_deadline, ready_deadline(agreement, datetime.now(timezone.utc)))
    a.out.mkdir(parents=True)
    cmd = [str(BIN / "llama-server"), "-m", mp, "--alias", "qwen2.5-3b-instruct", "--port", str(PORT), "-ngl", "99",
           "-np", "4", "-c", "32768", "--jinja", "--host", "127.0.0.1"]
    env = dict(os.environ, LLAMA_MEDIA_MARKER=snap["media_marker"])
    mem_before = {"swap": sh("sysctl -n vm.swapusage").strip(), "vm_stat": sh("vm_stat | head -6")}
    if datetime.now(timezone.utc) >= setup_deadline:
        raise SystemExit("Setup deadline passed before spawn; no server launched")
    if launcher_provenance(agreement) != provenance:
        raise SystemExit("Launcher revision changed during setup; refusing to spawn")
    log = open(a.out / "llama_server.log", "w")
    started = now(); t0 = time.monotonic()
    try:
        proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
    except BaseException:
        log.close()
        raise
    rec = {"schema": "mrl16-own-receiver-launch-v31", **provenance, "pid": proc.pid, "command": cmd,
           "env_pinned": {"LLAMA_MEDIA_MARKER": snap["media_marker"]}, "host": os.uname().nodename,
           "started_utc": started, "pinned_build_files_verified": nfiles, "model_sha256": MODEL_SHA,
           "memory_before": mem_before, "ownership_record": str(a.ownership), "ownership_sha256": agreement_sha,
           "setup_deadline_utc": setup_deadline.isoformat(),
           "shared_window_hard_end_utc": agreement.get("hard_end_utc", agreement.get("exclusive_window_end_utc")),
           "generation_requests": 0}
    ready = None
    try:
        rec["process_identity"] = process_identity(proc.pid)
        if rec["process_identity"] is None:
            raise SystemExit("Owned receiver exited before its identity could be recorded")
        (a.out / "launch.json").write_text(json.dumps(rec, indent=1) + "\n")
        while time.monotonic() - t0 < 600 and datetime.now(timezone.utc) < setup_deadline:
            if proc.poll() is not None:
                break
            text = (a.out / "llama_server.log").read_text(errors="replace")
            # Readiness markers actually emitted by the pinned 4fea119 build, observed in the 2026-09-22T04:35Z
            # attempt log: "llama_server: model loaded" then "llama_server: listening on http://127.0.0.1:8193".
            # (The former "server is listening"/"all slots are idle" strings never appear in this build.)
            if READY_MARKER in text:
                ready = now(); break
            time.sleep(1)
        if ready is None:
            raise SystemExit("Server not ready before setup/Phase A deadline (or exited); no retry")
        rec["memory_ready"] = {"swap": sh("sysctl -n vm.swapusage").strip(), "vm_stat": sh("vm_stat | head -6")}
    except BaseException as exc:
        rec["startup_error"] = str(exc)
        terminate_owned_child(proc)
        rec["stopped_utc"] = now()
        raise
    finally:
        log.close()
        rec.update(ready_utc=ready, ready_seconds=time.monotonic() - t0, exited=proc.poll())
        try:
            (a.out / "launch.json").write_text(json.dumps(rec, indent=1) + "\n")
        except BaseException:
            # A record-write failure must not strand an unrecorded live receiver.
            terminate_owned_child(proc)
            raise
    print(json.dumps({k: rec[k] for k in ("pid", "started_utc", "ready_utc", "ready_seconds", "exited")}, indent=1))


if __name__ == "__main__":
    main()
