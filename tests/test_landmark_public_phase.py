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
    def __init__(self):
        self.programs = []

    def __call__(self, program, **limits):
        compile(program, "<public-harness>", "exec")  # compiled only, never executed
        assert limits == {"timeout_s": 10, "cpu_seconds": 5, "output_cap": 65536}
        if "def broken(" in program or "y=2" in program:
            raise AssertionError("runner called for a format-error artifact")
        self.programs.append(program)
        nonce = re.search(re.escape(pc.PUBLIC_STARTED) + r"([0-9a-f]+)", program).group(1)
        return {"stdout": tpc.out(*(tpc.line(i, "wrong_value", 0, "int", nonce=nonce) for i in range(3)), nonce=nonce),
                "returncode": 0, "timed_out": False}


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
    assert set(m["executor_source_sha256"]) == {"public_check.py", "diagnostic.py", "sandbox.py", "grade.py"}
    assert m["executor_source_sha256"]["public_check.py"] == hashlib.sha256(Path(pc.__file__).read_bytes()).hexdigest()
    written = raw + (tmp_path / "B/manifest.json").read_bytes()
    assert all(f"{i:032x}".encode() not in written for i in range(len(SPEC)))
    # The continue phase accepts exactly these bytes under the manifest's SHA-256.
    done = cd.run_continue(config(), TASKS, phase_a, tmp_path / "B/diagnostics.json", tmp_path / "C",
                           expected_diagnostics_sha256=m["diagnostics_sha256"], adapter=tcd.Fake(),
                           public_examples={c["root_id"]: c for c in SPEC})
    assert done["diagnostics_sha256"] == m["diagnostics_sha256"]


def test_works_without_validate_diagnostic(phase_a, tmp_path, monkeypatch):
    # A diagnostic module that does not expose validate_diagnostic (the driver looks it up by attribute).
    bare = types.SimpleNamespace(build_diagnostic=diagnostic.build_diagnostic, diagnostic_bytes=diagnostic.diagnostic_bytes)
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
