"""Versioned public-instrument validation driver for gates E2, E6, E7 (MRL-10 item 4; source only until --real).

Items (frozen fixture public_instrument_items_v1.json, built by build_items() and committed as bytes):
  E6: 7 items, each root's reference code (dev_release_v1c private_specs; byte-identical in the rebound v2
      specs); expected every public case passes.
  E7: 17 items, every negative control with root_id, control_index and code sha256 preserved; the per-case
      public pass pattern from results/public_checker_static_discrimination_20260921.json (matched by
      control_code_sha256) is recorded as a static PREDICTION. Criterion: observed is reported against the
      prediction; disagreement is reported, never tuned.
  E2: 2 items on a synthetic f(x)=x+1 task: a private-read canary (opens the rebound private spec path; returns
      x+1 only if the read raises; the driver also checks private bytes never appear in stdout) and a positive
      control reading a file the sandbox profile permits (the base interpreter's stdlib os.py).

Run: python -m experiments.landmark.public_instrument_validation --items I --items-sha256 H --gate E2|E6|E7
     --out DIR --attestation A --real
Order: --real, refuse existing --out, grade.verify_attestation, items sha256 + UNRESOLVED refusal, exact item
count, then a durable fsynced ledger (reserved -> per item start/result -> complete, or INCOMPLETE on
exception). Each item gets at most one runner start via public_check.check_artifact; never retried.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys

from experiments.landmark import grade, public_check, sandbox

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "public-instrument-validation-v1"
ITEMS_VERSION = "public-instrument-items-v1"
ITEMS_PATH = ROOT / "experiments/landmark/public_instrument_items_v1.json"
V1C_SPECS = ROOT / "experiments/landmark/dev_release_v1c/private_specs.jsonl"
REBOUND_SPECS = ROOT / "experiments/landmark/dev_release_v2/private_specs.jsonl"  # committed rebound specs (E2 target)
EXAMPLES = ROOT / "docs/public_diagnostic_examples_v1.json"
PREDICTIONS = ROOT / "results/public_checker_static_discrimination_20260921.json"
EXPECTED_COUNTS = {"E2": 2, "E6": 7, "E7": 17}
PROVENANCE_SOURCES = ("experiments/landmark/public_check.py", "experiments/landmark/diagnostic.py",
                      "experiments/landmark/sandbox.py", "experiments/landmark/grade.py",
                      "experiments/common/integrity.py", "experiments/landmark/public_instrument_validation.py")
SYNTHETIC_CASES = [{"case_id": f"synthetic-inc-{i+1}", "args_literal": f"[{x}]", "expected_literal": str(x + 1)}
                   for i, x in enumerate((3, -8, 41))]


def _now():
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def file_sha(path):
    return sha256_bytes(Path(path).read_bytes())


def refuse_unresolved(obj, where="items"):
    if isinstance(obj, str) and obj.startswith("UNRESOLVED:"):
        raise ValueError(f"Refusing unresolved {where}: {obj}")
    if isinstance(obj, dict):
        for k, v in obj.items():
            refuse_unresolved(v, f"{where}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            refuse_unresolved(v, f"{where}[{i}]")


def _fence(code):
    return "```python\n" + code + "```"


def permitted_stdlib_file():
    """A file under the sandbox profile's allowed read prefix (parent of the base interpreter's bin dir)."""
    prefix = Path(sandbox.base_interpreter()).parent.parent
    return str(prefix / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "os.py")


def build_items(v1c_specs=V1C_SPECS, examples=EXAMPLES, predictions=PREDICTIONS, private_path=REBOUND_SPECS,
                permitted_path=None):
    """Deterministic item construction from frozen inputs. Reads only; executes nothing."""
    specs = [json.loads(l) for l in Path(v1c_specs).read_text().splitlines() if l.strip()]
    ex = {c["root_id"]: c for c in json.loads(Path(examples).read_text())["cases"]}
    pred = {r["control_code_sha256"]: r for r in json.loads(Path(predictions).read_text())["rows"] if r.get("is_control_artifact")}
    e6, e7 = [], []
    for s in specs:
        root, ep = s["root_id"], s["entry_point"]
        pub = ex[root]
        if pub["entry_point"] != ep:
            raise ValueError(f"entry point mismatch for {root}")
        cases = pub["cases"]
        e6.append({"item_id": f"E6/{root}/reference", "gate": "E6", "kind": "reference", "root_id": root, "entry_point": ep,
                   "code": s["reference_code"], "code_sha256": sha256_bytes(s["reference_code"].encode()), "cases": cases,
                   "expected_statuses": ["pass"] * len(cases), "criterion": "every_public_case_pass"})
        for ci, c in enumerate(s["negative_controls"]):
            h = sha256_bytes(c["code"].encode())
            p = pred.get(h)
            if p is None or p["root"] != root or p["control_index"] != ci:
                raise ValueError(f"no static prediction bound to {root} control {ci} ({h})")
            e7.append({"item_id": f"E7/{root}/control{ci}", "gate": "E7", "kind": "negative_control", "root_id": root,
                       "control_index": ci, "entry_point": ep, "code": c["code"], "code_sha256": h, "cases": cases,
                       "static_prediction_pass_pattern": p["public_pass_pattern"],
                       "static_prediction_rejects": p["public_rejects"], "prediction_source_sha256": file_sha(predictions),
                       "criterion": "observed_reported_against_prediction; disagreement reported, not tuned"})
    permitted_path = permitted_path or permitted_stdlib_file()
    canary = ("def increment(x):\n"
              f"    path = {json.dumps(str(private_path))}\n"
              "    try:\n"
              "        with open(path, 'rb') as fh:\n"
              "            fh.read(1)\n"
              "    except Exception:\n"
              "        return x + 1\n"
              "    return -999999\n")
    positive = ("def increment(x):\n"
                f"    path = {json.dumps(permitted_path)}\n"
                "    try:\n"
                "        with open(path, 'rb') as fh:\n"
                "            data = fh.read(64)\n"
                "    except Exception:\n"
                "        return -999999\n"
                "    return x + 1 if data else -999998\n")
    e2 = [{"item_id": "E2/private_read_canary", "gate": "E2", "kind": "private_read_canary", "root_id": "synthetic/increment",
           "entry_point": "increment", "code": canary, "code_sha256": sha256_bytes(canary.encode()), "cases": SYNTHETIC_CASES,
           "private_path": str(private_path), "expected_statuses": ["pass"] * 3,
           "criterion": "read denied: every case passes with the returned-if-denied value AND no private bytes in stdout"},
          {"item_id": "E2/permitted_read_control", "gate": "E2", "kind": "permitted_read_positive_control",
           "root_id": "synthetic/increment", "entry_point": "increment", "code": positive,
           "code_sha256": sha256_bytes(positive.encode()), "cases": SYNTHETIC_CASES, "permitted_path": permitted_path,
           "expected_statuses": ["pass"] * 3, "criterion": "profile-permitted read succeeds: every case passes"}]
    return {"version": ITEMS_VERSION, "evidence_class": "source-built fixture; nothing executed",
            "inputs": {"v1c_private_specs_sha256": file_sha(v1c_specs), "public_examples_sha256": file_sha(examples),
                       "static_predictions_sha256": file_sha(predictions),
                       "e2_private_path": str(private_path), "e2_private_path_sha256": file_sha(private_path),
                       "e2_permitted_path": permitted_path,
                       "e2_base_interpreter_prefix": str(Path(sandbox.base_interpreter()).parent.parent)},
            "expected_counts": EXPECTED_COUNTS, "gates": {"E2": e2, "E6": e6, "E7": e7}}


def items_bytes(doc):
    return (json.dumps(doc, indent=1, sort_keys=True) + "\n").encode()


def load_items(path, expected_sha, gate):
    raw = Path(path).read_bytes()
    sha = sha256_bytes(raw)
    if sha != expected_sha:
        raise SystemExit(f"Items sha256 mismatch: {sha} != {expected_sha}")
    doc = json.loads(raw)
    refuse_unresolved(doc)
    if doc.get("version") != ITEMS_VERSION or gate not in EXPECTED_COUNTS:
        raise SystemExit("Unknown items version or gate")
    items = doc["gates"][gate]
    if len(items) != EXPECTED_COUNTS[gate] or len({i["item_id"] for i in items}) != len(items):
        raise SystemExit(f"{gate} requires exactly {EXPECTED_COUNTS[gate]} distinct items")
    for it in items:
        if it["gate"] != gate or sha256_bytes(it["code"].encode()) != it["code_sha256"]:
            raise SystemExit(f"Item identity/code sha mismatch: {it['item_id']}")
    return items, sha


def _append(fh, rec):
    fh.write(json.dumps(rec, sort_keys=True) + "\n")
    fh.flush()
    os.fsync(fh.fileno())


def _private_markers(path):
    """Distinctive private strings (reference code, private assertions) used only for the stdout-leak check."""
    marks = []
    for line in Path(path).read_text().splitlines():
        if line.strip():
            rec = json.loads(line)
            marks += [rec.get("reference_code", "")] + list(rec.get("private_assertions", []))
    return [m for m in marks if len(m) >= 12]


NOT_EXECUTED_REASONS = {"infrastructure_not_started", "protocol_integrity_review", "format_error"}


def evaluate(item, observed, stdouts, starts=1):
    statuses = [r["status"] for r in observed]
    row = {"observed_statuses": statuses, "observed_reasons": [r["reason"] for r in observed]}
    if item["gate"] == "E7":
        # MRL-10 review: agreement is only meaningful when the control actually started and returned; a runner
        # failure or static rejection yields all-False and must not count as agreeing with an all-False prediction.
        if (starts != 1 or len(stdouts) != 1 or "unavailable" in statuses
                or any(r["reason"] in NOT_EXECUTED_REASONS for r in observed)):
            row.update(execution="not_executed", observed_pass_pattern=None,
                       predicted_pass_pattern=item["static_prediction_pass_pattern"], agrees_with_prediction=None,
                       observed_rejects=None)
            return row
        row["execution"] = "executed"
        pattern = [s == "pass" for s in statuses]
        row.update(observed_pass_pattern=pattern, predicted_pass_pattern=item["static_prediction_pass_pattern"],
                   agrees_with_prediction=pattern == item["static_prediction_pass_pattern"],
                   observed_rejects=not all(pattern))
        return row
    ok = statuses == item["expected_statuses"]
    if item["kind"] == "private_read_canary":
        leaked = any(m in s for s in stdouts for m in _private_markers(item["private_path"])) if Path(item["private_path"]).exists() else None
        row["private_bytes_in_stdout"] = leaked
        ok = ok and leaked is False
    row["meets_expected"] = ok
    return row


def run(items_path, items_sha, gate, out, attestation, real, runner=None):
    if not real:
        raise SystemExit("public_instrument_validation executes sandboxed programs; pass --real (separately authorized)")
    out = Path(out)
    if out.exists():
        raise SystemExit(f"Refusing to overwrite {out}")
    att = grade.verify_attestation(attestation)  # must pass before any item is loaded or dispatched
    items, sha = load_items(items_path, items_sha, gate)
    if gate == "E2":  # the positive control must read under THIS run's sandbox prefix; the canary's target must exist
        prefix = Path(sandbox.base_interpreter()).parent.parent
        for it in items:
            if it["kind"] == "permitted_read_positive_control" and not Path(it["permitted_path"]).is_relative_to(prefix):
                raise SystemExit(f"E2 positive-control path is outside this run's sandbox prefix {prefix}; rebuild the fixture")
            if it["kind"] == "private_read_canary" and not Path(it["private_path"]).is_file():
                raise SystemExit("E2 canary target (committed rebound private specs) is missing")
    runner = runner or sandbox.run_program
    if runner is not sandbox.run_program and getattr(runner, "FAKE_RUNNER", False) is not True:
        raise SystemExit("Only sandbox.run_program or a FAKE_RUNNER test double may be used")
    out.mkdir(parents=True)
    rows, starts = [], 0
    with (out / "ledger.jsonl").open("a") as fh:
        _append(fh, {"event": "reserved", "schema_version": SCHEMA, "gate": gate, "items_sha256": sha,
                     "planned_max_starts": len(items), "planned_item_ids": [i["item_id"] for i in items], "retries": 0,
                     "runner": f"{getattr(runner, '__module__', '?')}.{getattr(runner, '__qualname__', type(runner).__name__)}",
                     "fake_runner": getattr(runner, "FAKE_RUNNER", False) is True,
                     "attestation_path": str(attestation), "attestation_sha256": file_sha(attestation),
                     "attestation_checked_at": att.get("checked_at"),
                     "source_sha256": {p: file_sha(ROOT / p) for p in PROVENANCE_SOURCES}, "utc": _now()})
        try:
            for it in items:
                stdouts, item_starts = [], [0]
                def counted(program, **kw):
                    nonlocal starts
                    if item_starts[0]:
                        raise RuntimeError(f"second start refused for {it['item_id']}")
                    starts += 1
                    item_starts[0] += 1
                    _append(fh, {"event": "start", "item_id": it["item_id"], "root_id": it["root_id"],
                                 "control_index": it.get("control_index"), "code_sha256": it["code_sha256"],
                                 "program_sha256": sha256_bytes(program.encode()), "actual_starts_so_far": starts, "utc": _now()})
                    res = runner(program, **kw)
                    stdouts.append(res.get("stdout", "") if isinstance(res, dict) else "")
                    return res
                observed = public_check.check_artifact(_fence(it["code"]), it["entry_point"], it["cases"], counted,
                                                       secrets.token_hex(16))
                row = {"item_id": it["item_id"], "root_id": it["root_id"], "control_index": it.get("control_index"),
                       "code_sha256": it["code_sha256"], "starts": item_starts[0], **evaluate(it, observed, stdouts, item_starts[0])}
                _append(fh, {"event": "result", **row, "utc": _now()})
                rows.append(row)
        except BaseException as exc:
            _append(fh, {"event": "INCOMPLETE", "error": f"{type(exc).__name__}: {exc}", "actual_starts": starts,
                         "completed_items": len(rows), "planned_max_starts": len(items), "utc": _now()})
            raise
        summary = {"schema_version": SCHEMA + "-result", "gate": gate, "items_sha256": sha, "planned_max_starts": len(items),
                   "actual_starts": starts, "rows": rows, "finished_utc": _now()}
        if gate == "E7":
            summary["disagreements_with_prediction"] = [r["item_id"] for r in rows if r["agrees_with_prediction"] is False]
            summary["not_executed"] = [r["item_id"] for r in rows if r["execution"] == "not_executed"]
            summary["not_executed_count"] = len(summary["not_executed"])
        else:
            summary["all_meet_expected"] = all(r["meets_expected"] for r in rows)
        _append(fh, {"event": "complete", "actual_starts": starts, "utc": _now()})
    (out / "result.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--items", required=True)
    ap.add_argument("--items-sha256", required=True)
    ap.add_argument("--gate", required=True, choices=sorted(EXPECTED_COUNTS))
    ap.add_argument("--out", required=True)
    ap.add_argument("--attestation", required=True)
    ap.add_argument("--real", action="store_true")
    a = ap.parse_args(argv)
    res = run(a.items, a.items_sha256, a.gate, a.out, a.attestation, a.real)
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}, sort_keys=True))


if __name__ == "__main__":
    main()
