"""Step 16: TRENDS

Summarise the two large sources that the equity comparison does not use:
deaths by cancer site (Statistics Finland) and new medicine reimbursement
entitlements (Kela). Together they are 87 % of the cleaned rows.
"""
from collections import defaultdict

from common import ANALYSIS_WINDOW_YEARS, ANALYSIS_YEAR

# Disease-based cancer entitlements in the Kela data (the other codes are single medicines).
ENTITLEMENTS = ("115 ", "116 ", "117 ", "128 ", "130 ")


def trends(ctx):
    """Build two small tables.

    national_trends          deaths per cancer site and year, with the change since the
                             first year of the window. National only; the source has
                             no regional or socioeconomic breakdown.
    treatment_entitlements   new special-reimbursement entitlements per region in the
                             analysis year, per 100,000 inhabitants. An entitlement is
                             granted when cancer medication starts, so this is a rough
                             indicator of people entering treatment, not of need.
    """
    step = "16 trends"
    first_year = ANALYSIS_YEAR - ANALYSIS_WINDOW_YEARS + 1
    deaths = defaultdict(dict)            # site -> {year: deaths}
    started = defaultdict(float)          # (region, entitlement) -> new entitlements
    for r in ctx.results["observations"]:
        if r["indicator_key"] == "cancer_deaths":
            if r["sex"] == "total" and r["age_group"] == "all" and r["year"] >= first_year:
                deaths[r["detail"]][r["year"]] = r["value"]
        elif r["indicator_key"] == "drug_reimbursement_entitlements":
            if (r["measure"] == "alkanut_lkm" and r["year"] == ANALYSIS_YEAR
                    and r["region_level"] == "wellbeing_county" and r["detail"].startswith(ENTITLEMENTS)):
                started[(r["region_code"], r["region_name"], r["detail"])] += r["value"]

    national = []
    for site in sorted(deaths):
        years = sorted(deaths[site])
        base = deaths[site][years[0]]
        for year in years:
            change = round(100 * (deaths[site][year] - base) / base, 1) if base else ""
            national.append({"cancer_site": site, "year": year, "deaths": int(deaths[site][year]),
                             "change_since_" + str(years[0]) + "_percent": change})
    ctx.count(step, "cancer sites with a mortality series", len(deaths))

    population = {p["region_code"]: p["population"] for p in ctx.results["region_profile"]}
    regional = []
    for (code, name, entitlement), count in sorted(started.items()):
        people = population.get(code)
        regional.append({"region_code": code, "region_name": name, "entitlement": entitlement,
                         "year": ANALYSIS_YEAR, "new_entitlements": int(count),
                         "per_100000": round(100000 * count / people, 1) if people else ""})
    ctx.count(step, "region-entitlement figures", len(regional))
    ctx.results["national_trends"] = national
    ctx.results["treatment_entitlements"] = regional
