"""Checks the three fallback rules of step 9 on a tiny hand-made table.

The real data currently triggers only the first rule (temporal_mean), so the
other two are exercised here.

Run:  python3 pipeline/tests/test_impute.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import Context                                # noqa: E402
from steps import s08_completeness, s09_impute            # noqa: E402


def row(code, year, value):
    return {"indicator_key": "daily_smokers", "indicator_name": "Daily smokers", "kind": "context",
            "pathway_stage": "", "cancer": "", "detail": "", "region_code": code,
            "region_level": "wellbeing_county", "region_name": code, "year": year,
            "period": str(year), "sex": "total", "age_group": "all", "measure": "value",
            "factor": "", "factor_level": "", "value": value, "unit": "percent",
            "numerator": None, "denominator": None, "status": "observed", "flags": "",
            "source": "test", "source_url": "", "source_file": "test", "source_row": 1,
            "also_in": "", "imputation_method": "", "imputation_basis": ""}


def main():
    ctx = Context()
    codes = [c["region_code"] for c in ctx.ref.counties]
    rows = []
    for code in codes:
        if code == "01":
            rows += [row(code, 2020, 10.0), row(code, 2022, 14.0)]      # 2021 missing, both sides known
        elif code == "02":
            rows += [row(code, 2020, 8.0), row(code, 2021, 9.0)]        # 2022 missing, one side known
        elif code == "03":
            rows += [row(code, 2016, 20.0)]                             # 2020-2022 missing, nothing nearby
        else:
            rows += [row(code, y, 12.0) for y in (2020, 2021, 2022)]

    rows = s08_completeness.completeness(ctx, rows)
    rows = s09_impute.impute(ctx, rows)
    got = {(r["region_code"], r["year"]): r for r in rows if r["status"] == "imputed"}

    assert got[("01", 2021)]["imputation_method"] == "temporal_mean"
    assert got[("01", 2021)]["value"] == 12.0                           # (10 + 14) / 2
    assert got[("02", 2022)]["imputation_method"] == "nearest_year"
    assert got[("02", 2022)]["value"] == 9.0
    assert got[("03", 2021)]["imputation_method"] == "regional_mean"
    # 2021: region 01 is missing, 02 has 9.0, the other 19 regions have 12.0
    assert got[("03", 2021)]["value"] == round((9.0 + 19 * 12.0) / 20, 1)
    # A fallback must never be built from another fallback: 03/2018 borrows the
    # observed 2016 value, not the imputed 2017 one.
    assert got[("03", 2018)]["imputation_basis"] == "2016: 20.0"
    # Every imputed row is labelled and carries no counts.
    assert all(r["flags"] == "imputed" and r["numerator"] is None and r["source"] == "Pipeline fallback"
               for r in got.values())
    print(f"ok: {len(got)} fallback values, all three rules behave as specified")


if __name__ == "__main__":
    main()
