"""Step 3: VALIDATE_SCHEMA

Check structure and types; rows that cannot be read reliably go to quarantine.
"""
import json
import re
import unicodedata

from common import RAW_COLUMNS


REQUIRED = ["source", "dataset", "indicator", "year", "measure", "value"]
PERIOD = re.compile(r"^\d{4}(-\d{4})?$")      # a year, or a range such as 2021-2023


def validate_schema(ctx, rows):
    """Check structure and types. A row that cannot be read reliably is quarantined."""
    step = "03 validate_schema"
    for row in rows:
        # Text hygiene: trim whitespace and use one Unicode form, so "Päijät-Häme"
        # typed in two different ways still compares as equal.
        for col in RAW_COLUMNS:
            row[col] = unicodedata.normalize("NFC", (row[col] or "").strip())

        missing = [c for c in REQUIRED if row[c] == ""]
        if missing:
            ctx.reject(step, row, "required field empty: " + ", ".join(missing))
            continue
        if not PERIOD.match(row["year"]):
            ctx.reject(step, row, "year is not a year or a year range")
            continue
        try:
            row["_value"] = float(row["value"].replace(",", ".").replace(" ", ""))
        except ValueError:
            ctx.reject(step, row, "value is not a number")
            continue
        try:
            extra = json.loads(row["extra"]) if row["extra"] else {}
            if not isinstance(extra, dict):
                raise ValueError
            row["_extra"] = extra
        except ValueError:
            ctx.reject(step, row, "extra is not valid JSON")
            continue
        ctx.count(step, "rows passed")
        yield row
