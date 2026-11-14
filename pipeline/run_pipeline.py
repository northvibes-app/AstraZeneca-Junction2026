"""Equal Care Navigator - data pipeline prototype.

Runs the 18 steps in order and writes the results to pipeline/output/.

    python3 pipeline/run_pipeline.py             # run the pipeline
    python3 pipeline/run_pipeline.py --upload    # run it, then upload the results to Azure

     1 ingest            read every source into one common raw layout
     2 profile           measure the data before anything is changed
     3 validate_schema   structure and types; broken rows go to quarantine
     4 standardise       one vocabulary for regions, sex, age, units, indicators
     5 scope_filter      keep only the administrative levels the project uses
     6 deduplicate       remove repeated observations, resolve conflicts by rule
     7 quality_checks    range, date and arithmetic rules; flag outliers and small cells
     8 completeness      list what is missing
     9 impute            labelled fallback values for missing region-year cells
    10 integrate         final sort, stable ids, analysis subset
    11 enrich            attach each region's social and economic context and population
    12 derive            confidence intervals, multi-year averages, position against the target
    13 categorise        tag every figure with the equity factor it informs
    14 measure           size and certainty of each gap, with its evidence type
    15 recommend         link each gap to a measure from the national roadmap
    16 trends            mortality by cancer site and new treatment entitlements by region
    17 compare_runs      what changed since the previous run
    18 publish           write all outputs, fact sheets, lineage and the run report

Settings are in pipeline/config.json.
Only the Python standard library is used, so nothing needs to be installed.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import Context                                                    # noqa: E402
from steps import (s01_ingest, s02_profile, s03_validate_schema, s04_standardise,   # noqa: E402
                   s05_scope_filter, s06_deduplicate, s07_quality_checks, s08_completeness,
                   s09_impute, s10_integrate, s11_enrich, s12_derive, s13_categorise,
                   s14_measure, s15_recommend, s16_trends, s17_compare_runs, s18_publish)


def main():
    started = datetime.now(timezone.utc)
    ctx = Context()

    # Steps 1-5 look at one row at a time. They are chained generators: each row
    # flows through all five before the next row is read, so the 745,000-row raw
    # file never has to sit in memory in its raw form. list() pulls the stream through.
    stream = s01_ingest.ingest(ctx)
    stream = s02_profile.profile(ctx, stream)
    stream = s03_validate_schema.validate_schema(ctx, stream)
    stream = s04_standardise.standardise(ctx, stream)
    stream = s05_scope_filter.scope_filter(ctx, stream)
    rows = list(stream)

    # Steps 6-10 need the whole table at once.
    rows = s06_deduplicate.deduplicate(ctx, rows)
    rows = s07_quality_checks.quality_checks(ctx, rows)
    rows = s08_completeness.completeness(ctx, rows)
    rows = s09_impute.impute(ctx, rows)
    rows = s10_integrate.integrate(ctx, rows)

    # Steps 11-18 build the equity view and write everything out.
    s11_enrich.enrich(ctx)
    s12_derive.derive(ctx)
    s13_categorise.categorise(ctx)
    s14_measure.measure(ctx)
    s15_recommend.recommend(ctx)
    s16_trends.trends(ctx)
    s17_compare_runs.compare_runs(ctx)      # must run before publish overwrites the old files
    s18_publish.publish(ctx, started)

    for name, counter in ctx.stats.items():
        print(name)
        for key, value in counter.items():
            print(f"    {key}: {value:,}")
    print("\nOutputs written to pipeline/output/")

    # Optional last stage: copy the CSV results to the team's Azure Blob Storage.
    # It is opt-in so that a normal run never needs a network connection.
    if "--upload" in sys.argv:
        import upload_to_azure
        print()
        if not upload_to_azure.upload():
            sys.exit("Upload incomplete, see the messages above.")


if __name__ == "__main__":
    main()
