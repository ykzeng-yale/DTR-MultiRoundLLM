"""MRL-28 deterministic source fixtures for the supplied-data empirical learner (LEAD-POLICY-17).
Toy inputs only: no historical-data fit, sampled simulation, receiver or candidate execution, and no policy evidence."""
import ast
import builtins
import copy
import hashlib
import json
import subprocess
from fractions import Fraction
from pathlib import Path

import pytest

from experiments.prompt_choice import empirical_policy as ep

ROOT = Path(__file__).resolve().parents[1]
IDS = ep.load_identity()
F = lambda d: Fraction(d["num"], d["den"])


def act(rid, pf, inc, patch, rethink):
    return {"root_id": rid, "state": {"has_payload_failure": pf, "has_incomplete": inc},
            "outcomes": {"PATCH": list(patch), "RETHINK": list(rethink)}}


def common(rid, y, disp="initial_receiver_failure_without_artifact"):
    return {"root_id": rid, "state": None, "common_outcome": y, "invalid_disposition": disp}


def data(families, R=2):
    return {"partition": "development", "replicates": R,
            "families": [{"family_id": fid, "roots": roots} for fid, roots in families]}


def J(fitres_rows, mapping):
    return ep.value(fitres_rows, mapping)[0]


# ---- configuration and pins
def test_config_pins_contract_and_accepted_mrl26():
    cfg = ep.load_config()
    assert cfg["source_only"] is True and cfg["collection_enabled"] is False and cfg["real_data_fit_authorized"] is False
    blob = subprocess.run(["git", "-C", str(ROOT), "show", "b113895:docs/policy_learning_contract_20260926.md"],
                          capture_output=True, check=True).stdout
    assert hashlib.sha256(blob).hexdigest() == cfg["contract"]["sha256"]
    for path in ("experiments/prompt_choice/patch_rethink.py", "experiments/prompt_choice/patch_rethink_source_v1.json"):
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == cfg["accepted_mrl26"][path]
    assert {"raw", "object"} <= set(cfg["hash_conventions"])
    assert IDS == {"source_sha256": hashlib.sha256((ROOT / "experiments/prompt_choice/empirical_policy.py").read_bytes()).hexdigest(),
                   "config_sha256": hashlib.sha256((ROOT / "experiments/prompt_choice/empirical_policy_source_v1.json").read_bytes()).hexdigest()}
    assert ep.object_sha256({"b": 1, "a": "é"}) == hashlib.sha256('{"a":"é","b":1}'.encode()).hexdigest()


# ---- optimization
UNEQUAL = data([
    ("fam-A", [act("a1", False, False, [1, 1], [0, 1]), act("a2", True, False, [0, 0], [1, 1])]),
    ("fam-B", [act("b1", False, True, [0, None], [1, 0]), act("b2", True, True, [1, 0], [0, 0]),
               act("b3", False, False, [0, 1], [1, 1]), common("b4", 1)]),
    ("fam-C", [act("c1", True, False, [1, 1], [0, 1])]),
])


def test_exhaustive_16_maps_d_maximizes_the_criterion_and_dominates_b1():
    res = ep.fit(UNEQUAL, IDS)
    rows = ep._rows(UNEQUAL)
    maps = ep.all_maps()
    assert len(maps) == 16 and len({tuple(m.values()) for m in maps}) == 16
    best = max(J(rows, m) for m in maps)
    d = res["report"]["d"]
    assert J(rows, d) == best == F(res["report"]["d_value"]["lower"])
    assert F(res["report"]["d_value"]["lower"]) >= F(res["report"]["b1_value"]["lower"])
    const = {a: J(rows, dict.fromkeys(ep.CELLS, a)) for a in ep.ACTIONS}
    assert res["report"]["b1"] == ("RETHINK" if const["RETHINK"] > const["PATCH"] else "PATCH")


