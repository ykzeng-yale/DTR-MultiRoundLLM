"""Check planning arithmetic against the existing reviewed bound."""
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("precision_plan",ROOT/"scripts/plan_landmark_precision.py")
plan=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(plan)


class PrecisionPlanningTests(unittest.TestCase):
    def test_seven_independent_roots_cannot_clear_zero_even_at_observed_one(self):
        r=plan.scenario("seven",[1]*7,.05)
        self.assertLess(r["hypothetical_all_positive_interval"][0],0)
        self.assertEqual(r["all_arm_calls_at_two_repeats"],49)

    def test_repeating_roots_in_one_group_never_creates_independent_units(self):
        one=plan.scenario("one",[1],.005)
        seven=plan.scenario("seven",[7],.005)
        self.assertEqual(one["radius"],seven["radius"])
        self.assertEqual(seven["hypothetical_all_positive_interval"],[-1,1])

    def test_family_imbalance_reduces_effective_count(self):
        balanced=plan.scenario("balanced",[4]*6,.005)
        unbalanced=plan.scenario("unbalanced",[19,1,1,1,1,1],.005)
        self.assertGreater(unbalanced["radius"],balanced["radius"])
        self.assertLess(unbalanced["effective_families"],balanced["effective_families"])

    def test_integer_precision_threshold_brackets_existing_analyzer(self):
        for alpha in [.05,.005]:
            for h in [.1,.05,.03]:
                n=plan.required_equal_families(h,alpha)
                with self.subTest(alpha=alpha,half_width=h):
                    self.assertLessEqual(plan.scenario("enough",[1]*n,alpha)["radius"],h)
                    self.assertGreater(plan.scenario("less",[1]*(n-1),alpha)["radius"],h)

    def test_invalid_planning_inputs(self):
        for h in [0,-.1,float("nan"),2]:
            with self.assertRaises(ValueError): plan.required_equal_families(h,.05)
        with self.assertRaises(ValueError): plan.scenario("zero",[0],.05)


if __name__=="__main__": unittest.main()
