"""Download regional screening and context indicators from Sotkanet (THL open API).

Writes four CSVs next to this file. Only published aggregates are fetched.
Run:  python3 Statistics/fetch_sotkanet.py
"""
import csv
import json
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
API = "https://sotkanet.fi/rest/1.1"
META = "https://sotkanet.fi/sotkanet/en/metadata/indicators/{}"
YEAR = 2024
TREND_YEARS = [2021, 2022, 2023, 2024]

# Same English names as breast_screening_by_region_2024.csv
REGION_EN = {
    "Koko maa": "Finland",
    "Helsingin kaupunki": "City of Helsinki",
    "Vantaan ja Keravan hyvinvointialue": "Vantaa and Kerava",
    "Länsi-Uudenmaan hyvinvointialue": "West Uusimaa",
    "Itä-Uudenmaan hyvinvointialue": "East Uusimaa",
    "Keski-Uudenmaan hyvinvointialue": "Central Uusimaa",
    "Varsinais-Suomen hyvinvointialue": "Southwest Finland",
    "Satakunnan hyvinvointialue": "Satakunta",
    "Kanta-Hämeen hyvinvointialue": "Kanta-Häme",
    "Pirkanmaan hyvinvointialue": "Pirkanmaa",
    "Päijät-Hämeen hyvinvointialue": "Päijät-Häme",
    "Kymenlaakson hyvinvointialue": "Kymenlaakso",
    "Etelä-Karjalan hyvinvointialue": "South Karelia",
    "Etelä-Savon hyvinvointialue": "South Savo",
    "Pohjois-Savon hyvinvointialue": "North Savo",
    "Pohjois-Karjalan hyvinvointialue": "North Karelia",
    "Keski-Suomen hyvinvointialue": "Central Finland",
    "Etelä-Pohjanmaan hyvinvointialue": "South Ostrobothnia",
    "Pohjanmaan hyvinvointialue": "Ostrobothnia",
    "Keski-Pohjanmaan hyvinvointialue": "Central Ostrobothnia",
    "Pohjois-Pohjanmaan hyvinvointialue": "North Ostrobothnia",
    "Kainuun hyvinvointialue": "Kainuu",
    "Lapin hyvinvointialue": "Lapland",
}

SCREENING = {"breast": 3621, "colorectal": 6103, "cervical": 3620}
CONTEXT = {
    "low_income_rate_percent": 3099,
    "education_level_index": 180,
    "other_native_language_per_1000": 187,
    "primary_care_doctor_wait_over_7_days_percent": 6411,
}


def get(path):
    # The API rejects Python's default user agent.
    req = urllib.request.Request(f"{API}/{path}", headers={"User-Agent": "curl/8.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def fetch(indicator, years, genders=("total",)):
    q = "&".join([f"indicator={indicator}"] + [f"years={y}" for y in years]
                 + [f"genders={g}" for g in genders])
    out = {}
    for x in get(f"json?{q}"):
        name = REGION_NAMES.get(x["region"])
        if name in REGION_EN and x.get("value") is not None:
            out[(REGION_EN[name], x["year"], x["gender"])] = (x["value"], x.get("absValue"))
    return out


def write(name, header, rows):
    with open(HERE / name, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"{name}: {len(rows)} rows")


def order(regions):
    return sorted(regions, key=lambda r: (r != "Finland", r))


REGION_NAMES = {x["id"]: x["title"]["fi"] for x in get("regions")
                if x["category"] in ("HYVINVOINTIALUE", "MAA")}


def main():
    # Colorectal: total, male and female. attended_n is the Sotkanet absolute value.
    d = fetch(SCREENING["colorectal"], [YEAR], ("total", "male", "female"))
    rows = [[YEAR, r, sex, d[(r, YEAR, sex)][1], d[(r, YEAR, sex)][0], META.format(6103)]
            for r in order({k[0] for k in d}) for sex in ("total", "male", "female")
            if (r, YEAR, sex) in d]
    write("colorectal_screening_by_region_2024.csv",
          ["year", "region", "sex", "attended_n", "participation_percent", "source_url"], rows)

    d = fetch(SCREENING["cervical"], [YEAR])
    rows = [[YEAR, r, d[(r, YEAR, "total")][1], d[(r, YEAR, "total")][0], META.format(3620)]
            for r in order({k[0] for k in d})]
    write("cervical_screening_by_region_2024.csv",
          ["year", "region", "attended_n", "participation_percent", "source_url"], rows)

    rows = []
    for programme, ind in SCREENING.items():
        d = fetch(ind, TREND_YEARS)
        rows += [[y, programme, d[("Finland", y, "total")][0], META.format(ind)]
                 for y in TREND_YEARS if ("Finland", y, "total") in d]
    write("screening_participation_national_trend.csv",
          ["year", "programme", "participation_percent", "source_url"], rows)

    rows = []
    for indicator, ind in CONTEXT.items():
        d = fetch(ind, [YEAR])
        rows += [[YEAR, r, indicator, d[(r, YEAR, "total")][0], META.format(ind)]
                 for r in order({k[0] for k in d})]
    write("region_context_2024.csv", ["year", "region", "indicator", "value", "source_url"], rows)


if __name__ == "__main__":
    main()
