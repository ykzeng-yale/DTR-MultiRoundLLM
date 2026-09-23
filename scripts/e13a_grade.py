#!/usr/bin/env python3
"""E13a private grading: POST-HOC-MOTIVATED DEVELOPMENT follow-up grading on five fixed checkpoints.

Evidence class: post-hoc-motivated development follow-up at the five development-selected checkpoints named by
the E13a stage descriptor. Not a test of the selected gated rule, not a test of a diagnostic-only effect, never
pooled with E12. This module grades a finished collection; it makes NO receiver or model call ever.

Two stages, in this order, and never interleaved:

1. validate_handoff(collect_dir, stage, plan) -- runs BEFORE any grade row exists and refuses loudly (writing
   nothing) unless all of the following hold:
     * collect/{manifest.json,completion.json,calls.jsonl} exist and parse strictly (no duplicate JSON keys);
     * completion.json binds the manifest by sha256, and its assigned/dispatched/completed counts agree with the
       assignment and with the call ledger;
     * manifest.checksums covers EXACTLY the written files under collect_dir (manifest.json and completion.json
       excepted) and every recorded sha256 matches the bytes on disk -- an unlisted file is a refusal, not a skip;
     * every artifact's bytes hash to the output digest recorded for its slot (collect.digest over the output
       text, E12 semantics), so tampered bytes and a wrong recorded digest are distinct refusals;
     * every assigned root_id/arm/replicate slot appears EXACTLY once; absent or duplicate is a hard refusal, as
       is any unexpected slot, and each row's recorded request pins (seed, messages_sha256) equal the plan's;
     * the pins match: stage descriptor sha256, request plan sha256, the e13a_release release_manifest.json
       sha256 at the recorded path, grade.GRADER_VERSION, and the release's model/evaluator pins.

2. grade(collect_dir, release_dir, out_dir, executor=..., real=False, clock=None) -- grades through the REAL
   private grading components (experiments.landmark.grade.extract_code / prepare_program / evaluate, the frozen
   grading contract, validate_specs, and the release's grading_limits) with an INJECTED private executor.

   With real=False the executor is a deterministic stub (StubPrivateExecutor): it never executes a candidate,
   reference or containment payload, and every row, the summary and the failure report are labelled
   transport_only -- transport-only output is not a grade of model behaviour and must not be reported as one.
   With real=True the committed-release verification and the containment attestation are mandatory; this module
   still starts nothing itself, it only counts and caps what the injected executor is permitted to start.

   Start ceilings come from the release manifest's grading_limits (E13a: artifact_starts 60, recheck_starts 10,
   containment_starts 9, max_private_starts 79, grading_seconds 300) and are enforced with the shared StageClock
   (phase "private_grading") plus a local monotonic deadline, whichever is tighter. Cache hits and pre-execution
   format rejection reduce actual starts and NEVER drop an assigned grade row. Reaching a ceiling or the seconds
   cap degrades the remaining rows to an explicit missing_reason; an integrity failure or a StageClock cap
   exhaustion aborts, and the abort still writes grades.jsonl retaining every assigned slot plus a failure
   report. Unavailable outcomes are never zero-filled and never counted as failures.

Output: out_dir/grade/{grades.jsonl,grading_attempts.jsonl,summary.json} (+ failure_report.json on abort), in the
record shape scripts/e13a_analyze.py consumes. Existing outputs are never overwritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.landmark import grade as private_grade
from experiments.landmark import study_adapter
from experiments.landmark.collect import digest, file_sha

GRADE_DRIVER_VERSION = "e13a-private-grading-driver-v1"
EVIDENCE_CLASS = (
    "post-hoc-motivated development follow-up grading at the five development-selected checkpoints named by the "
    "E13a stage descriptor; NOT a test of the selected gated rule; not pooled with E12"
)
DEFAULT_STAGE = ROOT / "experiments/landmark/e13a_stage.json"
DEFAULT_RELEASE_DIR = ROOT / "experiments/landmark/e13a_release"
PRIVATE_GRADING_PHASE = "private_grading"

# Keys the collection handoff must carry. Extras are allowed; every one of these is mandatory.
REQUIRED_MANIFEST_KEYS = frozenset({
    "stage", "stage_descriptor_path", "stage_descriptor_sha256", "request_plan_path", "request_plan_sha256",
    "release_manifest_path", "release_manifest_sha256", "grader_version", "model", "evaluator", "checksums",
    "transport_only",
})
REQUIRED_COMPLETION_KEYS = frozenset({"stage", "manifest_sha256", "assigned", "dispatched", "completed", "status"})
REQUIRED_CALL_KEYS = frozenset({"root_id", "arm", "replicate", "status", "artifact_path", "output_sha256",
                                "missing_reason"})
CALL_STATUSES = {"completed", "unavailable"}
USAGE_INT_FIELDS = ("calls", "prompt_tokens", "completion_tokens")

# The E13a grading_limits shape: the five keys study_adapter already reads, plus containment_starts. Read
# strictly here (same numeric ceilings as study_adapter.load_grading_limits); no existing check is relaxed.
E13A_GRADING_LIMIT_KEYS = frozenset({"n_roots", "artifact_starts", "recheck_starts", "containment_starts",
                                     "max_private_starts", "grading_seconds"})

MARKER_RE = re.compile(r"(?:" + re.escape(private_grade.STARTED) + r"|__LANDMARK_PRIVATE_OK__)[0-9a-f]{24}")


class HandoffRefusal(Exception):
    """The collection handoff does not satisfy the E13a grading contract; nothing is written."""


class GradingAbort(Exception):
    """An integrity or resource failure stopped grading; every assigned slot is still written."""


def _sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _strict_json(data, what):
    def no_duplicates(pairs):
        seen = {}
        for key, value in pairs:
            if key in seen:
                raise HandoffRefusal(f"{what}: duplicate JSON key {key!r}")
            seen[key] = value
        return seen

    try:
        return json.loads(data.decode() if isinstance(data, (bytes, bytearray)) else data,
                          object_pairs_hook=no_duplicates)
    except json.JSONDecodeError as exc:
        raise HandoffRefusal(f"{what}: not valid JSON: {exc}") from exc


def _load_pinned(value, what):
    """(data, sha256) for a descriptor given as a path (file bytes) or as an already-loaded mapping."""
    if isinstance(value, (str, Path)):
        path = Path(value)
        if not path.is_file():
            raise HandoffRefusal(f"{what}: {path} does not exist")
        raw = path.read_bytes()
        return _strict_json(raw, what), _sha256_bytes(raw), str(path)
    if isinstance(value, dict):
        return value, digest(value), "<in-memory descriptor>"
    raise HandoffRefusal(f"{what}: expected a path or a mapping, got {type(value).__name__}")


def _resolve(path):
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def load_e13a_grading_limits(manifest_bytes, specs=None):
    """Strict grading_limits reader for the E13a release (containment_starts added to the study_adapter shape).

    The classic five-key shape is delegated to study_adapter.load_grading_limits unchanged. The E13a six-key
    shape is checked with the same strictness: exact key set, ints, max_private_starts == artifact + recheck +
    containment and <= study_adapter.MAX_PRIVATE_STARTS, 0 < grading_seconds <= study_adapter.MAX_GRADING_SECONDS,
    n_roots == len(specs). grading_limits are mandatory for E13a: a release without them is refused, never
    defaulted."""
    raw = study_adapter._manifest_bytes(manifest_bytes)
    manifest = _strict_json(raw, "release manifest")
    limits = manifest.get("grading_limits")
    if limits is None:
        raise HandoffRefusal("E13a release manifest must declare grading_limits explicitly")
    if not isinstance(limits, dict):
        raise HandoffRefusal("release manifest grading_limits must be an object")
    keys = set(limits)
    required = set(study_adapter.GRADING_LIMIT_KEYS)
    allowed = required | set(getattr(study_adapter, "OPTIONAL_GRADING_LIMIT_KEYS", ()) or ())
    if required <= keys <= allowed:
        # study_adapter reads this shape: use its validator, then re-check the arithmetic here as well.
        try:
            resolved = study_adapter.load_grading_limits(raw, specs)
        except ValueError as exc:
            raise HandoffRefusal(f"release grading_limits refused: {exc}") from exc
        a, r = resolved["artifact_starts"], resolved["recheck_starts"]
        c = resolved.get("containment_starts", 0)
        mx = resolved.get("max_private_starts", a + r + c)
        if mx != a + r + c or mx > study_adapter.MAX_PRIVATE_STARTS \
                or not 0 < resolved["grading_seconds"] <= study_adapter.MAX_GRADING_SECONDS:
            raise HandoffRefusal("release grading_limits do not satisfy max_private_starts == artifact + recheck "
                                 f"+ containment <= {study_adapter.MAX_PRIVATE_STARTS}")
        return {**resolved, "containment_starts": c, "max_private_starts": mx, "n_roots": limits["n_roots"],
                "shape": "study_adapter"}
    if keys != set(E13A_GRADING_LIMIT_KEYS):
        raise HandoffRefusal(f"grading_limits must carry exactly int {sorted(E13A_GRADING_LIMIT_KEYS)} "
                             f"(or the study_adapter five-key shape); got {sorted(keys)}")
    if not all(type(limits[k]) is int for k in E13A_GRADING_LIMIT_KEYS):
        raise HandoffRefusal("every grading_limits value must be an int")
    a, r, c = limits["artifact_starts"], limits["recheck_starts"], limits["containment_starts"]
    mx, secs, n_roots = limits["max_private_starts"], limits["grading_seconds"], limits["n_roots"]
    if a < 1 or r < 0 or c < 0 or mx != a + r + c or mx > study_adapter.MAX_PRIVATE_STARTS:
        raise HandoffRefusal("grading_limits starts invalid: max_private_starts must equal artifact + recheck + "
                             f"containment and be <= {study_adapter.MAX_PRIVATE_STARTS}")
    if not 0 < secs <= study_adapter.MAX_GRADING_SECONDS:
        raise HandoffRefusal(f"grading_limits grading_seconds must be in (0, {study_adapter.MAX_GRADING_SECONDS}]")
    if n_roots < 1 or (specs is not None and n_roots != len(specs)):
        raise HandoffRefusal("grading_limits n_roots does not equal the number of private specs")
    return {"artifact_starts": a, "recheck_starts": r, "containment_starts": c, "max_private_starts": mx,
            "grading_seconds": secs, "seconds_cap": secs, "n_roots": n_roots, "source": "grading_limits",
            "shape": "e13a_6key"}


def assigned_slots(stage, plan):
    """Ordered assignment table from the stage descriptor and the request plan; the two must agree exactly.

    Returns (order, requests) where order is a list of (root_id, arm, replicate) in root-balanced plan order and
    requests maps each slot to the plan's recorded request pins."""
    stage_roots = stage.get("roots")
    stage_arms = stage.get("arms")
    if not isinstance(stage_roots, list) or not stage_roots:
        raise HandoffRefusal("stage descriptor has no non-empty 'roots' list")
    if not isinstance(stage_arms, dict) or not stage_arms:
        raise HandoffRefusal("stage descriptor has no non-empty 'arms' map")
    stage_expected = set()
    for root_id in stage_roots:
        if not isinstance(root_id, str) or not root_id:
            raise HandoffRefusal(f"stage descriptor root {root_id!r} is not a root id")
        for arm, replicates in stage_arms.items():
            if not isinstance(replicates, list) or not replicates:
                raise HandoffRefusal(f"stage descriptor arm {arm!r} has no non-empty replicate list")
            for replicate in replicates:
                if type(replicate) is not int or replicate < 0:
                    raise HandoffRefusal(f"stage descriptor arm {arm!r} has a non-integer replicate")
                stage_expected.add((root_id, arm, replicate))

    plan_roots = plan.get("roots")
    if not isinstance(plan_roots, list) or not plan_roots:
        raise HandoffRefusal("request plan has no non-empty 'roots' list")
    order, requests = [], {}
    for entry in plan_roots:
        if not isinstance(entry, dict):
            raise HandoffRefusal(f"request plan root entry {entry!r} is not an object")
        root_id = entry.get("root_id")
        if root_id not in stage_roots:
            raise HandoffRefusal(f"request plan root {root_id!r} is not a stage checkpoint {stage_roots}")
        plan_requests = entry.get("requests")
        if not isinstance(plan_requests, list) or not plan_requests:
            raise HandoffRefusal(f"request plan root {root_id} has no non-empty 'requests' list")
        for request in plan_requests:
            slot = (root_id, request.get("arm"), request.get("replicate"))
            if slot not in stage_expected:
                raise HandoffRefusal(f"request plan slot {slot} is not assigned by the stage descriptor")
            if slot in requests:
                raise HandoffRefusal(f"request plan repeats slot {slot[0]}/{slot[1]}/{slot[2]}")
            requests[slot] = request
            order.append(slot)
    missing = sorted(stage_expected - set(requests))
    if missing:
        raise HandoffRefusal("request plan omits assigned slots: "
                             + ", ".join(f"{r}/{a}/{rep}" for r, a, rep in missing))
    return order, requests


