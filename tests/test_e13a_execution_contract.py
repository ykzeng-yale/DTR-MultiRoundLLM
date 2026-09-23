"""Static consistency audit of the E13a prospective execution contract (SOURCE ONLY evidence class).

Nothing here executes a receiver, grader, sandbox or network call: every check re-derives a number,
path or sha256 that docs/e13a_execution_contract_20260923.md asserts, directly from the committed
files, so a drifted document fails instead of silently misstating the caps that bound a future run.
Unknown/absent inputs are explicit skips-by-assertion, never zero-filled.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/e13a_execution_contract_20260923.md"
STAGE = ROOT / "experiments/landmark/e13a_stage.json"
PLAN = ROOT / "results/e13a_request_plan_20260922.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def text() -> str:
    assert DOC.exists(), f"contract missing: {DOC}"
    return DOC.read_text(encoding="utf-8")


# --------------------------------------------------------------- caps table (MRL-19 item 1)
CAP_STRINGS = (
    "**60**",          # receiver calls
    "**30,720**",      # reserved completion tokens
    "**At most 79**",  # total isolated executor starts
    "**600 s**",       # setup
    "**480 s**",       # collection
    "**300 s**",       # grading and analysis
    "**2,700 s / 45 min**",
    "**$0**",
)


@pytest.mark.parametrize("needle", CAP_STRINGS)
def test_cap_table_states_every_required_maximum(text, needle):
    assert needle in text, f"cap table does not state {needle}"


def test_starts_decompose_to_seventy_nine(text):
    assert "60 (#4) + 10 (#5) + 9 (#6)" in text
    # 79 must be labelled a maximum, not an expectation
    assert "explicitly a maximum, not an expected count" in text


def test_containment_check_count_matches_grader(text):
    from experiments.landmark import grade

    assert len(grade.REQUIRED_CHECKS) == 9
    for name in grade.REQUIRED_CHECKS:
        assert f"`{name}`" in text, f"REQUIRED_CHECKS name absent from contract: {name}"


def test_reserved_tokens_equal_calls_times_release_max_tokens():
    config = json.loads((ROOT / "experiments/landmark/dev_release_v3/config.json").read_bytes())
    assert config["max_tokens_per_call"] == 512
    assert 60 * config["max_tokens_per_call"] == 30_720


def test_plan_and_stage_report_seventy_grading_starts():
    """The 70 vs 79 reconciliation the contract makes must stay true of the real files."""
    plan = json.loads(PLAN.read_bytes())
    stage = json.loads(STAGE.read_bytes())
    assert plan["budget"]["receiver_calls"] == 60
    assert plan["budget"]["reserved_completion_tokens"] == 30_720
    assert plan["budget"]["isolated_starts"] == 70
    limits = stage["grading_limits"]
    assert limits["artifact_starts"] == 60
    assert limits["recheck_starts"] == 10
    assert limits["max_private_starts"] == 70 == limits["artifact_starts"] + limits["recheck_starts"]
    assert limits["grading_seconds"] == 300


def test_grading_limits_extension_is_additive_as_the_contract_claims(text):
    """Section 2 claims the limit validator was extended additively, not relaxed. Verify both halves."""
    from experiments.landmark import study_adapter as sa

    assert sa.GRADING_LIMIT_KEYS == {
        "n_roots", "artifact_starts", "recheck_starts", "max_private_starts", "grading_seconds"}
    assert sa.OPTIONAL_GRADING_LIMIT_KEYS == {"containment_starts"}
    assert sa.MAX_GRADING_SECONDS == 600 and sa.MAX_PRIVATE_STARTS == 200

    def limits(**lim):
        return sa.load_grading_limits(json.dumps({"grading_limits": lim}).encode())

    e13a = limits(n_roots=5, artifact_starts=60, recheck_starts=10, containment_starts=9,
                  max_private_starts=79, grading_seconds=300)
    assert e13a["max_private_starts"] == 79 == 60 + 10 + 9
    assert e13a["grading_seconds"] == e13a["seconds_cap"] == 300
    # the pre-existing rule still binds when containment_starts is absent (v3 releases unchanged)
    assert limits(n_roots=14, artifact_starts=154, recheck_starts=28,
                  max_private_starts=182, grading_seconds=600)["containment_starts"] == 0
    refusals = (
        dict(n_roots=5, artifact_starts=60, recheck_starts=10, max_private_starts=79, grading_seconds=300),
        dict(n_roots=5, artifact_starts=60, recheck_starts=10, containment_starts=9,
             max_private_starts=70, grading_seconds=300),
        dict(n_roots=5, artifact_starts=60, recheck_starts=10, containment_starts=9,
             max_private_starts=79, grading_seconds=601),
        dict(n_roots=5, artifact_starts=60, recheck_starts=10, containment_starts=9,
             max_private_starts=79, grading_seconds=300, public_starts=60),
        dict(artifact_starts=60, recheck_starts=10, containment_starts=9,
             max_private_starts=79, grading_seconds=300),
    )
    for bad in refusals:
        with pytest.raises(ValueError):
            limits(**bad)
    assert "extended **additively** for E13a, not relaxed" in text
    assert "`79 == 60 + 10 + 9`" in text


def test_release_manifest_limits_match_the_contract_table():
    from experiments.landmark import study_adapter as sa

    manifest = ROOT / "experiments/landmark/e13a_release/release_manifest.json"
    assert manifest.exists(), "e13a_release bindings are missing"
    # allowlisted with the SAME strict check as the older releases, not a new looser branch
    assert "experiments/landmark/e13a_release/release_manifest.json" in sa.COMMITTED_RELEASE_MANIFESTS
    limits = json.loads(manifest.read_bytes())["grading_limits"]
    assert limits == {"n_roots": 5, "artifact_starts": 60, "recheck_starts": 10,
                      "containment_starts": 9, "max_private_starts": 79, "grading_seconds": 300}


# --------------------------------------------------------------- one shared clock (MRL-19 item 2)
def test_shared_stage_clock_rules_are_stated(text):
    assert "### 2.1 One persisted stage start and deadline, shared by every phase" in text
    assert "`<run>/stage_clock.json`" in text
    assert "**Separate commands must not reset the outer cap.**" in text
    for api in ("from_start", "persist", "load", "remaining", "check", "CapExhausted"):
        assert api in text, f"StageClock API not named: {api}"


# --------------------------------------------------------------- commands (MRL-19 item 3)
def test_preflight_precedes_snapshot_diff(text):
    """The launcher's real order: preflight, then the diff of its saved output against the frozen snapshot."""
    body = text[text.index("### 5.1 Exact runnable command lines"):]
    pre = body.index("receiver_preflight_mrl10.py")
    diff = body.index("diff_receiver_snapshot_v31.py")
    assert pre < diff, "section 5.1 must order preflight BEFORE the snapshot diff"
    assert "**Step 3 — preflight, BEFORE the snapshot diff**" in text
    assert body.index("**Step 3 ") < body.index("**Step 4 ")
    # section 4's prose keeps the same order
    assert "**Run preflight before snapshot comparison.**" in text


