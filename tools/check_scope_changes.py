#!/usr/bin/env python3
"""Check that every change to the scope record has an entry in mas/scope-changes.json.

The log stores a fingerprint of the scope after each change. The newest entry's
fingerprint must equal the fingerprint of the current record. When they differ,
the scope changed without a log entry (rule SCN-CSO-MAR, auditable evaluation
records). Run with --print to show the current fingerprint when you add an entry.

The fingerprint covers what defines the boundary: each resource's id, decision,
zone and kind, each flow's id, endpoints and data classes, the prohibited flows,
the third-party resources and the conditional exclusions.

Fingerprint methods:
  1  conditions recorded only as the IDs of resources that have conditions. It could not
     see a change to a condition's text or evidence (issue #38).
  2  every condition's ID, text and evidence, so any edit to a condition changes the fingerprint.

A change of method is not a scope change, so it is recorded in the log's "rebaselines" list and
not as an entry. A rebaseline names the entry it follows and gives the fingerprint of the record
under the old method (which must equal that entry's fingerprint, so no scope change is hidden)
and under the new method. Entries after a rebaseline use the new method.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TYPES = {"added", "removed", "moved", "decision_changed", "condition_changed", "flow_changed", "other"}
SCN = {"routine", "adaptive", "transformative", "not_significant"}


CURRENT_METHOD = 2


def _conditions_v1(rec: dict) -> list:
    return (sorted((r["id"], c) for r in rec["information_resources"] for c in (r.get("conditions") or [])
                   if isinstance(c, str)) or sorted(r["id"] for r in rec["information_resources"] if r.get("conditions")))


def _conditions_v2(rec: dict) -> list:
    out = []
    for r in rec["information_resources"]:
        for c in r.get("conditions") or []:
            if isinstance(c, dict):
                out.append((r["id"], c.get("id"), c.get("text"), c.get("evidence")))
            else:
                out.append((r["id"], None, c, None))
    return sorted(out, key=lambda x: tuple("" if v is None else str(v) for v in x))


def fingerprint(rec: dict, method: int = CURRENT_METHOD) -> str:
    if method not in (1, 2):
        raise ValueError(f"unknown fingerprint method {method}")
    core = {
        "resources": sorted((r["id"], r["decision"], r["zone"], r["kind"]) for r in rec["information_resources"]),
        "flows": sorted((f["id"], f["source"], f["destination"], tuple(f["data_classes"])) for f in rec["information_flows"]),
        "prohibited": sorted(f["id"] for f in rec["prohibited_flows"]),
        "tpr": sorted(t["id"] for t in rec["third_party_resources"]),
        "conditions": _conditions_v1(rec) if method == 1 else _conditions_v2(rec),
    }
    return hashlib.sha256(json.dumps(core, sort_keys=True, default=str).encode()).hexdigest()[:16]


def reference(log: dict) -> tuple[str | None, int, list[str]]:
    """The fingerprint the current record must match, the method it uses, and problems with the rebaselines."""
    problems = []
    entries = log.get("entries", [])
    position = {e["id"]: i for i, e in enumerate(entries)}
    rebaselines = log.get("rebaselines", [])
    method, last_rb_pos = 1, -1
    for rb in rebaselines:
        pos = position.get(rb.get("after_entry"))
        if pos is None:
            problems.append(f"rebaseline {rb.get('date')}: after_entry {rb.get('after_entry')} is not in the log")
            continue
        if pos < last_rb_pos:
            problems.append(f"rebaseline {rb.get('date')}: rebaselines are not in log order")
        if rb.get("method_from") != method or rb.get("method_to") != method + 1:
            problems.append(f"rebaseline {rb.get('date')}: expected method {method} to {method + 1}")
        if rb.get("fingerprint_before") != entries[pos]["scope_fingerprint_after"]:
            problems.append(f"rebaseline {rb.get('date')}: fingerprint_before does not equal {rb['after_entry']} "
                            "scope_fingerprint_after, so the scope may have changed without an entry")
        method, last_rb_pos = rb.get("method_to", method + 1), pos
    if method != CURRENT_METHOD:
        problems.append(f"the log reaches fingerprint method {method}, but this check uses method {CURRENT_METHOD}: add a rebaseline")
    if not entries:
        return None, method, problems
    if rebaselines and last_rb_pos == len(entries) - 1:
        return rebaselines[-1].get("fingerprint_after"), method, problems
    return entries[-1]["scope_fingerprint_after"], method, problems


def main() -> int:
    rec = json.loads((ROOT / "mas/mas-record.json").read_text())
    now = fingerprint(rec)
    if "--print" in sys.argv:
        print(now)
        return 0
    log = json.loads((ROOT / "mas/scope-changes.json").read_text())
    problems = []
    ids = {r["id"] for r in rec["information_resources"]}
    seen = set()
    for e in log["entries"]:
        if e["id"] in seen:
            problems.append(f"duplicate entry id {e['id']}")
        seen.add(e["id"])
        if e["change_type"] not in TYPES:
            problems.append(f"{e['id']}: unknown change_type {e['change_type']}")
        if e["scn_category"] not in SCN:
            problems.append(f"{e['id']}: unknown scn_category {e['scn_category']}")
        for r in e.get("resources", []):
            if r not in ids and e["change_type"] != "removed":
                problems.append(f"{e['id']}: resource {r} is not in the scope record")
        if e["scn_category"] in ("adaptive", "transformative") and not e.get("notification"):
            problems.append(f"{e['id']}: {e['scn_category']} change needs a notification record")
    dates = [e["date"] for e in log["entries"]]
    if dates != sorted(dates):
        problems.append("entries are not in date order")
    ref, _, rb_problems = reference(log)
    problems += rb_problems
    if ref != now:
        problems.append(f"scope record changed without a log entry (log fingerprint {ref or 'none'}, record {now}). "
                        f"Add an entry to mas/scope-changes.json with scope_fingerprint_after {now}")
    for p in problems:
        print("PROBLEM:", p, file=sys.stderr)
    print("scope change log matches the scope record" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
