"""Write what the decision tree decided, as Markdown.

Two documents come out of one pipeline run:

    decision_tree/output/decisions.md      the full record: every rule, every question put
                                           to the tree with the rules that were checked and
                                           why each did or did not apply, and the relevance
                                           of every gap
    pipeline/output/facts/priorities.md    a short fact sheet for the document search,
                                           ordered by the three tasks of the challenge:
                                           identify the gap, locate it, recommend what to do
"""
from collections import Counter, defaultdict

from common import ROOT
from relevance import LEVEL_ORDER

DECISIONS_FILE = ROOT / "decision_tree" / "output" / "decisions.md"
BOTTLENECKS = ["late detection", "transition from primary to specialist care",
               "time from diagnosis to treatment", "none of the three"]
KIND_LABEL = {"group_gap": "Difference between population groups", "target_shortfall": "Region below the screening target",
              "regional_pattern": "Pattern between areas", "waiting_time": "Waiting time above the guidance",
              "documented_barrier": "Barrier described in strategy texts", "data_gap": "No open data"}


def _cell(value):
    """Text that is safe inside a Markdown table cell."""
    return str(value).replace("|", "/").replace("\n", " ")


def _table(header, rows):
    return ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |",
            *["| " + " | ".join(_cell(c) for c in row) + " |" for row in rows]]


def _condition(rule):
    if rule.get("otherwise"):
        return "otherwise"
    return " and ".join(f"{k} = {' or '.join(v) if isinstance(v, list) else v}" for k, v in rule["condition"].items())


def write_decisions(tree, decisions, relevance, measures, lineage):
    """The full record of one run."""
    lines = [
        "# Decision tree: rules and results of the latest run",
        "",
        f"Written by the data pipeline. Run finished {lineage['run_finished_utc']}. Rule set version "
        f"{tree['version']}. Do not edit by hand; change `decision_tree/rules.json` and run "
        "`python3 pipeline/run_pipeline.py` again.",
        "",
        "The decision tree, not the AI model, decides which measure is proposed and how relevant a gap is. "
        "Every result below can be traced to one rule. A proposal is something to evaluate, not a proven "
        "remedy: the data shows where a gap is, not what causes it.",
        "",
        "## 1. The rules",
        "",
    ]
    for name, subject in tree["subjects"].items():
        mode = ("The first matching rule decides." if subject["match"] == "first"
                else "Every matching rule applies.")
        lines += [f"### {name}", "", f"{subject['description']} {mode}", ""]
        rules = [r for r in tree["rules"] if r["subject"] == name]
        if subject.get("decides") == "relevance":
            lines += _table(["Rule", "Condition", "Relevance", "Status"],
                            [(r["rule_id"], _condition(r), r["level"], r["status"]) for r in rules])
        else:
            lines += _table(["Rule", "Condition", "Measure", "Fit", "Evidence", "Status"],
                            [(r["rule_id"], _condition(r),
                              f"{r['measure_id']} {measures[r['measure_id']]['title']}", r["fit"],
                              r["evidence_type"], r["status"]) for r in rules])
        lines += ["", "Fields: " + "; ".join(f"`{k}`: {v}" for k, v in subject["fields"].items()), ""]

    lines += ["### Relevance levels", "",
              *_table(["Level", "Meaning"], list(tree["levels"].items())), "",
              "### Thresholds", "", tree["bands"]["note"], "",
              *_table(["Band", "Large from", "Medium from", "Meaning"],
                      [(k, v["large"], v["medium"], v["meaning"]) for k, v in tree["bands"].items() if k != "note"]),
              "", "### Place in the challenge", "", tree["challenge_pathway"]["note"], "",
              *_table(["Pathway stage in the data", "Stage in the challenge", "Bottleneck"],
                      [(k or "(prevention)", v["challenge_stage"], v["bottleneck"])
                       for k, v in tree["challenge_pathway"]["stages"].items()]), ""]

    lines += ["## 2. Which measure applies: every question put to the tree", ""]
    for name in [n for n, s in tree["subjects"].items() if s.get("decides") != "relevance"]:
        asked = [d for d in decisions if d["subject"] == name]
        with_result = sum(1 for d in asked if d["measures"])
        lines += [f"### {name}", "",
                  f"{len(asked)} cases checked, {with_result} with a recommendation.", ""]
        table = []
        for d in asked:
            facts = "; ".join(f"{k} = {v or '(none)'}" for k, v in d["facts"].items())
            path = "; ".join(f"{rule} {'yes' if matched else 'no'} ({reason})" for rule, matched, reason in d["path"])
            result = ", ".join(f"{m} {measures[m]['title']}" for m in d["measures"]) or "no recommendation"
            table.append((d["case"], facts, path, result))
        lines += _table(["Case", "Facts", "Rules checked", "Result"], table) + [""]

    counts = Counter(r["relevance"] for r in relevance)
    lines += ["## 3. How relevant each gap is", "",
              f"{len(relevance)} gaps were sorted: " + ", ".join(f"{counts[l]} {l.replace('_', ' ')}" for l in LEVEL_ORDER)
              + ".", ""]
    for level in LEVEL_ORDER:
        rows = [r for r in relevance if r["relevance"] == level]
        lines += [f"### {level.replace('_', ' ').capitalize()} ({len(rows)})", "", tree["levels"][level], ""]
        lines += _table(["Rule", "Kind", "Who", "What", "Where", "Stage in the challenge", "Bottleneck",
                         "Size (points)", "People", "Year", "Measures", "Reason", "Source"],
                        [(r["rule_id"], KIND_LABEL[r["kind"]], r["group_factor"], r["problem"], r["region"],
                          r["challenge_stage"], r["bottleneck"], r["size_points"], r["reach_people"],
                          r["year"], r["measures"] or "none linked", r["reason"], r["source"]) for r in rows]) + [""]

    DECISIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    DECISIONS_FILE.write_text("\n".join(lines), encoding="utf-8")


