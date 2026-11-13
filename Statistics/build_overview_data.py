"""Bundle the CSVs in this folder into overview-data.js for statistics-overview.html.

A .js file loads from file:// without a local server.
Run:  python3 Statistics/build_overview_data.py
"""
import csv
import json
from pathlib import Path

HERE = Path(__file__).parent
FILES = {
    "national": "national_key_statistics.csv",
    "breast": "breast_screening_by_region_2024.csv",
    "colorectal": "colorectal_screening_by_region_2024.csv",
    "cervical": "cervical_screening_by_region_2024.csv",
    "cervical_equity": "cervical_screening_equity_2025_preliminary.csv",
    "trend": "screening_participation_national_trend.csv",
    "context": "region_context_2024.csv",
}


def main():
    data = {}
    for key, name in FILES.items():
        with open(HERE / name, encoding="utf-8") as f:
            data[key] = list(csv.DictReader(f))
    (HERE / "overview-data.js").write_text(
        "window.STATISTICS = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n",
        encoding="utf-8")
    print("overview-data.js:", {k: len(v) for k, v in data.items()})


if __name__ == "__main__":
    main()
