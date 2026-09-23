#!/usr/bin/env python3
"""Build the exact E14 request plan (PROPOSED, NOT RELEASED) from E12's immutable artifacts. No receiver call.

E14 (docs/e14_same_prefix_revision_proposal_20260923.md, sections 1, 2, 5, 6) holds messages 0-3 BYTE-IDENTICAL
across two arms at nine development roots and varies only message 4's instruction wording:

  NEUTRAL  (seed labels N1:2..N1:7) : diagnostic.N_INSTRUCTION      + "\\n\\n" + terminal-output-contract-v1
  DIRECTED (seed labels S1:2..S1:7) : diagnostic.select_s1(diag)    + "\\n\\n" + terminal-output-contract-v1

The shared prefix is exactly diagnostic.render_arms(...)["N1"][:4] == [...]["S1"][:4]: the system turn, the public
task prompt, the receiver's own previous answer RETAINED as the assistant turn, and ONE shared
diagnostic.diagnostic_message(diag) object. The contract bytes are read out of the proposal file itself (never
retyped) and appended identically to both arms.

Public information only. This build opens the frozen phase-A initial artifacts, the frozen public diagnostics, the
frozen call log and the release package's public files; it never opens a private spec, a grade, a private execution
record or any hidden score, and it refuses if any path it would open matches a private-artifact token.
"""
from __future__ import annotations
import argparse, hashlib, json, random, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.landmark import collect  # noqa: E402
from experiments.landmark import collect_diagnostic as cd  # noqa: E402

RUN = ROOT / "results/e12_dev_v3_20260922T030255Z"
PKG = ROOT / "experiments/landmark/dev_release_v3"
PROPOSAL = ROOT / "docs/e14_same_prefix_revision_proposal_20260923.md"

# Section 5 roster, in preregistered frame-rank order, with the proposal's recorded rank and provisional family.
ROSTER = (("mbpp/918", 1, "PF-918"), ("mbpp/825", 2, "PF-825"), ("mbpp/816", 7, "PF-816"),
          ("mbpp/895", 8, "PF-895"), ("mbpp/868", 9, "PF-813"), ("mbpp/154", 11, "PF-49"),
          ("mbpp/651", 18, "PF-651"), ("mbpp/499", 19, "PF-499"), ("mbpp/974", 20, "PF-147"))
E13A_CHECKPOINTS = ("mbpp/842", "mbpp/288", "mbpp/863", "mbpp/966", "mbpp/652")
ARMS = (("NEUTRAL", "N1"), ("DIRECTED", "S1"))
REPLICATES = tuple(range(2, 8))
CONTRACT_LABEL = "terminal-output-contract-v1"
CONTRACT_SECTION = "## 2. Common terminal-output contract"
ENDPOINT_LABEL = "e14-endpoint-v1"
TOKENS_PER_CALL = 512
RECHECKS_PER_ROOT = 2
VALIDATION_STARTS_PER_ROOT = 3
MAX_SECONDS = 480
SECONDS_PER_CALL = 314.3 / 154  # scripts/e13_sizing.py:20 (E12 measured A+C collection)
# Any path whose posix spelling contains one of these is a private-outcome artifact: opening one is refused.
PRIVATE_TOKENS = ("private", "grade", "hidden", "reference_solution", "/D/", "analysis_report", "analysis_input",
                  "summary.json", "tests.xml")