def _check_usage(row, slot):
    for field in USAGE_INT_FIELDS:
        value = row.get(field)
        if value is None:
            continue
        if isinstance(value, bool) or type(value) is not int or value < 0:
            raise HandoffRefusal(f"slot {slot}: {field}={value!r} must be a nonnegative int or absent/null")


def validate_handoff(collect_dir, stage, plan):
    """Validate the collection handoff. Raises HandoffRefusal and writes nothing on any mismatch."""
    collect_dir = Path(collect_dir)
    if collect_dir.is_dir() and not (collect_dir / "manifest.json").is_file() \
            and (collect_dir / "collect" / "manifest.json").is_file():
        collect_dir = collect_dir / "collect"
    if not collect_dir.is_dir():
        raise HandoffRefusal(f"collection directory {collect_dir} does not exist")
    for name in ("manifest.json", "completion.json", "calls.jsonl"):
        if not (collect_dir / name).is_file():
            raise HandoffRefusal(f"collection handoff is missing {name}")

    stage_data, stage_sha, stage_path = _load_pinned(stage, "stage descriptor")
    plan_data, plan_sha, plan_path = _load_pinned(plan, "request plan")
    order, requests = assigned_slots(stage_data, plan_data)

    manifest_bytes = (collect_dir / "manifest.json").read_bytes()
    manifest = _strict_json(manifest_bytes, "collection manifest")
    absent = sorted(REQUIRED_MANIFEST_KEYS - set(manifest))
    if absent:
        raise HandoffRefusal(f"collection manifest is missing required keys: {absent}")
    completion = _strict_json((collect_dir / "completion.json").read_bytes(), "collection completion record")
    absent = sorted(REQUIRED_COMPLETION_KEYS - set(completion))
    if absent:
        raise HandoffRefusal(f"collection completion record is missing required keys: {absent}")

    manifest_sha = _sha256_bytes(manifest_bytes)
    if completion["manifest_sha256"] != manifest_sha:
        raise HandoffRefusal("completion record does not bind the collection manifest bytes "
                             f"(records {completion['manifest_sha256']!r}, manifest is {manifest_sha})")
    if manifest.get("stage") != stage_data.get("stage") or completion.get("stage") != stage_data.get("stage"):
        raise HandoffRefusal(f"collection stage label does not match the stage descriptor "
                             f"{stage_data.get('stage')!r}")
    if manifest["stage_descriptor_sha256"] != stage_sha:
        raise HandoffRefusal("stale or wrong stage pin: collection recorded stage_descriptor_sha256 "
                             f"{manifest['stage_descriptor_sha256']!r}, descriptor is {stage_sha}")
    if manifest["request_plan_sha256"] != plan_sha:
        raise HandoffRefusal("stale or wrong request-plan pin: collection recorded request_plan_sha256 "
                             f"{manifest['request_plan_sha256']!r}, plan is {plan_sha}")
    if manifest["grader_version"] != private_grade.GRADER_VERSION:
        raise HandoffRefusal(f"grader pin mismatch: collection recorded {manifest['grader_version']!r}, this "
                             f"grader is {private_grade.GRADER_VERSION!r}")

    # Manifest checksums must cover exactly the written files (manifest/completion excepted).
    checksums = manifest["checksums"]
    if not isinstance(checksums, dict) or not checksums:
        raise HandoffRefusal("collection manifest carries no checksums")
    present = {str(p.relative_to(collect_dir)) for p in collect_dir.rglob("*") if p.is_file()}
    present -= {"manifest.json", "completion.json"}
    listed = set(checksums)
    if listed != present:
        raise HandoffRefusal("collection manifest checksums do not cover the written files exactly "
                             f"(unlisted: {sorted(present - listed)}; listed but absent: {sorted(listed - present)})")
    for relpath, recorded in sorted(checksums.items()):
        if not isinstance(recorded, str) or not re.fullmatch(r"[0-9a-f]{64}", recorded):
            raise HandoffRefusal(f"checksum for {relpath} is not a sha256 hex digest")
        actual = file_sha(collect_dir / relpath)
        if actual != recorded:
            raise HandoffRefusal(f"written file {relpath} does not match its recorded checksum "
                                 f"(recorded {recorded}, bytes hash to {actual})")

    rows, artifacts = {}, {}
    lines = (collect_dir / "calls.jsonl").read_text().splitlines()
    for lineno, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        row = _strict_json(line, f"calls.jsonl line {lineno}")
        absent = sorted(REQUIRED_CALL_KEYS - set(row))
        if absent:
            raise HandoffRefusal(f"calls.jsonl line {lineno} is missing required keys: {absent}")
        slot = (row["root_id"], row["arm"], row["replicate"])
        if slot not in requests:
            raise HandoffRefusal(f"calls.jsonl line {lineno} records unassigned slot {slot}")
        if slot in rows:
            raise HandoffRefusal(f"calls.jsonl has duplicate records for assigned slot "
                                 f"{slot[0]}/{slot[1]}/{slot[2]}")
        request = requests[slot]
        for pin in ("seed", "messages_sha256"):
            if pin in request and row.get(pin) != request[pin]:
                raise HandoffRefusal(f"slot {slot[0]}/{slot[1]}/{slot[2]} records {pin}={row.get(pin)!r} but the "
                                     f"assignment pins {request[pin]!r}")
        if row["status"] not in CALL_STATUSES:
            raise HandoffRefusal(f"slot {slot[0]}/{slot[1]}/{slot[2]} has status {row['status']!r}; "
                                 f"expected one of {sorted(CALL_STATUSES)}")
        _check_usage(row, f"{slot[0]}/{slot[1]}/{slot[2]}")
        artifact_path = row["artifact_path"]
        if artifact_path is None:
            if row["status"] != "unavailable":
                raise HandoffRefusal(f"slot {slot[0]}/{slot[1]}/{slot[2]} has no artifact but status "
                                     f"{row['status']!r}")
            reason = row["missing_reason"]
            if not isinstance(reason, str) or not reason.strip():
                raise HandoffRefusal(f"slot {slot[0]}/{slot[1]}/{slot[2]} has no artifact and no missing_reason")
            if row["output_sha256"] is not None:
                raise HandoffRefusal(f"slot {slot[0]}/{slot[1]}/{slot[2]} has no artifact but an output digest")
        else:
            if row["status"] != "completed" or row["missing_reason"] is not None:
                raise HandoffRefusal(f"slot {slot[0]}/{slot[1]}/{slot[2]} carries an artifact with status "
                                     f"{row['status']!r} and missing_reason {row['missing_reason']!r}")
            if not isinstance(artifact_path, str) or artifact_path.startswith("/") or ".." in Path(artifact_path).parts:
                raise HandoffRefusal(f"slot {slot[0]}/{slot[1]}/{slot[2]} artifact_path {artifact_path!r} must be "
                                     "a relative path inside the collection directory")
            if artifact_path not in checksums:
                raise HandoffRefusal(f"artifact {artifact_path} is not covered by the manifest checksums")
            text = (collect_dir / artifact_path).read_text()
            recorded = row["output_sha256"]
            actual = digest(text)
            if recorded != actual:
                raise HandoffRefusal(f"artifact {artifact_path} bytes do not match the output digest recorded "
                                     f"for {slot[0]}/{slot[1]}/{slot[2]} (recorded {recorded!r}, bytes digest {actual})")
            artifacts[slot] = text
        rows[slot] = row
    absent = [slot for slot in order if slot not in rows]
    if absent:
        raise HandoffRefusal("assigned slots absent from calls.jsonl: "
                             + ", ".join(f"{r}/{a}/{rep}" for r, a, rep in absent))

    if completion["assigned"] != len(order):
        raise HandoffRefusal(f"completion record claims {completion['assigned']} assigned slots; the assignment "
                             f"has {len(order)}")
    completed = sum(1 for slot in order if slot in artifacts)
    if completion["completed"] != completed:
        raise HandoffRefusal(f"completion record claims {completion['completed']} completed slots; the call ledger "
                             f"carries {completed}")
    dispatched = completion["dispatched"]
    if type(dispatched) is not int or not completed <= dispatched <= len(order):
        raise HandoffRefusal(f"completion record dispatched={dispatched!r} is not between completed ({completed}) "
                             f"and assigned ({len(order)})")

    release_manifest_path = _resolve(manifest["release_manifest_path"])
    if not release_manifest_path.is_file():
        raise HandoffRefusal(f"release manifest {release_manifest_path} recorded by the collection does not exist")
    release_bytes = release_manifest_path.read_bytes()
    release_sha = _sha256_bytes(release_bytes)
    if manifest["release_manifest_sha256"] != release_sha:
        raise HandoffRefusal("stale or wrong release pin: collection recorded release_manifest_sha256 "
                             f"{manifest['release_manifest_sha256']!r}, manifest is {release_sha}")
    release = _strict_json(release_bytes, "release manifest")
    for field in ("model", "evaluator"):
        if field not in release:
            raise HandoffRefusal(f"release manifest has no {field} pin")
        if digest(manifest[field]) != digest(release[field]):
            raise HandoffRefusal(f"{field} pin mismatch between the collection manifest and the release manifest")
    limits = load_e13a_grading_limits(release_bytes)
    if limits["artifact_starts"] < len(order):
        raise HandoffRefusal(f"release grading_limits allow {limits['artifact_starts']} artifact starts for "
                             f"{len(order)} assigned slots")

    return {
        "collect_dir": collect_dir,
        "manifest": manifest,
        "manifest_sha256": manifest_sha,
        "completion": completion,
        "order": order,
        "requests": requests,
        "rows": rows,
        "artifacts": artifacts,
        "grading_limits": limits,
        "release_manifest_path": release_manifest_path,
        "release_manifest_sha256": release_sha,
        "release": release,
        "transport_only": bool(manifest["transport_only"]),
        "pins": {
            "stage_descriptor_path": stage_path, "stage_descriptor_sha256": stage_sha,
            "request_plan_path": plan_path, "request_plan_sha256": plan_sha,
            "release_manifest_path": str(release_manifest_path), "release_manifest_sha256": release_sha,
            "grader_version": private_grade.GRADER_VERSION,
            "collection_manifest_sha256": manifest_sha,
            "collection_calls_sha256": file_sha(collect_dir / "calls.jsonl"),
            "collection_completion_sha256": file_sha(collect_dir / "completion.json"),
        },
    }


