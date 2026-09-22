"""MRL-16: mock A -> B(display v2) -> C -> grade -> analysis over the REAL dev_release_v3 tasks, specs and public
examples. Fakes only: a fake receiver, a FAKE_RUNNER that emits authentic v2 result lines (programs are compiled,
never executed), a parse-only fake for sandbox.run_program and a faked attestation / committed-release check.
No model, receiver, reference, candidate or control program is ever executed."""
import ast, hashlib, importlib.util, json, re, sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.landmark import study_adapter as sa, public_phase as pp, public_check as pc, grade, sandbox  # noqa: E402
from experiments.landmark import diagnostic, analyze_diagnostic as ad  # noqa: E402
from experiments.common.integrity import hack_gate  # noqa: E402


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


tcd = _load("_e12_collect_helpers", "test_landmark_collect_diagnostic.py")
cd = tcd.cd
PKG = ROOT / "experiments/landmark/dev_release_v3"
EXAMPLES = PKG / "public_examples_v3.json"
ROSTER = [918, 825, 842, 816, 895, 868, 288, 154, 863, 966, 652, 651, 499, 974]
TASKS = [json.loads(x) for x in (PKG / "tasks.jsonl").read_text().splitlines() if x.strip()]
SPECS = [json.loads(x) for x in (PKG / "private_specs.jsonl").read_text().splitlines() if x.strip()]
SPEC = json.loads(EXAMPLES.read_text())["cases"]
BY_EP = {c["entry_point"]: c for c in SPEC}
LIMITS = {"n_roots": 14, "artifact_starts": 154, "recheck_starts": 28, "max_private_starts": 182, "grading_seconds": 600}


def _signature(task):
    return re.search(r"^Required function interface: (def .+:)$", task["public_context"], flags=re.M).group(1)


class Receiver(tcd.Fake):
    """Plausible code: the task's own interface line with a constant body (text only; never run)."""
    def generate(self, payload, timeout):
        self.payloads.append(payload)
        i = len(self.payloads) - 1
        text = f"{_signature(TASKS[i])}\n    return None\n" if i < len(TASKS) else "def g():\n    return 1\n"
        return {"message": {"content": text}, "done": True, "prompt_eval_count": 40, "eval_count": 20}


class V2Runner:
    """FAKE_RUNNER for the REAL v2 harness: compiles it, then emits authentic v2 lines for this run's nonce.
    Even roster positions pass (canonical repr of the expected value); odd ones are wrong_value."""
    FAKE_RUNNER = True

    def __init__(self):
        self.programs = []

    def __call__(self, program, **limits):
        compile(program, "<public-harness>", "exec")  # compiled only, never executed
        assert "_pc_display_value" in program  # the v2 display policy is computed inside isolation
        self.programs.append(program)
        nonce = re.search(re.escape(pc.PUBLIC_STARTED) + r"([0-9a-f]+)", program).group(1)
        ep = next(e for e in BY_EP if re.search(rf"\b{re.escape(e)}\b", program))
        passing = [c["root_id"] for c in SPEC].index(BY_EP[ep]["root_id"]) % 2 == 0
        lines = []
        for i, case in enumerate(BY_EP[ep]["cases"]):
            exp = ast.literal_eval(case["expected_literal"])
            got = exp if passing else (None if exp is not None else 0)
            kind, rep = diagnostic.display_value_v2(got)
            assert kind == "literal"
            lines.append(json.dumps({"n": nonce, "i": i, "status": "pass" if passing else "wrong_value",
                                     "returned": rep, "value_kind": "literal"}, sort_keys=True, separators=(",", ":")))
        return {"stdout": pc.PUBLIC_STARTED + nonce + "\n" + "".join(l + "\n" for l in lines),
                "returncode": 0, "timed_out": False}


