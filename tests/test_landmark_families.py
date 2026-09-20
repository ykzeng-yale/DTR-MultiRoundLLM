"""Behavioral checks for source-only curation; no benchmark execution."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("landmark_family_audit", Path(__file__).resolve().parents[1]/"scripts/audit_landmark_families.py")
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


class FamilyAuditTests(unittest.TestCase):
    def test_slate_independent_of_input_order_and_no_replacement(self):
        pool = list(range(1, 100))
        chosen = audit.select_slate(pool)
        self.assertEqual(chosen, audit.select_slate(list(reversed(pool))))
        self.assertEqual(len(set(chosen)), 24)
        with self.assertRaises(ValueError):
            audit.select_slate(pool+[1])

    def test_shape_flags_identifier_renaming_but_preserves_constants(self):
        a = audit.code_features("def foo(x):\n return x+1\n")
        b = audit.code_features("def bar(z):\n return z+1\n")
        c = audit.code_features("def foo(x):\n return x+2\n")
        self.assertEqual(a["shape_hashes"], b["shape_hashes"])
        self.assertNotEqual(a["shape_hashes"], c["shape_hashes"])

    def test_defaults_annotations_are_not_exported(self):
        for code in ["def f(x=731):\n return x\n", "def f(x: 'answer_731'):\n return x\n"]:
            result = audit.interface(code)
            self.assertIsNone(result["public_signature_candidate"])
            self.assertTrue(result["interface_flags"])

    def test_no_source_execution_or_body_in_interface(self):
        result = audit.interface("raise RuntimeError('must never run')\ndef f(x):\n return 'secret_answer'\n")
        self.assertEqual(result["public_signature_candidate"], "def f(x):")
        self.assertNotIn("secret_answer", str(result))

    def test_semantic_structure_not_lexical_proof(self):
        self.assertEqual(audit.cosine({"same": 1}, {"different": 1}), 0)
        self.assertAlmostEqual(audit.cosine({"same": 2}, {"same": 1}), 1)
        self.assertEqual(audit.normalize("  Ａ\nB  "), "a b")

    def test_type_words_survive_lexical_preprocessing(self):
        self.assertIn("string", audit.terms("Write a function to count digits in a string"))
        self.assertIn("number", audit.terms("Write a function to count digits in a number"))

    def test_old_variants_collapse_to_one_root_without_auto_exclusion(self):
        full = {1: {"text": "sort integers", "code": "def old(x):\n return sorted(x)"},
                2: {"text": "sort integers", "code": "def new(y):\n return sorted(y)"}}
        canonical = [{"uid": "mbpp/1", "benchmark": "mbpp", "source_task_id": 1,
                      "prompt": "sort integers", "reference": full[1]["code"]}]
        row = audit.screen(full, canonical, [2])[0]
        self.assertEqual(len(row["top_lexical_prior_roots"]), 1)
        self.assertAlmostEqual(row["top_lexical_prior_roots"][0]["lexical_cosine"], 1)
        self.assertTrue(row["lexical_review_flag"])
        self.assertNotIn("exclude", row)

    def test_existing_outputs_fail_before_input_reads_and_remain_unchanged(self):
        for filename in ("manifest.json", "all_candidate_screen.json"):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as temp:
                out = Path(temp)
                protected = out/filename
                protected.write_bytes(b"immutable completed result\n")
                adjudications = out/"adjudications.json"
                adjudications.write_bytes(b"preserved input\n")
                argv = ["audit_landmark_families.py", "--full", str(out/"missing_full"),
                        "--canonical", str(out/"missing_canonical"),
                        "--source-audit", str(out/"missing_source_audit"),
                        "--out", str(out), "--adjudications", str(adjudications)]
                with patch("sys.argv", argv), self.assertRaisesRegex(FileExistsError, "choose a new"):
                    audit.main()
                self.assertEqual(protected.read_bytes(), b"immutable completed result\n")
                self.assertEqual(adjudications.read_bytes(), b"preserved input\n")
                self.assertEqual(set(p.name for p in out.iterdir()), {filename, "adjudications.json"})


if __name__ == "__main__":
    unittest.main()