@pytest.mark.parametrize("phase", ["Step 0", "Step 1", "Step 2", "Step 3", "Step 4", "Step 5", "Step 6", "Step 7"])
def test_every_phase_has_a_command_block(text, phase):
    assert f"**{phase} —" in text


def test_in_flight_drivers_are_named_without_a_stale_digest(text):
    """The three untracked drivers must be named, and deliberately carry no frozen digest yet."""
    for rel in ("scripts/e13a_stage_clock.py", "scripts/e13a_collect.py", "scripts/e13a_grade.py"):
        assert (ROOT / rel).exists(), f"driver missing: {rel}"
        assert rel in text, f"driver not named in the contract: {rel}"
        assert sha(ROOT / rel) not in text, f"{rel} carries an uncommitted digest that will decay"
    assert "records **no digest** for them" in text


def test_real_flags_exist_and_invented_ones_are_marked(text):
    """Flags quoted for committed scripts must be real; flags for absent scripts must be marked (D…)."""
    import argparse

    checks = {
        "scripts/check_landmark_sandbox.py": {"--runner", "--output"},
        "scripts/receiver_preflight_mrl10.py": {"--tasks", "--examples", "--base-url", "--out"},
        "scripts/diff_receiver_snapshot_v31.py": {"--new-preflight", "--out"},
        "scripts/launch_own_receiver_v31.py": {"--ownership", "--out"},
        "scripts/e13a_analyze.py": {"--grades", "--stage", "--out"},
        "scripts/e13a_stage_clock.py": {"--run-dir", "--init", "--start-utc", "--phase"},
        "scripts/e13a_collect.py": {"--out", "--stage", "--plan", "--release-dir", "--real",
                                    "--ownership", "--rebuild-only"},
        "scripts/e13a_grade.py": {"--collect", "--release", "--out", "--stage", "--plan", "--real",
                                  "--attestation", "--validate-only"},
    }
    for rel, quoted in checks.items():
        src = (ROOT / rel).read_text(encoding="utf-8")
        declared = set(re.findall(r'add_argument\(\s*"(--[a-z0-9-]+)"', src))
        declared |= {f for f in re.findall(r'"(--[a-z0-9-]+)"', src)}
        missing = quoted - declared
        assert not missing, f"{rel}: contract quotes flags that do not exist: {sorted(missing)}"
    # e13a_analyze.py really has no --clock, which is why the contract files it as dependency D5
    assert "--clock" not in (ROOT / "scripts/e13a_analyze.py").read_text(encoding="utf-8")
    assert "no** `--clock` flag" in text
    assert "| D6 |" in text and "| D5 |" in text
    for dep in ("| D1 |", "| D2 |", "| D3 |", "| D4 |", "| D7 |", "| D8 |"):
        assert dep in text


