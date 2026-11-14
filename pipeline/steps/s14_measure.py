"""Step 14: MEASURE

Compute the size of each gap, how certain it is, and its evidence type.

    A               groups compared directly (education, language, sex)
    B               22 regions compared by their category on a factor
    B-municipality  the same comparison across about 300 municipalities
    C               barriers that are documented but not measured
"""
import math
from collections import defaultdict

from common import (ANALYSIS_YEAR, MIN_INVITED_MUNICIPALITY, SIGNIFICANCE, holm_adjust,
                    normal_p_value, permutation_p_value, spearman)

GAP_COLUMNS = ["evidence_type", "factor", "indicator_key", "indicator_name", "pathway_stage",
               "year", "unit", "region_code", "region", "worse_group", "worse_value",
               "better_group", "better_value", "gap", "gap_ci_low", "gap_ci_high", "gap_weighted",
               "people_in_worse_group", "potential_additional", "spearman_rho", "n_regions",
               "p_value", "p_adjusted", "robust", "basis", "status", "note", "source_url"]


def _blank(evidence, factor, r):
    row = dict.fromkeys(GAP_COLUMNS, "")
    row.update(evidence_type=evidence, factor=factor, indicator_key=r["indicator_key"],
               indicator_name=r["indicator_name"], pathway_stage=r["pathway_stage"],
               year=r["year"], unit=r["unit"], status=r["status"], source_url=r["source_url"])
    return row


def _mean(values, weights=None):
    if weights is None:
        return sum(values) / len(values)
    return sum(v * w for v, w in zip(values, weights)) / sum(weights)


def _correct(rows):
    """Holm correction within one family of tests; marks which patterns survive it."""
    adjusted = holm_adjust([r["p_value"] for r in rows])
    for r, p in zip(rows, adjusted):
        r["p_adjusted"] = round(p, 4)
        r["p_value"] = round(r["p_value"], 4)
        r["robust"] = "yes" if p < SIGNIFICANCE else "no"


