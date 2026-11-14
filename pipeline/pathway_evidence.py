"""Waiting times on the care pathway: what is known, and how strong each figure is.

The open statistics contain no waiting times by region or population group. That gap
stays a gap. What does exist are single figures: legal limits, national targets,
numbers published by individual hospitals, one study, and statements by private
providers. They are collected by hand in research/finland_cancer_waiting_times.csv.

This module reads that file and sorts every line by how much it can carry:

    legal_limit         maximum set by law                       usable as a yardstick
    target              national target or guidance, not binding usable as a yardstick
    measured            average or median published by a
                        hospital or a study                      usable as evidence
    provider_statement  description or marketing claim           NOT evidence
    single_case         one patient's story                      NOT evidence
    no_data             the provider publishes nothing           NOT evidence

Nothing is estimated or filled in. Lines that are not evidence are kept and labelled,
so that a reader sees they were considered and why they do not count.
"""
import csv
import hashlib

from common import CONFIG, ROOT

SOURCE_FILE = ROOT / CONFIG["inputs"]["pathway_evidence"]

# The file's stage names, translated to the stage names used everywhere else in the pipeline.
STAGES = {"before appointment": "first_contact", "appointment": "referral", "diagnostics": "diagnosis",
          "treatment": "treatment_start", "whole pathway": "whole_pathway"}
USABLE = ("legal_limit", "target", "measured")
COLUMNS = ["sector", "provider", "cancer_type", "pathway_stage", "measure", "days_min", "days_max",
           "wait_as_stated", "data_period", "kind", "usable_as_evidence", "against_guidance",
           "notes", "source_url"]


def parse_days(text):
    """'28' -> (28, 28); '28-42' -> (28, 42); '' -> (None, None)."""
    parts = [p.strip() for p in (text or "").split("-") if p.strip()]
    try:
        numbers = [int(p) for p in parts]
    except ValueError:
        return None, None
    if not numbers or len(numbers) > 2:
        return None, None
    return numbers[0], numbers[-1]


def kind_of(evidence_type):
    """Sort the free-text description of a line into one of six kinds."""
    text = (evidence_type or "").lower()
    if text.startswith("statutory"):
        return "legal_limit"
    if text.startswith("national target"):
        return "target"
    if text.startswith("measured"):
        return "measured"
    if text.startswith("single patient"):
        return "single_case"
    if text.startswith("no data"):
        return "no_data"
    return "provider_statement"


def load_waiting_times():
    """Read the research file. Returns (rows, manifest entry); ([], None) if the file is missing."""
    if not SOURCE_FILE.exists():
        return [], None
    raw_bytes = SOURCE_FILE.read_bytes()
    with open(SOURCE_FILE, encoding="utf-8-sig", newline="") as f:
        raw = list(csv.DictReader(f))
    rows = []
    for r in raw:
        low, high = parse_days(r["wait_days"])
        kind = kind_of(r["evidence_type"])
        rows.append({"sector": r["sector"].strip().lower(), "provider": r["provider"].strip(),
                     "cancer_type": r["cancer_type"].strip(),
                     "pathway_stage": STAGES.get(r["pathway_stage"].strip().lower(), "unknown"),
                     "measure": r["measure"].strip(), "days_min": low, "days_max": high,
                     "wait_as_stated": r["wait_as_stated"].strip(), "data_period": r["data_period"].strip(),
                     "kind": kind,
                     # A figure counts only if its kind is usable AND it actually states a number of days.
                     "usable_as_evidence": "yes" if kind in USABLE and low is not None else "no",
                     "against_guidance": "", "notes": r["notes"].strip(), "source_url": r["source_url"].strip()})
    _compare_with_guidance(rows)
    manifest = {"file": str(SOURCE_FILE.relative_to(ROOT)), "rows": len(rows), "bytes": len(raw_bytes),
                "sha256": hashlib.sha256(raw_bytes).hexdigest()}
    return rows, manifest


def _compare_with_guidance(rows):
    """Mark measured times from referral to first treatment as within or above the national guidance.

    Only figures that measure the same span as the guidance are compared: from the
    referral reaching specialised care to the first treatment. Everything else stays blank.
    """
    guidance = next((r for r in rows if r["kind"] == "target" and r["days_max"] is not None
                     and r["measure"].lower().startswith("referral arrival to first treatment")), None)
    if not guidance:
        return
    limit = guidance["days_max"]
    for r in rows:
        measure = r["measure"].lower()
        same_span = (measure.startswith("referral arrival to first surgery")
                     or measure.startswith("referral arrival to first drug treatment")
                     or measure.startswith("time in specialised care before treatment"))
        if r["kind"] == "measured" and r["pathway_stage"] == "treatment_start" and same_span:
            r["against_guidance"] = (f"within the {limit}-day guidance" if r["days_max"] <= limit
                                     else f"above the {limit}-day guidance")


def fact_sheet(rows):
    """Plain-language summary for the document search."""
    def days(r):
        if r["days_min"] is None:
            return "no number of days stated"
        return f"{r['days_min']} days" if r["days_min"] == r["days_max"] else f"{r['days_min']}-{r['days_max']} days"

    def entry(r):
        extra = f" ({r['against_guidance']})" if r["against_guidance"] else ""
        note = f" Note: {r['notes']}." if r["notes"] else ""
        return (f"- {r['provider']}, {r['cancer_type'].lower()}: {r['measure'].lower()}: {days(r)}{extra}. "
                f"Period: {r['data_period']}.{note} Source: {r['source_url']}")

    by_kind = lambda *kinds: [r for r in rows if r["kind"] in kinds]
    compared = [r for r in rows if r["against_guidance"]]
    above = [r for r in compared if r["against_guidance"].startswith("above")]
    lines = [
        "# Waiting times on the cancer care pathway: what is known",
        "",
        "No open statistics show waiting times from referral to diagnosis and treatment by region or by "
        "population group. That remains a data gap. This sheet lists the single figures that do exist and "
        "says how much each one can carry. None of them allows a comparison between regions or groups.",
        "",
        "## Limits set by law and national targets",
        "",
        "These are yardsticks, not measurements.",
        "",
        *[entry(r) for r in by_kind("legal_limit", "target")],
        "",
        "## Measured by a hospital or a study",
        "",
        "Each figure covers one hospital or one study. An average or a median hides the longest waits.",
        "",
        *[entry(r) for r in by_kind("measured")],
        "",
    ]
    if compared:
        lines += [f"Of {len(compared)} measured times from referral to first treatment, {len(above)} "
                  f"{'is' if len(above) == 1 else 'are'} above the national guidance and "
                  f"{len(compared) - len(above)} within it. The guidance figure itself was taken from a "
                  "summary and has not been checked against the original document.", ""]
    lines += [
        "## Not usable as evidence",
        "",
        "Statements by providers, a single patient's case and providers that publish nothing. Listed so "
        "that it is clear they were looked at.",
        "",
        *[entry(r) for r in by_kind("provider_statement", "single_case", "no_data")],
        "",
        "## What follows from this",
        "",
        "- Public hospitals that publish figures report short waits for breast cancer and for the oncology clinic.",
        "- The one study that follows patients from first symptoms shows that most of the delay can lie before "
        "specialised care: with the patient and in primary care.",
        "- Private providers state waits of days, but as claims without statistics. A difference between public "
        "and private access is plausible and is not measured.",
        "- Whether waits differ by region, income, education or language can not be answered with open data. "
        "Roadmap measure 3.1.2 (national care pathways with public monitoring) addresses exactly this.",
    ]
    return "\n".join(lines) + "\n"
