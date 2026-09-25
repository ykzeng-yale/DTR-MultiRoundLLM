"""Source-only tests for the dev_release_v3 builder (no candidate/reference/control is executed)."""
import ast
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import build_dev_release_v3 as b  # noqa: E402
from experiments.landmark import grade  # noqa: E402
from experiments.common.integrity import hack_gate  # noqa: E402

PKG = ROOT / "experiments/landmark/dev_release_v3"
NAMES = ("tasks.jsonl", "private_specs.jsonl", "public_examples_v3.json", "controls_rationale.json",
         "exclusions.json", "overlap_audit.json", "BUILD_NOTES.md")


@pytest.fixture(scope="module")
def files():
    if not b.MBPP.is_file():  # LEAD-PORT-01: explicit skip on a clean checkout; the builder itself fails closed
        pytest.skip("pinned MBPP source cache absent (work/ is gitignored); acquire and verify it with docs/mbpp_source_acquisition_20260925.md. A skip does NOT reproduce the committed package")
    return b.build()


def test_builder_fails_closed_without_the_pinned_source(tmp_path, monkeypatch):
    monkeypatch.setattr(b, "MBPP", tmp_path / "absent.jsonl")
    with pytest.raises(FileNotFoundError):
        b.build()


def test_builder_fails_closed_on_a_wrong_source_hash(tmp_path, monkeypatch):
    bogus = tmp_path / "mbpp.jsonl"
    bogus.write_text('{"task_id": 1}\n')
    monkeypatch.setattr(b, "MBPP", bogus)
    with pytest.raises(SystemExit, match="hash mismatch"):
        b.build()


def _jsonl(text):
    return [json.loads(l) for l in text.splitlines() if l.strip()]


PACKAGE_BUILD_COMMIT = "9d4a1f2"  # dev_release_v3 was built and committed here; later lead doc edits must not break it


def test_deterministic_and_matches_committed_package(files):
    """Rebuild is deterministic and equals the committed package. The one provenance field that hashes the
    (lead-editable) release document is checked against that document's bytes at the package build commit,
    not the current file, so later documentation amendments cannot make the frozen package look changed."""
    import hashlib, subprocess
    assert b.build() == files
    assert set(files) == set(NAMES)
    for name in NAMES:
        committed = (PKG / name).read_text()
        if name != "exclusions.json":
            assert committed == files[name], name
            continue
        c, f = json.loads(committed), json.loads(files[name])
        blob = subprocess.check_output(["git", "show", f"{PACKAGE_BUILD_COMMIT}:docs/e12_bundled_release_20260922.md"], cwd=ROOT)
        assert c["sources"]["bundled_release_sha256"] == hashlib.sha256(blob).hexdigest()
        c["sources"].pop("bundled_release_sha256"); f["sources"].pop("bundled_release_sha256")
        assert c == f, name


def test_refuses_to_overwrite(tmp_path):
    with pytest.raises(SystemExit):
        b.main(["--out", str(tmp_path)])


def test_roster_order_and_held_accounting(files):
    tasks = _jsonl(files["tasks.jsonl"])
    exc = json.loads(files["exclusions.json"])
    retained = [t["root_id"] for t in tasks]
    assert exc["retained"] == retained and exc["n_retained"] == len(retained)
    held = {h["root_id"] for h in exc["held"]}
    assert [r for r in (f"mbpp/{t}" for t in b.ROSTER) if r not in held] == retained
    assert len(retained) + len(held) == 14 and len(retained) == 14


def test_specs_validate_and_bind(files):
    tasks, specs = _jsonl(files["tasks.jsonl"]), _jsonl(files["private_specs.jsonl"])
    grade.validate_specs(tasks, specs)
    assert [s["root_id"] for s in specs] == [t["root_id"] for t in tasks]
    for s in specs:
        assert set(s) == grade.SPEC_KEYS and s["public_assertions"] == [] and s["preamble"] == []
        assert len(s["negative_controls"]) == 1


def test_controls_compile_pass_hack_gate_and_predicted_to_fail(files):
    specs = _jsonl(files["private_specs.jsonl"])
    rat = {r["root_id"]: r for r in json.loads(files["controls_rationale.json"])["controls"]}
    for s in specs:
        code = s["negative_controls"][0]["code"]
        compile(code, "<control>", "exec")
        assert hack_gate(code, s["entry_point"]) == []
        r = rat[s["root_id"]]
        assert [c["assertion"] for c in r["private_cases"]] == s["private_assertions"]
        assert r["predicted_failing_private_assertions"] >= 1
        for c in r["private_cases"]:
            assert c["predicted_fails"] == (c["predicted_control_return"] != c["expected"])


def test_no_private_text_in_public_material(files):
    specs = _jsonl(files["private_specs.jsonl"])
    public = re.sub(r"\s+", "", files["tasks.jsonl"] + files["public_examples_v3.json"])
    for s in specs:
        for a in s["private_assertions"]:
            assert re.sub(r"\s+", "", a) not in public


def test_public_examples_shape_and_source(files):
    pub = json.loads(files["public_examples_v3.json"])
    assert pub["version"] == "public-examples-v3"
    tasks = _jsonl(files["tasks.jsonl"])
    assert [c["root_id"] for c in pub["cases"]] == [t["root_id"] for t in tasks]
    for entry, task in zip(pub["cases"], tasks):
        assert set(entry) == {"root_id", "entry_point", "cases"} and len(entry["cases"]) == 1
        case = entry["cases"][0]
        assert set(case) == {"case_id", "args_literal", "expected_literal"}
        assert case["case_id"] == f"public-{entry['root_id'].split('/')[1]}-1"
        assert type(ast.literal_eval(case["args_literal"])) is list
        assert task["public_context"].startswith("Required function interface: def ")


def test_overlap_audit_present(files):
    audit = json.loads(files["overlap_audit.json"])
    roots = {r["root_id"]: r for r in audit["roots"]}
    assert list(roots) == [t["root_id"] for t in _jsonl(files["tasks.jsonl"])]
    assert roots["mbpp/154"]["shared_argument_positions"]
    assert "matrix" in roots["mbpp/154"]["review_semantic_note"]
