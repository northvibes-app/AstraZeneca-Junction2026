"""Step 8: COMPLETENESS

Detect and record what is missing (DATA GAP records).
"""
from collections import defaultdict

from common import ANALYSIS_WINDOW_YEARS, ANALYSIS_YEAR, CURRENT_YEAR


def completeness(ctx, rows):
    """Find the holes in the data and write them down as DATA GAP records.

    This step only detects and records. A gap is a result in its own right: it
    tells decision-makers what cannot be judged yet. Step 9 decides which gaps
    may receive a labelled fallback value.
    """
    step, ref, gaps = "08 completeness", ctx.ref, []
    county_codes = sorted(c["region_code"] for c in ref.counties)
    first_year = ANALYSIS_YEAR - ANALYSIS_WINDOW_YEARS + 1

    # (a) Region-year grid: every outcome and context indicator should have a value
    #     for all 22 regions in every year between its first and last published year.
    grid = defaultdict(dict)     # indicator_key -> {(region_code, year): row}
    for row in rows:
        if (row["region_level"] == "wellbeing_county" and row["sex"] == "total"
                and row["factor"] == "" and row["kind"] in ("outcome", "context")
                and first_year <= row["year"] <= CURRENT_YEAR):
            grid[row["indicator_key"]][(row["region_code"], row["year"])] = row
    latest = {}
    for key in sorted(grid):
        years = [year for (_, year) in grid[key]]
        latest[key] = max(years)
        ctx.count(step, "indicators checked for region-year coverage")
        for year in range(min(years), max(years) + 1):
            for code in county_codes:
                if (code, year) not in grid[key]:
                    gaps.append({"gap_type": "region_year_missing",
                                 "pathway_stage": ref.indicator_by_key[key]["pathway_stage"],
                                 "indicator_key": key, "year": year, "region_code": code,
                                 "region_name": ref.region_by_code[code]["name_en"],
                                 "description": "No value published for this region and year",
                                 "fallback": "", "fallback_value": ""})
                    ctx.count(step, "gaps: region-year missing")

    # (b) Information the challenge needs but no open source provides.
    for g in ref.known_data_gaps:
        gaps.append({"gap_type": "no_open_data", "pathway_stage": g["pathway_stage"],
                     "indicator_key": "", "year": "", "region_code": "", "region_name": "",
                     "description": f"{g['missing_information']}. {g['why_it_matters']}",
                     "fallback": "none", "fallback_value": ""})
        ctx.count(step, "gaps: no open data")

    ctx.results["data_gaps"] = gaps
    ctx.results["grid"] = grid
    ctx.results["latest_year"] = latest
    return rows
