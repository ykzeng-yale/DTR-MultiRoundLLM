"""E13a release bindings (MRL-19 deliverable 1). EVIDENCE CLASS: none - bindings and guards only.

Source/mock only: nothing here calls a receiver or model, executes a candidate/reference/control program,
starts the sandbox or touches the network. The frozen dev_release_v3 package and results/ are read, never
written. What is checked: the builder is deterministic and the committed bytes are its output; the five
checkpoint rows (and their private assertions) are the frozen rows byte for byte; grade.validate_specs still
accepts the five-root package; study_adapter loads the new grading limits and gives the new allowlisted
manifest the identical committed-hash check (a non-allowlisted path and tampered bytes stay refused).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

sys.path.insert(0, str(ROOT / "scripts"))
import build_e13a_release as builder  # noqa: E402
from experiments.landmark import grade, study_adapter as sa  # noqa: E402
from experiments.landmark.collect import digest, file_sha  # noqa: E402

RELEASE = ROOT / "experiments/landmark/e13a_release"
SOURCE = ROOT / "experiments/landmark/dev_release_v3"
MANIFEST_REL = "experiments/landmark/e13a_release/release_manifest.json"
ROOTS = ["mbpp/842", "mbpp/288", "mbpp/863", "mbpp/966", "mbpp/652"]
PACKAGE = ("tasks.jsonl", "private_specs.jsonl", "public_examples_v3.json", "controls_rationale.json", "config.json")


def _manifest():
    return json.loads((RELEASE / "release_manifest.json").read_text())


def _lines(path):
    return {json.loads(line)["root_id"]: line for line in Path(path).read_bytes().split(b"\n") if line.strip()}


def _records(path, key):
    return {r["root_id"]: r for r in json.loads(Path(path).read_text())[key]}


def _specs():
    return [json.loads(l) for l in (RELEASE / "private_specs.jsonl").read_text().splitlines() if l.strip()]


def _tasks():
    return [json.loads(l) for l in (RELEASE / "tasks.jsonl").read_text().splitlines() if l.strip()]


def test_release_exists_with_the_five_roots_in_assignment_order():
    assert [t["root_id"] for t in _tasks()] == ROOTS
    assert [s["root_id"] for s in _specs()] == ROOTS
    m = _manifest()
    assert m["roots"] == ROOTS and m["n_roots"] == 5 and m["manifest"] == "e13a-two-arm-release"
    assert m["stage"]["arms"] == {"R1": [2, 3, 4, 5, 6, 7], "FRESH": [0, 1, 2, 3, 4, 5]}
    assert m["stage"]["requests"] == 60
    assert (m["stage"]["contrast"]["treatment"], m["stage"]["contrast"]["reference"]) == ("R1", "FRESH")


def test_rebuild_is_deterministic_and_equals_the_committed_bytes(tmp_path):
    a, b = tmp_path / "a" / "e13a_release", tmp_path / "b" / "e13a_release"
    builder.build(a)
    builder.build(b)
    names = sorted(p.name for p in a.iterdir())
    assert names == sorted(p.name for p in b.iterdir()) == sorted(p.name for p in RELEASE.iterdir())
    for n in names:
        assert (a / n).read_bytes() == (b / n).read_bytes(), f"rebuild is not deterministic: {n}"
        assert (a / n).read_bytes() == (RELEASE / n).read_bytes(), (
            f"committed {n} is not the builder's output; rerun scripts/build_e13a_release.py after editing "
            f"a grading source (expected_source_hashes/expected_contract_sha256 are live pins)")
    assert builder.verify(RELEASE)["verified"] is True


def test_builder_refuses_to_overwrite(tmp_path):
    out = tmp_path / "e13a_release"
    builder.build(out)
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        builder.build(out)
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        builder.main(["--out", str(out)])


def test_rows_are_byte_identical_to_dev_release_v3():
    for name in ("tasks.jsonl", "private_specs.jsonl"):
        src, new = _lines(SOURCE / name), _lines(RELEASE / name)
        assert set(new) == set(ROOTS)
        for r in ROOTS:
            assert new[r] == src[r], f"{name} row for {r} is not the frozen line bytes"
    for name, key in (("public_examples_v3.json", "cases"), ("controls_rationale.json", "controls")):
        src, new = _records(SOURCE / name, key), _records(RELEASE / name, key)
        assert set(new) == set(ROOTS)
        for r in ROOTS:
            assert digest(new[r]) == digest(src[r]) and new[r] == src[r], f"{name} record for {r} changed"
        assert json.loads((RELEASE / name).read_text())["version"] == json.loads((SOURCE / name).read_text())["version"]
    assert (RELEASE / "config.json").read_bytes() == (SOURCE / "config.json").read_bytes()


def test_private_assertions_and_controls_unchanged():
    src = {json.loads(l)["root_id"]: json.loads(l) for l in (SOURCE / "private_specs.jsonl").read_text().splitlines() if l.strip()}
    for spec in _specs():
        s = src[spec["root_id"]]
        for field in ("private_assertions", "public_assertions", "negative_controls", "reference_code", "preamble",
                      "entry_point", "public_task_sha256"):
            assert spec[field] == s[field], f"{field} changed for {spec['root_id']}"
        assert len(spec["private_assertions"]) == 2 and spec["negative_controls"]


def test_grade_validate_specs_accepts_the_five_root_package():
    grade.validate_specs(_tasks(), _specs())  # raises on any contract violation
    assert _manifest()["grading_bindings"]["expected_contract_sha256"] == digest(grade.contract(_specs()))
    assert _manifest()["evaluator"]["grader_version"] == grade.GRADER_VERSION


def test_release_bindings_load_and_package_hashes_hold():
    m = _manifest()
    for name in PACKAGE:
        assert m["package"][name] == file_sha(RELEASE / name)
    b = sa.load_release_bindings(RELEASE / "release_manifest.json", RELEASE / "private_specs.jsonl")
    assert b["frozen_tasks_path"] == RELEASE / "tasks.jsonl"
    assert b["frozen_tasks_sha256"] == file_sha(RELEASE / "tasks.jsonl")
    assert sa.manifest_diagnostic_schema((RELEASE / "release_manifest.json").read_bytes()) == "public-diagnostic-v2"


def test_grading_limits_load_with_containment_starts():
    data = (RELEASE / "release_manifest.json").read_bytes()
    lim = sa.load_grading_limits(data, _specs())
    assert (lim["artifact_starts"], lim["recheck_starts"], lim["containment_starts"]) == (60, 10, 9)
    assert (lim["max_private_starts"], lim["grading_seconds"], lim["seconds_cap"]) == (79, 300, 300)
    assert lim["source"] == "grading_limits"
    assert lim["artifact_starts"] == 5 * 2 * 6
    with pytest.raises(ValueError, match="n_roots"):
        sa.load_grading_limits(data, _specs()[:4])


def test_containment_starts_is_additive_and_no_ceiling_is_relaxed():
    """The optional field cannot smuggle starts past the 200 ceiling or past the artifact+recheck identity."""
    assert sa.MAX_PRIVATE_STARTS == 200 and sa.MAX_GRADING_SECONDS == 600
    base = {"n_roots": 1, "artifact_starts": 60, "recheck_starts": 10, "containment_starts": 9,
            "max_private_starts": 79, "grading_seconds": 300}
    assert sa.load_grading_limits(json.dumps({"grading_limits": base}).encode())["containment_starts"] == 9
    v3 = {k: v for k, v in base.items() if k != "containment_starts"} | {"max_private_starts": 70}
    assert sa.load_grading_limits(json.dumps({"grading_limits": v3}).encode())["containment_starts"] == 0
    for bad in ({**base, "max_private_starts": 70},                                    # containment not counted
                {**base, "containment_starts": -1},
                {**base, "artifact_starts": 150, "recheck_starts": 40, "containment_starts": 11,
                 "max_private_starts": 201},                                            # over the 200 ceiling
                {**base, "grading_seconds": 601},
                {**base, "containment_starts": "9"},
                {**base, "extra": 1}):
        with pytest.raises(ValueError, match="grading_limits"):
            sa.load_grading_limits(json.dumps({"grading_limits": bad}).encode())


def _tracked(rel):
    return subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", f"HEAD:{rel}"], capture_output=True).returncode == 0


def test_new_manifest_is_allowlisted_and_gets_the_same_committed_check(tmp_path):
    assert MANIFEST_REL in sa.COMMITTED_RELEASE_MANIFESTS
    path = ROOT / MANIFEST_REL
    data = path.read_bytes()
    if _tracked(MANIFEST_REL):
        assert sa.verify_committed_release(path, data) == hashlib.sha256(data).hexdigest()
    else:  # not committed yet: the allowlist entry buys no exemption
        with pytest.raises(ValueError, match="HEAD"):
            sa.verify_committed_release(path, data)


def test_non_allowlisted_and_tampered_manifests_are_refused(tmp_path):
    copy = tmp_path / "release_manifest.json"
    copy.write_bytes((RELEASE / "release_manifest.json").read_bytes())
    for bad in (copy, ROOT / "experiments/landmark/e13a_stage.json",
                ROOT / "experiments/landmark/e13a_release/tasks.jsonl"):
        with pytest.raises(ValueError, match="committed"):
            sa.verify_committed_release(bad)
    tampered = json.loads((RELEASE / "release_manifest.json").read_text())
    tampered["grading_limits"]["max_private_starts"] = 999
    with pytest.raises(ValueError, match="HEAD"):  # bytes that are not the HEAD blob (or no blob at all)
        sa.verify_committed_release(ROOT / MANIFEST_REL, json.dumps(tampered).encode())


def test_dev_release_v3_bytes_unchanged_on_disk():
    src = json.loads((SOURCE / "release_manifest.json").read_text())
    for name, want in src["package"].items():
        assert file_sha(SOURCE / name) == want, f"frozen dev_release_v3 file changed: {name}"
    pins = _manifest()["source_release"]
    assert pins["manifest_sha256"] == file_sha(SOURCE / "release_manifest.json")
    for name, want in pins["files"].items():
        assert file_sha(SOURCE / name) == want
    assert pins["assignment_table_sha256"] == src["assignment_table_sha256"]


def test_manifest_pins_sources_and_authorizes_nothing():
    m = _manifest()
    auth = m["authorization"]
    assert (auth["receiver_calls_authorized"], auth["candidate_executions_authorized"]) == (0, 0)
    assert auth["benchmark_executions_authorized"] == 0 and auth["paid_usd_authorized"] == 0
    assert "authorizes NO receiver" in auth["statement"] and "NO candidate" in auth["statement"]
    stage = ROOT / "experiments/landmark/e13a_stage.json"
    assert m["stage"]["descriptor_sha256"] == file_sha(stage)
    plan = ROOT / m["request_plan"]["path"]
    assert m["request_plan"]["sha256"] == file_sha(plan)
    run = ROOT / m["e12_conditioning"]["run_dir"]
    for name, want in m["e12_conditioning"]["artifacts"].items():
        assert file_sha(run / name) == want
    assert set(m["e12_conditioning"]["artifacts"]) == {"A/roots.jsonl", "B/diagnostics.json"}
    assert m["e12_conditioning"]["private_grades_are_an_input"] is False
    assert m["model"] == json.loads((SOURCE / "release_manifest.json").read_text())["model"]
    assert m["builder"]["script_sha256"] == file_sha(ROOT / "scripts/build_e13a_release.py")
    for root, prov in m["source_release"]["row_provenance"].items():
        assert prov["tasks_row_sha256"] == digest(next(t for t in _tasks() if t["root_id"] == root))
        assert prov["private_spec_row_sha256"] == digest(next(s for s in _specs() if s["root_id"] == root))


def test_builder_refuses_a_drifted_frozen_source(tmp_path):
    """A changed source byte is a refusal, not a silent copy: the frozen manifest's hashes gate every input."""
    fake = tmp_path / "src"
    fake.mkdir()
    for p in SOURCE.iterdir():
        if p.is_file():
            (fake / p.name).write_bytes(p.read_bytes())
    (fake / "tasks.jsonl").write_bytes((fake / "tasks.jsonl").read_bytes() + b'{"root_id": "mbpp/1"}\n')
    with pytest.raises(ValueError, match="frozen source file changed"):
        builder.build(tmp_path / "out", source_dir=fake)
    assert not (tmp_path / "out").exists()


def test_builder_refuses_a_stage_root_set_that_is_not_the_five(tmp_path):
    stage = json.loads((ROOT / "experiments/landmark/e13a_stage.json").read_text())
    stage["roots"] = stage["roots"][:4]
    p = tmp_path / "stage.json"
    p.write_text(json.dumps(stage))
    with pytest.raises(ValueError, match="distinct roots"):
        builder.build(tmp_path / "out", stage_path=p)
    stage["roots"] = ["mbpp/288", "mbpp/842", "mbpp/863", "mbpp/966", "mbpp/652"]  # reordered vs the plan
    p.write_text(json.dumps(stage))
    with pytest.raises(ValueError, match="request plan roots"):
        builder.build(tmp_path / "out2", stage_path=p)