class StubPrivateExecutor:
    """Deterministic transport-only stand-in for sandbox.run_program. It NEVER executes the program.

    It reads the start marker and sentinel out of the prepared program text and synthesises the result record the
    real grade.evaluate expects, so the real grading path is exercised end to end with nothing started. It
    declares sandbox_kind "seatbelt" because grade.evaluate refuses anything else; every record it produces
    carries transport_only True and the driver labels the whole run transport-only. Transport-only output
    describes plumbing, never model behaviour.

    outcomes: optional {(root_id, code_sha256): 1 | 0 | "unavailable"} override for candidate payloads.
    """

    kind = "stub-transport-only"

    def __init__(self, outcomes=None, seconds=0.001, default_candidate=None):
        self.outcomes = dict(outcomes or {})
        self.seconds = float(seconds)
        self.default_candidate = default_candidate
        self.context = None
        self.calls = []

    def set_context(self, root_id, kind, code_sha256):
        self.context = {"root_id": root_id, "kind": kind, "code_sha256": code_sha256}

    def _decide(self):
        context = self.context or {"root_id": None, "kind": "candidate", "code_sha256": ""}
        if context["kind"] == "reference":
            return 1
        if context["kind"] == "negative_control":
            return 0
        key = (context["root_id"], context["code_sha256"])
        if key in self.outcomes:
            return self.outcomes[key]
        if self.default_candidate is not None:
            return self.default_candidate
        return int(context["code_sha256"][:1] in set("0123456789abc"))

    def __call__(self, program, timeout_s=2, cpu_seconds=1, output_cap=65536):
        markers = MARKER_RE.findall(program)
        start = next((m for m in markers if m.startswith(private_grade.STARTED)), None)
        sentinel = next((m for m in markers if m.startswith("__LANDMARK_PRIVATE_OK__")), None)
        if start is None or sentinel is None:
            raise RuntimeError("prepared program carries no grader markers")
        decision = self._decide()
        self.calls.append({**(self.context or {}), "decision": decision})
        if decision == "unavailable":
            raise RuntimeError("stub private executor declared the outcome unavailable")
        passed = decision == 1
        return {"executed": True, "passed": passed, "timed_out": False, "returncode": 0,
                "sandbox_kind": "seatbelt", "stdout": start + "\n",
                "stdout_tail": sentinel if passed else "AssertionError: private assertion failed",
                "seconds": self.seconds, "transport_only": True}


