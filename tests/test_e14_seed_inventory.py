"""MRL-25 criterion 3: the seed inventory is built from every call log and is not vacuous. Static only."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import e14_seed_inventory as inv  # noqa: E402
import e14_connected_mock as cm  # noqa: E402

REC = json.loads((ROOT / "results/e14_seed_inventory_20260923.json").read_text())


def _committed_call_logs():
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"], capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("not a git checkout: the committed-file inventory claim cannot be evaluated")
    return {p for p in out.decode().split("\0") if p and Path(p).name in inv.LOG_NAMES}


def test_every_committed_call_log_is_covered():
    """LEAD-PORT-01: the claim is about COMMITTED call logs. REC is the original host-local inventory (19 logs:
    the 13 committed ones plus six ignored work/ logs on the worker host); it is kept as recorded, not rewritten."""
    committed = _committed_call_logs()
    covered = {s["path"] for s in REC["sources"]}
    assert committed and committed <= covered
    assert all(p.startswith("work/") for p in covered - committed)  # extras are host-local ignored logs only
    assert REC["complete"] is True and all(s["unparsed_lines"] == 0 for s in REC["sources"])


def test_lead_git_blob_inventory_is_a_separate_artifact_matching_committed_logs():
    lead = json.loads((ROOT / "results/e14_seed_inventory_lead_committed_20260923.json").read_text())
    assert {s["path"] for s in lead["sources"]} == _committed_call_logs()
    assert lead["n_committed_logs"] == 13 and len(REC["sources"]) == 19


def test_extractor_is_not_vacuous_positive_control(monkeypatch):
    """A zero can be an artifact of reading the wrong field; mbpp/842 WAS collected in E12 and E13a."""
    monkeypatch.setattr(inv, "E14_ROOTS", ["mbpp/842"])
    r = inv.build()["roots"]["mbpp/842"]
    assert len(r["labels"]) > 0 and len(r["numeric"]) == len(r["labels"])
    assert {"initial", "FRESH:0", "R1:2"} <= set(r["labels"])


def test_no_e14_root_has_recorded_prior_spend():
    assert REC["prior_spend_found_for_any_e14_root"] is False
    assert all(not v["labels"] and not v["numeric"] for v in REC["roots"].values())


def test_inventory_feeds_the_connected_plan_as_complete_with_no_collision():
    binding = cm.load_release(ROOT / "experiments/landmark/e14_release_v2",
                              ROOT / "docs/e14_lead_measurement_spec_20260923.json", cm.committed_manifest_sha256())
    slots, ev = cm.plan_slots(binding, {"complete": REC["complete"], "roots": REC["roots"]})
    assert len(slots) == 130 and ev["inventory_complete"] is True and ev["roots_without_inventory"] == []


def test_unscanned_sibling_logs_are_named_as_a_scope_limit():
    assert any("DTR-AgentEvals" in s and "NOT scanned" in s for s in REC["scope_limits"])
