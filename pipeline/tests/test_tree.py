"""Unit tests for the decision tree (decision_tree/rules.json and tree.py).

Run all tests:  python3 -m unittest discover -s pipeline/tests -v
"""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "decision_tree"))

from common import Context                 # noqa: E402
from tree import decide, load_rules        # noqa: E402


def measures_of(fired):
    return [hit["rule"]["measure_id"] for hit in fired]


class RuleFile(unittest.TestCase):
    def test_every_rule_points_to_a_known_measure(self):
        known = {m["measure_id"] for m in Context().ref.measures}
        load_rules(known_measures=known)             # raises if a measure is unknown

    def test_malformed_rules_are_rejected(self):
        tree = load_rules()
        for change in ({"status": "maybe"}, {"subject": "nothing"}, {"condition": {"no_such_field": "x"}}):
            broken = copy.deepcopy(tree)
            broken["rules"][0].update(change)
            path = ROOT / "decision_tree" / "_broken_for_test.json"
            try:
                import json
                path.write_text(json.dumps(broken), encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_rules(path)
            finally:
                path.unlink()


class Decisions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = load_rules()

    def gap(self, family, factor, robust="yes"):
        return decide(self.tree, "group_gap", {"indicator_family": family, "factor": factor,
                                               "robust": robust, "base": "x"})[0]

    def test_group_gaps(self):
        self.assertEqual(measures_of(self.gap("screening_participation", "education")), ["1.1.1"])
        self.assertEqual(measures_of(self.gap("screening_participation", "language")), ["1.3.1"])
        self.assertEqual(measures_of(self.gap("screening_participation", "sex")), ["2.4.1"])
        self.assertEqual(measures_of(self.gap("followup_attendance", "language")), ["1.2.3"])

    def test_gap_that_is_not_robust_gets_no_recommendation(self):
        self.assertEqual(self.gap("screening_participation", "education", robust="no"), [])

    def test_gap_without_a_matching_rule_gets_no_recommendation(self):
        self.assertEqual(self.gap("followup_attendance", "sex"), [])
        self.assertEqual(self.gap("other", "education"), [])

    def region(self, language, education):
        fired, _ = decide(self.tree, "region_below_target",
                          {"language_level": language, "education_level": education, "base": "Below target"})
        return fired

    def test_region_with_both_disadvantages_gets_both_measures(self):
        self.assertEqual(measures_of(self.region("disadvantaged", "disadvantaged")), ["1.3.1", "1.1.1"])

    def test_region_without_disadvantage_gets_the_general_measure(self):
        fired = self.region("middle", "advantaged")
        self.assertEqual(measures_of(fired), ["2.4.1"])
        self.assertTrue(fired[0]["trigger"].startswith("Below target; no language or education"))

    def test_general_measure_is_not_added_on_top_of_a_specific_one(self):
        self.assertEqual(measures_of(self.region("disadvantaged", "middle")), ["1.3.1"])

    def test_missing_pathway_data(self):
        yes = decide(self.tree, "pathway_data", {"pathway_data_missing": "yes", "missing": "referral times"})[0]
        self.assertEqual(measures_of(yes), ["3.1.2"])
        self.assertEqual(yes[0]["trigger"], "No open data exists for: referral times")
        self.assertEqual(decide(self.tree, "pathway_data", {"pathway_data_missing": "no"})[0], [])

    def test_path_explains_every_rule_that_was_checked(self):
        _, path = decide(self.tree, "region_below_target",
                         {"language_level": "middle", "education_level": "disadvantaged"})
        self.assertEqual([(rule, matched) for rule, matched, _ in path],
                         [("R1", False), ("R2", True), ("R3", False)])

    def test_only_active_rules_are_used(self):
        tree = copy.deepcopy(self.tree)
        for rule in tree["rules"]:
            if rule["rule_id"] == "R1":
                rule["status"] = "retired"
        fired, _ = decide(tree, "region_below_target",
                          {"language_level": "disadvantaged", "education_level": "middle", "base": "b"})
        self.assertEqual(measures_of(fired), ["2.4.1"])

    def test_unknown_subject_is_an_error(self):
        with self.assertRaises(ValueError):
            decide(self.tree, "no_such_subject", {})


if __name__ == "__main__":
    unittest.main()
