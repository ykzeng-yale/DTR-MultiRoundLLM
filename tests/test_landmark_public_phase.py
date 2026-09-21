"""MRL-08 Phase B driver tests: fake Phase A (fake receiver) and FAKE runners only; nothing is executed."""
import hashlib, importlib.util, json, re, sys, types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.landmark import diagnostic, public_check as pc, public_phase as pp  # noqa: E402


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tests" / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


tcd = _load("_pp_collect_diag_helpers", "test_landmark_collect_diagnostic.py")  # Fake receiver, make_config
tpc = _load("_pp_public_check_helpers", "test_landmark_public_check.py")       # authentic-line helper
cd = tcd.cd
EXAMPLES = ROOT / "docs" / "public_diagnostic_examples_v1.json"
SPEC = json.loads(EXAMPLES.read_text())["cases"]
BAD = {3: "def broken(:\n", 5: "```python\nx=1\n```\n```python\ny=2\n```"}  # static format errors: no start
TASKS = [{"root_id": c["root_id"], "family_id": f"fam{i}", "prompt": f"Write {c['entry_point']}.",
          "public_context": "Public information.\n\n" + diagnostic.render_public_examples(c["entry_point"], c["cases"])}
         for i, c in enumerate(SPEC)]


class Receiver(tcd.Fake):
    def generate(self, payload, timeout):
        self.payloads.append(payload)
        i = len(self.payloads) - 1
        text = BAD.get(i, f"def {SPEC[i]['entry_point']}(*a):\n    return 0\n")
        return {"message": {"content": text}, "done": True, "prompt_eval_count": 40, "eval_count": 20}


class Runner:
    """Canned stdout: three authentic wrong_value lines for this run's nonce. Records every invocation."""
    FAKE_RUNNER = True
    def __init__(self):
        self.programs = []

    def __call__(self, program, **limits):
        compile(program, "<public-harness>", "exec")  # compiled only, never executed
        assert limits == {"timeout_s": 10, "cpu_seconds": 5, "output_cap": 65536}
        if "def broken(" in program or "y=2" in program:
            raise AssertionError("runner called for a format-error artifact")
        self.programs.append(program)
        nonce = re.search(re.escape(pc.PUBLIC_STARTED) + r"([0-9a-f]+)", program).group(1)
        return {"stdout": tpc.out(*(tpc.line(i, "wrong_value", -12345, "int", nonce=nonce) for i in range(3)), nonce=nonce),
                "returncode": 0, "timed_out": False}


def _strict(data):
    def hook(pairs):
        keys = [k for k, _ in pairs]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate key")
        return dict(pairs)
    return json.loads(data, object_pairs_hook=hook)


@pytest.fixture(autouse=True)
def strict_loads(monkeypatch):
    # The 'strict' agent owns diagnostic.strict_json_loads; supply it only if absent so the driver's call resolves.
    if not hasattr(diagnostic, "strict_json_loads"):
        monkeypatch.setattr(diagnostic, "strict_json_loads", _strict, raising=False)


def config():
    return tcd.make_config(prior_seen_root_ids=[], prior_seen_family_ids=[])


@pytest.fixture
def phase_a(tmp_path):
    cd.run_initial(config(), TASKS, tmp_path / "A", adapter=Receiver())
    return tmp_path / "A"


def nonces():
    for i in range(100):
        yield f"{i:032x}"


