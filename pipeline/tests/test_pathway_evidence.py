"""Unit tests for the waiting-time research file and how its lines are classified.

Run all tests:  python3 -m unittest discover -s pipeline/tests -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pathway_evidence import (STAGES, fact_sheet, kind_of, load_waiting_times,   # noqa: E402
                              parse_days, _compare_with_guidance)


def line(**changes):
    row = {"sector": "public", "provider": "Hospital", "cancer_type": "Breast cancer",
           "pathway_stage": "treatment_start", "measure": "Referral arrival to first surgery",
           "days_min": 28, "days_max": 28, "wait_as_stated": "", "data_period": "2025", "kind": "measured",
           "usable_as_evidence": "yes", "against_guidance": "", "notes": "", "source_url": "https://example.org"}
    row.update(changes)
    return row


GUIDANCE = dict(kind="target", measure="Referral arrival to first treatment (surgery / drug / radiotherapy)",
                days_min=42, days_max=42)


class Parsing(unittest.TestCase):
    def test_days(self):
        self.assertEqual(parse_days("28"), (28, 28))
        self.assertEqual(parse_days("28-42"), (28, 42))
        self.assertEqual(parse_days(""), (None, None))
        self.assertEqual(parse_days("a few"), (None, None))

    def test_kinds(self):
        self.assertEqual(kind_of("Statutory maximum"), "legal_limit")
        self.assertEqual(kind_of("National target (not binding)"), "target")
        self.assertEqual(kind_of("Measured (average; unpublished study)"), "measured")
        self.assertEqual(kind_of("Provider claim (marketing)"), "provider_statement")
        self.assertEqual(kind_of("Provider description"), "provider_statement")
        self.assertEqual(kind_of("Single patient case"), "single_case")
        self.assertEqual(kind_of("No data published"), "no_data")


class Guidance(unittest.TestCase):
    def test_measured_times_are_compared_with_the_guidance(self):
        rows = [line(**GUIDANCE), line(), line(measure="Time in specialised care before treatment starts",
                                               days_min=58, days_max=58)]
        _compare_with_guidance(rows)
        self.assertEqual(rows[1]["against_guidance"], "within the 42-day guidance")
        self.assertEqual(rows[2]["against_guidance"], "above the 42-day guidance")

    def test_other_spans_and_claims_are_not_compared(self):
        rows = [line(**GUIDANCE),
                line(measure="Surgery to start of radiotherapy or drug treatment"),      # a different span
                line(kind="provider_statement", measure="Referral arrival to first surgery", days_min=7, days_max=7)]
        _compare_with_guidance(rows)
        self.assertEqual([r["against_guidance"] for r in rows], ["", "", ""])

    def test_no_guidance_means_no_comparison(self):
        rows = [line()]
        _compare_with_guidance(rows)
        self.assertEqual(rows[0]["against_guidance"], "")


class ResearchFile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.manifest = load_waiting_times()

    def test_file_is_read_and_recorded(self):
        self.assertGreater(len(self.rows), 0)
        self.assertEqual(self.manifest["rows"], len(self.rows))
        self.assertEqual(len(self.manifest["sha256"]), 64)

    def test_every_line_has_a_known_stage_and_a_source(self):
        for r in self.rows:
            self.assertIn(r["pathway_stage"], STAGES.values(), r["measure"])
            self.assertTrue(r["source_url"].startswith("https://"), r["measure"])

    def test_claims_and_missing_numbers_never_count_as_evidence(self):
        for r in self.rows:
            if r["kind"] in ("provider_statement", "single_case", "no_data") or r["days_min"] is None:
                self.assertEqual(r["usable_as_evidence"], "no", r["measure"])

    def test_private_providers_supply_no_usable_evidence(self):
        private = [r for r in self.rows if r["sector"] == "private"]
        self.assertTrue(private)
        self.assertTrue(all(r["usable_as_evidence"] == "no" for r in private))

    def test_fact_sheet_keeps_evidence_and_claims_apart(self):
        text = fact_sheet(self.rows)
        self.assertLess(text.index("## Measured by a hospital or a study"), text.index("## Not usable as evidence"))
        self.assertIn("remains a data gap", text)


if __name__ == "__main__":
    unittest.main()
