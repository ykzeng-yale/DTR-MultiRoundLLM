"""Descriptive five-arm diagnostic analyzer on synthetic records; nothing is executed."""
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.landmark import analyze_diagnostic as ad


def diag(rid, *statuses):
    return {"schema_version": ad.SCHEMA, "root_id": rid, "initial_artifact_sha256": "a" * 64,
            "cases": [{"case_id": f"c{i}", "call": "f(1)", "expected": 1, "status": s,
                       "returned": None, "value_kind": "none", "reason": None} for i, s in enumerate(statuses)]}


def rec(r, g, pt=100, ct=50, reason=None):
    return {"replicate": r, "grade": g, "missing_reason": reason, "calls": 1, "prompt_tokens": pt,
            "completion_tokens": ct, "executor_starts": 1, "executor_seconds": 0.5}


def root(rid, stop, arms, initial=None):
    row = {"root_id": rid, "family_id": "fam", "initial": initial or {"calls": 1, "prompt_tokens": 80, "completion_tokens": 40},
           "diagnostic_cost": {"executor_starts": 1, "executor_seconds": 2.0},
           "arms": {"STOP": [rec(0, stop)]}}
    for arm, gs in arms.items():
        row["arms"][arm] = [rec(i, g) for i, g in enumerate(gs)]
    return row


FULL = {"N0": (0, 0), "S0": (1, 0), "N1": (1, 1), "S1": (1, 1), "R1": (0, 1)}


@pytest.fixture
def data():
    roots = [root("r0", 1, FULL),                                                   # public all_pass, private pass
             root("r1", 0, {**FULL, "N1": (0, 1), "S1": (1, 0)}),                   # any_fail, fail; S1-N1 tie at .5
             root("r2", None, {**FULL, "S1": (1, 1), "N1": (0, 0)}),                # unknown (all unavailable), unknown
             root("r3", 0, {**FULL, "S1": (0, 0)})]                                 # no diagnostic -> unknown, fail
    diags = {"r0": diag("r0", "pass", "pass", "pass"),
             "r1": diag("r1", "pass", "timeout", "wrong_value"),                   # fail wins over timeout
             "r2": diag("r2", "unavailable", "unavailable", "unavailable")}
    return roots, diags


def test_arm_means_contrast_order_and_ties(data):
    rep = ad.analyze(*data)
    assert rep["arms"] == ["STOP", "N0", "S0", "N1", "S1", "R1"]
    names = list(rep["contrasts"])
    assert names[:4] == ["S1_minus_N1", "N1_minus_N0", "S0_minus_N0", "R1_minus_N1"]
    assert names[4:] == [f"{a}_minus_STOP" for a in ("N0", "S0", "N1", "S1", "R1")]
    assert [k for k, v in rep["contrasts"].items() if v["primary"]] == ["S1_minus_N1"]
    s1 = rep["quality"]["S1"]
    assert [p["value"] for p in s1["per_root"]] == [1.0, 0.5, 1.0, 0.0]
    assert s1["mean_complete_roots"] == pytest.approx(0.625)
    c = rep["contrasts"]["S1_minus_N1"]
    assert [p["value"] for p in c["per_root"]] == [0.0, 0.0, 1.0, -1.0]
    assert (c["positive"], c["ties"], c["negative"]) == (1, 2, 1)
    assert c["mean_complete_pairs"] == 0.0 and c["complete_pairs"] == 4
    # STOP has a missing grade on r2: the STOP contrasts lose that root, never impute it.
    st = rep["contrasts"]["S1_minus_STOP"]
    assert st["missing_pair_roots"] == 1 and st["per_root"][2]["value"] is None
    assert st["per_root"][0]["value"] == 0.0 and st["per_root"][1]["value"] == 0.5


def test_no_intervals_anywhere_and_note(data):
    rep = ad.analyze(*data)
    assert rep["inference"]["confidence_intervals"] is None
    assert "No confidence intervals" in rep["inference"]["note"] and "one unresolved family" in rep["inference"]["note"]
    text = repr(rep)
    assert "ci95" not in text and "'se'" not in text


