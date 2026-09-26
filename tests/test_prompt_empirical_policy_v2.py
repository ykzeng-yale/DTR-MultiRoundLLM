"""MRL-31 deterministic source fixtures for the v2 learner (LEAD-MEASUREMENT-01): unavailable histories are not common
outcomes. Toy supplied data only: no real-data fit, historical reanalysis, sampling, receiver or candidate execution."""
import ast
import builtins
import copy
import hashlib
import json
import subprocess
from fractions import Fraction
from pathlib import Path

import pytest

from experiments.prompt_choice import empirical_policy as v1
from experiments.prompt_choice import empirical_policy_v2 as v2
from experiments.prompt_choice import paired_inference as pinf

ROOT = Path(__file__).resolve().parents[1]
IDS = v2.load_identity()
IDS1 = v1.load_identity()
F = lambda d: Fraction(d["num"], d["den"])


def known(rid, pf, inc, patch, rethink):
    return {"root_id": rid, "state": {"has_payload_failure": pf, "has_incomplete": inc},
            "outcomes": {"PATCH": list(patch), "RETHINK": list(rethink)}}


def common(rid, y, disp="verified_common_fallback"):
    return {"root_id": rid, "state": None, "common_outcome": y, "invalid_disposition": disp}


def unavailable(rid, reason="initial_transport_missing"):
    return {"root_id": rid, "state": None, "history_unavailable_reason": reason}


def data(families, R=2):
    return {"partition": "development", "replicates": R,
            "families": [{"family_id": fid, "roots": roots} for fid, roots in families]}


MIXED = data([
    ("fam-A", [known("a1", False, False, [1, 1], [0, 1]), unavailable("a2"), known("a3", True, True, [0, None], [1, 0])]),
    ("fam-B", [known("b1", True, False, [0, 0], [1, 1]), common("b2", 1), unavailable("b3", "collection_cap_unattempted")]),
    ("fam-C", [known("c1", False, True, [None, 1], [1, 1]), known("c2", True, False, [1, 1], [0, 1])]),
    ("fam-D", [unavailable("d1", "history_record_unavailable")]),
])


