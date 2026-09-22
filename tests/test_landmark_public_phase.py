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
    def recording(d, *public, **kw):  # MRL-16: build_diagnostic may pass schema=
        seen.append(d["root_id"])
        return real(d, *public, **kw) if real else None
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


# --- MRL-10: complete checksum inventory + Phase A manifest/assignment coverage, all before any runner start ---
def _reseal(d):
    comp = json.loads((d / "completion.json").read_text())
    comp["checksums"] = {q.relative_to(d).as_posix(): hashlib.sha256(q.read_bytes()).hexdigest()
                         for q in sorted(d.rglob("*")) if q.is_file() and q.name != "completion.json"}
    (d / "completion.json").write_text(json.dumps(comp))


def _edit_json(d, name, fn):
    doc = json.loads((d / name).read_text())
    fn(doc)
    (d / name).write_text(json.dumps(doc))


def _refused_before_start(phase_a, tmp_path, match):
    runner = Runner()
    with pytest.raises(ValueError, match=match):
        pp.run_phase_b(phase_a, EXAMPLES, tmp_path / "B", runner)
    assert runner.programs == [] and not (tmp_path / "B").exists()


def test_unlisted_extra_file_refused(phase_a, tmp_path):
    (phase_a / "artifacts" / "smuggled.txt").write_text("def f(): pass\n")
    _refused_before_start(phase_a, tmp_path, "Incomplete checksum inventory")


def test_inventory_missing_required_file_refused(phase_a, tmp_path):
    for name in ("calls.jsonl", "roots.jsonl", "manifest.json"):
        _edit_json(phase_a, "completion.json", lambda c: c["checksums"].pop(name))
        _refused_before_start(phase_a, tmp_path, "Incomplete checksum inventory")
        _reseal(phase_a)
    pp.load_initial(phase_a)  # resealed complete inventory loads


def test_inventory_missing_artifact_entry_refused(phase_a, tmp_path):
    art = sorted((phase_a / "artifacts").glob("*.txt"))[0].relative_to(phase_a).as_posix()
    _edit_json(phase_a, "completion.json", lambda c: c["checksums"].pop(art))
    _refused_before_start(phase_a, tmp_path, "Incomplete checksum inventory")


@pytest.mark.parametrize("edit,match", [
    (lambda m: m.pop("evidence_type"), "evidence_type"),
    (lambda m: m.__setitem__("evidence_type", "graded"), "evidence_type"),
    (lambda m: m.__setitem__("arm_set", "other"), "arm_set"),
    (lambda m: m.pop("assignment_table"), "assignment_table"),
    (lambda m: m["assignment_table"].pop(), "assignment_table"),
    (lambda m: m["assignment_table"].reverse(), "assignment_table"),
])
def test_manifest_and_assignment_coverage_refused_even_when_resealed(phase_a, tmp_path, edit, match):
    _edit_json(phase_a, "manifest.json", edit)
    _reseal(phase_a)
    _refused_before_start(phase_a, tmp_path, match)


def test_duplicate_or_missing_root_row_refused(phase_a, tmp_path):
    lines = (phase_a / "roots.jsonl").read_text().splitlines()
    (phase_a / "roots.jsonl").write_text("\n".join(lines[:-1]) + "\n")
    _reseal(phase_a)
    _refused_before_start(phase_a, tmp_path, "assignment_table")


