#!/usr/bin/env python3
"""Build the exact E13a request plan (PROPOSED, NOT RELEASED) from E12's immutable artifacts. No receiver call.

MRL-18 (lead commit be417b5): the checkpoint set is derived from the FROZEN PUBLIC DIAGNOSTICS ONLY, through
analyze_diagnostic.public_status, and no private grade appears in this plan. Selection uses public information
that was available at decision time; it is not a private-outcome selection.

E13a re-samples two arms on E12's public-fail roots, conditioning on E12's initial artifacts and diagnostics:
  R1    : diagnostic.render_arms(...)["R1"], replicates 2..7 (E12 used 0..1), seed key "R1:<r>";
  FRESH : the original public prompt alone (collect.initial_messages), replicates 0..5, seed key "FRESH:<r>".
Every rendered message list is checked byte-for-byte against E12's recorded requests (R1 replicates, the
initial request), and every new seed against all seeds E12 used for that root, so only the seed differs.
"""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.landmark import collect  # noqa: E402
from experiments.landmark import collect_diagnostic as cd  # noqa: E402
from experiments.landmark.analyze_diagnostic import public_status  # noqa: E402

RUN = ROOT / "results/e12_dev_v3_20260922T030255Z"
PKG = ROOT / "experiments/landmark/dev_release_v3"
R1_REPLICATES = range(2, 8)
FRESH_REPLICATES = range(0, 6)
TOKENS_PER_CALL = 512
RECHECKS_PER_ROOT = 2


def _jsonl(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


def build(run=RUN, pkg=PKG):
    config = json.loads((pkg / "config.json").read_text())
    tasks = _jsonl(pkg / "tasks.jsonl")
    plan = cd.assignments(config, tasks)
    initial_dir, _, rows = cd._load_initial(run / "A", config, tasks, plan)  # re-verifies A bytes and bindings
    sums = json.loads((run / "ARTIFACT_SHA256SUMS.json").read_text())
    sums = sums.get("files", sums)
    raw = (run / "B/diagnostics.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != sums["B/diagnostics.json"]:
        raise ValueError("B/diagnostics.json differs from E12's artifact checksums")
    for rel in ("C/calls.jsonl",):
        if hashlib.sha256((run / rel).read_bytes()).hexdigest() != sums[rel]:
            raise ValueError(f"{rel} differs from E12's artifact checksums")
    dm = cd.diagnostic_module()
    diagnostics = dm.strict_json_loads(raw)
    # Checkpoints: public "any_fail" on the frozen diagnostic. The private grades are deliberately not read.
    gated = [rid for rid in diagnostics if public_status(diagnostics[rid], rid) == "any_fail"]
    calls = _jsonl(run / "C/calls.jsonl")
    by_task = {t["root_id"]: t for t in tasks}
    seeds_by_root = {p["root_id"]: p["seeds"] for p in plan}
    out_roots = []
    for rid in [p["root_id"] for p in plan if p["root_id"] in gated]:
        row = rows[rid]
        text = (initial_dir / row["artifact"]).read_bytes()
        if hashlib.sha256(text).hexdigest() != row["artifact_sha256"]:
            raise ValueError(f"initial artifact bytes changed for {rid}")
        diag = diagnostics[rid]
        if diag.get("initial_artifact_sha256") != row["artifact_sha256"]:
            raise ValueError(f"diagnostic for {rid} is bound to a different initial artifact")
        base = collect.initial_messages(by_task[rid])
        if collect.digest(base) != row["base_messages_sha256"] or base != row["initial"]["request"]["messages"]:
            raise ValueError(f"FRESH prompt for {rid} differs from E12's recorded initial request")
        r1 = dm.render_arms(base, text.decode("utf-8"), diag)["R1"]
        e12_r1 = [c["request"]["messages"] for c in calls if c["root_id"] == rid and c["arm"] == "R1"]
        if len(e12_r1) != 2 or any(m != r1 for m in e12_r1):
            raise ValueError(f"R1 prompt for {rid} differs from E12's recorded R1 requests")
        used = set(seeds_by_root[rid].values())
        requests = ([("R1", r, r1) for r in R1_REPLICATES] + [("FRESH", r, base) for r in FRESH_REPLICATES])
        reqs = []
        for arm, r, messages in requests:
            key = f"{arm}:{r}"
            seed = collect.seeded(config, rid, key)
            if seed in used:
                raise ValueError(f"seed for {rid} {key} repeats a seed E12 used")
            used.add(seed)
            reqs.append({"arm": arm, "replicate": r, "seed_key": key, "seed": seed,
                         "messages_sha256": collect.digest(messages)})
        out_roots.append({"root_id": rid,
                          "public_status": "any_fail",
                          "public_case_statuses": [c.get("status") for c in diag["cases"]],
                          "initial_artifact_sha256": row["artifact_sha256"],
                          "base_messages_sha256": row["base_messages_sha256"],
                          "r1_messages_sha256": collect.digest(r1), "requests": reqs})
    n_calls = sum(len(r["requests"]) for r in out_roots)
    return {
        "plan_version": "e13a-request-plan-v2-public-gated",
        "status": "PROPOSED, NOT RELEASED; no receiver call made",
        "evidence_class": "post-hoc-motivated development follow-up at five fixed public-fail checkpoints; not a test of the selected gated rule and not a diagnostic-only effect; a tie is inconclusive",
        "source_run": run.relative_to(ROOT).as_posix(),
        "inputs": {rel: sums[rel] for rel in ("A/roots.jsonl", "B/diagnostics.json", "C/calls.jsonl")
                   if rel in sums},
        "package_config_sha256": hashlib.sha256((pkg / "config.json").read_bytes()).hexdigest(),
        "decoding": {**config["decoding"], "num_predict": config["max_tokens_per_call"]},
        "checks": ["A bytes and config/dataset/assignment digests re-verified (collect_diagnostic._load_initial)",
                   "B diagnostics and C calls match E12 ARTIFACT_SHA256SUMS",
                   "checkpoints derived from frozen public diagnostics via analyze_diagnostic.public_status; no private grade is read",
                   "FRESH messages == E12 recorded initial request messages",
                   "R1 messages == both E12 recorded R1 request messages",
                   "no new seed equals any seed E12 used for the same root"],
        "roots": out_roots,
        "budget": {"receiver_calls": n_calls, "reserved_completion_tokens": TOKENS_PER_CALL * n_calls,
                   "isolated_starts": n_calls + RECHECKS_PER_ROOT * len(out_roots),
                   "cumulative_ledger_if_granted": 333 + n_calls + RECHECKS_PER_ROOT * len(out_roots),
                   "ledger_note": "accounting only; E12's unused starts are not authority for this stage (lead be417b5), and a separately enumerated allowance plus a renewed attestation and window are required",
                   "ledger_ceiling": 412},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit("Refusing to overwrite")
    out = build()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["budget"]), [r["root_id"] for r in out["roots"]])


if __name__ == "__main__":
    main()
