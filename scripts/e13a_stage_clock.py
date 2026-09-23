#!/usr/bin/env python3
"""Bound run clock and owned-child supervision for E13a; no scientific outcomes are produced.

A real phase loads the existing run-directory/stage-hash-bound clock. A durable active receipt and an
exclusive per-run lock reject overlapping work and silent recovery after abrupt process death. A crashed
phase requires review; deleting its receipt/lock or moving its clock is not a supported resume operation.

The outer anchor survives separate commands. Phase time is cumulative and charged once, including ordinary
exceptions. --check and --charge are bookkeeping only. --supervise bounds an external command by the smaller
remaining phase/outer budget and kills/reaps its own child process group on timeout. Detached receiver
processes need the separately verified owner-specific lifecycle cleanup; this module never kills a foreign PID.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import signal
import subprocess
import sys
import tempfile
import time

SCHEMA = "e13a-stage-clock-v2"
CLOCK_FILE = "stage_clock.json"
PHASE_CAPS = {"setup": 600, "collection": 480, "private_grading": 300, "analysis": 300}
OUTER_TOTAL_SECONDS = 2700
PERSIST_FIELDS = ("schema_version", "start_utc", "outer_seconds", "caps", "spent", "reloads", "persists",
                  "run_dir", "stage_sha256", "active_phase", "last_phase", "setup_complete_utc",
                  "setup_completed_commands", "failed_phases", "last_teardown")


class CapExhausted(RuntimeError):
    """The phase cap or outer deadline is exhausted; stop without an implicit retry."""


class ClockRefusal(ValueError):
    """Invalid binding, overlapping work or an unfinished phase; no automatic recovery is allowed."""


class UnreapedChild(RuntimeError):
    """An owned child did not yield a verified exit; keep the active receipt and lock for review."""


def utc_now():
    return datetime.now(timezone.utc)


def parse_utc(text, field="start_utc"):
    if isinstance(text, datetime):
        parsed = text
    elif isinstance(text, str) and text.strip():
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{field} is not an ISO-8601 timestamp: {text!r}") from exc
    else:
        raise ValueError(f"{field} must be a non-empty ISO-8601 timestamp")
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must carry a UTC offset")
    return parsed


def _seconds(value, field):
    if type(value) not in (int, float) or value != value or value in (float("inf"), float("-inf")) or value <= 0:
        raise ValueError(f"{field} must be a finite positive number of seconds")
    return float(value)


def _spent(value, field):
    if type(value) not in (int, float) or value != value or value in (float("inf"), float("-inf")) or value < 0:
        raise ValueError(f"{field} must be a finite non-negative number of seconds")
    return float(value)


def _clock_path(path):
    path = Path(path)
    return (path / CLOCK_FILE if path.is_dir() else path).resolve()


class StageClock:
    def __init__(self, start_utc, caps, *, outer_seconds=OUTER_TOTAL_SECONDS, spent=None, reloads=0, persists=0,
                 run_dir=None, stage_sha256=None, last_phase=None, now_utc=utc_now, monotonic=time.monotonic):
        self.start_utc = parse_utc(start_utc)
        if not isinstance(caps, dict) or set(caps) != set(PHASE_CAPS):
            raise ValueError("caps must name exactly the four fixed stage phases")
        self.caps = {p: _seconds(v, f"caps.{p}") for p, v in caps.items()}
        if any(self.caps[p] > PHASE_CAPS[p] for p in PHASE_CAPS):
            raise ValueError("phase caps may not exceed the fixed maxima")
        self.outer_seconds = _seconds(outer_seconds, "outer_seconds")
        if self.outer_seconds > OUTER_TOTAL_SECONDS:
            raise ValueError("outer_seconds may not exceed the fixed maximum")
        spent = dict(spent or {})
        if set(spent) - set(self.caps):
            raise ValueError("spent names phases that have no cap")
        self.spent = {p: _spent(spent.get(p, 0.0), f"spent.{p}") for p in self.caps}
        if (run_dir is None) != (stage_sha256 is None):
            raise ClockRefusal("run_dir and stage_sha256 must be bound together")
        if stage_sha256 is not None and (not isinstance(stage_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", stage_sha256)):
            raise ClockRefusal("stage_sha256 must be a lowercase SHA256 digest")
        self.run_dir = str(Path(run_dir).resolve()) if run_dir is not None else None
        self.stage_sha256 = stage_sha256
        self.reloads, self.persists = int(reloads), int(persists)
        self.now_utc, self.monotonic = now_utc, monotonic
        self.last_phase = last_phase
        self.setup_complete_utc = None
        self.setup_completed_commands = 0
        self.failed_phases = []
        self.last_teardown = None
        self._active = {}
        self._receipt = None
        self._phase_token = None
        self._path = None
        self._lock_path = None

    @classmethod
    def from_start(cls, start_utc, caps=None, **kwargs):
        return cls(start_utc, dict(PHASE_CAPS if caps is None else caps), **kwargs)

    def require_binding(self, run_dir, stage_sha256):
        if self.run_dir != str(Path(run_dir).resolve()) or self.stage_sha256 != stage_sha256:
            raise ClockRefusal("Clock run directory or stage SHA256 binding does not match")
        if self.run_dir is None or self.stage_sha256 is None:
            raise ClockRefusal("Real phases require a bound existing clock")
        if self.start_utc > self.now_utc():
            raise ClockRefusal("A bound stage start may not be in the future")
        if self._path is None or not self._path.is_file():
            raise ClockRefusal("Real phases require an existing persisted clock")
        if self._path.parent != Path(self.run_dir):
            raise ClockRefusal("Clock was moved outside its bound run directory")
        return self

    def _stamp(self):
        return self.start_utc.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _read(path):
        data = json.loads(Path(path).read_text())
        if not isinstance(data, dict) or data.get("schema_version") != SCHEMA:
            raise ValueError(f"{path} is not a {SCHEMA} stage clock")
        missing = [k for k in PERSIST_FIELDS if k not in data]
        if missing:
            raise ValueError(f"{path} is missing stage-clock fields: {missing}")
        if not isinstance(data["caps"], dict) or not isinstance(data["spent"], dict):
            raise ValueError(f"{path} has malformed caps or spent")
        # Validate persisted limits too; a later command must not accept widened/malformed caps.
        StageClock(data["start_utc"], data["caps"], outer_seconds=data["outer_seconds"], spent=data["spent"],
                   run_dir=data["run_dir"], stage_sha256=data["stage_sha256"])
        return data

    @classmethod
    def load(cls, path, *, run_dir=None, stage_sha256=None, require_bound=False, **kwargs):
        path = _clock_path(path)
        if path.with_suffix(path.suffix + ".lock").exists():
            raise ClockRefusal("Stage clock is locked by active or interrupted work; no automatic restart")
        data = cls._read(path)
        if data["active_phase"] is not None:
            raise ClockRefusal("Stage clock has an unfinished active phase; review required before any recovery")
        clock = cls(data["start_utc"], data["caps"], outer_seconds=data["outer_seconds"], spent=data["spent"],
                    reloads=int(data["reloads"]) + 1, persists=int(data["persists"]), run_dir=data["run_dir"],
                    stage_sha256=data["stage_sha256"], last_phase=data["last_phase"], **kwargs)
        clock._path = path
        clock.setup_complete_utc = data["setup_complete_utc"]
        clock.setup_completed_commands = data["setup_completed_commands"]
        clock.failed_phases = data["failed_phases"]
        clock.last_teardown = data["last_teardown"]
        if clock.run_dir is not None and path.parent != Path(clock.run_dir):
            raise ClockRefusal("Clock was moved outside its bound run directory")
        if require_bound or run_dir is not None or stage_sha256 is not None:
            clock.require_binding(run_dir if run_dir is not None else path.parent, stage_sha256)
        return clock

    def _acquire(self, path):
        if self._lock_path is not None:
            raise ClockRefusal("This clock already owns a phase lock")
        path.parent.mkdir(parents=True, exist_ok=True)
        lock = path.with_suffix(path.suffix + ".lock")
        try:
            fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as exc:
            raise ClockRefusal("Stage clock is locked by active or interrupted work; overlapping work refused") from exc
        with os.fdopen(fd, "w") as handle:
            json.dump({"pid": os.getpid(), "run_dir": self.run_dir, "stage_sha256": self.stage_sha256}, handle)
            handle.flush()
            os.fsync(handle.fileno())
        self._lock_path = lock

    def _release(self):
        if self._lock_path is not None:
            self._lock_path.unlink()
            self._lock_path = None

    def _prior(self, path):
        if not path.exists():
            return None
        prior = self._read(path)
        if prior["start_utc"] != self._stamp() or prior["outer_seconds"] != self.outer_seconds:
            raise ClockRefusal("Refusing to overwrite a different stage clock anchor or outer budget")
        if prior["caps"] != self.caps:
            raise ClockRefusal("Refusing to overwrite the persisted phase caps")
        if (prior["run_dir"], prior["stage_sha256"]) != (self.run_dir, self.stage_sha256):
            raise ClockRefusal("Refusing to overwrite immutable run/stage bindings")
        receipt = prior["active_phase"]
        if receipt is not None and (self._phase_token is None or receipt.get("token") != self._phase_token):
            raise ClockRefusal("Unfinished active phase cannot be reused or overwritten")
        return prior

    def _persist_locked(self, path):
        prior = self._prior(path)
        merged = self.snapshot_spent()
        if prior is not None:
            merged = {p: max(merged[p], prior["spent"][p]) for p in self.caps}
            if prior["setup_complete_utc"] is not None:
                if self.setup_complete_utc not in (None, prior["setup_complete_utc"]):
                    raise ClockRefusal("Setup completion timestamp is immutable")
                self.setup_complete_utc = prior["setup_complete_utc"]
            self.setup_completed_commands = max(self.setup_completed_commands, prior["setup_completed_commands"])
            self.failed_phases = sorted(set(self.failed_phases) | set(prior["failed_phases"]))
            for field in ("last_phase", "last_teardown"):
                current, old = getattr(self, field), prior[field]
                owned_phase = (field == "last_phase" and current is not None and self._phase_token is not None
                               and current.get("token") == self._phase_token)
                if old is not None and (current is None or (not owned_phase and (
                        parse_utc(old["ended_utc"]) > parse_utc(current["ended_utc"]) or
                        (parse_utc(old["ended_utc"]) == parse_utc(current["ended_utc"])
                         and self.persists < prior["persists"])))):
                    setattr(self, field, old)
            self.persists = max(self.persists, prior["persists"])
        self.spent = merged
        # The snapshot is now charged. Reset each in-memory timer so another persist/exit cannot charge it twice.
        for p in self._active:
            self._active[p] = self.monotonic()
        self.persists += 1
        payload = {"schema_version": SCHEMA, "start_utc": self._stamp(), "outer_seconds": self.outer_seconds,
                   "caps": dict(self.caps), "spent": dict(self.spent), "reloads": self.reloads,
                   "persists": self.persists, "run_dir": self.run_dir, "stage_sha256": self.stage_sha256,
                   "active_phase": self._receipt, "last_phase": self.last_phase,
                   "setup_complete_utc": self.setup_complete_utc,
                   "setup_completed_commands": self.setup_completed_commands,
                   "failed_phases": self.failed_phases, "last_teardown": self.last_teardown}
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".stage_clock.", suffix=".json")
        try:
            with os.fdopen(fd, "w") as handle:
                handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
        self._path = path
        return path

    def persist(self, path):
        path = _clock_path(path)
        if self.run_dir is not None and path.parent != Path(self.run_dir):
            raise ClockRefusal("Clock path is outside its bound run directory")
        if self._path is not None and path != self._path:
            raise ClockRefusal("A clock cannot be persisted to a different run path")
        if self._lock_path is not None:
            return self._persist_locked(path)
        self._acquire(path)
        try:
            return self._persist_locked(path)
        finally:
            self._release()

    def _phase(self, phase):
        if phase not in self.caps:
            raise ValueError(f"Unknown stage phase {phase!r}; known phases are {sorted(self.caps)}")
        return phase

    def active_elapsed(self, phase):
        start = self._active.get(self._phase(phase))
        return 0.0 if start is None else max(0.0, self.monotonic() - start)

    def snapshot_spent(self):
        return {p: self.spent[p] + self.active_elapsed(p) for p in self.caps}

    def elapsed_outer(self):
        return max(0.0, (self.now_utc() - self.start_utc).total_seconds())

    def remaining_outer(self):
        return self.outer_seconds - self.elapsed_outer()

    def deadline_utc(self):
        return self.start_utc + timedelta(seconds=self.outer_seconds)

    def remaining(self, phase):
        phase = self._phase(phase)
        own = self.caps[phase] - self.spent[phase] - self.active_elapsed(phase)
        if phase == "setup":
            own = min(own, self.caps[phase] - self.setup_wall_seconds())
            if self.setup_complete_utc is not None:
                return 0.0
        return min(own, self.remaining_outer())

    def setup_wall_seconds(self):
        end = parse_utc(self.setup_complete_utc) if self.setup_complete_utc is not None else self.now_utc()
        return max(0.0, (end - self.start_utc).total_seconds())

    def binding(self, phase):
        phase = self._phase(phase)
        own = self.caps[phase] - self.spent[phase] - self.active_elapsed(phase)
        if phase == "setup":
            own = min(own, self.caps[phase] - self.setup_wall_seconds())
        return "phase_cap" if own <= self.remaining_outer() else "outer_deadline"

    def check(self, phase):
        if phase == "collection" and self.run_dir is not None and self.setup_complete_utc is None:
            if self.setup_wall_seconds() > self.caps["setup"]:
                raise CapExhausted("setup: wall deadline passed before first collection entry")
            if not self.setup_completed_commands:
                raise ClockRefusal("Bound collection requires completed setup receipts")
            if "setup" in self.failed_phases:
                raise ClockRefusal("Failed setup may not be resumed or used for collection")
        left = self.remaining(phase)
        if left <= 0:
            raise CapExhausted(f"{phase}: {self.binding(phase)} exhausted (remaining={left:.3f}s)")
        if phase in self.failed_phases:
            raise ClockRefusal(f"Failed phase {phase} may not be silently retried")
        return left

    def charge(self, phase, seconds):
        """Bookkeeping for already elapsed time, never a substitute for supervising running work."""
        if self._active:
            raise ClockRefusal("Do not manually charge an active phase")
        self.spent[self._phase(phase)] += _spent(seconds, "seconds")
        return self.spent[phase]

    @contextmanager
    def phase(self, name, persist_to=None):
        """Persist active receipt before work; retain it after abrupt death; charge once on ordinary exit."""
        name = self._phase(name)
        if self._active or self._receipt is not None:
            raise ClockRefusal("Another phase is already active on this clock")
        path = _clock_path(persist_to) if persist_to is not None else self._path
        locked = False
        if path is not None:
            if self.run_dir is not None and (not path.is_file() or path.parent != Path(self.run_dir)):
                raise ClockRefusal("Bound phase requires its existing clock in the bound run directory")
            self._acquire(path)
            locked = True
        entered = False
        error = None
        try:
            if path is not None:
                prior = self._prior(path)
                if prior is not None:
                    # Two objects may have been loaded before either command started. Refresh under the lock.
                    self.spent = {p: max(self.spent[p], prior["spent"][p]) for p in self.caps}
                    self.setup_complete_utc = prior["setup_complete_utc"]
                    self.setup_completed_commands = prior["setup_completed_commands"]
                    self.failed_phases = prior["failed_phases"]
                    self.last_teardown = prior["last_teardown"]
            self.check(name)
            if name == "collection" and self.setup_complete_utc is None:
                self.setup_complete_utc = self.now_utc().isoformat()
            started = self.monotonic()
            self._phase_token = secrets.token_hex(16)
            self._receipt = {"phase": name, "token": self._phase_token, "pid": os.getpid(),
                             "started_utc": self.now_utc().isoformat()}
            self._active[name] = started
            entered = True
            if path is not None:
                self._persist_locked(path)
            try:
                yield self
            except BaseException as exc:
                error = exc
                raise
            finally:
                self.spent[name] += self.active_elapsed(name)
                del self._active[name]
                exceeded = self.spent[name] > self.caps[name] or self.remaining_outer() < 0
                if name == "setup":
                    exceeded = exceeded or self.setup_wall_seconds() > self.caps[name]
                self.last_phase = {**self._receipt, "ended_utc": self.now_utc().isoformat(),
                                   "elapsed_seconds": max(0.0, self.monotonic() - started),
                                   "status": "failed" if error is not None or exceeded else "completed",
                                   "error": type(error).__name__ if error is not None else
                                            ("CapExhausted" if exceeded else None)}
                unreaped = isinstance(error, UnreapedChild)
                if unreaped:
                    self._receipt = {**self._receipt, "status": "unreaped_child_review_required"}
                else:
                    self._receipt = None
                if error is not None or exceeded:
                    self.failed_phases = sorted(set(self.failed_phases) | {name})
                elif name == "setup":
                    self.setup_completed_commands += 1
                if path is not None:
                    self._persist_locked(path)
                if not unreaped:
                    self._phase_token = None
                if error is None and exceeded:
                    raise CapExhausted(f"{name}: phase or outer cap exceeded during work")
        finally:
            # If the active receipt could not be finalized, preserve the lock as a fail-closed recovery marker.
            if locked and (not entered or (self._receipt is None and self._phase_token is None)):
                self._release()

    def report(self):
        return {"schema_version": SCHEMA, "start_utc": self._stamp(),
                "outer_deadline_utc": self.deadline_utc().astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                "outer_seconds": self.outer_seconds, "outer_remaining_seconds": self.remaining_outer(),
                "caps": dict(self.caps), "spent_seconds": self.snapshot_spent(),
                "remaining_seconds": {p: self.remaining(p) for p in self.caps},
                "run_dir": self.run_dir, "stage_sha256": self.stage_sha256,
                "active_phase": self._receipt, "last_phase": self.last_phase,
                "setup_wall_seconds": self.setup_wall_seconds(), "setup_complete_utc": self.setup_complete_utc,
                "setup_completed_commands": self.setup_completed_commands,
                "failed_phases": self.failed_phases, "last_teardown": self.last_teardown,
                "reloads": self.reloads, "persists": self.persists}


def open_clock(run_dir, *, start_utc=None, caps=None, require_existing=False, stage_sha256=None, **kwargs):
    run_dir = Path(run_dir).resolve()
    path = run_dir / CLOCK_FILE
    if path.exists():
        return StageClock.load(path, run_dir=run_dir if require_existing or stage_sha256 is not None else None,
                               stage_sha256=stage_sha256, require_bound=require_existing, **kwargs), path
    if require_existing:
        raise ClockRefusal("Real phase requires an existing bound stage clock; initialize during authorized setup")
    clock = StageClock.from_start(start_utc or utc_now(), caps, run_dir=run_dir if stage_sha256 is not None else None,
                                 stage_sha256=stage_sha256, **kwargs)
    return clock, path


def ownership_deadline(path, now):
    """Temporal guard before setup work; agreement authenticity/resource authority are separately verified."""
    record = json.loads(Path(path).read_text())
    windows = []
    for start_key, end_key in (("start_utc", "hard_end_utc"),
                               ("exclusive_window_start_utc", "exclusive_window_end_utc")):
        if start_key in record or end_key in record:
            if start_key not in record or end_key not in record:
                raise ClockRefusal("Ownership record has an incomplete shared window")
            windows.append((parse_utc(record[start_key]), parse_utc(record[end_key])))
    if not windows or any(window != windows[0] for window in windows[1:]):
        raise ClockRefusal("Missing or conflicting ownership windows")
    start, end = windows[0]
    if not start <= now < end:
        raise ClockRefusal("Setup/analysis work is outside the agreed ownership window")
    return end


def _new_receiver_cleanup(clock, receiver_dir, helper, expected_helper_sha256, started_utc,
                          ownership_sha256, runner):
    """Only a record newly created by this command can trigger the pinned launcher's guarded --stop."""
    started = clock.monotonic()
    result = {"receiver_dir": str(receiver_dir), "helper_sha256": expected_helper_sha256,
              "started_utc": clock.now_utc().isoformat(), "kind": "abnormal_exit_owned_receiver_teardown",
              "budget_seconds": 20, "dispatch_authorized": False}
    try:
        record_path = receiver_dir / "launch.json"
        if not record_path.is_file():
            result["status"] = "no_new_launch_record_available_manual_reconciliation_required"
        else:
            record = json.loads(record_path.read_text())
            if (record.get("schema") != "mrl16-own-receiver-launch-v31"
                    or record.get("ownership_sha256") != ownership_sha256
                    or parse_utc(record["started_utc"]) < started_utc
                    or parse_utc(record["started_utc"]) > clock.now_utc()
                    or not record.get("process_identity")):
                raise ClockRefusal("New receiver record does not establish this command's ownership/identity")
            if hashlib.sha256(helper.read_bytes()).hexdigest() != expected_helper_sha256:
                raise ClockRefusal("Cleanup helper differs from its frozen digest")
            stopped = runner([sys.executable, str(helper), "--out", str(receiver_dir), "--stop"],
                             timeout=20, capture_output=True, text=True, check=False)
            result["returncode"] = stopped.returncode
            updated = json.loads(record_path.read_text())
            result["status"] = ("exit_observed" if stopped.returncode == 0 and updated.get("exit_observed") is True
                                else "cleanup_not_verified_manual_reconciliation_required")
    except Exception as exc:
        result.update(status="cleanup_failed_manual_reconciliation_required", error=f"{type(exc).__name__}: {exc}")
    result["elapsed_seconds"] = max(0.0, clock.monotonic() - started)
    result["ended_utc"] = clock.now_utc().isoformat()
    clock.last_teardown = result
    if clock._path is not None:
        clock.persist(clock._path)
    return result


