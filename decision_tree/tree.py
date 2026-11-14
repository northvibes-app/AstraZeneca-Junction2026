"""Decision tree: evaluate the rules in rules.json against a set of facts.

The rules are data, not code, so that the pipeline, the API and a human reviewer all
read the same file. This module is the only place where they are evaluated.

How a decision is taken
    A "subject" is the kind of thing being decided about, for example a gap between
    two population groups or a region below the screening target. A "fact" describes
    one such thing as a set of fields, for example
        {"indicator_family": "screening_participation", "factor": "language", "robust": "yes"}
    The rules of the subject are checked in the order they appear in the file:
      - a rule matches when every field in its condition has the stated value
        (a list means: any of these values);
      - subject match "first": the first matching rule decides, the rest are skipped;
      - subject match "all":   every matching rule gives a recommendation;
      - a rule marked "otherwise" applies only when no rule before it matched.
    Only rules with status "active" are used.

Use from Python
    from tree import load_rules, decide
    fired, path = decide(load_rules(), "region_below_target", {"language_level": "disadvantaged", ...})
    "fired" lists the rules that apply, with their trigger text filled in.
    "path" lists every rule that was checked and why it did or did not apply.

Use from the command line
    python3 decision_tree/tree.py                       # print all rules as a tree
    python3 decision_tree/tree.py region_below_target language_level=disadvantaged education_level=middle

Only the Python standard library is used.
"""
import json
import sys
from pathlib import Path

RULES_FILE = Path(__file__).resolve().parent / "rules.json"
STATUSES = ("active", "draft", "retired")
REQUIRED = ("rule_id", "subject", "condition", "evidence_reference", "version", "status")
# A subject decides one of two things, and its rules must carry the matching fields.
DECIDES = {"measure": ("measure_id", "fit", "evidence_type", "trigger"),   # which roadmap measure applies
           "relevance": ("level", "reason")}                               # how relevant a gap is


def load_rules(path=RULES_FILE, known_measures=None):
    """Read and check the rule file. Stops with a clear message if a rule is malformed."""
    tree = json.loads(Path(path).read_text(encoding="utf-8"))
    seen = set()
    for rule in tree["rules"]:
        name = rule.get("rule_id", "?")
        missing = [f for f in REQUIRED if f not in rule]
        if missing:
            raise ValueError(f"Rule {name}: missing {', '.join(missing)}")
        if name in seen:
            raise ValueError(f"Rule {name}: the rule_id is used twice")
        seen.add(name)
        if rule["subject"] not in tree["subjects"]:
            raise ValueError(f"Rule {name}: unknown subject '{rule['subject']}'")
        decides = tree["subjects"][rule["subject"]].get("decides", "measure")
        if decides not in DECIDES:
            raise ValueError(f"Subject {rule['subject']}: decides must be one of {', '.join(DECIDES)}")
        missing = [f for f in DECIDES[decides] if f not in rule]
        if missing:
            raise ValueError(f"Rule {name}: missing {', '.join(missing)}")
        if decides == "relevance" and rule["level"] not in tree.get("levels", {}):
            raise ValueError(f"Rule {name}: unknown level '{rule['level']}'")
        if rule["status"] not in STATUSES:
            raise ValueError(f"Rule {name}: status must be one of {', '.join(STATUSES)}")
        unknown = set(rule["condition"]) - set(tree["subjects"][rule["subject"]]["fields"])
        if unknown:
            raise ValueError(f"Rule {name}: condition uses unknown fields {', '.join(sorted(unknown))}")
        if not rule["condition"] and not rule.get("otherwise"):
            raise ValueError(f"Rule {name}: an empty condition is only allowed with \"otherwise\": true")
        if known_measures is not None and decides == "measure" and rule["measure_id"] not in known_measures:
            raise ValueError(f"Rule {name}: measure {rule['measure_id']} is not in measures.csv")
    for name, subject in tree["subjects"].items():
        if subject["match"] not in ("first", "all"):
            raise ValueError(f"Subject {name}: match must be 'first' or 'all'")
    return tree


