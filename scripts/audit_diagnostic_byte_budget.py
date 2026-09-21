"""Lead-owned illustrative byte budget; not a test of an undelivered renderer."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "docs/public_diagnostic_examples_v1.json"
header = "Public diagnostic report for the previous answer (execution status is recorded per case):\n"
rows = []
for root in json.loads(source.read_text())["cases"]:
    # Stress serialization only: these synthetic records are not observed verdicts.
    record = {
        "schema_version": "public-diagnostic-v1",
        "root_id": root["root_id"],
        "initial_artifact_sha256": "f" * 64,
        "cases": [dict(case_id=c["case_id"], entry_point=root["entry_point"],
                       args=ast.literal_eval(c["args_literal"]),
                       expected=ast.literal_eval(c["expected_literal"]),
                       returned=[-(10**18 - 1)] * 16,
                       value_kind="integer_list", status="program_exception")
                  for c in root["cases"]],
    }
    message = (header + json.dumps(record, sort_keys=True, separators=(",", ":"),
                                  ensure_ascii=False)).encode("utf-8")
    rows.append(dict(root_id=root["root_id"], bytes=len(message),
                     remaining_bytes=2048-len(message), sha256=hashlib.sha256(message).hexdigest()))
print(json.dumps(dict(
    evidence="synthetic serialization arithmetic, not simulation or executed diagnostic",
    source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    assumed_schema="Explicit illustrative keys in this script; worker schema is not delivered",
    cap_bytes=2048, includes_header=True, rows=rows,
    conclusion="All illustrative records fit; the actual renderer and bounded metadata still require validation",
    scope="Longest allowed signed integer list and longest status string; not every semantic status/value combination is valid",
    model_calls=0, candidate_executions=0, sandbox_executions=0, paid_cost_usd=0,
), indent=2))
