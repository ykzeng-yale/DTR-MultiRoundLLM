"""Build the source-only dev_release_v3 package (MRL-16).

Static/source-only: MBPP rows are parsed with ast/ast.literal_eval; no candidate, reference or control is
executed. Writes tasks.jsonl, private_specs.jsonl, public_examples_v3.json, controls_rationale.json,
exclusions.json, overlap_audit.json and BUILD_NOTES.md. config.json and release_manifest.json are written
later by integration. Refuses to overwrite an existing package directory. Output is deterministic.
"""
from __future__ import annotations
import argparse, ast, hashlib, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.landmark import collect, diagnostic, grade  # noqa: E402
from experiments.common.integrity import hack_gate  # noqa: E402

V2 = ROOT / "experiments/landmark/dev_release_v2"
V3 = ROOT / "experiments/landmark/dev_release_v3"
MBPP = ROOT / "work/task_sources/mbpp_full_20260920_4700efb9/mbpp.jsonl"
MBPP_SHA256 = "ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f"
REVIEW = ROOT / "docs/e12_contract_review_20260922.md"
BUNDLE = ROOT / "docs/e12_bundled_release_20260922.md"
ROSTER = (918, 825, 842, 816, 895, 868, 288, 154, 863, 966, 652, 651, 499, 974)
FAMILY = "unresolved_development_family"
ROW = re.compile(r"^\| \*\*(\d+)\*\* `([^`]+)` \| \u201c(.*?)\u201d \| (.*?) \|\s*$")

