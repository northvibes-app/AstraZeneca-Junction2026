"""Step 6: DEDUPLICATE

Remove repeated observations and resolve conflicting ones by a fixed rule.
"""
from common import SOURCE_PRIORITY


# Two rows describe the same observation when all of these fields agree.
KEY_FIELDS = ["indicator_key", "region_code", "period", "sex", "age_group", "detail",
              "measure", "factor", "factor_level"]


def _preference(row):
    """Lower is better: the row that carries more of the underlying counts wins,
    then the more authoritative source."""
    completeness = 0 if row["numerator"] is not None and row["denominator"] is not None \
        else 1 if row["numerator"] is not None else 2
    source_rank = SOURCE_PRIORITY.index(row["source"]) if row["source"] in SOURCE_PRIORITY else 99
    return (completeness, source_rank)


def deduplicate(ctx, rows):
    """Keep one row per observation.

    Same key and same value  -> a true duplicate. The more complete row is kept and
                                notes where else the value was found.
    Same key, different value -> a conflict. The preferred source is kept and the
                                other row is quarantined for a human to look at.
    """
    step, kept = "06 deduplicate", {}
    for row in rows:
        key = tuple(row[f] for f in KEY_FIELDS)
        other = kept.get(key)
        if other is None:
            kept[key] = row
            continue
        winner, loser = (other, row) if _preference(other) <= _preference(row) else (row, other)
        if abs(winner["value"] - loser["value"]) <= 0.05:
            ctx.count(step, "duplicates removed")
            ctx.count(step, "duplicates removed: " + (
                "same file" if winner["source_file"] == loser["source_file"] else "across files"))
            winner["also_in"] = loser["source_file"]
        else:
            ctx.reject(step, loser, f"conflicts with {winner['source_file']} (value {winner['value']})")
        kept[key] = winner
    ctx.count(step, "rows kept", len(kept))
    return list(kept.values())
