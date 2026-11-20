#!/usr/bin/env python3
"""Check evidence/latest.json against its schema and against the roll-up rules.

  - the file follows schemas/validation-result.schema.json
  - the summary counts equal the counts of KSI statuses
  - a KSI marked pass has at least two methods, all passing, and no coverage gap (FRC-CSX-VVK)
  - every KSI in the registry appears once
"""
import json
import sys
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    latest = json.loads((ROOT / "evidence/latest.json").read_text())
    schema = json.loads((ROOT / "schemas/validation-result.schema.json").read_text())
    registry = json.loads((ROOT / "evidence/ksi-registry.json").read_text())
    problems = [f"schema: {'/'.join(map(str, e.absolute_path))}: {e.message}" for e in Draft202012Validator(schema).iter_errors(latest)]
    counts = Counter(k["status"] for k in latest["ksis"])
    for key in ("pass", "partial", "fail", "not_implemented"):
        if latest["summary"][key] != counts.get(key, 0):
            problems.append(f"summary.{key} is {latest['summary'][key]} but {counts.get(key, 0)} KSIs have that status")
    ids = [k["id"] for k in latest["ksis"]]
    if sorted(ids) != sorted(k["id"] for k in registry["indicators"]) or len(ids) != len(set(ids)):
        problems.append("KSIs in latest.json do not match the registry one for one")
    for k in latest["ksis"]:
        if k["status"] == "pass":
            if len(k["methods"]) < 2:
                problems.append(f"{k['id']}: pass with fewer than 2 methods")
            if any(m["status"] != "pass" for m in k["methods"]):
                problems.append(f"{k['id']}: pass with a method that did not pass")
            if k["coverage_gap"]:
                problems.append(f"{k['id']}: pass with a known coverage gap")
        if k["status"] == "not_implemented" and k["methods"]:
            problems.append(f"{k['id']}: not_implemented but has methods")
    for p in problems:
        print("PROBLEM:", p, file=sys.stderr)
    print("evidence is valid" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