def test_family_weighting_can_choose_a_different_b1_than_root_pooling():
    d = data([("A", [act("a1", False, False, [0, 0], [1, 1])]),
              ("B", [act("b1", False, False, [1, 1], [0, 0]), act("b2", False, False, [1, 1], [0, 0]),
                     act("b3", False, False, [0, 0], [0, 0])])])
    assert ep.fit(d, IDS)["report"]["b1"] == "RETHINK"  # family weights: R = 1/2 > P = 1/3
    pooled = {a: sum(sum(r["outcomes"][a]) for f in d["families"] for r in f["roots"]) for a in ep.ACTIONS}
    assert pooled["PATCH"] > pooled["RETHINK"]  # root pooling would choose PATCH


def test_cell_ties_and_unseen_cells_fall_back_to_b1_and_mixed_state_is_its_own_cell():
    d = data([("A", [act("a1", False, False, [1, 0], [0, 1]),       # cell 00: exact tie
                     act("a2", True, True, [0, 0], [1, 1])]),        # cell 11 (mixed): RETHINK
              ("B", [act("b1", True, True, [0, 0], [1, 0])])])
    rep = ep.fit(d, IDS)["report"]
    b1 = rep["b1"]
    assert rep["d"]["00"] == b1 and rep["cells"]["00"]["tie_or_unseen_used_b1"]
    assert rep["d"]["01"] == rep["d"]["10"] == b1 and rep["cells"]["01"]["roots"] == 0  # unseen
    assert rep["d"]["11"] == "RETHINK" and rep["cells"]["11"]["distinct_families"] == 2


def test_exact_rational_ties_are_ties_where_floats_are_not():
    assert 0.1 + 0.2 != 0.3
    d = data([("A", [act("a1", False, False, [1] + [0] * 9, [0] * 10), act("a2", False, False, [1, 1] + [0] * 8, [0] * 10),
                     act("a3", False, False, [0] * 10, [1, 1, 1] + [0] * 7)])], R=10)
    rep = ep.fit(d, IDS)["report"]
    assert F(rep["cells"]["00"]["weighted_lower_sum"]["PATCH"]) == F(rep["cells"]["00"]["weighted_lower_sum"]["RETHINK"]) == Fraction(1, 10)
    assert rep["b1"] == "PATCH" and rep["d"]["00"] == "PATCH" and rep["cells"]["00"]["tie_or_unseen_used_b1"]


def test_duplicating_roots_within_a_family_is_invariant_but_new_family_weight_can_change_the_fit():
    base = data([("A", [act("a1", False, False, [1, 1], [0, 0])]), ("B", [act("b1", False, False, [0, 0], [1, 0])])])
    dup = data([("A", [act("a1", False, False, [1, 1], [0, 0]), act("a1bis", False, False, [1, 1], [0, 0])]),
                ("B", [act("b1", False, False, [0, 0], [1, 0]), act("b1bis", False, False, [0, 0], [1, 0])])])
    f0, f1 = ep.fit(base, IDS), ep.fit(dup, IDS)
    assert f0["artifact"]["map"] == f1["artifact"]["map"] and f0["report"]["d_value"] == f1["report"]["d_value"]
    more = data([("A", [act("a1", False, False, [1, 1], [0, 0])]), ("B", [act("b1", False, False, [0, 0], [1, 0])]),
                 ("C", [act("c1", False, False, [0, 0], [1, 1])]), ("D", [act("d1", False, False, [0, 0], [1, 1])])])
    assert f0["report"]["b1"] == "PATCH" and ep.fit(more, IDS)["report"]["b1"] == "RETHINK"


def test_null_slots_and_nonactionable_weights_are_retained():
    d = data([("A", [act("a1", True, False, [None, None], [1, None]), common("a2", None)]),
              ("B", [act("b1", True, False, [1, 0], [1, 1])])])
    rep = ep.fit(d, IDS)["report"]
    assert rep["roots"] == 3 and rep["missing_slots_total"] == {"PATCH": 2, "RETHINK": 1}
    assert rep["missing_common_outcomes"] == 1 and len(rep["nonactionable_roots"]) == 1
    na = rep["nonactionable_roots"][0]
    assert F(na["weight"]) == Fraction(1, 4) and [F(x) for x in na["common_interval"]] == [0, 1]
    c = rep["cells"]["10"]
    assert c["distinct_families"] == 2 and F(c["weight"]) == Fraction(1, 4) + Fraction(1, 2)  # weights use all planned roots
    assert F(rep["constant_values"]["PATCH"]["upper"]) - F(rep["constant_values"]["PATCH"]["lower"]) == Fraction(1, 4) + Fraction(1, 4)