def test_missing_grade_counted_not_dropped(data):
    roots, diags = data
    roots[0]["arms"]["N1"][1] = rec(1, None, reason="output_unavailable")
    del roots[1]["arms"]["R1"][1]                     # absent replicate record
    del roots[3]["arms"]["S0"]                        # whole arm absent
    roots[2]["arms"]["N0"][0]["grade"] = None         # None without reason
    rep = ad.analyze(roots, diags)
    q = rep["quality"]
    assert q["N1"]["missing_reasons"] == {"output_unavailable": 1}
    assert q["N1"]["per_root"][0]["value"] is None and q["N1"]["complete_roots"] == 3
    assert q["N1"]["incomplete_roots"] == 1 and q["N1"]["assigned_replicates"] == 8
    assert q["N1"]["all_assigned_mean_bounds"] == [pytest.approx(2.0 / 4), pytest.approx(2.5 / 4)]  # r0 (1,?) r1 (0,1) r2 (0,0) r3 (1,1)
    assert q["R1"]["missing_reasons"] == {"replicate_record_absent": 1}
    assert q["S0"]["missing_reasons"] == {"arm_record_absent": 2}
    assert q["N0"]["missing_reasons"] == {"ungraded_no_reason": 1}
    assert q["STOP"]["missing_reasons"] == {"ungraded_no_reason": 1} and q["STOP"]["missing_replicates"] == 1
    assert rep["contrasts"]["S1_minus_N1"]["missing_pair_roots"] == 1
    assert len(rep["contrasts"]["S1_minus_N1"]["per_root"]) == 4
    # Unknown cost components are counted, not zero-filled.
    assert rep["cost"]["arms"]["R1"]["totals"]["prompt_tokens"]["unknown_components"] == 1
    assert rep["cost"]["arms"]["S0"]["per_root_policy_mean"]["prompt_tokens"]["unknown_roots"] == 1
    assert rep["cost"]["arms"]["S0"]["totals"]["prompt_tokens"]["unknown_components"] == 2


def test_public_status_classification():
    assert ad.public_status(diag("x", "pass", "pass", "pass"), "x") == "all_pass"
    assert ad.public_status(diag("x", "unavailable", "unavailable", "unavailable"), "x") == "unknown"
    assert ad.public_status(diag("x", "pass", "output_limit", "pass"), "x") == "unknown"
    assert ad.public_status(diag("x", "timeout", "program_exception", "unavailable"), "x") == "any_fail"
    for s in ("wrong_value", "format_error", "interface_error", "program_exception"):
        assert ad.public_status(diag("x", "pass", s), "x") == "any_fail"
    assert ad.public_status(diag("x"), "x") == "unknown" and ad.public_status(None, "x") == "unknown"
    with pytest.raises(ValueError):
        ad.public_status(diag("x", "crashed"), "x")
    with pytest.raises(ValueError):
        ad.public_status(diag("y", "pass"), "x")
    with pytest.raises(ValueError):
        ad.public_status({**diag("x", "pass"), "schema_version": "v0"}, "x")


def test_field15_crosstab_and_strata(data):
    rep = ad.analyze(*data)
    ist = rep["initial_status"]
    assert ist["crosstab"] == {"all_pass": {"pass": 1, "fail": 0, "unknown": 0},
                               "any_fail": {"pass": 0, "fail": 1, "unknown": 0},
                               "unknown": {"pass": 0, "fail": 1, "unknown": 1}}
    assert ist["crosstab_roots"]["unknown"] == {"pass": [], "fail": ["r3"], "unknown": ["r2"]}
    assert ist["public_totals"] == {"all_pass": 1, "any_fail": 1, "unknown": 2}
    assert ist["private_totals"] == {"pass": 1, "fail": 2, "unknown": 1}
    assert ist["diagnostic_missing_roots"] == ["r3"]
    assert sum(ist["public_totals"].values()) == rep["n_roots"] == 4
    unk = ist["final_private_by_initial_public"]["unknown"]
    assert unk["n_roots"] == 2
    assert unk["arms"]["S1"]["mean_complete_roots"] == pytest.approx(0.5)
    assert unk["arms"]["STOP"] == {"mean_complete_roots": 0.0, "complete_roots": 1, "incomplete_roots": 1}
    assert "do not validate a learned conditional policy" in ist["note"]
    assert "final public-pass/private-fail" in ist["note"]


def test_all_unknown_diagnostics():
    roots = [root(f"u{i}", 1, FULL) for i in range(3)]
    diags = {f"u{i}": diag(f"u{i}", "unavailable", "timeout", "output_limit") for i in range(3)}
    ist = ad.analyze(roots, diags)["initial_status"]
    assert ist["public_totals"] == {"all_pass": 0, "any_fail": 0, "unknown": 3}
    assert ist["crosstab"]["unknown"]["pass"] == 3
    empty = ist["final_private_by_initial_public"]["all_pass"]
    assert empty["n_roots"] == 0 and empty["arms"]["S1"]["mean_complete_roots"] is None


