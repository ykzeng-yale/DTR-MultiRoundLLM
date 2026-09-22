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
(`--stop` does, only for the PID it recorded).
"""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "work/bin"
MANIFEST = ROOT / "experiments/env/llama_server_manifest.json"
SNAPSHOT = ROOT / "results/receiver_props_snapshot_8193.json"
MODEL_SHA = "626b4a6678b86442240e33df819e00132d3ba7dddfe1cdc4fbb18e0a9615c62d"
PORT = 8193


def now():
    return datetime.now(timezone.utc).isoformat()


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout


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
        rec = json.loads((a.out / "launch.json").read_text())
        pid = rec["pid"]
        cmdline = sh(f"ps -o command= -p {pid}")
        if "llama-server" not in cmdline or f"--port {PORT}" not in cmdline:
            raise SystemExit(f"PID {pid} is not our recorded server; refusing to signal")
        os.kill(pid, 15)
        rec["stopped_utc"] = now()
        (a.out / "launch.json").write_text(json.dumps(rec, indent=1) + "\n")
        print(json.dumps({"stopped_pid": pid, "utc": rec["stopped_utc"]}))
        return
    if a.ownership is None or not a.ownership.exists():
        raise SystemExit("Refusing to launch: no committed owner agreement (shared-hardware window) supplied")
    if subprocess.run(["git", "ls-files", "--error-unmatch", str(a.ownership)], cwd=ROOT, capture_output=True).returncode != 0:
        raise SystemExit("Refusing to launch: ownership record is not committed")
    if a.out.exists():
        raise SystemExit("Refusing to overwrite an existing receiver record")
    snap, mp, nfiles = verify()
    if sh(f"lsof -nP -iTCP:{PORT} -sTCP:LISTEN"):
        raise SystemExit(f"Port {PORT} is not free")
    if sh("ps -Ao command | grep -v grep | grep llama-server").strip():
        raise SystemExit("Another llama-server is running; refusing (one server at a time)")
    a.out.mkdir(parents=True)
    cmd = [str(BIN / "llama-server"), "-m", mp, "--alias", "qwen2.5-3b-instruct", "--port", str(PORT), "-ngl", "99",
           "-np", "4", "-c", "32768", "--jinja", "--host", "127.0.0.1"]
    env = dict(os.environ, LLAMA_MEDIA_MARKER=snap["media_marker"])
    mem_before = {"swap": sh("sysctl -n vm.swapusage").strip(), "vm_stat": sh("vm_stat | head -6")}
    log = open(a.out / "llama_server.log", "w")
    started = now(); t0 = time.monotonic()
    proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
    rec = {"schema": "mrl16-own-receiver-launch-v31", "pid": proc.pid, "command": cmd,
           "env_pinned": {"LLAMA_MEDIA_MARKER": snap["media_marker"]}, "host": os.uname().nodename,
           "started_utc": started, "pinned_build_files_verified": nfiles, "model_sha256": MODEL_SHA,
           "memory_before": mem_before, "ownership_record": str(a.ownership), "generation_requests": 0}
    (a.out / "launch.json").write_text(json.dumps(rec, indent=1) + "\n")
    ready = None
    while time.monotonic() - t0 < 600:
        if proc.poll() is not None:
            break
        text = (a.out / "llama_server.log").read_text(errors="replace")
        if "server is listening" in text or "all slots are idle" in text:
            ready = now(); break
        time.sleep(1)
    rec.update(ready_utc=ready, ready_seconds=time.monotonic() - t0, exited=proc.poll(),
               memory_ready={"swap": sh("sysctl -n vm.swapusage").strip(), "vm_stat": sh("vm_stat | head -6")})
    (a.out / "launch.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("pid", "started_utc", "ready_utc", "ready_seconds", "exited")}, indent=1))
    if ready is None:
        raise SystemExit("Server not ready within 600 s (or exited); record kept; no retry")


if __name__ == "__main__":
    main()
