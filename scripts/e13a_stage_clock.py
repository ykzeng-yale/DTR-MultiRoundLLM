#!/usr/bin/env python3
"""Shared stage clock for the E13a executable path. BOOKKEEPING ONLY: no receiver call, no candidate execution.

Evidence class: none. This module measures and persists time; it produces no outcome and interprets no arm.

One stage run is several separate commands (setup, collection, private grading, analysis). Each has its own
phase cap, and all of them read ONE shared outer deadline anchored to the stage's start_utc:

    setup 600 s | collection 480 s | private grading 300 s | analysis 300 s | OUTER TOTAL 2700 s

The outer deadline is wall-clock from start_utc, so a later command cannot extend it: StageClock.load reads
the persisted start_utc back and computes the remaining outer budget from it. Phase spend accumulates in the
same file, merged by maximum on persist, so a reload can only ever shrink the remaining budgets. Charging is
durable: an in-flight phase's elapsed seconds are folded into the persisted spend, so a command that aborts
mid-phase still pays for the time it used.

remaining(phase) is min(phase cap - phase spend, outer remaining); check(phase) raises CapExhausted when that
is non-positive and names the binding bound. Unknown phases are refused, never silently given a free budget.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile
import time

SCHEMA = "e13a-stage-clock-v1"
CLOCK_FILE = "stage_clock.json"
# The lead's fixed caps. Keys are the phase names every E13a command uses.
PHASE_CAPS = {"setup": 600, "collection": 480, "private_grading": 300, "analysis": 300}
OUTER_TOTAL_SECONDS = 2700
PERSIST_FIELDS = ("schema_version", "start_utc", "outer_seconds", "caps", "spent", "reloads", "persists")


class CapExhausted(RuntimeError):
    """A phase cap or the shared outer deadline is exhausted; the caller must stop, not retry."""


def utc_now():
    return datetime.now(timezone.utc)


def parse_utc(text, field="start_utc"):
    """ISO-8601 with an explicit UTC offset, as collect_diagnostic._utc requires of every attestation stamp."""
    if isinstance(text, datetime):
        if text.tzinfo is None:
            raise ValueError(f"{field} must carry a UTC offset")
        return text
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"{field} must be a non-empty ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} is not an ISO-8601 timestamp: {text!r}") from exc
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


class StageClock:
    """The one clock every E13a phase reads. Construct with from_start; carry it across commands with persist/load."""

    def __init__(self, start_utc, caps, *, outer_seconds=OUTER_TOTAL_SECONDS, spent=None, reloads=0, persists=0,
                 now_utc=utc_now, monotonic=time.monotonic):
        self.start_utc = parse_utc(start_utc)
        if not isinstance(caps, dict) or not caps:
            raise ValueError("caps must be a non-empty mapping of phase -> seconds")
        self.caps = {str(k): _seconds(v, f"caps.{k}") for k, v in caps.items()}
        self.outer_seconds = _seconds(outer_seconds, "outer_seconds")
        spent = dict(spent or {})
        unknown = sorted(set(spent) - set(self.caps))
        if unknown:
            raise ValueError(f"spent names phases that have no cap: {unknown}")
        self.spent = {p: _spent(spent.get(p, 0.0), f"spent.{p}") for p in self.caps}
        self.reloads, self.persists = int(reloads), int(persists)
        self.now_utc, self.monotonic = now_utc, monotonic
        self._active = {}  # phase -> monotonic start of an in-flight charge

    # ------------------------------------------------------------------ construction and persistence
    @classmethod
    def from_start(cls, start_utc, caps=None, **kwargs):
        """A fresh clock anchored at start_utc. caps defaults to the lead's fixed phase caps."""
        return cls(start_utc, dict(PHASE_CAPS if caps is None else caps), **kwargs)

    def persist(self, path):
        """Write (or update) stage_clock.json. The anchor and the outer budget can never change, and phase spend
        is merged by maximum, so persisting after a reload cannot hand any phase back time it already used."""
        path = Path(path)
        if path.is_dir():
            path = path / CLOCK_FILE
        merged = self.snapshot_spent()
        if path.exists():
            prior = self._read(path)
            if prior["start_utc"] != self._stamp() or prior["outer_seconds"] != self.outer_seconds:
                raise ValueError(f"Refusing to overwrite a different stage clock at {path}: "
                                 f"start_utc {prior['start_utc']} outer_seconds {prior['outer_seconds']}")
            if set(prior["caps"]) != set(self.caps) or any(prior["caps"][p] != self.caps[p] for p in self.caps):
                raise ValueError(f"Refusing to overwrite the persisted phase caps at {path}")
            merged = {p: max(merged[p], _spent(prior["spent"].get(p, 0.0), f"spent.{p}")) for p in self.caps}
        self.spent = merged
        self.persists += 1
        payload = {"schema_version": SCHEMA, "start_utc": self._stamp(), "outer_seconds": self.outer_seconds,
                   "caps": dict(self.caps), "spent": dict(self.spent), "reloads": self.reloads,
                   "persists": self.persists}
        path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".stage_clock.", suffix=".json")
        try:
            with os.fdopen(fd, "w") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
        return path

    @staticmethod
    def _read(path):
        data = json.loads(Path(path).read_bytes().decode("utf-8"))
        if not isinstance(data, dict) or data.get("schema_version") != SCHEMA:
            raise ValueError(f"{path} is not a {SCHEMA} stage clock")
        missing = [k for k in PERSIST_FIELDS if k not in data]
        if missing:
            raise ValueError(f"{path} is missing stage-clock fields: {missing}")
        if not isinstance(data["caps"], dict) or not isinstance(data["spent"], dict):
            raise ValueError(f"{path} has malformed caps or spent")
        return data

    @classmethod
    def load(cls, path, **kwargs):
        """Reload the clock a previous command persisted. The outer deadline is NOT reset: it stays anchored to
        the recorded start_utc, and the recorded phase spend is carried forward."""
        path = Path(path)
        if path.is_dir():
            path = path / CLOCK_FILE
        data = cls._read(path)
        clock = cls(data["start_utc"], data["caps"], outer_seconds=data["outer_seconds"], spent=data["spent"],
                    reloads=int(data["reloads"]) + 1, persists=int(data["persists"]), **kwargs)
        return clock

    def _stamp(self):
        return self.start_utc.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    # ------------------------------------------------------------------ budgets
    def _phase(self, phase):
        if phase not in self.caps:
            raise ValueError(f"Unknown stage phase {phase!r}; known phases are {sorted(self.caps)}")
        return phase

    def active_elapsed(self, phase):
        start = self._active.get(self._phase(phase))
        return 0.0 if start is None else max(0.0, self.monotonic() - start)

    def snapshot_spent(self):
        """Spend including any in-flight phase, so an abort mid-phase is still charged."""
        return {p: self.spent[p] + self.active_elapsed(p) for p in self.caps}

    def elapsed_outer(self):
        return max(0.0, (self.now_utc() - self.start_utc).total_seconds())

    def remaining_outer(self):
        return self.outer_seconds - self.elapsed_outer()

    def deadline_utc(self):
        return self.start_utc + timedelta(seconds=self.outer_seconds)

    def remaining(self, phase):
        """Seconds this phase may still use: its own cap minus its spend, never more than the shared outer budget."""
        phase = self._phase(phase)
        return min(self.caps[phase] - self.spent[phase] - self.active_elapsed(phase), self.remaining_outer())

    def binding(self, phase):
        phase = self._phase(phase)
        own = self.caps[phase] - self.spent[phase] - self.active_elapsed(phase)
        return "phase_cap" if own <= self.remaining_outer() else "outer_deadline"

    def check(self, phase):
        """Raise CapExhausted when this phase has no time left, naming the bound that binds."""
        left = self.remaining(phase)
        if left <= 0:
            raise CapExhausted(f"{phase}: {self.binding(phase)} exhausted "
                               f"(phase_remaining={self.caps[phase] - self.spent[phase] - self.active_elapsed(phase):.3f}s, "
                               f"outer_remaining={self.remaining_outer():.3f}s)")
        return left

    def charge(self, phase, seconds):
        self.spent[self._phase(phase)] += _spent(seconds, "seconds")
        return self.spent[phase]

    @contextmanager
    def phase(self, name, persist_to=None):
        """Charge a phase for the time spent in the block, whether it returns or raises."""
        name = self._phase(name)
        if name in self._active:
            raise ValueError(f"Phase {name!r} is already being charged on this clock")
        self.check(name)
        self._active[name] = self.monotonic()
        try:
            yield self
        finally:
            elapsed = self.active_elapsed(name)
            del self._active[name]
            self.spent[name] += elapsed
            if persist_to is not None:
                self.persist(persist_to)

    def report(self):
        return {"schema_version": SCHEMA, "start_utc": self._stamp(),
                "outer_deadline_utc": self.deadline_utc().astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                "outer_seconds": self.outer_seconds, "outer_remaining_seconds": self.remaining_outer(),
                "caps": dict(self.caps), "spent_seconds": self.snapshot_spent(),
                "remaining_seconds": {p: self.remaining(p) for p in self.caps},
                "reloads": self.reloads, "persists": self.persists}