def measure(ctx):
    """Turn tagged observations into gap figures. Differences are stated, not explained."""
    step, ref, gaps = "14 measure", ctx.ref, []
    tagged = ctx.results["observations_by_factor"]
    higher_is_better = lambda key: ref.indicator_by_key[key]["higher_is"] == "better"

    # --- Type A: compare the groups the source published --------------------------
    groups = defaultdict(list)
    for t in tagged:
        if t["evidence_type"] == "A":
            groups[(t["indicator_key"], t["year"], t["region_code"], t["factor"])].append(t)
    for (key, year, region, factor), members in sorted(groups.items()):
        if len(members) < 2:
            continue
        members.sort(key=lambda t: t["value"], reverse=not higher_is_better(key))
        worse, better = members[0], members[-1]
        g = _blank("A", factor, worse)
        g.update(region_code=region, region=worse["region_name"],
                 worse_group=worse["factor_level"], worse_value=worse["value"],
                 better_group=better["factor_level"], better_value=better["value"],
                 gap=round(abs(better["value"] - worse["value"]), 1),
                 basis="Direct comparison of groups published by the source")
        # Uncertainty of the gap: standard error of a difference of two proportions.
        n1, n2 = better["denominator"], worse["denominator"]
        if n1 and n2 and worse["unit"] == "percent":
            p1, p2 = better["value"] / 100, worse["value"] / 100
            se = 100 * math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
            g["gap_ci_low"], g["gap_ci_high"] = round(g["gap"] - 1.96 * se, 1), round(g["gap"] + 1.96 * se, 1)
            g["robust"] = "yes" if g["gap_ci_low"] > 0 else "no"
        if higher_is_better(key) and n2:
            # Arithmetic on published counts: how many more people would be reached if the
            # worse-off group came up to the level of the best group. Not an effect forecast.
            g["people_in_worse_group"] = int(n2)
            g["potential_additional"] = int(round(n2 * g["gap"] / 100))
        gaps.append(g)
        ctx.count(step, "gaps measured, evidence A")

    # --- Type B: compare disadvantaged with advantaged regions --------------------
    population = {p["region_code"]: p["population"] for p in ctx.results["region_profile"]}
    groups, family = defaultdict(list), []
    for t in tagged:
        if t["evidence_type"] == "B":
            groups[(t["indicator_key"], t["year"], t["factor"])].append(t)
    for (key, year, factor), members in sorted(groups.items()):
        # The multi-year average is used where it exists; a single year of a small
        # region is too noisy, especially for survival.
        value = lambda t: t["pooled_value"] if t["pooled_value"] != "" else t["value"]
        low = [t for t in members if t["factor_level"] == "disadvantaged"]
        high = [t for t in members if t["factor_level"] == "advantaged"]
        if len(members) < 15 or not low or not high:
            continue
        weights = lambda ts: [population.get(t["region_code"]) or 1 for t in ts]
        scores, values = [t["disadvantage_score"] for t in members], [value(t) for t in members]
        g = _blank("B", factor, members[0])
        g.update(region="22 regions",
                 worse_group=f"disadvantaged third ({len(low)} regions)",
                 worse_value=round(_mean([value(t) for t in low]), 1),
                 better_group=f"advantaged third ({len(high)} regions)",
                 better_value=round(_mean([value(t) for t in high]), 1),
                 spearman_rho=round(spearman(scores, values), 2), n_regions=len(members),
                 p_value=permutation_p_value(scores, values),
                 basis="Regional figures averaged over the latest years; permutation test")
        g["gap"] = round(g["worse_value"] - g["better_value"], 1)
        # Population-weighted version: Helsinki counts for more than Kainuu.
        g["gap_weighted"] = round(_mean([value(t) for t in low], weights(low))
                                  - _mean([value(t) for t in high], weights(high)), 1)
        g["note"] = ("gap = disadvantaged minus advantaged third. Negative rho = the more "
                     "disadvantaged the region, the lower the value. A pattern between regions, "
                     "not between people")
        family.append(g)
        ctx.count(step, "gaps measured, evidence B")
    _correct(family)
    gaps += family
    ctx.count(step, "evidence B patterns that survive correction",
              sum(1 for g in family if g["robust"] == "yes"))

    # --- Type B at municipality level --------------------------------------------
    # About 300 municipalities give far more statistical power than 22 regions. Small
    # municipalities are left out because their percentages rest on too few people.
    latest = ctx.results["latest_year"]
    outcomes, context = defaultdict(dict), defaultdict(dict)   # key -> {municipality: ...}
    for r in ctx.results["observations"]:
        if (r["region_level"] != "municipality" or r["sex"] != "total" or r["factor"]
                or r["status"] != "observed"):
            continue
        if r["kind"] == "outcome" and r["indicator_key"].startswith("screening_participation"):
            if r["year"] == latest.get(r["indicator_key"]) and r["numerator"] and r["value"] > 0:
                invited = r["numerator"] / (r["value"] / 100)
                if invited >= MIN_INVITED_MUNICIPALITY:
                    outcomes[r["indicator_key"]][r["region_code"]] = (r, invited)
        elif r["kind"] == "context" and r["year"] <= ANALYSIS_YEAR:
            previous = context[r["indicator_key"]].get(r["region_code"])
            if previous is None or r["year"] > previous[0]:
                context[r["indicator_key"]][r["region_code"]] = (r["year"], r["value"])
    family = []
    for key in sorted(outcomes):
        for factor in ref.factors:
            ctx_values = context.get(factor["context_indicator_key"], {})
            codes = sorted(set(outcomes[key]) & set(ctx_values))
            if len(codes) < 100:
                continue                          # this factor is not published per municipality
            sign = 1 if factor["disadvantaged_when"] == "high" else -1
            scores = [sign * ctx_values[c][1] for c in codes]
            values = [outcomes[key][c][0]["value"] for c in codes]
            invited = [outcomes[key][c][1] for c in codes]
            order = sorted(range(len(codes)), key=lambda i: -scores[i])
            third = len(codes) // 3
            low, high = order[:third], order[-third:]
            rho = spearman(scores, values)
            g = _blank("B-municipality", factor["factor"], outcomes[key][codes[0]][0])
            g.update(region=f"{len(codes)} municipalities",
                     worse_group=f"disadvantaged third ({third} municipalities)",
                     worse_value=round(_mean([values[i] for i in low]), 1),
                     better_group=f"advantaged third ({third} municipalities)",
                     better_value=round(_mean([values[i] for i in high]), 1),
                     spearman_rho=round(rho, 2), n_regions=len(codes),
                     p_value=normal_p_value(rho, len(codes)),
                     basis=f"Municipalities with at least {MIN_INVITED_MUNICIPALITY} invited people")
            g["gap"] = round(g["worse_value"] - g["better_value"], 1)
            g["gap_weighted"] = round(
                _mean([values[i] for i in low], [invited[i] for i in low])
                - _mean([values[i] for i in high], [invited[i] for i in high]), 1)
            g["note"] = "A pattern between municipalities, not between people"
            family.append(g)
            ctx.count(step, "gaps measured, evidence B-municipality")
    if family:
        _correct(family)
        gaps += family
        ctx.count(step, "municipality patterns that survive correction",
                  sum(1 for g in family if g["robust"] == "yes"))

    # --- Type C: barriers that are documented but not measured --------------------
    for b in ref.documented_barriers:
        g = dict.fromkeys(GAP_COLUMNS, "")
        g.update(evidence_type="C", factor=b["factor"], pathway_stage=b["pathway_stage"],
                 region="Finland", status="documented", note=b["barrier"],
                 source_url=f"{b['source']}, p. {b['page']}")
        gaps.append(g)
        ctx.count(step, "barriers listed, evidence C")
    ctx.results["equity_gaps"] = gaps
