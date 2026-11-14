"""Read screening figures by population group from the Finnish Cancer Registry.

The Registry publishes, for each national screening programme, how many people
were invited, how many took part and how many came to the follow-up examination,
split by level of education, native language and (colorectal only) sex. These are
the only open figures that compare GROUPS OF PEOPLE directly instead of regions.

Pages read (annual statistics 2020-2024 and preliminary statistics 2025):
    https://stats.cancerregistry.fi/joukkistilastot/<programme>.html
    https://stats.cancerregistry.fi/joukkistilastot/ennakkotilastot/<programme>_preliminary.html

Output: Statistics/screening_by_population_group.csv, one row per
year x programme x grouping x group x sex x measure, with numerator and denominator.

Run:  python3 pipeline/fetch_screening_groups.py
"""
import csv
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from net import ChangeLog, download      # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://stats.cancerregistry.fi/joukkistilastot/"
PAGES = [  # (programme, page, status of the figures on that page)
    ("breast", "breast.html", "observed"),
    ("colorectal", "colorectal.html", "observed"),
    ("cervical", "cervix.html", "observed"),
    ("breast", "ennakkotilastot/breast_preliminary.html", "preliminary"),
    ("colorectal", "ennakkotilastot/colorectal_preliminary.html", "preliminary"),
    ("cervical", "ennakkotilastot/cervix_preliminary.html", "preliminary"),
]
GROUPINGS = {"Native language": "native_language", "Education": "education", "Sex": "sex"}
SEXES = {"Men": "male", "Women": "female", "Total": "total"}
COLUMNS = ["year", "status", "programme", "grouping", "group", "sex", "measure",
           "numerator_n", "denominator_n", "percent", "source_url"]


def cells(row_html):
    found = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row_html, flags=re.S)
    return [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in found]


def parse_page(text, programme, status, url):
    rows = []
    for table in re.finditer(r"<table.*?</table>", text, flags=re.S):
        lines = [cells(r) for r in re.findall(r"<tr.*?</tr>", table.group(0), flags=re.S)]
        lines = [line for line in lines if line]
        if len(lines) < 3 or lines[0][0] not in GROUPINGS:
            continue
        header = lines[0]
        has_sex_column = len(header) > 1 and header[1] == "Sex"
        measures = header[2:] if has_sex_column else header[1:]
        # Only the table that starts with the invited population is wanted. Other tables
        # with the same first heading describe test results or interval cancers.
        if not measures or measures[0] not in ("Invited", "Picked") or len(measures) < 2:
            continue
        if header[0] == "Sex" and has_sex_column is False and measures[0] != "Picked":
            continue
        # The year is the closest heading above the table that consists of a year only.
        years = re.findall(r"<h[1-6][^>]*>\s*(20\d\d)\s*</h[1-6]>", text[:table.start()])
        if not years:
            continue
        year = years[-1]

        label_columns = 2 if has_sex_column else 1
        for line in lines[2:]:                       # lines[1] is the "N, N, %" sub-header
            group = line[0]
            if header[0] == "Sex":                   # the group itself is the sex
                sex, group_name, grouping = SEXES.get(group), "all", "sex"
            else:
                sex = SEXES.get(line[1]) if has_sex_column else "total"
                group_name, grouping = group, GROUPINGS[header[0]]
            values = line[label_columns:]
            if sex is None or len(values) < 3:
                continue
            try:
                invited, attended, percent = int(values[0]), int(values[1]), float(values[2])
            except ValueError:
                continue
            common = [year, status, programme, grouping, group_name, sex]
            rows.append(common + ["participation", attended, invited, percent, url])

            # Follow-up attendance: people who came to colonoscopy / colposcopy out of those
            # who needed it. Column k holds a count and a percentage; its base is the count
            # in the column before it.
            for k, name in enumerate(measures):
                if k >= 2 and name.startswith("Attended col"):
                    n_index = 1 + 2 * (k - 1)
                    base_index = 1 + 2 * (k - 2)
                    try:
                        rows.append(common + ["followup_attendance", int(values[n_index]),
                                              int(values[base_index]), float(values[n_index + 1]),
                                              url])
                    except (ValueError, IndexError):
                        pass
    return rows


def main():
    changes = ChangeLog(ROOT / "Statistics/screening_groups_manifest.json")
    rows = []
    for programme, page, status in PAGES:
        url = BASE + page
        raw = download(url, timeout=180)
        state = changes.record(page, raw)
        found = parse_page(raw.decode("utf-8", "replace"), programme, status, url)
        rows += found
        print(f"{page}: {len(found)} rows, {state} since last download")

    # The same table can appear more than once on a page; keep each figure once.
    unique = {tuple(r[:7]): r for r in rows}
    rows = sorted(unique.values(), key=lambda r: (r[2], r[6], r[3], r[0], r[4], r[5]))
    out = ROOT / "Statistics/screening_by_population_group.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        w.writerows(rows)
    changes.save()
    print(f"{out.name}: {len(rows)} rows")


if __name__ == "__main__":
    main()
