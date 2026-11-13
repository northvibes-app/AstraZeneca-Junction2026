"""Step 4: STANDARDISE

Translate every source's own labels into one shared vocabulary:
regions, sex, age groups, units, indicators and cancer sites.
"""
import sys


SEX = {"total": "total", "yhteensä": "total", "male": "male", "mies": "male", "miehet": "male",
       "female": "female", "nainen": "female", "naiset": "female"}

# Statistics Finland cause-of-death groups: code -> English name
CANCER_SITES = {
    "04-21": "All cancers (C00-C97)", "04": "Lip, oral cavity and pharynx (C00-C14)",
    "05": "Oesophagus (C15)", "06": "Stomach (C16)", "07": "Colon (C18-C19)",
    "08": "Rectum and anus (C20-C21)", "09": "Primary liver (C22)", "10": "Pancreas (C25)",
    "11": "Larynx, trachea and lung (C32-C34)", "13": "Breast (C50)", "14": "Cervix (C53)",
    "15": "Uterus (C54-C55)", "16": "Ovary (C56)", "17": "Prostate (C61)", "18": "Kidney (C64)",
    "19": "Bladder (C67)", "20": "Lymphoid and haematopoietic tissue (C81-C96)",
    "21": "Other cancers",
}
GROUPS = {  # group labels of the cervical equity file -> (factor, factor_level)
    "Primary education / unknown": ("education", "primary_or_unknown"),
    "Intermediate / secondary education": ("education", "secondary"),
    "Tertiary / higher education": ("education", "tertiary"),
    "Domestic": ("language", "domestic"),
    "Other / missing": ("language", "other_or_missing"),
}


def _age_group(text):
    """'0 - 14' -> '0-14', '65 -' -> '65+', 'Yhteensä' or empty -> 'all'."""
    text = text.replace(" ", "")
    if text in ("", "Yhteensä"):
        return "all"
    return text[:-1] + "+" if text.endswith("-") else text


def _resolve_region(ref, row):
    """Return (code, level, English name), or None when the region is unknown."""
    source, extra = row["source"], row["_extra"]
    if source == "Sotkanet":
        # Region NAMES are ambiguous in Sotkanet (five different regions are called
        # "Ahvenanmaa"), so the numeric region id is the only reliable key.
        region_id = str(extra.get("region_id", ""))
        if region_id in ref.region_by_sotkanet_id:
            r = ref.region_by_sotkanet_id[region_id]
            return r["region_code"], r["level"], r["name_en"]
        reg = ref.sotkanet_register.get(region_id)
        if reg is None:
            return None
        if reg["category"] == "KUNTA":
            return "M" + reg["code"], "municipality", reg["name_fi"]
        return "X" + region_id, reg["category"].lower(), reg["name_fi"]   # out of scope later
    if source == "Kela/avoindata.fi":
        if row["region"] == "Tuntematon":                 # "unknown" in the Kela export
            return "UNK", "unknown", "Unknown"
        r = ref.region_by_kela_name.get(row["region"])
    elif row["region"] == "":
        r = ref.region_by_code["FI"]                      # Statistics Finland: national only
    else:
        r = ref.region_by_alias.get(row["region"].lower())
    return (r["region_code"], r["level"], r["name_en"]) if r else None


def standardise(ctx, rows):
    """Translate every source's own labels into one shared vocabulary."""
    step, ref, intern = "04 standardise", ctx.ref, sys.intern
    for row in rows:
        cat = (ref.indicator_exact.get((row["source"], row["dataset"]))
               or ref.indicator_by_source.get(row["source"]))
        if cat is None:
            ctx.reject(step, row, "indicator not in catalogue")
            continue
        sex = SEX.get(row["sex"].lower())
        if sex is None:
            ctx.reject(step, row, "unknown sex label")
            continue
        region = _resolve_region(ref, row)
        if region is None:
            ctx.reject(step, row, "unknown region")
            continue

        extra = row["_extra"]
        period = row["year"]
        # What the row is about in detail: cancer site, entitlement or national indicator name.
        if row["source"] == "StatFin/Tilastokeskus":
            detail = CANCER_SITES.get(str(extra.get("cause_code", "")), row["cancer_site"])
        elif row["source"] == "Kela/avoindata.fi":
            detail = row["indicator"]
        elif cat["indicator_key"] == "national_key_statistic":
            detail = row["indicator"] + (f" [{extra['geography']}]" if extra.get("geography") else "")
        else:
            detail = ""
        factor, level = cat["factor"], cat["factor_level"]
        if extra.get("group") in GROUPS:
            factor, level = GROUPS[extra["group"]]

        # The raw files only carry the address of the Sotkanet home page. The indicator
        # id lets us link each figure to the page that defines exactly that indicator.
        source_url = row["source_url"]
        if row["source"] == "Sotkanet" and extra.get("indicator_id"):
            source_url = f"https://sotkanet.fi/sotkanet/en/metadata/indicators/{extra['indicator_id']}"

        def number(key):
            v = extra.get(key)
            try:
                return float(v) if v not in (None, "") else None
            except (TypeError, ValueError):
                return None

        ctx.count(step, "rows standardised")
        yield {
            "indicator_key": intern(cat["indicator_key"]), "indicator_name": intern(cat["name_en"]),
            "kind": intern(cat["kind"]), "pathway_stage": intern(cat["pathway_stage"]),
            "cancer": intern(cat["cancer"]), "detail": intern(detail),
            "region_code": intern(region[0]), "region_level": intern(region[1]),
            "region_name": intern(region[2]),
            "year": int(period[-4:]),            # a range is filed under its last year
            "period": intern(period), "sex": intern(sex),
            "age_group": intern(_age_group(row["age_group"])),
            "measure": intern(row["measure"]), "factor": intern(factor),
            "factor_level": intern(level), "value": row["_value"],
            # The unit column is empty in the Sotkanet export, so the catalogue supplies it.
            "unit": intern(row["unit"] if row["unit"] not in ("", "persons") else cat["unit"]),
            # attended_n / n is the count behind a percentage; invited_n is its base.
            "numerator": number("attended_n") if "attended_n" in extra else number("n"),
            "denominator": number("invited_n"),
            "status": intern(extra.get("status") or "observed"), "flags": "",
            "source": intern(row["source"]), "source_url": intern(source_url),
            "source_file": intern(row["_file"]), "source_row": row["_row"], "also_in": "",
            "imputation_method": "", "imputation_basis": "",
        }