def test_cost_accounting(data):
    roots, diags = data
    roots[0]["arms"]["R1"][0]["prompt_tokens"] = 60   # R1 omits the previous answer
    rep = ad.analyze(roots, diags)
    cost = rep["cost"]
    assert "Equal calls are not equal token/runtime cost" in cost["note"]
    assert cost["shared_initial"]["calls"] == {"known_sum": 4, "unknown_roots": 0}
    assert cost["shared_public_diagnostic"]["executor_seconds"] == {"known_sum": 8.0, "unknown_roots": 0}
    stop, n1, r1, n0 = (cost["arms"][a] for a in ("STOP", "N1", "R1", "N0"))
    assert stop["totals"]["calls"]["known_sum"] == 0 and stop["per_root_policy_mean"]["calls"]["mean_known_roots"] == 1
    assert n1["totals"]["calls"]["known_sum"] == 8 and n1["per_root_policy_mean"]["calls"]["mean_known_roots"] == 2
    assert r1["totals"]["calls"] == n1["totals"]["calls"]
    assert r1["totals"]["prompt_tokens"]["known_sum"] == 760 != n1["totals"]["prompt_tokens"]["known_sum"]
    assert n1["totals"]["grading_executor_starts"]["known_sum"] == 8
    assert n1["per_root_policy_mean"]["executor_seconds"]["mean_known_roots"] == 2.0
    assert n0["per_root_policy_mean"]["executor_seconds"]["mean_known_roots"] == 0
    assert n1["per_root_policy_mean"]["completion_tokens"]["mean_known_roots"] == 90


def test_validation_errors(data):
    roots, diags = data
    with pytest.raises(ValueError):
        ad.analyze(roots + [root("r0", 1, FULL)], diags)
    with pytest.raises(ValueError):
        ad.analyze(roots, {**diags, "zz": diag("zz", "pass")})
    bad = [dict(r) for r in roots]
    bad[0] = {**roots[0], "arms": {**roots[0]["arms"], "S1": [rec(0, True), rec(1, 1)]}}
    with pytest.raises(ValueError):
        ad.analyze(bad, diags)
    bad[0] = {**roots[0], "arms": {**roots[0]["arms"], "S1": [rec(0, 1), rec(0, 1)]}}
    with pytest.raises(ValueError):
        ad.analyze(bad, diags)
    bad[0] = {**roots[0], "arms": {**roots[0]["arms"], "X9": []}}
    with pytest.raises(ValueError):
        ad.analyze(bad, diags)
    with pytest.raises(ValueError):
        ad.analyze([{**roots[0], "initial_artifact_sha256": "b" * 64}], {"r0": diags["r0"]})
    bad[0] = {**roots[0], "arms": {**roots[0]["arms"], "S1": [rec(0, 1, pt=-3), rec(1, 1)]}}
    with pytest.raises(ValueError):
        ad.analyze(bad, diags)


def test_shared_contract_constants_agree_if_present():
    diagnostic = pytest.importorskip("experiments.landmark.diagnostic")
    assert diagnostic.SCHEMA == ad.SCHEMA


def test_v2_schema_accepted_and_reported(data):
    # MRL-16: v2 diagnostics carry the same case keys (repr-string displays); only statuses are read.
    roots, diags = data
    v2 = {rid: {**d, "schema_version": ad.SCHEMA_V2} for rid, d in diags.items()}
    rep1, rep2 = ad.analyze(roots, diags), ad.analyze(roots, v2)
    assert rep1["diagnostic_schema"] == "public-diagnostic-v1" and rep2["diagnostic_schema"] == "public-diagnostic-v2"
    assert rep1["initial_status"] == rep2["initial_status"] and rep1["quality"] == rep2["quality"]
    x = {**diag("x", "pass", "wrong_value"), "schema_version": ad.SCHEMA_V2}
    x["cases"][1].update(returned="'abc'", expected="('a', True)", value_kind="literal")
    assert ad.public_status(x, "x") == "any_fail"
    assert ad.analyze(roots, {})["diagnostic_schema"] == ad.SCHEMA


def test_mixed_or_unknown_schemas_refused(data):
    roots, diags = data
    first, *rest = sorted(diags)
    if rest:
        with pytest.raises(ValueError, match="one schema"):
            ad.analyze(roots, {**diags, first: {**diags[first], "schema_version": ad.SCHEMA_V2}})
    with pytest.raises(ValueError):
        ad.analyze(roots, {first: {**diags[first], "schema_version": "public-diagnostic-v3"}})


def test_v2_schema_constant_agrees_if_present():
    diagnostic = pytest.importorskip("experiments.landmark.diagnostic")
    if hasattr(diagnostic, "SCHEMA_V2"):
        assert diagnostic.SCHEMA_V2 == ad.SCHEMA_V2
