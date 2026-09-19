import dataclasses
import unittest

import numpy as np

from dtr_multiround.candidates import Candidate, SelectionRecord, selector_ratio, supported_greedy_selection
from dtr_multiround.estimators import (
    action_pseudo_outcome, continuation_pseudo_outcomes, estimate_task_mean,
    ipw_score, longitudinal_dr_score, task_folds, trajectory_weight, value_from_q,
)
from dtr_multiround.simulator import (
    ACTIONS, CORRECT, RETRY, STOP, FinitePromptProcess, History,
    adaptive_policy, behavior_policy, constant_policy, uniform_policy,
)


class ExactProcessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.process = FinitePromptProcess()
        q, value = cls.process.oracle(adaptive_policy)
        cls.q, cls.value = staticmethod(q), staticmethod(value)
        cls.truth = cls.process.policy_value(adaptive_policy)
        cls.paths = cls.process.enumerate(behavior_policy)

    def expectation(self, function):
        return sum(mass * function(path) for path, mass in self.paths)

    def test_enumeration_and_dynamic_programming_agree(self):
        self.assertAlmostEqual(sum(mass for _, mass in self.paths), 1.0, places=13)
        direct = sum(path.terminal_utility * mass for path, mass in self.process.enumerate(adaptive_policy))
        self.assertAlmostEqual(direct, self.truth, places=13)

    def test_stop_preserves_accepted_quality_and_charges_no_cost(self):
        initial = History(1, (1,))
        paths = self.process.enumerate(constant_policy(STOP), initial)
        self.assertEqual(len(paths), 1)
        path, mass = paths[0]
        self.assertEqual(mass, 1.0)
        self.assertEqual(path.terminal_utility, 1.0)
        self.assertEqual(path.steps[-1].next_history.cost, 0)
        self.assertEqual(path.steps[-1].next_history.actions, (STOP,) * 3)
        self.assertAlmostEqual(trajectory_weight(path, adaptive_policy, behavior_policy), 0.85 / 0.20)
        with self.assertRaisesRegex(ValueError, "absorbing"):
            self.process.transition(path.steps[0].next_history, RETRY)

    def test_dr_both_nuisances_correct(self):
        mean = self.expectation(lambda path: longitudinal_dr_score(path, adaptive_policy, behavior_policy, self.q))
        self.assertAlmostEqual(mean, self.truth, places=12)

    def test_dr_correct_propensity_wrong_q(self):
        mean = self.expectation(lambda path: longitudinal_dr_score(path, adaptive_policy, behavior_policy, self.process.wrong_q))
        self.assertAlmostEqual(mean, self.truth, places=12)

    def test_dr_correct_q_wrong_propensity(self):
        mean = self.expectation(lambda path: longitudinal_dr_score(path, adaptive_policy, uniform_policy, self.q))
        self.assertAlmostEqual(mean, self.truth, places=12)

    def test_dr_both_wrong_is_biased(self):
        mean = self.expectation(lambda path: longitudinal_dr_score(path, adaptive_policy, uniform_policy, self.process.wrong_q))
        self.assertGreater(abs(mean - self.truth), 0.01)

    def test_stagewise_mixed_robustness(self):
        # No single nuisance collection is globally correct: g at stages 1/3,
        # Q at stage 2. The exact remainder is zero stage by stage.
        g = lambda h: uniform_policy(h) if h.t == 2 else behavior_policy(h)
        q = lambda h, a: self.q(h, a) if h.t == 2 else self.process.wrong_q(h, a)
        mean = self.expectation(lambda path: longitudinal_dr_score(path, adaptive_policy, g, q))
        self.assertAlmostEqual(mean, self.truth, places=12)

    def test_exact_double_robust_remainder_identity(self):
        estimated = self.expectation(lambda path: longitudinal_dr_score(path, adaptive_policy, uniform_policy, self.process.wrong_q))

        def remainder(path):
            previous_weight, total = 1.0, 0.0
            for step in path.steps:
                h = step.history
                pi, b, g = adaptive_policy(h), behavior_policy(h), uniform_policy(h)
                total += previous_weight * sum(
                    pi[a] * (1 - b[a] / g[a]) * (self.process.wrong_q(h, a) - self.q(h, a))
                    for a in ACTIONS if pi[a] > 0
                )
                previous_weight *= pi[step.action] / g[step.action]
            return total

        self.assertAlmostEqual(estimated - self.truth, self.expectation(remainder), places=12)

    def test_ipw_contains_target_numerators(self):
        self.assertAlmostEqual(self.expectation(lambda p: ipw_score(p, adaptive_policy, behavior_policy)), self.truth, places=12)
        self.assertAlmostEqual(self.expectation(lambda p: trajectory_weight(p, adaptive_policy, behavior_policy)), 1.0, places=12)
        # Omitting target numerators does not estimate this stochastic regime.
        def no_numerator(path):
            weight = 1.0
            for step in path.steps:
                weight /= behavior_policy(step.history)[step.action]
            return weight * path.terminal_utility
        self.assertGreater(abs(self.expectation(no_numerator) - self.truth), 1.0)

    def test_backward_recursion_agrees_with_longitudinal_score(self):
        for path, _ in self.paths[::17]:
            z = continuation_pseudo_outcomes(path, adaptive_policy, behavior_policy, self.process.wrong_q)
            direct = longitudinal_dr_score(path, adaptive_policy, behavior_policy, self.process.wrong_q)
            self.assertAlmostEqual(z[0], direct, places=13)
            self.assertEqual(z[-1], path.terminal_utility)

    def test_conditional_action_pseudo_outcome_correct_propensity(self):
        for initial, _ in self.process.initial_distribution():
            paths = self.process.enumerate(behavior_policy, initial)
            for candidate in ACTIONS:
                label_mean = sum(mass * action_pseudo_outcome(path, 1, candidate, adaptive_policy, behavior_policy, self.process.wrong_q) for path, mass in paths)
                self.assertAlmostEqual(label_mean, self.q(initial, candidate), places=12)

    def test_conditional_action_pseudo_outcome_correct_q(self):
        for initial, _ in self.process.initial_distribution():
            paths = self.process.enumerate(behavior_policy, initial)
            for candidate in ACTIONS:
                label_mean = sum(mass * action_pseudo_outcome(path, 1, candidate, adaptive_policy, uniform_policy, self.q) for path, mass in paths)
                self.assertAlmostEqual(label_mean, self.q(initial, candidate), places=12)

    def test_q_depends_on_named_continuation(self):
        q_stop, _ = self.process.oracle(constant_policy(STOP))
        initial = History(1, (0,))
        self.assertGreater(abs(q_stop(initial, CORRECT) - self.q(initial, CORRECT)), 0.05)

    def test_optimal_selector_dominates_prespecified_selectors(self):
        optimal_value = self.process.policy_value(self.process.optimal_policy())
        for policy in (adaptive_policy, behavior_policy, constant_policy(RETRY), constant_policy(CORRECT), constant_policy(STOP)):
            self.assertGreaterEqual(optimal_value + 1e-13, self.process.policy_value(policy))

    def test_unsupported_target_fails(self):
        path = self.paths[0][0]
        with self.assertRaisesRegex(ValueError, "unsupported"):
            longitudinal_dr_score(path, adaptive_policy, constant_policy(RETRY), self.q)


