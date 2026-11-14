"""Step 12: DERIVE

Add the statistics that turn a bare percentage into something that can be judged:
its base, its uncertainty, a multi-year average and its position against the target.
"""
from collections import defaultdict

from common import POOLED_YEARS, SCREENING_TARGET, wilson_interval


def derive(ctx):
    """Build one statistics record per outcome figure.

    denominator      the published base, or the base recovered from participants and
                     percentage where only those two are published (marked as derived)
    ci_low, ci_high  95 % confidence interval of a percentage. A small region has a
                     wide interval, so a low value there is weaker evidence of a gap
    pooled_value     average of the latest years, which smooths chance variation
    target_status    for screening participation, against the national 80 % target:
                     below_target / near_target (interval includes 80) / at_or_above_target
    """
    step, latest = "12 derive", ctx.results["latest_year"]
    analysis = [r for r in ctx.results["analysis"]
                if r["kind"] == "outcome" and r["status"] != "imputed"
                and r["unit"] in ("percent", "index")]

    # Year series of every figure, needed for the multi-year average.
    history = defaultdict(dict)
    series_key = lambda r: (r["indicator_key"], r["region_code"], r["sex"], r["factor"], r["factor_level"])
    for r in analysis:
        history[series_key(r)][r["year"]] = r["value"]

    stats = []
    for r in analysis:
        is_group_figure = r["factor"] != "" or r["sex"] != "total"
        if not is_group_figure and r["year"] != latest.get(r["indicator_key"]):
            continue                    # for plain regional figures only the latest year is needed

        denominator, source = r["denominator"], "published" if r["denominator"] is not None else ""
        if denominator is None and r["numerator"] is not None and r["value"] > 0 and r["unit"] == "percent":
            denominator, source = round(r["numerator"] / (r["value"] / 100)), "derived"
            ctx.count(step, "denominators derived from participants and percentage")

        ci_low = ci_high = ""
        if r["unit"] == "percent" and denominator:
            successes = r["numerator"] if r["numerator"] is not None else r["value"] / 100 * denominator
            ci_low, ci_high = wilson_interval(successes, denominator)
            ctx.count(step, "confidence intervals computed")

        years = [y for y in history[series_key(r)] if r["year"] - POOLED_YEARS < y <= r["year"]]
        pooled = round(sum(history[series_key(r)][y] for y in years) / len(years), 1)

        target_status = ""
        if r["indicator_key"].startswith("screening_participation"):
            if ci_high != "" and ci_high < SCREENING_TARGET:
                target_status = "below_target"
            elif ci_low != "" and ci_low >= SCREENING_TARGET:
                target_status = "at_or_above_target"
            elif ci_low != "":
                target_status = "near_target"
            else:                                   # no base known, so no interval
                target_status = "below_target" if r["value"] < SCREENING_TARGET else "at_or_above_target"
            ctx.count(step, f"target status: {target_status}")

        stats.append({"observation_id": r["observation_id"], "indicator_key": r["indicator_key"],
                      "indicator_name": r["indicator_name"], "region_code": r["region_code"],
                      "region_name": r["region_name"], "year": r["year"], "sex": r["sex"],
                      "factor": r["factor"], "factor_level": r["factor_level"], "value": r["value"],
                      "unit": r["unit"], "numerator": r["numerator"], "denominator": denominator,
                      "denominator_source": source, "ci_low": ci_low, "ci_high": ci_high,
                      "pooled_value": pooled, "pooled_years": len(years),
                      "target_status": target_status, "status": r["status"]})
    ctx.count(step, "outcome figures with statistics", len(stats))
    ctx.results["outcome_stats"] = stats
    ctx.results["stats_by_id"] = {s["observation_id"]: s for s in stats}
