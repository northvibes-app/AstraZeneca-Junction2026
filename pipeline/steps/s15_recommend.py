"""Step 15: RECOMMEND

Link each gap to a measure from the national implementation roadmap.

The rules are deliberately simple and written out, so that anyone can check why a
measure was proposed. Every proposal is something to evaluate, not a proven remedy:
the data shows where a gap is, not what causes it.
"""
from collections import defaultdict

SCREENING = {"screening_participation_breast": "breast", "screening_participation_colorectal": "colorectal",
             "screening_participation_cervical": "cervical"}


def recommend(ctx):
    """Create national and regional recommendations.

    National, from gaps measured directly between groups (evidence A, latest full year):
        education gap in screening participation   -> 1.1.1
        language gap in screening participation    -> 1.3.1
        gap between men and women                  -> 2.4.1 (closest match)
        gap in follow-up attendance                -> 1.2.3 (closest match)
        pathway stages without any open data       -> 3.1.2
    Regional, for each region that is clearly below the 80 % screening target:
        region in the disadvantaged third for language   -> 1.3.1
        region in the disadvantaged third for education  -> 1.1.1
        neither                                          -> 2.4.1
    and independently, slow access to primary care       -> 2.5.1

    "closest match" means the roadmap has no measure aimed exactly at this gap.
    """
    step, ref, out = "15 recommend", ctx.ref, []
    measures = {m["measure_id"]: m for m in ref.measures}

    def add(scope, region_code, region, measure_id, fit, trigger, evidence, gap=None):
        m = measures[measure_id]
        out.append({"scope": scope, "region_code": region_code, "region": region,
                    "measure_id": measure_id, "measure": m["title"], "fit": fit,
                    "trigger": trigger, "evidence_type": evidence,
                    "pathway_stage": m["pathway_stage"], "cost_eur": m["cost_eur"],
                    "cost_note": m["cost_note"], "success_kpi": m["kpi"],
                    "people_in_worse_group": gap["people_in_worse_group"] if gap else "",
                    "potential_additional": gap["potential_additional"] if gap else "",
                    "source": f"Implementation Roadmap 2026-2031, p. {m['roadmap_page']}"})
        ctx.count(step, f"{scope} recommendations")

    # --- national ----------------------------------------------------------------
    observed = [g for g in ctx.results["equity_gaps"]
                if g["evidence_type"] == "A" and g["region_code"] == "FI" and g["status"] == "observed"]
    newest = {}
    for g in observed:
        k = (g["indicator_key"], g["factor"])
        if k not in newest or g["year"] > newest[k]["year"]:
            newest[k] = g
    for (key, factor), g in sorted(newest.items()):
        # Only the newest full year counts, and only if its gap is clearly larger than
        # chance (confidence interval above zero). An older year must not stand in for it.
        if g["robust"] != "yes":
            ctx.count(step, "gaps without a recommendation: not clearly above zero")
            continue
        trigger = (f"{g['indicator_name']} {g['year']}: {g['worse_value']} % in the group "
                   f"'{g['worse_group']}' against {g['better_value']} % in '{g['better_group']}', "
                   f"a gap of {g['gap']} points")
        if key in SCREENING and factor == "education":
            add("national", "FI", "Finland", "1.1.1", "direct", trigger, "A", g)
        elif key in SCREENING and factor == "language":
            add("national", "FI", "Finland", "1.3.1", "direct", trigger, "A", g)
        elif key in SCREENING and factor == "sex":
            add("national", "FI", "Finland", "2.4.1", "closest match", trigger, "A", g)
        elif key.startswith("followup_attendance") and factor in ("education", "language"):
            add("national", "FI", "Finland", "1.2.3", "closest match", trigger, "A", g)
    missing = [g["description"].split(". ")[0] for g in ctx.results["data_gaps"]
               if g["gap_type"] == "no_open_data" and g["pathway_stage"] in ("referral", "diagnosis", "treatment_start")]
    if missing:
        add("national", "FI", "Finland", "3.1.2", "direct",
            "No open data exists for: " + "; ".join(missing), "data gap")

    # --- regional ----------------------------------------------------------------
    level_of = ctx.results["level_of"]
    below = defaultdict(list)
    for s in ctx.results["outcome_stats"]:
        if (s["indicator_key"] in SCREENING and s["sex"] == "total" and not s["factor"]
                and s["target_status"] == "below_target" and s["region_code"] != "FI"):
            below[(s["region_code"], s["region_name"])].append(
                f"{SCREENING[s['indicator_key']]} {s['value']} %")
    for (code, name), programmes in sorted(below.items()):
        trigger = "Clearly below the 80 % target in " + ", ".join(sorted(programmes))
        level = lambda factor: level_of.get((factor, code), ("", 0))[0]
        matched = False
        if level("language") == "disadvantaged":
            add("regional", code, name, "1.3.1", "direct",
                trigger + "; in the third of regions with the most other-language speakers", "B")
            matched = True
        if level("education") == "disadvantaged":
            add("regional", code, name, "1.1.1", "direct",
                trigger + "; in the third of regions with the lowest education level", "B")
            matched = True
        if not matched:
            add("regional", code, name, "2.4.1", "direct",
                trigger + "; no language or education disadvantage in the regional data", "B")
    for region in ref.counties:
        code = region["region_code"]
        if level_of.get(("primary_care_access", code), ("", 0))[0] == "disadvantaged":
            add("regional", code, region["name_en"], "2.5.1", "direct",
                "In the third of regions with the longest waits for a non-urgent doctor appointment", "B")
    ctx.results["recommendations"] = out
