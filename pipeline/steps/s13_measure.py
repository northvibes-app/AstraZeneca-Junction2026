"""Step 13: MEASURE

Compute the size of each gap, with its evidence type (A, B or C).
"""
from collections import defaultdict

from common import spearman


def measure(ctx):
    """Turn tagged observations into gap figures. Differences are stated, not explained."""
    step, ref, gaps = "13 measure", ctx.ref, []
    tagged = ctx.results["observations_by_factor"]

    def base(evidence, factor, r):
        return {"evidence_type": evidence, "factor": factor,
                "indicator_key": r["indicator_key"], "indicator_name": r["indicator_name"],
                "pathway_stage": r["pathway_stage"], "year": r["year"], "unit": r["unit"],
                "region": "", "worse_group": "", "worse_value": "", "better_group": "",
                "better_value": "", "gap": "", "people_in_worse_group": "",
                "potential_additional": "", "spearman_rho": "", "n_regions": "",
                "status": r["status"], "note": "", "source_url": r["source_url"]}

    # --- Type A: compare the groups the source published --------------------------
    groups = defaultdict(list)
    for t in tagged:
        if t["evidence_type"] == "A":
            groups[(t["indicator_key"], t["year"], t["region_code"], t["factor"])].append(t)
    for (key, year, region, factor), members in sorted(groups.items()):
        if len(members) < 2:
            continue
        higher_is_better = ref.indicator_by_key[key]["higher_is"] == "better"
        members.sort(key=lambda t: t["value"], reverse=not higher_is_better)
        worse, better = members[0], members[-1]
        g = base("A", factor, worse)
        g.update(region=worse["region_name"], worse_group=worse["factor_level"],
                 worse_value=worse["value"], better_group=better["factor_level"],
                 better_value=better["value"], gap=round(abs(better["value"] - worse["value"]), 1))
        if higher_is_better and worse["denominator"]:
            # Arithmetic on published counts: how many more people would take part if the
            # worse-off group reached the level of the best group. Not an effect forecast.
            g["people_in_worse_group"] = int(worse["denominator"])
            g["potential_additional"] = int(round(worse["denominator"] * g["gap"] / 100))
        g["note"] = "Direct comparison of groups published by the source"
        gaps.append(g)
        ctx.count(step, "gaps measured, evidence A")

    # --- Type B: compare disadvantaged with advantaged regions --------------------
    groups = defaultdict(list)
    for t in tagged:
        if t["evidence_type"] == "B":
            groups[(t["indicator_key"], t["year"], t["factor"])].append(t)
    for (key, year, factor), members in sorted(groups.items()):
        low = [t["value"] for t in members if t["factor_level"] == "disadvantaged"]
        high = [t["value"] for t in members if t["factor_level"] == "advantaged"]
        if len(members) < 15 or not low or not high:
            continue
        g = base("B", factor, members[0])
        mean_low, mean_high = sum(low) / len(low), sum(high) / len(high)
        g.update(region="22 regions", worse_group=f"disadvantaged third ({len(low)} regions)",
                 worse_value=round(mean_low, 1),
                 better_group=f"advantaged third ({len(high)} regions)",
                 better_value=round(mean_high, 1), gap=round(mean_low - mean_high, 1),
                 spearman_rho=round(spearman([t["disadvantage_score"] for t in members],
                                             [t["value"] for t in members]), 2),
                 n_regions=len(members))
        g["note"] = ("Unweighted regional averages; gap = disadvantaged minus advantaged. "
                     "Negative rho = the more disadvantaged the region, the lower the value. "
                     "A pattern between regions, not between people")
        gaps.append(g)
        ctx.count(step, "gaps measured, evidence B")

    # --- Type C: barriers that are documented but not measured --------------------
    for b in ref.documented_barriers:
        gaps.append({"evidence_type": "C", "factor": b["factor"], "indicator_key": "",
                     "indicator_name": "", "pathway_stage": b["pathway_stage"], "year": "",
                     "unit": "", "region": "Finland", "worse_group": "", "worse_value": "",
                     "better_group": "", "better_value": "", "gap": "",
                     "people_in_worse_group": "", "potential_additional": "", "spearman_rho": "",
                     "n_regions": "", "status": "documented", "note": b["barrier"],
                     "source_url": f"{b['source']}, p. {b['page']}"})
        ctx.count(step, "barriers listed, evidence C")
    ctx.results["equity_gaps"] = gaps
