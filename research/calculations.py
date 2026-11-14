"""Do measures against unequal screening participation pay off for the health system?

    python3 research/calculations.py

The calculation follows one chain for each screening programme:

    measure -> more people from the disadvantaged group take part
            -> more findings (cancers, and for colorectal screening pre-stages of cancer)
            -> less treatment of advanced disease later
            -> saving for the health system, compared with what the measure and the
               extra screening cost today

Three kinds of numbers go in, and they are kept apart on purpose:

    measured     counts for 2024 from the Finnish Cancer Registry
                 (research/screening_yield_2024.csv)
    published    costs and effects from studies, each with its source
    assumption   values nobody has published for Finland; marked as such
                 (both in research/assumptions.csv, column "basis")

Every value in assumptions.csv has a pessimistic, a central and an optimistic version.
"Pessimistic" always means: worse for the financial result. The calculation is run
three times, once with each set, so the result is a range and not a single number.

What is counted: costs and savings of the health system. Lost working time, costs to
patients and families, and the value of longer life are NOT counted as money; the
number of cancers found earlier or prevented is reported next to the euros instead.

Outputs: research/calculation_results.csv and research/calculation_results.md
Only the Python standard library is used.
"""
import csv
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCENARIOS = ("pessimistic", "central", "optimistic")

# One line per measure: which gap it addresses and between which two groups.
MEASURES = [
    {"measure_id": "1.1.1", "grouping": "education", "worse": "primary_or_unknown", "better": "tertiary",
     "label": "People with primary or unknown education"},
    {"measure_id": "1.3.1", "grouping": "native_language", "worse": "other_or_missing", "better": "domestic",
     "label": "People with a native language other than Finnish or Swedish"},
]
PROGRAMMES = ("colorectal", "breast", "cervical")


