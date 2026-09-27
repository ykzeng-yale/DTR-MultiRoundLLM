"""MRL-41 tests for the local-files BigCodeBench inventory builder. Synthetic fixtures plus an optional read-only check of the
lead-supplied files. No network, installation, dataset-code import or execution."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("bcb", ROOT / "scripts/inventory_bigcodebench_source_20260927.py")
bcb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bcb)
DS, CODE = bcb.PINNED_REVISIONS["dataset"], bcb.PINNED_REVISIONS["code"]
CARD = ("---\nlicense: apache-2.0\ndataset_info:\n  features:\n  - name: task_id\n    dtype: string\n  - name: libs\n    dtype: string\n"
        "  splits:\n  - name: v0.1.4\n    num_bytes: 100\n    num_examples: 3\n---\n# card\n")
PARQUET = b"PAR1" + b"\x00" * 20 + (10).to_bytes(4, "little") + b"PAR1"
FILES = {"dataset_README.md": CARD.encode(), "v0.1.4.parquet": PARQUET, "code_LICENSE": b"   Apache License\n  Version 2.0\n",
         "requirements-eval.txt": b"numpy==1.21.2\nxlrd==2.0.1\nxlrd==2.0.1\nRequests==2.31.0\nrequests==2.31.0\n",
         "requirements.txt": b"fire>=0.6.0\n"}


def make(tmp_path, files=None, mutate=None):
    files = dict(FILES if files is None else files)
    for name, data in files.items():
        (tmp_path / name).write_bytes(data)
    receipt = {"files": [{"name": n, "bytes": len(d), "sha256": hashlib.sha256(d).hexdigest(), "status": "complete",
                          "url": (f"https://huggingface.co/datasets/x/resolve/{DS}/{n}" if n in ("dataset_README.md", "v0.1.4.parquet")
                                  else f"https://raw.githubusercontent.com/x/{CODE}/{n}")} for n, d in FILES.items()]}
    if mutate:
        mutate(receipt)
    (tmp_path / "acquisition.json").write_text(json.dumps(receipt))
    return receipt


def test_synthetic_inventory_and_blocked_row_level_status(tmp_path, monkeypatch):
    receipt = make(tmp_path)
    monkeypatch.setattr(bcb.importlib.util, "find_spec", lambda name: None)
    doc = bcb.build(tmp_path, receipt)
    assert doc["declared_v014_split"] == {"name": "v0.1.4", "num_bytes": 100, "num_examples": 3}
    assert [f["name"] for f in doc["dataset_card"]["features_declared"]] == ["task_id", "libs"]
    ev = doc["requirements"]["requirements-eval.txt"]
    assert ev["n_entries"] == 5 and ev["n_distinct_names_case_insensitive"] == 3 and ev["duplicate_names_case_insensitive"] == ["requests", "xlrd"]
    assert doc["parquet_container"] == {"magic_start_end": "PAR1", "footer_length_bytes": 10, "file_bytes": len(PARQUET)}
    assert doc["row_level_inventory"]["status"] == "blocked_no_installed_parquet_reader"
    assert doc["licences"]["dataset_card_license_field"] == "apache-2.0" and doc["licences"]["code_LICENSE_first_lines"][0] == "Apache License"
    assert all(f["verified"] for f in doc["manifest_verification"]["files"])


@pytest.mark.parametrize("mutate", [
    lambda r: r["files"][0].update(sha256="0" * 64),                       # hash mismatch
    lambda r: r["files"][1].update(bytes=1),                               # size mismatch
    lambda r: r["files"][2].update(url="https://raw.githubusercontent.com/x/main/code_LICENSE"),   # not the pinned revision
    lambda r: r["files"][3].update(status="partial"),                      # incomplete acquisition
    lambda r: r["files"].pop(),                                            # manifest missing a file
])
def test_manifest_verification_refusals(tmp_path, mutate):
    receipt = make(tmp_path, mutate=mutate)
    with pytest.raises(bcb.InventoryRefused):
        bcb.build(tmp_path, receipt)


def test_committed_receipt_mismatch_and_missing_file_are_refused(tmp_path):
    receipt = make(tmp_path)
    with pytest.raises(bcb.InventoryRefused, match="committed"):
        bcb.build(tmp_path, dict(receipt, lead="other"))
    (tmp_path / "requirements.txt").unlink()
    with pytest.raises(bcb.InventoryRefused, match="missing"):
        bcb.build(tmp_path, receipt)


@pytest.mark.parametrize("data", [b"NOPE" + b"\x00" * 20 + b"PAR1", b"PAR1" + b"\x00" * 4 + (999).to_bytes(4, "little") + b"PAR1"])
def test_parquet_container_refusals(data):
    with pytest.raises(bcb.InventoryRefused):
        bcb.parquet_container(data)


def test_card_without_front_matter_is_refused():
    with pytest.raises(bcb.InventoryRefused):
        bcb.parse_card("# no front matter\n")


def test_existing_output_is_never_overwritten(tmp_path):
    out = tmp_path / "out.json"
    out.write_text("keep")
    assert bcb.main(["--out", str(out)]) == 2 and out.read_text() == "keep"


def test_builder_is_stdlib_only_with_no_execution_or_network():
    tree = ast.parse((ROOT / "scripts/inventory_bigcodebench_source_20260927.py").read_text())
    mods = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | \
           {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert mods == {"__future__", "argparse", "hashlib", "importlib.util", "json", "re", "pathlib"}
    called = {n.func.id if isinstance(n.func, ast.Name) else n.func.attr for n in ast.walk(tree)
              if isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute))}
    assert not called & {"eval", "exec", "compile", "__import__", "import_module", "run", "Popen", "system", "urlopen", "read_parquet"}


REAL = (ROOT / bcb.SOURCE_DIR / "acquisition.json").exists() and (ROOT / bcb.COMMITTED_RECEIPT).exists()


@pytest.mark.skipif(not REAL, reason="lead-supplied files not present in gitignored work/")
def test_real_lead_supplied_files_verify():
    committed = json.loads((ROOT / bcb.COMMITTED_RECEIPT).read_bytes())
    doc = bcb.build(ROOT / bcb.SOURCE_DIR, committed)
    assert doc["manifest_verification"]["total_bytes"] == 2383786 and len(doc["manifest_verification"]["files"]) == 5
    assert doc["declared_v014_split"]["num_examples"] == 1140 and len(doc["dataset_card"]["features_declared"]) == 9
    assert doc["parquet_container"]["magic_start_end"] == "PAR1"
