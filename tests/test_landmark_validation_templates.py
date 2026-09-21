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


def test_cli_real_with_fake_runner_writes_ledger_first_and_no_retries(tmp_path, monkeypatch):
    monkeypatch.setattr(vc.grade, "verify_attestation", lambda p: {"checked_at": "2026-09-21T00:00:00+00:00"})
    monkeypatch.setattr(vc.sandbox, "run_program", lambda *a, **k: (_ for _ in ()).throw(AssertionError("real runner")))
    seen = []
    def fake(program, **kw):
        compile(program, "<harness>", "exec")  # compile only; never executed
        seen.append((tmp_path / "o" / "ledger.json").exists())
        return {"stdout": "", "returncode": 1, "timed_out": False}
    res = vc.run(CANARIES, tmp_path / "o", tmp_path / "a.json", True, runner=fake)
    assert all(seen) and res["actual_starts"] == len(seen) == 18
    assert all(r["observed"][0] == {"status": "unavailable", "reason": "infrastructure_not_started"} for r in res["rows"])
    assert not res["all_within_acceptable"]


def test_plan_doc_lists_e1_to_e10_not_run():
    text = (ROOT / "docs/e1_e10_validation_plan_20260921.md").read_text()
    assert "NOT RUN" in text and "separate lead authorization" in text
    for i in range(1, 11):
        assert re.search(rf"^\| E{i} \|", text, re.M)