class _StartLedger:
    """Start ceilings and the grading seconds cap. A refused start never drops an assigned grade row."""

    def __init__(self, limits, clock=None, phase=PRIVATE_GRADING_PHASE):
        self.caps = {"candidate": limits["artifact_starts"], "recheck": limits["recheck_starts"],
                     "containment": limits["containment_starts"], "total": limits["max_private_starts"]}
        self.used = {kind: 0 for kind in self.caps}
        self.seconds_cap = float(limits["grading_seconds"])
        self.clock = clock
        self.phase = phase
        self.started = time.monotonic()
        self.executor_seconds = 0.0
        self.refusals = []

    @staticmethod
    def _bucket(kind):
        return "candidate" if kind == "candidate" else "recheck" if kind in ("reference", "negative_control") \
            else "containment"

    def elapsed(self):
        return time.monotonic() - self.started

    def blocked(self, kind):
        """None if a start is permitted, else the explicit reason it is not. Raises GradingAbort on a clock cap."""
        if self.clock is not None:
            try:
                self.clock.check(self.phase)
            except Exception as exc:  # the shared StageClock raises CapExhausted; treat any cap as a resource abort
                raise GradingAbort(f"stage clock refused phase {self.phase}: {type(exc).__name__}: {exc}") from exc
            remaining = None
            try:
                remaining = self.clock.remaining(self.phase)
            except Exception:
                remaining = None
            if remaining is not None and remaining <= 2:
                return "grading_seconds_exhausted"
        if self.elapsed() + 2 > self.seconds_cap:
            return "grading_seconds_exhausted"
        bucket = self._bucket(kind)
        if self.used[bucket] >= self.caps[bucket]:
            return f"start_ceiling_reached:{bucket}"
        if self.used["total"] >= self.caps["total"]:
            return "start_ceiling_reached:total"
        return None

    def record(self, kind, started, seconds):
        if not started:
            return 0
        bucket = self._bucket(kind)
        self.used[bucket] += 1
        self.used["total"] += 1
        self.executor_seconds = round(self.executor_seconds + float(seconds or 0.0), 6)
        if self.used[bucket] > self.caps[bucket] or self.used["total"] > self.caps["total"]:
            raise GradingAbort(f"private start ceiling exceeded for {bucket}: "
                               f"{self.used[bucket]}/{self.caps[bucket]}, total {self.used['total']}/{self.caps['total']}")
        return 1

    def report(self):
        return {"caps": dict(self.caps), "used": dict(self.used),
                "executor_seconds_known_sum": self.executor_seconds,
                "grading_seconds_cap": self.seconds_cap, "wall_seconds": round(self.elapsed(), 6),
                "refused_starts": list(self.refusals)}


