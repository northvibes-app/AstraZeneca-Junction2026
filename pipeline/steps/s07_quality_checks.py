"""Step 7: QUALITY_CHECKS

Apply range, date and arithmetic rules; flag outliers and small cells.
"""
import statistics
from collections import defaultdict

import math

from common import CURRENT_YEAR, OUTLIER_Z, PERCENT_TOLERANCE, SKEW_RATIO, SMALL_CELL_THRESHOLD


def quality_checks(ctx, rows):
    """Apply business rules. Impossible values are quarantined, unusual ones are flagged."""
    step, ref, passed = "07 quality_checks", ctx.ref, []
    for row in rows:
        cat = ref.indicator_by_key[row["indicator_key"]]
        value, num, den = row["value"], row["numerator"], row["denominator"]

        # Rule 1: the value must lie inside the range that is possible for its indicator.
        if cat["min_value"] != "" and value < float(cat["min_value"]):
            ctx.reject(step, row, "value below allowed minimum")
            continue
        if cat["max_value"] != "" and value > float(cat["max_value"]):
            ctx.reject(step, row, "value above allowed maximum")
            continue
        # Rule 2: measured values cannot come from the future. Targets and projections can.
        if row["year"] > CURRENT_YEAR and row["status"] in ("observed", "preliminary"):
            ctx.reject(step, row, "observed value dated in the future")
            continue
        if row["year"] < 1950:
            ctx.reject(step, row, "implausible year")
            continue
        # Rule 3: a percentage must agree with the counts published next to it.
        if row["unit"] == "percent" and num is not None and den is not None:
            if den <= 0 or num > den:
                ctx.reject(step, row, "numerator and denominator inconsistent")
                continue
            if abs(100 * num / den - value) > PERCENT_TOLERANCE:
                ctx.reject(step, row, "percent does not match numerator / denominator")
                continue

        flags = []
        if row["status"] != "observed":
            flags.append(row["status"])                       # e.g. preliminary, projection
        # A percentage is unstable when it rests on few people. The right yardstick is
        # its base (the denominator). Where only the numerator is published, the base
        # is recovered from numerator and percentage.
        base = den
        if base is None and num is not None and value > 0 and row["unit"] == "percent":
            base = num / (value / 100)
        if row["unit"] == "percent" and base is not None and base < SMALL_CELL_THRESHOLD:
            flags.append("small_cell")
        row["_flags"] = flags
        passed.append(row)

    # Outlier screening with the median and the median absolute deviation (MAD).
    # Both are robust: one extreme municipality cannot hide itself by shifting the average.
    groups = defaultdict(list)
    for row in passed:
        if row["unit"] != "count" and row["region_level"] in ("wellbeing_county", "municipality"):
            groups[(row["indicator_key"], row["region_level"], row["year"], row["sex"],
                    row["factor_level"])].append(row)
    for members in groups.values():
        if len(members) < 10:
            continue
        values = [m["value"] for m in members]
        # Strongly right-skewed measures (for example other-language speakers per 1,000,
        # where a few cities are far above everyone else) are judged on a log scale.
        # Otherwise the ordinary city-countryside difference is flagged as an error.
        log_scale = min(values) > 0 and max(values) / statistics.median(values) > SKEW_RATIO
        if log_scale:
            values = [math.log(v) for v in values]
        median = statistics.median(values)
        mad = statistics.median(abs(v - median) for v in values)
        if mad == 0:
            continue
        for m, v in zip(members, values):
            if abs(0.6745 * (v - median) / mad) > OUTLIER_Z:
                m["_flags"].append("outlier")

    for row in passed:
        for flag in row["_flags"]:
            ctx.count(step, f"flagged: {flag}")
        row["flags"] = "|".join(row.pop("_flags"))
    ctx.count(step, "rows passed", len(passed))
    return passed
