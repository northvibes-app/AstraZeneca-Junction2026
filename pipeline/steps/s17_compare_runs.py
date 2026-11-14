"""Step 17: COMPARE RUNS

Report what changed in the analysis figures since the previous pipeline run.
"""
import csv

from common import OUT

KEY = ["indicator_key", "region_code", "period", "sex", "age_group", "detail", "measure",
       "factor", "factor_level"]


def compare_runs(ctx):
    """Compare this run's analysis figures with the file the previous run left behind.

    Sources revise their figures. Without this step a changed number would simply
    replace the old one unnoticed. The comparison lists every figure that is new,
    gone or different, so a revision can be checked before it reaches a presentation.
    """
    step = "17 compare_runs"
    previous_file, changes = OUT / "observations_analysis.csv", []
    if not previous_file.exists():
        ctx.count(step, "no previous run to compare with")
        ctx.results["run_changes"] = changes
        return
    with open(previous_file, encoding="utf-8", newline="") as f:
        previous = {tuple(row[k] for k in KEY): row["value"] for row in csv.DictReader(f)}
    current = {tuple(str(r[k]) for k in KEY): r["value"] for r in ctx.results["analysis"]}

    def record(kind, key, old, new):
        changes.append(dict(zip(KEY, key), change=kind, previous_value=old, new_value=new))
        ctx.count(step, f"figures {kind}")

    for key, value in current.items():
        if key not in previous:
            record("added", key, "", value)
        elif abs(float(previous[key]) - value) > 1e-9:
            record("changed", key, previous[key], value)
    for key, value in previous.items():
        if key not in current:
            record("removed", key, value, "")
    ctx.count(step, "figures unchanged", len(current) - sum(1 for c in changes if c["change"] != "removed"))
    ctx.results["run_changes"] = changes