def _load_jsonl(path, what):
    rows = []
    for lineno, line in enumerate(Path(path).read_text().splitlines(), start=1):
        if line.strip():
            rows.append(_strict_json(line, f"{what} line {lineno}"))
    return rows


def _release_inputs(release_dir, handoff, real):
    """Specs, tasks and the frozen grading contract for the release the collection pinned."""
    release_dir = Path(release_dir)
    manifest_path = release_dir / "release_manifest.json"
    if manifest_path.resolve() != handoff["release_manifest_path"].resolve():
        raise HandoffRefusal(f"release directory {release_dir} does not hold the release manifest the collection "
                             f"pinned ({handoff['release_manifest_path']})")
    release_bytes = manifest_path.read_bytes()
    if _sha256_bytes(release_bytes) != handoff["release_manifest_sha256"]:
        raise HandoffRefusal("release manifest changed between handoff validation and grading")
    release = handoff["release"]
    package = release.get("package")
    if not isinstance(package, dict) or not package:
        raise HandoffRefusal("release manifest carries no package hashes")
    for name, recorded in sorted(package.items()):
        path = release_dir / name
        if not path.is_file():
            raise HandoffRefusal(f"release package file {name} is missing")
        if file_sha(path) != recorded:
            raise HandoffRefusal(f"release package file {name} does not match its recorded hash")
    specs = _load_jsonl(release_dir / "private_specs.jsonl", "private specs")
    tasks = _load_jsonl(release_dir / "tasks.jsonl", "release tasks")
    try:
        private_grade.validate_specs(tasks, specs)
    except ValueError as exc:
        raise HandoffRefusal(f"private specs do not bind the release tasks: {exc}") from exc
    limits = load_e13a_grading_limits(release_bytes, specs)
    contract = private_grade.contract(specs)
    contract_sha = digest(contract)
    bindings = release.get("grading_bindings") or {}
    expected = bindings.get("expected_contract_sha256")
    if expected is not None and expected != contract_sha:
        raise HandoffRefusal(f"frozen grading contract pin mismatch: release expects {expected}, this source "
                             f"tree produces {contract_sha}")
    committed = None
    if real:
        committed = study_adapter.verify_committed_release(manifest_path, data=release_bytes)
        study_adapter.load_release_bindings(manifest_path, release_dir / "private_specs.jsonl", data=release_bytes)
    else:
        try:
            committed = study_adapter.verify_committed_release(manifest_path, data=release_bytes)
        except Exception as exc:  # transport-only: recorded as an explicit unknown, never silently passed
            committed = f"unverified: {type(exc).__name__}: {exc}"
    return {"specs": specs, "tasks": tasks, "contract": contract, "contract_sha256": contract_sha,
            "limits": limits, "committed_release_verification": committed,
            "release_dir": release_dir, "release_manifest_path": manifest_path}


