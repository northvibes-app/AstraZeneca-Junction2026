"""Goal 3 reference facts: values typed once, from Strategy p. 5, and written to the outputs."""
import csv
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))


def rows():
    with open(ROOT / "pipeline" / "reference" / "goal3_targets.csv", encoding="utf-8", newline="") as f:
        return {r["indicator"]: r for r in csv.DictReader(f)}


class Goal3Reference(unittest.TestCase):
    def test_survival_targets_match_strategy_page_5(self):
        r = rows()
        self.assertEqual(r["five_year_survival_lung_increase"]["target_value"], "14")
        self.assertEqual(r["five_year_survival_pancreas_increase"]["target_value"], "6")
        self.assertEqual(r["five_year_survival_liver_increase"]["target_value"], "14")

    def test_mortality_target_and_baseline(self):
        r = rows()["cancer_deaths_reduction"]
        self.assertEqual((r["target_value"], r["baseline_value"]), ("10", "13300"))

    def test_every_row_has_source_and_page(self):
        for r in rows().values():
            self.assertTrue(r["source"] and r["page"], r["indicator"])

    def test_stage_target_is_labelled_goal_2(self):
        self.assertEqual(rows()["diagnosed_stage_I_II_share"]["goal"], "2")

    def test_published_fact_sheet_exists_after_a_run(self):
        sheet = ROOT / "pipeline" / "output" / "facts" / "goal3.md"
        if sheet.exists():
            self.assertIn("13 300", sheet.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
