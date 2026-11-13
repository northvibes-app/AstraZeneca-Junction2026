"""Step 14: PUBLISH

Write all outputs, the lineage record and the run report.

The step fails if any input row is unaccounted for.
"""
import csv
import gzip
import json
from datetime import datetime, timezone

from common import ANALYSIS_YEAR, OBS_COLUMNS, OUT, write_csv


def publish(ctx, started):
    """Write every output and a run report, and check that no row went missing."""
    step, res = "14 publish", ctx.results
    OUT.mkdir(parents=True, exist_ok=True)

    # Clean layer: every observation that passed all checks (compressed, it is large).
    with gzip.open(OUT / "observations_clean.csv.gz", "wt", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OBS_COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(res["observations"])
    write_csv(OUT / "observations_analysis.csv", res["analysis"], OBS_COLUMNS)
    write_csv(OUT / "region_profile.csv", res["region_profile"])
    write_csv(OUT / "region_factor_levels.csv", res["region_factor_levels"])
    write_csv(OUT / "observations_by_factor.csv", res["observations_by_factor"])
    write_csv(OUT / "equity_gaps.csv", res["equity_gaps"])
    write_csv(OUT / "data_gaps.csv", res["data_gaps"])
    write_csv(OUT / "quarantine.csv", ctx.quarantine,
              ["step", "reason", "source_file", "source_row", "source", "indicator", "year",
               "region", "value"])
    (OUT / "profile.json").write_text(json.dumps(res["profile"], ensure_ascii=False, indent=1),
                                      encoding="utf-8")

    # Reconciliation: every row that was read must be accounted for exactly once.
    s = ctx.stats
    read = s["01 ingest"]["rows read"]
    imputed = res["imputed_count"]           # rows the pipeline added itself
    accounted = (len(res["observations"]) - imputed + len(ctx.quarantine)
                 + s["05 scope_filter"]["filtered out"] + s["06 deduplicate"]["duplicates removed"])
    balanced = read == accounted
    ctx.count(step, "rows read", read)
    ctx.count(step, "rows accounted for", accounted)

    finished = datetime.now(timezone.utc)
    lineage = {"run_started_utc": started.isoformat(timespec="seconds"),
               "run_finished_utc": finished.isoformat(timespec="seconds"),
               "analysis_year": ANALYSIS_YEAR, "inputs": res["manifest"],
               "reconciliation": {"rows_read": read, "published": len(res["observations"]),
                                  "of_which_imputed": imputed,
                                  "quarantined": len(ctx.quarantine),
                                  "filtered_out_of_scope": s["05 scope_filter"]["filtered out"],
                                  "duplicates_removed": s["06 deduplicate"]["duplicates removed"],
                                  "balanced": balanced},
               "steps": {name: dict(counter) for name, counter in s.items()}}
    (OUT / "lineage.json").write_text(json.dumps(lineage, ensure_ascii=False, indent=1),
                                      encoding="utf-8")

    # Bundle for pipeline/test_visualisation.html. A .js file loads straight from
    # disk (file://), so the page works with a double click and no local server.
    bundle = {"lineage": lineage, "equity_gaps": res["equity_gaps"],
              "region_factor_levels": res["region_factor_levels"],
              "data_gaps": res["data_gaps"], "quarantine": ctx.quarantine,
              "imputed": [{k: r[k] for k in ("indicator_name", "region_name", "year", "value",
                                             "unit", "imputation_method", "imputation_basis")}
                          for r in res["analysis"] if r["status"] == "imputed"]}
    (OUT / "pipeline-data.js").write_text(
        "window.PIPELINE = " + json.dumps(bundle, ensure_ascii=False) + ";\n", encoding="utf-8")

    lines = ["# Pipeline run report", "",
             f"Run finished {finished.isoformat(timespec='seconds')} "
             f"({(finished - started).total_seconds():.0f} s). Analysis year {ANALYSIS_YEAR}.", "",
             "## Reconciliation", "",
             "| Rows read | Published | of which imputed | Quarantined | Out of scope | Duplicates removed | Balanced |",
             "| ---: | ---: | ---: | ---: | ---: | ---: | --- |",
             f"| {read:,} | {len(res['observations']):,} | {imputed:,} | {len(ctx.quarantine):,} | "
             f"{s['05 scope_filter']['filtered out']:,} | {s['06 deduplicate']['duplicates removed']:,} | "
             f"{'yes' if balanced else 'NO'} |", "", "## Steps", ""]
    for name, counter in s.items():
        lines.append(f"### {name}")
        lines += [f"- {key}: {value:,}" for key, value in counter.items()]
        lines.append("")
    (OUT / "run_report.md").write_text("\n".join(lines), encoding="utf-8")
    if not balanced:
        raise SystemExit(f"Reconciliation failed: read {read}, accounted for {accounted}")
