import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiments.landmark import collect, public_check, validation_canaries as vc  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "experiments/landmark/dev_release_v2_template"
CANARIES = ROOT / "experiments/landmark/validation_canaries_v1.json"
TASKS = [{"root_id": "r", "family_id": "f", "prompt": "p", "public_context": ""}]


def load(name):
    return json.loads((T / name).read_text())


def test_templates_parse_and_config_has_exact_v2_keys():
    cfg = load("config.template.json")
    required = {"schema_version", "protocol_version", "freeze_commit", "model", "model_digest", "server_build", "base_url", "seed",
                "split_seed", "split_fractions", "prior_seen_root_ids", "prior_seen_family_ids", "max_calls", "max_completion_tokens",
                "max_seconds", "max_tokens_per_call", "request_timeout_seconds", "max_request_bytes", "decoding", "dataset_sha256",
                "source_code_sha256", "grading_contract_sha256", "dataset_source", "dataset_license", "paid_api_budget_usd",
                "branch_replicates"} | collect.V2_KEYS
    assert set(cfg) == required
    assert cfg["model_digest"].startswith("626b4a66") and cfg["server_build"] == "b1-4fea119"
    assert cfg["base_url"] == "http://127.0.0.1:8193" and cfg["decoding"] == {"temperature": 0.7, "top_p": 0.95, "num_ctx": 8192}
    assert (cfg["max_tokens_per_call"], cfg["max_calls"], cfg["max_completion_tokens"], cfg["branch_replicates"], cfg["paid_api_budget_usd"]) == (512, 77, 39424, 2, 0)
    assert cfg["sampler_law"] == "server_defaults_pinned"
    collect.check_sampler(cfg["sampler"])
    for k in ("receiver_state_sha256", "dataset_sha256", "grading_contract_sha256", "source_code_sha256", "freeze_commit"):
        assert cfg[k].startswith("UNRESOLVED:")
    own = load("ownership.template.json")
    assert set(own) == {"receiver_base_url", "server_pid", "server_start_utc", "owner_project", "exclusive_window_start_utc",
                        "exclusive_window_end_utc", "agreement_ref", "recorded_by", "recorded_utc"}
    assert all(v.startswith("UNRESOLVED:") for v in own.values())
    man = load("release_manifest.template.json")
    assert [g["gate"] for g in man["gates"]] == [f"E{i}" for i in range(1, 11)]
    assert man["start_ledger"]["integrity_total"] == 24 and man["start_ledger"]["core_total"] == 161


def test_config_template_refused_in_real_and_by_unresolved_helper():
    cfg = load("config.template.json")
    with pytest.raises(ValueError):
        collect.validate(cfg, TASKS, real=True)
    with pytest.raises(ValueError, match="UNRESOLVED"):
        vc.refuse_unresolved(cfg, "config")
    with pytest.raises(ValueError, match="UNRESOLVED"):
        vc.refuse_unresolved(load("ownership.template.json"), "ownership")


def test_canary_schema_compiles_and_statuses_allowed():
    doc, sha = vc.load_canaries(CANARIES)
    assert re.fullmatch(r"[0-9a-f]{64}", sha)
    by_gate = {}
    for c in doc["canaries"]:
        by_gate[c["gate"]] = by_gate.get(c["gate"], 0) + 1
        compile(c["candidate_code"], c["id"], "exec")  # compile only
        assert public_check.static_code(c["candidate_code"]) is not None
        assert c["expected"] in c["acceptable"]
        for pattern in c["acceptable"]:
            assert all(r["status"] in public_check.STATUSES for r in pattern)
            for i in c["never_pass_cases"]:
                assert pattern[i]["status"] != "pass"
    assert by_gate == {"E3": 11, "E4": 2, "E5": 5} == doc["starts"]


