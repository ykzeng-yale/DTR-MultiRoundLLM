"""Supplied-data empirical learner v2: MRL-31 source-only implementation of LEAD-MEASUREMENT-01, extending
LEAD-POLICY-17. Self-contained: it does not import v1, and v1, the renderer and the inference files are unchanged.

v2 adds one root shape, an UNAVAILABLE HISTORY {root_id, state: null, history_unavailable_reason}. Such a root keeps
its original family/root weight. Every policy's marginal score interval is [0, 1], so it adds 0 to the lower criterion
and w to the upper criterion for EVERY map. It is NOT a shared outcome: no state, cell, action, grade or primitive is
imputed. Two unknown policy scores need not cancel in a contrast, and this API returns no contrast.

fit/predict are pure and in memory: no file reads, file discovery, historical-outcome loading, receiver dispatch,
network or candidate execution. Source/config identities come only from the separate load_identity() helper, which
reads exactly the two named package files, and are passed in explicitly. Identity syntax and internal equality do NOT
prove a trusted execution freeze or external roster provenance. The caller supplies the development
records. This API cannot establish provenance, family independence or planned-roster completeness, and a future adapter
must bind the inputs to a committed development manifest.

Features are the two public Booleans from the accepted MRL-26 renderer. The cell label is
f"{int(has_payload_failure)}{int(has_incomplete)}", giving the ordered cells 00, 01, 10, 11. Scores are exact Fractions.
Weights are w_gi = 1/(G * m_g). A missing slot contributes [0, 1] over the planned replicate count R.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from fractions import Fraction
from itertools import product
from pathlib import Path

VERSION = "empirical-policy-source-v2"
ACTIONS = ("PATCH", "RETHINK")
FEATURES = ("has_payload_failure", "has_incomplete")
CELLS = ("00", "01", "10", "11")
HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "empirical_policy_source_v2.json"
SOURCE_PATH = HERE / "empirical_policy_v2.py"
UNAVAILABLE_REASONS = ("initial_transport_missing", "history_record_unavailable", "collection_cap_unattempted")


class PolicyInputError(ValueError):
    """Explicit refusal before any fitting."""


def raw_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def object_sha256(obj) -> str:
    """Canonical serialized-object hash: sorted keys, compact separators, UTF-8, no ASCII escaping."""
    return raw_sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def frac(x: Fraction) -> dict:
    return {"num": x.numerator, "den": x.denominator}


def load_identity() -> dict:
    """The only file access in this module besides load_config: raw-byte SHA256 of exactly the two named package
    files (this module and its config). No data discovery. Not proof of a trusted execution freeze or roster provenance."""
    return {"source_sha256": raw_sha256(SOURCE_PATH.read_bytes()), "config_sha256": raw_sha256(CONFIG_PATH.read_bytes())}


def _identities(ids, what="identities"):
    if (type(ids) is not dict or set(ids) != {"source_sha256", "config_sha256"}
            or not all(type(v) is str and re.fullmatch(r"[0-9a-f]{64}", v) for v in ids.values())):
        raise PolicyInputError(f"{what} must be exactly source_sha256 and config_sha256 as 64 lowercase hex")
    return dict(ids)


def cell_of(state: dict) -> str:
    return f"{int(state['has_payload_failure'])}{int(state['has_incomplete'])}"


# ---------------------------------------------------------------- validation
def _text(value, what):
    if type(value) is not str or not value:
        raise PolicyInputError(f"{what} must be a nonempty string")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise PolicyInputError(f"{what} is not valid UTF-8 text") from None
    return value


def _score(v, what):
    if v is None or (type(v) is int and v in (0, 1)):
        return v
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        raise PolicyInputError(f"{what}: NaN/infinity is not a score")
    raise PolicyInputError(f"{what}: a slot must be integer 0, integer 1 or null (Boolean and fractional refused)")


def _state(state, what):
    if type(state) is not dict or set(state) != set(FEATURES) or not all(type(state[f]) is bool for f in FEATURES):
        raise PolicyInputError(f"{what}: state must have exactly the two Boolean public features")
    return state


def validate(data) -> None:
    if type(data) is not dict or set(data) != {"partition", "replicates", "families"}:
        raise PolicyInputError("input must have exactly partition, replicates, families")
    if data["partition"] != "development":
        raise PolicyInputError("partition must be 'development'")
    R = data["replicates"]
    if type(R) is not int or R < 1:
        raise PolicyInputError("replicates must be a positive integer (Boolean refused)")
    fams = data["families"]
    if type(fams) is not list or not fams:
        raise PolicyInputError("families must be a nonempty list")
    fam_ids, root_ids = set(), set()
    for f in fams:
        if type(f) is not dict or set(f) != {"family_id", "roots"}:
            raise PolicyInputError("each family must have exactly family_id and roots")
        fid = _text(f["family_id"], "family_id")
        if fid in fam_ids:
            raise PolicyInputError(f"duplicate family_id {fid!r}")
        fam_ids.add(fid)
        if type(f["roots"]) is not list or not f["roots"]:
            raise PolicyInputError(f"family {fid!r} must have a nonempty root list")
        for r in f["roots"]:
            if type(r) is not dict:
                raise PolicyInputError("root must be an object")
            if set(r) == {"root_id", "state", "outcomes"} and r["state"] is not None:
                rid = _text(r["root_id"], "root_id")
                _state(r["state"], rid)
                o = r["outcomes"]
                if type(o) is not dict or set(o) != set(ACTIONS):
                    raise PolicyInputError(f"{rid}: outcomes must have exactly PATCH and RETHINK")
                for a in ACTIONS:
                    if type(o[a]) is not list or len(o[a]) != R:
                        raise PolicyInputError(f"{rid}: {a} must list exactly {R} replicate slots")
                    for i, v in enumerate(o[a]):
                        _score(v, f"{rid}/{a}/{i}")
            elif set(r) == {"root_id", "state", "common_outcome", "invalid_disposition"} and r["state"] is None:
                rid = _text(r["root_id"], "root_id")
                _score(r["common_outcome"], f"{rid}/common_outcome")
                _text(r["invalid_disposition"], f"{rid}/invalid_disposition")
            elif set(r) == {"root_id", "state", "history_unavailable_reason"} and r["state"] is None:
                rid = _text(r["root_id"], "root_id")
                if type(r["history_unavailable_reason"]) is not str or r["history_unavailable_reason"] not in UNAVAILABLE_REASONS:
                    raise PolicyInputError(f"{rid}: history_unavailable_reason must be one of {UNAVAILABLE_REASONS}")
            else:
                raise PolicyInputError("root must be exactly {root_id, state, outcomes} (known history), "
                                       "{root_id, state: null, common_outcome, invalid_disposition} (verified common) or "
                                       "{root_id, state: null, history_unavailable_reason} (unavailable history)")
            if rid in root_ids:
                raise PolicyInputError(f"duplicate root_id {rid!r}")
            root_ids.add(rid)


# ---------------------------------------------------------------- fitting
def _rows(data):
    """Canonically ordered weighted rows. Identifier contents order the output only; they never choose an action."""
    R, fams = data["replicates"], sorted(data["families"], key=lambda f: f["family_id"])
    G = len(fams)
    rows = []
    for f in fams:
        w = Fraction(1, G * len(f["roots"]))
        for r in sorted(f["roots"], key=lambda r: r["root_id"]):
            if r["state"] is None and "history_unavailable_reason" in r:
                rows.append({"family_id": f["family_id"], "root_id": r["root_id"], "w": w, "cell": None, "kind": "unavailable",
                             "reason": r["history_unavailable_reason"]})
            elif r["state"] is None:
                y = r["common_outcome"]
                lo, hi = (Fraction(y), Fraction(y)) if y is not None else (Fraction(0), Fraction(1))
                rows.append({"family_id": f["family_id"], "root_id": r["root_id"], "w": w, "cell": None, "kind": "common",
                             "common": (lo, hi), "missing_common": int(y is None), "disposition": r["invalid_disposition"]})
            else:
                bounds, missing = {}, {}
                for a in ACTIONS:
                    slots = r["outcomes"][a]
                    miss = sum(v is None for v in slots)
                    lo = Fraction(sum(v for v in slots if v is not None), R)
                    bounds[a], missing[a] = (lo, lo + Fraction(miss, R)), miss
                rows.append({"family_id": f["family_id"], "root_id": r["root_id"], "w": w, "cell": cell_of(r["state"]),
                             "kind": "known", "bounds": bounds, "missing": missing})
    return rows


def value(rows, mapping) -> tuple:
    """Exact (lower, upper) criterion of a map {cell: action}; common roots add identically for every map."""
    lo = hi = Fraction(0)
    for r in rows:
        if r["kind"] == "unavailable":  # [0, 1] for every policy: 0 to the lower, w to the upper, for every map
            hi += r["w"]
        elif r["kind"] == "common":
            lo += r["w"] * r["common"][0]
            hi += r["w"] * r["common"][1]
        else:
            b = r["bounds"][mapping[r["cell"]]]
            lo += r["w"] * b[0]
            hi += r["w"] * b[1]
    return lo, hi


def all_maps():
    return [dict(zip(CELLS, acts)) for acts in product(ACTIONS, repeat=len(CELLS))]


def fit(data, identities) -> dict:
    """Validate (before any copy; typed-leaf validation also refuses cyclic structures), then return
    {'artifact': prediction artifact, 'report': fit report}. In memory only; the input is never mutated."""
    ids = _identities(identities)
    validate(data)
    snapshot = copy.deepcopy(data)
    rows = _rows(snapshot)
    const = {a: value(rows, dict.fromkeys(CELLS, a)) for a in ACTIONS}
    b1 = "RETHINK" if const["RETHINK"][0] > const["PATCH"][0] else "PATCH"  # quality tie rule, not a cost claim
    d, cells = {}, {}
    for c in CELLS:
        rc = [r for r in rows if r["cell"] == c]
        s = {a: sum((r["w"] * r["bounds"][a][0] for r in rc), Fraction(0)) for a in ACTIONS}
        d[c] = "RETHINK" if s["RETHINK"] > s["PATCH"] else "PATCH" if s["PATCH"] > s["RETHINK"] else b1
        cells[c] = {"action": d[c], "distinct_families": len({r["family_id"] for r in rc}), "roots": len(rc),
                    "weight": frac(sum((r["w"] for r in rc), Fraction(0))),
                    "weighted_lower_sum": {a: frac(s[a]) for a in ACTIONS},
                    "missing_slots": {a: sum(r["missing"][a] for r in rc) for a in ACTIONS},
                    "tie_or_unseen_used_b1": s["RETHINK"] == s["PATCH"]}
    d_lo, d_hi = value(rows, d)
    b_lo, b_hi = value(rows, dict.fromkeys(CELLS, b1))
    artifact = {"version": VERSION, **ids, "map": dict(d), "b1": b1}
    report = {"version": VERSION, "partition": "development", "replicates": snapshot["replicates"],
              "families": len(snapshot["families"]), "roots": len(rows),
              "known_history_roots": [{"family_id": r["family_id"], "root_id": r["root_id"], "weight": frac(r["w"]), "cell": r["cell"],
                                    "planned_slots": snapshot["replicates"],
                                    "actions": {a: {"interval": [frac(r["bounds"][a][0]), frac(r["bounds"][a][1])],
                                                    "missing": r["missing"][a]} for a in ACTIONS}}
                                   for r in rows if r["kind"] == "known"],
              "verified_common_rows": [{"family_id": r["family_id"], "root_id": r["root_id"], "weight": frac(r["w"]),
                                        "common_interval": [frac(r["common"][0]), frac(r["common"][1])],
                                        "missing": r["missing_common"], "invalid_disposition": r["disposition"]}
                                       for r in rows if r["kind"] == "common"],
              "unavailable_history_roots": [{"family_id": r["family_id"], "root_id": r["root_id"], "weight": frac(r["w"]),
                                             "reason": r["reason"], "planned_slots_per_action": snapshot["replicates"],
                                             "marginal_policy_interval": [frac(Fraction(0)), frac(Fraction(1))],
                                             "label": "not a shared outcome"}
                                            for r in rows if r["kind"] == "unavailable"],
              "unavailable_history_count": sum(r["kind"] == "unavailable" for r in rows),
              "unavailable_history_weight": frac(sum((r["w"] for r in rows if r["kind"] == "unavailable"), Fraction(0))),
              "cells": cells, "b1": b1, "d": dict(d), "d_is_constant": len(set(d.values())) == 1,
              "constant_values": {a: {"lower": frac(const[a][0]), "upper": frac(const[a][1])} for a in ACTIONS},
              "d_value": {"lower": frac(d_lo), "upper": frac(d_hi)},
              "b1_value": {"lower": frac(b_lo), "upper": frac(b_hi)},
              "missing_slots_total": {a: sum(r["missing"][a] for r in rows if r["kind"] == "known") for a in ACTIONS},
              "missing_common_outcomes": sum(r["missing_common"] for r in rows if r["kind"] == "common"),
              "identity_note": "source/config identity checks are not proof of a future trial freeze or of external roster provenance",
              "interpretation": "training criterion only: not an estimate of selected-policy value, a confidence "
                                "bound or evidence of improvement; counts are support diagnostics, not sample sizes"}
    if data != snapshot:
        raise RuntimeError("input was mutated during fitting")
    return {"artifact": artifact, "report": report}


# ---------------------------------------------------------------- prediction
def validate_artifact(artifact, expected_identities) -> dict:
    if type(artifact) is not dict or set(artifact) != {"version", "source_sha256", "config_sha256", "map", "b1"}:
        raise PolicyInputError("artifact must have exactly version, source_sha256, config_sha256, map, b1")
    if artifact["version"] != VERSION:
        raise PolicyInputError("artifact version mismatch")
    expected = _identities(expected_identities, "expected_identities")
    if artifact["source_sha256"] != expected["source_sha256"] or artifact["config_sha256"] != expected["config_sha256"]:
        raise PolicyInputError("artifact source/config identity does not match the supplied expected identities")
    m = artifact["map"]
    if type(m) is not dict or set(m) != set(CELLS) or not all(m[c] in ACTIONS for c in CELLS) or artifact["b1"] not in ACTIONS:
        raise PolicyInputError("artifact map must assign PATCH or RETHINK to exactly cells 00, 01, 10, 11")
    return artifact


def predict(features, artifact, expected_identities) -> str:
    """Label-free and in memory: exactly the two Boolean public features, a strictly validated artifact, and the
    explicitly supplied expected identities."""
    _state(features, "features")
    return validate_artifact(artifact, expected_identities)["map"][cell_of(features)]


def nonactionable(artifact, expected_identities) -> dict:
    """For state null: an explicit nonactionable disposition. It is not a prompt action, STOP or an inferred PASS."""
    validate_artifact(artifact, expected_identities)
    return {"disposition": "nonactionable", "prompt_action": None}


def load_config() -> dict:
    """Separate explicit loader for the one named package config; not used by fit/predict."""
    cfg = json.loads(CONFIG_PATH.read_text())
    if cfg.get("source_only") is not True or cfg.get("collection_enabled") is not False:
        raise PolicyInputError("config must be source_only true and collection_enabled false")
    return cfg
