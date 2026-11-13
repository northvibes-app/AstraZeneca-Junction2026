"""Shared configuration, reference data and helpers for all pipeline steps."""
import csv
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

ANALYSIS_YEAR = 2024          # reference year for the equity analysis
CURRENT_YEAR = 2026           # observations dated later than this must be projections or targets
PERCENT_TOLERANCE = 0.1       # allowed rounding difference between numerator/denominator and percent
SMALL_CELL_THRESHOLD = 30     # counts below this make a percentage unstable
OUTLIER_Z = 3.5               # robust z-score above which a value is flagged (not removed)
ANALYSIS_WINDOW_YEARS = 10    # the analysis subset and the fallback cover this many years
MAX_YEAR_DISTANCE = 2         # a fallback may borrow from at most this many years away
MIN_REGIONS_FOR_MEAN = 5      # a regional mean needs at least this many observed regions
# Fallback values are estimates. They are published and labelled, but the equity
# measures use observed values only unless this switch is turned on.
USE_IMPUTED_IN_MEASURES = False

# When the same observation arrives from two sources, the earlier entry wins.
SOURCE_PRIORITY = ["Finnish Cancer Registry", "Team curated", "Sotkanet",
                   "StatFin/Tilastokeskus", "Kela/avoindata.fi"]


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


def spearman(a, b):
    """Rank correlation with average ranks for ties."""
    def ranks(values):
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

    ra, rb = ranks(a), ranks(b)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5
    return num / den if den else 0.0