def test_support_counts_include_families_with_entirely_missing_outcomes():
    d = data([("A", [act("a1", False, True, [None, None], [None, None])]), ("B", [act("b1", False, True, [1, 1], [0, 0])])])
    assert ep.fit(d, IDS)["report"]["cells"]["01"]["distinct_families"] == 2


def test_opposing_cells_with_tied_marginals_give_a_state_dependent_d():
    d = data([("A", [act("a1", False, False, [1, 1], [0, 0])]), ("B", [act("b1", True, False, [0, 0], [1, 1])])])
    rep = ep.fit(d, IDS)["report"]
    assert F(rep["constant_values"]["PATCH"]["lower"]) == F(rep["constant_values"]["RETHINK"]["lower"])  # marginal tie
    assert rep["b1"] == "PATCH" and rep["d"]["00"] == "PATCH" and rep["d"]["10"] == "RETHINK" and not rep["d_is_constant"]


# ---- refusals
@pytest.mark.parametrize("mutate", [
    lambda d: d.update(partition="evaluation"),
    lambda d: d.update(replicates=True),
    lambda d: d.update(replicates=0),
    lambda d: d.update(extra=1),
    lambda d: d.update(families=[]),
    lambda d: d["families"][0].update(roots=[]),
    lambda d: d["families"][0].update(note="x"),
    lambda d: d["families"].append(copy.deepcopy(d["families"][0])),                    # duplicate family and root IDs
    lambda d: d["families"][1]["roots"].append(copy.deepcopy(d["families"][0]["roots"][0])),  # duplicate root across families
    lambda d: d["families"][0].update(family_id="bad\ud800"),
    lambda d: d["families"][0]["roots"][0]["outcomes"]["PATCH"].append(1),
    lambda d: d["families"][0]["roots"][0]["outcomes"].update(STOP=[1, 1]),
    lambda d: d["families"][0]["roots"][0]["outcomes"]["PATCH"].__setitem__(0, True),
    lambda d: d["families"][0]["roots"][0]["outcomes"]["PATCH"].__setitem__(0, 0.5),
    lambda d: d["families"][0]["roots"][0]["outcomes"]["PATCH"].__setitem__(0, float("nan")),
    lambda d: d["families"][0]["roots"][0]["outcomes"]["PATCH"].__setitem__(0, 1.0),
    lambda d: d["families"][0]["roots"][0]["state"].update(has_incomplete=1),
    lambda d: d["families"][0]["roots"][0].update(label="hidden grade"),
    lambda d: d["families"][0]["roots"].append(common("z", True)),
    lambda d: d["families"][0]["roots"].append(common("z", 1, disp="")),
    lambda d: d["families"][0]["roots"].append({"root_id": "z", "state": None, "outcomes": {}}),
])
def test_malformed_inputs_are_refused_before_fitting(mutate):
    d = copy.deepcopy(UNEQUAL)
    mutate(d)
    with pytest.raises(ep.PolicyInputError):
        ep.fit(d, IDS)


def test_cyclic_input_is_refused_explicitly():
    d = copy.deepcopy(UNEQUAL)
    d["families"][0]["roots"][0]["outcomes"]["PATCH"][0] = d["families"][0]["roots"][0]["outcomes"]["PATCH"]
    with pytest.raises(ep.PolicyInputError):
        ep.fit(d, IDS)
    d2 = copy.deepcopy(UNEQUAL)
    d2["families"].append(d2["families"])
    with pytest.raises(ep.PolicyInputError):
        ep.fit(d2, IDS)


