"""Step 13: CATEGORISE

Tag every figure with the equity factor it informs.

Evidence types (see DATA_PIPELINE.md):
    A  stratified  the source reports the outcome separately per group
    B  regional    regions are grouped by a characteristic and compared
    C  documented  a cited document describes the barrier; no open number exists

Fallback values from step 9 are published but, by default, not used from here on:
gaps between groups should rest on what was actually measured.
"""
from common import USE_IMPUTED_IN_MEASURES


def categorise(ctx):
    """Assign equity-factor categories.

    Regions get two categories per factor:
      factor_level  relative: the 22 regions are ranked and split into thirds,
                    'disadvantaged' (7 regions), 'middle' (8) and 'advantaged' (7)
      vs_national   absolute: is the region's value worse or better than Finland's?
    The relative split always labels seven regions as disadvantaged, however small
    the differences are. The absolute comparison does not have that weakness.

    Observations: every outcome figure is then listed once per factor it can inform,
    together with its evidence type.
    """
    step, ref = "13 categorise", ctx.ref
    profiles = ctx.results["region_profile"]
    counties = [p for p in profiles if p["region_level"] == "wellbeing_county"]
    finland = next(p for p in profiles if p["region_level"] == "country")

    # --- regions -> factor levels ------------------------------------------------
    region_levels, level_of = [], {}
    for factor in ref.factors:
        key, high_is_bad = factor["context_indicator_key"], factor["disadvantaged_when"] == "high"
        have = [p for p in counties if p[key] != ""]
        # Sort so that the most disadvantaged region comes first.
        have.sort(key=lambda p: p[key], reverse=high_is_bad)
        third = len(have) // 3
        for rank, p in enumerate(have):
            level = ("disadvantaged" if rank < third
                     else "advantaged" if rank >= len(have) - third else "middle")
            # Disadvantage score: larger always means more disadvantaged, whatever the
            # direction of the underlying measure. Used for the rank correlation.
            score = p[key] if high_is_bad else -p[key]
            vs_national = ""
            if finland[key] != "":
                worse = p[key] > finland[key] if high_is_bad else p[key] < finland[key]
                vs_national = "worse_than_finland" if worse else "same_or_better_than_finland"
            level_of[(factor["factor"], p["region_code"])] = (level, score)
            region_levels.append({"factor": factor["factor"], "factor_label": factor["label"],
                                  "region_code": p["region_code"], "region_name": p["region_name"],
                                  "context_indicator": key, "context_value": p[key],
                                  "context_year": p[key + "_year"], "national_value": finland[key],
                                  "factor_level": level, "vs_national": vs_national})
            ctx.count(step, "region categories assigned")
    ctx.results["region_factor_levels"] = region_levels
    ctx.results["level_of"] = level_of

    # --- observations -> factor tags ---------------------------------------------
    latest, stats, tagged = ctx.results["latest_year"], ctx.results["stats_by_id"], []

    def tag(r, factor, level, evidence, score=""):
        s = stats.get(r["observation_id"], {})
        tagged.append({"evidence_type": evidence, "factor": factor, "factor_level": level,
                       "disadvantage_score": score, "indicator_key": r["indicator_key"],
                       "indicator_name": r["indicator_name"], "pathway_stage": r["pathway_stage"],
                       "region_code": r["region_code"], "region_name": r["region_name"],
                       "year": r["year"], "value": r["value"], "unit": r["unit"],
                       "pooled_value": s.get("pooled_value", ""), "numerator": r["numerator"],
                       "denominator": s.get("denominator", r["denominator"]),
                       "ci_low": s.get("ci_low", ""), "ci_high": s.get("ci_high", ""),
                       "status": r["status"], "flags": r["flags"],
                       "observation_id": r["observation_id"], "source_url": r["source_url"]})
        ctx.count(step, f"observations tagged, evidence {evidence}")

    for r in ctx.results["analysis"]:
        if r["status"] == "imputed" and not USE_IMPUTED_IN_MEASURES:
            ctx.count(step, "imputed observations left out of the measures")
            continue
        if r["kind"] != "outcome" and not r["factor"]:
            continue
        # Type A: the source itself split the figure by education or language.
        # Figures split by a factor AND by sex stay in the tables but are not compared here.
        if r["factor"]:
            if r["sex"] == "total":
                tag(r, r["factor"], r["factor_level"], "A")
        # Type A by sex. Indexes are excluded: they are standardised within each sex, so
        # men and women both equal 100 nationally and a comparison would be meaningless.
        elif r["sex"] != "total":
            if r["unit"] == "percent" and (r["region_level"] == "country"
                                           or r["year"] == latest.get(r["indicator_key"])):
                tag(r, "sex", r["sex"], "A")
        # Type B: a regional outcome, tagged with the category of its region for every factor.
        elif (r["region_level"] == "wellbeing_county"
              and r["year"] == latest.get(r["indicator_key"])):
            for factor in ref.factors:
                hit = level_of.get((factor["factor"], r["region_code"]))
                if hit:
                    tag(r, factor["factor"], hit[0], "B", hit[1])
    ctx.results["observations_by_factor"] = tagged
