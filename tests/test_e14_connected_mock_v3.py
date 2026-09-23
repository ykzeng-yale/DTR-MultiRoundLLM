"""MRL-25 failure-mode matrix through the real run()/score_private() entry points. Injected fakes only.

The module under test is loaded from E14_MOCK_UNDER_TEST (default: scripts/e14_connected_mock.py), so the SAME
fixtures can be run against the reviewed v2 baseline (1c66f86) to show each one fails there and passes on v3.
"""
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
_path = Path(os.environ.get("E14_MOCK_UNDER_TEST", ROOT / "scripts/e14_connected_mock.py"))
_spec = importlib.util.spec_from_file_location("e14_mut", _path)
cm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cm)

V2 = ROOT / "experiments/landmark/e14_release_v2"
SPEC = ROOT / "docs/e14_lead_measurement_spec_20260923.json"
SCHEMA = "public-diagnostic-v2"


def inventory():
    tasks = [json.loads(x) for x in (V2 / "tasks.jsonl").read_text().splitlines() if x.strip()]
    return {"complete": True, "roots": {t["root_id"]: {"labels": [], "numeric": []} for t in tasks}}


def trusted():
    import hashlib, subprocess
    blob = subprocess.run(["git", "show", "HEAD:experiments/landmark/e14_release_v2/release_manifest.json"],
                          cwd=ROOT, capture_output=True, check=True).stdout
    return hashlib.sha256(blob).hexdigest()


class Fakes:
    def __init__(self, returns=None, status="wrong_value", diag_override=None):
        self.returns, self.status, self.diag_override = returns or {}, status, diag_override
        self.transport_calls, self.checker_calls = [], []

    def transport(self, messages, seed):
        self.transport_calls.append(seed)
        n = len(self.transport_calls)
        if n in self.returns:
            return self.returns[n]
        return {"text": f"def f():\n    return {seed}\n", "usage": {"completion_tokens": 5}}

    def checker(self, rid, answer):
        self.checker_calls.append(rid)
        if self.diag_override is not None:
            return self.diag_override
        return {"schema_version": SCHEMA, "root_id": rid, "cases": [{"case_id": "public-1", "status": self.status}]}


def go(tmp_path, fakes, rel=V2, spec=SPEC, name="run", **kw):
    """Adapts to either API so the same fixture runs on the reviewed v2 module and on v3."""
    args = dict(transport=fakes.transport, public_checker=fakes.checker, scorer=None, inventory=inventory(), **kw)
    if hasattr(cm, "committed_manifest_sha256"):
        args["trusted_manifest_sha256"] = trusted()
    return cm.run(rel, spec, tmp_path / name, **args)


def disk(tmp_path, name="run"):
    return json.loads((tmp_path / name / "ledger.json").read_text())


def classified(doc):
    """No slot may be left mid-flight or unclassified once a run returns."""
    return all(s["state"] in ("completed", "failed", "not_attempted") for s in doc["slots"].values())


# ------------------------------------------------ criterion 1: exact binding, refused before ANY transport
def _copy(tmp_path):
    d = tmp_path / "relocated"
    shutil.copytree(V2, d)
    return d


def test_changed_terminal_text_under_the_same_label_is_refused_before_transport(tmp_path):
    s = json.loads(SPEC.read_text())
    s["terminal_instruction"]["text"] += " Also explain your answer."          # label unchanged
    bad = tmp_path / "spec.json"
    bad.write_text(json.dumps(s))
    f = Fakes()
    with pytest.raises(Exception):
        go(tmp_path, f, spec=bad)
    assert f.transport_calls == []