# One source-designed wrong control per root. `predicted` is the hand-traced return of the control's logic on
# each private assertion input (derived statically; the control text is never executed). A predicted value of
# the string "IndexError" marks a traced exception.
CONTROLS = {
    918: ("def coin_change(S, m, n):\n    ways = [1] + [0] * n\n    for amount in range(1, n + 1):\n"
          "        for c in S:\n            if c <= amount:\n                ways[amount] += ways[amount - c]\n"
          "    return ways[n]\n",
          "Counts ordered sequences (permutations) of coins instead of unordered combinations.",
          "Amount 9 over [4..9]: ordered sequences are (9), (4,5), (5,4) -> 3, expected 2. Amount 4: only (4) -> 1.",
          [3, 1]),
    825: ("def access_elements(nums, list_index):\n    return [nums[i - 1] for i in list_index]\n",
          "Treats the supplied indices as 1-based instead of Python zero-based list indexing.",
          "[1,2,3,4,5] at [1,2] -> nums[0], nums[1] = [1, 2], expected [2, 3]. [1,0,2,3] at [0,1] -> nums[-1], nums[0] = [3, 1], expected [1, 0].",
          [[1, 2], [3, 1]]),
    842: ("def get_odd_occurence(arr, arr_size):\n    return arr[0]\n",
          "Returns the first element instead of the value occurring an odd number of times.",
          "[1,2,3,2,3,1,3] -> 1, expected 3. [5,7,2,7,5,2,5] -> 5, expected 5.",
          [1, 5]),
    816: ("def clear_tuple(test_tup):\n    return test_tup\n",
          "Returns the input tuple unchanged instead of the cleared (empty) tuple.",
          "(2, 1, 4, 5, 6) -> (2, 1, 4, 5, 6), expected (). (3, 2, 5, 6, 8) -> itself, expected ().",
          [(2, 1, 4, 5, 6), (3, 2, 5, 6, 8)]),
    895: ("def max_sum_subseq(A):\n    return sum(x for x in A if x > 0)\n",
          "Ignores the non-adjacency constraint: sums every positive element (adjacent picks allowed).",
          "[1,2,9,5,6,0,5,12,7] -> 1+2+9+5+6+5+12+7 = 47, expected 28. [1,3,10,5,6,0,6,14,21] -> 66, expected 44.",
          [47, 66]),
    868: ("def length_Of_Last_Word(a):\n    return len(a.split())\n",
          "Returns the number of words instead of the length of the last word.",
          "\"PHP\" -> 1 word, expected 3. \"\" -> 0, expected 0.",
          [1, 0]),
    288: ("def modular_inverse(arr, N, P):\n    count = 0\n    for i in range(N):\n"
          "        if arr[i] * arr[i] == 1:\n            count += 1\n    return count\n",
          "Omits the modulus: counts entries with x*x == 1 instead of x*x congruent to 1 modulo P.",
          "[1,3,8,12,12] mod 13: only 1 has x*x == 1 -> 1, expected 3 (1, 12, 12). [2,3,4,5] mod 6: none -> 0, expected 1 (5).",
          [1, 0]),
    154: ("def specified_element(nums, N):\n    return list(nums[N])\n",
          "Returns row N instead of column N.",
          "N=2 -> row [7, 1, 9, 5], expected [3, 6, 9]. N=3 -> no row 3 (IndexError), expected [2, 2, 5].",
          [[7, 1, 9, 5], "IndexError"]),
    863: ("def find_longest_conseq_subseq(arr, n):\n    best = cur = 1\n    for i in range(1, n):\n"
          "        cur = cur + 1 if arr[i] == arr[i - 1] + 1 else 1\n        best = max(best, cur)\n    return best\n",
          "Counts runs of consecutive values in the original order without sorting or deduplicating.",
          "[1,9,3,10,4,20,2]: no adjacent pair increases by 1 -> 1, expected 4. [36,41,56,35,44,33,34,92,43,32,42]: only (33,34) -> 2, expected 5.",
          [1, 2]),
    966: ("def remove_empty(tuple1):\n    return [t for t in tuple1 if not isinstance(t, tuple)]\n",
          "Removes every tuple (including nonempty ones) instead of only the empty tuples.",
          "[(),(),('',),'python','program'] -> ['python', 'program'], expected [('',), 'python', 'program']. [(),(),('',),'java'] -> ['java'], expected [('',), 'java'].",
          [["python", "program"], ["java"]]),
    652: ("def matrix_to_list(test_list):\n    temp = [ele for sub in test_list for ele in sub]\n    return str(temp)\n",
          "Flattens the tuples in row-major order but omits the transpose into component tuples.",
          "Second case -> '[(5, 6), (8, 9), (11, 14), (19, 18), (1, 5), (11, 2)]', expected '[(5, 8, 11, 19, 1, 11), (6, 9, 14, 18, 5, 2)]'; third case likewise.",
          ["[(5, 6), (8, 9), (11, 14), (19, 18), (1, 5), (11, 2)]",
           "[(6, 7), (9, 10), (12, 15), (20, 21), (23, 7), (15, 8)]"]),
    651: ("def check_subset(test_tup1, test_tup2):\n    return set(test_tup1).issubset(test_tup2)\n",
          "Reverses the subset direction: tests whether the first tuple's elements occur in the second.",
          "((1,2,3,4),(5,6)) -> False, expected False. ((7,8,9,10),(10,8)) -> {7,8,9,10} subset of {8,10} is False, expected True.",
          [False, False]),
    499: ("def diameter_circle(r):\n    return r * r\n",
          "Squares the radius instead of doubling it.",
          "r=40 -> 1600, expected 80. r=15 -> 225, expected 30.",
          [1600, 225]),
    974: ("def min_sum_path(A):\n    memo = list(A[-1])\n    for i in range(len(A) - 2, -1, -1):\n"
          "        for j in range(len(A[i])):\n            memo[j] = A[i][j] + max(memo[j], memo[j + 1])\n    return memo[0]\n",
          "Returns the maximum top-to-bottom path sum instead of the minimum.",
          "[[2],[3,7],[8,5,6]]: row1 -> 3+8=11, 7+6=13; top 2+13 = 15, expected 10. [[3],[6,4],[5,2,7]]: row1 -> 11, 11; top 14, expected 9.",
          [15, 14]),
}


def fsha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def parse_assert(src, entry):
    """Return (args, expected) for `assert entry(<literals>) == <literal>`, or raise ValueError."""
    try:
        tree = ast.parse(src.strip())
    except SyntaxError as e:
        raise ValueError(f"syntax error: {e}") from None
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.Assert) or tree.body[0].msg is not None:
        raise ValueError("not a single bare assert")
    test = tree.body[0].test
    if not (isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq)):
        raise ValueError("assert is not a single == comparison")
    call, rhs = test.left, test.comparators[0]
    if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == entry and not call.keywords):
        raise ValueError("left side is not a positional call of the entry point")
    try:
        args = [ast.literal_eval(a) for a in call.args]
        expected = ast.literal_eval(rhs)
    except (ValueError, SyntaxError, TypeError) as e:
        raise ValueError(f"non-literal argument or expected value: {e}") from None
    if any(isinstance(a, ast.Starred) for a in call.args):
        raise ValueError("starred argument")
    return args, expected


