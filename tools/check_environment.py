#!/usr/bin/env python3
"""Check that the fictional environment matches the scope record.

  - every resource in environment/iac-plan.json has a `scope` ID that exists in mas/mas-record.json
  - every in-scope machine-based resource in the record is implemented by at least one IaC resource
  - every `scope` ID used in environment/live-state.json exists in the record
  - every data flow in the record has an observed TLS measurement in live-state.json

Exit status is non-zero on any problem.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
load = lambda p: json.loads((ROOT / p).read_text())


def scopes(o):
    if isinstance(o, dict):
        if "scope" in o and isinstance(o["scope"], str):
            yield o["scope"]
        for v in o.values():
            yield from scopes(v)
    elif isinstance(o, list):
        for v in o:
            yield from scopes(v)


def main() -> int:
    rec, iac, live = load("mas/mas-record.json"), load("environment/iac-plan.json"), load("environment/live-state.json")
    ids = {r["id"] for r in rec["information_resources"]}
    need = {r["id"] for r in rec["information_resources"] if r["decision"] == "in_scope" and r["kind"] == "machine_based"}
    problems = []
    declared = {r.get("scope") for r in iac["resources"]}
    for r in iac["resources"]:
        if not r.get("scope"):
            problems.append(f"IaC resource {r['type']}.{r['name']} has no scope ID")
        elif r["scope"] not in ids:
            problems.append(f"IaC resource {r['type']}.{r['name']} uses unknown scope ID {r['scope']}")
    for m in sorted(need - declared):
        problems.append(f"in-scope resource {m} is implemented by no IaC resource")
    for s in sorted(set(scopes(live)) - ids):
        problems.append(f"live-state uses unknown scope ID {s}")
    seen = {o["flow"] for o in live.get("flow_tls", [])}
    for f in rec["information_flows"]:
        if f["type"] == "data" and f["id"] not in seen:
            problems.append(f"data flow {f['id']} has no observed TLS measurement")
    for p in problems:
        print("ERROR:", p)
    print("environment matches the scope record" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
