"""Step 12: CATEGORISE

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

    Regions: for each factor the 22 regions are ranked and split into thirds:
    'disadvantaged' (7 regions), 'middle' (8) and 'advantaged' (7). Thirds are used
    instead of fixed cut-offs because no official threshold exists for these measures.

    Observations: every outcome figure is then listed once per factor it can inform,
    together with its evidence type.
    """
    step, ref = "12 categorise", ctx.ref
    counties = [p for p in ctx.results["region_profile"] if p["region_level"] == "wellbeing_county"]

    # --- regions -> factor levels ------------------------------------------------
    region_levels, level_of = [], {}
    for factor in ref.factors:
        key = factor["context_indicator_key"]
        have = [p for p in counties if p[key] != ""]
        # Sort so that the most disadvantaged region comes first.
        have.sort(key=lambda p: p[key], reverse=(factor["disadvantaged_when"] == "high"))
        third = len(have) // 3
        for rank, p in enumerate(have):
            level = ("disadvantaged" if rank < third
                     else "advantaged" if rank >= len(have) - third else "middle")
            # Disadvantage score: larger always means more disadvantaged, whatever the
            # direction of the underlying measure. Used for the rank correlation.
            score = p[key] if factor["disadvantaged_when"] == "high" else -p[key]
            level_of[(factor["factor"], p["region_code"])] = (level, score)
            region_levels.append({"factor": factor["factor"], "factor_label": factor["label"],
                                  "region_code": p["region_code"], "region_name": p["region_name"],
                                  "context_indicator": key, "context_value": p[key],
                                  "context_year": p[key + "_year"], "factor_level": level})
            ctx.count(step, "region categories assigned")
    ctx.results["region_factor_levels"] = region_levels
    ctx.results["level_of"] = level_of

    # --- observations -> factor tags ---------------------------------------------
    latest, tagged = ctx.results["latest_year"], []

    def tag(r, factor, level, evidence, context_value=""):
        tagged.append({"evidence_type": evidence, "factor": factor, "factor_level": level,
                       "disadvantage_score": context_value, "indicator_key": r["indicator_key"],
                       "indicator_name": r["indicator_name"], "pathway_stage": r["pathway_stage"],
                       "region_code": r["region_code"], "region_name": r["region_name"],
                       "year": r["year"], "value": r["value"], "unit": r["unit"],
                       "numerator": r["numerator"], "denominator": r["denominator"],
                       "status": r["status"], "flags": r["flags"],
                       "observation_id": r["observation_id"], "source_url": r["source_url"]})
        ctx.count(step, f"observations tagged, evidence {evidence}")

    for r in ctx.results["analysis"]:
        if r["status"] == "imputed" and not USE_IMPUTED_IN_MEASURES:
            ctx.count(step, "imputed observations left out of the measures")
            continue
        # Type A: the source itself split the figure by education or language ...
        if r["factor"]:
            tag(r, r["factor"], r["factor_level"], "A")
        # ... or by sex (kept only for the latest year to stay readable).
        # Indexes are excluded: they are standardised within each sex, so men and
        # women both equal 100 nationally and a comparison would be meaningless.
        elif (r["sex"] != "total" and r["kind"] == "outcome" and r["unit"] == "percent"
              and r["year"] == latest.get(r["indicator_key"])):
            tag(r, "sex", r["sex"], "A")
        # Type B: a regional outcome, tagged with the category of its region for every factor.
        elif (r["kind"] == "outcome" and r["region_level"] == "wellbeing_county"
              and r["sex"] == "total" and r["year"] == latest.get(r["indicator_key"])):
            for factor in ref.factors:
                hit = level_of.get((factor["factor"], r["region_code"]))
                if hit:
                    tag(r, factor["factor"], hit[0], "B", hit[1])
    ctx.results["observations_by_factor"] = tagged