class GradeRunner:
    """Parse-only FAKE for sandbox.run_program: passes iff the program embeds a spec's reference code verbatim."""
    def __init__(self):
        self.programs = []
        self.refs = [s["reference_code"] for s in SPECS]

    def __call__(self, program, timeout_s, cpu_seconds, output_cap):
        compile(program, "<fake>", "exec")  # never executed
        self.programs.append(program)
        start = re.search(grade.STARTED + r"[0-9a-f]{24}", program).group(0)
        sentinel = re.search(r"__LANDMARK_PRIVATE_OK__[0-9a-f]{24}", program).group(0)
        ok = any(r in program for r in self.refs)
        return {"stdout": start + "\n" + (sentinel + "\n" if ok else ""), "stdout_tail": sentinel if ok else "AssertionError",
                "timed_out": False, "returncode": 0 if ok else 1, "sandbox_kind": "seatbelt", "passed": ok,
                "executed": True, "seconds": 0.01}


@pytest.fixture(autouse=True)
def no_real_execution(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("sandbox.run_program must never run in MRL-16 tests")
    monkeypatch.setattr(sandbox, "run_program", refuse)


def config():
    return tcd.make_config(prior_seen_root_ids=[], prior_seen_family_ids=[], max_calls=154,
                           max_completion_tokens=154 * 512)


def test_real_v3_package_static_checks():
    assert [t["root_id"] for t in TASKS] == [s["root_id"] for s in SPECS] == [c["root_id"] for c in SPEC] \
        == [f"mbpp/{i}" for i in ROSTER]
    grade.validate_specs(TASKS, SPECS)
    for t, s, c in zip(TASKS, SPECS, SPEC):
        assert c["entry_point"] == s["entry_point"]
        assert t["public_context"].endswith("\n\n" + diagnostic.render_public_examples(c["entry_point"], c["cases"]))
        assert [x["case_id"] for x in c["cases"]] == [f"public-{t['root_id'].split('/')[1]}-1"]
        # every public expected value is displayable under v2 and its skeleton fits the schema
        assert diagnostic.display_value_v2(ast.literal_eval(c["cases"][0]["expected_literal"]))[0] == "literal"
        for ctl in s["negative_controls"]:
            compile(ctl["code"], "<control>", "exec")
            assert hack_gate(ctl["code"], s["entry_point"]) == []
    pc.assert_public_inputs_only([EXAMPLES])  # the one allowlisted public file of the release
    for name in ("tasks.jsonl", "private_specs.jsonl", "controls_rationale.json"):
        with pytest.raises(ValueError):
            pc.assert_public_inputs_only([PKG / name])


def write_release(tmp_path, cfg):
    rel = tmp_path / "R"
    rel.mkdir()
    (rel / "tasks.jsonl").write_bytes((PKG / "tasks.jsonl").read_bytes())
    (rel / "private_specs.jsonl").write_bytes((PKG / "private_specs.jsonl").read_bytes())
    (rel / "config.json").write_text(json.dumps(cfg))
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    bindings = {"frozen_tasks_path": str(rel / "tasks.jsonl"), "frozen_tasks_sha256": sha(rel / "tasks.jsonl"),
                "expected_contract_sha256": grade.digest(grade.contract(SPECS)),
                "expected_config_sha256": sa.digest(cfg), "expected_source_hashes": sa.grading_source_hashes()}
    manifest = {"package": {n: sha(rel / n) for n in sa.PACKAGE_FILES}, "grading_bindings": bindings,
                "grading_limits": dict(LIMITS), "diagnostic_schema": "public-diagnostic-v2"}
    (rel / "release_manifest.json").write_text(json.dumps(manifest))
    return rel


def test_real_v3_a_b_c_grade_analysis(tmp_path, monkeypatch):
    cfg = config()
    # A: 14 initial calls, one per root.
    cd.run_initial(cfg, TASKS, tmp_path / "A", adapter=Receiver())
    # B: the real v2 harness via check_artifact(display="v2"), at most one executor start per root.
    runner = V2Runner()
    gen = iter(f"{i:032x}" for i in range(100))
    m = pp.run_phase_b(tmp_path / "A", EXAMPLES, tmp_path / "B", runner, nonce_factory=lambda: next(gen), display="v2")
    assert m["executor_starts"] == len(runner.programs) <= 14 and len(runner.programs) == 14
    assert m["display"] == "v2" and m["diagnostic_schema"] == diagnostic.SCHEMA_V2
    raw = (tmp_path / "B/diagnostics.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == m["diagnostics_sha256"]
    diags = json.loads(raw)
    assert sorted(diags) == sorted(c["root_id"] for c in SPEC)
    for k, c in enumerate(SPEC):
        d = diags[c["root_id"]]
        diagnostic.validate_diagnostic(d, c["entry_point"], c["cases"])
        assert len(json.dumps(d).encode()) <= diagnostic.MAX_DIAGNOSTIC_BYTES
        row = d["cases"][0]
        assert row["value_kind"] == "literal" and row["status"] == ("pass" if k % 2 == 0 else "wrong_value")
        assert ast.literal_eval(row["expected"]) == ast.literal_eval(c["cases"][0]["expected_literal"])
    # C: 140 continue calls bound to B's diagnostics sha -> 154 planned and attempted calls in total.
    done = cd.run_continue(cfg, TASKS, tmp_path / "A", tmp_path / "B/diagnostics.json", tmp_path / "C",
                           expected_diagnostics_sha256=m["diagnostics_sha256"], adapter=tcd.Fake(),
                           public_examples={c["root_id"]: c for c in SPEC})
    assert done["attempted_calls"] == 154 and done["fatal_error"] is None  # cumulative: 14 initial + 140 continue
    assert done["reserved_completion_tokens"] == 154 * 512
    cman = json.loads((tmp_path / "C/manifest.json").read_text())
    assert cman["diagnostic_schema"] == "public-diagnostic-v2"
    planned = cman.get("planned_calls")
    if planned is not None:
        assert planned["total"] == 154
    # Grade: temp manifest carries grading_limits; the committed-path gate is faked (tested in e11 orchestration).
    rel = write_release(tmp_path, cfg)
    (tmp_path / "att.json").write_text("{}")
    grunner = GradeRunner()
    monkeypatch.setattr(sandbox, "run_program", grunner)
    monkeypatch.setattr(grade, "verify_attestation", lambda path: {"passed": True})
    monkeypatch.setattr(sa, "verify_committed_release", lambda path, data=None: "c" * 64)
    summary = sa.main(["grade", "--release-manifest", str(rel / "release_manifest.json"),
                       "--specs", str(rel / "private_specs.jsonl"), "--initial-dir", str(tmp_path / "A"),
                       "--continue-dir", str(tmp_path / "C"), "--out", str(tmp_path / "G"),
                       "--attestation", str(tmp_path / "att.json"), "--real"])
    assert summary["planned_max_starts"] == 182 and summary["planned_max_artifacts"] == 154
    assert summary["planned_max_rechecks"] == 28 and summary["grading_seconds"] == 600
    assert 0 < summary["actual_starts"] == len(grunner.programs) <= 182
    # Analysis input, with the release fixing the diagnostic schema; then the analysis itself.
    data = sa.main(["analysis-input", "--view", str(tmp_path / "G/view"), "--grades", str(tmp_path / "G/grades.jsonl"),
                    "--phase-b-dir", str(tmp_path / "B"), "--expected-diagnostics-sha256", m["diagnostics_sha256"],
                    "--release-manifest", str(rel / "release_manifest.json"), "--out", str(tmp_path / "in.json")])
    assert {r["root_id"] for r in data["roots"]} == {c["root_id"] for c in SPEC}
    report = ad.analyze(data["roots"], data["diagnostics"], replicates=2)
    assert report["diagnostic_schema"] == diagnostic.SCHEMA_V2
    json.dumps(report)