class TaskInferenceTests(unittest.TestCase):
    def test_task_replication_does_not_inflate_effective_n(self):
        once = estimate_task_mean([0.0, 1.0, 2.0], ["a", "b", "c"])
        replicated = estimate_task_mean([0.0] * 10 + [1.0] * 2 + [2.0] * 4, ["a"] * 10 + ["b"] * 2 + ["c"] * 4)
        self.assertEqual(once.estimate, replicated.estimate)
        self.assertEqual(once.standard_error, replicated.standard_error)
        self.assertEqual(replicated.n_tasks, 3)

    def test_task_folds_keep_all_replicas_together(self):
        ids = ["a", "b", "a", "c", "d", "b"]
        folds = task_folds(ids, 3, 10)
        self.assertEqual(folds[0], folds[2])
        self.assertEqual(folds[1], folds[5])
        self.assertEqual(set(folds), {0, 1, 2})
        np.testing.assert_array_equal(folds, task_folds(ids, 3, 10))

    def test_numpy_scores_and_paired_contrasts(self):
        estimate = estimate_task_mean(np.array([0.1, 0.1, 0.4, 0.4]), [0, 0, 1, 1])
        self.assertAlmostEqual(estimate.estimate, 0.25)
        self.assertAlmostEqual(estimate.standard_error, 0.15)

    def test_single_task_uncertainty_rejected(self):
        with self.assertRaisesRegex(ValueError, "independent tasks"):
            estimate_task_mean([1.0, 2.0], ["a", "a"])


class CandidateContractTests(unittest.TestCase):
    def setUp(self):
        self.record = SelectionRecord(
            "task-1", "episode-1", 1, "a" * 64, "receiver@sha", "generator@sha",
            (Candidate("retry", "Try again."), Candidate("check", "Check the calculation."), Candidate("stop", "", "STOP")),
            "check", {"retry": 0.2, "check": 0.6, "stop": 0.2},
        )

    def test_selector_ratio_uses_conditional_target_probability(self):
        ratio = selector_ratio(self.record, {"retry": 0.1, "check": 0.8, "stop": 0.1}, "generator@sha")
        self.assertAlmostEqual(ratio, 4.0 / 3.0)

    def test_changed_generator_requires_new_support_argument(self):
        with self.assertRaisesRegex(ValueError, "changed generator"):
            selector_ratio(self.record, self.record.behavior_probabilities, "new-generator")

    def test_unsupported_candidate_fails_even_if_not_observed(self):
        record = dataclasses.replace(self.record, behavior_probabilities={"retry": 0, "check": 0.8, "stop": 0.2})
        with self.assertRaisesRegex(ValueError, "unsupported"):
            selector_ratio(record, {"retry": 0.1, "check": 0.8, "stop": 0.1}, "generator@sha")
        self.assertEqual(supported_greedy_selection(record, {"retry": 100.0, "check": 0.5, "stop": 0.2}), "check")

    def test_duplicate_text_keeps_distinct_candidate_ids(self):
        # Selection unit is candidate ID; duplicate texts can be coarsened only
        # after the additional version/exclusion assumptions are justified.
        first = Candidate("a", "Same text")
        second = Candidate("b", "Same text")
        self.assertEqual(first.text_sha256, second.text_sha256)
        self.assertNotEqual(first.candidate_id, second.candidate_id)

    def test_duplicate_candidate_ids_rejected(self):
        record = dataclasses.replace(self.record, candidates=self.record.candidates + (self.record.candidates[0],))
        with self.assertRaisesRegex(ValueError, "unique"):
            record.validate()


if __name__ == "__main__":
    unittest.main()
