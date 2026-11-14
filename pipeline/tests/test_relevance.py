"""Unit tests for the relevance rules and the place of each gap in the challenge.

Run all tests:  python3 -m unittest discover -s pipeline/tests -v
"""
import csv
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "decision_tree"))

from tree import band, challenge_position, decide, load_rules      # noqa: E402


class Bands(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = load_rules()

    def test_size(self):
        self.assertEqual(band(self.tree, "size_points", 22.4), "large")
        self.assertEqual(band(self.tree, "size_points", 15), "large")       # the threshold itself counts
        self.assertEqual(band(self.tree, "size_points", 8.3), "medium")
        self.assertEqual(band(self.tree, "size_points", 4.9), "small")
        self.assertEqual(band(self.tree, "size_points", -9.7), "medium")    # the direction does not matter

    def test_reach(self):
        self.assertEqual(band(self.tree, "reach_people", 37116), "large")
        self.assertEqual(band(self.tree, "reach_people", 2460), "medium")
        self.assertEqual(band(self.tree, "reach_people", 150), "small")

    def test_missing_value_is_unknown_not_small(self):
        self.assertEqual(band(self.tree, "size_points", None), "unknown")
        self.assertEqual(band(self.tree, "reach_people", ""), "unknown")


class RelevanceRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = load_rules()

    def level(self, evidence, size="unknown", reach="unknown"):
        fired, _ = decide(self.tree, "gap_relevance", {"evidence": evidence, "size": size, "reach": reach})
        self.assertEqual(len(fired), 1, "exactly one relevance rule must decide")
        return fired[0]["rule"]["level"]

    def test_high_needs_robust_evidence_large_size_and_enough_people(self):
        self.assertEqual(self.level("group_measured_robust", "large", "large"), "high")
        self.assertEqual(self.level("group_measured_robust", "large", "medium"), "high")
        self.assertEqual(self.level("group_measured_robust", "large", "small"), "medium")
        self.assertEqual(self.level("group_measured_robust", "large", "unknown"), "medium")
        self.assertEqual(self.level("group_measured_robust", "medium", "large"), "medium")
        self.assertEqual(self.level("group_measured_robust", "small", "large"), "low")

    def test_region_below_target_is_treated_like_a_measured_gap(self):
        self.assertEqual(self.level("target_shortfall", "large", "large"), "high")
        self.assertEqual(self.level("target_shortfall", "medium", "medium"), "medium")
        self.assertEqual(self.level("target_shortfall", "small", "large"), "low")

    def test_pattern_between_areas_never_reaches_high(self):
        self.assertEqual(self.level("regional_pattern_robust", "large", "large"), "medium")
        self.assertEqual(self.level("regional_pattern_robust", "small"), "low")

    def test_what_could_be_chance_is_uncertain_whatever_its_size(self):
        for evidence in ("group_measured_uncertain", "regional_pattern_not_robust", "single_source_measured"):
            self.assertEqual(self.level(evidence, "large", "large"), "uncertain")

    def test_missing_data_is_not_ranked_as_unimportant(self):
        self.assertEqual(self.level("documented_only"), "not_measurable")
        self.assertEqual(self.level("no_open_data"), "not_measurable")
        self.assertIn("not the same as unimportant", self.tree["levels"]["not_measurable"])

    def test_every_kind_of_evidence_gets_a_level(self):
        for evidence in ("group_measured_robust", "target_shortfall", "regional_pattern_robust",
                         "group_measured_uncertain", "regional_pattern_not_robust", "single_source_measured",
                         "documented_only", "no_open_data"):
            for size in ("large", "medium", "small", "unknown"):
                self.level(evidence, size, "unknown")


class ChallengeMapping(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = load_rules()

    def test_the_three_bottlenecks_of_the_challenge(self):
        self.assertEqual(challenge_position(self.tree, "early_detection"), ("detection", "late detection"))
        self.assertEqual(challenge_position(self.tree, "referral")[1], "transition from primary to specialist care")
        self.assertEqual(challenge_position(self.tree, "treatment_start"),
                         ("treatment initiation", "time from diagnosis to treatment"))

    def test_every_pathway_stage_used_in_the_reference_data_has_a_place(self):
        stages = set()
        for name in ("indicators.csv", "documented_barriers.csv", "known_data_gaps.csv", "measures.csv"):
            with open(ROOT / "pipeline" / "reference" / name, encoding="utf-8") as f:
                stages |= {row["pathway_stage"] for row in csv.DictReader(f)}
        for stage in stages:
            challenge_position(self.tree, stage)          # raises if a stage is missing

    def test_unknown_stage_is_an_error(self):
        with self.assertRaises(ValueError):
            challenge_position(self.tree, "no_such_stage")


class PublishedRelevance(unittest.TestCase):
    """Checks on the output of the latest run, if there is one."""

    @classmethod
    def setUpClass(cls):
        path = ROOT / "pipeline" / "output" / "gap_relevance.csv"
        cls.rows = list(csv.DictReader(open(path, encoding="utf-8"))) if path.exists() else []

    def test_group_gaps_are_national_and_listed_once(self):
        gaps = [(r["group_factor"], r["problem"].split(":")[0]) for r in self.rows if r["kind"] == "group_gap"]
        self.assertEqual(len(gaps), len(set(gaps)))
        self.assertTrue(all(r["region"] == "Finland" for r in self.rows if r["kind"] == "group_gap"))

    def test_high_relevance_always_has_a_measure_and_a_source(self):
        for r in self.rows:
            if r["relevance"] == "high":
                self.assertTrue(r["measures"] and r["source"], r["problem"])


if __name__ == "__main__":
    unittest.main()