def test_config_pins_contract_and_is_self_contained():
    cfg = json.loads((ROOT / "experiments/prompt_choice/empirical_policy_source_v2.json").read_text())
    blob = subprocess.run(["git", "-C", str(ROOT), "show", "23c652b:docs/policy_unavailable_history_contract_20260926.md"],
                          capture_output=True, check=True).stdout
    assert hashlib.sha256(blob).hexdigest() == cfg["contract"]["sha256"] and cfg["version"] == v2.VERSION
    assert cfg["source_only"] is True and cfg["collection_enabled"] is False
    for path, want in cfg["v1_preserved_not_a_dependency"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == want
    tree = ast.parse((ROOT / "experiments/prompt_choice/empirical_policy_v2.py").read_text())
    mods = {(n.module or "") for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | \
           {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert not any("experiments" in m or "empirical_policy" in m for m in mods)  # no hidden v1 dependency
    assert IDS["source_sha256"] == hashlib.sha256((ROOT / "experiments/prompt_choice/empirical_policy_v2.py").read_bytes()).hexdigest()


def test_exhaustive_16_maps_on_mixed_known_common_unavailable_rows():
    res = v2.fit(MIXED, IDS)
    rows = v2._rows(MIXED)
    maps = v2.all_maps()
    lows = [v2.value(rows, m)[0] for m in maps]
    assert v2.value(rows, res["report"]["d"])[0] == max(lows) == F(res["report"]["d_value"]["lower"])
    assert F(res["report"]["d_value"]["lower"]) >= F(res["report"]["b1_value"]["lower"])
    w_unavail = F(res["report"]["unavailable_history_weight"])
    for m in maps:  # each unavailable root adds 0 to every lower and exactly w to every upper
        lo, hi = v2.value(rows, m)
        known_common = [r for r in rows if r["kind"] != "unavailable"]
        klo, khi = v2.value(known_common, m)
        assert lo == klo and hi == khi + w_unavail
    assert w_unavail == Fraction(1, 12) + Fraction(1, 12) + Fraction(1, 4)


def test_denominator_retention_reverses_b1_when_an_unavailable_root_is_dropped():
    kept = data([("A", [known("a1", False, False, [0, 0], [1, 1]), unavailable("a2")]),
                 ("B", [known("b1", False, False, [1, 0], [0, 0])])])
    dropped = data([("A", [known("a1", False, False, [0, 0], [1, 1])]),
                    ("B", [known("b1", False, False, [1, 0], [0, 0])])])
    assert v2.fit(kept, IDS)["report"]["b1"] == "PATCH"      # 1/4 vs 1/4: tie -> PATCH
    assert v2.fit(dropped, IDS)["report"]["b1"] == "RETHINK"  # dropping the root inflates a1's weight to 1/2


def test_all_unavailable_histories():
    d = data([("A", [unavailable("a1"), unavailable("a2", "collection_cap_unattempted")]), ("B", [unavailable("b1")])])
    rep = v2.fit(d, IDS)["report"]
    assert set(rep["d"].values()) == {"PATCH"} and rep["b1"] == "PATCH" and rep["d_is_constant"]
    assert F(rep["d_value"]["lower"]) == 0 and F(rep["d_value"]["upper"]) == 1
    assert all(c["roots"] == 0 and c["distinct_families"] == 0 for c in rep["cells"].values())
    assert rep["roots"] == 3 and rep["families"] == 2 and rep["unavailable_history_count"] == 3


V1_FIXTURES = [
    data([("fam-A", [known("a1", False, False, [1, 1], [0, 1]), known("a2", True, False, [0, 0], [1, 1])]),
          ("fam-B", [known("b1", False, True, [0, None], [1, 0]), known("b2", True, True, [1, 0], [0, 0]),
                     known("b3", False, False, [0, 1], [1, 1]), common("b4", 1)]),
          ("fam-C", [known("c1", True, False, [1, 1], [0, 1])])]),
    data([("A", [known("a1", True, False, [None, None], [1, None]), common("a2", None)]),
          ("B", [known("b1", True, False, [1, 0], [1, 1])])]),
    data([("A", [known("a1", False, False, [1, 1], [0, 0])]), ("B", [known("b1", True, False, [0, 0], [1, 1])])]),
]


@pytest.mark.parametrize("fixture", V1_FIXTURES)
def test_v1_compatibility_when_no_unavailable_root_occurs(fixture):
    r1, r2 = v1.fit(fixture, IDS1)["report"], v2.fit(fixture, IDS)["report"]
    for key in ("d", "b1", "d_is_constant", "cells", "constant_values", "d_value", "b1_value", "missing_slots_total",
                "missing_common_outcomes", "roots", "families"):
        assert r1[key] == r2[key], key
    assert r1["actionable_roots"] == r2["known_history_roots"] and r1["nonactionable_roots"] == r2["verified_common_rows"]
    assert r2["unavailable_history_roots"] == [] and r2["unavailable_history_count"] == 0


def test_missing_history_and_common_rows_are_reported_separately_and_never_as_shared_outcomes():
    rep = v2.fit(MIXED, IDS)["report"]
    assert [r["root_id"] for r in rep["verified_common_rows"]] == ["b2"]
    un = {r["root_id"]: r for r in rep["unavailable_history_roots"]}
    assert set(un) == {"a2", "b3", "d1"}
    for r in un.values():
        assert r["label"] == "not a shared outcome" and [F(x) for x in r["marginal_policy_interval"]] == [0, 1]
        assert r["planned_slots_per_action"] == 2 and not ({"cell", "action", "grade", "primitive_id"} & set(r))
    assert un["b3"]["reason"] == "collection_cap_unattempted" and F(un["d1"]["weight"]) == Fraction(1, 4)
    assert rep["missing_slots_total"] == {"PATCH": 2, "RETHINK": 0} and rep["missing_common_outcomes"] == 0
    assert rep["roots"] == 9 and sum(c["roots"] for c in rep["cells"].values()) == 5  # support: known histories only
    assert not any("contrast" in k for k in rep)  # the fit API returns no contrast


def test_observed_incomplete_is_a_known_state_not_an_unavailable_history():
    d = data([("A", [known("a1", False, True, [1, 1], [0, 0])])])
    rep = v2.fit(d, IDS)["report"]
    assert rep["cells"]["01"]["roots"] == 1 and rep["unavailable_history_count"] == 0


def test_informative_loss_bookkeeping_needs_no_missing_at_random_assumption():
    # Loss concentrated where the known roots succeed: the lower criterion counts it as 0 and the upper as 1, whatever
    # the (unknown) mechanism; no imputation or MAR reweighting happens.
    d = data([("A", [known("a1", False, False, [1, 1], [1, 1]), unavailable("a2"), unavailable("a3")]),
              ("B", [known("b1", False, False, [0, 0], [0, 0])])])
    rep = v2.fit(d, IDS)["report"]
    lo, hi = F(rep["d_value"]["lower"]), F(rep["d_value"]["upper"])
    assert lo == Fraction(1, 6) and hi == Fraction(1, 6) + Fraction(2, 6)
    assert hi - lo == F(rep["unavailable_history_weight"])


def test_two_unknown_policy_scores_need_not_cancel():
    # Equal marginal intervals [0,1] do not make the realised scores equal: as distinct primitives the contrast is [-1, 1],
    # and only a declared shared execution would cancel. The v2 fit API adds no fake outcome or contrast.
    assert pinf.score_bounds([("patch_unknown", 1), ("rethink_unknown", -1)],
                             [("patch_unknown", 0, 1), ("rethink_unknown", 0, 1)]) == (-1, 1)
    assert pinf.score_bounds([("shared", 1), ("shared", -1)], [("shared", 0, 1)]) == (0, 0)
    art = v2.fit(data([("A", [unavailable("a1")])]), IDS)["artifact"]
    assert set(art) == {"version", "source_sha256", "config_sha256", "map", "b1"}


@pytest.mark.parametrize("mutate", [
    lambda d: d.update(partition="evaluation"),
    lambda d: d["families"][0]["roots"].append({"root_id": "z", "state": None, "history_unavailable_reason": "outage"}),
    lambda d: d["families"][0]["roots"].append({"root_id": "z", "state": None, "history_unavailable_reason": True}),
    lambda d: d["families"][0]["roots"].append({"root_id": "z", "state": {"has_payload_failure": False, "has_incomplete": False},
                                                "history_unavailable_reason": "initial_transport_missing"}),
    lambda d: d["families"][0]["roots"].append({"root_id": "z", "state": None, "history_unavailable_reason": "initial_transport_missing",
                                                "common_outcome": 1}),
    lambda d: d["families"][0]["roots"].append({"root_id": "z", "state": None, "history_unavailable_reason": "initial_transport_missing",
                                                "outcomes": {"PATCH": [1, 1], "RETHINK": [1, 1]}}),
    lambda d: d["families"][0]["roots"].append({"root_id": "z", "state": None, "history_unavailable_reason": "initial_transport_missing",
                                                "note": "x"}),
    lambda d: d["families"][0]["roots"].append(unavailable("a1")),                  # duplicate root id
    lambda d: d["families"][0]["roots"].append(unavailable("bad\ud800")),           # invalid UTF-8
    lambda d: d["families"][0]["roots"].append({"root_id": "z", "state": None}),     # incomplete shape
    lambda d: d.update(replicates=True),
])
def test_malformed_inputs_are_refused(mutate):
    d = copy.deepcopy(MIXED)
    mutate(d)
    with pytest.raises(v2.PolicyInputError):
        v2.fit(d, IDS)


def test_immutable_inputs_label_free_prediction_and_version_identity_refusal(monkeypatch):
    before = copy.deepcopy(MIXED)
    art = v2.fit(MIXED, IDS)["artifact"]
    assert MIXED == before and art["version"] == "empirical-policy-source-v2"
    assert not any(k in json.dumps(art) for k in ("a1", "fam-A", "unavailable", "root_id"))

    def boom(*a, **k):
        raise AssertionError("file access during fit/predict")
    monkeypatch.setattr(Path, "read_bytes", boom)
    monkeypatch.setattr(Path, "read_text", boom)
    monkeypatch.setattr(builtins, "open", boom)
    v2.fit(MIXED, IDS)
    for pf in (False, True):
        for inc in (False, True):
            assert v2.predict({"has_payload_failure": pf, "has_incomplete": inc}, art, IDS) == art["map"][f"{int(pf)}{int(inc)}"]
    with pytest.raises(v2.PolicyInputError):
        v2.predict({"has_payload_failure": True, "has_incomplete": False}, art, IDS1)  # a v1 identity is refused
    art1 = v1.fit(V1_FIXTURES[0], IDS1)["artifact"]
    with pytest.raises(v2.PolicyInputError):
        v2.predict({"has_payload_failure": True, "has_incomplete": False}, art1, IDS)  # a v1 artifact is refused
    with pytest.raises(v1.PolicyInputError):
        v1.predict({"has_payload_failure": True, "has_incomplete": False}, art, IDS1)  # and v1 refuses a v2 artifact
    with pytest.raises(v2.PolicyInputError):
        v2.predict({"has_payload_failure": True, "has_incomplete": False, "history_unavailable_reason": "x"}, art, IDS)


def test_integer_oracle_all_6561_assignments_against_an_independent_16_map_enumeration():
    # Lead-specified independent oracle (no _rows/value/all_maps): R=1; A=[known 00] weight 6/18; B=[known 01, unavailable]
    # weights 3/18; C=[known 10, known 11, common null] weights 2/18. Integer scores in eighteenths; lower null=0, upper null=1.
    import itertools
    cells, acts = ("00", "01", "10", "11"), ("PATCH", "RETHINK")
    weight = dict(zip(cells, (6, 3, 2, 2)))
    maps = [dict(zip(cells, m)) for m in itertools.product(acts, repeat=4)]
    assert len(maps) == 16
    for ys in itertools.product((0, 1, None), repeat=8):
        y = {(c, a): ys[2 * i + j] for i, c in enumerate(cells) for j, a in enumerate(acts)}
        k = lambda rid, c: {"root_id": rid, "state": {"has_payload_failure": c[0] == "1", "has_incomplete": c[1] == "1"},
                            "outcomes": {a: [y[c, a]] for a in acts}}
        d = {"partition": "development", "replicates": 1, "families": [
            {"family_id": "A", "roots": [k("a00", "00")]},
            {"family_id": "B", "roots": [k("b01", "01"), unavailable("bu", "history_record_unavailable")]},
            {"family_id": "C", "roots": [k("c10", "10"), k("c11", "11"), common("cc", None)]}]}
        lo = lambda m: sum(weight[c] * (y[c, m[c]] == 1) for c in cells)
        hi = lambda m: sum(weight[c] * (y[c, m[c]] != 0) for c in cells) + 3 + 2  # unavailable 3/18 + common null 2/18
        b1 = "RETHINK" if lo(dict.fromkeys(cells, "RETHINK")) > lo(dict.fromkeys(cells, "PATCH")) else "PATCH"
        want_d = {c: "RETHINK" if y[c, "RETHINK"] == 1 and y[c, "PATCH"] != 1 else
                     "PATCH" if y[c, "PATCH"] == 1 and y[c, "RETHINK"] != 1 else b1 for c in cells}
        best = max(lo(m) for m in maps)
        rep = v2.fit(d, IDS)["report"]
        assert rep["b1"] == b1 and rep["d"] == want_d and lo(want_d) == best, ys
        assert F(rep["d_value"]["lower"]) == Fraction(best, 18) and F(rep["d_value"]["upper"]) == Fraction(hi(want_d), 18), ys
        b1m = dict.fromkeys(cells, b1)
        assert (F(rep["b1_value"]["lower"]), F(rep["b1_value"]["upper"])) == (Fraction(lo(b1m), 18), Fraction(hi(b1m), 18)), ys
        for a in acts:
            cm = dict.fromkeys(cells, a)
            assert (F(rep["constant_values"][a]["lower"]), F(rep["constant_values"][a]["upper"])) == \
                   (Fraction(lo(cm), 18), Fraction(hi(cm), 18)), ys
            assert rep["missing_slots_total"][a] == sum(y[c, a] is None for c in cells), ys
        for c in cells:
            assert rep["cells"][c]["tie_or_unseen_used_b1"] == ((y[c, "RETHINK"] == 1) == (y[c, "PATCH"] == 1)), ys
        assert F(rep["unavailable_history_weight"]) == Fraction(3, 18) and rep["unavailable_history_count"] == 1
        assert [(r["root_id"], F(r["weight"]), [F(x) for x in r["common_interval"]]) for r in rep["verified_common_rows"]] \
            == [("cc", Fraction(2, 18), [0, 1])] and rep["missing_common_outcomes"] == 1
        assert [(r["root_id"], F(r["weight"])) for r in rep["unavailable_history_roots"]] == [("bu", Fraction(3, 18))]
