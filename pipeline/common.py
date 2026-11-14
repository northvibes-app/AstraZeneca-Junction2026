"""Shared configuration, reference data and helpers for all pipeline steps."""
import csv
import json
import math
import random
from collections import Counter, OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATS = ROOT / "Statistics"
REF = ROOT / "pipeline" / "reference"
OUT = ROOT / "pipeline" / "output"

# The 14-column layout every source is converted to before any cleaning happens.
RAW_COLUMNS = ["source", "source_url", "dataset", "indicator", "year", "region", "sex",
               "age_group", "cancer_site", "measure", "value", "unit", "extra", "scraped_at"]

# Layout of a cleaned observation (the "long table" described in DATA_PIPELINE.md).
OBS_COLUMNS = ["observation_id", "indicator_key", "indicator_name", "kind", "pathway_stage",
               "cancer", "detail", "region_code", "region_level", "region_name", "year", "period",
               "sex", "age_group", "measure", "factor", "factor_level", "value", "unit",
               "numerator", "denominator", "status", "flags", "source", "source_url",
               "source_file", "source_row", "also_in",
               "imputation_method", "imputation_basis"]

# Administrative levels the project works with. Everything else (hospital districts,
# sub-regions, EU countries ...) is dropped by the scope filter.
IN_SCOPE_LEVELS = {"country", "wellbeing_county", "autonomous_region", "municipality"}

# --------------------------------------------------------------------------- #
# Settings. All tunable values live in pipeline/config.json, so changing a
# threshold or adding an input file needs no code change.
# --------------------------------------------------------------------------- #
CONFIG = json.loads((ROOT / "pipeline" / "config.json").read_text(encoding="utf-8"))

ANALYSIS_YEAR = CONFIG["analysis_year"]                  # reference year for the equity analysis
CURRENT_YEAR = CONFIG["current_year"]                    # later observations must be projections or targets
ANALYSIS_WINDOW_YEARS = CONFIG["analysis_window_years"]  # years covered by the analysis subset and the fallback
SCREENING_TARGET = CONFIG["screening_target_percent"]    # National Cancer Strategy: 80 % in every programme and region

PERCENT_TOLERANCE = CONFIG["quality"]["percent_tolerance"]        # rounding allowed between counts and percent
SMALL_CELL_THRESHOLD = CONFIG["quality"]["small_cell_threshold"]  # a percentage on fewer people is unstable
OUTLIER_Z = CONFIG["quality"]["outlier_z"]                        # robust z-score above which a value is flagged
SKEW_RATIO = CONFIG["quality"]["skew_ratio_for_log_scale"]        # max / median above which outliers are judged on a log scale

MAX_YEAR_DISTANCE = CONFIG["fallback"]["max_year_distance"]        # a fallback may borrow from this many years away
MIN_REGIONS_FOR_MEAN = CONFIG["fallback"]["min_regions_for_mean"]  # regions needed for a regional mean
# Fallback values are estimates. They are published and labelled, but the equity
# measures use observed values only unless this switch is turned on.
USE_IMPUTED_IN_MEASURES = CONFIG["fallback"]["use_imputed_in_measures"]

POOLED_YEARS = CONFIG["statistics"]["pooled_years"]                  # years averaged to smooth chance variation
PERMUTATIONS = CONFIG["statistics"]["permutations"]                  # shuffles for the permutation test
RANDOM_SEED = CONFIG["statistics"]["random_seed"]                    # fixed, so every run gives the same p-values
SIGNIFICANCE = CONFIG["statistics"]["significance_level"]
MIN_INVITED_MUNICIPALITY = CONFIG["statistics"]["min_invited_per_municipality"]

# When the same observation arrives from two sources, the earlier entry wins.
SOURCE_PRIORITY = CONFIG["source_priority"]


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, columns=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = columns or (list(rows[0].keys()) if rows else [])
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


