"""MRL-08: study adapter (diagnostic-v1 phases -> private grading view -> analyze_diagnostic input).
Fake receiver and FAKE grading runner only; no sandbox, no model, no generated code is executed."""
import hashlib, json, re, sys
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
    by = {t["root_id"]: t for t in TASKS}
    return [{"root_id": r, "public_task_sha256": grade.digest(by[r]), "entry_point": "f", "public_assertions": [],
             "private_assertions": ["assert f(5) == 6"], "preamble": [], "reference_code": "def f(x):\n    return x + 1",
             "negative_controls": [{"code": "def f(x):\n    return x", "rationale": "identity is off by one"}]} for r in roots]


ALL = [t["root_id"] for t in TASKS]


@pytest.fixture(autouse=True)
def strict_loads(monkeypatch):
    """Until the 'strict' agent lands diagnostic.strict_json_loads, supply an equivalent (duplicate keys refused)."""
    from experiments.landmark import diagnostic
    if not hasattr(diagnostic, "strict_json_loads"):
        def loads(data):
            def hook(pairs):
                keys = [k for k, _ in pairs]
                if len(keys) != len(set(keys)):
                    raise ValueError("duplicate key")
                return dict(pairs)
            return json.loads(data, object_pairs_hook=hook)
        monkeypatch.setattr(diagnostic, "strict_json_loads", loads, raising=False)


def frozen(tmp_path, spec_list=None):
    path = tmp_path / "tasks.jsonl"
    path.write_text("".join(json.dumps(t) + "\n" for t in TASKS))
    return {"frozen_tasks_path": path, "frozen_tasks_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "expected_contract_sha256": grade.digest(grade.contract(spec_list or specs(ALL))),
            "initial_dir": tmp_path / "A", "continue_dir": tmp_path / "C",
            "expected_source_hashes": sa.grading_source_hashes(), "fake_runner_for_tests": True,
            "expected_config_sha256": sa.digest(make_config())}


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
    result = sa.grade_study(tmp_path / "V", specs(ALL), runner, **frozen(tmp_path))
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
    result = sa.grade_study(view, specs(ALL), FakeRunner(), **frozen(tmp_path))
    unavailable = sum(x["output"] is None for r in view for recs in r["arms"].values() for x in recs)
    assert unavailable > 0
    grades = [g for g in result["grades"] if not (g["root_id"] == "root1" and g["arm"] == "S1" and g["replicate"] == 0)]
    inp = sa.to_analysis_input(view, grades, diags(tmp_path))
    rec = inp["roots"][1]["arms"]["S1"][0]
    assert rec["grade"] is None and rec["missing_reason"] == "grade_row_missing"
    assert inp["missing_grades"]["grade_row_missing"] == 1
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


