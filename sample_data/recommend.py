"""Rule engine: gap -> pathway stage -> measure from the national roadmap.

Reads the synthetic CSVs and thresholds.json, writes
  synthetic_recommendations.csv   one row per detected gap
  synthetic_sensitivity.csv       how many decisions change when a threshold moves
  dashboard-data.js               the same content for equal-care-decision-dashboard.html

Run:  python3 sample_data/recommend.py
"""
import copy
import csv
import json
import statistics
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent

# Measures are taken from the Implementation Roadmap 2026-2031 (page in the PDF).
MEASURES = {
    "1.1.1": ("Co-design screening and prevention services with residents", "Roadmap p.26"),
    "1.2.3": ("Named care coordinator model", "Roadmap p.32"),
    "1.3.1": ("Targeted, community-based communication for language groups", "Roadmap p.33"),
    "1.3.2": ("National symptom-awareness communication", "Roadmap p.34"),
    "2.4.1": ("Screening quality manuals in procurement and steering", "Roadmap p.47"),
    "2.5.1": ("More physician capacity in primary care (personal doctor model)", "Roadmap p.51"),
    "2.5.2": ("Standardised referral criteria in national care pathways", "Roadmap p.52"),
    "3.1.2": ("Regional care pathways with agreed access times", "Roadmap p.56"),
    "3.5.1": ("Workforce sufficiency strategy for diagnostics and treatment", "Roadmap p.70"),
    "4.1.1": ("Uniform structured recording of cancer data", "Roadmap p.77"),
    "p13":   ("Deliver care closer to home: remote services, shared care, home hospital",
              "Roadmap p.13 (text, not a numbered measure)"),
}


def num(x):
    return None if x in ("", None) else float(x)


def load():
    def read(name):
        with open(HERE / name, encoding="utf-8") as f:
            return list(csv.DictReader(f))

    regions = {r["region"]: {k: (v if k == "region" else float(v)) for k, v in r.items()}
               for r in read("synthetic_regions.csv")}
    pathway = read("synthetic_pathway.csv")
    edu_gap = {}
    for r in read("synthetic_ses_gradient.csv"):
        if r["screening_participation"] != "":
            edu_gap.setdefault((r["region"], r["cancer"]), {})[r["education"]] = float(
                r["screening_participation"])
    edu_gap = {k: v["high"] - v["low"] for k, v in edu_gap.items()}
    return regions, pathway, edu_gap


def national_medians(pathway):
    cols = ["share_stage_I_II", "days_first_contact_to_referral", "days_referral_to_diagnosis"]
    out = {}
    for cancer in {r["cancer"] for r in pathway}:
        for col in cols:
            vals = [num(r[col]) for r in pathway if r["cancer"] == cancer and num(r[col]) is not None]
            out[(cancer, col)] = statistics.median(vals)
    return out


def evaluate(regions, pathway, edu_gap, th):
    """Return one finding per detected gap."""
    t = {k: v["value"] for k, v in th.items() if not k.startswith("_")}
    med = national_medians(pathway)
    findings = []

    def add(row, stage, indicator, value, benchmark, severity, measure, decided_by, basis):
        title, source = MEASURES[measure]
        findings.append(dict(
            region=row["region"], cancer=row["cancer"], pathway_stage=stage,
            indicator=indicator, value=value, benchmark=benchmark,
            severity="" if severity is None else round(severity, 3),
            priority="" if severity is None else round(severity * float(row["new_cases_per_year"])),
            measure=measure, measure_title=title, measure_source=source,
            decided_by=decided_by, threshold_basis=basis,
            success_kpi=f"{indicator} reaches {benchmark}",
        ))

    for row in pathway:
        reg = regions[row["region"]]
        cancer = row["cancer"]

        # 1 Early detection: screening participation (documented 80 % target)
        screen = num(row["screening_participation"])
        if screen is not None and screen < t["screening_target"]:
            gap = edu_gap.get((row["region"], cancer), 0)
            if reg["share_foreign_language"] >= t["foreign_language_share_high"]:
                m, why = "1.3.1", f"foreign-language share {reg['share_foreign_language']:.0%}"
            elif gap >= t["education_gap_pp"]:
                m, why = "1.1.1", f"education gap {gap * 100:.0f} pp"
            else:
                m, why = "2.4.1", "no language or education driver"
            add(row, "1 Early detection", "screening_participation", screen, t["screening_target"],
                (t["screening_target"] - screen) / t["screening_target"], m, why, "documented")

        # 2 Stage at diagnosis: outcome of everything before the diagnosis
        early = num(row["share_stage_I_II"])
        bench = med[(cancer, "share_stage_I_II")]
        if bench - early >= t["early_stage_gap_pp"]:
            if reg["primary_care_wait_days"] >= t["primary_care_wait_high_days"]:
                m, why = "2.5.1", f"primary care wait {reg['primary_care_wait_days']:.0f} d"
            else:
                m, why = "1.3.2", "primary care wait not elevated"
            add(row, "2 Stage at diagnosis", "share_stage_I_II", early, round(bench, 3),
                (bench - early) / bench, m, why, "placeholder")

        # 3 Primary care -> referral, 4 referral -> diagnosis
        for stage, col, branch in (
            ("3 Referral", "days_first_contact_to_referral", "primary_care"),
            ("4 Diagnosis", "days_referral_to_diagnosis", "vacancy"),
        ):
            value = num(row[col])
            bench = med[(cancer, col)]
            if value is None:
                add(row, stage, col, "missing", "reported", None, "4.1.1",
                    "indicator not reported", "n/a")
                continue
            if value / bench < t["delay_ratio"]:
                continue
            if branch == "primary_care":
                if reg["primary_care_wait_days"] >= t["primary_care_wait_high_days"]:
                    m, why = "2.5.1", f"primary care wait {reg['primary_care_wait_days']:.0f} d"
                else:
                    m, why = "2.5.2", "primary care wait not elevated"
            else:
                if reg["specialist_vacancy_rate"] >= t["vacancy_high"]:
                    m, why = "3.5.1", f"vacancy rate {reg['specialist_vacancy_rate']:.0%}"
                else:
                    m, why = "3.1.2", "vacancy rate not elevated"
            add(row, stage, col, value, round(bench, 1), value / bench - 1, m, why, "placeholder")

        # 5 Treatment start (Goal 3 indicator)
        within = num(row["share_treated_within_target"])
        if within < t["treatment_within_target_min"]:
            if reg["median_distance_to_radiotherapy_km"] >= t["distance_far_km"]:
                m, why = "p13", f"distance {reg['median_distance_to_radiotherapy_km']:.0f} km"
            elif reg["specialist_vacancy_rate"] >= t["vacancy_high"]:
                m, why = "3.5.1", f"vacancy rate {reg['specialist_vacancy_rate']:.0%}"
            else:
                m, why = "3.1.2", "no distance or workforce driver"
            add(row, "5 Treatment start", "share_treated_within_target", within,
                t["treatment_within_target_min"],
                (t["treatment_within_target_min"] - within) / t["treatment_within_target_min"],
                m, why, "placeholder")

    return findings


