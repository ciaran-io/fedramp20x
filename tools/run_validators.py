#!/usr/bin/env python3
"""Run every registered KSI validation method and write evidence.

Outputs:
  evidence/latest.json          full result of this run
  evidence/history/<date>.json  one daily summary written by each run

Per-KSI status roll-up (honest by design):
  pass            >=2 automated methods ran and all passed
  fail            any method failed
  partial         methods passed but fewer than 2 are implemented, or a known gap
                  against the official KSI statement is recorded (validators/registry.py)
  not_implemented no automated method exists yet
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from validators.base import Env, ERROR  # noqa: E402
from validators.registry import KSI_METHODS, KSI_GAPS, KSI_NOTES  # noqa: E402

REQUIRED_METHODS = 2  # FRC-CSX-VVK, Class C


def load(p: str) -> dict:
    return json.loads((ROOT / p).read_text())


def roll_up(results: list[dict], gap: str | None = None) -> str:
    if not results:
        return "not_implemented"
    if any(r["status"] != "pass" for r in results):
        return "fail"
    if len(results) < REQUIRED_METHODS or gap:
        return "partial"
    return "pass"


def main() -> int:
    registry = load("evidence/ksi-registry.json")
    env = Env(company=load("environment/company.json"),
              iac=load("environment/iac-plan.json"),
              live=load("environment/live-state.json"),
              mas=load("mas/mas-record.json"),
              grc=load("environment/grc-records.json"))
    now = datetime.now(timezone.utc)
    ksis = []
    for ind in registry["indicators"]:
        results = []
        for fn in KSI_METHODS.get(ind["id"], []):
            try:
                results.append(fn(env).to_dict())
            except Exception as exc:  # a crashing check is an error, never a pass
                results.append({"method_id": fn.__name__, "kind": "unknown", "source": "n/a",
                                "description": "method raised", "status": ERROR,
                                "expected": "", "observed": repr(exc), "findings": [repr(exc)]})
        gap = KSI_GAPS.get(ind["id"])
        ksis.append({**ind, "status": roll_up(results, gap), "coverage_gap": gap, "coverage_note": KSI_NOTES.get(ind["id"]), "methods": results})

    counts: dict[str, int] = {s: 0 for s in ("pass", "partial", "fail", "not_implemented")}
    for k in ksis:
        counts[k["status"]] = counts.get(k["status"], 0) + 1

    out = {
        "demo_notice": "FICTIONAL company and data. Not a real FedRAMP certification.",
        "company": env.company["name"],
        "cso": env.company["cso"]["name"],
        "class": registry["class"],
        "frmr_version": registry["frmr_version"],
        "generated_at": now.isoformat(timespec="seconds"),
        "summary": {"total": len(ksis), **counts},
        "ksis": ksis,
    }
    (ROOT / "evidence/latest.json").write_text(json.dumps(out, indent=2) + "\n")

    hist = ROOT / "evidence/history"
    hist.mkdir(exist_ok=True)
    day = {"date": now.date().isoformat(), "synthetic": False,
           "ksi_status": {k["id"]: k["status"] for k in ksis}}
    (hist / f"{day['date']}.json").write_text(json.dumps(day, indent=2) + "\n")
    print("summary:", out["summary"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
