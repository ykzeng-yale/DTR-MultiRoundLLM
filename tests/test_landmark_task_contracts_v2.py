"""landmark-curated-development-contracts-v2: every boundary value re-derived from the SPECIFICATION.

Oracles below are written from each task's public definition using the standard library. No reference,
candidate or control program from the contract file is executed; boundary arguments are parsed as data
with ast.literal_eval.
"""
import ast, json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V1 = json.loads((ROOT / "experiments/landmark/task_contracts_v1.json").read_text())
V2 = json.loads((ROOT / "experiments/landmark/task_contracts_v2.json").read_text())

ORACLE = {
    52: lambda b, h: b * h,
    357: lambda L: max(x for t in L for x in t),
    373: lambda l, w, h: l * w * h,
    378: lambda L: ([L[-1]] + L[:-1]) if L else [],
    402: lambda n, r, p: math.comb(n, r) % p,
    489: lambda n, arr: arr.count(max(arr)),
    509: lambda n: sum(range(1, n + 1, 2)) // len(range(1, n + 1, 2)),
}


def tasks(c):
    return {t["source_task_id"]: t for t in c["tasks"]}


def test_every_boundary_value_matches_the_specification_oracle():
    for tid, t in tasks(V2).items():
        for case in t["boundary_cases"]:
            args = ast.literal_eval(case["args_literal"])
            assert ORACLE[tid](*args) == ast.literal_eval(case["expected_literal"]), (tid, case)


def test_v2_is_a_strict_superset_of_v1_and_v1_is_untouched():
    t1, t2 = tasks(V1), tasks(V2)
    assert set(t1) == set(t2) and V1["version"].endswith("-v1")
    for tid in t1:
        for key in ("boundary_cases", "negative_controls"):
            old = [{k: v for k, v in x.items()} for x in t1[tid][key]]
            new = [{k: v for k, v in x.items() if k not in ("added_in", "reason")} for x in t2[tid][key]]
            assert new[:len(old)] == old, (tid, key)


def test_no_duplicate_private_boundary_arguments():
    for tid, t in tasks(V2).items():
        args = [c["args_literal"] for c in t["boundary_cases"]]
        assert len(args) == len(set(args)), tid


def test_357_now_separates_the_last_element_and_first_tuple_programs():
    cases = [ast.literal_eval(c["args_literal"])[0] for c in tasks(V2)[357]["boundary_cases"]]
    assert any(max(t[-1] for t in L) != ORACLE[357](L) for L in cases)
    assert any(max(L[0]) != ORACLE[357](L) for L in cases)


def test_402_now_tests_a_composite_modulus_that_prime_only_lucas_gets_wrong():
    def lucas(n, r, p):
        out = 1
        while n or r:
            ni, ri = n % p, r % p
            if ri > ni:
                return 0
            out = out * math.comb(ni, ri) % p
            n //= p; r //= p
        return out % p
    composite = [ast.literal_eval(c["args_literal"]) for c in tasks(V2)[402]["boundary_cases"]]
    composite = [a for a in composite if a[2] >= 4 and any(a[2] % q == 0 for q in range(2, a[2]))]
    assert any(lucas(*a) != ORACLE[402](*a) for a in composite)


def test_489_now_separates_the_count_first_element_program():
    cases = [ast.literal_eval(c["args_literal"]) for c in tasks(V2)[489]["boundary_cases"]]
    assert any(arr.count(arr[0]) != ORACLE[489](n, arr) for n, arr in cases)


def test_402_repair_is_minimal_and_retains_p_equal_one():
    rep = tasks(V2)[402]["reference_repair"]
    assert rep["p_equals_1_retained"] is True
    assert rep["original_canonical_json_digest"] == "60c271e5bbdf2f739a783bc54ce4371959c8b164daf3c8d9b92d7cd44ecb91a9"
    assert "return C[r] % p" in rep["change"]
    assert any(ast.literal_eval(c["args_literal"])[2] == 1 for c in tasks(V2)[402]["boundary_cases"])