def _evaluate(spec, code, kind, executor, ledger, attempts, root_id):
    """One bounded pass through the REAL grade.evaluate with the injected executor."""
    code_sha = digest(code)
    blocked = ledger.blocked(kind)
    if blocked is not None:
        ledger.refusals.append({"root_id": root_id, "kind": kind, "code_sha256": code_sha, "reason": blocked})
        attempt = {"root_id": root_id, "kind": kind, "code_sha256": code_sha, "outcome": None,
                   "reason": blocked, "sandbox_executed": False, "started": 0}
        attempts.append(attempt)
        return {"outcome": None, "reason": blocked, "sandbox_executed": False, "starts": 0}
    if hasattr(executor, "set_context"):
        executor.set_context(root_id, kind, code_sha)
    result = private_grade.evaluate(spec, code, executor)
    seconds = (result.get("run") or {}).get("seconds", 0.0)
    starts = ledger.record(kind, bool(result.get("sandbox_executed")), seconds)
    attempts.append({"root_id": root_id, "kind": kind, "code_sha256": code_sha,
                     "outcome": result.get("outcome"), "reason": result.get("reason"),
                     "sandbox_executed": bool(result.get("sandbox_executed")), "started": starts,
                     "executor_seconds": seconds, "details": result.get("details")})
    return {**result, "starts": starts, "executor_seconds": seconds}


