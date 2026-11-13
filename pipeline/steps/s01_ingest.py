"""Step 1: INGEST

Read every source into one common raw layout.

Each row remembers the file and line it came from, and every input file gets a
checksum, so any published figure can be traced back to its exact origin.
"""
import csv
import gzip
import hashlib
import json

from common import RAW_COLUMNS, STATS


# Files that already use the 14-column raw layout.
RAW_LAYOUT_FILES = ["cancer_stats_raw.csv.gz", "equity_context_raw.csv.gz"]


def _adapt_breast(row):
    """Team file: breast screening by region -> raw layout."""
    extra = {"invited_n": row["invited_n"], "attended_n": row["attended_n"], "status": "observed"}
    return {"source": "Finnish Cancer Registry", "source_url": row["source_url"],
            "dataset": "curated breast_screening_by_region",
            "indicator": "Breast screening participation", "year": row["year"],
            "region": row["region"], "sex": "total", "age_group": "", "cancer_site": "",
            "measure": "value", "value": row["participation_percent"], "unit": "percent",
            "extra": json.dumps(extra), "scraped_at": ""}


def _adapt_cervical_equity(row):
    """Team file: cervical screening by education and native language -> raw layout."""
    extra = {"invited_n": row["invited_n"], "attended_n": row["attended_n"],
             "status": row["status"], "grouping": row["grouping"], "group": row["group"]}
    return {"source": "Finnish Cancer Registry", "source_url": row["source_url"],
            "dataset": "curated cervical_screening_equity",
            "indicator": "Cervical screening participation by group", "year": row["year"],
            "region": "Finland", "sex": "total", "age_group": "", "cancer_site": "",
            "measure": "value", "value": row["participation_percent"], "unit": "percent",
            "extra": json.dumps(extra), "scraped_at": ""}


def _adapt_national(row):
    """Team file: national key statistics, targets and projections -> raw layout."""
    extra = {"status": row["status"], "geography": row["geography"], "notes": row["notes"]}
    return {"source": "Team curated", "source_url": row["source_url"],
            "dataset": "curated national_key_statistics", "indicator": row["indicator"],
            "year": row["period"], "region": "Finland", "sex": "total", "age_group": "",
            "cancer_site": "", "measure": "value", "value": row["value"], "unit": row["unit"],
            "extra": json.dumps(extra), "scraped_at": ""}


# Files with their own layout need an adapter that maps them to the raw layout.
ADAPTED_FILES = {
    "breast_screening_by_region_2024.csv": _adapt_breast,
    "cervical_screening_equity_2025_preliminary.csv": _adapt_cervical_equity,
    "national_key_statistics.csv": _adapt_national,
}


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def ingest(ctx):
    """Read all sources. Each row remembers the file and line it came from (lineage)."""
    manifest = []
    for name in RAW_LAYOUT_FILES + list(ADAPTED_FILES):
        path = STATS / name
        if not path.exists():
            ctx.count("01 ingest", f"missing file: {name}")
            continue
        opener = gzip.open if name.endswith(".gz") else open
        adapter = ADAPTED_FILES.get(name)
        rows = 0
        # utf-8-sig removes the byte-order mark some exports put before the first column name.
        with opener(path, "rt", encoding="utf-8-sig", newline="") as f:
            for line_no, row in enumerate(csv.DictReader(f), start=2):
                raw = adapter(row) if adapter else {c: row.get(c, "") for c in RAW_COLUMNS}
                raw["_file"], raw["_row"] = name, line_no
                rows += 1
                ctx.count("01 ingest", "rows read")
                yield raw
        # The checksum proves later which exact file version a result was built from.
        manifest.append({"file": name, "rows": rows, "bytes": path.stat().st_size,
                         "sha256": _sha256(path)})
    ctx.results["manifest"] = manifest
