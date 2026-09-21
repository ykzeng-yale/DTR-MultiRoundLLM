"""MRL-12: complete A-E mock orchestration (fakes only). Phase A fake receiver -> Phase B FAKE_RUNNER ->
Phase C bound to Phase B's diagnostics sha -> study_adapter CLI grade (sandbox.run_program monkeypatched to a
parse-only FAKE; attestation verification faked) -> analysis-input CLI -> analyze_diagnostic.analyze.
No model, receiver, reference, candidate, canary or sandbox program is ever executed."""
import hashlib, importlib.util, json, re, sys
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
    monkeypatch.setattr(sa, "verify_committed_release", lambda path: "c" * 64)  # tmp release; the gate is tested below


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