def _mismatch(condition, fact):
    """Return the first reason the condition is not met, or None if it is met."""
    for field, wanted in condition.items():
        allowed = wanted if isinstance(wanted, list) else [wanted]
        if fact.get(field) not in allowed:
            return f"{field} is '{fact.get(field, '')}', needs {' or '.join(map(str, allowed))}"
    return None


def decide(tree, subject, fact):
    """Apply the rules of one subject to one fact. Returns (fired, path)."""
    if subject not in tree["subjects"]:
        raise ValueError(f"Unknown subject '{subject}'")
    first_only = tree["subjects"][subject]["match"] == "first"
    fired, path = [], []
    for rule in tree["rules"]:
        if rule["subject"] != subject or rule["status"] != "active":
            continue
        if first_only and fired:
            path.append((rule["rule_id"], False, "skipped, an earlier rule already decided"))
            continue
        if rule.get("otherwise") and fired:
            path.append((rule["rule_id"], False, "not needed, an earlier rule applied"))
            continue
        reason = _mismatch(rule["condition"], fact)
        if reason:
            path.append((rule["rule_id"], False, reason))
            continue
        path.append((rule["rule_id"], True,
                     "no earlier rule applied" if rule.get("otherwise") else "condition met"))
        # Fields that are missing from the fact stay visible as {name} instead of failing.
        text = rule.get("trigger", rule.get("reason", "")).format_map(_Keep(fact))
        fired.append({"rule": rule, "trigger": text})
    return fired, path


def band(tree, name, value):
    """Turn a number into 'large', 'medium' or 'small' using the thresholds in rules.json.

    name is 'size_points' or 'reach_people'. A missing value gives 'unknown'.
    """
    if value is None or value == "":
        return "unknown"
    limits, value = tree["bands"][name], abs(float(value))
    return "large" if value >= limits["large"] else "medium" if value >= limits["medium"] else "small"


def challenge_position(tree, pathway_stage):
    """Where a pathway stage sits in the challenge: (stage of the challenge, bottleneck)."""
    entry = tree["challenge_pathway"]["stages"].get(pathway_stage or "")
    if entry is None:
        raise ValueError(f"Pathway stage '{pathway_stage}' has no place in challenge_pathway (rules.json)")
    return entry["challenge_stage"], entry["bottleneck"]


class _Keep(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def describe(tree):
    """The whole rule set as indented text, one block per subject."""
    lines = [f"Decision rules, version {tree['version']}"]
    for name, subject in tree["subjects"].items():
        mode = "the first matching rule decides" if subject["match"] == "first" else "every matching rule applies"
        lines += ["", f"{name}: {subject['description']}", f"  ({mode})"]
        for rule in tree["rules"]:
            if rule["subject"] != name:
                continue
            condition = " and ".join(
                f"{k} = {' or '.join(v) if isinstance(v, list) else v}" for k, v in rule["condition"].items())
            if rule.get("otherwise"):
                condition = "otherwise"
            state = "" if rule["status"] == "active" else f"  [{rule['status']}]"
            lines.append(f"  {rule['rule_id']:3} {condition}")
            result = (f"relevance: {rule['level']}" if "level" in rule
                      else f"measure {rule['measure_id']} ({rule['fit']}, evidence {rule['evidence_type']})")
            lines.append(f"        -> {result}{state}")
    return "\n".join(lines)


def main(arguments):
    tree = load_rules()
    if not arguments:
        print(describe(tree))
        return 0
    subject, fact = arguments[0], dict(a.split("=", 1) for a in arguments[1:] if "=" in a)
    try:
        fired, path = decide(tree, subject, fact)
    except ValueError as error:
        print(f"{error}. Subjects: {', '.join(tree['subjects'])}")
        return 1
    for rule_id, matched, reason in path:
        print(f"  {'yes' if matched else 'no ':3} {rule_id}: {reason}")
    if not fired:
        print("Result: no rule applies, no recommendation.")
    for hit in fired:
        rule = hit["rule"]
        what = f"relevance {rule['level']}" if "level" in rule else f"measure {rule['measure_id']} ({rule['fit']})"
        print(f"Result: {what} by rule {rule['rule_id']} - {hit['trigger']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
