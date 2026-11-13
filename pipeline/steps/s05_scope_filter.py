"""Step 5: SCOPE_FILTER

Keep only the administrative levels the project works with.
"""
from common import IN_SCOPE_LEVELS


def scope_filter(ctx, rows):
    """Keep country, wellbeing services county, Åland and municipality level only.

    Rows at other levels are valid data, just not needed, so they are counted
    as filtered and not sent to quarantine.
    """
    step = "05 scope_filter"
    for row in rows:
        if row["region_level"] in IN_SCOPE_LEVELS:
            ctx.count(step, "rows kept")
            yield row
        else:
            ctx.count(step, "filtered out")
            ctx.count(step, f"filtered out: level {row['region_level']}")
