"""Step 9: IMPUTE

Add labelled fallback values for missing region-year cells.
"""
from common import MAX_YEAR_DISTANCE, MIN_REGIONS_FOR_MEAN


def impute(ctx, rows):
    """Give missing region-year cells a labelled fallback value where one is defensible.

    Fallback ladder, first rule that applies wins:

      1 temporal_mean   the region has a value shortly before AND shortly after the
                        missing year -> average of those two values
      2 nearest_year    the region has a value on one side only -> that value
      3 regional_mean   the region has nothing nearby, but other regions reported
                        that year -> unweighted average of those regions
      - none            otherwise the gap stays empty

    Rules 1 and 2 come first because a region resembles itself in neighbouring
    years far more than it resembles other regions.

    Safeguards:
      * only observed values are used as a basis, never another fallback value
      * every fallback row has status "imputed", the method, the values it was built
        from, and no numerator or denominator
      * "no_open_data" gaps (for example waiting times) are never filled: there is
        nothing to average
    """
    step, ref = "09 impute", ctx.ref
    grid, new_rows = ctx.results["grid"], []
    county_codes = [c["region_code"] for c in ref.counties]

    for gap in ctx.results["data_gaps"]:
        if gap["gap_type"] != "region_year_missing":
            continue
        key, code, year = gap["indicator_key"], gap["region_code"], gap["year"]
        cells = grid[key]

        def neighbour(direction):
            """Nearest observed year of the same region, looking backwards (-1) or forwards (+1)."""
            for distance in range(1, MAX_YEAR_DISTANCE + 1):
                hit = cells.get((code, year + direction * distance))
                if hit is not None:
                    return hit
            return None

        before, after = neighbour(-1), neighbour(+1)
        if before and after:
            method = "temporal_mean"
            value = (before["value"] + after["value"]) / 2
            basis = f"{before['year']}: {before['value']}, {after['year']}: {after['value']}"
            template = before
        elif before or after:
            method, template = "nearest_year", before or after
            value = template["value"]
            basis = f"{template['year']}: {template['value']}"
        else:
            others = [cells[(c, year)] for c in county_codes if (c, year) in cells]
            if len(others) < MIN_REGIONS_FOR_MEAN:
                gap["fallback"] = "none"
                ctx.count(step, "gaps left empty")
                continue
            method, template = "regional_mean", others[0]
            values = [o["value"] for o in others]
            value = sum(values) / len(values)
            basis = f"{len(values)} regions in {year}, range {min(values)} to {max(values)}"

        value = round(value, 1)
        region = ref.region_by_code[code]
        row = dict(template)                 # copies indicator name, unit, stage ...
        row.update(region_code=code, region_name=region["name_en"], year=year, period=str(year),
                   value=value, numerator=None, denominator=None, status="imputed",
                   flags="imputed", source="Pipeline fallback", source_url="", source_file="",
                   source_row="", also_in="", imputation_method=method, imputation_basis=basis)
        new_rows.append(row)
        gap["fallback"], gap["fallback_value"] = method, value
        ctx.count(step, "values imputed")
        ctx.count(step, f"values imputed: {method}")

    ctx.count(step, "values imputed", 0)
    ctx.results["imputed_count"] = len(new_rows)
    return rows + new_rows
