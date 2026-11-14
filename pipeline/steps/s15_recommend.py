"""Step 15: RECOMMEND

Link each gap to a measure from the national implementation roadmap.

The rules are not written in this file. They are in decision_tree/rules.json and are
evaluated by decision_tree/tree.py, so that the pipeline, the API and a human reviewer
all read the same rules. This step only describes each gap or region as a set of
facts and asks the decision tree which measures apply.

Every proposal is something to evaluate, not a proven remedy: the data shows where a
gap is, not what causes it.
"""
import sys
from collections import defaultdict

from common import ROOT, SCREENING_TARGET

sys.path.insert(0, str(ROOT / "decision_tree"))
from tree import decide, load_rules      # noqa: E402

import relevance                                    # noqa: E402
from pathway_evidence import load_waiting_times     # noqa: E402

SCREENING = {"screening_participation_breast": "breast", "screening_participation_colorectal": "colorectal",
             "screening_participation_cervical": "cervical"}


def indicator_family(indicator_key):
    """The group of indicators a rule can refer to."""
    if indicator_key in SCREENING:
        return "screening_participation"
    if indicator_key.startswith("followup_attendance"):
        return "followup_attendance"
    return "other"


def recommend(ctx):
    """Create national and regional recommendations.

    Facts handed to the decision tree (subjects in rules.json):
        group_gap            each gap measured directly between groups for Finland
                             (evidence A), newest full year only
        pathway_data         whether referral, diagnosis or treatment start lack open data
        region_below_target  each region clearly below the 80 % screening target
        region_access        each region, for access to primary care
    Afterwards every gap the pipeline knows of gets a relevance level (see relevance.py).

    Every question put to the tree is recorded with the rules that were checked, so
    that the reasons can be published (decision_tree/output/decisions.md).
    """
    step, ref, out = "15 recommend", ctx.ref, []
    measures = {m["measure_id"]: m for m in ref.measures}
    tree = load_rules(known_measures=measures)

    decisions = []

    def apply(subject, fact, scope, region_code, region, gap=None, case=""):
        """Ask the decision tree and record one recommendation per rule that applies."""
        fired, path = decide(tree, subject, fact)
        decisions.append({"subject": subject, "case": case or region,
                          "facts": {k: v for k, v in fact.items() if k in tree["subjects"][subject]["fields"]},
                          "path": path, "measures": [hit["rule"]["measure_id"] for hit in fired]})
        for hit in fired:
            rule, m = hit["rule"], measures[hit["rule"]["measure_id"]]
            out.append({"scope": scope, "region_code": region_code, "region": region,
                        "measure_id": rule["measure_id"], "measure": m["title"], "fit": rule["fit"],
                        "trigger": hit["trigger"], "evidence_type": rule["evidence_type"],
                        "pathway_stage": m["pathway_stage"], "cost_eur": m["cost_eur"],
                        "cost_note": m["cost_note"], "success_kpi": m["kpi"],
                        "people_in_worse_group": gap["people_in_worse_group"] if gap else "",
                        "potential_additional": gap["potential_additional"] if gap else "",
                        "source": f"Implementation Roadmap 2026-2031, p. {m['roadmap_page']}",
                        "rule_id": rule["rule_id"], "rule_version": rule["version"]})
            ctx.count(step, f"{scope} recommendations")
        return fired

    # --- national ----------------------------------------------------------------
    observed = [g for g in ctx.results["equity_gaps"]
                if g["evidence_type"] == "A" and g["region_code"] == "FI" and g["status"] == "observed"]
    newest, gap_measures = {}, {}
    for g in observed:
        k = (g["indicator_key"], g["factor"])
        if k not in newest or g["year"] > newest[k]["year"]:
            newest[k] = g
    for (key, factor), g in sorted(newest.items()):
        # Only the newest full year is handed over. An older year must not stand in for it.
        fact = {"indicator_family": indicator_family(key), "factor": factor, "robust": g["robust"],
                "base": (f"{g['indicator_name']} {g['year']}: {g['worse_value']} % in the group "
                         f"'{g['worse_group']}' against {g['better_value']} % in '{g['better_group']}', "
                         f"a gap of {g['gap']} points")}
        fired = apply("group_gap", fact, "national", "FI", "Finland", g,
                      case=f"{g['indicator_name']} by {factor}, {g['year']}")
        gap_measures[(key, factor)] = [hit["rule"]["measure_id"] for hit in fired]
        if not fired and g["robust"] != "yes":
            ctx.count(step, "gaps without a recommendation: not clearly above zero")
    missing = [g["description"].split(". ")[0] for g in ctx.results["data_gaps"]
               if g["gap_type"] == "no_open_data" and g["pathway_stage"] in ("referral", "diagnosis", "treatment_start")]
    apply("pathway_data", {"pathway_data_missing": "yes" if missing else "no", "missing": "; ".join(missing)},
          "national", "FI", "Finland", case="Open data on referral, diagnosis and treatment times")

    # --- regional ----------------------------------------------------------------
    level_of = ctx.results["level_of"]
    level = lambda factor, code: level_of.get((factor, code), ("", 0))[0]
    below, shortfalls, region_measures = defaultdict(list), [], {}
    for s in ctx.results["outcome_stats"]:
        if (s["indicator_key"] in SCREENING and s["sex"] == "total" and not s["factor"]
                and s["target_status"] == "below_target" and s["region_code"] != "FI"):
            below[(s["region_code"], s["region_name"])].append(
                f"{SCREENING[s['indicator_key']]} {s['value']} %")
            shortfalls.append({**s, "target": SCREENING_TARGET})
    for (code, name), programmes in sorted(below.items()):
        region_measures[code] = [hit["rule"]["measure_id"] for hit in apply("region_below_target",
              {"language_level": level("language", code), "education_level": level("education", code),
               "base": "Clearly below the 80 % target in " + ", ".join(sorted(programmes))},
              "regional", code, name)]
    for region in ref.counties:
        code = region["region_code"]
        apply("region_access", {"primary_care_access_level": level("primary_care_access", code)},
              "regional", code, region["name_en"])
    ctx.results["recommendations"] = out
    ctx.results["decisions"] = decisions

    # --- relevance of every gap ---------------------------------------------------
    # Waiting times collected by hand are needed here, so they are read now; step 18
    # writes them out. They are not observations and not part of the row reconciliation.
    ctx.results["waiting_times"], waiting_manifest = load_waiting_times()
    if waiting_manifest:
        ctx.results["manifest"] = ctx.results["manifest"] + [waiting_manifest]
    ctx.results["gap_relevance"] = relevance.build(ctx, tree, gap_measures, region_measures, shortfalls)
    ctx.results["decision_tree"] = tree
