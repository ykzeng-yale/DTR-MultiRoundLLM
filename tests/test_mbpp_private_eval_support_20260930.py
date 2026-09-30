import unittest

from scripts.audit_mbpp_private_eval_support_20260930 import audit


class MbppPrivateEvalSupportTests(unittest.TestCase):
    def test_reports_missing_challenge_partition_without_raw_content(self):
        source = {
            1: {
                "task_id": 1,
                "text": "must not appear in output",
                "code": "raise RuntimeError('must not execute')",
                "test_list": ["public assertion"],
                "challenge_test_list": [],
            },
            2: {
                "task_id": 2,
                "text": "also excluded",
                "code": "raise RuntimeError('must not execute')",
                "test_list": ["one", "two"],
                "challenge_test_list": ["challenge"],
            },
        }
        result = audit(source, [2, 1], [1])
        self.assertEqual(result["broad_candidate_root_count"], 2)
        self.assertEqual(result["public_test_count_total"], 3)
        self.assertEqual(result["challenge_test_count_total"], 1)
        self.assertEqual(result["roots_with_challenge_tests"], 1)
        self.assertEqual(result["residual_root_count"], 1)
        self.assertEqual(result["residual_challenge_test_count_total"], 0)
        self.assertEqual([r["task_id"] for r in result["residual_records"]], [1])
        self.assertNotIn("text", result)
        self.assertNotIn("code", result)
        self.assertEqual(result["execution_counts"]["candidate"], 0)

    def test_rejects_duplicate_and_missing_ids(self):
        with self.assertRaises(ValueError):
            audit({}, [3, 3], [])
        with self.assertRaises(ValueError):
            audit({}, [3], [3])
        with self.assertRaises(ValueError):
            audit({1: {}, 2: {}}, [1, 2], [3])

    def test_rejects_non_list_test_metadata(self):
        with self.assertRaises(ValueError):
            audit({1: {"test_list": None, "challenge_test_list": []}}, [1], [1])


if __name__ == "__main__":
    unittest.main()