def _jsonl(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def assert_public_only(paths):
    """Refuse the whole build if any file it opens is a private-outcome artifact (requirement 6, by construction)."""
    for rel in paths:
        low = rel.lower()
        if any(tok in low for tok in PRIVATE_TOKENS):
            raise ValueError(f"refusing to read a private/hidden-score artifact: {rel}")
    return list(paths)


def contract_text(proposal: Path = PROPOSAL) -> str:
    """The terminal-output-contract-v1 bytes, read out of section 2 of the proposal (never retyped)."""
    lines = proposal.read_text(encoding="utf-8").splitlines()
    try:
        start = next(i for i, x in enumerate(lines) if x.startswith(CONTRACT_SECTION))
    except StopIteration:
        raise ValueError(f"{proposal.name} has no {CONTRACT_SECTION!r} section")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    quoted = [x[3:-1] for x in lines[start:end] if x.startswith("> `") and x.endswith("`") and len(x) > 4]
    if len(quoted) != 1:
        raise ValueError(f"section 2 must quote exactly one contract string, found {len(quoted)}")
    text = quoted[0]
    if CONTRACT_LABEL not in "\n".join(lines[start:end]) or "\n" in text or not text.strip():
        raise ValueError("contract quote is not a single labelled line of text")
    return text


def _selection_reason(dm, diag):
    """Which S1_STRINGS index select_s1 picks and the PUBLIC status that triggers it (public statuses only)."""
    cases = diag["cases"]
    for c in cases:
        if c["status"] in dm.PAYLOAD_FAILURES:
            return 0, {"rule": "any status in PAYLOAD_FAILURES", "trigger_status": c["status"],
                       "trigger_case_id": c["case_id"]}
    for c in cases:
        if c["status"] in dm.INCOMPLETE:
            return 1, {"rule": "no payload failure; a status in INCOMPLETE", "trigger_status": c["status"],
                       "trigger_case_id": c["case_id"]}
    return 2, {"rule": "every public example passes", "trigger_status": "pass", "trigger_case_id": None}


def build(run=RUN, pkg=PKG, proposal=PROPOSAL):
    opened = ["experiments/landmark/dev_release_v3/config.json",
              "experiments/landmark/dev_release_v3/tasks.jsonl",
              "experiments/landmark/dev_release_v3/public_examples_v3.json",
              proposal.relative_to(ROOT).as_posix(),
              "results/e12_dev_v3_20260922T030255Z/ARTIFACT_SHA256SUMS.json",
              "results/e12_dev_v3_20260922T030255Z/A/manifest.json",
              "results/e12_dev_v3_20260922T030255Z/A/completion.json",
              "results/e12_dev_v3_20260922T030255Z/A/roots.jsonl",
              "results/e12_dev_v3_20260922T030255Z/A/calls.jsonl",
              "results/e12_dev_v3_20260922T030255Z/A/artifacts/*.txt (checksum re-verification)",
              "results/e12_dev_v3_20260922T030255Z/B/diagnostics.json",
              "results/e12_dev_v3_20260922T030255Z/C/calls.jsonl"]
    assert_public_only(opened)

    config = json.loads((pkg / "config.json").read_text())
    tasks = _jsonl(pkg / "tasks.jsonl")
    examples = json.loads((pkg / "public_examples_v3.json").read_text())
    examples = {e["root_id"]: e for e in examples["cases"]}
    plan = cd.assignments(config, tasks)
    initial_dir, _, rows = cd._load_initial(run / "A", config, tasks, plan)  # re-verifies A bytes and bindings
    sums = json.loads((run / "ARTIFACT_SHA256SUMS.json").read_text())
    sums = sums.get("files", sums)
    for rel in ("A/roots.jsonl", "A/calls.jsonl", "B/diagnostics.json", "C/calls.jsonl"):
        if _sha_bytes((run / rel).read_bytes()) != sums[rel]:
            raise ValueError(f"{rel} differs from E12's artifact checksums")
    dm = cd.diagnostic_module()
    diagnostics = dm.strict_json_loads((run / "B/diagnostics.json").read_bytes())
    cd.diagnostics_schema(dm, diagnostics)

    contract = contract_text(proposal)
    contract_sha = _sha_bytes(contract.encode("utf-8"))
    proposal_bytes = proposal.read_bytes()
    for quoted in (dm.N_INSTRUCTION, *dm.S1_STRINGS):
        if quoted.encode("utf-8") not in proposal_bytes:
            raise ValueError("proposal does not quote an arm instruction string verbatim")

    roster = [r for r in ROSTER]
    if any(rid in E13A_CHECKPOINTS for rid, _, _ in roster):
        raise ValueError("roster includes an E13a outcome-inspected checkpoint")
    if len({rid for rid, _, _ in roster}) != 9:
        raise ValueError("roster must be nine distinct roots")
    by_task = {t["root_id"]: t for t in tasks}
    by_plan = {p["root_id"]: p for p in plan}
    a_calls, c_calls = _jsonl(run / "A/calls.jsonl"), _jsonl(run / "C/calls.jsonl")

    out_roots, order = [], []
    for rid, rank, family in roster:
        if rid not in by_task or rid not in diagnostics or by_plan[rid]["excluded"]:
            raise ValueError(f"{rid} is not a retained E12 root with a frozen diagnostic")
        row = rows[rid]
        text = (initial_dir / row["artifact"]).read_bytes()
        if _sha_bytes(text) != row["artifact_sha256"] or _sha_bytes(text) != sums[f"A/{row['artifact']}"]:
            raise ValueError(f"initial artifact bytes changed for {rid}")
        diag = diagnostics[rid]
        if diag.get("initial_artifact_sha256") != row["artifact_sha256"]:
            raise ValueError(f"diagnostic for {rid} is bound to a different initial artifact")
        ex = examples[rid]
        dm.validate_diagnostic(diag, ex["entry_point"], ex["cases"])  # exact public cases, keys and byte cap
        base = collect.initial_messages(by_task[rid])
        if collect.digest(base) != row["base_messages_sha256"] or base != row["initial"]["request"]["messages"]:
            raise ValueError(f"public prompt for {rid} differs from E12's recorded initial request")

        rendered = dm.render_arms(base, text.decode("utf-8"), diag)
        prefixes = {name: rendered[label][:4] for name, label in ARMS}
        if len(set(collect.digest(p) for p in prefixes.values())) != 1 or len({json.dumps(p, sort_keys=True) for p in prefixes.values()}) != 1:
            raise ValueError(f"messages 0-3 differ between the two arms at {rid}")
        prefix = prefixes["NEUTRAL"]
        if [m["role"] for m in prefix] != ["system", "user", "assistant", "user"]:
            raise ValueError(f"prefix roles at {rid} are not system/user/assistant/user")
        if prefix[2]["content"] != text.decode("utf-8"):
            raise ValueError(f"assistant turn at {rid} is not E12's frozen previous answer")
        shared = dm.diagnostic_message(diag)
        if prefix[3] != shared or prefix[3]["content"].encode("utf-8") != shared["content"].encode("utf-8"):
            raise ValueError(f"diagnostic turn at {rid} is not the shared diagnostic message object")
        for label in ("N1", "S1"):
            recorded = [c["request"]["messages"] for c in c_calls if c["root_id"] == rid and c["arm"] == label]
            if len(recorded) != 2 or any(m[:4] != prefix for m in recorded):
                raise ValueError(f"prefix for {rid} differs from E12's recorded {label} requests")

        s1_index, reason = _selection_reason(dm, diag)
        directed = dm.select_s1(diag)
        if directed != dm.S1_STRINGS[s1_index] or directed != rendered["S1"][4]["content"]:
            raise ValueError(f"DIRECTED instruction at {rid} is not select_s1 of the frozen diagnostic")
        if rendered["N1"][4]["content"] != dm.N_INSTRUCTION:
            raise ValueError(f"NEUTRAL instruction at {rid} is not N_INSTRUCTION")
        instructions = {"NEUTRAL": dm.N_INSTRUCTION, "DIRECTED": directed}
        messages, tails = {}, {}
        for name, _label in ARMS:
            tail = {"role": "user", "content": instructions[name] + "\n\n" + contract}
            if not tail["content"].endswith("\n\n" + contract):
                raise ValueError("contract is not appended verbatim")
            tails[name] = tail
            messages[name] = [*prefix, tail]
        for name, _label in ARMS:
            if tails[name]["content"][len(instructions[name]):] != "\n\n" + contract:
                raise ValueError(f"contract bytes in {name} at {rid} are not the shared contract")

        spent_labels = sorted({c["seed_key"] for c in (*a_calls, *c_calls) if c["root_id"] == rid})
        if not spent_labels or "initial" not in spent_labels:
            raise ValueError(f"no spent labels recovered from E12's call logs for {rid}")
        spent_seeds = {k: collect.seeded(config, rid, k) for k in spent_labels}
        recorded_seeds = by_plan[rid]["seeds"]
        if any(recorded_seeds.get(k) != v for k, v in spent_seeds.items()):
            raise ValueError(f"spent seeds for {rid} disagree with E12's assignment table")
        used = dict(spent_seeds)
        arm_out = {}
        for name, label in ARMS:
            reqs = []
            for r in REPLICATES:
                key = f"{label}:{r}"
                if key in spent_seeds:
                    raise ValueError(f"label {key} was already spent at {rid}")
                seed = collect.seeded(config, rid, key)
                if seed in used.values():
                    clash = [k for k, v in used.items() if v == seed]
                    raise ValueError(f"seed for {rid} {key} collides with {clash}")
                used[key] = seed
                reqs.append({"arm": name, "replicate": r, "seed_key": key, "seed": seed,
                             "messages_sha256": collect.digest(messages[name])})
            arm_out[name] = {"seed_label_prefix": label, "instruction": instructions[name],
                             "instruction_sha256": _sha_bytes(instructions[name].encode("utf-8")),
                             "message4_sha256": _sha_bytes(tails[name]["content"].encode("utf-8")),
                             "messages_sha256": collect.digest(messages[name]), "requests": reqs}

        arm_names = [name for name, _ in ARMS]
        random.Random(collect.seeded(config, rid, "order")).shuffle(arm_names)
        for name in arm_names:
            for r in REPLICATES:
                order.append({"root_id": rid, "arm": name, "replicate": r, "seed_key": f"{dict(ARMS)[name]}:{r}"})

        out_roots.append({
            "root_id": rid, "frame_rank": rank, "provisional_family": family,
            "family_id_in_package": by_task[rid]["family_id"], "label": "development",
            "initial_artifact_sha256": row["artifact_sha256"], "base_messages_sha256": row["base_messages_sha256"],
            "prefix_message_count": len(prefix), "prefix_messages_sha256": collect.digest(prefix),
            "prefix_roles": [m["role"] for m in prefix],
            "diagnostic_message_sha256": _sha_bytes(shared["content"].encode("utf-8")),
            "diagnostic_message_bytes": len(shared["content"].encode("utf-8")),
            "diagnostic_schema_version": diag["schema_version"],
            "public_case_statuses": [c["status"] for c in diag["cases"]],
            "directed_s1_index": s1_index, "directed_selection": reason,
            "spent_labels": spent_labels, "spent_seeds": spent_seeds,
            "arms": arm_out,
        })

    n_calls = sum(len(a["requests"]) for r in out_roots for a in r["arms"].values())
    per_arm = {name: sum(len(r["arms"][name]["requests"]) for r in out_roots) for name, _ in ARMS}
    if n_calls != 108 or set(per_arm.values()) != {54}:
        raise ValueError(f"expected 108 slots (54 per arm), got {n_calls} {per_arm}")
    if len({(o["root_id"], o["arm"], o["replicate"]) for o in order}) != 108:
        raise ValueError("scheduling order is not the 108 distinct slots")
    all_seeds = [(r["root_id"], q["seed"]) for r in out_roots for a in r["arms"].values() for q in a["requests"]]
    for r in out_roots:
        spent = set(r["spent_seeds"].values())
        if any(s in spent for rid, s in all_seeds if rid == r["root_id"]):
            raise ValueError(f"seed collision at {r['root_id']}")

    return {
        "plan_version": "e14-request-plan-v1-same-prefix",
        "status": "PROPOSED; NOT RELEASED; no receiver call made; built source-only with zero receiver, candidate, "
                  "reference, containment or sandbox execution and zero spend",
        "release_note": "Execution requires a separate explicit lead release, a real host window, renewed "
                        "attestation, receiver preflight, a resource agreement and an independent design/measurement "
                        "review. This file authorizes nothing.",
        "evidence_class": "development-only within-root paired instruction-wording contrast at nine already-seen E12 "
                          "histories; identifies nothing beyond the wording it varies; no population effect, no "
                          "policy validation, no repair or reinterpretation of E13a",
        "endpoint_label": ENDPOINT_LABEL,
        "endpoint": "frozen private-suite-plus-output-validity score in {0,1} per slot; scorer code unchanged; all "
                    "108 assigned slots reported, missing stay missing under all-assigned completion bounds",
        "proposal": {"path": proposal.relative_to(ROOT).as_posix(), "sha256": _sha_bytes(proposal_bytes),
                     "sections_implemented": [1, 2, 5, 6]},
        "source_run": run.relative_to(ROOT).as_posix(),
        "receiver_identity_required_for_prefix_reuse": {
            "model": config["model"], "model_digest": config["model_digest"],
            "server_build": config["server_build"], "num_ctx": config["decoding"]["num_ctx"],
            "note": "any receiver or sampler change invalidates the reuse of E12's frozen prefixes"},
        "inputs": {rel: sums[rel] for rel in ("A/roots.jsonl", "A/calls.jsonl", "B/diagnostics.json", "C/calls.jsonl")},
        "package": {f: _sha_bytes((pkg / f).read_bytes())
                    for f in ("config.json", "tasks.jsonl", "public_examples_v3.json")},
        "decoding": {**config["decoding"], "num_predict": TOKENS_PER_CALL},
        "seed_law": {"seed": config["seed"],
                     "derivation": "collect.seeded(config, root_id, \"<arm_label>:<replicate>\") "
                                   "= int(digest([seed, root_id, label])[:15], 16) % 2**31",
                     "spent_labels_source": "E12 A/calls.jsonl and C/calls.jsonl seed_key fields (not hard-coded)"},
        "contract": {"label": CONTRACT_LABEL, "text": contract, "sha256": contract_sha,
                     "bytes": len(contract.encode("utf-8")), "identical_in_both_arms": True,
                     "read_from": f"{proposal.relative_to(ROOT).as_posix()} section 2 (bytes, not retyped)",
                     "validation_required_before_primary_collection": True},
        "arms": {name: {"seed_label_prefix": label,
                        "instruction_source": "diagnostic.N_INSTRUCTION" if name == "NEUTRAL"
                                              else "diagnostic.select_s1(diag) over public statuses only",
                        "replicates": list(REPLICATES),
                        "message4": "<instruction> + \"\\n\\n\" + terminal-output-contract-v1"}
                 for name, label in ARMS},
        "neutral_instruction": dm.N_INSTRUCTION,
        "s1_strings": [{"index": i, "sha256": _sha_bytes(s.encode("utf-8")), "text": s}
                       for i, s in enumerate(dm.S1_STRINGS)],
        "private_information_barrier": {
            "no_private_grade_spec_or_hidden_score_read": True,
            "files_opened": opened,
            "refused_path_tokens": list(PRIVATE_TOKENS),
            "assertion": "arm assignment, instruction selection, scheduling and seeds are functions of public "
                         "statuses, public prompts and the receiver's own previous answer only; every private "
                         "evaluation happens strictly after collection and is never fed back into any prompt"},
        "checks": [
            "A bytes and config/dataset/assignment digests re-verified (collect_diagnostic._load_initial)",
            "A/roots.jsonl, A/calls.jsonl, B/diagnostics.json and C/calls.jsonl match E12 ARTIFACT_SHA256SUMS",
            "messages 0-3 byte-identical between NEUTRAL and DIRECTED at every root (collect.digest of the "
            "4-message prefix equal, and the message objects equal); refuses otherwise",
            "assistant turn present at index 2 and equal to E12's frozen initial artifact bytes "
            "(sha256 == roots.jsonl artifact_sha256 == ARTIFACT_SHA256SUMS entry)",
            "message 3 is one shared diagnostic.diagnostic_message(diag) object per root, and each diagnostic "
            "passes diagnostic.validate_diagnostic against that root's fixed public examples (entry_point, cases)",
            "prefix bytes equal the first four messages of both of E12's recorded N1 and S1 requests at each root",
            "terminal-output-contract-v1 bytes read from the proposal file, identical in both arms, sha256 recorded once",
            "DIRECTED instruction == diagnostic.select_s1(frozen diagnostic) and == S1_STRINGS[recorded index]; "
            "NEUTRAL instruction == diagnostic.N_INSTRUCTION; proposal quotes all four strings verbatim",
            "all 108 derived seeds disjoint from every seed spent at that root, with spent labels derived from "
            "E12's A/calls.jsonl plus C/calls.jsonl seed_key values and cross-checked against E12's assignment table",
            "no private grade, private spec, private execution record or hidden score opened; the opened-file list "
            "is enumerated in the plan and every path is screened against private-artifact tokens",
            "108 slots = 9 roots x 2 arms x 6 replicates, 54 per arm, inclusion probability 1, root-balanced order "
            "recorded as scheduling only",
            "no E13a outcome-inspected checkpoint (842, 288, 863, 966, 652) is in the roster",
        ],
        "assignment": {"n_roots": len(out_roots), "n_arms": len(ARMS), "replicates_per_cell": len(REPLICATES),
                       "inclusion_probability": 1.0, "per_arm_calls": per_arm, "total_calls": n_calls,
                       "adaptive_assignment": False, "propensity": None,
                       "order_role": "scheduling_not_assignment",
                       "order_note": "root-balanced so a truncated window loses whole roots; arm order shuffled "
                                     "within root by collect.seeded(config, root_id, \"order\"); carries no "
                                     "inferential role",
                       "retries_or_backfill": False, "outcome_driven_stopping": False},
        "roots": out_roots,
        "scheduling_order": order,
        "budget": {"receiver_calls": n_calls, "max_tokens_per_call": TOKENS_PER_CALL,
                   "reserved_completion_tokens": TOKENS_PER_CALL * n_calls,
                   "expected_collection_seconds": round(n_calls * SECONDS_PER_CALL, 1),
                   "max_seconds": MAX_SECONDS,
                   "isolated_starts": VALIDATION_STARTS_PER_ROOT * len(out_roots) + n_calls
                                      + RECHECKS_PER_ROOT * len(out_roots),
                   "paid_spend_usd": 0,
                   "note": "caps are proposed; no allowance, window or attestation is claimed by this file"},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit("Refusing to overwrite")
    out = build()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["budget"]),
          [(r["root_id"], r["directed_s1_index"]) for r in out["roots"]])


if __name__ == "__main__":
    main()