def read_inputs():
    counts = defaultdict(dict)                    # (programme, grouping, group) -> {measure: count}
    with open(HERE / "screening_yield_2024.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            counts[(row["programme"], row["grouping"], row["group"])][row["measure"]] = int(row["count"])
    with open(HERE / "assumptions.csv", encoding="utf-8") as f:
        assumptions = {row["key"]: row for row in csv.DictReader(f)}
    with open(ROOT / "pipeline/reference/measures.csv", encoding="utf-8") as f:
        measures = {row["measure_id"]: row for row in csv.DictReader(f)}
    return counts, assumptions, measures


def one_programme(programme, measure, counts, p):
    """Effects of one measure in one programme for one screening year.

    p holds the assumption values of the scenario being calculated.
    """
    worse = counts[(programme, measure["grouping"], measure["worse"])]
    better = counts[(programme, measure["grouping"], measure["better"])]
    rate_worse = 100 * worse["attended"] / worse["invited"]
    rate_better = 100 * better["attended"] / better["invited"]
    gap = rate_better - rate_worse
    # A measure can at most close the gap; it cannot lift the group above the other one.
    gain = min(p[f"gain_pp_{programme}"], gap)
    extra_people = worse["invited"] * gain / 100

    # A saving that arrives some years later is worth less today (discounting), but
    # treatment also gets more expensive every year (cost growth). Both are applied.
    def value_today(years):
        return ((1 + p["cost_growth_per_case"]) / (1 + p["discount_rate"])) ** years

    r = {"programme": programme, "invited": worse["invited"], "participation_now": rate_worse,
         "participation_other_group": rate_better, "gap_pp": gap, "gain_pp": gain,
         "extra_participants": extra_people, "cancers_found_earlier": 0.0, "cancers_prevented": 0.0,
         "precancers_found": 0.0, "cost_screening": None, "cost_followup": None,
         "cost_overdiagnosis": None, "saving": None}

    if programme == "colorectal":
        national = counts[("colorectal", "all", "all")]
        positives = extra_people * worse["test_positive"] / worse["attended"]
        colonoscopies = positives * worse["colonoscopy_attended"] / worse["test_positive"]
        # Findings per colonoscopy are only published for the whole country.
        cancers = colonoscopies * national["findings_cancer"] / national["colonoscopy_attended"]
        adenomas = colonoscopies * national["findings_advanced_adenoma"] / national["colonoscopy_attended"]
        prevented = adenomas * p["colorectal_adenoma_progression_10y"]

        share = p["colorectal_direct_cost_share"]
        periods = p["colorectal_metastatic_periods"]
        # What treating metastatic disease costs the health system, beyond the follow-up
        # the same patient would have had in remission during that time.
        metastatic_course = share * (periods * (p["colorectal_cost_metastatic_6m"] - p["colorectal_cost_remission_6m"])
                                     + p["colorectal_cost_palliative_6m"])
        # A cancer that never develops saves the whole treatment: first six months, one
        # year of rehabilitation, 3.5 years of follow-up, and for some the metastatic course.
        whole_case = (share * (p["colorectal_cost_primary_6m"] + 2 * p["colorectal_cost_rehabilitation_6m"]
                               + 7 * p["colorectal_cost_remission_6m"])
                      + p["colorectal_stage4_share_unscreened"] * metastatic_course)

        r.update(cancers_found_earlier=cancers, precancers_found=adenomas, cancers_prevented=prevented,
                 cost_screening=extra_people * p["colorectal_fit_cost_per_participant"],
                 cost_followup=colonoscopies * p["colorectal_colonoscopy_cost"],
                 cost_overdiagnosis=0.0,
                 saving=(cancers * p["colorectal_stage4_reduction"] * metastatic_course
                         * value_today(p["years_until_stage4_cost_colorectal"])
                         + prevented * whole_case * value_today(p["years_until_prevented_cancer"])))

    elif programme == "breast":
        cancers = extra_people * worse["malignant"] / worse["attended"]
        overdiagnosed = cancers * p["breast_overdiagnosis_share"]
        metastatic_course = p["breast_metastatic_periods"] * (p["breast_cost_metastatic_6m"]
                                                              - p["breast_cost_remission_6m"])
        treatment_of_one_case = (p["breast_cost_primary_6m"] + 2 * p["breast_cost_rehabilitation_6m"]
                                 + 7 * p["breast_cost_remission_6m"])
        r.update(cancers_found_earlier=cancers - overdiagnosed,
                 # The programme cost per screened woman already contains the further examinations.
                 cost_screening=extra_people * p["breast_screening_cost_per_attendee"],
                 cost_followup=0.0,
                 cost_overdiagnosis=overdiagnosed * treatment_of_one_case,
                 saving=((cancers - overdiagnosed) * p["breast_distant_recurrence_reduction"] * metastatic_course
                         * value_today(p["years_until_metastatic_cost_breast"])))

    else:   # cervical: the findings can be counted, but no Finnish cost per case was found
        r.update(precancers_found=extra_people * worse["hsil_or_worse"] / worse["attended"])
    return r


def calculate():
    counts, assumptions, measures = read_inputs()
    rows = []
    for scenario in SCENARIOS:
        p = {key: float(a[scenario]) for key, a in assumptions.items()}
        years = p["programme_years"]
        for measure in MEASURES:
            budget = float(measures[measure["measure_id"]]["cost_eur"])
            parts = [one_programme(prog, measure, counts, p) for prog in PROGRAMMES]
            costed = [x for x in parts if x["saving"] is not None]
            saving = sum(x["saving"] for x in costed)
            extra_cost = sum(x["cost_screening"] + x["cost_followup"] + x["cost_overdiagnosis"] for x in costed)
            before_measure = saving - extra_cost            # per screening year
            for x in parts:
                rows.append({"scenario": scenario, "measure_id": measure["measure_id"],
                             "group": measure["label"], "row": x["programme"], **_rounded(x)})
            rows.append({
                "scenario": scenario, "measure_id": measure["measure_id"], "group": measure["label"],
                "row": "TOTAL (breast and colorectal, per year)",
                "extra_participants": round(sum(x["extra_participants"] for x in parts)),
                "cancers_found_earlier": round(sum(x["cancers_found_earlier"] for x in parts), 1),
                "cancers_prevented": round(sum(x["cancers_prevented"] for x in parts), 1),
                "precancers_found": round(sum(x["precancers_found"] for x in parts), 1),
                "cost_screening": round(sum(x["cost_screening"] for x in costed)),
                "cost_followup": round(sum(x["cost_followup"] for x in costed)),
                "cost_overdiagnosis": round(sum(x["cost_overdiagnosis"] for x in costed)),
                "saving": round(saving),
                "measure_cost_per_year": round(budget / years),
                "net_per_year": round(before_measure - budget / years),
                "net_over_programme": round(before_measure * years - budget),
                "saving_per_euro_spent": round(saving / (extra_cost + budget / years), 2),
                # The largest budget the measure could have and still pay for itself.
                "break_even_budget": round(max(before_measure, 0) * years),
                "roadmap_budget": round(budget)})
    return rows, assumptions


def sensitivity(measure):
    """Change one assumption at a time and see how far the six-year net result moves.

    All other values stay central. The result is sorted so that the assumption with
    the largest influence comes first.
    """
    counts, assumptions, measures = read_inputs()
    central = {key: float(a["central"]) for key, a in assumptions.items()}
    budget = float(measures[measure["measure_id"]]["cost_eur"])

    def net(p):
        costed = [x for x in (one_programme(prog, measure, counts, p) for prog in PROGRAMMES)
                  if x["saving"] is not None]
        per_year = sum(x["saving"] - x["cost_screening"] - x["cost_followup"] - x["cost_overdiagnosis"]
                       for x in costed)
        return per_year * p["programme_years"] - budget

    out = []
    for key, a in assumptions.items():
        if a["pessimistic"] == a["optimistic"]:
            continue
        low = net({**central, key: float(a["pessimistic"])})
        high = net({**central, key: float(a["optimistic"])})
        if low != high:
            out.append((key, a["basis"], round(low), round(high)))
    return sorted(out, key=lambda item: abs(item[3] - item[2]), reverse=True), round(net(central))


def _rounded(x):
    money = ("cost_screening", "cost_followup", "cost_overdiagnosis", "saving")
    out = {"invited": x["invited"], "participation_now": round(x["participation_now"], 1),
           "participation_other_group": round(x["participation_other_group"], 1),
           "gap_pp": round(x["gap_pp"], 1), "gain_pp": round(x["gain_pp"], 1),
           "extra_participants": round(x["extra_participants"]),
           "cancers_found_earlier": round(x["cancers_found_earlier"], 1),
           "cancers_prevented": round(x["cancers_prevented"], 1),
           "precancers_found": round(x["precancers_found"], 1)}
    out.update({k: ("not calculated" if x[k] is None else round(x[k])) for k in money})
    return out


COLUMNS = ["scenario", "measure_id", "group", "row", "invited", "participation_now", "participation_other_group",
           "gap_pp", "gain_pp", "extra_participants", "cancers_found_earlier", "cancers_prevented",
           "precancers_found", "cost_screening", "cost_followup", "cost_overdiagnosis", "saving",
           "measure_cost_per_year", "net_per_year", "net_over_programme", "saving_per_euro_spent",
           "break_even_budget", "roadmap_budget"]


def eur(value):
    return "not calculated" if value == "not calculated" else f"{value:,.0f} €".replace(",", " ")


def write_report(rows, assumptions):
    get = lambda scenario, measure, row: next(
        r for r in rows if r["scenario"] == scenario and r["measure_id"] == measure and r["row"].startswith(row))
    a = {k: v for k, v in assumptions.items()}
    cost_now = float(a["national_cancer_care_cost_2024"]["central"])
    cost_2035 = float(a["national_cancer_care_cost_2035"]["central"])
    lines = [
        "# Do measures against unequal screening pay off for the health system?",
        "",
        "Written by `research/calculations.py`. Do not edit by hand; change `research/assumptions.csv` and run the script again.",
        "",
        "## The question",
        "",
        f"Cancer care cost Finland about {cost_now / 1e9:.1f} billion euros in 2024. The National Cancer Strategy "
        f"expects {cost_2035 / 1e9:.1f} billion a year by 2035 if nothing specific is done. The two roadmap measures "
        "against unequal screening participation have budgets of 1.5 million and 0.4 million euros for 2026-2031. "
        "This file estimates what the health system gets back for that money.",
        "",
        "## Result per measure",
        "",
        "All amounts are for the health system. Each column is one set of assumptions. The pessimistic column sets "
        "every uncertain value to its unfavourable end at the same time, the optimistic column every value to its "
        "favourable end. Both extremes are unlikely; they mark the range.",
        "",
    ]
    for m in MEASURES:
        mid = m["measure_id"]
        lines += [f"### Measure {mid}: {m['label']}", "",
                  "| | Pessimistic | Central | Optimistic |", "| --- | ---: | ---: | ---: |"]
        total = {s: get(s, mid, "TOTAL") for s in SCENARIOS}

        def line(title, key, money=True):
            cells = [eur(total[s][key]) if money else f"{total[s][key]:,}".replace(",", " ") for s in SCENARIOS]
            lines.append(f"| {title} | " + " | ".join(cells) + " |")
        line("Extra participants per year (all three programmes)", "extra_participants", money=False)
        line("Cancers found earlier per year", "cancers_found_earlier", money=False)
        line("Colorectal cancers prevented per year", "cancers_prevented", money=False)
        line("Extra screening cost per year", "cost_screening")
        line("Extra follow-up examinations per year", "cost_followup")
        line("Treatment of overdiagnosed breast cancers per year", "cost_overdiagnosis")
        line("Saving on later treatment per year, in today's money", "saving")
        line("Cost of the measure per year (roadmap budget / 6)", "measure_cost_per_year")
        line("**Net result per year**", "net_per_year")
        line("**Net result over 2026-2031**", "net_over_programme")
        line("Largest budget at which the measure still pays for itself", "break_even_budget")
        lines.append("| Saving per euro spent | " + " | ".join(
            f"{total[s]['saving_per_euro_spent']:.2f} €" for s in SCENARIOS) + " |")
        lines += ["", "By programme, central assumptions, per year:", "",
                  "| Programme | Gap (points) | Gain used | Extra participants | Extra cost | Saving |",
                  "| --- | ---: | ---: | ---: | ---: | ---: |"]
        for prog in PROGRAMMES:
            x = get("central", mid, prog)
            cost = ("not calculated" if x["saving"] == "not calculated"
                    else x["cost_screening"] + x["cost_followup"] + x["cost_overdiagnosis"])
            lines.append(f"| {prog.capitalize()} | {x['gap_pp']} | {x['gain_pp']} | "
                         f"{x['extra_participants']:,} | {eur(cost)} | {eur(x['saving'])} |".replace(",", " "))
        lines.append("")

    c1, c2 = get("central", "1.1.1", "TOTAL"), get("central", "1.3.1", "TOTAL")
    col1, br1 = get("central", "1.1.1", "colorectal"), get("central", "1.1.1", "breast")
    lines += [
        "## How to read this",
        "",
        f"- **The money comes back through colorectal screening.** Removing pre-stages of cancer prevents cancers "
        f"altogether, and each prevented case saves its whole treatment. With central assumptions the education "
        f"measure saves {eur(col1['saving'])} a year there against "
        f"{eur(col1['cost_screening'] + col1['cost_followup'])} of extra screening and colonoscopies.",
        f"- **Breast screening does not pay for itself in euros.** The extra screening and the treatment of "
        f"overdiagnosed cancers cost more ({eur(br1['cost_screening'] + br1['cost_overdiagnosis'])} a year) than is "
        f"saved on metastatic treatment ({eur(br1['saving'])}). Its case is fewer deaths, not lower spending.",
        "- **Cervical screening is counted in people, not in euros.** No Finnish cost per case was found, so its "
        "extra costs and its savings are both missing from the totals.",
        f"- **The budgets are small against the stakes.** Both measures together cost "
        f"{eur(c1['roadmap_budget'] + c2['roadmap_budget'])} over six years, which is "
        f"{100 * (c1['roadmap_budget'] + c2['roadmap_budget']) / cost_now:.2f} % of one year of cancer care.",
        "- **Do not add the two measures together.** Some people belong to both groups, so the effects overlap.",
        "",
        "## Which assumption matters most",
        "",
        "Measure 1.1.1, net result over 2026-2031 when one value is changed and all others stay central "
        f"(central result: {eur(sensitivity(MEASURES[0])[1])}).",
        "",
        "| Value changed | Basis | At its pessimistic end | At its optimistic end |",
        "| --- | --- | ---: | ---: |",
        *[f"| `{key}` | {basis} | {eur(low)} | {eur(high)} |" for key, basis, low, high in sensitivity(MEASURES[0])[0]],
        "",
        "## What this calculation can not show",
        "",
        "- **Whether the measures reach the assumed gain.** The gains come from reviews of mostly US studies. "
        "Whether a budget of this size produces them across Finland is not known. The row \"largest budget at which "
        "the measure still pays for itself\" shows how much room there is.",
        "- **Costs that are estimates.** The cost of a stool test and of a colonoscopy are rough estimates, because "
        "no Finnish unit cost was found. They are marked `assumption` in `assumptions.csv`.",
        "- **Old cost studies.** Treatment costs per patient come from Finnish studies published in 2015 and 2019. "
        "New medicines have probably made advanced disease more expensive since, which would raise the savings.",
        "- **Who is found by screening.** People who start taking part after a measure may differ from those who "
        "already take part. Findings per examination are taken from the group as it is today.",
        "- **Savings arrive later than costs.** Screening is paid in the same year; the savings come three to five "
        "years later and are converted to today's money.",
        "- **Health is not priced.** Longer life, working years and costs to families are left out.",
        "",
        "## Sources of the numbers",
        "",
        "| Value | Pessimistic | Central | Optimistic | Basis | Source |",
        "| --- | ---: | ---: | ---: | --- | --- |",
    ]
    for key, v in assumptions.items():
        source = f"[link]({v['source']})" if v["source"] else "-"
        lines.append(f"| `{key}` | {v['pessimistic']} | {v['central']} | {v['optimistic']} | {v['basis']} | {source} |")
    # The complete result table, so that the report holds every figure the CSV holds.
    shown = [c for c in COLUMNS if c != "group"]
    lines += ["", "## All results", "",
              "Every row of `research/calculation_results.csv`. Amounts in euros per screening year unless the "
              "column says otherwise. 1.1.1 is the education measure, 1.3.1 the native-language measure.", "",
              "| " + " | ".join(shown) + " |", "| " + " | ".join("---" for _ in shown) + " |"]
    for r in rows:
        lines.append("| " + " | ".join(str(r.get(c, "")) for c in shown) + " |")
    lines += ["", "Counts of invited people, participants and findings: Finnish Cancer Registry, screening statistics "
              "2024, in `research/screening_yield_2024.csv`. Measure budgets: `pipeline/reference/measures.csv`.", ""]
    (HERE / "calculation_results.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    rows, assumptions = calculate()
    with open(HERE / "calculation_results.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, restval="")
        writer.writeheader()
        writer.writerows(rows)
    write_report(rows, assumptions)
    for r in rows:
        if r["row"].startswith("TOTAL"):
            print(f"{r['scenario']:11} measure {r['measure_id']}: saving {r['saving']:>10,} | "
                  f"extra cost {r['cost_screening'] + r['cost_followup'] + r['cost_overdiagnosis']:>9,} | "
                  f"measure {r['measure_cost_per_year']:>7,} | net per year {r['net_per_year']:>10,} | "
                  f"per euro {r['saving_per_euro_spent']}")
    print("Written: research/calculation_results.csv and research/calculation_results.md")


if __name__ == "__main__":
    main()