def test_changed_task_prompt_is_refused_before_transport(tmp_path):
    d = _copy(tmp_path)
    rows = [json.loads(x) for x in (d / "tasks.jsonl").read_text().splitlines() if x.strip()]
    rows[0]["prompt"] += " (edited)"
    (d / "tasks.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    f = Fakes()
    with pytest.raises(Exception):
        go(tmp_path, f, rel=d)
    assert f.transport_calls == []


def test_changed_manifest_is_refused_before_transport(tmp_path):
    d = _copy(tmp_path)
    m = json.loads((d / "release_manifest.json").read_text())
    m["status"] += " (edited)"
    (d / "release_manifest.json").write_text(json.dumps(m))
    f = Fakes()
    with pytest.raises(Exception):
        go(tmp_path, f, rel=d)
    assert f.transport_calls == []


def test_relocated_copy_with_different_bytes_is_refused(tmp_path):
    d = _copy(tmp_path)
    p = json.loads((d / "public_examples_v3.json").read_text())
    p["version"] = p.get("version", "") + "-edited"
    (d / "public_examples_v3.json").write_text(json.dumps(p))
    f = Fakes()
    with pytest.raises(Exception):
        go(tmp_path, f, rel=d)
    assert f.transport_calls == []


def test_relocated_copy_with_identical_bytes_is_accepted(tmp_path):
    led = go(tmp_path, Fakes(), rel=_copy(tmp_path))
    assert len(led.doc["slots"]) == 130 and led.doc["stopped"] is None


# ------------------------------------------------ criterion 2: explicit stop state at every boundary
@pytest.mark.parametrize("bad_return", [{"no_text": 1}, None, {"text": 7}])
def test_malformed_transport_return_is_classified_and_stops(tmp_path, bad_return):
    f = Fakes(returns={2: bad_return})
    led = go(tmp_path, f)
    doc = disk(tmp_path)
    assert classified(doc), [s["slot"] for s in doc["slots"].values() if s["state"] not in ("completed", "failed", "not_attempted")]
    assert doc["stopped"] == "MalformedTransportReturn" and doc["collection_closed"] is True
    assert len(f.transport_calls) == 2


@pytest.mark.parametrize("diag", [
    {"schema_version": "not-a-schema", "root_id": "x", "cases": []},
    {"schema_version": SCHEMA, "root_id": "x", "cases": [{"case_id": "c", "status": "no-such-status"}]},
])
def test_invalid_public_diagnostic_stops_before_any_continuation(tmp_path, diag):
    f = Fakes(diag_override=diag)
    led = go(tmp_path, f)
    doc = disk(tmp_path)
    assert doc["stopped"] == "InvalidPublicDiagnostic" and classified(doc) and doc["collection_closed"] is True
    assert len(f.transport_calls) == 1 and len(f.checker_calls) == 1


def test_request_byte_violation_stops_the_batch_immediately(tmp_path):
    d = _copy(tmp_path)
    cfg = json.loads((d / "config.json").read_text()); cfg["max_request_bytes"] = 50
    (d / "config.json").write_text(json.dumps(cfg, indent=1))
    m = json.loads((d / "release_manifest.json").read_text())
    import hashlib
    m["package"]["config.json"] = hashlib.sha256((d / "config.json").read_bytes()).hexdigest()
    (d / "release_manifest.json").write_text(json.dumps(m))
    f = Fakes()
    if hasattr(cm, "committed_manifest_sha256"):             # trust the edited manifest explicitly for this probe
        led = cm.run(d, SPEC, tmp_path / "run", transport=f.transport, public_checker=f.checker, scorer=None,
                     inventory=inventory(),
                     trusted_manifest_sha256=hashlib.sha256((d / "release_manifest.json").read_bytes()).hexdigest())
    else:
        led = cm.run(d, SPEC, tmp_path / "run", transport=f.transport, public_checker=f.checker, scorer=None,
                     inventory=inventory())
    doc = disk(tmp_path)
    assert f.transport_calls == [] and doc["stopped"] == "RequestByteLimit" and classified(doc)


# ------------------------------------------------ repair 3: durable, counted scoring
def test_scorer_exception_keeps_prior_grades_on_disk_and_stops_scoring(tmp_path):
    led = go(tmp_path, Fakes())
    calls = {"n": 0}

    def scorer(rid, text):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("sandbox died")
        return 1
    try:
        r = cm.score_private(led, scorer)
    except RuntimeError:
        r = None
    doc = disk(tmp_path)
    graded = [s for s in doc["slots"].values() if s.get("grade_state") == "graded"]
    assert len(graded) == 1 and graded[0]["grade"] == 1                   # the success survived on disk
    assert doc["scoring_stopped"] == "RuntimeError"
    assert sum(1 for s in doc["slots"].values() if s["kind"] == "continuation" and s.get("grade") is None) == 119
    assert r is not None and r["point_contrast"] is None and r["completion_bounds"] is not None


def test_invalid_scorer_return_is_unavailable_not_zero(tmp_path):
    led = go(tmp_path, Fakes())
    try:
        r = cm.score_private(led, lambda rid, text: 2)
    except ValueError:
        r = None
    doc = disk(tmp_path)
    assert r is not None and doc["scoring_stopped"] == "ValueError"
    assert all(s.get("grade") is None for s in doc["slots"].values() if s["kind"] == "continuation")


def test_each_scoring_attempt_is_persisted_before_the_scorer_runs(tmp_path):
    led = go(tmp_path, Fakes())
    seen = []

    def scorer(rid, text):
        doc = disk(tmp_path)
        seen.append(sum(1 for s in doc["slots"].values() if s.get("grade_state") == "scoring_attempt"))
        return 0
    cm.score_private(led, scorer)
    assert seen and all(n == 1 for n in seen)


def test_private_scoring_starts_are_counted_in_the_same_bounded_ledger(tmp_path):
    led = go(tmp_path, Fakes())
    cm.score_private(led, lambda rid, text: 1)
    used = disk(tmp_path)["start_ledger"]["used"]
    assert used["candidate"] == 10 + 120                                  # initial-public + continuation-private


def test_scoring_start_cap_leaves_the_rest_unavailable(tmp_path):
    sl = cm.StartLedger({"containment": 18, "instrument": 40, "grader_rechecks": 30, "candidate": 15})
    led = go(tmp_path, Fakes(), starts=sl)
    r = cm.score_private(led, lambda rid, text: 1)
    doc = disk(tmp_path)
    assert doc["scoring_stopped"] == "start_cap_exhausted" and r["point_contrast"] is None
    assert sum(1 for s in doc["slots"].values() if s.get("grade_state") == "graded") == 5   # 15 - 10 initial-public