def priorities_fact_sheet(tree, relevance, measures):
    """A short sheet for the document search, ordered by the three tasks of the challenge."""
    by_level = defaultdict(list)
    for r in relevance:
        by_level[r["relevance"]].append(r)

    def gap_line(r):
        people = f", {r['reach_people']:,} people in the disadvantaged group" if r["reach_people"] != "" else ""
        named = ", ".join(f"{m} ({measures[m]['title']})" for m in filter(None, r["measures"].split(", ")))
        measure = f" Measure to evaluate: {named}." if named else " No roadmap measure is linked."
        where = "" if r["region"] == "Finland" else f" ({r['region']})"
        return (f"- By {r['group_factor']}{where}: {r['problem']}{people}. "
                f"Pathway: {r['challenge_stage']}.{measure}")

    lines = [
        "# Which gaps matter most: priorities for decision-makers",
        "",
        "Every gap the project knows of is sorted by a fixed rule, not by an AI model. Three facts decide: "
        "how the gap is known and whether it is clearly larger than chance, how large it is, and how many "
        "people it affects. A gap is always a pair: a group of people and a result on the care pathway.",
        "",
        "## 1. Identify the gap",
        "",
        f"### High relevance ({len(by_level['high'])})",
        "",
        tree["levels"]["high"],
        "",
        *[gap_line(r) for r in by_level["high"]],
        "",
        f"### Medium relevance ({len(by_level['medium'])})",
        "",
        tree["levels"]["medium"],
        "",
        *[gap_line(r) for r in by_level["medium"] if r["kind"] in ("group_gap", "waiting_time")],
    ]
    regions = sorted({r["region"] for r in by_level["medium"] if r["kind"] == "target_shortfall"})
    if regions:
        lines.append(f"- By region of residence: {len(regions)} wellbeing services counties are at least "
                     f"{tree['bands']['size_points']['medium']} points below the 80 % screening target in at "
                     f"least one programme: {', '.join(regions)}.")
    patterns = [r for r in by_level["medium"] if r["kind"] == "regional_pattern"]
    if patterns:
        lines.append(f"- {len(patterns)} patterns between areas, for example by "
                     f"{', '.join(sorted({p['group_factor'] for p in patterns}))}. They describe areas, not people.")
    lines += [
        "",
        f"### Low relevance ({len(by_level['low'])}) and uncertain ({len(by_level['uncertain'])})",
        "",
        f"{len(by_level['low'])} gaps are measured and clearly larger than chance, but small. "
        f"{len(by_level['uncertain'])} differences could be chance or rest on a single source; most are patterns "
        "between regions for income, employment and access to primary care. They are not a basis for action "
        "on their own.",
        "",
        f"### Not measurable ({len(by_level['not_measurable'])})",
        "",
        tree["levels"]["not_measurable"],
        "",
        *[f"- {r['problem']} (pathway: {r['challenge_stage']})" for r in by_level["not_measurable"]],
        "",
        "## 2. Locate the gap in the care pathway",
        "",
        "The challenge names three bottlenecks. This is how the gaps are spread over them:",
        "",
    ]
    table = []
    for b in BOTTLENECKS:
        rows = [r for r in relevance if r["bottleneck"] == b]
        c = Counter(r["relevance"] for r in rows)
        table.append((b.capitalize(), c["high"], c["medium"], c["low"], c["uncertain"], c["not_measurable"]))
    lines += _table(["Bottleneck", "High", "Medium", "Low", "Uncertain", "Not measurable"], table)
    measured_late = sum(1 for r in relevance if r["bottleneck"] == "late detection" and r["relevance"] in ("high", "medium"))
    lines += [
        "",
        f"- Late detection is where the open data is strong: {measured_late} gaps of high or medium relevance, all "
        "in screening participation and in the follow-up examination after a positive screening test.",
        "- For the transition from primary to specialist care and for the time from diagnosis to treatment, "
        "no open data compares regions or groups. What exists are single figures from hospitals and one study "
        "and barriers described in strategy texts. These bottlenecks may be large; they can not be ranked.",
        "",
        "## 3. Recommend what to do",
        "",
        "In this order:",
        "",
    ]
    # Measures are ordered by the gaps they address: first by the number of gaps of high
    # relevance, then by the number of medium relevance.
    high, medium = Counter(), Counter()
    for level, counter in (("high", high), ("medium", medium)):
        for r in by_level[level]:
            counter.update(filter(None, r["measures"].split(", ")))
    step = 1
    for m in sorted(set(high) | set(medium), key=lambda m: (-high[m], -medium[m], m)):
        if m == "3.1.2":
            continue
        x = measures[m]
        cost = f"{float(x['cost_eur']):,.0f} euros, {x['cost_note']}" if x["cost_eur"] else x["cost_note"]
        lines.append(f"{step}. Measure {m}, {x['title']}: addresses {high[m]} gaps of high and {medium[m]} of "
                     f"medium relevance. Cost: {cost}. Success is measured by: {x['kpi']}. "
                     f"Source: Implementation Roadmap 2026-2031, p. {x['roadmap_page']}.")
        step += 1
    x = measures["3.1.2"]
    lines += [
        f"{step}. Measure 3.1.2, {x['title']}: makes the two bottlenecks without data measurable. "
        f"Cost: {float(x['cost_eur']):,.0f} euros, {x['cost_note']}. Success is measured by: {x['kpi']}. "
        f"Source: Implementation Roadmap 2026-2031, p. {x['roadmap_page']}.",
        "",
        "Barriers described in strategy texts (costs to patients, distance to the treating unit, health literacy, "
        "faster access through occupational health care) have no roadmap measure linked to them in this project.",
        "",
        "The full record, with the rule behind every line, is in `decision_tree/output/decisions.md`.",
    ]
    return "\n".join(lines) + "\n"
