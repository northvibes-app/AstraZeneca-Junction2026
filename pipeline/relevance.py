"""How relevant is each gap for a decision?

Problem factors are not all the same kind of thing, so they are first sorted by role:

    who is affected        level of education, native language, sex, income, employment,
                           the region someone lives in
    what goes worse        screening participation, attendance at the follow-up
                           examination, waiting times, survival
    what stands in the way barriers such as costs, distance and health literacy

A gap is always a pair: one group (who) and one result on the care pathway (what).
Every gap the pipeline knows of is collected here in one list, whatever its source:

    group_gap           a difference measured directly between two population groups
    target_shortfall    a region clearly below the 80 % screening target
    regional_pattern    a pattern between regions or municipalities
    waiting_time        a measured waiting time above the national guidance
    documented_barrier  a barrier described in national strategy texts
    data_gap            something no open data can show

Each gap is described by three facts and handed to the decision tree
(decision_tree/rules.json, subject "gap_relevance"), which returns its level:

    evidence   how the gap is known and whether it is clearly larger than chance
    size       how large the difference is, in percentage points
    reach      how many people are in the disadvantaged group

Each gap is also placed in the challenge: at which of its pathway stages it sits and
which of the three named bottlenecks it belongs to. The thresholds for "large" and
"medium" and the mapping to the challenge are data in rules.json, not code.

"not_measurable" is a level of its own. It does not mean unimportant.
"""
from tree import band, challenge_position, decide

LEVEL_ORDER = ["high", "medium", "low", "uncertain", "not_measurable"]
COLUMNS = ["relevance", "rule_id", "kind", "group_factor", "problem", "region", "challenge_stage",
           "bottleneck", "pathway_stage", "size_points", "size", "reach_people", "reach", "evidence",
           "year", "measures", "reason", "source"]
FACTOR_LABEL = {"education": "level of education", "language": "native language", "sex": "sex",
                "income": "income", "employment": "employment", "smoking": "smoking",
                "primary_care_access": "access to primary care"}
MONITORED_STAGES = ("referral", "diagnosis", "treatment_start")


def _number(value):
    return None if value in (None, "") else float(value)


