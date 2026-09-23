"""MRL-12: complete A-E mock orchestration (fakes only). Phase A fake receiver -> Phase B FAKE_RUNNER ->
Phase C bound to Phase B's diagnostics sha -> study_adapter CLI grade (sandbox.run_program monkeypatched to a
parse-only FAKE; attestation verification faked) -> analysis-input CLI -> analyze_diagnostic.analyze.
No model, receiver, reference, candidate, canary or sandbox program is ever executed."""
import hashlib, importlib.util, inspect, json, re, sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.landmark import study_adapter as sa, public_phase as pp, grade, sandbox, diagnostic  # noqa: E402
from experiments.landmark import analyze_diagnostic as ad  # noqa: E402


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


tpp = _load("_e11_public_phase_helpers", "test_landmark_public_phase.py")
cd, SPEC, TASKS, EXAMPLES = tpp.cd, tpp.SPEC, tpp.TASKS, tpp.EXAMPLES
FAILED = 1  # this root's initial receiver call fails -> initial_failed, no artifact


class Receiver(tpp.Receiver):
    def generate(self, payload, timeout):
        if len(self.payloads) == FAILED:
            self.payloads.append(payload)
            raise ConnectionError("receiver dropped the request")
        return super().generate(payload, timeout)


class GradeRunner:
    """Parse-only FAKE for sandbox.run_program: passes iff a line is exactly `return x + 1`."""
    def __init__(self, raise_at=None):
        self.programs, self.raise_at = [], raise_at

    def __call__(self, program, timeout_s, cpu_seconds, output_cap):
        compile(program, "<fake>", "exec")  # never executed
        if self.raise_at is not None and len(self.programs) == self.raise_at:
            raise RuntimeError("sandbox host lost mid-grading")
        self.programs.append(program)
        start = re.search(grade.STARTED + r"[0-9a-f]{24}", program).group(0)
        sentinel = re.search(r"__LANDMARK_PRIVATE_OK__[0-9a-f]{24}", program).group(0)
        ok = re.search(r"^\s*return x \+ 1$", program, flags=re.M) is not None
        return {"stdout": start + "\n" + (sentinel + "\n" if ok else ""), "stdout_tail": sentinel if ok else "AssertionError",
                "timed_out": False, "returncode": 0 if ok else 1, "sandbox_kind": "seatbelt", "passed": ok,
                "executed": True, "seconds": 0.01}


def specs():
    by = {t["root_id"]: t for t in TASKS}
    out = []
    for c in SPEC:
        ep = c["entry_point"]
        out.append({"root_id": c["root_id"], "public_task_sha256": grade.digest(by[c["root_id"]]), "entry_point": ep,
                    "public_assertions": [], "private_assertions": [f"assert {ep}(987654) == 987655"], "preamble": [],
                    "reference_code": f"def {ep}(x):\n    return x + 1",
                    "negative_controls": [{"code": f"def {ep}(x):\n    return x", "rationale": "identity is off by one"}]})
    return out