def test_cli_refuses_without_real_and_on_bad_attestation(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("sandbox must never be called in tests")
    monkeypatch.setattr(vc.sandbox, "run_program", boom)
    with pytest.raises(SystemExit):
        vc.main(["--canaries", str(CANARIES), "--out", str(tmp_path / "o"), "--attestation", str(tmp_path / "a.json")])
    (tmp_path / "a.json").write_text(json.dumps({"schema_version": "landmark-containment-v1", "passed": False}))
    with pytest.raises(ValueError, match="attestation"):
        vc.main(["--canaries", str(CANARIES), "--out", str(tmp_path / "o"), "--attestation", str(tmp_path / "a.json"), "--real"])
    assert not (tmp_path / "o").exists()


ATT = {"schema_version": "landmark-containment-v1", "passed": True, "checked_at": "2026-09-21T00:00:00+00:00",
       "checks": [{"name": "c1", "passed": True, "payload_started": True}]}


def _att(tmp_path, monkeypatch):
    (tmp_path / "a.json").write_text(json.dumps(ATT))
    monkeypatch.setattr(vc.grade, "verify_attestation", lambda p: dict(ATT))
    monkeypatch.setattr(vc.sandbox, "run_program", lambda *a, **k: (_ for _ in ()).throw(AssertionError("real runner")))
    return tmp_path / "a.json"


def _records(out):
    return [json.loads(x) for x in (out / "ledger.jsonl").read_text().splitlines()]


def test_cli_real_with_fake_runner_writes_ledger_first_and_no_retries(tmp_path, monkeypatch):
    att = _att(tmp_path, monkeypatch)
    out = tmp_path / "o"
    seen = []
    def fake(program, **kw):
        compile(program, "<harness>", "exec")  # compile only; never executed
        recs = _records(out)
        seen.append(recs[-1]["record"] == "start" and (out / "ledger.json").exists())
        return {"stdout": "", "returncode": 1, "timed_out": False}
    fake.FAKE_RUNNER = True
    res = vc.run(CANARIES, out, att, True, runner=fake)
    assert all(seen) and res["actual_starts"] == len(seen) == 18 == res["planned_max_starts"]
    assert all(r["observed"][0] == {"status": "unavailable", "reason": "infrastructure_not_started"} for r in res["rows"])
    assert not res["all_within_acceptable"]
    recs = _records(out)
    assert [r["record"] for r in recs] == ["reserved"] + ["start", "runner_result", "result"] * 18 + ["complete"]
    reserved = recs[0]
    assert set(reserved["source_sha256"]) == set(vc.PROVENANCE_SOURCES) and all(len(v) == 64 for v in reserved["source_sha256"].values())
    assert reserved["attestation"]["verified_check_names"] == ["c1"] and len(reserved["attestation"]["sha256"]) == 64
    assert reserved["runner"]["fake_runner"] is True and len(reserved["runner"]["source_file_sha256"]) == 64
    assert set(reserved["decided_by"].values()) == {"payload"}
    with pytest.raises(SystemExit, match="overwrite"):
        vc.run(CANARIES, out, att, True, runner=fake)


def test_runner_exception_mid_run_leaves_incomplete_ledger(tmp_path, monkeypatch):
    att = _att(tmp_path, monkeypatch)
    out = tmp_path / "o"
    n = []
    def fake(program, **kw):
        n.append(1)
        return {"stdout": "", "returncode": 1, "timed_out": False}
    fake.FAKE_RUNNER = True
    def boom(*a, **k):
        if len(n) == 3:
            raise KeyboardInterrupt
        return orig(*a, **k)
    orig = vc.public_check.classify
    monkeypatch.setattr(vc.public_check, "classify", boom)
    with pytest.raises(KeyboardInterrupt):
        vc.run(CANARIES, out, att, True, runner=fake)
    recs = _records(out)
    assert [r["record"] for r in recs] == ["reserved"] + ["start", "runner_result", "result"] * 2 + ["start", "runner_result", "INCOMPLETE"]
    assert recs[-1]["actual_starts"] == 3 and recs[-1]["planned_max_starts"] == 18
    assert not (out / "result.json").exists() and (out / "ledger.json").exists()


def test_static_gate_canaries_expect_no_start(tmp_path, monkeypatch):
    doc, _ = vc.load_canaries(CANARIES)
    base = doc["canaries"][13]  # e5_wrong_value (payload path)
    fmt = dict(base, id="fmt", candidate_code="```python\nx=1\n```\n```python\ny=2\n```")
    assert vc.decided_by(fmt)[0] == "static_format_gate"
    integ = dict(base, id="integ", candidate_code="def f(x):\n    return eval('x')\n")
    path, flags = vc.decided_by(integ)
    if path == "static_integrity_gate":  # a payload expectation for a statically decided canary is refused
        bad = dict(doc, canaries=[dict(integ, static_gate_flags=flags)])
        (tmp_path / "c.json").write_text(json.dumps(bad))
        with pytest.raises(ValueError, match="static_integrity_gate"):
            vc.load_canaries(tmp_path / "c.json")
    wrong_flags = dict(doc, canaries=[dict(base, static_gate_flags=["x"])])
    (tmp_path / "w.json").write_text(json.dumps(wrong_flags))
    with pytest.raises(ValueError, match="static_gate_flags"):
        vc.load_canaries(tmp_path / "w.json")
    # every frozen v1 canary is decided by payload execution: hack_gate flags none, so planned max = 18 starts
    assert {vc.decided_by(c)[0] for c in doc["canaries"]} == {"payload"}
    assert all(c["static_gate_flags"] == [] for c in doc["canaries"])


def test_plan_doc_lists_e1_to_e10_not_run():
    text = (ROOT / "docs/e1_e10_validation_plan_20260921.md").read_text()
    assert "NOT RUN" in text and "separate lead authorization" in text
    for i in range(1, 11):
        assert re.search(rf"^\| E{i} \|", text, re.M)


def _fake_runner(program, **kw):
    return {"stdout": "", "returncode": 1, "timed_out": False}


_fake_runner.FAKE_RUNNER = True


def test_start_ledger_failure_ends_incomplete_not_swallowed(tmp_path, monkeypatch):
    # MRL-10 review: check_artifact converts wrapper exceptions to infrastructure_not_started; a failed durable
    # start write must not be swallowed nor counted as a start.
    att = _att(tmp_path, monkeypatch)
    out = tmp_path / "o"
    orig = vc.public_phase.Ledger.write
    def write(self, rec):
        if rec.get("record") == "start":
            raise OSError("disk full")
        return orig(self, rec)
    monkeypatch.setattr(vc.public_phase.Ledger, "write", write)
    with pytest.raises(OSError):
        vc.run(CANARIES, out, att, True, runner=_fake_runner)
    recs = _records(out)
    assert recs[-1]["record"] == "INCOMPLETE" and recs[-1]["actual_starts"] == 0
    assert not (out / "result.json").exists()


def test_provenance_includes_public_phase_and_raw_runner_results(tmp_path, monkeypatch):
    att = _att(tmp_path, monkeypatch)
    out = tmp_path / "o"
    vc.run(CANARIES, out, att, True, runner=_fake_runner)
    recs = _records(out)
    assert "experiments/landmark/public_phase.py" in recs[0]["source_sha256"]
    raw = [r for r in recs if r["record"] == "runner_result"]
    assert len(raw) == 18 and all(r["returncode"] == 1 and r["timed_out"] is False and len(r["stdout_sha256"]) == 64 for r in raw)


def test_attestation_changed_during_verification_refused(tmp_path, monkeypatch):
    att = _att(tmp_path, monkeypatch)
    def swap(p):
        Path(p).write_text("{}")
        return dict(ATT)
    monkeypatch.setattr(vc.grade, "verify_attestation", swap)
    with pytest.raises(SystemExit, match="changed during verification"):
        vc.run(CANARIES, tmp_path / "o", att, True, runner=_fake_runner)
    assert not (tmp_path / "o").exists()
