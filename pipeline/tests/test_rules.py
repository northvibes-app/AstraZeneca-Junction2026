"""Unit tests for the rules the pipeline's results depend on most.

Run all tests:  python3 -m unittest discover -s pipeline/tests -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import (Context, IN_SCOPE_LEVELS, holm_adjust, normal_p_value,   # noqa: E402
                    permutation_p_value, spearman, wilson_interval)
from steps import s04_standardise, s06_deduplicate, s07_quality_checks       # noqa: E402


def observation(**changes):
    """A valid cleaned observation; tests override only the fields they care about."""
    row = {"indicator_key": "screening_participation_breast", "indicator_name": "Breast screening participation",
           "kind": "outcome", "pathway_stage": "early_detection", "cancer": "breast", "detail": "",
           "region_code": "90", "region_level": "wellbeing_county", "region_name": "City of Helsinki",
           "year": 2024, "period": "2024", "sex": "total", "age_group": "all", "measure": "value",
           "factor": "", "factor_level": "", "value": 74.3, "unit": "percent", "numerator": None,
           "denominator": None, "status": "observed", "flags": "", "source": "Sotkanet",
           "source_url": "", "source_file": "a.csv", "source_row": 2, "also_in": "",
           "imputation_method": "", "imputation_basis": ""}
    row.update(changes)
    return row


def raw(source, region, extra):
    return {"source": source, "region": region, "_extra": extra}


class Statistics(unittest.TestCase):
    def test_wilson_interval(self):
        self.assertEqual(wilson_interval(50, 100), (40.4, 59.6))
        low, high = wilson_interval(0, 20)             # stays inside 0-100 even at the edge
        self.assertEqual(low, 0.0)
        self.assertGreater(high, 0)
        self.assertEqual(wilson_interval(5, 0), (None, None))

    def test_interval_narrows_with_more_people(self):
        small, large = wilson_interval(70, 100), wilson_interval(7000, 10000)
        self.assertGreater(small[1] - small[0], large[1] - large[0])

    def test_spearman(self):
        self.assertAlmostEqual(spearman([1, 2, 3, 4], [10, 20, 30, 40]), 1.0)
        self.assertAlmostEqual(spearman([1, 2, 3, 4], [40, 30, 20, 10]), -1.0)
        self.assertAlmostEqual(spearman([1, 2, 3, 4], [1, 1, 1, 1]), 0.0)   # no variation

    def test_holm_adjust(self):
        adjusted = holm_adjust([0.01, 0.04, 0.03])
        self.assertEqual([round(p, 2) for p in adjusted], [0.03, 0.06, 0.06])
        self.assertEqual(holm_adjust([0.9, 0.8]), [1.0, 1.0])               # capped at 1

    def test_p_values(self):
        strong = permutation_p_value(list(range(22)), list(range(22)), permutations=500)
        self.assertLess(strong, 0.01)
        # the fixed seed makes the test repeatable
        a, b = [3, 1, 4, 1, 5, 9, 2, 6], [2, 7, 1, 8, 2, 8, 1, 8]
        self.assertEqual(permutation_p_value(a, b, 300), permutation_p_value(a, b, 300))
        self.assertLess(normal_p_value(-0.3, 300), 0.001)
        self.assertGreater(normal_p_value(0.05, 300), 0.3)


class RegionResolution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ref = Context().ref

    def test_sotkanet_regions_are_resolved_by_id(self):
        resolve = s04_standardise._resolve_region
        self.assertEqual(resolve(self.ref, raw("Sotkanet", "Helsingin kaupunki", {"region_id": 960}))[0], "90")
        self.assertEqual(resolve(self.ref, raw("Sotkanet", "Koko maa", {"region_id": 658}))[:2], ("FI", "country"))
        # Five different regions are called "Ahvenanmaa"; only id 956 is the one the project uses.
        levels = {rid: resolve(self.ref, raw("Sotkanet", "Ahvenanmaa", {"region_id": rid}))[1]
                  for rid in (956, 844, 850, 728, 506)}
        self.assertEqual(levels[956], "autonomous_region")
        self.assertEqual(len(set(levels.values())) > 1, True)
        self.assertIsNone(resolve(self.ref, raw("Sotkanet", "410", {"region_id": 99999999})))

    def test_other_sources_are_resolved_by_name(self):
        resolve = s04_standardise._resolve_region
        self.assertEqual(resolve(self.ref, raw("Kela/avoindata.fi", "Pirkanmaa", {}))[0], "08")
        self.assertEqual(resolve(self.ref, raw("Kela/avoindata.fi", "Tuntematon", {}))[1], "unknown")
        self.assertNotIn("unknown", IN_SCOPE_LEVELS)
        self.assertEqual(resolve(self.ref, raw("Finnish Cancer Registry", "Finland (excluding Åland)", {}))[0], "FI")
        self.assertEqual(resolve(self.ref, raw("StatFin/Tilastokeskus", "", {}))[0], "FI")
        self.assertIsNone(resolve(self.ref, raw("Finnish Cancer Registry", "Atlantis", {})))

    def test_age_groups(self):
        self.assertEqual(s04_standardise._age_group("0 - 14"), "0-14")
        self.assertEqual(s04_standardise._age_group("65 -"), "65+")
        self.assertEqual(s04_standardise._age_group("Yhteensä"), "all")
        self.assertEqual(s04_standardise._age_group(""), "all")


class Deduplication(unittest.TestCase):
    def test_same_value_keeps_the_row_with_counts(self):
        ctx = Context()
        plain = observation(source_file="raw.csv")
        full = observation(source_file="team.csv", source="Finnish Cancer Registry",
                           numerator=28686.0, denominator=38630.0)
        kept = s06_deduplicate.deduplicate(ctx, [plain, full])
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["source_file"], "team.csv")
        self.assertEqual(kept[0]["also_in"], "raw.csv")
        self.assertEqual(ctx.stats["06 deduplicate"]["duplicates removed"], 1)
        self.assertEqual(ctx.quarantine, [])

    def test_numerator_alone_beats_no_counts(self):
        kept = s06_deduplicate.deduplicate(Context(), [observation(source_file="a.csv"),
                                                       observation(source_file="b.csv", numerator=100.0)])
        self.assertEqual(kept[0]["source_file"], "b.csv")

    def test_conflicting_values_are_quarantined(self):
        ctx = Context()
        kept = s06_deduplicate.deduplicate(ctx, [
            observation(source="Sotkanet", value=73.4, source_file="sotkanet.csv"),
            observation(source="Finnish Cancer Registry", value=73.8, source_file="registry.csv")])
        self.assertEqual([r["source_file"] for r in kept], ["registry.csv"])   # preferred source wins
        self.assertEqual(len(ctx.quarantine), 1)
        self.assertIn("conflicts with registry.csv", ctx.quarantine[0]["reason"])

    def test_different_groups_are_not_duplicates(self):
        rows = [observation(), observation(sex="male"), observation(year=2023, period="2023"),
                observation(factor="education", factor_level="tertiary")]
        self.assertEqual(len(s06_deduplicate.deduplicate(Context(), rows)), 4)


class QualityChecks(unittest.TestCase):
    def check(self, **changes):
        ctx = Context()
        passed = s07_quality_checks.quality_checks(ctx, [observation(**changes)])
        return passed, ctx.quarantine

    def test_valid_row_passes(self):
        passed, rejected = self.check(numerator=28686.0, denominator=38630.0)
        self.assertEqual((len(passed), rejected), (1, []))

    def test_percent_must_match_counts(self):
        passed, rejected = self.check(value=80.0, numerator=28686.0, denominator=38630.0)
        self.assertEqual(passed, [])
        self.assertIn("percent does not match", rejected[0]["reason"])

    def test_range_and_dates(self):
        self.assertIn("above allowed maximum", self.check(value=140.0)[1][0]["reason"])
        self.assertIn("future", self.check(year=2031)[1][0]["reason"])
        # a target may lie in the future, an observation may not
        self.assertEqual(len(self.check(year=2035, status="strategy_target")[0]), 1)

    def test_small_cell_uses_the_base_not_the_numerator(self):
        # 20 of 25 invited: unstable. 20 participants out of 2,000 invited: not small.
        self.assertIn("small_cell", self.check(value=80.0, numerator=20.0, denominator=25.0)[0][0]["flags"])
        self.assertNotIn("small_cell", self.check(value=1.0, numerator=20.0, denominator=2000.0)[0][0]["flags"])
        # only the numerator is published: the base is recovered from the percentage
        self.assertIn("small_cell", self.check(value=80.0, numerator=20.0)[0][0]["flags"])


if __name__ == "__main__":
    unittest.main()