@pytest.fixture(autouse=True)
def no_real_execution(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("sandbox.run_program must never run in MRL-12 tests")
    monkeypatch.setattr(sandbox, "run_program", refuse)


def write_release(tmp_path, **binding_override):
    rel = tmp_path / "R"
    rel.mkdir()
    (rel / "tasks.jsonl").write_text("".join(json.dumps(t) + "\n" for t in TASKS))
    (rel / "private_specs.jsonl").write_text("".join(json.dumps(s) + "\n" for s in specs()))
    (rel / "config.json").write_text(json.dumps(tpp.config()))
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    bindings = {"frozen_tasks_path": str(rel / "tasks.jsonl"), "frozen_tasks_sha256": sha(rel / "tasks.jsonl"),
                "expected_contract_sha256": grade.digest(grade.contract(specs())),
                "expected_config_sha256": sa.digest(tpp.config()), "expected_source_hashes": sa.grading_source_hashes()}
    for k, v in binding_override.items():
        if v is None:
            bindings.pop(k)
        else:
            bindings[k] = v
    manifest = {"package": {n: sha(rel / n) for n in sa.PACKAGE_FILES}, "grading_bindings": bindings}
    (rel / "release_manifest.json").write_text(json.dumps(manifest))
    return rel


@pytest.fixture
def phases(tmp_path):
    cfg = tpp.config()
    cd.run_initial(cfg, TASKS, tmp_path / "A", adapter=Receiver())
    gen = iter(f"{i:032x}" for i in range(100))
    runner = tpp.Runner()
    m = pp.run_phase_b(tmp_path / "A", EXAMPLES, tmp_path / "B", runner, nonce_factory=lambda: next(gen))
    cd.run_continue(cfg, TASKS, tmp_path / "A", tmp_path / "B/diagnostics.json", tmp_path / "C",
                    expected_diagnostics_sha256=m["diagnostics_sha256"], adapter=tpp.tcd.Fake(),
                    public_examples={c["root_id"]: c for c in SPEC})
    (tmp_path / "att.json").write_text("{}")
    return m


def grade_argv(tmp_path, rel, out="G", real=True):
    argv = ["grade", "--release-manifest", str(rel / "release_manifest.json"), "--specs", str(rel / "private_specs.jsonl"),
            "--initial-dir", str(tmp_path / "A"), "--continue-dir", str(tmp_path / "C"), "--out", str(tmp_path / out),
            "--attestation", str(tmp_path / "att.json")]
    return argv + (["--real"] if real else [])


def fake_real(monkeypatch, runner):
    monkeypatch.setattr(sandbox, "run_program", runner)
    monkeypatch.setattr(grade, "verify_attestation", lambda path: {"passed": True})
    monkeypatch.setattr(sa, "verify_committed_release", lambda path, data=None: "c" * 64)  # tmp release; the gate is tested below


def events(path):
    return [json.loads(x) for x in path.read_text().splitlines()]


def test_complete_a_to_e_cli(tmp_path, phases, monkeypatch):
    rel = write_release(tmp_path)
    runner = GradeRunner()
    fake_real(monkeypatch, runner)
    summary = sa.main(grade_argv(tmp_path, rel))
    assert summary["actual_starts"] >= 2, summary
    assert summary["actual_starts"] == len(runner.programs) == summary["actual_results"] <= summary["planned_max_starts"] == 101
    ev = events(tmp_path / "G" / sa.GRADING_LEDGER)
    assert ev[0]["event"] == "reserved" and ev[-1]["event"] == "complete"
    kinds = [e["event"] for e in ev]
    assert kinds.count("start") == kinds.count("result") == len(runner.programs)
    for i, e in enumerate(ev):  # every start is immediately followed by its result record
        if e["event"] == "start":
            assert ev[i + 1]["event"] == "result" and ev[i + 1]["n"] == e["n"] and ev[i + 1]["elapsed_seconds"] >= 0
    # Phase B cost contract: executor_seconds is carried when present; null stays null (never 0).
    bman = json.loads((tmp_path / "B/manifest.json").read_text())
    failed_root = SPEC[FAILED]["root_id"]
    assert failed_root not in {r["root_id"] for r in bman["roots"]}
    h = phases["diagnostics_sha256"]
    data = sa.main(["analysis-input", "--view", str(tmp_path / "G/view"), "--grades", str(tmp_path / "G/grades.jsonl"),
                    "--phase-b-dir", str(tmp_path / "B"), "--expected-diagnostics-sha256", h, "--out", str(tmp_path / "in.json")])
    roots = {r["root_id"]: r for r in data["roots"]}
    for r in bman["roots"]:
        c = roots[r["root_id"]]["diagnostic_cost"]
        assert c["executor_starts"] == r["runner_invocations"]
        assert c["executor_seconds"] == r.get("executor_seconds")  # None when not measured
    # initial_failed must flow through as MISSING (never graded 0) -- asserted unconditionally, not skipped.
    assert failed_root in roots, "the initial_failed root vanished from the analysis input"
    assert roots[failed_root]["diagnostic_cost"] == {"executor_starts": 0, "executor_seconds": 0.0}
    assert all(x["grade"] is None and x["missing_reason"] for x in roots[failed_root]["arms"]["STOP"])
    report = ad.analyze(data["roots"], data["diagnostics"], replicates=2)
    json.dumps(report)
    with pytest.raises(SystemExit, match="exists"):  # refuse overwrite
        sa.main(grade_argv(tmp_path, rel))


def test_null_executor_seconds_stays_null(tmp_path, phases):
    man = json.loads((tmp_path / "B/manifest.json").read_text())
    for r in man["roots"]:
        r["executor_seconds"] = None
    man["roots"][0]["executor_seconds"] = 1.5
    (tmp_path / "B/manifest.json").write_text(json.dumps(man))
    _, costs = sa.phase_b_costs(tmp_path / "B", phases["diagnostics_sha256"])
    first = man["roots"][0]["root_id"]
    assert costs[first]["executor_seconds"] == 1.5
    assert all(v["executor_seconds"] is None for k, v in costs.items() if k != first)


def test_diagnostics_hash_mismatch_refused(tmp_path, phases, monkeypatch):
    rel = write_release(tmp_path)
    fake_real(monkeypatch, GradeRunner())
    sa.main(grade_argv(tmp_path, rel))
    with pytest.raises(ValueError, match="diagnostics"):
        sa.main(["analysis-input", "--view", str(tmp_path / "G/view"), "--grades", str(tmp_path / "G/grades.jsonl"),
                 "--phase-b-dir", str(tmp_path / "B"), "--expected-diagnostics-sha256", "0" * 64,
                 "--out", str(tmp_path / "in.json")])
    assert not (tmp_path / "in.json").exists()


def test_interrupted_grading_leaves_incomplete_and_ledger(tmp_path, phases, monkeypatch):
    rel = write_release(tmp_path)
    fake_real(monkeypatch, GradeRunner(raise_at=1))
    with pytest.raises(sa.GradingInterrupted):
        sa.main(grade_argv(tmp_path, rel))
    assert (tmp_path / "G/INCOMPLETE").exists() and not (tmp_path / "G/summary.json").exists()
    ev = events(tmp_path / "G" / sa.GRADING_LEDGER)
    kinds = [e["event"] for e in ev]
    assert kinds.count("start") == 2 and kinds.count("result") == 2 and kinds[-1] == "incomplete"
    assert "runner_error" in [e for e in ev if e["event"] == "result"][-1]
    with pytest.raises(SystemExit, match="exists"):  # no rerun into the charged directory
        sa.main(grade_argv(tmp_path, rel))


@pytest.mark.parametrize("override", [{"expected_contract_sha256": None}, {"expected_source_hashes": None},
                                      {"expected_config_sha256": "UNRESOLVED: pending freeze"},
                                      {"frozen_tasks_sha256": "0" * 64}, {"expected_contract_sha256": "0" * 64}])
def test_missing_unresolved_or_mismatched_binding_refused(tmp_path, phases, monkeypatch, override):
    rel = write_release(tmp_path, **override)
    runner = GradeRunner()
    fake_real(monkeypatch, runner)
    with pytest.raises((SystemExit, ValueError)):
        sa.main(grade_argv(tmp_path, rel))
    assert runner.programs == []


def test_refusals_before_any_start(tmp_path, phases, monkeypatch):
    rel = write_release(tmp_path)
    with pytest.raises(SystemExit, match="--real"):
        sa.main(grade_argv(tmp_path, rel, real=False))
    with pytest.raises(SystemExit, match="attestation"):  # real verify_attestation refuses the fake file FIRST
        sa.main(grade_argv(tmp_path, rel))
    assert not (tmp_path / "G").exists()
    fake_real(monkeypatch, GradeRunner())
    (rel / "private_specs.jsonl").write_text((rel / "private_specs.jsonl").read_text() + "\n")
    with pytest.raises(SystemExit, match="release bindings"):
        sa.main(grade_argv(tmp_path, rel))
    assert not (tmp_path / "G").exists()


def _analysis_argv(tmp_path, h, bdir="B"):
    return ["analysis-input", "--view", str(tmp_path / "G/view"), "--grades", str(tmp_path / "G/grades.jsonl"),
            "--phase-b-dir", str(tmp_path / bdir), "--expected-diagnostics-sha256", h, "--out", str(tmp_path / "in.json")]


def test_unrelated_phase_b_dir_refused(tmp_path, phases, monkeypatch):
    """MRL-12 finding 1: a self-consistent Phase B dir from another run must not be accepted."""
    rel = write_release(tmp_path)
    fake_real(monkeypatch, GradeRunner())
    sa.main(grade_argv(tmp_path, rel))
    other = tmp_path / "B2"
    other.mkdir()
    raw = json.dumps({"other": {}}).encode()
    (other / "diagnostics.json").write_bytes(raw)
    h = hashlib.sha256(raw).hexdigest()
    (other / "manifest.json").write_text(json.dumps({"diagnostics_sha256": h, "roots": [
        {"root_id": "other", "runner_invocations": 3, "executor_seconds": 1.5}]}))
    with pytest.raises(ValueError, match="continue phase bound"):
        sa.main(_analysis_argv(tmp_path, h, "B2"))
    assert not (tmp_path / "in.json").exists()


def test_phase_b_root_set_must_equal_view(tmp_path, phases, monkeypatch):
    rel = write_release(tmp_path)
    fake_real(monkeypatch, GradeRunner())
    sa.main(grade_argv(tmp_path, rel))
    man = json.loads((tmp_path / "B/manifest.json").read_text())
    man["roots"] = man["roots"][1:]
    (tmp_path / "B/manifest.json").write_text(json.dumps(man))
    with pytest.raises(ValueError, match="roots"):
        sa.main(_analysis_argv(tmp_path, phases["diagnostics_sha256"]))
    assert not (tmp_path / "in.json").exists()


def test_out_of_repo_release_manifest_refused(tmp_path, phases, monkeypatch):
    """MRL-12 finding 2: bindings must come from the committed release manifest, not a copy."""
    rel = write_release(tmp_path)
    monkeypatch.setattr(sandbox, "run_program", GradeRunner())
    monkeypatch.setattr(grade, "verify_attestation", lambda path: {"passed": True})
    with pytest.raises(SystemExit, match="committed"):
        sa.main(grade_argv(tmp_path, rel))
    assert not (tmp_path / "G").exists()
    with pytest.raises(ValueError, match="committed"):
        sa.verify_committed_release(rel / "release_manifest.json")


def test_contract_binding_shape_checked_at_load(tmp_path):
    rel = write_release(tmp_path, expected_contract_sha256="not-a-digest")
    with pytest.raises(ValueError, match="expected_contract_sha256"):
        sa.load_release_bindings(rel / "release_manifest.json", rel / "private_specs.jsonl")


# ---------------------------------------------------------------- MRL-16: allowlist, grading_limits, diag schema
def _with_manifest_fields(rel, **fields):
    m = json.loads((rel / "release_manifest.json").read_text())
    m.update(fields)
    (rel / "release_manifest.json").write_text(json.dumps(m))


def test_allowlist_names_v2_and_v3_only(tmp_path):
    """MRL-19 added the E13a five-root release; every entry still gets the identical committed-hash check."""
    assert sa.COMMITTED_RELEASE_MANIFESTS == ("experiments/landmark/dev_release_v2/release_manifest.json",
                                              "experiments/landmark/dev_release_v3/release_manifest.json",
                                              "experiments/landmark/e13a_release/release_manifest.json")
    for bad in (ROOT / "experiments/landmark/dev_release_v2_1/release_manifest.json", tmp_path / "release_manifest.json"):
        with pytest.raises(ValueError, match="committed"):
            sa.verify_committed_release(bad)


def test_grading_limits_default_v2_and_strict_v3(tmp_path):
    rel = write_release(tmp_path)
    n = len(specs())
    d = sa.load_grading_limits(rel / "release_manifest.json", specs())
    assert (d["artifact_starts"], d["recheck_starts"], d["grading_seconds"], d["seconds_cap"]) == (77, 24, 240, 240)
    good = {"n_roots": n, "artifact_starts": 11 * n, "recheck_starts": 2 * n, "max_private_starts": 13 * n, "grading_seconds": 600}
    _with_manifest_fields(rel, grading_limits=good)
    d = sa.load_grading_limits(rel / "release_manifest.json", specs())
    assert (d["artifact_starts"], d["recheck_starts"], d["grading_seconds"]) == (11 * n, 2 * n, 600)
    for bad in ({**good, "grading_seconds": 601}, {**good, "max_private_starts": 13 * n + 1},
                {**good, "artifact_starts": 190, "recheck_starts": 11, "max_private_starts": 201}, {**good, "n_roots": n + 1},
                {**good, "grading_seconds": True}, {k: v for k, v in good.items() if k != "n_roots"}, {**good, "extra": 1}):
        _with_manifest_fields(rel, grading_limits=bad)
        with pytest.raises(ValueError, match="grading_limits"):
            sa.load_grading_limits(rel / "release_manifest.json", specs())


def test_limits_and_schema_parse_the_verified_bytes_not_a_reread(tmp_path, monkeypatch):
    """Review finding (TOCTOU): the manifest is read once, those bytes are checked against the HEAD blob, and
    grading_limits / diagnostic_schema are parsed from the same bytes; a later swap of the file is ignored."""
    import types
    n = len(specs())
    good = {"n_roots": n, "artifact_starts": 11 * n, "recheck_starts": 2 * n, "max_private_starts": 13 * n, "grading_seconds": 600}
    swapped = {"n_roots": n, "artifact_starts": 199, "recheck_starts": 1, "max_private_starts": 200, "grading_seconds": 600}
    rel = sa.COMMITTED_RELEASE_MANIFESTS[1]
    path = tmp_path / rel
    path.parent.mkdir(parents=True)
    blob = json.dumps({"grading_limits": good, "diagnostic_schema": "public-diagnostic-v2"}).encode()
    path.write_bytes(blob)
    monkeypatch.setattr(sa, "ROOT", tmp_path)
    monkeypatch.setattr(sa, "subprocess", types.SimpleNamespace(run=lambda *a, **k: types.SimpleNamespace(returncode=0, stdout=blob)))
    data = path.read_bytes()
    assert sa.verify_committed_release(path, data) == hashlib.sha256(blob).hexdigest()
    path.write_bytes(json.dumps({"grading_limits": swapped}).encode())  # replaced after the gate
    d = sa.load_grading_limits(data, specs())
    assert (d["artifact_starts"], d["recheck_starts"]) == (11 * n, 2 * n)
    assert sa.manifest_diagnostic_schema(data) == "public-diagnostic-v2"
    with pytest.raises(ValueError, match="HEAD"):
        sa.verify_committed_release(path, path.read_bytes())  # bytes that differ from the blob are refused
    src = inspect.getsource(sa.cmd_grade) + inspect.getsource(sa.cmd_analysis_input)
    assert "load_grading_limits(release_bytes" in src and "manifest_diagnostic_schema(release_bytes)" in src
    assert src.count("verify_committed_release(a.release_manifest, release_bytes)") == 2


def test_grade_study_seconds_cap_only_raised_explicitly(tmp_path):
    kw = dict(fake_runner_for_tests=True)  # budget checks run before any other input is touched
    with pytest.raises(ValueError, match="budget"):
        sa.grade_study([], specs(), GradeRunner(), max_seconds=600, **kw)  # default cap 240
    with pytest.raises(ValueError, match="budget"):
        sa.grade_study([], specs(), GradeRunner(), max_seconds=601, max_seconds_cap=601, **kw)
    with pytest.raises(ValueError, match="budget"):
        sa.grade_study([], specs(), GradeRunner(), max_executions=201, max_seconds=600, max_seconds_cap=600, **kw)
    with pytest.raises(ValueError, match="required"):  # passes the budget gate, then needs the J7 bindings
        sa.grade_study([], specs(), GradeRunner(), max_executions=200, max_seconds=600, max_seconds_cap=600, **kw)


def test_cli_grade_uses_manifest_grading_limits(tmp_path, phases, monkeypatch):
    rel = write_release(tmp_path)
    n = len(specs())
    _with_manifest_fields(rel, grading_limits={"n_roots": n, "artifact_starts": 11 * n, "recheck_starts": 2 * n,
                                               "max_private_starts": 13 * n, "grading_seconds": 600},
                          diagnostic_schema=diagnostic.SCHEMA)
    runner = GradeRunner()
    fake_real(monkeypatch, runner)
    seen = {}
    real_gs = sa.grade_study
    monkeypatch.setattr(sa, "grade_study", lambda *a, **k: seen.update(k) or real_gs(*a, **k))
    summary = sa.main(grade_argv(tmp_path, rel))
    assert summary["planned_max_starts"] == 13 * n and summary["grading_seconds"] == 600
    assert (seen["max_executions"], seen["max_seconds"], seen["max_seconds_cap"]) == (13 * n, 600, 600)
    assert events(tmp_path / "G" / sa.GRADING_LEDGER)[0]["planned_max_starts"] == 13 * n


def test_cli_grade_refuses_bad_grading_limits_before_reservation(tmp_path, phases, monkeypatch):
    rel = write_release(tmp_path)
    _with_manifest_fields(rel, grading_limits={"n_roots": 99, "artifact_starts": 1, "recheck_starts": 0,
                                               "max_private_starts": 1, "grading_seconds": 60})
    fake_real(monkeypatch, GradeRunner())
    with pytest.raises(SystemExit, match="grading_limits"):
        sa.main(grade_argv(tmp_path, rel))
    assert not (tmp_path / "G").exists()


def test_analysis_input_enforces_manifest_diagnostic_schema(tmp_path, phases, monkeypatch):
    rel = write_release(tmp_path)
    fake_real(monkeypatch, GradeRunner())
    sa.main(grade_argv(tmp_path, rel))
    h = phases["diagnostics_sha256"]
    _with_manifest_fields(rel, diagnostic_schema=diagnostic.SCHEMA)
    argv = _analysis_argv(tmp_path, h) + ["--release-manifest", str(rel / "release_manifest.json")]
    data = sa.main(argv)
    assert data["sources"]["diagnostic_schema"] == diagnostic.SCHEMA
    assert data["sources"]["committed_release_manifest_sha256"] == "c" * 64
    (tmp_path / "in.json").unlink()
    monkeypatch.setattr(diagnostic, "SCHEMA_V2", "public-diagnostic-v2", raising=False)
    _with_manifest_fields(rel, diagnostic_schema="public-diagnostic-v2")
    with pytest.raises(ValueError, match="not schema public-diagnostic-v2"):  # v1 records under a v2 release
        sa.main(argv)
    assert not (tmp_path / "in.json").exists()
    _with_manifest_fields(rel, diagnostic_schema="public-diagnostic-v9")
    with pytest.raises(ValueError, match="Unknown diagnostic_schema"):
        sa.main(argv)


def test_validate_phase_b_diagnostics_v2_dispatch(monkeypatch):
    monkeypatch.setattr(diagnostic, "SCHEMA_V2", "public-diagnostic-v2", raising=False)
    calls = []
    monkeypatch.setattr(diagnostic, "validate_diagnostic", lambda d, *a, **k: calls.append(k))
    v2 = {"r1": {"schema_version": "public-diagnostic-v2", "root_id": "r1", "initial_artifact_sha256": "a" * 64, "cases": []}}
    assert sa.validate_phase_b_diagnostics(v2) == "public-diagnostic-v2" and calls == [{"schema": "public-diagnostic-v2"}]
    v1 = {"r1": dict(v2["r1"], schema_version=diagnostic.SCHEMA)}
    assert sa.validate_phase_b_diagnostics(v1) == diagnostic.SCHEMA and calls[-1] == {}
    with pytest.raises(ValueError, match="mix schemas"):
        sa.validate_phase_b_diagnostics({**v2, "r2": dict(v1["r1"], root_id="r2")})
    with pytest.raises(ValueError, match="carries root_id"):
        sa.validate_phase_b_diagnostics({"r9": v2["r1"]})
