"""Step 18: PUBLISH

Write all outputs, the lineage record and the run report.

The step fails if any input row is unaccounted for.
"""
import csv
import gzip
import json
import shutil
from collections import defaultdict
from datetime import datetime, timezone

from common import ANALYSIS_YEAR, OBS_COLUMNS, OUT, REF, SCREENING_TARGET, write_csv

from .s14_measure import GAP_COLUMNS

FACTOR_LABEL = {"income": "lower income", "employment": "unemployment", "education": "lower education",
                "language": "language barrier", "smoking": "smoking",
                "primary_care_access": "slow access to primary care", "sex": "sex"}


def _write_facts(ctx):
    """Plain-language fact sheets for document search (RAG).

    A language model retrieves and reads text far better than rows of a CSV file.
    Each sheet is short, self-contained and names its sources, so a retrieved
    passage can be quoted with its origin.
    """
    res, ref = ctx.results, ctx.ref
    facts = OUT / "facts"
    if facts.exists():
        shutil.rmtree(facts)          # sheets of regions that no longer exist must not linger
    facts.mkdir(parents=True)
    footer = ("\nSources: Finnish Cancer Registry, Statistics Finland and THL via Sotkanet, processed by "
              "the Equal Care Navigator data pipeline. Regional differences are unadjusted and do not "
              "show causes.\n")

    stats = defaultdict(list)
    for s in res["outcome_stats"]:
        if s["sex"] == "total" and not s["factor"]:
            stats[s["region_code"]].append(s)
    # Rank of each region per indicator, 1 = best.
    rank = {}
    by_indicator = defaultdict(list)
    for code, items in stats.items():
        if code != "FI":
            for s in items:
                by_indicator[s["indicator_key"]].append(s)
    for key, items in by_indicator.items():
        better = ref.indicator_by_key[key]["higher_is"] == "better"
        for s in items:
            ahead = sum(1 for o in items if (o["value"] > s["value"] if better else o["value"] < s["value"]))
            rank[(s["region_code"], key)] = (ahead + 1, len(items))
    levels = defaultdict(list)
    for r in res["region_factor_levels"]:
        levels[r["region_code"]].append(r)
    recs = defaultdict(list)
    for r in res["recommendations"]:
        recs[r["region_code"]].append(r)

    def rec_lines(items):
        lines = []
        for r in items:
            cost = f"{int(r['cost_eur']):,} euros ({r['cost_note']})" if r["cost_eur"] else r["cost_note"]
            lines.append(f"- Measure {r['measure_id']}, {r['measure']} ({r['fit']}). Why: {r['trigger']}. "
                         f"Cost: {cost}. Success is measured by: {r['success_kpi']}. {r['source']}.")
        return lines

    for region in ref.counties:
        code, name = region["region_code"], region["name_en"]
        lines = [f"# {name}: cancer equity profile", "",
                 f"{name} is one of Finland's 22 wellbeing services regions.", "",
                 "## Outcomes"]
        for s in sorted(stats[code], key=lambda s: s["indicator_key"]):
            position, of = rank[(code, s["indicator_key"])]
            text = f"- {s['indicator_name']} {s['year']}: {s['value']}"
            text += " %" if s["unit"] == "percent" else ""
            if s["ci_low"] != "":
                text += f" (95 % confidence interval {s['ci_low']} to {s['ci_high']})"
            text += f", rank {position} of {of} regions where 1 is best"
            if s["target_status"]:
                text += f", {s['target_status'].replace('_', ' ')} against the {SCREENING_TARGET} % target"
            lines.append(text + ".")
        lines += ["", "## Equity factors"]
        for r in levels[code]:
            lines.append(f"- {r['factor_label']}: {r['context_indicator'].replace('_', ' ')} "
                         f"{r['context_value']} in {r['context_year']} (Finland {r['national_value']}); "
                         f"{r['factor_level']} third of regions, {r['vs_national'].replace('_', ' ')}.")
        lines += ["", "## Measures to evaluate"]
        lines += rec_lines(recs[code]) or ["- No region-specific measure is triggered by the data."]
        (facts / f"region_{code}_{name.lower().replace(' ', '_')}.md").write_text(
            "\n".join(lines) + "\n" + footer, encoding="utf-8")

    # National gaps between groups, newest year per indicator and factor.
    newest = {}
    for g in res["equity_gaps"]:
        if g["evidence_type"] == "A" and g["region_code"] == "FI":
            k = (g["indicator_key"], g["factor"])
            if k not in newest or g["year"] > newest[k]["year"]:
                newest[k] = g
    lines = ["# Equity gaps in Finnish cancer screening and care", "",
             "## Gaps measured directly between population groups"]
    for g in sorted(newest.values(), key=lambda g: -g["gap"]):
        text = (f"- {g['indicator_name']} {g['year']} by {FACTOR_LABEL.get(g['factor'], g['factor'])}: "
                f"{g['worse_value']} % in the group '{g['worse_group'].replace('_', ' ')}' against "
                f"{g['better_value']} % in '{g['better_group'].replace('_', ' ')}', a gap of {g['gap']} points")
        if g["gap_ci_low"] != "":
            text += f" (95 % confidence interval {g['gap_ci_low']} to {g['gap_ci_high']})"
        if g["potential_additional"] != "":
            text += (f". The worse-off group has {g['people_in_worse_group']:,} people; "
                     f"{g['potential_additional']:,} more would take part at the level of the best group")
        lines.append(text + f". Status: {g['status']}.")
    lines += ["", "## Patterns between regions that survive correction for multiple comparisons"]
    robust = [g for g in res["equity_gaps"] if g["evidence_type"].startswith("B") and g["robust"] == "yes"]
    for g in robust:
        lines.append(f"- {FACTOR_LABEL.get(g['factor'], g['factor']).capitalize()} and {g['indicator_name']} "
                     f"across {g['region']}: rank correlation {g['spearman_rho']}, adjusted p-value "
                     f"{g['p_adjusted']}. {g['worse_group']} {g['worse_value']}, {g['better_group']} {g['better_value']}.")
    if not robust:
        lines.append("- None.")
    lines += ["", "## Barriers documented in the national roadmap but not measured"]
    for g in res["equity_gaps"]:
        if g["evidence_type"] == "C":
            lines.append(f"- {g['factor'].replace('_', ' ').capitalize()}: {g['note']} ({g['source_url']}).")
    (facts / "equity_gaps.md").write_text("\n".join(lines) + "\n" + footer, encoding="utf-8")

    lines = ["# Measures to evaluate, nationally", ""] + rec_lines(recs["FI"])
    (facts / "recommendations_national.md").write_text("\n".join(lines) + "\n" + footer, encoding="utf-8")

    lines = ["# What the open data cannot show", "",
             "No open, comparable data exists for the following. The pipeline reports these as "
             "gaps and never fills them with estimates.", ""]
    lines += [f"- {g['pathway_stage'].replace('_', ' ').capitalize()}: {g['description']}"
              for g in res["data_gaps"] if g["gap_type"] == "no_open_data"]
    (facts / "data_gaps.md").write_text("\n".join(lines) + "\n" + footer, encoding="utf-8")
    # Goal 3 fact sheet, written from pipeline/reference/goal3_targets.csv (single source of truth).
    g3 = load_goal3_targets()
    lines = ["# Goal 3: equal and effective cancer treatment", "",
             "Goal 3 of the National Cancer Strategy 2026-2035 asks for better survival, lower cancer "
             "mortality and treatment within target times. No open data shows time from diagnosis to "
             "treatment start by region, so that indicator cannot be measured here.", "",
             "Targets and baselines set by the strategy:", ""]
    for r in g3:
        value = f"{r['target_value']} {r['unit'].replace('_', ' ')}" if r["target_value"] else "no numeric target"
        lines.append(f"- Goal {r['goal']}, {r['indicator'].replace('_', ' ')}: {value} ({r['source']}, p. {r['page']}). {r['note']}.")
    deaths = [x for x in res["national_trends"] if x["cancer_site"].startswith("All cancers")]
    if deaths:
        lines += ["", "Observed cancer deaths per year, all cancers:", ""]
        lines += [f"- {x['year']}: {x['deaths']}" for x in deaths]
    (facts / "goal3.md").write_text("\n".join(lines) + "\n" + footer, encoding="utf-8")
    ctx.count("18 publish", "fact sheets written", len(list(facts.glob("*.md"))))


