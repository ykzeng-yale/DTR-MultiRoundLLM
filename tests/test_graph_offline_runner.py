"""Failure accounting for the offline runner, using authored stub fixtures only.

These tests exercise run/write control flow without generating graphs, invoking
the upstream verifier, making receiver calls, or executing candidate programs.
Git/source checks are stubbed so tests do not depend on their own commit status.
"""
from contextlib import ExitStack, contextmanager
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("graph_offline_runner", ROOT / "scripts/validate_graph_offline.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class GraphOfflineRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.output = self.directory / "run"
        self.config = json.loads((ROOT / runner.CONFIG_PATH).read_text())
        # This is an explicitly mocked three-root control-flow fixture, not the
        # frozen 32-root experiment or a change to its checked-in configuration.
        self.config.update(root_count=3, vertex_schedule=[3], edge_probability_schedule=[0.2])
        self.config["fixed_controls"] = [
            {"name": "valid", "response": '{"0":1,"1":2,"2":3}', "expected_score": 1},
            {"name": "missing", "response": None, "expected_score": None},
        ]
        self.config_path = self.directory / "config.json"
        self.config_bytes = json.dumps(self.config).encode()
        self.config_path.write_bytes(self.config_bytes)
        self.puzzle = {"vertices": [0, 1, 2], "edges": [[0, 1], [1, 2]], "color_options": [1, 2, 3]}

    def generated(self):
        return {"status": "generated", "puzzle": self.puzzle,
                "reference": {0: 1, 1: 2, 2: 3}, "attempts": 1}

    @staticmethod
    def grade_stub(puzzle, response, **kwargs):
        return {"status": "missing" if response is None else "observed",
                "score": None if response is None else 1,
                "diagnostic": {"code": "missing_output" if response is None else "valid"}}

    @staticmethod
    def public_stub(root_id, family_id, puzzle):
        return {"root_id": root_id, "family_id": family_id,
                "prompt": "Authored graph fixture", "public_context": json.dumps(puzzle)}

    @contextmanager
    def environment(self, generated=None):
        with ExitStack() as stack:
            stack.enter_context(patch.object(runner, "git", return_value="a" * 40))
            stack.enter_context(patch.object(runner.subprocess, "check_output", return_value=self.config_bytes))
            stack.enter_context(patch.object(runner.subprocess, "run"))
            stack.enter_context(patch.object(runner, "_verify_sources", return_value={"stub.py": "b" * 64}))
            stack.enter_context(patch.object(runner, "peak_rss_bytes", return_value=1024))
            stack.enter_context(patch.object(runner.signal, "signal"))
            stack.enter_context(patch.object(runner.signal, "setitimer"))
            stack.enter_context(patch.object(runner, "validate_puzzle"))
            stack.enter_context(patch.object(runner, "grade_response", side_effect=self.grade_stub))
            stack.enter_context(patch.object(runner, "build_public_task", side_effect=self.public_stub))
            generator = stack.enter_context(patch.object(
                runner, "generate_root", side_effect=generated, return_value=self.generated()))
            yield generator

    def rows(self, name):
        return [json.loads(line) for line in (self.output / name).read_text().splitlines() if line]

    def assert_exports_match_ledger(self):
        ledger = self.rows("root_ledger.jsonl")
        public = self.rows("public_tasks.jsonl")
        private = self.rows("private_references.jsonl")
        accepted = {r["root_id"] for r in ledger if r["status"] == "accepted"}
        self.assertEqual({r["root_id"] for r in public}, accepted)
        self.assertEqual({r["root_id"] for r in private}, accepted)
        self.assertEqual(len(public), len(private))
        manifest = json.loads((self.output / "manifest.json").read_text())
        self.assertEqual(manifest["accepted_roots"], len(accepted))
        self.assertEqual(manifest["assigned_roots"], len(ledger))
        self.assertEqual(sum(manifest["root_status_counts"].values()), len(ledger))
        return ledger, manifest

    def test_interrupted_generation_preserves_accepted_root_and_assigned_denominator(self):
        with self.environment([self.generated(), runner.BudgetExceeded("injected generation interruption")]):
            result = runner.run(self.config_path, self.output)
        ledger, manifest = self.assert_exports_match_ledger()
        self.assertEqual(result["status"], "failed")
        self.assertEqual([r["status"] for r in ledger], [
            "accepted", "generation_interrupted_attempt_count_unknown", "not_attempted_run_failure"])
        self.assertEqual(manifest["recorded_generation_attempts"], 1)
        self.assertEqual(manifest["generation_attempt_count_unknown_roots"], 1)
        controls = json.loads((self.output / "fixed_controls.json").read_text())
        missing = next(c for c in controls if c["name"] == "missing")
        self.assertIsNone(missing["actual"]["score"])
        self.assertEqual(missing["actual"]["status"], "missing")

    def test_interruption_before_acceptance_exports_no_partial_root(self):
        with self.environment(), patch.object(
            runner, "_accept_record", side_effect=runner.BudgetExceeded("before acceptance")):
            result = runner.run(self.config_path, self.output)
        ledger, manifest = self.assert_exports_match_ledger()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(manifest["accepted_roots"], 0)
        self.assertEqual(ledger[0]["status"], "validation_interrupted")

    def test_interruption_after_atomic_acceptance_keeps_all_exports_consistent(self):
        original_accept = runner._accept_record

        def accept_then_interrupt(records, record):
            original_accept(records, record)
            raise runner.BudgetExceeded("after acceptance")

        with self.environment(), patch.object(runner, "_accept_record", side_effect=accept_then_interrupt):
            result = runner.run(self.config_path, self.output)
        ledger, manifest = self.assert_exports_match_ledger()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(manifest["accepted_roots"], 1)
        self.assertEqual(ledger[0]["status"], "accepted")

    def test_partial_write_failure_is_marked_and_cannot_be_overwritten(self):
        original_open = Path.open

        def fail_selected_write(path, mode="r", *args, **kwargs):
            if path == self.output / "private_references.jsonl" and "x" in mode:
                raise OSError("injected artifact write failure")
            return original_open(path, mode, *args, **kwargs)

        with self.environment(), patch.object(Path, "open", fail_selected_write):
            with self.assertRaises(OSError):
                runner.run(self.config_path, self.output)
        self.assertTrue((self.output / "RUN_STARTED.json").exists())
        self.assertTrue((self.output / "FAILURE.json").exists())
        self.assertFalse((self.output / "manifest.json").exists())
        before = {p.name: p.read_bytes() for p in self.output.iterdir() if p.is_file()}
        with self.environment() as generator:
            with self.assertRaises(FileExistsError):
                runner.run(self.config_path, self.output)
            generator.assert_not_called()
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.output.iterdir() if p.is_file()})

    def test_artifact_cap_retains_small_failure_record_without_completion(self):
        self.config["max_artifact_bytes"] = 1024
        self.config_bytes = json.dumps(self.config).encode()
        self.config_path.write_bytes(self.config_bytes)
        with self.environment():
            with self.assertRaises(runner.BudgetExceeded):
                runner.run(self.config_path, self.output)
        self.assertTrue((self.output / "RUN_STARTED.json").exists())
        self.assertTrue((self.output / "FAILURE.json").exists())
        self.assertFalse((self.output / "manifest.json").exists())
        self.assertFalse((self.output / "public_tasks.jsonl").exists())
        self.assertLessEqual(sum(p.stat().st_size for p in self.output.iterdir()), 1024)

    def test_config_byte_change_fails_before_output_or_generation(self):
        self.config_path.write_bytes(self.config_bytes + b"\n")
        with self.environment() as generator:
            with self.assertRaisesRegex(ValueError, "exact committed offline fixture design"):
                runner.run(self.config_path, self.output)
            generator.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_completed_run_cannot_be_overwritten(self):
        with self.environment():
            runner.run(self.config_path, self.output)
        before = {p.name: p.read_bytes() for p in self.output.iterdir() if p.is_file()}
        with self.environment() as generator:
            with self.assertRaises(FileExistsError):
                runner.run(self.config_path, self.output)
            generator.assert_not_called()
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.output.iterdir() if p.is_file()})


if __name__ == "__main__":
    unittest.main()
