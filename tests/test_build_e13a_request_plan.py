"""E13a request plan: binds to E12's immutable artifacts; no receiver, model or candidate is executed."""
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_e13a_request_plan as b  # noqa: E402


def test_plan_shape_seeds_and_budget():
    p = b.build()
    assert [r["root_id"] for r in p["roots"]] == ["mbpp/842", "mbpp/288", "mbpp/863", "mbpp/966", "mbpp/652"]
    for r in p["roots"]:
        keys = [q["seed_key"] for q in r["requests"]]
        assert keys == [f"R1:{i}" for i in range(2, 8)] + [f"FRESH:{i}" for i in range(6)]
        assert len({q["seed"] for q in r["requests"]}) == 12
        assert {q["messages_sha256"] for q in r["requests"] if q["arm"] == "FRESH"} == {r["base_messages_sha256"]}
        assert {q["messages_sha256"] for q in r["requests"] if q["arm"] == "R1"} == {r["r1_messages_sha256"]}
    bud = p["budget"]
    assert (bud["receiver_calls"], bud["reserved_completion_tokens"], bud["isolated_starts"]) == (60, 30720, 70)
    assert bud["cumulative_ledger_if_granted"] == 403 and bud["ledger_ceiling"] == 412
    assert "not authority" in bud["ledger_note"]


def test_checkpoints_come_from_public_diagnostics_and_no_private_grade_leaks():
    """MRL-18: gate from frozen public diagnostics only; no private grade in the executable input."""
    p = b.build()
    blob = json.dumps(p)
    assert "private_grade" not in blob and "analysis_report" not in blob
    for r in p["roots"]:
        assert r["public_status"] == "any_fail"
        assert r["public_case_statuses"] and all(
            s in ("wrong_value", "format_error", "interface_error", "program_exception") for s in r["public_case_statuses"])
    assert any("public_status" in c for c in p["checks"])
    assert "tie is inconclusive" in p["evidence_class"]


def test_committed_plan_matches_rebuild():
    committed = json.loads((ROOT / "results/e13a_request_plan_20260922.json").read_text())
    assert committed == json.loads(json.dumps(b.build()))


def test_tampered_e12_record_is_refused(tmp_path):
    run = tmp_path / "run"
    shutil.copytree(b.RUN, run)
    calls = run / "C/calls.jsonl"
    calls.write_text(calls.read_text().replace('"arm": "R1"', '"arm": "R1" ', 1))
    with pytest.raises(ValueError, match="C/calls.jsonl"):
        b.build(run=run)


def test_refuses_to_overwrite(tmp_path):
    out = tmp_path / "x.json"
    out.write_text("{}")
    with pytest.raises(SystemExit):
        b.main(["--out", str(out)])