def _write_outputs(out_grade_dir, grades, attempts, summary, failure=None):
    (out_grade_dir / "grades.jsonl").write_text("".join(json.dumps(g) + "\n" for g in grades))
    (out_grade_dir / "grading_attempts.jsonl").write_text("".join(json.dumps(a) + "\n" for a in attempts))
    if failure is not None:
        (out_grade_dir / "failure_report.json").write_text(json.dumps(failure, indent=1) + "\n")
    summary = {**summary, "checksums": {p.name: file_sha(p) for p in sorted(out_grade_dir.glob("*"))
                                        if p.is_file() and p.name != "summary.json"}}
    (out_grade_dir / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    return summary


def grade(collect_dir, release_dir, out_dir, *, executor=None, real=False, clock=None, stage=None, plan=None,
          attestation_path=None):
    """Validate the handoff, then grade every assigned slot through the real private grading components.

    Returns the summary dict. Refusals (HandoffRefusal) happen before any output directory is created; an
    integrity or resource abort still writes grades.jsonl with every assigned slot plus failure_report.json."""
    out_grade_dir = Path(out_dir) / "grade"
    if out_grade_dir.exists():
        raise HandoffRefusal(f"Refusing to overwrite {out_grade_dir}")
    if stage is None:
        stage = DEFAULT_STAGE
    handoff = validate_handoff(collect_dir, stage, plan if plan is not None else _plan_from_collection(collect_dir))
    inputs = _release_inputs(release_dir, handoff, real)
    limits = inputs["limits"]
    if executor is None:
        if not real:
            raise HandoffRefusal("a private executor must be injected; with real=False pass StubPrivateExecutor")
        executor = private_grade.sandbox.run_program
    transport_only = bool(handoff["transport_only"] or not real)

    containment = {"status": "not_started_transport_only", "starts_used": 0, "attestation_sha256": None}
    if real:
        if attestation_path is None:
            raise HandoffRefusal("real grading requires a containment attestation")
        attestation = private_grade.verify_attestation(attestation_path)
        checks = len(attestation.get("checks", []))
        if checks > limits["containment_starts"]:
            raise HandoffRefusal(f"containment attestation records {checks} payload starts; the release allows "
                                 f"{limits['containment_starts']}")
        containment = {"status": "attested", "starts_used": checks,
                       "attestation_sha256": file_sha(attestation_path)}

    out_grade_dir.mkdir(parents=True, exist_ok=False)
    ledger = _StartLedger(limits, clock=clock)
    ledger.used["containment"] = containment["starts_used"]
    ledger.used["total"] = containment["starts_used"]
    by_root = {spec["root_id"]: spec for spec in inputs["specs"]}
    grader_id = "landmark-private-tests-v1:" + inputs["contract_sha256"][:12]

    grades, attempts, cache = [], [], {}
    references, controls = {}, {}
    status, abort_reason = "complete", None

    def blank_row(slot, reason):
        row = handoff["rows"][slot]
        return {"root_id": slot[0], "arm": slot[1], "replicate": slot[2],
                "output_sha256": row["output_sha256"], "outcome": None, "missing_reason": reason,
                "grader_id": grader_id, "grading_contract_sha256": inputs["contract_sha256"],
                "grader_version": private_grade.GRADER_VERSION, "transport_only": transport_only,
                "calls": row.get("calls"), "prompt_tokens": row.get("prompt_tokens"),
                "completion_tokens": row.get("completion_tokens"), "executor_starts": 0, "executor_seconds": 0.0}

    try:
        for slot in handoff["order"]:
            root_id, arm, replicate = slot
            row = handoff["rows"][slot]
            spec = by_root.get(root_id)
            if spec is None:
                raise GradingAbort(f"release has no private spec for assigned root {root_id}")
            if root_id not in references:
                references[root_id] = _evaluate(spec, spec["reference_code"], "reference", executor, ledger,
                                                attempts, root_id)
                controls[root_id] = []
                if references[root_id]["outcome"] == 1:
                    controls[root_id] = [_evaluate(spec, control["code"], "negative_control", executor, ledger,
                                                   attempts, root_id) for control in spec["negative_controls"]]
            outcome, reason, starts, seconds = None, None, 0, 0.0
            if slot not in handoff["artifacts"]:
                reason = row["missing_reason"]
            elif references[root_id]["outcome"] != 1:
                reason = "reference_validation_failed_or_unavailable:" + str(references[root_id].get("reason"))
            elif not controls[root_id] or not all(c["outcome"] == 0 and c["sandbox_executed"]
                                                  for c in controls[root_id]):
                reason = "negative_control_validation_failed_or_unavailable"
            else:
                # Defense in depth: the artifact bytes are re-bound to the recorded digest at grading time.
                text = (handoff["collect_dir"] / row["artifact_path"]).read_text()
                if digest(text) != row["output_sha256"]:
                    raise GradingAbort(f"artifact {row['artifact_path']} changed after handoff validation; its "
                                       f"bytes no longer match the recorded output digest")
                key = (root_id, row["output_sha256"])
                if key in cache:
                    cached = cache[key]
                    outcome, reason = cached["outcome"], cached["reason"]
                    attempts.append({"root_id": root_id, "kind": "candidate_cache_hit",
                                     "code_sha256": cached["code_sha256"], "outcome": outcome, "reason": reason,
                                     "sandbox_executed": False, "started": 0})
                else:
                    try:
                        code = private_grade.extract_code(text)
                    except ValueError as exc:
                        # Pre-execution format rejection: an observed endpoint failure, no start consumed.
                        cache[key] = {"outcome": 0, "reason": None, "code_sha256": digest(text),
                                      "details": str(exc)}
                        attempts.append({"root_id": root_id, "kind": "candidate_format_rejection",
                                         "code_sha256": digest(text), "outcome": 0,
                                         "reason": "unparseable_output", "sandbox_executed": False, "started": 0,
                                         "details": str(exc)})
                        outcome, reason = 0, None
                        code = None
                    if code is not None:
                        result = _evaluate(spec, code, "candidate", executor, ledger, attempts, root_id)
                        outcome = result["outcome"]
                        reason = None if outcome is not None else result.get("reason")
                        starts, seconds = result["starts"], result.get("executor_seconds") or 0.0
                        cache[key] = {"outcome": outcome, "reason": reason, "code_sha256": digest(code)}
                    else:
                        outcome, reason = cache[key]["outcome"], cache[key]["reason"]
            if outcome is None and (not isinstance(reason, str) or not reason.strip()):
                reason = "grading_outcome_unavailable_without_recorded_reason"
            grades.append({"root_id": root_id, "arm": arm, "replicate": replicate,
                           "output_sha256": row["output_sha256"], "outcome": outcome,
                           "missing_reason": reason if outcome is None else None,
                           "grader_id": grader_id, "grading_contract_sha256": inputs["contract_sha256"],
                           "grader_version": private_grade.GRADER_VERSION, "transport_only": transport_only,
                           "calls": row.get("calls"), "prompt_tokens": row.get("prompt_tokens"),
                           "completion_tokens": row.get("completion_tokens"),
                           "executor_starts": starts, "executor_seconds": round(float(seconds), 6)})
    except (GradingAbort, HandoffRefusal, OSError) as exc:
        status, abort_reason = "aborted", f"{type(exc).__name__}: {exc}"
        graded_slots = {(g["root_id"], g["arm"], g["replicate"]) for g in grades}
        for slot in handoff["order"]:
            if slot not in graded_slots:
                grades.append(blank_row(slot, f"grading_aborted: {abort_reason}"))

    summary = {
        "grade_driver_version": GRADE_DRIVER_VERSION,
        "evidence_class": EVIDENCE_CLASS,
        "status": status,
        "abort_reason": abort_reason,
        "stage": handoff["manifest"]["stage"],
        "real": bool(real),
        "transport_only": transport_only,
        "transport_only_note": ("private executor injected; no candidate, reference or containment payload was "
                               "executed; these rows describe plumbing only and are NOT grades of model behaviour"
                               if transport_only else "real private execution under the frozen containment gate"),
        "executor": getattr(executor, "kind", type(executor).__name__),
        "pins": {**handoff["pins"], "grading_contract_sha256": inputs["contract_sha256"],
                 "grading_contract": inputs["contract"],
                 "committed_release_verification": inputs["committed_release_verification"],
                 "release_dir": str(inputs["release_dir"])},
        "grading_limits": limits,
        "containment": containment,
        "start_accounting": ledger.report(),
        "assigned_slots": len(handoff["order"]),
        "grade_rows": len(grades),
        "graded_slots": sum(1 for g in grades if g["outcome"] is not None),
        "missing_slots": [{"root_id": g["root_id"], "arm": g["arm"], "replicate": g["replicate"],
                           "missing_reason": g["missing_reason"]} for g in grades if g["outcome"] is None],
        "cache_hits": sum(1 for a in attempts if a["kind"] == "candidate_cache_hit"),
        "format_rejections": sum(1 for a in attempts if a["kind"] == "candidate_format_rejection"),
        "receiver_calls": 0,
        "model_calls": 0,
        "analysis_command": ("python3 scripts/e13a_analyze.py --grades <out>/grade/grades.jsonl "
                             "--stage experiments/landmark/e13a_stage.json --out <out>/analysis_report.json"),
    }
    failure = None
    if status == "aborted":
        failure = {"status": status, "abort_reason": abort_reason, "assigned_slots": len(handoff["order"]),
                   "retained_slots": len(grades),
                   "slots": [{"root_id": g["root_id"], "arm": g["arm"], "replicate": g["replicate"],
                              "outcome": g["outcome"], "missing_reason": g["missing_reason"]} for g in grades],
                   "start_accounting": ledger.report(),
                   "note": "every assigned slot is retained; no row is dropped and no outcome is zero-filled"}
    return _write_outputs(out_grade_dir, grades, attempts, summary, failure)


def _plan_from_collection(collect_dir):
    """The request plan path the collection recorded, so grade() needs only the collection directory."""
    collect_dir = Path(collect_dir)
    manifest_path = collect_dir / "manifest.json"
    if not manifest_path.is_file():
        manifest_path = collect_dir / "collect" / "manifest.json"
    if not manifest_path.is_file():
        raise HandoffRefusal(f"collection directory {collect_dir} has no manifest.json")
    manifest = _strict_json(manifest_path.read_bytes(), "collection manifest")
    recorded = manifest.get("request_plan_path")
    if not isinstance(recorded, str) or not recorded:
        raise HandoffRefusal("collection manifest records no request_plan_path; pass plan= explicitly")
    return _resolve(recorded)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--collect", type=Path, required=True, help="collection run directory (or its collect/ dir)")
    ap.add_argument("--release", type=Path, default=DEFAULT_RELEASE_DIR, help="e13a_release directory")
    ap.add_argument("--out", type=Path, required=True, help="run directory; grade/ is created inside it")
    ap.add_argument("--stage", type=Path, default=DEFAULT_STAGE)
    ap.add_argument("--plan", type=Path, default=None, help="request plan (default: the one the collection pinned)")
    ap.add_argument("--real", action="store_true",
                    help="require the committed release and containment attestation; the executor is still injected")
    ap.add_argument("--attestation", type=Path, default=None)
    ap.add_argument("--validate-only", action="store_true", help="run validate_handoff and write nothing")
    a = ap.parse_args(argv)
    try:
        if a.validate_only:
            handoff = validate_handoff(a.collect, a.stage,
                                       a.plan if a.plan is not None else _plan_from_collection(a.collect))
            print(json.dumps({"handoff": "validated", "assigned_slots": len(handoff["order"]),
                              "completed_artifacts": len(handoff["artifacts"]), "pins": handoff["pins"]}, indent=1))
            return 0
        if a.real:
            raise SystemExit("Refusing: real private execution is not authorized from this CLI (MRL-19 allowance); "
                             "grade(real=True) requires a separately bound executor and attestation")
        summary = grade(a.collect, a.release, a.out, executor=StubPrivateExecutor(), real=False,
                        stage=a.stage, plan=a.plan, attestation_path=a.attestation)
    except HandoffRefusal as exc:
        raise SystemExit(f"Refusing to grade: {exc}") from exc
    print(json.dumps({"status": summary["status"], "grade_rows": summary["grade_rows"],
                      "graded_slots": summary["graded_slots"], "transport_only": summary["transport_only"],
                      "start_accounting": summary["start_accounting"]["used"]}, indent=1))
    return 0 if summary["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