def supervise(clock, phase, command, *, deadline_utc=None, popen=subprocess.Popen, killpg=os.killpg,
              owned_receiver_dir=None, cleanup_helper_sha256=None, ownership_sha256=None,
              cleanup_runner=subprocess.run):
    """Bound an owned child group; optional abnormal-launch cleanup is separate, bounded teardown."""
    if not command:
        raise ValueError("A supervised command is required")
    receiver_dir = Path(owned_receiver_dir).resolve() if owned_receiver_dir is not None else None
    helper = Path(__file__).with_name("launch_own_receiver_v31.py").resolve()
    if receiver_dir is not None:
        if phase != "setup" or receiver_dir.exists():
            raise ClockRefusal("Owned-receiver cleanup is only for a new setup-launch directory")
        if (not isinstance(cleanup_helper_sha256, str)
                or hashlib.sha256(helper.read_bytes()).hexdigest() != cleanup_helper_sha256):
            raise ClockRefusal("The cleanup helper must match its frozen SHA256")
        if not ownership_sha256:
            raise ClockRefusal("Owned-receiver cleanup requires the agreed ownership digest")
        if str(helper) not in [str(Path(arg).resolve()) for arg in command] or "--out" not in command:
            raise ClockRefusal("Owned-receiver cleanup is restricted to the pinned launcher command")
        if Path(command[command.index("--out") + 1]).resolve() != receiver_dir or "--stop" in command:
            raise ClockRefusal("Launcher output differs from the new owned receiver directory")
    started_utc = clock.now_utc()
    try:
        return _supervise_work(clock, phase, command, deadline_utc=deadline_utc, popen=popen, killpg=killpg)
    except BaseException:
        if receiver_dir is not None:
            _new_receiver_cleanup(clock, receiver_dir, helper, cleanup_helper_sha256, started_utc,
                                  ownership_sha256, cleanup_runner)
        raise


