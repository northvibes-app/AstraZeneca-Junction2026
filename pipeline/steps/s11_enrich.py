"""Step 11: ENRICH

Attach each region's social and economic context.
"""
from collections import defaultdict

from common import ANALYSIS_YEAR


def enrich(ctx):
    """Build one profile row per region with its context values.

    If a context indicator has no value for the analysis year, the most recent
    earlier year is used and that year is written next to the value.
    """
    step, ref = "11 enrich", ctx.ref
    by_region = defaultdict(lambda: defaultdict(dict))    # region -> indicator -> year -> value
    for r in ctx.results["analysis"]:
        if (r["kind"] in ("context", "population") and r["sex"] == "total" and r["factor"] == ""
                and r["status"] != "imputed"):
            by_region[r["region_code"]][r["indicator_key"]][r["year"]] = r["value"]

    profiles = []
    for region in ref.regions:
        if region["level"] not in ("country", "wellbeing_county"):
            continue
        row = {"region_code": region["region_code"], "region_name": region["name_en"],
               "region_level": region["level"]}
        for factor in ref.factors:
            key = factor["context_indicator_key"]
            years = [y for y in by_region[region["region_code"]][key] if y <= ANALYSIS_YEAR]
            if years:
                row[key] = by_region[region["region_code"]][key][max(years)]
                row[key + "_year"] = max(years)
                ctx.count(step, "context values attached")
            else:
                row[key], row[key + "_year"] = "", ""
                ctx.count(step, "context values missing")
        # Population, used later to weight regional averages.
        years = [y for y in by_region[region["region_code"]]["population"] if y <= ANALYSIS_YEAR]
        row["population"] = by_region[region["region_code"]]["population"][max(years)] if years else ""
        row["population_year"] = max(years) if years else ""
        profiles.append(row)
    ctx.results["region_profile"] = profiles
