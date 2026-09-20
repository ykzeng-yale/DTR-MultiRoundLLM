"""Contract-export behavior on authored fixtures, with no benchmark execution."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("contract_builder", ROOT/"scripts/build_landmark_task_contracts.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class ContractBuilderTests(unittest.TestCase):
    def setUp(self):
        (ROOT/"work").mkdir(exist_ok=True)
        self.config = json.loads((ROOT/"experiments/landmark/task_contracts_v1.json").read_text())
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.source = Path(self.tmp.name)/"fixture.jsonl"
        self.rows = [{"task_id": t["source_task_id"], "text": "PRIVATE_ORIGINAL_DESCRIPTION",
            "code": f"def {t['entry_point']}({', '.join(t['arguments'])}):\n    raise RuntimeError('MUST_NOT_EXECUTE')\n",
            "test_setup_code": "", "challenge_test_list": [],
            "test_list": [f"assert {t['entry_point']}({', '.join('17' for _ in t['arguments'])}) == 731"]}
            for t in self.config["tasks"]]
        self.write_fixture()

    def write_fixture(self):
        self.source.write_text("".join(json.dumps(r)+"\n" for r in self.rows))

    def build_fixture(self, config=None):
        # Fixtures test export behavior; the production CLI has no hash bypass.
        with patch.object(builder, "file_sha", return_value=builder.SOURCE_SHA):
            return builder.build(self.source, config or self.config)

    def test_export_public_private_separation_and_original_preservation(self):
        tasks, specs, provenance = self.build_fixture()
        self.assertEqual([t["root_id"] for t in tasks], [f"mbpp/{i}" for i in builder.RETAINED])
        for task, spec, original in zip(tasks, specs, self.rows):
            self.assertEqual(set(task), {"root_id", "family_id", "prompt", "public_context"})
            self.assertNotIn("731", str(task))
            self.assertNotIn("MUST_NOT_EXECUTE", str(task))
            self.assertNotIn("PRIVATE_ORIGINAL_DESCRIPTION", str(task))
            self.assertEqual(spec["reference_code"], original["code"])
            self.assertEqual(spec["private_assertions"][0], original["test_list"][0])
            self.assertEqual(spec["public_task_sha256"], builder.digest(task))
        self.assertEqual(provenance[4]["status"], "known_reference_boundary_defect")
        self.assertEqual(len({t["family_id"] for t in tasks}), 1)

    def test_source_hash_is_required(self):
        with self.assertRaisesRegex(ValueError, "Pinned source"):
            builder.build(self.source, self.config)

    def test_no_backfill_or_silent_hold_clearance(self):
        for mutate in [lambda c: c["tasks"].pop(),
                       lambda c: c["tasks"][4].update(status="ready"),
                       lambda c: c.update(family_id="independent_by_id")]:
            config = copy.deepcopy(self.config)
            mutate(config)
            with self.assertRaises(ValueError):
                self.build_fixture(config)

    def test_interface_mismatch_and_unreviewed_setup_are_blocked(self):
        self.rows[0]["code"] = "def wrong(b,h):\n return 0"
        self.write_fixture()
        with self.assertRaisesRegex(ValueError, "interface"):
            self.build_fixture()
        self.rows[0]["code"] = "def parallelogram_area(b,h):\n return 0"
        self.rows[0]["test_setup_code"] = "import os"
        self.write_fixture()
        with self.assertRaisesRegex(ValueError, "setup"):
            self.build_fixture()

    def test_boundary_literals_preserve_tuples_and_reject_calls(self):
        c = self.config["tasks"][1]
        assertion = builder.boundary_assertion(c["entry_point"], c["arguments"], c["boundary_cases"][0])
        call = ast.parse(assertion).body[0].test.left
        self.assertIsInstance(call.args[0].elts[0], ast.Tuple)
        with self.assertRaises(ValueError):
            builder.boundary_assertion("f", ["x"], {"args_literal": "[danger()]", "expected_literal": "0"})

    def test_static_flagged_control_is_not_treated_as_known_executed_failure(self):
        self.config["tasks"][0]["negative_controls"][0]["code"] = "def __eq__(self,other): return True"
        with self.assertRaisesRegex(ValueError, "static integrity"):
            self.build_fixture()

    def test_duplicate_private_boundary_is_rejected(self):
        c = self.config["tasks"][0]
        c["boundary_cases"].append(copy.deepcopy(c["boundary_cases"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.build_fixture()

    def test_existing_output_fails_before_read_and_is_preserved(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"work") as existing:
            marker = Path(existing)/"manifest.json"
            marker.write_text("immutable")
            with patch.object(builder, "build", side_effect=AssertionError("must not build")):
                with self.assertRaises(FileExistsError):
                    builder.main(["--source", "/missing", "--out", existing])
            self.assertEqual(marker.read_text(), "immutable")

    def test_private_outputs_outside_work_are_blocked(self):
        with self.assertRaisesRegex(ValueError, "ignored work"):
            builder.main(["--source", "/missing", "--out", str(Path(self.tmp.name)/"output")])

    def test_prepared_package_is_bound_and_explicitly_not_ready(self):
        tasks, specs, provenance = self.build_fixture()
        with tempfile.TemporaryDirectory(dir=ROOT/"work") as parent:
            output = Path(parent)/"new"
            with patch.object(builder, "build", return_value=(tasks, specs, provenance)):
                builder.main(["--source", str(self.source), "--out", str(output)])
            manifest = json.loads((output/"manifest.json").read_text())
            self.assertFalse(manifest["ready_for_collection"])
            self.assertFalse(manifest["reference_controls_executed"])
            self.assertEqual(manifest["accounting"]["benchmark_reference_control_executions"], 0)
            for name, sha in manifest["artifacts"].items():
                self.assertEqual(builder.file_sha(output/name), sha)
            spec = json.loads((output/"private_specs.REVIEW_ONLY.json").read_text())
            self.assertEqual(builder.digest(spec), manifest["private_specs_canonical_sha256"])


if __name__ == "__main__":
    unittest.main()
