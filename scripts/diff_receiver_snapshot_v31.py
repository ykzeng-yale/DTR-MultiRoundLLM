#!/usr/bin/env python3
"""MRL-16 v3.1: field-by-field diff of a fresh non-generating receiver preflight against the frozen snapshot.

Reads only saved files: the frozen results/receiver_props_snapshot_8193.json and prior MRL-10 preflight
renders, and a NEW preflight directory produced by scripts/receiver_preflight_mrl10.py against the restarted
server. Reports every differing /props field path, the canonical receiver_state digest (collect.receiver_state,
which excludes only is_sleeping) versus the frozen 1b8bf998..., and byte equality of all 42 rendered prompts.
"""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.landmark import collect  # noqa: E402

FROZEN = ROOT / "results/receiver_props_snapshot_8193.json"
PRIOR = ROOT / "results/receiver_preflight_mrl10_20260921T194506Z"
FROZEN_STATE = "1b8bf998c5dd06a611f692bab9e802b285ae75164b8b389fd8b381c06a83f5c1"
MODEL_SHA = "626b4a6678b86442240e33df819e00132d3ba7dddfe1cdc4fbb18e0a9615c62d"


def validate_preflight(directory, new, state):
    """Validate saved observations, not the preflight process's (always-zero) exit status."""
    errors = []
    summary = json.loads((directory / "summary.json").read_text())
    prior = json.loads((PRIOR / "summary.json").read_text())
    for key in ("error", "blocker", "state_drift_fields", "sampler_differences_vs_template"):
        if summary.get(key):
            errors.append(f"preflight reports {key}")
    expected = [("GET", "/slots"), ("GET", "/props"), ("GET", "/v1/models")] + [("POST", "/apply-template")] * 42 + [("GET", "/props"), ("GET", "/slots")]
    log = summary.get("request_log", [])
    if summary.get("requests_made") != 47 or len(log) != 47 or any(
        (row.get("method"), row.get("path")) != expected[i] or row.get("status") != "ok" or row.get("n") != i + 1
        for i, row in enumerate(log[:47])
    ):
        errors.append("complete ordered 47-request successful preflight required")
    for key in ("tasks_sha256", "examples_sha256", "base_url", "limits"):
        if summary.get(key) != prior.get(key):
            errors.append(f"preflight {key} differs from frozen fixtures")
    if summary.get("weight_digest") != MODEL_SHA or summary.get("generation_requests") != 0 or summary.get("model_calls") != 0:
        errors.append("wrong weight digest or nonzero/absent generation accounting")
    after = json.loads((directory / "props_after.json").read_text())
    after_state = collect.digest(collect.receiver_state(after))
    if state != after_state or any(summary.get(k) != state for k in ("receiver_state_sha256_before", "receiver_state_sha256_after")):
        errors.append("saved before/after state or summary binding differs")
    for name in ("slots_before.json", "slots_after.json"):
        slots = json.loads((directory / name).read_text())
        valid = isinstance(slots, list) and len(slots) == 4 and all(
            isinstance(s, dict) and type(s.get("id")) is int and type(s.get("is_processing")) is bool
            and s["is_processing"] is False and type(s.get("n_ctx")) is int and s["n_ctx"] == 8192 for s in slots
        )
        if not valid or {s["id"] for s in slots} != set(range(4)):
            errors.append(f"{name} must show all four typed, idle 8192-context slots")
    fixtures = summary.get("template_fixtures", [])
    if len(fixtures) != 42 or fixtures != prior.get("template_fixtures"):
        errors.append("42 frozen template fixture bindings required")
    return errors


def walk(a, b, path=""):
    if type(a) is not type(b):
        yield path or "<root>", a, b; return
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                yield f"{path}.{k}", a.get(k, "<absent>"), b.get(k, "<absent>")
            else:
                yield from walk(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, list):
        if len(a) != len(b):
            yield path, a, b
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                yield from walk(x, y, f"{path}[{i}]")
    elif a != b:
        yield path, a, b


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--new-preflight", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit("Refusing to overwrite")
    old = json.loads(FROZEN.read_text()); new = json.loads((a.new_preflight / "props_before.json").read_text())
    diffs = [{"field": p, "frozen": o, "new": n} for p, o, n in walk(old, new)]
    state = collect.digest(collect.receiver_state(new))
    renders = {}
    for f in sorted((PRIOR / "rendered").glob("*.prompt.txt")):
        g = a.new_preflight / "rendered" / f.name
        renders[f.name] = g.exists() and g.read_bytes() == f.read_bytes()
    out = {"frozen_snapshot_sha256": hashlib.sha256(FROZEN.read_bytes()).hexdigest(), "new_preflight": str(a.new_preflight),
           "field_differences": diffs, "n_field_differences": len(diffs),
           "receiver_state_sha256_new": state, "receiver_state_sha256_frozen": FROZEN_STATE, "state_identical": state == FROZEN_STATE,
           "rendered_prompts_compared": len(renders), "rendered_prompts_identical": sum(renders.values()),
           "render_mismatches": [k for k, v in renders.items() if not v]}
    try:
        errors = validate_preflight(a.new_preflight, new, state)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        errors = [f"incomplete/invalid saved preflight: {type(exc).__name__}: {exc}"]
    new_names = {f.name for f in (a.new_preflight / "rendered").glob("*.prompt.txt")}
    if len(renders) != 42 or new_names != set(renders) or not all(renders.values()):
        errors.append("exactly all 42 original rendered prompt bytes required")
    if state != FROZEN_STATE:
        errors.append("receiver state differs; unclassified differences do not release collection")
    out["validation_errors"], out["passed"] = errors, not errors
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(json.dumps({k: out[k] for k in ("n_field_differences", "state_identical", "rendered_prompts_compared", "rendered_prompts_identical")}, indent=1))
    for d in diffs[:20]:
        print("DIFF", d["field"], "|", str(d["frozen"])[:80], "->", str(d["new"])[:80])
    if errors:
        raise SystemExit("Preflight failed: " + "; ".join(errors))


if __name__ == "__main__":
    main()