def key(f):
    return (f["region"], f["cancer"], f["pathway_stage"])


def sensitivity(regions, pathway, edu_gap, th, base):
    """Move one threshold at a time and count decisions that appear, vanish or switch measure."""
    variants = {
        "screening_target": (0.75, 0.85),
        "distance_far_km": (50, 150),
        "treatment_within_target_min": (0.70, 0.90),
        "delay_ratio": (1.15, 1.35),
        "early_stage_gap_pp": (0.03, 0.07),
        "foreign_language_share_high": (0.05, 0.12),
        "education_gap_pp": (0.06, 0.10),
        "primary_care_wait_high_days": (12, 18),
        "vacancy_high": (0.09, 0.15),
    }
    base_map = {key(f): f["measure"] for f in base}
    rows = []
    for name, values in variants.items():
        for v in values:
            alt = copy.deepcopy(th)
            alt[name]["value"] = v
            alt_map = {key(f): f["measure"] for f in evaluate(regions, pathway, edu_gap, alt)}
            rows.append(dict(
                threshold=name, status=th[name]["status"],
                base_value=th[name]["value"], tested_value=v,
                gaps_added=len(alt_map.keys() - base_map.keys()),
                gaps_removed=len(base_map.keys() - alt_map.keys()),
                measure_switched=sum(1 for k in alt_map.keys() & base_map.keys()
                                     if alt_map[k] != base_map[k]),
            ))
    for r in rows:
        r["decisions_changed"] = r["gaps_added"] + r["gaps_removed"] + r["measure_switched"]
    return rows


def write(name, rows):
    with open(HERE / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main():
    regions, pathway, edu_gap = load()
    th = json.loads((HERE / "thresholds.json").read_text(encoding="utf-8"))
    findings = evaluate(regions, pathway, edu_gap, th)
    findings.sort(key=lambda f: -(f["priority"] or 0))
    write("synthetic_recommendations.csv", findings)
    sens = sensitivity(regions, pathway, edu_gap, th, findings)
    write("synthetic_sensitivity.csv", sens)

    # Same content for the dashboard page. A .js file loads from file:// without a server.
    payload = dict(
        regions=list(regions.values()), pathway=pathway, findings=findings,
        sensitivity=sens, measures={k: dict(title=v[0], source=v[1]) for k, v in MEASURES.items()},
        thresholds={k: v for k, v in th.items() if not k.startswith("_")},
    )
    (HERE / "dashboard-data.js").write_text(
        "window.EQUAL_CARE_DATA = " + json.dumps(payload, ensure_ascii=False, indent=1) + ";\n",
        encoding="utf-8")

    print(f"{len(findings)} gaps in {len(pathway)} region x cancer cells\n")
    print("By pathway stage:")
    for k, v in sorted(Counter(f["pathway_stage"] for f in findings).items()):
        print(f"  {k:22} {v}")
    print("\nBy measure:")
    for k, v in Counter(f["measure"] for f in findings).most_common():
        print(f"  {k:6} {v:3}  {MEASURES[k][0]}")
    print("\nTop 8 by priority (severity x new cases):")
    for f in findings[:8]:
        print(f"  {f['priority']:>4}  {f['region']:18} {f['cancer']:10} {f['pathway_stage']:20} "
              f"-> {f['measure']:5} ({f['decided_by']})")
    print("\nSensitivity (one threshold moved at a time):")
    print(f"  {'threshold':30} {'base':>6} {'test':>6} {'added':>6} {'removed':>8} {'switched':>9} {'total':>6}")
    for r in sens:
        print(f"  {r['threshold']:30} {r['base_value']:>6} {r['tested_value']:>6} {r['gaps_added']:>6} "
              f"{r['gaps_removed']:>8} {r['measure_switched']:>9} {r['decisions_changed']:>6}")


if __name__ == "__main__":
    main()
