"""MRL-08: study adapter (diagnostic-v1 phases -> private grading view -> analyze_diagnostic input).
Fake receiver and FAKE grading runner only; no sandbox, no model, no generated code is executed."""
import json, re, sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_landmark_collect_diagnostic import Fake, TASKS, dm, make_config, run_both  # noqa: E402,F401
from experiments.landmark import study_adapter as sa  # noqa: E402
from experiments.landmark import analyze_diagnostic as ad  # noqa: E402
from experiments.landmark import grade  # noqa: E402


def specs(roots):
    return [{"root_id": r, "public_task_sha256": "0" * 64, "entry_point": "f", "public_assertions": [],
             "private_assertions": ["assert f(1) == 2"], "preamble": [], "reference_code": "def f(x):\n    return x + 1",
             "negative_controls": [{"code": "def f(x):\n    return x"}]} for r in roots]


class FakeRunner:
    """Never executes: passes iff the program text contains `return x + 1` as a whole line."""
    def __init__(self): self.programs = []

    def __call__(self, program, timeout_s, cpu_seconds, output_cap):
        compile(program, "<fake>", "exec")  # parse only, never exec
        self.programs.append(program)
        start = re.search(grade.STARTED + r"[0-9a-f]{24}", program).group(0)
        sentinel = re.search(r"__LANDMARK_PRIVATE_OK__[0-9a-f]{24}", program).group(0)
        ok = re.search(r"^\s*return x \+ 1$", program, flags=re.M) is not None
        return {"stdout": start + "\n" + (sentinel + "\n" if ok else ""), "stdout_tail": sentinel if ok else "AssertionError",
                "timed_out": False, "returncode": 0 if ok else 1, "sandbox_kind": "seatbelt", "passed": ok,
                "executed": True, "seconds": 0.01}


def build(tmp_path, dm, continue_adapter=None):
    run_both(tmp_path, dm, continue_adapter=continue_adapter)
    return sa.to_grading_view(tmp_path / "A", tmp_path / "C", tmp_path / "V")


def diags(tmp_path):
    return json.loads((tmp_path / "diag.json").read_text())


def test_view_layout_and_bindings(tmp_path, dm):
    view = build(tmp_path, dm)
    assert len(view) == 7 and all(set(r["arms"]) == set(sa.STUDY_ARMS) for r in view)
    for r in view:
        assert len(r["arms"]["STOP"]) == 1 and all(len(r["arms"][a]) == 2 for a in sa.CONTINUATION_ARMS)
        a = json.loads([x for x in (tmp_path / "A/roots.jsonl").read_text().splitlines() if json.loads(x)["root_id"] == r["root_id"]][0])
        assert r["initial_artifact_sha256"] == a["artifact_sha256"]
        assert r["arms"]["STOP"][0]["output"].encode("utf-8") == (tmp_path / "A" / a["artifact"]).read_bytes()
        for recs in r["arms"].values():
            for x in recs:
                assert x["output_sha256"] == grade.digest(x["output"])
    assert sa.load_view(tmp_path / "V") == view
    assert json.loads((tmp_path / "V/view_manifest.json").read_text())["grade_py_blockers"] == list(sa.GRADE_PY_BLOCKERS)


def test_tampered_initial_artifact_rejected(tmp_path, dm):
    run_both(tmp_path, dm)
    art = sorted((tmp_path / "A/artifacts").iterdir())[0]
    art.write_bytes(art.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="artifact bytes"):
        sa.to_grading_view(tmp_path / "A", tmp_path / "C", tmp_path / "V")


def test_grade_py_collection_path_is_blocked_by_its_own_checks(tmp_path, dm):
    build(tmp_path, dm)
    with pytest.raises((ValueError, KeyError, FileNotFoundError)):
        grade.grade_collection(tmp_path / "V", specs([t["root_id"] for t in TASKS]), tmp_path / "G", _runner=FakeRunner())


def test_grade_study_fake_runner_and_analysis_round_trip(tmp_path, dm):
    view = build(tmp_path, dm)
    runner = FakeRunner()
    result = sa.grade_study(tmp_path / "V", specs([t["root_id"] for t in TASKS]), runner, fake_runner_for_tests=True)
    assert result["model_calls"] == 0 and result["sandbox_executions"] == len(runner.programs)
    assert len(result["grades"]) == 7 * 11 and result["missing_grade_rows"] == 0
    # reference + one control per root, then one candidate per distinct output
    kinds = [e["kind"] for e in result["executions"]]
    assert kinds.count("reference") == 7 and kinds.count("negative_control") == 7
    stop = {g["root_id"]: g["outcome"] for g in result["grades"] if g["arm"] == "STOP"}
    assert stop["root0"] == 1 and sum(stop.values()) == 1  # initial Fake outputs x+1..x+7 in root order
    inp = sa.to_analysis_input(view, result["grades"], diags(tmp_path))
    assert inp["missing_grades"] == {}
    report = ad.analyze(inp["roots"], inp["diagnostics"], replicates=2)
    assert report is not None
    json.dumps(report)


def test_missing_grade_stays_none_and_counted(tmp_path, dm):
    view = build(tmp_path, dm, continue_adapter=Fake(fail_every=4))
    ids = [t["root_id"] for t in TASKS]
    result = sa.grade_study(view, specs(ids[:-1]), FakeRunner(), fake_runner_for_tests=True)  # last root has no private spec
    unavailable = sum(x["output"] is None for r in view for recs in r["arms"].values() for x in recs)
    assert unavailable > 0
    grades = [g for g in result["grades"] if not (g["root_id"] == "root1" and g["arm"] == "S1" and g["replicate"] == 0)]
    inp = sa.to_analysis_input(view, grades, diags(tmp_path))
    rec = inp["roots"][1]["arms"]["S1"][0]
    assert rec["grade"] is None and rec["missing_reason"] == "grade_row_missing"
    assert inp["missing_grades"]["grade_row_missing"] == 1
    assert inp["missing_grades"]["private_spec_missing"] >= 1
    assert sum(inp["missing_grades"].values()) == sum(
        x["grade"] is None for r in inp["roots"] for recs in r["arms"].values() for x in recs)
    assert all(g["missing_reason"] for g in grades if g["outcome"] is None)
    ad.analyze(inp["roots"], inp["diagnostics"], replicates=2)


def test_runner_required_and_unassigned_grade_rejected(tmp_path, dm):
    view = build(tmp_path, dm)
    with pytest.raises(ValueError, match="runner"):
        sa.grade_study(view, specs(["root0"]), None)
    bogus = [{"root_id": "root0", "arm": "N0", "replicate": 9, "output_sha256": None, "outcome": None, "missing_reason": "x"}]
    with pytest.raises(ValueError, match="unassigned"):
        sa.to_analysis_input(view, bogus, {})


def test_real_grading_requires_a_containment_attestation():
    """MRL-08: the study grader keeps grade.py's containment gate; only a declared fake runner skips it."""
    with pytest.raises(ValueError, match="Containment attestation required"):
        sa.grade_study([], {}, lambda *a, **k: None)