def open_clock(run_dir, *, start_utc=None, caps=None, **kwargs):
    """The clock for a run directory: reload run_dir/stage_clock.json when it exists, else anchor a new one.

    Reloading is the normal case, because separate commands must share one outer deadline."""
    run_dir = Path(run_dir)
    path = run_dir / CLOCK_FILE
    if path.exists():
        return StageClock.load(path, **kwargs), path
    clock = StageClock.from_start(start_utc or utc_now(), caps, **kwargs)
    return clock, path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dir", type=Path, required=True, help="run directory holding stage_clock.json")
    ap.add_argument("--init", action="store_true", help="anchor a new clock (refuses to re-anchor an existing one)")
    ap.add_argument("--start-utc", help="--init: the stage start timestamp (default: now)")
    ap.add_argument("--phase", choices=sorted(PHASE_CAPS), help="also print this phase's remaining seconds")
    # MRL-19: a phase whose work runs in a separate command (e.g. the analyzer, which takes no clock) is
    # enforced from the shell: --check before it, --charge after it. Both persist, so the outer deadline is
    # shared and a reload can only shrink the remaining budget.
    ap.add_argument("--check", choices=sorted(PHASE_CAPS), help="exit non-zero if this phase has no budget left")
    ap.add_argument("--charge", choices=sorted(PHASE_CAPS), help="record seconds spent by an external command")
    ap.add_argument("--seconds", type=float, help="--charge: seconds to record")
    args = ap.parse_args(argv)
    if args.charge and args.seconds is None:
        ap.error("--charge requires --seconds")
    path = args.run_dir / CLOCK_FILE
    if args.init:
        if path.exists():
            raise SystemExit(f"Refusing to re-anchor an existing stage clock: {path}")
        clock = StageClock.from_start(args.start_utc or utc_now())
        clock.persist(path)
    else:
        if not path.exists():
            raise SystemExit(f"No stage clock at {path}; run with --init first")
        clock = StageClock.load(path)
    if args.check:
        try:
            clock.check(args.check)
        except CapExhausted as exc:
            clock.persist(path)
            raise SystemExit(f"Stage cap exhausted for {args.check}: {exc}")
    if args.charge:
        clock.charge(args.charge, args.seconds)
        clock.persist(path)
    report = clock.report()
    if args.phase:
        report["queried_phase"] = {"phase": args.phase, "remaining_seconds": clock.remaining(args.phase),
                                   "binding": clock.binding(args.phase)}
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


if __name__ == "__main__":
    main()
