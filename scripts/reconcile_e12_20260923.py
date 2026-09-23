"""Reconcile saved E12 records without importing collectors or executing answers."""
import argparse
import collections
import datetime
import hashlib
import json
import math
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "results/e12_dev_v3_20260922T030255Z"
ARMS = ("STOP", "N0", "S0", "N1", "S1", "R1")


def reconcile():
    started = time.perf_counter()
    read = lambda name: json.loads((RUN / name).read_text())
    rows = lambda name: [json.loads(s) for s in (RUN / name).read_text().splitlines()]
    sums = read("ARTIFACT_SHA256SUMS.json")["files"]
    for name, digest in sums.items():
        assert hashlib.sha256((RUN / name).read_bytes()).hexdigest() == digest, name
    tasks = [json.loads(s) for s in (ROOT / "experiments/landmark/dev_release_v3/tasks.jsonl").read_text().splitlines()]
    roots = [x["root_id"] for x in tasks]
    grades = rows("D/grades.jsonl")
    by = {(g["root_id"], g["arm"], g["replicate"]): g for g in grades}
    expected = {(r, a, j) for r in roots for a in ARMS for j in range(1 if a == "STOP" else 2)}
    assert len(by) == len(grades) == 154 and set(by) == expected
    # This audit verifies the delivered complete batch; it does not fill missing data.
    assert all(g["outcome"] in (0, 1) and g["missing_reason"] is None for g in grades)
    calls = rows("A/calls.jsonl") + rows("C/calls.jsonl")
    assert len(calls) == 154 and all(c["attempted"] for c in calls)
    callkeys = set()
    for c in calls:
        k = (c["root_id"], "STOP" if c["phase"] == "initial" else c["arm"], c["replicate"])
        assert k not in callkeys
        callkeys.add(k)
        # Frozen output_sha256 hashes the JSON string; artifact_sha256 hashes raw bytes.
        digest = hashlib.sha256(json.dumps(c["output"], sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        assert digest == c["output_sha256"] == by[k]["output_sha256"]
    assert callkeys == expected
    inp, report = read("analysis_input.json"), read("analysis_report.json")
    assert {r["root_id"] for r in inp["roots"]} == set(roots)
    for r in inp["roots"]:
        for a, records in r["arms"].items():
            for g in records:
                assert g["grade"] == by[r["root_id"], a, g["replicate"]]["outcome"]
    means = {a: {r: sum(by[r, a, j]["outcome"] for j in range(1 if a == "STOP" else 2)) / (1 if a == "STOP" else 2) for r in roots} for a in ARMS}
    arm_counts = {}
    for a in ARMS:
        q = report["quality"][a]
        assert {x["root_id"]: x["value"] for x in q["per_root"]} == means[a]
        assert math.isclose(sum(means[a].values()) / len(roots), q["mean_complete_roots"])
        arm_counts[a] = {"passes": sum(g["outcome"] for g in grades if g["arm"] == a), "assigned": sum(g["arm"] == a for g in grades), "mean": q["mean_complete_roots"]}
    contrasts = {}
    for key, published in report["contrasts"].items():
        a, b = key.split("_minus_")
        d = {r: means[a][r] - means[b][r] for r in roots}
        assert {x["root_id"]: x["value"] for x in published["per_root"]} == d
        value = sum(d.values()) / len(roots)
        assert math.isclose(value, published["mean_complete_pairs"], abs_tol=1e-12)
        contrasts[key] = {"mean": value, "per_root": d}
    initially_wrong = [r for r in roots if means["STOP"][r] == 0]
    initially_right = [r for r in roots if means["STOP"][r] == 1]
    repair_damage = {a: {"repairs": sum(by[r, a, j]["outcome"] for r in initially_wrong for j in range(2)), "repair_slots": 2 * len(initially_wrong), "damage": sum(1 - by[r, a, j]["outcome"] for r in initially_right for j in range(2)), "damage_slots": 2 * len(initially_right)} for a in ARMS[1:]}
    diagnostics = read("B/diagnostics.json")
    gated = []
    for rid, d in diagnostics.items():
        assert d["schema_version"] == "public-diagnostic-v2"
        assert all(c["status"] in {"pass", "wrong_value"} for c in d["cases"])
        initial = next(c for c in calls if c["root_id"] == rid and c["phase"] == "initial")
        assert d["initial_artifact_sha256"] == hashlib.sha256(initial["output"].encode()).hexdigest()
        if any(c["status"] != "pass" for c in d["cases"]):
            gated.append(rid)
    # Use the saved statuses verbatim, and reject a changed schema instead of guessing.
    assert set(gated) == {"mbpp/842", "mbpp/288", "mbpp/863", "mbpp/966", "mbpp/652"}
    posthoc = sum(means["R1"][r] if r in gated else means["STOP"][r] for r in roots) / len(roots)
    accounting = {"receiver_calls": len(calls), "prompt_tokens": sum(c["prompt_tokens"] for c in calls), "completion_tokens": sum(c["completion_tokens"] for c in calls), "unknown_usage_calls": sum(c["prompt_tokens"] is None or c["completion_tokens"] is None for c in calls)}
    ledgers = {f: dict(collections.Counter(x["event"] for x in rows(f))) for f in ("B/attempts.jsonl", "D/grading_attempts.jsonl")}
    return {"checked_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "evidence_class": "saved-record arithmetic; no model, benchmark execution, or regrading", "source_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "input_hashes": sums, "files_checked": len(sums), "all_assigned_grade_and_call_keys_match": True, "canonical_JSON_output_hashes_bind_all_grades": True, "analysis_input_and_published_contrasts_match_raw_grades": True, "arm_counts": arm_counts, "contrasts": contrasts, "repair_damage": repair_damage, "public_fail_roots": sorted(gated), "posthoc_gated_R1_value": posthoc, "posthoc_gated_R1_minus_STOP": posthoc - arm_counts["STOP"]["mean"], "posthoc_scope": "selected on these same outcomes; not independent policy validation", "usage": accounting, "ledger_events": ledgers, "review_runtime_seconds": time.perf_counter() - started, "new_model_calls": 0, "new_model_tokens": 0, "new_benchmark_executions": 0, "paid_cost_usd": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Refusing to overwrite an existing audit")
    result = reconcile()
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("files_checked", "arm_counts", "usage", "review_runtime_seconds")}, indent=2))