def test_specs_must_validate_against_frozen_public_tasks(tmp_path, dm):
    view = build(tmp_path, dm)
    with pytest.raises(ValueError, match="exactly the declared public roots"):  # partial specs now refused
        sa.grade_study(view, specs(ALL[:-1]), FakeRunner(), **frozen(tmp_path))
    bad = specs(ALL)
    bad[0]["public_task_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="does not bind the public task"):
        sa.grade_study(view, bad, FakeRunner(), **frozen(tmp_path, bad))


def test_frozen_tasks_bytes_verified_before_use(tmp_path, dm):
    view = build(tmp_path, dm)
    kw = frozen(tmp_path)
    kw["frozen_tasks_path"].write_text(kw["frozen_tasks_path"].read_text() + "\n")
    with pytest.raises(ValueError, match="Frozen public tasks bytes"):
        sa.grade_study(view, specs(ALL), FakeRunner(), **kw)


def test_contract_digest_must_match_frozen(tmp_path, dm):
    view = build(tmp_path, dm)
    runner = FakeRunner()
    with pytest.raises(ValueError, match="contract digest"):
        sa.grade_study(view, specs(ALL), runner, **{**frozen(tmp_path), "expected_contract_sha256": "f" * 64})
    assert runner.programs == []


@pytest.mark.parametrize("missing", ["frozen_tasks_path", "expected_contract_sha256", "initial_dir", "expected_source_hashes",
                                     "expected_config_sha256"])
def test_protection_arguments_required_on_fake_path(tmp_path, dm, missing):
    view = build(tmp_path, dm)
    with pytest.raises(ValueError, match="required"):
        sa.grade_study(view, specs(ALL), FakeRunner(), **{**frozen(tmp_path), missing: None})


def test_source_hashes_verified(tmp_path, dm):
    view = build(tmp_path, dm)
    current = sa.grading_source_hashes()
    assert set(current) == set(sa.GRADING_SOURCES) and "experiments/landmark/analyze.py" in current
    wrong = {**current, "experiments/landmark/grade.py": "0" * 64}
    with pytest.raises(ValueError, match="source hash mismatch"):
        sa.grade_study(view, specs(ALL), FakeRunner(), **{**frozen(tmp_path), "expected_source_hashes": wrong})
    partial = {k: v for k, v in current.items() if not k.endswith("sandbox.py")}
    with pytest.raises(ValueError, match="cover exactly"):
        sa.grade_study(view, specs(ALL), FakeRunner(), **{**frozen(tmp_path), "expected_source_hashes": partial})


def test_phase_completion_checksums_recomputed(tmp_path, dm):
    view = build(tmp_path, dm)
    p = tmp_path / "C/calls.jsonl"
    p.write_text(p.read_text() + "\n")
    with pytest.raises(ValueError, match="checksum mismatch"):
        sa.grade_study(view, specs(ALL), FakeRunner(), **frozen(tmp_path))


def test_phase_completion_duplicate_key_refused(tmp_path, dm):
    view = build(tmp_path, dm)
    p = tmp_path / "A/completion.json"
    p.write_text(p.read_text().replace("{", '{"phase": "x",', 1))
    with pytest.raises(ValueError):
        sa.grade_study(view, specs(ALL), FakeRunner(), **frozen(tmp_path))


def test_exact_assignment_coverage(tmp_path, dm):
    view = build(tmp_path, dm)
    kw = frozen(tmp_path)
    missing = json.loads(json.dumps(view)); missing[0]["arms"]["N1"].pop()
    with pytest.raises(ValueError, match="coverage mismatch"):
        sa.grade_study(missing, specs(ALL), FakeRunner(), **kw)
    extra = json.loads(json.dumps(view)); extra[0]["arms"]["STOP"].append({**extra[0]["arms"]["STOP"][0], "replicate": 1})
    with pytest.raises(ValueError, match="coverage mismatch"):
        sa.grade_study(extra, specs(ALL), FakeRunner(), **kw)
    dup = json.loads(json.dumps(view)); dup[0]["arms"]["S0"].append(dict(dup[0]["arms"]["S0"][0]))
    with pytest.raises(ValueError, match="Duplicate assignment"):
        sa.grade_study(dup, specs(ALL), FakeRunner(), **kw)
    fam = json.loads(json.dumps(view)); fam[0]["family_id"] = "other"
    with pytest.raises(ValueError, match="coverage mismatch"):
        sa.grade_study(fam, specs(ALL), FakeRunner(), **kw)
    dropped = json.loads(json.dumps(view))[1:]
    with pytest.raises(ValueError, match="roots or exclusions"):
        sa.grade_study(dropped, specs(ALL), FakeRunner(), **kw)


def test_view_must_equal_rebuilt_view(tmp_path, dm):
    view = build(tmp_path, dm)
    swapped = json.loads(json.dumps(view))
    swapped[0]["arms"]["N0"][0]["missing_reason"] = "edited"
    with pytest.raises(ValueError, match="rebuilt"):
        sa.grade_study(swapped, specs(ALL), FakeRunner(), **frozen(tmp_path))


def test_no_stale_no_gate_prose():
    assert "no containment attestation gate" not in (ROOT / "experiments/landmark/study_adapter.py").read_text()


# ---- MRL-09 fixer regressions (J7 frozen config, strict parsing, replicate type, artifact containment) ----
def _resum(d, rel):
    c = json.loads((d / "completion.json").read_text())
    c["checksums"][rel] = hashlib.sha256((d / rel).read_bytes()).hexdigest()
    (d / "completion.json").write_text(json.dumps(c, indent=2) + "\n")


@pytest.mark.parametrize("over", [{"prior_seen_root_ids": []}, {"branch_replicates": 1, "max_calls": 42}])
def test_plan_derived_only_from_frozen_config(tmp_path, dm, over):
    frozen_cfg = make_config(prior_seen_root_ids=["root0"])
    run_both(tmp_path, dm, cfg=make_config(**{"prior_seen_root_ids": ["root0"], **over}))
    rows = sa.build_view(tmp_path / "A", tmp_path / "C")
    runner = FakeRunner()
    with pytest.raises(ValueError, match="frozen config digest"):
        sa.grade_study(rows, specs(ALL), runner, **{**frozen(tmp_path), "expected_config_sha256": sa.digest(frozen_cfg)})
    assert runner.programs == []


def test_roots_jsonl_duplicate_key_refused(tmp_path, dm):
    run_both(tmp_path, dm)
    C = tmp_path / "C"
    lines = (C / "roots.jsonl").read_text().splitlines()
    lines[0] = '{"root_id": "decoy", "excluded": true, ' + lines[0][1:]
    (C / "roots.jsonl").write_text("\n".join(lines) + "\n")
    _resum(C, "roots.jsonl")
    with pytest.raises(ValueError):
        sa.build_view(tmp_path / "A", C)


def test_view_manifest_duplicate_key_refused(tmp_path, dm):
    build(tmp_path, dm)
    V = tmp_path / "V"
    text = (V / "view_manifest.json").read_text()
    (V / "view_manifest.json").write_text(text.replace('{', '{"roots_sha256": "0", ', 1))
    with pytest.raises(ValueError):
        sa.load_view(V)


def test_replicate_must_be_int(tmp_path, dm):
    run_both(tmp_path, dm)
    C = tmp_path / "C"
    rows0 = [json.loads(x) for x in (C / "roots.jsonl").read_text().splitlines()]
    r = next(r for r in rows0 if not r["excluded"])
    for rec in r["arms"]["N0"]:
        if rec["replicate"] == 1:
            rec["replicate"] = True
    (C / "roots.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows0))
    _resum(C, "roots.jsonl")
    rows = sa.build_view(tmp_path / "A", C)
    runner = FakeRunner()
    with pytest.raises(ValueError, match="Replicate must be an int"):
        sa.grade_study(rows, specs(ALL), runner, **frozen(tmp_path))
    assert runner.programs == []


def test_initial_artifact_must_be_checksummed_inside_phase_dir(tmp_path, dm):
    run_both(tmp_path, dm)
    A = tmp_path / "A"
    rows0 = [json.loads(x) for x in (A / "roots.jsonl").read_text().splitlines()]
    r = next(r for r in rows0 if r.get("artifact"))
    outside = tmp_path / "elsewhere.txt"
    outside.write_bytes((A / r["artifact"]).read_bytes())
    c = json.loads((A / "completion.json").read_text())
    del c["checksums"][r["artifact"]]
    (A / r["artifact"]).unlink()
    r["artifact"] = str(outside)
    (A / "roots.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows0))
    c["checksums"]["roots.jsonl"] = hashlib.sha256((A / "roots.jsonl").read_bytes()).hexdigest()
    (A / "completion.json").write_text(json.dumps(c, indent=2) + "\n")
    with pytest.raises(ValueError, match="checksummed"):
        sa.build_view(A, tmp_path / "C")
    (A / "stray.json").write_text("{}")
    with pytest.raises(ValueError, match="exactly the phase files"):
        sa.verify_phase_dir(A)
