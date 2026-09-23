#!/usr/bin/env python3
"""E13a analysis path: POST-HOC-MOTIVATED DEVELOPMENT follow-up on a small fixed set of checkpoints.

Static JSON only: this script reads a graded records file and a stage descriptor (the E13a request plan,
or any descriptor carrying the same roots[].root_id / roots[].requests[].{arm,replicate} assignment shape)
and emits a deterministic report. Nothing is executed here: no receiver, no grader, no sandbox, no network.

Arms, replicate indices and roots come from the stage descriptor; no E12 arm list, replicate count or
sample-size assumption is imported. The primary endpoint is whatever frozen graded outcome the grades file
carries (E12/E13a: private-suite-plus-format score in {0,1}).

The reported contrast is a finite-checkpoint DESCRIPTIVE quantity over the fixed development-selected
checkpoints named by the descriptor: no population interval, no test, no p-value, no significance and no
futility claim. A tie is inconclusive and does not identify a resampling mechanism.

Unavailable outcomes are kept separate from failures and are never zero-filled; unknown usage counts are
reported as unknown counts, not as zeros. Any assigned slot absent from the grades file without a
missing_reason, any unexpected root/arm/replicate, any duplicate slot and any existing --out path is a
hard refusal rather than a silent drop.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ANALYSIS_VERSION = "e13a-finite-checkpoint-contrast-v1"
EVIDENCE_CLASS = (
    "post-hoc-motivated development follow-up on the fixed development-selected checkpoints named by the "
    "stage descriptor; NOT a test of the selected gated rule; NOT a test of a diagnostic-only effect; "
    "not pooled with E12; descriptive only"
)

METRIC_DEFINITIONS = {
    "outcome": "Frozen primary endpoint as recorded in the grades file (private-suite-plus-format score in {0,1}); this script never grades, executes or re-derives it.",
    "assigned": "Number of root-arm-replicate slots the stage descriptor assigns. Inclusion probability is 1 for every root-arm; ordering is scheduling only.",
    "graded": "Number of assigned slots with an available outcome in {0,1}. graded + missing == assigned.",
    "passes": "Number of graded slots with outcome == 1. Slots with an unavailable outcome are NOT counted as failures.",
    "missing": "Number of assigned slots whose outcome is unavailable, each with an explicit missing_reason; never zero-filled and never folded into failures.",
    "mean": "passes / graded, i.e. the mean over AVAILABLE outcomes only. null when graded == 0; it is not a zero-filled mean over assigned slots.",
    "per_root_difference": "Per root, mean(treatment arm) - mean(reference arm) over available outcomes at that single fixed checkpoint. null when either arm has no available outcome at that root.",
    "finite_checkpoint_contrast": "Equally weighted mean of the per-root differences over the fixed development-selected checkpoints in the stage descriptor. A finite-checkpoint DESCRIPTIVE quantity about these checkpoints only: no population interval, no standard error, no test, no p-value, no significance claim and no futility claim. null when any per-root difference is null.",
    "interpretation_tie": "A tie (contrast at or near zero) is INCONCLUSIVE: it does not identify a resampling mechanism, does not establish a diagnostic-only effect, and does not license a futility claim from this many draws.",
    "interpretation_direction": "A nonzero contrast describes these fixed checkpoints under this development stage only; it is not a test of the selected gated rule and must not be pooled with E12 or escalated on the basis of its size.",
    "calls_known_sum": "Sum of recorded nonnegative integer 'calls' values only; records without the field contribute to calls_unknown_count and are not assumed zero.",
    "prompt_tokens_known_sum": "Sum of recorded nonnegative integer prompt_tokens only; unknown counts are reported separately and never assumed zero.",
    "completion_tokens_known_sum": "Sum of recorded nonnegative integer completion_tokens only; unknown counts are reported separately and never assumed zero.",
    "executor_starts_known_sum": "Sum of recorded nonnegative integer executor_starts (private-grading executor starts) only; unknown counts reported separately.",
    "executor_seconds_known_sum": "Sum of recorded nonnegative executor_seconds only; unknown counts reported separately.",
}

NO_SIGNIFICANCE_STATEMENT = (
    "No hypothesis test, p-value, confidence interval, significance claim or futility claim is computed or "
    "implied; no significance-driven escalation follows from this report."
)
TIE_STATEMENT = METRIC_DEFINITIONS["interpretation_tie"]

USAGE_FIELDS = ("calls", "prompt_tokens", "completion_tokens", "executor_starts", "executor_seconds")


class RefusalError(Exception):
    """Raised when the inputs do not satisfy the assigned-versus-completed contract."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_jsonl(path: Path):
    rows = []
    for lineno, line in enumerate(Path(path).read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise RefusalError(f"grades line {lineno} is not valid JSON: {exc}") from exc
    return rows


def _requests_from_arm_map(descriptor, root_id):
    """Stage-descriptor shape: {"arms": {arm: [replicate, ...]}, "roots": [root_id, ...]} (root-balanced)."""
    arm_map = descriptor.get("arms")
    if not isinstance(arm_map, dict) or not arm_map:
        raise RefusalError(f"root {root_id} is a bare id but the descriptor has no non-empty 'arms' map")
    requests = []
    for arm, replicates in arm_map.items():
        if not isinstance(replicates, list) or not replicates:
            raise RefusalError(f"descriptor arm {arm!r} has no non-empty replicate list")
        requests += [{"arm": arm, "replicate": replicate} for replicate in replicates]
    return requests


def plan_from_descriptor(descriptor, treatment_arm=None, reference_arm=None):
    """Derive the arm/replicate/root plan from the stage descriptor. No arm list is hard-coded here.

    Two descriptor shapes are accepted: per-root request lists (the E13a request plan) and an
    arms-by-replicate map with bare root ids (the E13a stage descriptor). Both are read, never assumed.
    """
    roots_spec = descriptor.get("roots")
    if not isinstance(roots_spec, list) or not roots_spec:
        raise RefusalError("stage descriptor has no non-empty 'roots' list")
    contrast = descriptor.get("contrast") or {}
    treatment = treatment_arm or contrast.get("treatment")
    reference = reference_arm or contrast.get("reference")
    plan, root_order = {}, []
    for entry in roots_spec:
        if isinstance(entry, str):
            entry = {"root_id": entry, "requests": _requests_from_arm_map(descriptor, entry)}
        elif not isinstance(entry, dict):
            raise RefusalError(f"stage descriptor root entry {entry!r} is neither a root id nor an object")
        root_id = entry.get("root_id")
        if not isinstance(root_id, str) or not root_id:
            raise RefusalError("stage descriptor root entry without a string root_id")
        if root_id in plan:
            raise RefusalError(f"stage descriptor repeats root {root_id}")
        requests = entry.get("requests")
        if not isinstance(requests, list) or not requests:
            raise RefusalError(f"stage descriptor root {root_id} has no non-empty 'requests' list")
        per_arm = {}
        for request in requests:
            arm, replicate = request.get("arm"), request.get("replicate")
            if not isinstance(arm, str) or not arm:
                raise RefusalError(f"stage descriptor root {root_id} has a request without a string arm")
            if type(replicate) is not int or replicate < 0:
                raise RefusalError(f"stage descriptor root {root_id} arm {arm} has a non-integer replicate")
            arm_reps = per_arm.setdefault(arm, [])
            if replicate in arm_reps:
                raise RefusalError(f"stage descriptor repeats slot {root_id}/{arm}/{replicate}")
            arm_reps.append(replicate)
        plan[root_id] = {arm: sorted(reps) for arm, reps in sorted(per_arm.items())}
        root_order.append(root_id)
    arms = sorted({arm for per_arm in plan.values() for arm in per_arm})
    if treatment is None or reference is None:
        raise RefusalError(
            "contrast arms unknown: pass --treatment-arm/--reference-arm or put "
            f"contrast.treatment/contrast.reference in the descriptor (arms present: {arms})"
        )
    for label, arm in (("treatment", treatment), ("reference", reference)):
        if arm not in arms:
            raise RefusalError(f"{label} arm {arm!r} is not assigned by the stage descriptor (arms: {arms})")
    if treatment == reference:
        raise RefusalError("treatment and reference arm must differ")
    return {"roots": plan, "root_order": root_order, "arms": arms,
            "treatment_arm": treatment, "reference_arm": reference}


def _outcome_of(record, slot):
    outcome, reason = record.get("outcome"), record.get("missing_reason")
    if outcome is None:
        if not isinstance(reason, str) or not reason.strip():
            raise RefusalError(f"slot {slot} has no outcome and no missing_reason; refusing to guess")
        return None, reason.strip()
    if isinstance(outcome, bool) or not isinstance(outcome, (int, float)) or outcome not in (0, 1):
        raise RefusalError(f"slot {slot} has outcome {outcome!r}; expected 0, 1 or null with a missing_reason")
    if isinstance(reason, str) and reason.strip():
        raise RefusalError(f"slot {slot} carries both an outcome and missing_reason {reason!r}")
    return int(outcome), None


def index_grades(grade_rows, plan):
    """Map each assigned slot to its record; refuse on unexpected, duplicate or silently absent slots."""
    assigned = {(r, a, rep) for r, per_arm in plan["roots"].items() for a, reps in per_arm.items() for rep in reps}
    indexed = {}
    for i, record in enumerate(grade_rows):
        root_id, arm, replicate = record.get("root_id"), record.get("arm"), record.get("replicate")
        slot = (root_id, arm, replicate)
        if root_id not in plan["roots"]:
            raise RefusalError(f"grades record {i} has unexpected root_id {root_id!r}; stage roots: {plan['root_order']}")
        if arm not in plan["roots"][root_id]:
            raise RefusalError(f"grades record {i} has unexpected arm {arm!r} for root {root_id}; "
                               f"stage arms at this root: {sorted(plan['roots'][root_id])}")
        if slot not in assigned:
            raise RefusalError(f"grades record {i} has unexpected replicate {replicate!r} for {root_id}/{arm}; "
                               f"assigned replicates: {plan['roots'][root_id][arm]}")
        if slot in indexed:
            raise RefusalError(f"grades file has duplicate records for slot {root_id}/{arm}/{replicate}")
        indexed[slot] = record
    absent = sorted(slot for slot in assigned if slot not in indexed)
    if absent:
        raise RefusalError("assigned slots absent from the grades file with no record and no missing_reason: "
                           + ", ".join(f"{r}/{a}/{rep}" for r, a, rep in absent))
    return indexed


def _usage_accumulator():
    acc = {}
    for field in USAGE_FIELDS:
        acc[f"{field}_known_sum"] = 0
        acc[f"{field}_unknown_count"] = 0
    return acc


def _accumulate_usage(acc, record, slot):
    for field in USAGE_FIELDS:
        value = record.get(field)
        if value is None:
            acc[f"{field}_unknown_count"] += 1
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise RefusalError(f"slot {slot} has {field}={value!r}; expected a nonnegative number or null")
        if field == "executor_seconds":
            acc[f"{field}_known_sum"] = round(acc[f"{field}_known_sum"] + float(value), 6)
        elif type(value) is int:
            acc[f"{field}_known_sum"] += value
        else:
            raise RefusalError(f"slot {slot} has non-integer {field}={value!r}")


def analyze(grade_rows, plan):
    indexed = index_grades(grade_rows, plan)
    usage_total, usage_by_arm = _usage_accumulator(), {arm: _usage_accumulator() for arm in plan["arms"]}
    per_root, slots = {}, []
    for root_id in plan["root_order"]:
        per_root[root_id] = {}
        for arm, replicates in plan["roots"][root_id].items():
            cell = {"assigned": len(replicates), "assigned_replicates": list(replicates),
                    "graded": 0, "passes": 0, "failures": 0, "missing": 0,
                    "missing_reasons": {}, "missing_replicates": [], "mean": None}
            for replicate in replicates:
                slot = (root_id, arm, replicate)
                record = indexed[slot]
                outcome, reason = _outcome_of(record, f"{root_id}/{arm}/{replicate}")
                if outcome is None:
                    cell["missing"] += 1
                    cell["missing_replicates"].append(replicate)
                    cell["missing_reasons"][reason] = cell["missing_reasons"].get(reason, 0) + 1
                else:
                    cell["graded"] += 1
                    cell["passes"] += outcome == 1
                    cell["failures"] += outcome == 0
                _accumulate_usage(usage_total, record, f"{root_id}/{arm}/{replicate}")
                _accumulate_usage(usage_by_arm[arm], record, f"{root_id}/{arm}/{replicate}")
                slots.append({"root_id": root_id, "arm": arm, "replicate": replicate,
                              "outcome": outcome, "missing_reason": reason,
                              "output_sha256": record.get("output_sha256")})
            if cell["graded"]:
                cell["mean"] = cell["passes"] / cell["graded"]
            cell["missing_reasons"] = dict(sorted(cell["missing_reasons"].items()))
            per_root[root_id][arm] = cell

    treatment, reference = plan["treatment_arm"], plan["reference_arm"]
    contrasts, values = [], []
    for root_id in plan["root_order"]:
        t, r = per_root[root_id].get(treatment), per_root[root_id].get(reference)
        if t is None or r is None:
            raise RefusalError(f"root {root_id} does not assign both contrast arms {treatment} and {reference}")
        difference = None if t["mean"] is None or r["mean"] is None else t["mean"] - r["mean"]
        unavailable = None if difference is not None else (
            f"no available outcome for {treatment}" if t["mean"] is None else f"no available outcome for {reference}")
        contrasts.append({
            "root_id": root_id,
            f"{treatment}_passes": t["passes"], f"{treatment}_graded": t["graded"],
            f"{treatment}_assigned": t["assigned"], f"{treatment}_missing": t["missing"],
            f"{treatment}_mean": t["mean"],
            f"{reference}_passes": r["passes"], f"{reference}_graded": r["graded"],
            f"{reference}_assigned": r["assigned"], f"{reference}_missing": r["missing"],
            f"{reference}_mean": r["mean"],
            "difference": difference, "difference_unavailable_reason": unavailable,
        })
        values.append(difference)
    complete = all(v is not None for v in values)
    finite = {
        "label": f"equally weighted mean of the per-root {treatment}-minus-{reference} differences over the "
                 f"{len(values)} fixed development-selected checkpoints",
        "quantity_type": "finite-checkpoint descriptive quantity (no population target, no inference)",
        "checkpoints": list(plan["root_order"]),
        "n_checkpoints": len(values),
        "contrast": (sum(values) / len(values)) if complete else None,
        "contrast_unavailable_reason": None if complete else "one or more per-root differences are unavailable",
        "per_root_differences": {c["root_id"]: c["difference"] for c in contrasts},
        "no_population_interval": True, "no_test": True, "no_p_value": True,
        "no_significance_language": NO_SIGNIFICANCE_STATEMENT,
        "tie_is_inconclusive": TIE_STATEMENT,
        "pooling": "not pooled with E12; E12 replicates are a separate frozen stage",
    }
    accounting = {
        "assigned_slots": len(slots),
        "graded_slots": sum(1 for s in slots if s["outcome"] is not None),
        "missing_slots": [{"root_id": s["root_id"], "arm": s["arm"], "replicate": s["replicate"],
                           "missing_reason": s["missing_reason"]} for s in slots if s["outcome"] is None],
        "assigned_by_arm": {arm: sum(len(plan["roots"][r].get(arm, [])) for r in plan["root_order"])
                            for arm in plan["arms"]},
        "graded_by_arm": {arm: sum(1 for s in slots if s["arm"] == arm and s["outcome"] is not None)
                          for arm in plan["arms"]},
        "usage_totals": usage_total,
        "usage_by_arm": usage_by_arm,
    }
    return {"per_root": per_root, "per_root_contrasts": contrasts,
            "finite_checkpoint_contrast": finite, "accounting": accounting, "slots": slots}


def build_report(grades_path, descriptor_path, descriptor, plan, grade_rows, stage_id=None):
    result = analyze(grade_rows, plan)
    return {
        "analysis_version": ANALYSIS_VERSION,
        "evidence_class": EVIDENCE_CLASS,
        "stage_id": (stage_id or descriptor.get("stage_id") or descriptor.get("plan_version")
                     or descriptor.get("stage") or "unknown"),
        "stage_status_as_recorded": descriptor.get("status", "unknown"),
        "stage_evidence_class_as_recorded": descriptor.get("evidence_class", "unknown"),
        "stage_not_a_test_of_as_recorded": descriptor.get("not_a_test_of", "unknown"),
        "stage_interpretation_rules_as_recorded": descriptor.get("interpretation_rules", "unknown"),
        "primary_endpoint": "frozen private-suite-plus-format score as recorded in the grades file; "
                            "checkpoint selection and gating derive from frozen public diagnostics only",
        "inputs": {
            "grades": {"path": str(grades_path), "sha256": _sha256(grades_path), "records": len(grade_rows)},
            "stage_descriptor": {"path": str(descriptor_path), "sha256": _sha256(descriptor_path)},
        },
        "plan_validated_against": {
            "root_order": plan["root_order"], "arms": plan["arms"],
            "treatment_arm": plan["treatment_arm"], "reference_arm": plan["reference_arm"],
            "assigned_replicates": {r: plan["roots"][r] for r in plan["root_order"]},
        },
        "metric_definitions": METRIC_DEFINITIONS,
        "statements": {"no_significance": NO_SIGNIFICANCE_STATEMENT, "tie_inconclusive": TIE_STATEMENT},
        **result,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--grades", type=Path, required=True, help="JSONL grades file (E12 D/grades.jsonl record shape)")
    ap.add_argument("--stage", type=Path, required=True, help="stage descriptor JSON (e.g. the E13a request plan)")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--treatment-arm", default=None)
    ap.add_argument("--reference-arm", default=None)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit(f"Refusing to overwrite {a.out}")
    descriptor = json.loads(a.stage.read_text())
    try:
        plan = plan_from_descriptor(descriptor, a.treatment_arm, a.reference_arm)
        report = build_report(a.grades, a.stage, descriptor, plan, load_jsonl(a.grades))
    except RefusalError as exc:
        raise SystemExit(f"Refusing to analyze: {exc}") from exc
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({"finite_checkpoint_contrast": report["finite_checkpoint_contrast"]["contrast"],
                      "per_root_differences": report["finite_checkpoint_contrast"]["per_root_differences"],
                      "graded_slots": report["accounting"]["graded_slots"],
                      "assigned_slots": report["accounting"]["assigned_slots"]}, indent=1))


if __name__ == "__main__":
    main()
