"""Step 2: PROFILE

Describe the raw data before anything is changed.
"""
from collections import Counter

from common import RAW_COLUMNS


def profile(ctx, rows):
    """Describe the raw data per source: size, empty fields, distinct values, year range.

    Profiling changes nothing. It documents what arrived, so later surprises
    (a new sex label, an empty unit column) can be traced to the input.
    """
    prof = {}
    for row in rows:
        p = prof.setdefault(row["source"], {"rows": 0, "empty": Counter(), "distinct": {},
                                            "year_min": None, "year_max": None})
        p["rows"] += 1
        for col in RAW_COLUMNS:
            value = row[col]
            if value == "":
                p["empty"][col] += 1
            seen = p["distinct"].setdefault(col, set())
            if len(seen) <= 60:          # enough to list small vocabularies such as sex
                seen.add(value)
        year = row["year"][:4]
        if year.isdigit():
            p["year_min"] = min(p["year_min"] or year, year)
            p["year_max"] = max(p["year_max"] or year, year)
        ctx.count("02 profile", "rows profiled")
        yield row
    report = {}
    for source, p in prof.items():
        report[source] = {
            "rows": p["rows"], "year_min": p["year_min"], "year_max": p["year_max"],
            "empty_share": {c: round(p["empty"][c] / p["rows"], 4) for c in RAW_COLUMNS},
            "distinct_values": {c: (sorted(v) if len(v) <= 12 else f"{'>' if len(v) > 60 else ''}{min(len(v), 60)} values")
                                for c, v in p["distinct"].items() if c in ("sex", "unit", "measure", "dataset")},
        }
    ctx.results["profile"] = report