class Reference:
    """Lookup tables loaded once and shared by the steps."""

    def __init__(self):
        self.regions = read_csv(REF / "regions.csv")
        self.region_by_code = {r["region_code"]: r for r in self.regions}
        self.region_by_sotkanet_id = {r["sotkanet_id"]: r for r in self.regions}
        self.region_by_kela_name = {r["kela_name"]: r for r in self.regions if r["kela_name"]}
        self.region_by_alias = {}
        for r in self.regions:
            for alias in r["aliases"].split("|") + [r["name_fi"], r["name_en"]]:
                self.region_by_alias[alias.strip().lower()] = r
        # Full Sotkanet register: tells us the administrative level of every region id.
        self.sotkanet_register = {r["region_id"]: r for r in read_csv(REF / "sotkanet_regions.csv")}

        self.indicators = read_csv(REF / "indicators.csv")
        self.indicator_exact = {(i["match_source"], i["match_dataset"]): i for i in self.indicators}
        self.indicator_by_source = {i["match_source"]: i for i in self.indicators
                                    if i["match_dataset"] == "*"}
        self.indicator_by_key = {}
        for i in self.indicators:
            self.indicator_by_key.setdefault(i["indicator_key"], i)

        self.measures = read_csv(REF / "measures.csv")
        self.factors = read_csv(REF / "equity_factors.csv")
        self.documented_barriers = read_csv(REF / "documented_barriers.csv")
        self.known_data_gaps = read_csv(REF / "known_data_gaps.csv")
        self.counties = [r for r in self.regions if r["level"] == "wellbeing_county"]


class Context:
    """Carries counters, rejected rows and results from step to step."""

    def __init__(self):
        self.ref = Reference()
        self.stats = OrderedDict()   # step name -> Counter of what happened
        self.quarantine = []         # rows removed because they failed a rule
        self.results = {}            # named outputs of the steps

    def count(self, step, key, n=1):
        self.stats.setdefault(step, Counter())[key] += n

    def reject(self, step, row, reason):
        """Move a row to quarantine. Nothing is ever repaired by guessing."""
        self.count(step, "rejected")
        self.count(step, f"rejected: {reason}")
        self.quarantine.append({
            "step": step, "reason": reason,
            "source_file": row.get("_file") or row.get("source_file", ""),
            "source_row": row.get("_row") or row.get("source_row", ""),
            "source": row.get("source", ""),
            "indicator": row.get("indicator") or row.get("indicator_key", ""),
            "year": row.get("year", ""),
            "region": row.get("region") or row.get("region_name", ""),
            "value": row.get("value", ""),
        })


def ranks(values):
    """Ranks starting at 1; tied values share their average rank."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    result, i = [0.0] * len(values), 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            result[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return result


def spearman(a, b):
    """Rank correlation with average ranks for ties."""
    ra, rb = ranks(a), ranks(b)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5
    return num / den if den else 0.0



def wilson_interval(successes, total, z=1.96):
    """95 % confidence interval for a proportion, in percent.

    The Wilson interval stays inside 0-100 % and behaves well for small groups,
    unlike the simpler "p plus or minus 1.96 standard errors".
    """
    if not total:
        return None, None
    p = successes / total
    centre = p + z * z / (2 * total)
    spread = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total))
    denominator = 1 + z * z / total
    return (round(100 * (centre - spread) / denominator, 1),
            round(100 * (centre + spread) / denominator, 1))


def permutation_p_value(a, b, permutations=PERMUTATIONS, seed=RANDOM_SEED):
    """Two-sided p-value of a rank correlation by shuffling one of the two lists.

    It asks: if there were no relation at all, how often would chance alone give
    a correlation at least this strong? No assumption about distributions is needed,
    which matters with only 22 regions.
    """
    # Shuffling the values or their ranks is the same thing, so the ranks are computed
    # once and each shuffle only needs a sum of products.
    ra, rb = ranks(a), ranks(b)
    mean = sum(ra) / len(ra)
    ca, cb = [x - mean for x in ra], [y - mean for y in rb]
    observed = abs(sum(x * y for x, y in zip(ca, cb)))
    rng, hits = random.Random(seed), 0
    for _ in range(permutations):
        rng.shuffle(cb)
        if abs(sum(x * y for x, y in zip(ca, cb))) >= observed - 1e-9:
            hits += 1
    return (hits + 1) / (permutations + 1)


def normal_p_value(rho, n):
    """Two-sided p-value of a rank correlation for large n (used for municipalities)."""
    if n < 4 or abs(rho) >= 1:
        return 0.0 if abs(rho) >= 1 else 1.0
    t = abs(rho) * math.sqrt((n - 2) / (1 - rho * rho))
    return math.erfc(t / math.sqrt(2))


def holm_adjust(p_values):
    """Holm correction for many comparisons. Returns adjusted p-values in the input order.

    Testing 42 combinations at the 5 % level produces about two "findings" by chance.
    The correction raises each p-value according to how many tests were run.
    """
    order = sorted(range(len(p_values)), key=lambda i: p_values[i])
    adjusted, running = [0.0] * len(p_values), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(p_values) - rank) * p_values[i]))
        adjusted[i] = running
    return adjusted