def _supervise_work(clock, phase, command, *, deadline_utc, popen, killpg):
    with clock.phase(phase):
        budget = clock.check(phase)
        if deadline_utc is not None:
            budget = min(budget, (parse_utc(deadline_utc) - clock.now_utc()).total_seconds())
            if budget <= 0:
                raise CapExhausted(f"{phase}: ownership window exhausted before command dispatch")
        started = clock.monotonic()
        child = popen(command, start_new_session=True)
        def terminate_owned_group():
            try:
                killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired as exc:
                raise UnreapedChild(f"Owned child {child.pid} exit unobserved after bounded cleanup; review required") from exc
        try:
            # Charge process-start overhead against the same budget, rather than restarting a timeout afterward.
            child.wait(timeout=max(0.0, min(budget - (clock.monotonic() - started), clock.remaining(phase))))
        except subprocess.TimeoutExpired as exc:
            terminate_owned_group()
            raise CapExhausted(f"{phase}: supervised command reached its phase/outer deadline") from exc
        except BaseException:
            terminate_owned_group()
            raise
        if child.returncode:
            terminate_owned_group()
            raise ChildProcessError(f"{phase}: supervised command exited with status {child.returncode}")
    return clock.report()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dir", type=Path, required=True)
    ap.add_argument("--init", action="store_true", help="initialize once before authorized setup")
    ap.add_argument("--stage", type=Path, help="stage descriptor, required for bound initialization/supervision")
    ap.add_argument("--ownership", type=Path, help="agreed window; required before any supervised setup command")
    ap.add_argument("--owned-receiver-dir", type=Path, help="new launcher --out directory; abnormal-exit cleanup only")
    ap.add_argument("--cleanup-helper-sha256", help="frozen SHA256 of launch_own_receiver_v31.py")
    ap.add_argument("--start-utc", help="reviewed explicit anchor, never in the future")
    ap.add_argument("--phase", choices=sorted(PHASE_CAPS))
    ap.add_argument("--check", choices=sorted(PHASE_CAPS), help="bookkeeping check; does not supervise later work")
    ap.add_argument("--charge", choices=sorted(PHASE_CAPS), help="bookkeeping for elapsed work, not enforcement")
    ap.add_argument("--seconds", type=float)
    ap.add_argument("--supervise", choices=("setup", "analysis"), help="run a command with phase/outer deadline enforcement")
    ap.add_argument("command", nargs=argparse.REMAINDER, help="-- followed by the owned command and arguments")
    args = ap.parse_args(argv)
    if args.charge and args.seconds is None:
        ap.error("--charge requires --seconds")
    if (args.init or args.supervise) and args.stage is None:
        ap.error("--init and --supervise require --stage for immutable binding")
    if args.supervise and (args.init or args.check or args.charge):
        ap.error("--supervise cannot be combined with initialization/check/charge")
    if args.supervise == "setup" and args.ownership is None:
        ap.error("supervised setup requires --ownership before containment or launch")
    run_dir = args.run_dir.resolve()
    path = run_dir / CLOCK_FILE
    stage_hash = hashlib.sha256(args.stage.read_bytes()).hexdigest() if args.stage is not None else None
    if args.init:
        clock = StageClock.from_start(args.start_utc or utc_now(), run_dir=run_dir, stage_sha256=stage_hash)
        if clock.start_utc > utc_now():
            raise SystemExit("A bound stage start may not be in the future")
        clock._acquire(path)
        try:
            if path.exists():
                raise SystemExit(f"Refusing to re-anchor an existing stage clock: {path}")
            clock._persist_locked(path)
        finally:
            clock._release()
    else:
        if not path.exists():
            raise SystemExit(f"No stage clock at {path}; initialize during authorized setup first")
        clock = StageClock.load(path, run_dir=run_dir if stage_hash is not None else None,
                                stage_sha256=stage_hash, require_bound=args.supervise is not None)
    if args.check:
        try:
            clock.check(args.check)
        except CapExhausted as exc:
            raise SystemExit(f"Stage cap exhausted for {args.check}: {exc}") from exc
    if args.charge:
        clock.charge(args.charge, args.seconds)
        clock.persist(path)
        if clock.remaining(args.charge) < 0:
            raise SystemExit(f"Already elapsed {args.charge} work exceeded its cap; no further work authorized")
    if args.supervise:
        command = args.command[1:] if args.command[:1] == ["--"] else args.command
        deadline = ownership_deadline(args.ownership, clock.now_utc()) if args.ownership is not None else None
        options = {"deadline_utc": deadline}
        if args.owned_receiver_dir is not None:
            options.update(owned_receiver_dir=args.owned_receiver_dir,
                           cleanup_helper_sha256=args.cleanup_helper_sha256,
                           ownership_sha256=hashlib.sha256(args.ownership.read_bytes()).hexdigest()
                           if args.ownership is not None else None)
        supervise(clock, args.supervise, command, **options)
    report = clock.report()
    if args.phase:
        report["queried_phase"] = {"phase": args.phase, "remaining_seconds": clock.remaining(args.phase),
                                   "binding": clock.binding(args.phase)}
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


if __name__ == "__main__":
    main()
