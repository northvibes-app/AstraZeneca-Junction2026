"""Step 10: INTEGRATE

Produce the final long table and the small analysis subset.
"""
from common import ANALYSIS_WINDOW_YEARS, ANALYSIS_YEAR


def integrate(ctx, rows):
    """Produce the final long table: fixed order, stable ids, plus a small analysis subset."""
    step = "10 integrate"
    rows.sort(key=lambda r: (r["indicator_key"], r["region_level"], r["region_code"], r["year"],
                             r["sex"], r["age_group"], r["detail"], r["measure"], r["factor_level"]))
    for i, row in enumerate(rows, start=1):
        row["observation_id"] = f"OBS{i:07d}"
    ctx.count(step, "observations in clean layer", len(rows))

    # Analysis subset: national and regional figures the equity analysis works with.
    # Kela entitlements and deaths by age group stay in the clean layer only.
    analysis = [r for r in rows
                if r["region_level"] in ("country", "wellbeing_county")
                and r["kind"] in ("outcome", "context", "reference", "population")
                and r["age_group"] == "all"
                and (r["year"] > ANALYSIS_YEAR - ANALYSIS_WINDOW_YEARS or r["kind"] == "reference")]
    ctx.count(step, "observations in analysis subset", len(analysis))
    ctx.results["observations"] = rows
    ctx.results["analysis"] = analysis
    return rows
