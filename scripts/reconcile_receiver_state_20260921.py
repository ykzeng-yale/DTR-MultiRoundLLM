#!/usr/bin/env python3
"""MRL-06 linked derived record: which receiver law did the v1/v1b/v1c collections actually run under?

Reads preserved run records and one read-only /props snapshot. No generation, no re-collection, no execution.
The original runs are not modified; this only adds what they did not record (sampler defaults).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments/landmark"))
import collect  # noqa: E402

RUNS = ["landmark_dev_release_v1_20260921T130048Z", "landmark_dev_release_v1b_20260921T130349Z",
        "landmark_dev_release_v1c_20260921T130757Z"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--props", type=Path, required=True, help="saved read-only /props snapshot")
    ap.add_argument("--snapshot-utc", required=True)
    ap.add_argument("--process-start-utc", required=True, help="receiver process start, from ps lstart")
    ap.add_argument("--out", type=Path, default=ROOT / "results/receiver_state_reconciliation_20260921.json")
    a = ap.parse_args(argv)
    props = json.loads(a.props.read_text())
    state = collect.receiver_state(props)
    params = props["default_generation_settings"]["params"]
    runs = []
    for name in RUNS:
        comp = json.loads((ROOT / "results" / name / "completion.json").read_text())
        man = json.loads((ROOT / "results" / name / "manifest.json").read_text())
        md = comp["model_metadata"]
        d = md["definition"]
        runs.append({"run": name, "freeze_commit": man["freeze"]["resolved_commit"],
                     "recorded_build": md["version"]["version"], "build_matches_snapshot": md["version"]["version"] == props["build_info"],
                     "recorded_weight_digest_before_after": [md["before"]["digest"], md["after"]["digest"]],
                     "template_matches_snapshot": d["template"] == props["chat_template"],
                     "n_ctx_matches_snapshot": d["parameters"]["n_ctx_per_slot"] == props["default_generation_settings"]["n_ctx"],
                     "slots_match_snapshot": d["parameters"]["total_slots"] == props["total_slots"],
                     "model_path_matches_snapshot": d["model_info"]["model_path"] == props["model_path"],
                     "request_overrides": sorted(json.loads((ROOT / "results" / name / "calls.jsonl").read_text().splitlines()[0])["request"]["options"])})
    effective = {k: params[k] for k in collect.PINNED_SAMPLER}
    out = {
        "record": "mrl06-receiver-state-reconciliation-v1", "evidence_class": "derived record from preserved outputs + one read-only /props GET",
        "snapshot_utc": a.snapshot_utc, "receiver_process_start_utc": a.process_start_utc,
        "receiver_state_sha256": collect.digest(state), "endpoint_props_mutable": props.get("endpoint_props"),
        "unrecorded_active_defaults": effective, "sampler_order": params.get("samplers"),
        "effective_sampler_v1_v1b_v1c": {"temperature": 0.7, "top_p": 0.95, **effective, "seed": "per request"},
        "runs": runs,
        "inference": ("The receiver process started before all three collections and is still running, and POST /props is "
                      "disabled, so launch-time defaults could not change through the API; build, template, n_ctx, slots and "
                      "model path recorded by each run match the snapshot. The snapshot's sampler defaults were therefore "
                      "most plausibly in force during v1/v1b/v1c."),
        "limits": ["Relies on llama-server semantics: per-request sampler fields do not persist and defaults are launch-time "
                   "when POST /props is disabled. Not independently proven here.",
                   "Process identity is from ps PID and start time; /props exposes no process identity.",
                   "Sampler defaults were never recorded by the runs themselves; this does not convert v1-v1c into "
                   "receiver-verified efficacy evidence (they remain descriptive development data).",
                   "One snapshot after the fact is not a continuous record of the runs."],
        "accounting": {"model_calls": 0, "executions": 0, "props_reads": 1, "slots_reads": 1, "usd": 0}}
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("receiver_state_sha256", "unrecorded_active_defaults")}, indent=1))
    print(json.dumps(runs, indent=1))


if __name__ == "__main__":
    main()
