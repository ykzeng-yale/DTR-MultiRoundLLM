"""MRL-24 criterion 5: portable v2 package and meaningful leakage checks. Static only; nothing is executed."""
import ast
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_e14_release_v2 as b2  # noqa: E402
import e14_connected_mock as cm  # noqa: E402

V2 = ROOT / "experiments/landmark/e14_release_v2"
V1 = ROOT / "experiments/landmark/e14_release"
SOURCES = [ROOT / b2.DEFAULT_SOURCE_FILE, ROOT / b2.ALT_SOURCE_FILE]


def test_identical_bytes_at_both_cache_locations_give_the_same_package(tmp_path):
    present = [p for p in SOURCES if p.is_file()]
    if len(present) < 2:
        pytest.skip("both cache locations are needed on this host to test portability")
    a, b = tmp_path / "a", tmp_path / "b"
    b2.build(a, source_path=present[0])
    b2.build(b, source_path=present[1])
    for name in sorted(p.name for p in a.iterdir()):
        assert (a / name).read_bytes() == (b / name).read_bytes(), name


def test_no_local_cache_path_is_recorded_anywhere_in_v2():
    for f in V2.iterdir():
        text = f.read_text()
        assert "work/sources" not in text and "work/task_sources" not in text, f.name


def test_v2_rebuild_equals_committed_bytes(tmp_path):
    fresh = tmp_path / "v2"
    b2.build(fresh)
    for name in sorted(p.name for p in fresh.iterdir()):
        assert (fresh / name).read_bytes() == (V2 / name).read_bytes(), name


def test_legacy_replicate_field_removed_and_phase_limits_stated():
    cfg = json.loads((V2 / "config.json").read_text())
    assert "branch_replicates" not in cfg
    assert cfg["e14"]["draws_per_arm"] == 6 and cfg["e14"]["legacy_fields_removed"] == ["branch_replicates"]
    assert cfg["e14"]["phase_limits_seconds"] == {"setup": 600, "collection": 480, "private_grading": 300,
                                                 "analysis": 300, "outer": 2700}
    assert cfg["max_seconds"] == 480


def test_v1_package_is_preserved_and_still_carries_its_known_defect():
    """v1 is historical: unchanged bytes, and its inherited field is exactly what v2 repairs."""
    assert json.loads((V1 / "config.json").read_text())["branch_replicates"] == 2


def test_connected_path_accepts_the_real_v2_package(tmp_path):
    tasks = [json.loads(x) for x in (V2 / "tasks.jsonl").read_text().splitlines() if x.strip()]
    inv = {"complete": True, "roots": {t["root_id"]: {"labels": [], "numeric": []} for t in tasks}}
    binding = cm.load_release(V2, ROOT / "docs/e14_lead_measurement_spec_20260923.json",
                              cm.committed_manifest_sha256())
    slots, _ = cm.plan_slots(binding, inv)
    assert len(slots) == 130


# ---- leakage: decode every public field and compare against PARSED private content, not serialized strings
def _private_atoms():
    atoms = set()
    for line in (V2 / "private_specs.jsonl").read_text().splitlines():
        spec = json.loads(line)
        for a in spec["private_assertions"]:
            test = ast.parse(a).body[0].test
            atoms.add(ast.unparse(test.left))                # the private call, canonical form
    return atoms


def _public_texts(pkg):
    out = []
    for line in (pkg / "tasks.jsonl").read_text().splitlines():
        t = json.loads(line)                                 # decoded, so escaping cannot hide content
        out += [t["prompt"], t["public_context"]]
    pub = json.loads((pkg / "public_examples_v3.json").read_text())
    for entry in pub["cases"]:
        for c in entry["cases"]:
            out.append(c["args_literal"])
    return out


def _canon(text):
    return "".join(text.split())


def test_no_private_call_appears_in_any_decoded_public_field():
    public = _canon(" ".join(_public_texts(V2)))
    for atom in _private_atoms():
        assert _canon(atom) not in public, atom


def test_leak_check_catches_a_deliberate_re_represented_leak(tmp_path):
    """Plant a private call in a public field with different spacing and JSON escaping; the check must see it."""
    import shutil
    pkg = tmp_path / "leaky"
    shutil.copytree(V2, pkg)
    atom = sorted(_private_atoms())[0]
    rows = [json.loads(x) for x in (pkg / "tasks.jsonl").read_text().splitlines() if x.strip()]
    rows[0]["public_context"] += "\n" + atom.replace(", ", " ,  ")      # re-spaced
    (pkg / "tasks.jsonl").write_text("".join(json.dumps(r, ensure_ascii=True) + "\n" for r in rows))
    public = _canon(" ".join(_public_texts(pkg)))
    assert _canon(atom) in public


def test_grading_phase_limit_is_reconciled_between_manifest_and_config():
    """v1 carried grading_seconds 600 against a 300 s grading phase; v2 states one governing value."""
    m = json.loads((V2 / "release_manifest.json").read_text())
    cfg = json.loads((V2 / "config.json").read_text())
    assert m["grading_limits"]["grading_seconds"] == cfg["e14"]["phase_limits_seconds"]["private_grading"] == 300