def test_pinned_hashes_match_the_real_files(text):
    """Every '| [label](path) | `sha` |' row in the pin tables must equal the file's actual digest."""
    rows = re.findall(r"^\|\s*\[[^\]]+\]\(([^)]+)\)\s*\|\s*`([0-9a-f]{64})`\s*\|$", text, re.M)
    assert len(rows) >= 18, f"expected the full pin table, found {len(rows)} rows"  # 17 lead+MRL-19 pins + release manifest
    for rel, claimed in rows:
        target = (DOC.parent / rel).resolve()
        assert target.exists(), f"pinned path does not exist: {rel}"
        assert sha(target) == claimed, f"pin drifted for {rel}: {sha(target)} != {claimed}"


def test_unlinked_pins_match_too(text):
    for rel, label in (("experiments/landmark/dev_release_v2/tasks.jsonl", "MRL-10 preflight fixture"),
                       ("docs/public_diagnostic_examples_v1.json", "Preflight public fixtures")):
        assert sha(ROOT / rel) in text, f"{label} digest missing or drifted for {rel}"
    assert sha(STAGE) in text and sha(PLAN) in text


def test_receiver_and_evaluator_pins_are_quoted(text):
    manifest = json.loads((ROOT / "experiments/landmark/dev_release_v3/release_manifest.json").read_bytes())
    assert manifest["model"]["model_digest"] in text
    assert manifest["model"]["server_build"] in text
    assert manifest["model"]["receiver_state_sha256_expected"] in text
    assert manifest["evaluator"]["grader_version"] in text
    assert manifest["evaluator"]["diagnostic_schema"] in text


# --------------------------------------------------------------- window rules (MRL-19 item 4)
def test_window_rules_separate_readiness_from_the_outer_deadline(text):
    assert "shared-window hard end minus 60 minutes**" in text
    assert "**separately and after** readiness" in text
    assert "September 24 07:10–08:20 placeholder is withdrawn**" in text
    assert "It was never a reservation" in text
    assert "earliest feasible mutually agreed window after source readiness" in text


def test_reported_peer_window_state_matches_the_committed_records(text):
    window = json.loads((ROOT / "docs/e12_shared_window_20260922T071000Z.json").read_bytes())
    assert window["start_utc"] == "2026-09-22T07:10:00Z" and window["hard_end_utc"] == "2026-09-22T08:20:00Z"
    for value in (window["start_utc"], window["hard_end_utc"], window["phase_a_latest_start_utc"]):
        assert value in text, f"window field not reported in contract: {value}"
    assert "there is no agreed E13a window anywhere" in text
    peer = Path("/Users/yukangzengcmac/DTR-AgentEvals")
    if peer.exists():  # read-only sibling; absence must not fabricate a window
        agreements = sorted(p.name for p in (peer / "results/v2_agent").glob("slot_agreement_*.json"))
        assert agreements == ["slot_agreement_20260922.json", "slot_agreement_20260922_0710.json"], (
            f"peer slot agreements changed: {agreements}; re-verify the contract's window section")
        assert "slot_agreement_20260922_0710.json" in text


# --------------------------------------------------------------- supplement and disposition (items 5, 6)
def test_supplement_is_separately_costed_and_excluded(text):
    assert "**This supplement is explicitly NOT part of the primary allowance of section 2.**" in text
    assert "at most 149 starts" in text
    assert "| Additional paid spend | $0 |" in text


def test_no_starts_released_and_dependency_is_the_executable_path(text):
    assert "**Nothing here releases a single start.**" in text
    assert "**Nothing here borrows the expired E12 allowance.**" in text
    assert "**The immediate dependency is the executable path, not owner permission.**" in text
    assert "**No guard was weakened to produce this contract.**" in text
    stage = json.loads(STAGE.read_bytes())
    assert stage["receiver_calls_authorized"] == 0
    assert stage["candidate_executions_authorized"] == 0


def test_e12_latency_figures_are_reproducible():
    """Section 2's measured per-call sums must still equal the immutable E12 ledgers."""
    run = ROOT / "results/e12_dev_v3_20260922T030255Z"
    sums = {}
    for phase in ("A", "C"):
        rows = [json.loads(line) for line in (run / phase / "calls.jsonl").read_text().splitlines() if line.strip()]
        seconds = [r["seconds"] for r in rows if r.get("seconds") is not None]
        assert len(seconds) == len(rows), f"{phase}: a call has no recorded seconds; do not zero-fill"
        sums[phase] = round(sum(seconds), 6)
    assert sums == {"A": 14.977224, "C": 295.594775}
    doc = DOC.read_text(encoding="utf-8")
    assert "14.977224" in doc and "295.594775" in doc
