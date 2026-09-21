"""Phase B driver for the MRL-08 public diagnostic (source/mock only; this module never executes anything itself).

run_phase_b reads Phase A's directory (collect_diagnostic.run_initial: manifest.json, completion.json, roots.jsonl,
artifacts/<artifact_name(root_id)>), re-verifies every file against completion.json's checksums and every artifact's
raw-bytes SHA-256 against roots.jsonl's artifact_sha256 (initial_artifact_sha256 convention), and refuses on any
mismatch. For each collected root, in roots.jsonl order, it calls public_check.check_artifact with the INJECTED runner
and a fresh nonce, then diagnostic.build_diagnostic, then diagnostic.validate_diagnostic when the module defines it.

Input boundary: public cases come ONLY from examples_path, which passes public_check.assert_public_inputs_only. The
initial artifacts are read by this driver as text, outside the executor, and handed to public_check as the candidate
answer; the executor's own inputs are that text plus the public cases, so the work/ rule of the allowlist governs
what enters the executor, not this driver's read of Phase A's directory (which may legitimately live under work/).

Outputs (out_dir must not exist; nothing is ever overwritten):
  diagnostics.json  exact bytes json.dumps({root_id: diag}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                    .encode(); its SHA-256 is what collect_diagnostic.run_continue(expected_diagnostics_sha256=...) binds.
  manifest.json     diagnostics_sha256, executor source SHA-256s, PUBLIC_LIMITS, actual runner invocations. Nonces are
                    ephemeral and never written. There are no retries: each root gets at most one runner invocation.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import secrets

from experiments.landmark import diagnostic, public_check

HERE = Path(__file__).resolve().parent
EXECUTOR_SOURCES = ("public_check.py", "diagnostic.py", "sandbox.py", "grade.py")
SCHEMA = "public-phase-b-v1"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _artifact_name(root_id):
    return root_id.replace("/", "%2F") + ".txt"  # collect_diagnostic.artifact_name (kept import-free of that module)


def load_examples(examples_path):
    """root_id -> (entry_point, cases) from a public_diagnostic_examples_v1.json file; refuses duplicates."""
    doc = json.loads(Path(examples_path).read_text(encoding="utf-8"))
    out = {}
    for item in doc["cases"]:
        if item["root_id"] in out:
            raise ValueError(f"Duplicate public examples for {item['root_id']}")
        out[item["root_id"]] = (item["entry_point"], item["cases"])
    return out


def load_initial(initial_dir):
    """Phase A rows with verified artifact text, in roots.jsonl (assignment) order. Refuses on any mismatch."""
    initial_dir = Path(initial_dir)
    manifest = json.loads((initial_dir / "manifest.json").read_text())
    completion = json.loads((initial_dir / "completion.json").read_text())
    if manifest.get("phase") != "initial" or completion.get("phase") != "initial":
        raise ValueError("Not a diagnostic initial-phase directory")
    for rel, sha in completion["checksums"].items():
        if _sha((initial_dir / rel).read_bytes()) != sha:
            raise ValueError(f"Initial-phase file changed after completion: {rel}")
    rows = [json.loads(x) for x in (initial_dir / "roots.jsonl").read_text().splitlines() if x.strip()]
    ids = [r["root_id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate root in roots.jsonl")
    collected = []
    for r in rows:
        if not r.get("artifact_sha256"):
            continue
        if r.get("artifact") != "artifacts/" + _artifact_name(r["root_id"]):
            raise ValueError(f"Unexpected artifact path for {r['root_id']}")
        data = (initial_dir / r["artifact"]).read_bytes()
        if _sha(data) != r["artifact_sha256"]:
            raise ValueError(f"Initial artifact bytes differ from the recorded SHA-256 for {r['root_id']}")
        collected.append((r["root_id"], r["artifact_sha256"], data.decode("utf-8")))
    return completion, collected


def run_phase_b(initial_dir: Path, examples_path: Path, out_dir: Path, runner, nonce_factory=secrets.token_hex) -> dict:
    out_dir = Path(out_dir)
    if out_dir.exists():
        raise FileExistsError(f"Phase B output already exists: {out_dir}")
    public_check.assert_public_inputs_only([examples_path])
    examples = load_examples(examples_path)
    completion, collected = load_initial(initial_dir)
    missing = [root for root, _, _ in collected if root not in examples]
    if missing:
        raise ValueError(f"No public examples for collected roots: {missing}")

    invocations = {"n": 0}

    def counted(*args, **kwargs):  # every runner invocation is an executor start attempt; no retries
        invocations["n"] += 1
        return runner(*args, **kwargs)

    diags, per_root = {}, []
    validate = getattr(diagnostic, "validate_diagnostic", None)
    for root, sha, text in collected:
        entry_point, cases = examples[root]
        before = invocations["n"]
        results = public_check.check_artifact(text, entry_point, cases, counted, nonce_factory())
        diag = diagnostic.build_diagnostic(root, sha, entry_point, cases, results)
        if validate is not None:
            validate(diag)
        diagnostic.diagnostic_bytes(diag)  # cap check; raises, never truncates
        diags[root] = diag
        per_root.append({"root_id": root, "initial_artifact_sha256": sha, "runner_invocations": invocations["n"] - before,
                         "statuses": [r["status"] for r in results]})

    data = json.dumps(diags, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    manifest = {
        "schema_version": SCHEMA, "diagnostics_sha256": _sha(data),
        "initial_completion_sha256": _sha((Path(initial_dir) / "completion.json").read_bytes()),
        "examples_sha256": _sha(Path(examples_path).read_bytes()),
        "executor_source_sha256": {name: _sha((HERE / name).read_bytes()) for name in EXECUTOR_SOURCES},
        "public_limits": dict(public_check.PUBLIC_LIMITS),
        "executor_starts": invocations["n"],  # runner invocations (format errors / integrity flags start nothing)
        "retries": 0, "nonces_recorded": False, "roots": per_root,
    }
    out_dir.mkdir(parents=True, exist_ok=False)
    with (out_dir / "diagnostics.json").open("xb") as f:
        f.write(data)
    with (out_dir / "manifest.json").open("x", encoding="utf-8") as f:
        f.write(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return manifest
