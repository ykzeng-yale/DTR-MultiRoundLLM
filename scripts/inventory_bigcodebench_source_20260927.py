#!/usr/bin/env python3
"""MRL-41: data-only inventory of the lead-supplied BigCodeBench v0.1.4 files (local files only).

docs/population_source_inquiry_20260927.md (local-files scope 425c2de). No network, download, installation, import of dataset
code, benchmark/reference/test execution or model call. Standard library only. Verifies the lead's acquisition manifest byte
for byte, reads the public dataset card, code licence and requirements as text, checks the Parquet container markers, and
probes (without importing) whether an installed Parquet reader exists. If none is installed, the row-level inventory is
reported as blocked rather than produced by other means. Library names are metadata, not family labels, and no licence
clearance for dependencies is inferred.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path

VERSION = "bigcodebench-source-inventory-v1"
SOURCE_DIR = Path("work/task_sources/bigcodebench_v014_20260927")
COMMITTED_RECEIPT = Path("results/bigcodebench_source_acquisition_20260927.json")
EXPECTED_FILES = ("dataset_README.md", "v0.1.4.parquet", "code_LICENSE", "requirements-eval.txt", "requirements.txt")
PINNED_REVISIONS = {"dataset": "b74c0d0bf70d2c0bc459be537895cca163007f1a", "code": "09dd993f46c3fbf3a799465bb96d524edcb0b199"}
PARQUET_READERS = ("pyarrow", "fastparquet")


class InventoryRefused(ValueError):
    """Manifest, file or structure verification failed; nothing is written."""


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def verify_manifest(source_dir: Path, receipt: dict, committed: dict | None) -> list:
    if committed is not None and committed != receipt:
        raise InventoryRefused("local acquisition.json differs from the committed lead receipt")
    files = receipt.get("files")
    if not isinstance(files, list) or sorted(f.get("name") for f in files) != sorted(EXPECTED_FILES):
        raise InventoryRefused("manifest does not list exactly the five pinned files")
    out = []
    for f in files:
        url = f.get("url", "")
        rev = PINNED_REVISIONS["dataset"] if "huggingface.co" in url else PINNED_REVISIONS["code"]
        if rev not in url:
            raise InventoryRefused(f"{f['name']}: URL is not at the pinned revision")
        if f.get("status") != "complete":
            raise InventoryRefused(f"{f['name']}: acquisition status {f.get('status')!r}")
        try:
            data = (source_dir / f["name"]).read_bytes()
        except OSError as e:
            raise InventoryRefused(f"{f['name']}: missing or unreadable ({type(e).__name__})") from None
        if len(data) != f["bytes"] or sha256_bytes(data) != f["sha256"]:
            raise InventoryRefused(f"{f['name']}: bytes or sha256 differ from the manifest")
        out.append({"name": f["name"], "url": url, "revision": rev, "bytes": len(data), "sha256": f["sha256"], "verified": True})
    return out


def parquet_container(data: bytes) -> dict:
    """Container markers only: leading/trailing 'PAR1' and the declared footer length. No page or Thrift decoding."""
    ok = len(data) >= 12 and data[:4] == b"PAR1" and data[-4:] == b"PAR1"
    if not ok:
        raise InventoryRefused("parquet container markers missing")
    footer_len = int.from_bytes(data[-8:-4], "little")
    if not 0 < footer_len < len(data) - 8:
        raise InventoryRefused("parquet footer length out of range")
    return {"magic_start_end": "PAR1", "footer_length_bytes": footer_len, "file_bytes": len(data)}


def parse_card(text: str) -> dict:
    """Minimal line parser for the card's YAML front matter (no YAML library is installed): licence, features, splits."""
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        raise InventoryRefused("dataset card has no YAML front matter")
    front = m.group(1)
    lic = re.search(r"^license:\s*(\S+)\s*$", front, re.M)
    features = re.findall(r"^\s*- name: (\S+)\n\s*dtype: (\S+)\s*$", front, re.M)
    splits = [{"name": n, "num_bytes": int(b), "num_examples": int(e)}
              for n, b, e in re.findall(r"^\s*- name: (\S+)\n\s*num_bytes: (\d+)\n\s*num_examples: (\d+)\s*$", front, re.M)]
    if not lic or not features or not splits:
        raise InventoryRefused("dataset card front matter lacks licence, features or splits")
    return {"license_declared_by_card": lic.group(1), "features_declared": [{"name": n, "dtype": d} for n, d in features],
            "splits_declared": splits,
            "note": "publisher declarations from the card front matter, not counts verified from the Parquet rows"}


