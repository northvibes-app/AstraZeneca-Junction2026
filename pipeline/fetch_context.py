"""Download the equity-context indicators from the Sotkanet open API (THL).

The team's raw file (Statistics/cancer_stats_raw.csv.gz) holds cancer outcomes but
no information about income, education, language or smoking. This script fetches
those published aggregates and stores them in the SAME 14-column raw layout, so
they travel through exactly the same pipeline steps as every other source.

It also saves the Sotkanet region register, which the pipeline needs to tell
apart regions that share a name (for example the five different "Ahvenanmaa").

Run:  python3 pipeline/fetch_context.py
"""
import csv
import gzip
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from net import ChangeLog, download      # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
API = "https://sotkanet.fi/rest/1.1"
YEARS = range(2015, 2026)

# indicator id -> why we need it (documentation only; names come from the API)
CONTEXT_INDICATORS = {
    3099: "general low-income rate (income factor)",
    181: "unemployed, % of labour force (income factor, second measure)",
    180: "education level index (education factor)",
    187: "native language other than Finnish/Swedish/Sami per 1,000 (language factor)",
    4404: "daily smokers, % (smoking factor)",
    4408: "daily smokers, %, low education (smoking stratified by education)",
    4409: "daily smokers, %, medium education (smoking stratified by education)",
    4410: "daily smokers, %, high education (smoking stratified by education)",
    6411: "primary care doctor wait over 7 days, % (access factor)",
    127: "population on 31 Dec (weights for regional averages)",
    # Screening participation is already in the team's raw file, but without the count
    # of participants. Fetching it again adds that count, which the pipeline needs for
    # confidence intervals. The duplicate values are removed by the deduplication step.
    3621: "breast screening participation, with participant count",
    6103: "colorectal screening participation, with participant count",
    3620: "cervical screening participation, with participant count",
}

RAW_COLUMNS = ["source", "source_url", "dataset", "indicator", "year", "region", "sex",
               "age_group", "cancer_site", "measure", "value", "unit", "extra", "scraped_at"]


def get(path):
    """Download one API resource. Returns (parsed JSON, raw bytes)."""
    raw = download(f"{API}/{path}")
    return json.loads(raw), raw


def main():
    scraped_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # 1) Region register: id -> administrative level and names.
    changes = ChangeLog(ROOT / "Statistics/equity_context_manifest.json")
    regions, _ = get("regions")
    with open(ROOT / "pipeline/reference/sotkanet_regions.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["region_id", "category", "code", "name_fi", "name_en"])
        for r in sorted(regions, key=lambda r: r["id"]):
            w.writerow([r["id"], r["category"], r.get("code", ""), r["title"]["fi"],
                        r["title"].get("en", "")])
    region_name = {r["id"]: r["title"]["fi"] for r in regions}
    print(f"sotkanet_regions.csv: {len(regions)} regions")

    # 2) Context indicators in the shared raw layout.
    rows = []
    for ind in CONTEXT_INDICATORS:
        title = get(f"indicators/{ind}")[0]["title"]["fi"]
        query = "&".join([f"indicator={ind}"] + [f"years={y}" for y in YEARS]
                         + ["genders=total", "genders=male", "genders=female"])
        data, raw = get(f"json?{query}")
        state = changes.record(f"indicator {ind}", raw)
        for x in data:
            if x.get("value") is None or x["region"] not in region_name:
                continue
            extra = {"indicator_id": ind, "region_id": x["region"], "n": x.get("absValue")}
            rows.append(["Sotkanet", "https://sotkanet.fi/sotkanet/fi/index", f"indicator {ind}",
                         title, x["year"], region_name[x["region"]], x["gender"], "", "",
                         "value", x["value"], "", json.dumps(extra), scraped_at])
        print(f"indicator {ind}: {len(data)} values, {state} since last download  ({title})")

    out = ROOT / "Statistics/equity_context_raw.csv.gz"
    with gzip.open(out, "wt", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(RAW_COLUMNS)
        w.writerows(rows)
    changes.save()
    print(f"{out.name}: {len(rows)} rows")


if __name__ == "__main__":
    main()