def load_goal3_targets():
    """Strategy targets typed once, in a CSV, with page numbers."""
    with open(REF / "goal3_targets.csv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def publish(ctx, started):
    """Write every output and a run report, and check that no row went missing."""
    step, res = "18 publish", ctx.results
    OUT.mkdir(parents=True, exist_ok=True)

    # Clean layer: every observation that passed all checks (compressed, it is large).
    with gzip.open(OUT / "observations_clean.csv.gz", "wt", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OBS_COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(res["observations"])
    write_csv(OUT / "observations_analysis.csv", res["analysis"], OBS_COLUMNS)
    write_csv(OUT / "outcome_stats.csv", res["outcome_stats"])
    write_csv(OUT / "region_profile.csv", res["region_profile"])
    write_csv(OUT / "region_factor_levels.csv", res["region_factor_levels"])
    write_csv(OUT / "observations_by_factor.csv", res["observations_by_factor"])
    write_csv(OUT / "equity_gaps.csv", res["equity_gaps"], GAP_COLUMNS)
    write_csv(OUT / "recommendations.csv", res["recommendations"])
    write_csv(OUT / "national_trends.csv", res["national_trends"])
    write_csv(OUT / "treatment_entitlements_by_region.csv", res["treatment_entitlements"])
    write_csv(OUT / "data_gaps.csv", res["data_gaps"])
    write_csv(OUT / "changes_since_last_run.csv", res["run_changes"],
              ["change", "indicator_key", "region_code", "period", "sex", "age_group", "detail",
               "measure", "factor", "factor_level", "previous_value", "new_value"])
    write_csv(OUT / "quarantine.csv", ctx.quarantine,
              ["step", "reason", "source_file", "source_row", "source", "indicator", "year",
               "region", "value"])
    (OUT / "profile.json").write_text(json.dumps(res["profile"], ensure_ascii=False, indent=1),
                                      encoding="utf-8")
    _write_facts(ctx)

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

    # Latest observed figure per region and indicator, for the region map page.
    latest, catalogue = res["latest_year"], ctx.ref.indicator_by_key
    region_facts = [
        {"region_code": r["region_code"], "region_name": r["region_name"],
         "indicator_key": r["indicator_key"], "indicator_name": r["indicator_name"],
         "kind": r["kind"], "pathway_stage": r["pathway_stage"],
         "higher_is": catalogue[r["indicator_key"]]["higher_is"], "sex": r["sex"],
         "year": r["year"], "value": r["value"], "unit": r["unit"], "flags": r["flags"],
         "ci_low": res["stats_by_id"].get(r["observation_id"], {}).get("ci_low", ""),
         "ci_high": res["stats_by_id"].get(r["observation_id"], {}).get("ci_high", ""),
         "target_status": res["stats_by_id"].get(r["observation_id"], {}).get("target_status", ""),
         "source_url": r["source_url"]}
        for r in res["analysis"]
        if r["kind"] in ("outcome", "context") and r["factor"] == "" and r["status"] != "imputed"
        and r["year"] == latest.get(r["indicator_key"])]
    indicator_sources = {}
    for r in res["analysis"]:
        if r["source_url"] and r["sex"] == "total" and r["factor"] == "":
            indicator_sources.setdefault(r["indicator_key"], r["source_url"])

    # Bundle for pipeline/test_visualisation.html and pipeline/region_map.html. A .js file
    # loads straight from disk (file://), so the pages work with a double click.
    bundle = {"lineage": lineage, "region_facts": region_facts,
              "indicator_sources": indicator_sources, "equity_gaps": res["equity_gaps"],
              "recommendations": res["recommendations"],
              "region_factor_levels": res["region_factor_levels"],
              "data_gaps": res["data_gaps"], "quarantine": ctx.quarantine,
              "goal3_targets": load_goal3_targets(), "national_trends": res["national_trends"],
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