def test_excluded_root_with_artifact_refused(phase_a, tmp_path):
    rows = [json.loads(x) for x in (phase_a / "roots.jsonl").read_text().splitlines() if x.strip()]
    k = next(i for i, r in enumerate(rows) if r.get("artifact_sha256"))
    rows[k]["excluded"] = True
    (phase_a / "roots.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    _edit_json(phase_a, "manifest.json", lambda m: m["assignment_table"][k].__setitem__("excluded", True))
    _reseal(phase_a)
    _refused_before_start(phase_a, tmp_path, "Excluded root has an artifact")


def _reseal(phase_a):
    comp = json.loads((phase_a / "completion.json").read_text())
    comp["checksums"] = {q.relative_to(phase_a).as_posix(): hashlib.sha256(q.read_bytes()).hexdigest()
                         for q in phase_a.rglob("*") if q.is_file() and q.name != "completion.json"}
    (phase_a / "completion.json").write_text(json.dumps(comp))


def test_uncovered_assigned_root_refused(phase_a, tmp_path):
    # MRL-10 review: a non-excluded assigned root with no artifact and no recorded failure must not be skipped.
    rows = [json.loads(x) for x in (phase_a / "roots.jsonl").read_text().splitlines()]
    victim = next(r for r in rows if not r["excluded"])
    (phase_a / victim["artifact"]).unlink()
    victim.update(artifact=None, artifact_sha256=None)
    victim.pop("status", None)
    (phase_a / "roots.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    _reseal(phase_a)
    with pytest.raises(ValueError, match="neither collected nor recorded"):
        pp.load_initial(phase_a)


def test_stray_artifact_refused(phase_a, tmp_path):
    (phase_a / "artifacts" / "ghost%2F999.txt").write_text("x")
    _reseal(phase_a)
    with pytest.raises(ValueError, match="artifacts/ does not equal"):
        pp.load_initial(phase_a)


# --- MRL-12: per-root executor elapsed seconds (time.monotonic around each runner call; fake clock) ---
class Clock:
    """Deterministic stand-in for public_phase.time; only the driver's module reference is replaced."""
    def __init__(self, broken=False):
        self.t, self.broken = 100.0, broken

    def monotonic(self):
        if self.broken:
            raise OSError("clock unavailable")
        return self.t


class TimedRunner(Runner):
    def __init__(self, clock, step, fail=False):
        super().__init__()
        self.clock, self.step, self.fail = clock, step, fail

    def __call__(self, program, **limits):
        self.clock.t += self.step
        if self.fail and "def broken(" not in program and "y=2" not in program:
            self.programs.append(program)
            raise RuntimeError("fake executor crashed")
        return super().__call__(program, **limits)


def _ledger(d):
    return [json.loads(x) for x in (d / "attempts.jsonl").read_text().splitlines()]


def test_executor_seconds_per_root_and_elapsed_in_ledger(phase_a, tmp_path, monkeypatch):
    clock = Clock()
    monkeypatch.setattr(pp, "time", clock)
    runner = TimedRunner(clock, 1.5)
    m = pp.run_phase_b(phase_a, EXAMPLES, tmp_path / "B", runner)
    assert [r["executor_seconds"] for r in m["roots"]] == [0.0 if i in BAD else 1.5 for i in range(len(SPEC))]
    for i, r in enumerate(m["roots"]):
        assert type(r["executor_seconds"]) is float  # format errors: zero starts, measured 0.0 (not null)
        assert r["runner_invocations"] == (0 if i in BAD else 1)
    assert json.loads((tmp_path / "B/manifest.json").read_text()) == m
    recs = _ledger(tmp_path / "B")
    results = [r for r in recs if r["event"] == "result"]
    assert len(results) == len(runner.programs) and all(r["elapsed_seconds"] == 1.5 for r in results)
    classified = {r["root_id"]: r["executor_seconds"] for r in recs if r["event"] == "classified"}
    assert classified == {r["root_id"]: r["executor_seconds"] for r in m["roots"]}


def test_elapsed_measured_when_runner_raises(phase_a, tmp_path, monkeypatch):
    clock = Clock()
    monkeypatch.setattr(pp, "time", clock)
    runner = TimedRunner(clock, 2.25, fail=True)
    m = pp.run_phase_b(phase_a, EXAMPLES, tmp_path / "B", runner)
    results = [r for r in _ledger(tmp_path / "B") if r["event"] == "result"]
    assert results and all("runner_error" in r and r["elapsed_seconds"] == 2.25 for r in results)
    assert [r["executor_seconds"] for r in m["roots"]] == [0.0 if i in BAD else 2.25 for i in range(len(SPEC))]


def test_unmeasurable_elapsed_is_null_never_zero(phase_a, tmp_path, monkeypatch):
    clock = Clock(broken=True)
    monkeypatch.setattr(pp, "time", clock)
    runner = Runner()
    m = pp.run_phase_b(phase_a, EXAMPLES, tmp_path / "B", runner)
    assert [r["executor_seconds"] for r in m["roots"]] == [0.0 if i in BAD else None for i in range(len(SPEC))]
    on_disk = json.loads((tmp_path / "B/manifest.json").read_text())
    assert [r["executor_seconds"] for r in on_disk["roots"]] == [r["executor_seconds"] for r in m["roots"]]
    results = [r for r in _ledger(tmp_path / "B") if r["event"] == "result"]
    assert len(results) == len(runner.programs) and all(r["elapsed_seconds"] is None for r in results)
    assert m["executor_starts"] == len(runner.programs)  # measurement failure never blocks or retries a start


def test_elapsed_helpers_null_on_unreadable_or_backwards_clock(monkeypatch):
    # Direct unit check of the per-root aggregation helpers: a backwards/unreadable clock yields null.
    clock = Clock()
    monkeypatch.setattr(pp, "time", clock)
    t0 = pp._monotonic()
    clock.t += 0.75
    assert pp._since(t0) == 0.75
    clock.t -= 5.0
    assert pp._since(t0) is None
    assert pp._since(None) is None
    clock.broken = True
    assert pp._monotonic() is None


# ---- MRL-16: display="v2" through A -> B -> C on a synthetic 3-root package (str / bool / tuple outputs) ----

V2_SPEC = [
    {"root_id": "mbpp/9001", "entry_point": "f_str",
     "cases": [{"case_id": "public-9001-1", "args_literal": "['ab']", "expected_literal": "'abc'"}]},
    {"root_id": "mbpp/9002", "entry_point": "f_bool",
     "cases": [{"case_id": "public-9002-1", "args_literal": "[3]", "expected_literal": "True"}]},
    {"root_id": "mbpp/9003", "entry_point": "f_tuple",
     "cases": [{"case_id": "public-9003-1", "args_literal": "[1, 'a']", "expected_literal": "(1, 'a')"}]},
]
V2_TASKS = [{"root_id": c["root_id"], "family_id": f"v2fam{i}", "prompt": f"Write {c['entry_point']}.",
             "public_context": "Public information.\n\n" + diagnostic.render_public_examples(c["entry_point"], c["cases"])}
            for i, c in enumerate(V2_SPEC)]
# What the (faked) isolated v2 harness observed for each root: str pass, bool wrong_value, tuple wrong_value.
V2_RESULTS = {"f_str": {"status": "pass", "returned": "'abc'", "value_kind": "literal", "reason": None},
              "f_bool": {"status": "wrong_value", "returned": "False", "value_kind": "literal", "reason": None},
              "f_tuple": {"status": "wrong_value", "returned": "(1, 'b', True)", "value_kind": "literal", "reason": None}}


class V2Receiver(tcd.Fake):
    def generate(self, payload, timeout):
        self.payloads.append(payload)
        i = len(self.payloads) - 1
        text = f"def {V2_SPEC[i]['entry_point']}(*a):\n    return None\n" if i < len(V2_SPEC) else "def g():\n    return 1\n"
        return {"message": {"content": text}, "done": True, "prompt_eval_count": 40, "eval_count": 20}


class V2Runner:
    FAKE_RUNNER = True
    def __init__(self):
        self.programs = []

    def __call__(self, program, **limits):
        compile(program, "<public-harness>", "exec")  # compiled only, never executed
        self.programs.append(program)
        return {"stdout": "", "returncode": 0, "timed_out": False}


@pytest.fixture
def v2_package(tmp_path):
    ex = tmp_path / "public_examples_v3.json"
    ex.write_text(json.dumps({"version": "public-examples-v3", "cases": V2_SPEC}))
    cfg = tcd.make_config(prior_seen_root_ids=[], prior_seen_family_ids=[])
    cd.run_initial(cfg, V2_TASKS, tmp_path / "A", adapter=V2Receiver())
    return cfg, ex, tmp_path / "A"


def _fake_check(seen):
    def check(output, entry_point, cases, runner, nonce, display="v1"):
        seen.append(display)
        runner(f"# harness for {entry_point}\nx = 1\n", timeout_s=10, cpu_seconds=5, output_cap=65536)  # one counted start
        return [dict(V2_RESULTS[entry_point]) for _ in cases]
    return check


def test_v2_display_end_to_end_a_b_c(v2_package, tmp_path, monkeypatch):
    cfg, ex, a = v2_package
    seen = []
    monkeypatch.setattr(pp.public_check, "check_artifact", _fake_check(seen))
    runner = V2Runner()
    m = pp.run_phase_b(a, ex, tmp_path / "B", runner, display="v2")
    assert seen == ["v2"] * 3 and m["executor_starts"] == len(runner.programs) == 3
    assert m["display"] == "v2" and m["diagnostic_schema"] == diagnostic.SCHEMA_V2 == "public-diagnostic-v2"
    reserved = json.loads((tmp_path / "B/attempts.jsonl").read_text().splitlines()[0])
    assert reserved["display"] == "v2" and reserved["diagnostic_schema"] == "public-diagnostic-v2"
    raw = (tmp_path / "B/diagnostics.json").read_bytes()
    diags = json.loads(raw)
    assert hashlib.sha256(raw).hexdigest() == m["diagnostics_sha256"]
    for c in V2_SPEC:
        d = diags[c["root_id"]]
        assert d["schema_version"] == "public-diagnostic-v2"
        diagnostic.validate_diagnostic(d, c["entry_point"], c["cases"])  # schema detected from the record
    rows = {c["root_id"]: diags[c["root_id"]]["cases"][0] for c in V2_SPEC}
    assert rows["mbpp/9001"]["expected"] == "'abc'" and rows["mbpp/9001"]["status"] == "pass"
    assert rows["mbpp/9002"]["expected"] == "True" and rows["mbpp/9002"]["returned"] == "False"
    assert rows["mbpp/9003"]["expected"] == "(1, 'a')" and rows["mbpp/9003"]["returned"] == "(1, 'b', True)"
    assert all(r["value_kind"] == "literal" for r in rows.values())
    # C: the continue phase validates each diagnostic with the schema it records, against the same examples file.
    examples = {c["root_id"]: c for c in json.loads(ex.read_text())["cases"]}
    done = cd.run_continue(cfg, V2_TASKS, a, tmp_path / "B/diagnostics.json", tmp_path / "C",
                           expected_diagnostics_sha256=m["diagnostics_sha256"], adapter=tcd.Fake(), public_examples=examples)
    assert done["diagnostics_sha256"] == m["diagnostics_sha256"] and done["attempted_calls"] == 3 * 11
    man = json.loads((tmp_path / "C/manifest.json").read_text())
    assert man["diagnostic_schema"] == "public-diagnostic-v2"


def test_v2_display_default_is_v1_and_unknown_display_refused(v2_package, tmp_path, monkeypatch):
    cfg, ex, a = v2_package
    with pytest.raises(ValueError, match="display"):
        pp.run_phase_b(a, ex, tmp_path / "B", V2Runner(), display="v3")
    assert not (tmp_path / "B").exists()
    # Default v1: v2 outputs (str/bool/tuple expected) are outside the v1 display policy -> refused, no diagnostics.
    with pytest.raises(ValueError):
        pp.run_phase_b(a, ex, tmp_path / "B", V2Runner())
    assert not (tmp_path / "B/diagnostics.json").exists()


def test_v1_manifest_and_ledger_unchanged_by_v2_fields(phase_a, tmp_path):
    m = pp.run_phase_b(phase_a, EXAMPLES, tmp_path / "B", Runner(), nonce_factory=lambda gen=nonces(): next(gen))
    assert "display" not in m and "diagnostic_schema" not in m
    reserved = json.loads((tmp_path / "B/attempts.jsonl").read_text().splitlines()[0])
    assert "display" not in reserved and "diagnostic_schema" not in reserved
    diags = json.loads((tmp_path / "B/diagnostics.json").read_text())
    assert {d["schema_version"] for d in diags.values()} == {"public-diagnostic-v1"}


def test_cli_display_flag_parsed_and_passed(phase_a, tmp_path, no_sandbox, monkeypatch):
    got = {}
    monkeypatch.setattr(pp, "run_phase_b", lambda *a, **k: got.update(k) or {})
    from experiments.landmark import grade
    monkeypatch.setattr(grade, "verify_attestation", lambda path: {k: True for k in pp.ATTESTATION_FIELDS} | {"checks": [{"name": "x"}]})
    att = tmp_path / "att.json"
    att.write_text("{}")
    pp.main(["--initial-dir", str(phase_a), "--examples", str(EXAMPLES), "--out", str(tmp_path / "B"),
             "--attestation", str(att), "--real", "--display", "v2"])
    assert got["display"] == "v2"
    pp.main(["--initial-dir", str(phase_a), "--examples", str(EXAMPLES), "--out", str(tmp_path / "B"),
             "--attestation", str(att), "--real"])
    assert got["display"] == "v1"
    with pytest.raises(SystemExit):
        pp.main(["--initial-dir", str(phase_a), "--examples", str(EXAMPLES), "--out", str(tmp_path / "B"),
                 "--attestation", str(att), "--real", "--display", "v3"])