def entry_of(src):
    test = ast.parse(src.strip()).body[0].test
    return test.left.func.id


def signature(code, entry):
    fns = [n for n in ast.parse(code).body if isinstance(n, ast.FunctionDef) and n.name == entry]
    if len(fns) != 1:
        raise ValueError("reference does not define the entry point exactly once")
    a = fns[0].args
    if a.posonlyargs or a.vararg or a.kwonlyargs or a.kwarg or a.defaults:
        raise ValueError("reference signature is not plain positional")
    return f"{entry}({', '.join(x.arg for x in a.args)})"


def norm(v):
    if isinstance(v, (tuple, list)):
        return [norm(x) for x in v]
    return v


def review_rows():
    rows = {}
    for line in REVIEW.read_text().splitlines():
        m = ROW.match(line)
        if m:
            rows[int(m.group(1))] = {"signature": m.group(2), "prompt": m.group(3), "note": m.group(4)}
    return rows


def format_instruction():
    tasks = [json.loads(l) for l in (V2 / "tasks.jsonl").read_text().splitlines() if l.strip()]
    lines = {t["public_context"].split("\n")[1] for t in tasks}
    if len(lines) != 1:
        raise SystemExit("v2 format instruction is not unique")
    return lines.pop()


def jline(obj):
    return json.dumps(obj, sort_keys=True) + "\n"