@pytest.mark.parametrize("ids", [None, {}, {"source_sha256": "x", "config_sha256": "y"}, {**IDS, "extra": "0" * 64}])
def test_identity_argument_is_validated(ids):
    with pytest.raises(ep.PolicyInputError):
        ep.fit(UNEQUAL, ids)


# ---- prediction
def test_predictions_are_label_free_in_memory_and_inputs_are_immutable(monkeypatch):
    before = copy.deepcopy(UNEQUAL)
    res = ep.fit(UNEQUAL, IDS)
    assert UNEQUAL == before
    art = res["artifact"]
    assert set(art) == {"version", "source_sha256", "config_sha256", "map", "b1"}
    assert not any(k in json.dumps(art) for k in ("a1", "fam-A", "outcomes", "root_id"))

    def boom(*a, **k):
        raise AssertionError("file access during fit/predict")
    monkeypatch.setattr(Path, "read_bytes", boom)
    monkeypatch.setattr(Path, "read_text", boom)
    monkeypatch.setattr(builtins, "open", boom)
    ep.fit(UNEQUAL, IDS)  # identities were loaded beforehand; fitting reads nothing
    for pf in (False, True):
        for inc in (False, True):
            assert ep.predict({"has_payload_failure": pf, "has_incomplete": inc}, art, IDS) == art["map"][f"{int(pf)}{int(inc)}"]
    assert ep.nonactionable(art, IDS) == {"disposition": "nonactionable", "prompt_action": None}
    with pytest.raises(ep.PolicyInputError):
        ep.predict({"has_payload_failure": True, "has_incomplete": False, "root_id": "a1"}, art, IDS)
    with pytest.raises(ep.PolicyInputError):
        ep.predict({"has_payload_failure": 1, "has_incomplete": False}, art, IDS)
    with pytest.raises(ep.PolicyInputError):
        ep.predict({"has_payload_failure": True, "has_incomplete": False}, art, {**IDS, "config_sha256": "0" * 64})
    with pytest.raises(ep.PolicyInputError):
        ep.predict({"has_payload_failure": True, "has_incomplete": False}, {**art, "map": {**art["map"], "00": "STOP"}}, IDS)


def test_module_has_no_data_discovery_network_or_execution_path():
    tree = ast.parse((ROOT / "experiments/prompt_choice/empirical_policy.py").read_text())
    imported = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    imported |= {(n.module or "").split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert imported <= {"__future__", "copy", "hashlib", "json", "math", "re", "fractions", "itertools", "pathlib"}
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert not names & {"glob", "rglob", "iterdir", "listdir", "walk", "open", "exec", "eval", "system", "Popen", "urlopen", "socket"}


def test_report_preserves_every_actionable_roots_exact_interval_denominator_and_missingness():
    d = data([("A", [act("a1", True, False, [None, 1, 0], [1, None, None]), common("a2", None)]),
              ("B", [act("b1", False, True, [1, 1, 1], [0, 0, 0])])], R=3)
    res = ep.fit(d, IDS)
    per = {r["root_id"]: r for r in res["report"]["actionable_roots"]}
    assert set(per) == {"a1", "b1"} and "actionable_roots" not in res["artifact"]
    a1 = per["a1"]
    assert a1["family_id"] == "A" and a1["cell"] == "10" and a1["planned_slots"] == 3 and F(a1["weight"]) == Fraction(1, 4)
    assert [F(x) for x in a1["actions"]["PATCH"]["interval"]] == [Fraction(1, 3), Fraction(2, 3)] and a1["actions"]["PATCH"]["missing"] == 1
    assert [F(x) for x in a1["actions"]["RETHINK"]["interval"]] == [Fraction(1, 3), Fraction(1, 1)] and a1["actions"]["RETHINK"]["missing"] == 2
    b1 = per["b1"]
    assert b1["cell"] == "01" and F(b1["weight"]) == Fraction(1, 2) and [F(x) for x in b1["actions"]["PATCH"]["interval"]] == [1, 1]
