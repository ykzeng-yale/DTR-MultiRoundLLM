#!/usr/bin/env python3
"""Descriptive five-arm analyzer for the public-diagnostic development study.

Pure arithmetic over supplied records: it never imports a sandbox, opens a model
connection, or executes any output. Nothing here is fresh efficacy evidence.

Input format (explicit; every field below is read, nothing else is inferred):

roots: list of dicts, one per frozen root (e.g. parsed roots.jsonl lines)::

    {"root_id": str, "family_id": str | None,
     "initial_artifact_sha256": str | None,          # optional; cross-checked with the diagnostic
     "initial": {"calls": int|None, "prompt_tokens": int|None, "completion_tokens": int|None},
     "diagnostic_cost": {"executor_starts": int|None, "executor_seconds": float|None},
     "arms": {arm: [{"replicate": int, "grade": 1 | 0 | None, "missing_reason": str | None,
                     "calls": int|None, "prompt_tokens": int|None, "completion_tokens": int|None,
                     "executor_starts": int|None, "executor_seconds": float|None}, ...]}}

  arm is one of STOP, N0, S0, N1, S1, R1. STOP holds exactly one record (replicate 0):
  the private grade of the initial artifact; it adds no continuation call. Continuation
  records carry the cost of that one continuation call. Record executor_* fields are the
  private GRADING executions of that artifact (measurement cost). "initial" is the shared
  first receiver call; "diagnostic_cost" is the root's public diagnostic execution, which
  N1/S1/R1 consume (a selector that observes it has paid it, per the design doc). A cost
  field that is absent or None is UNKNOWN, never zero; the one exception is STOP's
  continuation, which is zero by definition.

diagnostics: mapping root_id -> dict as produced by diagnostic.build_diagnostic::

    {"schema_version": "public-diagnostic-v1", "root_id": str, "initial_artifact_sha256": str,
     "cases": [{"case_id", "call", "expected", "status", "returned", "value_kind", "reason"}, ...]}

  Only "status" (and the identity fields) are read. A root without a diagnostic is
  classified public-unknown and listed separately; it is never dropped.

Missing grades, records and whole arms are counted per arm with reasons; root means
with any missing replicate are None (complete-case) and all-assigned completion
bounds are reported beside them. No value is imputed and no row is silently dropped.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path

# Mirrors diagnostic.SCHEMA / the shared status contract; kept local so this analyzer
# does not depend on the renderer module (checked for agreement in the tests).
SCHEMA = "public-diagnostic-v1"
STATUSES = ("pass", "wrong_value", "format_error", "interface_error", "program_exception",
            "timeout", "unavailable", "output_limit")
FAIL_STATUSES = frozenset(("wrong_value", "format_error", "interface_error", "program_exception"))
UNKNOWN_STATUSES = frozenset(("timeout", "unavailable", "output_limit"))
PUBLIC_STRATA = ("all_pass", "any_fail", "unknown")
PRIVATE_STRATA = ("pass", "fail", "unknown")
CONTINUATION_ARMS = ("N0", "S0", "N1", "S1", "R1")
ARMS = ("STOP", *CONTINUATION_ARMS)
DIAGNOSTIC_ARMS = frozenset(("N1", "S1", "R1"))  # receivers that see (hence paid for) the diagnostic
PRIMARY = ("S1", "N1")
CONTRASTS = (PRIMARY, ("N1", "N0"), ("S0", "N0"), ("R1", "N1"),
             *((arm, "STOP") for arm in CONTINUATION_ARMS))
COST_KEYS = ("calls", "prompt_tokens", "completion_tokens")
EXEC_KEYS = ("executor_starts", "executor_seconds")
NO_INTERVAL_NOTE = ("No confidence intervals or tests: every root belongs to one unresolved "
                    "family, so there is no independent replication to support population "
                    "inference. Means and per-root vectors are descriptive only.")
FIELD15_NOTE = ("Descriptive strata only (lead field 15). Initial public status comes from the "
                "planned diagnostic executions of the initial artifacts; final artifacts were not "
                "executed on public cases, so this does not estimate final public-pass/private-fail "
                "rates, and these subgroup summaries do not validate a learned conditional policy "
                "or its value on new roots or families.")
COST_NOTE = ("Equal calls are not equal token/runtime cost: R1 omits the previous answer, "
             "N1/S1/R1 carry the diagnostic message and its executor cost, and completion "
             "lengths differ by arm. Unknown cost components are counted, never zero-filled.")


def _num(x, key):
    if x is None:
        return None
    if type(x) is bool or not isinstance(x, (int, float)) or not math.isfinite(x) or x < 0:
        raise ValueError(f"Invalid cost value for {key}: {x!r}")
    return x


def public_status(diag, root_id):
    """all_pass / any_fail / unknown for one root's initial diagnostic (None -> unknown).

    Precedence matches diagnostic.select_s1: any observed fail wins; otherwise any
    timeout/unavailable/output_limit is unknown; all-pass needs >=1 case, all pass.
    """
    if diag is None:
        return "unknown"
    if diag.get("schema_version") != SCHEMA or diag.get("root_id") != root_id:
        raise ValueError(f"Diagnostic schema/root mismatch for {root_id}")
    statuses = [c.get("status") for c in diag.get("cases", [])]
    if any(s not in STATUSES for s in statuses):
        raise ValueError(f"Unknown diagnostic status for {root_id}")
    if any(s in FAIL_STATUSES for s in statuses):
        return "any_fail"
    if not statuses or any(s in UNKNOWN_STATUSES for s in statuses):
        return "unknown"
    return "all_pass"


def _records(row, arm, expected):
    """Validated slot list of length `expected`: record dict or None (absent)."""
    raw = row["arms"].get(arm)
    slots = [None] * expected
    for rec in raw or []:
        r = rec.get("replicate")
        if type(r) is not int or not 0 <= r < expected or slots[r] is not None:
            raise ValueError(f"Unassigned or duplicate replicate {r!r} in {row['root_id']}/{arm}")
        g = rec.get("grade")
        if g is not None and (type(g) is not int or g not in (0, 1)):
            raise ValueError(f"Grade must be 1, 0 or None in {row['root_id']}/{arm}")
        slots[r] = rec
    return slots, raw is None


def analyze(roots, diagnostics, replicates=2):
    """Return the descriptive report dict. `replicates` = assigned continuations per arm."""
    if type(replicates) is not int or replicates < 1:
        raise ValueError("replicates must be a positive integer")
    ids = [r["root_id"] for r in roots]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate root_id")
    if set(diagnostics) - set(ids):
        raise ValueError("Diagnostic for an unassigned root")
    for row in roots:
        if set(row["arms"]) - set(ARMS):
            raise ValueError(f"Unknown arm in {row['root_id']}")
        d = diagnostics.get(row["root_id"])
        if d is not None and row.get("initial_artifact_sha256") is not None \
                and d.get("initial_artifact_sha256") != row["initial_artifact_sha256"]:
            raise ValueError(f"Diagnostic is for a different initial artifact: {row['root_id']}")
    expected = {arm: 1 if arm == "STOP" else replicates for arm in ARMS}
    slots = {(row["root_id"], arm): _records(row, arm, expected[arm]) for row in roots for arm in ARMS}

    def grades(rid, arm):
        return [None if s is None else s.get("grade") for s in slots[rid, arm][0]]

    def root_mean(rid, arm):  # replicates averaged within root; complete-case only
        g = grades(rid, arm)
        return None if any(x is None for x in g) else sum(g) / len(g)

    def bounds(rid, arm):
        g = grades(rid, arm)
        known = sum(x for x in g if x is not None)
        return known / len(g), (known + sum(x is None for x in g)) / len(g)

    def mean(values):
        v = [x for x in values if x is not None]
        return sum(v) / len(v) if v else None

    n = len(roots)
    report = {"analysis_version": "landmark-diagnostic-analysis-v1", "diagnostic_schema": SCHEMA,
              "arms": list(ARMS), "assigned_replicates": expected, "n_roots": n,
              "n_families": len({r.get("family_id") for r in roots}) if n else 0,
              "inference": {"confidence_intervals": None, "note": NO_INTERVAL_NOTE},
              "quality": {}, "contrasts": {}, "initial_status": {}, "cost": {"note": COST_NOTE, "arms": {}},
              "interpretation": ("Development-stage descriptive comparison of fixed prompt arms on "
                                 "these roots; no efficacy, population futility or policy-validation claim.")}

    for arm in ARMS:
        missing = Counter()
        for row in roots:
            recs, absent = slots[row["root_id"], arm]
            for rec in recs:
                if absent:
                    missing["arm_record_absent"] += 1
                elif rec is None:
                    missing["replicate_record_absent"] += 1
                elif rec.get("grade") is None:
                    missing[rec.get("missing_reason") or "ungraded_no_reason"] += 1
        per_root = [{"root_id": r["root_id"], "value": root_mean(r["root_id"], arm)} for r in roots]
        complete = sum(p["value"] is not None for p in per_root)
        report["quality"][arm] = {
            "per_root": per_root, "mean_complete_roots": mean(p["value"] for p in per_root),
            "complete_roots": complete, "incomplete_roots": n - complete,
            "assigned_replicates": n * expected[arm], "missing_replicates": sum(missing.values()),
            "missing_reasons": dict(sorted(missing.items())),
            "all_assigned_mean_bounds": None if not n else
                [sum(bounds(r["root_id"], arm)[k] for r in roots) / n for k in (0, 1)],
            "bounds_scope": "Completion bounds for this realized root set; not a confidence interval"}

    for a, b in CONTRASTS:
        per_root = []
        for r in roots:
            ma, mb = root_mean(r["root_id"], a), root_mean(r["root_id"], b)
            per_root.append({"root_id": r["root_id"], "value": None if ma is None or mb is None else ma - mb})
        vals = [p["value"] for p in per_root if p["value"] is not None]
        lo = hi = 0.0
        for r in roots:
            (la, ua), (lb, ub) = bounds(r["root_id"], a), bounds(r["root_id"], b)
            lo, hi = lo + la - ub, hi + ua - lb
        report["contrasts"][f"{a}_minus_{b}"] = {
            "primary": (a, b) == PRIMARY, "per_root": per_root, "mean_complete_pairs": mean(vals),
            "complete_pairs": len(vals), "missing_pair_roots": n - len(vals),
            "positive": sum(v > 0 for v in vals), "ties": sum(v == 0 for v in vals),
            "negative": sum(v < 0 for v in vals),
            "all_assigned_mean_bounds": None if not n else [lo / n, hi / n]}

    # Field 15: initial public diagnostic status x initial private STOP status, unknowns kept.
    table = {p: {q: [] for q in PRIVATE_STRATA} for p in PUBLIC_STRATA}
    stratum = {}
    for r in roots:
        rid = r["root_id"]
        p = public_status(diagnostics.get(rid), rid)
        g = grades(rid, "STOP")[0]
        table[p]["unknown" if g is None else "pass" if g == 1 else "fail"].append(rid)
        stratum[rid] = p
    by_stratum = {}
    for p in PUBLIC_STRATA:
        members = [r["root_id"] for r in roots if stratum[r["root_id"]] == p]
        by_stratum[p] = {"n_roots": len(members), "arms": {arm: {
            "mean_complete_roots": mean(root_mean(rid, arm) for rid in members),
            "complete_roots": sum(root_mean(rid, arm) is not None for rid in members),
            "incomplete_roots": sum(root_mean(rid, arm) is None for rid in members)} for arm in ARMS}}
    report["initial_status"] = {
        "public_definition": "all_pass: every case pass; any_fail: any wrong_value/format_error/interface_error/program_exception; unknown: otherwise (any timeout/unavailable/output_limit, no cases, or no diagnostic)",
        "private_definition": "Initial artifact STOP grade: 1 pass, 0 fail, missing unknown",
        "crosstab": {p: {q: len(v) for q, v in row.items()} for p, row in table.items()},
        "crosstab_roots": table,
        "public_totals": {p: sum(len(v) for v in table[p].values()) for p in PUBLIC_STRATA},
        "private_totals": {q: sum(len(table[p][q]) for p in PUBLIC_STRATA) for q in PRIVATE_STRATA},
        "diagnostic_missing_roots": [r["root_id"] for r in roots if r["root_id"] not in diagnostics],
        "final_private_by_initial_public": by_stratum, "note": FIELD15_NOTE}

    def shared(section, keys):  # once-per-root components shared by arms: [known sum, unknown roots]
        out = {}
        for k in keys:
            vals = [_num((r.get(section) or {}).get(k), k) for r in roots]
            out[k] = {"known_sum": sum(v for v in vals if v is not None), "unknown_roots": sum(v is None for v in vals)}
        return out
    report["cost"]["shared_initial"] = shared("initial", COST_KEYS)
    report["cost"]["shared_public_diagnostic"] = shared("diagnostic_cost", EXEC_KEYS)
    for arm in ARMS:
        # totals: continuation calls/tokens and private-grading executions paid for this arm's
        # records across ALL replicates: [known sum, unknown components].
        totals = {k: [0, 0] for k in (*COST_KEYS, *("grading_" + k for k in EXEC_KEYS))}
        per_root_cost = {k: [] for k in (*COST_KEYS, *EXEC_KEYS)}
        for row in roots:
            init, dcost = row.get("initial") or {}, row.get("diagnostic_cost") or {}
            recs = slots[row["root_id"], arm][0]
            for k in COST_KEYS:
                iv = _num(init.get(k), k)
                cont = 0
                if arm != "STOP":
                    reps = [None if rec is None else _num(rec.get(k), k) for rec in recs]
                    totals[k][0] += sum(v for v in reps if v is not None)
                    totals[k][1] += sum(v is None for v in reps)
                    cont = None if any(v is None for v in reps) else sum(reps) / len(reps)
                per_root_cost[k].append(None if iv is None or cont is None else iv + cont)
            for k in EXEC_KEYS:
                reps = [None if rec is None else _num(rec.get(k), k) for rec in recs]
                totals["grading_" + k][0] += sum(v for v in reps if v is not None)
                totals["grading_" + k][1] += sum(v is None for v in reps)
                # Policy runtime = public diagnostic acquisition only (grading is measurement).
                per_root_cost[k].append(_num(dcost.get(k), k) if arm in DIAGNOSTIC_ARMS else 0)
        report["cost"]["arms"][arm] = {
            "totals": {k: {"known_sum": s, "unknown_components": u} for k, (s, u) in totals.items()},
            "per_root_policy_mean": {k: {"mean_known_roots": mean(v), "known_roots": sum(x is not None for x in v),
                                          "unknown_roots": sum(x is None for x in v)} for k, v in per_root_cost.items()},
            "scope": ("per_root_policy_mean = shared initial call + replicate-averaged continuation (none "
                      "for STOP) + the root's public diagnostic executor cost for N1/S1/R1 only. totals = "
                      "continuation calls/tokens and private-grading executions across all replicates; "
                      "the shared initial call and diagnostic are reported once under shared_*.")}
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--roots", type=Path, required=True, help="JSONL, one root row per line")
    p.add_argument("--diagnostics", type=Path, required=True, help="JSON object root_id -> diagnostic")
    p.add_argument("--replicates", type=int, default=2)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    roots = [json.loads(line) for line in args.roots.read_text().splitlines() if line.strip()]
    result = analyze(roots, json.loads(args.diagnostics.read_text()), args.replicates)
    with args.output.open("x") as f:
        f.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"n_roots": result["n_roots"], "output": str(args.output)}))


if __name__ == "__main__":
    main()