def parse_requirements(text: str) -> dict:
    entries = [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]
    names = [re.split(r"[=<>!~ ]", e, maxsplit=1)[0] for e in entries]
    norm = [n.lower().replace("_", "-") for n in names]
    dup = sorted({n for n in norm if norm.count(n) > 1})
    return {"n_entries": len(entries), "n_distinct_names_case_insensitive": len(set(norm)), "entries": entries,
            "duplicate_names_case_insensitive": dup,
            "note": "dependency metadata only; no licence clearance or installability is inferred"}


def reader_probe() -> dict:
    found = {name: importlib.util.find_spec(name) is not None for name in PARQUET_READERS}
    return {"probed_without_import": found, "any_available": any(found.values())}


def build(source_dir: Path, committed: dict | None) -> dict:
    try:
        receipt = json.loads((source_dir / "acquisition.json").read_bytes())
    except (OSError, ValueError) as e:
        raise InventoryRefused(f"acquisition.json unreadable ({type(e).__name__})") from None
    files = verify_manifest(source_dir, receipt, committed)
    card = parse_card((source_dir / "dataset_README.md").read_text(encoding="utf-8"))
    container = parquet_container((source_dir / "v0.1.4.parquet").read_bytes())
    lic_head = (source_dir / "code_LICENSE").read_text(encoding="utf-8").strip().splitlines()[:2]
    probe = reader_probe()
    v014 = [s for s in card["splits_declared"] if s["name"] == "v0.1.4"]
    return {
        "version": VERSION, "request": "MRL-41", "scope": "local files supplied by the lead (425c2de); no network, install or execution",
        "manifest_verification": {"files": files, "total_bytes": sum(f["bytes"] for f in files),
                                  "local_acquisition_json_equals_committed_receipt": committed is not None},
        "dataset_card": card, "declared_v014_split": v014[0] if v014 else None,
        "licences": {"dataset_card_license_field": card["license_declared_by_card"],
                     "code_LICENSE_first_lines": [line.strip() for line in lic_head],
                     "note": "dataset and code licences recorded separately; no clearance for dependencies is inferred"},
        "requirements": {"requirements.txt": parse_requirements((source_dir / "requirements.txt").read_text(encoding="utf-8")),
                         "requirements-eval.txt": parse_requirements((source_dir / "requirements-eval.txt").read_text(encoding="utf-8"))},
        "parquet_container": container,
        "parquet_reader": probe,
        "row_level_inventory": ({"status": "blocked_no_installed_parquet_reader",
                                 "not_installed_per_contract": True,
                                 "not_produced": ["exact row count from the file", "schema/types from the file", "unique/duplicate task IDs",
                                                  "duplicate complete/instruct prompt hashes", "entry-point counts",
                                                  "declared library sets and frequencies", "missing fields"],
                                 "unblocking_options_for_the_lead": ["authorize an isolated installation of a Parquet reader",
                                                                     "or supply an installed reader or a lead-converted export"]}
                                if not probe["any_available"] else
                                {"status": "reader_available_but_row_inventory_not_implemented_in_this_delivery"}),
        "compatibility_questions_from_static_text": [
            "Tests are declared as unittest source ('test' field; the card describes unittest-based tests), whereas the current public "
            "diagnostic takes one assert-style literal public case. Deriving a public case would need an explicit new contract.",
            "requirements-eval.txt lists 74 pinned entries (71 distinct names; requests, statsmodels and xlrd repeated) (for example tensorflow 2.11, keras, selenium, django, flask, "
            "requests, matplotlib, pandas 2.0.3, numpy 1.21.2). The strict sandbox's pinned interpreter has none of them, and numpy 1.21.2 "
            "predates the project's Python 3.12. Installability and version conflicts are unknown; nothing was installed.",
            "Some pinned packages (requests, selenium, wikipedia, sendgrid, dnspython, requests_mock, pyfakefs) suggest network, browser or "
            "file-system interaction. The sandbox denies network and restricts writes; which tasks depend on these is unknown without the rows.",
            "Return values for library tasks (for example DataFrames, plots, arrays) are unknown from static text. The diagnostic-v2 display "
            "policy bounds literals only; expected-value compatibility cannot be judged without reading, not executing, the rows.",
            "Complete and Instruct prompt variants of one task must stay together; which variant and what public information would be "
            "permitted is an open estimand decision for the lead.",
        ],
        "not_claimed": ["no task is declared eligible", "library names are not family labels",
                        "card counts are publisher declarations, not verified row counts"],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = Path(a.out)
    if out.exists():
        print(f"refused: {out} already exists (never overwritten)")
        return 2
    try:
        committed = json.loads(COMMITTED_RECEIPT.read_bytes())
        doc = build(SOURCE_DIR, committed)
    except (InventoryRefused, OSError, ValueError) as e:
        print(f"refused: {e}")
        return 2
    doc["script_sha256"] = sha256_bytes(Path(__file__).read_bytes())
    with open(out, "x", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, sort_keys=True, indent=1) + "\n")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