def jdump(obj):
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def build():
    """Return {filename: text} for the package (pure; deterministic)."""
    if fsha(MBPP) != MBPP_SHA256:
        raise SystemExit("pinned MBPP source hash mismatch")
    mbpp = {}
    for line in MBPP.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            mbpp[r["task_id"]] = r
    reviews, instruction = review_rows(), format_instruction()
    tasks, specs, publics, rationale, held, overlap = [], [], [], [], [], []
    for tid in ROSTER:
        root, row, rev = f"mbpp/{tid}", mbpp[tid], reviews.get(tid)
        try:
            if rev is None:
                raise ValueError("no public specification row in the contract review")
            if row.get("test_setup_code"):
                raise ValueError("MBPP test_setup_code is nonempty")
            tests = row["test_list"]
            if len(tests) < 2:
                raise ValueError("fewer than two source assertions")
            entry = entry_of(tests[0])
            pub_args, pub_exp = parse_assert(tests[0], entry)
            priv = [parse_assert(t, entry) for t in tests[1:]]
            sig = signature(row["code"], entry)
            if sig != rev["signature"]:
                raise ValueError(f"reference signature {sig} differs from review {rev['signature']}")
        except (ValueError, SyntaxError, AttributeError, IndexError) as e:
            held.append({"root_id": root, "reason": str(e)})
            continue
        case = {"case_id": f"public-{tid}-1", "args_literal": repr(pub_args), "expected_literal": repr(pub_exp)}
        if diagnostic.literal(case["args_literal"]) != pub_args or diagnostic.literal(case["expected_literal"]) != pub_exp:
            held.append({"root_id": root, "reason": "public example does not round-trip through repr/literal_eval"})
            continue
        context = (f"Required function interface: def {sig}:\n{instruction}\n\n"
                   + diagnostic.render_public_examples(entry, [case]))
        task = {"family_id": FAMILY, "prompt": rev["prompt"], "public_context": context, "root_id": root}
        code, why, trace, predicted = CONTROLS[tid]
        spec = {"entry_point": entry, "negative_controls": [{"code": code, "rationale": why}], "preamble": [],
                "private_assertions": list(tests[1:]), "public_assertions": [],
                "public_task_sha256": collect.digest(task), "reference_code": row["code"], "root_id": root}
        tasks.append(task)
        specs.append(spec)
        publics.append({"root_id": root, "entry_point": entry, "cases": [case]})
        expected = [e for _, e in priv]
        rationale.append({
            "root_id": root, "fault": why, "static_trace": trace,
            "private_cases": [{"assertion": t, "expected": repr(e), "predicted_control_return": repr(p),
                               "predicted_fails": p != e} for t, e, p in zip(tests[1:], expected, predicted)],
            "predicted_failing_private_assertions": sum(p != e for e, p in zip(expected, predicted)),
            "method": "hand trace of the control's logic on literal private inputs; control text never executed"})
        overlap.append({
            "root_id": root, "public_call": diagnostic.render_call(entry, case["args_literal"]),
            "full_input_overlap": [t for t, (a, _) in zip(tests[1:], priv) if norm(a) == norm(pub_args)],
            "shared_argument_positions": [
                {"assertion": t, "positions": [i for i, (x, y) in enumerate(zip(pub_args, a)) if norm(x) == norm(y)]}
                for t, (a, _) in zip(tests[1:], priv)
                if any(norm(x) == norm(y) for x, y in zip(pub_args, a))],
            "same_expected_output": [t for t, e in zip(tests[1:], expected) if norm(e) == norm(pub_exp)],
            "review_semantic_note": rev["note"]})
    grade.validate_specs(tasks, specs)
    for spec in specs:
        for c in spec["negative_controls"]:
            compile(c["code"], "<control>", "exec")
            if hack_gate(c["code"], spec["entry_point"]):
                raise SystemExit(f"control for {spec['root_id']} fails hack_gate")
    for r in rationale:
        if r["predicted_failing_private_assertions"] < 1:
            raise SystemExit(f"control for {r['root_id']} is not predicted to fail any private assertion")
    retained = [t["root_id"] for t in tasks]
    sources = {"mbpp_jsonl_sha256": MBPP_SHA256, "contract_review_sha256": fsha(REVIEW),
               "bundled_release_sha256": fsha(BUNDLE), "v2_tasks_sha256": fsha(V2 / "tasks.jsonl")}
    files = {
        "tasks.jsonl": "".join(jline(t) for t in tasks),
        "private_specs.jsonl": "".join(jline(s) for s in specs),
        "public_examples_v3.json": jdump({"version": "public-examples-v3", "cases": publics}),
        "controls_rationale.json": jdump({"version": "dev-release-v3-controls", "controls": rationale}),
        "exclusions.json": jdump({"version": "dev-release-v3-exclusions",
                                  "roster": [f"mbpp/{t}" for t in ROSTER], "retained": retained,
                                  "n_retained": len(retained), "held": held, "backfill": False, "sources": sources}),
        "overlap_audit.json": jdump({"version": "dev-release-v3-overlap",
                                     "normalization": "tuples and lists compared as equal sequences, recursively",
                                     "roots": overlap}),
    }
    files["BUILD_NOTES.md"] = (
        "# dev_release_v3 build notes\n\n"
        "Built by `scripts/build_dev_release_v3.py` (source-only: ast parsing and literal_eval; no candidate, "
        "reference or control was executed; no model requests).\n\n"
        f"- Roster (fixed order): {', '.join(str(t) for t in ROSTER)}.\n"
        f"- Retained: {len(retained)}; held: {len(held)} (see exclusions.json; no backfill).\n"
        f"- MBPP source sha256 `{MBPP_SHA256}`; public example = test_list[0], private = test_list[1:] verbatim.\n"
        f"- Prompts copied verbatim from the public-specification table of `docs/e12_contract_review_20260922.md` "
        f"(sha256 `{sources['contract_review_sha256']}`), including the 288 general-modulus amendment.\n"
        "- public_context = interface line + the v2 format instruction + one rendered public example "
        "(diagnostic.render_public_examples).\n"
        "- One source-designed wrong control per root; controls_rationale.json records a static hand trace "
        "showing each fails at least one private assertion. Controls compile and pass hack_gate.\n"
        "- Deviation from the suggested control list: 825 uses 1-based indexing (the suggested sorted-index "
        "control passes both private cases, whose index lists are already sorted); 868 returns the word count "
        "(the suggested first-word control passes both private cases, 'PHP' and '').\n"
        "- config.json and release_manifest.json are written by integration, not this builder.\n")
    for name, text in files.items():
        if name != "BUILD_NOTES.md" and "private_specs" not in name and name != "controls_rationale.json" \
                and name != "overlap_audit.json":
            for spec in specs:
                for a in spec["private_assertions"]:
                    if re.sub(r"\s+", "", a) in re.sub(r"\s+", "", text):
                        raise SystemExit(f"private assertion text leaked into {name}")
    return files


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=V3)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit("Refusing to overwrite an existing package directory")
    files = build()
    a.out.mkdir(parents=True)
    for name in sorted(files):
        (a.out / name).write_text(files[name])
    print(json.dumps({"out": str(a.out), "files": {n: fsha(a.out / n) for n in sorted(files)}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