def test_end_to_end_diagnostics_bound_and_accepted_by_continue(phase_a, tmp_path, monkeypatch):
    seen, real = [], getattr(diagnostic, "validate_diagnostic", None)
    def recording(d, *public):
        seen.append(d["root_id"])
        return real(d, *public) if real else None
    monkeypatch.setattr(diagnostic, "validate_diagnostic", recording, raising=False)
    runner, gen = Runner(), nonces()
    m = pp.run_phase_b(phase_a, EXAMPLES, tmp_path / "B", runner, nonce_factory=lambda: next(gen))
    raw = (tmp_path / "B/diagnostics.json").read_bytes()
    diags = json.loads(raw)
    assert raw == json.dumps(diags, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    assert hashlib.sha256(raw).hexdigest() == m["diagnostics_sha256"]
    assert json.loads((tmp_path / "B/manifest.json").read_text()) == m
    # Fixed roots.jsonl order; build_diagnostic may also validate internally, so dedupe consecutive calls.
    assert list(dict.fromkeys(seen)) == [c["root_id"] for c in SPEC] and list(diags) == sorted(set(seen))
    rows = {json.loads(x)["root_id"]: json.loads(x) for x in (phase_a / "roots.jsonl").read_text().splitlines()}
    for i, c in enumerate(SPEC):
        d = diags[c["root_id"]]
        assert d["initial_artifact_sha256"] == rows[c["root_id"]]["artifact_sha256"]
        want = "format_error" if i in BAD else "wrong_value"
        assert [r["status"] for r in d["cases"]] == [want] * 3
    # Start count excludes format errors; no retries; nonces are not written anywhere.
    assert m["executor_starts"] == len(runner.programs) == len(SPEC) - len(BAD)
    assert [r["runner_invocations"] for r in m["roots"]] == [0 if i in BAD else 1 for i in range(len(SPEC))]
    assert m["retries"] == 0 and m["public_limits"] == pc.PUBLIC_LIMITS
    assert set(m["executor_source_sha256"]) == {f"experiments/landmark/{n}" for n in (
        "public_phase.py", "public_check.py", "diagnostic.py", "sandbox.py", "grade.py")} | {"experiments/common/integrity.py"}
    assert m["executor_source_sha256"]["experiments/landmark/public_check.py"] == hashlib.sha256(Path(pc.__file__).read_bytes()).hexdigest()
    assert m["runner"] == {"module": __name__, "qualname": "Runner"} and m["attestation"] == "fake_runner_for_tests"
    ledger = (tmp_path / "B/attempts.jsonl").read_bytes()
    assert hashlib.sha256(ledger).hexdigest() == m["attempts_ledger_sha256"]
    events = [json.loads(x)["event"] for x in ledger.splitlines()]
    assert events[0] == "reserved" and events[-1] == "complete"
    assert events.count("start") == events.count("result") == len(runner.programs) and events.count("classified") == len(SPEC)
    written = raw + (tmp_path / "B/manifest.json").read_bytes() + ledger
    assert all(f"{i:032x}".encode() not in written for i in range(len(SPEC)))
    # The continue phase accepts exactly these bytes under the manifest's SHA-256.
    done = cd.run_continue(config(), TASKS, phase_a, tmp_path / "B/diagnostics.json", tmp_path / "C",
                           expected_diagnostics_sha256=m["diagnostics_sha256"], adapter=tcd.Fake(),
                           public_examples={c["root_id"]: c for c in SPEC})
    assert done["diagnostics_sha256"] == m["diagnostics_sha256"]


def test_works_without_validate_diagnostic(phase_a, tmp_path, monkeypatch):
    # A diagnostic module that does not expose validate_diagnostic (the driver looks it up by attribute).
    bare = types.SimpleNamespace(build_diagnostic=diagnostic.build_diagnostic, diagnostic_bytes=diagnostic.diagnostic_bytes,
                                 strict_json_loads=diagnostic.strict_json_loads, public_skeleton=diagnostic.public_skeleton)
    monkeypatch.setattr(pp, "diagnostic", bare)
    m = pp.run_phase_b(phase_a, EXAMPLES, tmp_path / "B", Runner())
    assert m["executor_starts"] == len(SPEC) - len(BAD)


def test_tampered_artifact_refused(phase_a, tmp_path):
    art = sorted((phase_a / "artifacts").glob("*.txt"))[0]
    art.write_bytes(art.read_bytes() + b"# edited\n")
    runner = Runner()
    with pytest.raises(ValueError, match="changed after completion"):
        pp.run_phase_b(phase_a, EXAMPLES, tmp_path / "B", runner)
    # Even with completion.json re-sealed, the roots.jsonl artifact SHA-256 still refuses it.
    comp = json.loads((phase_a / "completion.json").read_text())
    comp["checksums"][art.relative_to(phase_a).as_posix()] = hashlib.sha256(art.read_bytes()).hexdigest()
    (phase_a / "completion.json").write_text(json.dumps(comp))
    with pytest.raises(ValueError, match="differ from the recorded SHA-256"):
        pp.run_phase_b(phase_a, EXAMPLES, tmp_path / "B", runner)
    assert runner.programs == [] and not (tmp_path / "B").exists()


def test_refuses_existing_out_dir(phase_a, tmp_path):
    (tmp_path / "B").mkdir()
    runner = Runner()
    with pytest.raises(FileExistsError):
        pp.run_phase_b(phase_a, EXAMPLES, tmp_path / "B", runner)
    assert runner.programs == [] and list((tmp_path / "B").iterdir()) == []


def test_examples_path_goes_through_public_allowlist(phase_a, tmp_path):
    with pytest.raises(ValueError):
        pp.run_phase_b(phase_a, ROOT / "work" / "public_diagnostic_examples_v1.json", tmp_path / "B", Runner())


def test_ledger_keeps_start_when_classifier_raises(phase_a, tmp_path, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("classifier crashed")
    monkeypatch.setattr(pc, "classify", boom)
    gen = nonces()
    with pytest.raises(RuntimeError, match="classifier crashed"):
        pp.run_phase_b(phase_a, EXAMPLES, tmp_path / "B", Runner(), nonce_factory=lambda: next(gen))
    recs = [json.loads(x) for x in (tmp_path / "B/attempts.jsonl").read_text().splitlines()]
    assert [r["event"] for r in recs] == ["reserved", "start", "result", "incomplete"]
    start, result = recs[1], recs[2]
    assert start["root_id"] == SPEC[0]["root_id"] and start["nonce_sha256"] == hashlib.sha256(f"{0:032x}".encode()).hexdigest()
    assert f"{0:032x}" not in (tmp_path / "B/attempts.jsonl").read_text()
    assert result["returncode"] == 0 and result["timed_out"] is False and len(result["stdout_sha256"]) == 64
    assert "classifier crashed" in (tmp_path / "B/INCOMPLETE").read_text()
    assert not (tmp_path / "B/diagnostics.json").exists() and not (tmp_path / "B/manifest.json").exists()
    # A rerun into the same out_dir is refused and does not start anything (no uncharged rerun).
    monkeypatch.undo()
    runner = Runner()
    with pytest.raises(FileExistsError, match="no uncharged rerun"):
        pp.run_phase_b(phase_a, EXAMPLES, tmp_path / "B", runner)
    assert runner.programs == []


def test_strict_json_used_for_phase_a_reads(phase_a, tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(diagnostic, "strict_json_loads", lambda d: calls.append(1) or _strict(d), raising=False)
    comp = (phase_a / "completion.json").read_text()
    (phase_a / "completion.json").write_text(comp.replace("{", '{"phase": "initial", ', 1))
    with pytest.raises(ValueError, match="duplicate"):
        pp.run_phase_b(phase_a, EXAMPLES, tmp_path / "B", Runner())
    assert calls and not (tmp_path / "B").exists()


def test_sandbox_runner_refused_without_attestation(phase_a, tmp_path, monkeypatch):
    from experiments.landmark import sandbox
    assert "source_sha256" in pp.runner_identity(sandbox.run_program)
    with pytest.raises(ValueError, match="attestation"):
        pp.run_phase_b(phase_a, EXAMPLES, tmp_path / "B", sandbox.run_program)
    assert not (tmp_path / "B").exists()


@pytest.fixture
def no_sandbox(monkeypatch):
    from experiments.landmark import grade, sandbox
    def never(*a, **k):
        raise AssertionError("sandbox.run_program must not be reached")
    monkeypatch.setattr(sandbox, "run_program", never)
    return grade


def _argv(phase_a, tmp_path, *extra):
    return ["--initial-dir", str(phase_a), "--examples", str(EXAMPLES), "--out", str(tmp_path / "B"),
            "--attestation", str(tmp_path / "att.json"), *extra]


def test_cli_refuses_without_real(phase_a, tmp_path, no_sandbox, monkeypatch):
    monkeypatch.setattr(no_sandbox, "verify_attestation", lambda p: pytest.fail("verified without --real"))
    with pytest.raises(SystemExit, match="--real"):
        pp.main(_argv(phase_a, tmp_path))
    assert not (tmp_path / "B").exists()


def test_cli_refuses_missing_or_invalid_attestation_first(phase_a, tmp_path, no_sandbox, monkeypatch):
    with pytest.raises(SystemExit, match="attestation not verified"):  # missing file
        pp.main(_argv(phase_a, tmp_path, "--real"))
    (tmp_path / "att.json").write_text("{}")
    def bad(path):
        raise ValueError("Containment attestation did not pass")
    monkeypatch.setattr(no_sandbox, "verify_attestation", bad)
    monkeypatch.setattr(pp, "load_initial", lambda *a: pytest.fail("inputs touched before attestation"))
    with pytest.raises(SystemExit, match="did not pass"):
        pp.main(_argv(phase_a, tmp_path, "--real"))
    assert not (tmp_path / "B").exists()


def test_cli_refuses_unresolved_value(phase_a, tmp_path, no_sandbox, monkeypatch):
    monkeypatch.setattr(no_sandbox, "verify_attestation", lambda p: pytest.fail("verified an unresolved path"))
    argv = _argv(phase_a, tmp_path, "--real")
    argv[argv.index("--attestation") + 1] = "UNRESOLVED: containment run"
    with pytest.raises(SystemExit, match="unresolved"):
        pp.main(argv)


def test_cli_verified_attestation_provenance_but_refuses_before_dispatch(phase_a, tmp_path, no_sandbox, monkeypatch):
    # Verified (fake) attestation, then a tampered Phase A refuses before out_dir or the (patched) sandbox is reached.
    (tmp_path / "att.json").write_text('{"x": 1}')
    fake = {"schema_version": "landmark-containment-v1", "passed": True, "checked_at": "t", "binding": {}, "script_sha256": "s",
            "checks": [{"name": "c1"}]}
    monkeypatch.setattr(no_sandbox, "verify_attestation", lambda p: fake)
    prov = pp.attestation_provenance(tmp_path / "att.json", fake)
    assert prov["sha256"] == hashlib.sha256(b'{"x": 1}').hexdigest() and prov["verified_check_names"] == ["c1"]
    art = sorted((phase_a / "artifacts").glob("*.txt"))[0]
    art.write_bytes(art.read_bytes() + b"#\n")
    with pytest.raises(ValueError, match="changed after completion"):
        pp.main(_argv(phase_a, tmp_path, "--real"))
    assert not (tmp_path / "B").exists()


# ---- MRL-09 fixer regressions ----
def test_wrapped_real_runner_and_incomplete_attestation_refused(tmp_path, phase_a):
    import functools as ft
    from experiments.landmark import sandbox
    assert (tmp_path / "A").is_dir()  # a real Phase A directory, so the refusal cannot be a missing-directory error
    for runner in (ft.partial(sandbox.run_program), lambda *a, **k: sandbox.run_program(*a, **k)):
        with pytest.raises(ValueError, match="attestation"):
            pp.run_phase_b(tmp_path / "A", EXAMPLES, tmp_path / "B", runner)
    for bad in ({"sha256": "x", "verified_fields": {"passed": False}},
                {"sha256": "a" * 64, "verified_fields": {k: None for k in pp.ATTESTATION_FIELDS}, "verified_check_names": ["c"]}):
        with pytest.raises(ValueError, match="Incomplete attestation"):
            pp.run_phase_b(tmp_path / "A", EXAMPLES, tmp_path / "B", sandbox.run_program, attestation=bad)
    assert not (tmp_path / "B").exists()


def test_malformed_public_example_is_refused_before_reservation(tmp_path, phase_a):
    """MRL-09 finding 6: an example the diagnostic policy rejects (tuple args_literal) must be refused before
    out_dir is reserved or any runner start is charged."""
    data = json.loads(Path(EXAMPLES).read_text())
    data["cases"][1]["cases"][0]["args_literal"] = "(4, [-4, -2, -2, -9])"
    bad = tmp_path / "examples_bad.json"
    bad.write_text(json.dumps(data))

    class Never:
        FAKE_RUNNER = True

        def __call__(self, *a, **k):
            raise AssertionError("runner must not start")
    with pytest.raises(ValueError, match="list literal"):
        pp.run_phase_b(tmp_path / "A", bad, tmp_path / "B", Never())
    assert not (tmp_path / "B").exists()