def build(ctx, tree, gap_measures, region_measures, shortfalls):
    """Return one row per gap, sorted from most to least relevant.

    gap_measures      (indicator_key, factor) -> measures the tree proposed for that group gap
    region_measures   region code -> measures the tree proposed for that region
    shortfalls        rows of regions clearly below the screening target
    """
    res, rows = ctx.results, []
    monitoring = decide(tree, "pathway_data", {"pathway_data_missing": "yes"})[0]
    monitoring_measure = ", ".join(hit["rule"]["measure_id"] for hit in monitoring)

    def add(kind, evidence, stage, size=None, reach=None, uncertain_text="", **fields):
        size_band, reach_band = band(tree, "size_points", size), band(tree, "reach_people", reach)
        fact = {"evidence": evidence, "size": size_band, "reach": reach_band,
                "size_text": fields.pop("size_text", None) or (
                    "size unknown" if size is None else f"{abs(size):.1f} percentage points ({size_band})"),
                "reach_text": ("number of people affected unknown" if reach is None
                               else f"{reach:,.0f} people in the disadvantaged group ({reach_band})"),
                "uncertain_text": uncertain_text}
        fired, _ = decide(tree, "gap_relevance", fact)
        if not fired:
            raise ValueError(f"No relevance rule applies to {kind} with evidence '{evidence}'")
        challenge_stage, bottleneck = challenge_position(tree, stage)
        rows.append({"relevance": fired[0]["rule"]["level"], "rule_id": fired[0]["rule"]["rule_id"],
                     "kind": kind, "challenge_stage": challenge_stage, "bottleneck": bottleneck,
                     "pathway_stage": stage or "prevention",
                     "size_points": "" if size is None else round(abs(size), 1), "size": size_band,
                     "reach_people": "" if reach is None else round(reach), "reach": reach_band,
                     "evidence": evidence, "reason": fired[0]["trigger"], **fields})
        ctx.count("15 recommend", f"gaps with relevance {fired[0]['rule']['level']}")

    # 1. Differences measured directly between groups for all of Finland: newest full year of each.
    #    The same comparison inside single regions rests on small numbers and is left out.
    newest = {}
    for g in res["equity_gaps"]:
        if g["evidence_type"] == "A" and g["status"] == "observed" and g["region_code"] == "FI":
            key = (g["indicator_key"], g["factor"])
            if key not in newest or g["year"] > newest[key]["year"]:
                newest[key] = g
    for key, g in sorted(newest.items()):
        robust = g["robust"] == "yes"
        add("group_gap", "group_measured_robust" if robust else "group_measured_uncertain",
            g["pathway_stage"], size=_number(g["gap"]) if g["unit"] == "percent" else None,
            reach=_number(g["people_in_worse_group"]),
            uncertain_text=("The 95 % interval of the difference includes zero" if g["robust"] == "no"
                            else "The source gives no counts, so no interval can be calculated"),
            group_factor=FACTOR_LABEL.get(g["factor"], g["factor"]),
            problem=(f"{g['indicator_name']}: {g['worse_value']} % in the group '{g['worse_group']}' "
                     f"against {g['better_value']} % in '{g['better_group']}'"),
            region="Finland", year=g["year"], measures=", ".join(gap_measures.get(key, [])),
            source=g["source_url"])

    # 2. Regions clearly below the screening target (the whole 95 % interval is below 80 %).
    for s in shortfalls:
        add("target_shortfall", "target_shortfall", "early_detection",
            size=s["target"] - float(s["value"]), reach=_number(s["denominator"]),
            group_factor="region of residence",
            problem=f"{s['indicator_name']}: {s['value']} % against a target of {s['target']} %",
            region=s["region_name"], year=s["year"],
            measures=", ".join(region_measures.get(s["region_code"], [])), source=s.get("source_url", ""))

    # 3. Patterns between regions or municipalities.
    for g in res["equity_gaps"]:
        if g["evidence_type"] in ("B", "B-municipality"):
            robust = g["robust"] == "yes"
            gap = g["gap_weighted"] if g["gap_weighted"] not in (None, "") else g["gap"]
            add("regional_pattern", "regional_pattern_robust" if robust else "regional_pattern_not_robust",
                g["pathway_stage"], size=_number(gap) if g["unit"] == "percent" else None,
                uncertain_text="A pattern between areas that does not survive the correction for many comparisons",
                group_factor=FACTOR_LABEL.get(g["factor"], g["factor"]),
                problem=(f"{g['indicator_name']}: areas in the disadvantaged third against the advantaged "
                         f"third, rank correlation {g['spearman_rho']}"),
                region=g["region"], year=g["year"], measures="", source=g["source_url"])

    # 4. Waiting times measured above the national guidance (single hospitals or studies).
    for w in res.get("waiting_times", []):
        if w["against_guidance"].startswith("above"):
            add("waiting_time", "single_source_measured", w["pathway_stage"],
                size_text=f"{w['days_max']} days, {w['against_guidance']}",
                uncertain_text="Measured by a single source; no comparison between regions or groups is possible",
                group_factor="not broken down by group",
                problem=f"{w['cancer_type']}: {w['measure'].lower()}, {w['days_max']} days",
                region=w["provider"], year=w["data_period"], measures=monitoring_measure, source=w["source_url"])

    # 5. Barriers described in strategy texts.
    for g in res["equity_gaps"]:
        if g["evidence_type"] == "C":
            add("documented_barrier", "documented_only", g["pathway_stage"],
                group_factor=g["factor"].replace("_", " "), problem=g["note"], region="Finland",
                year="", measures="", source=g["source_url"])

    # 6. What no open data can show.
    for g in res["data_gaps"]:
        if g["gap_type"] == "no_open_data":
            add("data_gap", "no_open_data", g["pathway_stage"],
                group_factor="not available", problem=g["description"].split(". ")[0], region="Finland",
                year="", measures=monitoring_measure if g["pathway_stage"] in MONITORED_STAGES else "",
                source="pipeline/reference/known_data_gaps.csv")

    rows.sort(key=lambda r: (LEVEL_ORDER.index(r["relevance"]), -(r["size_points"] or 0),
                             -(r["reach_people"] or 0)))
    return rows
