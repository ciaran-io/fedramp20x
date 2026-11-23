#!/usr/bin/env python3
"""Run every registered KSI validation method and write evidence.

Outputs:
  evidence/latest.json                       full result of this run
  evidence/history/runs/<date>T<time>Z.json  one record per run, never overwritten (issue #47)
  evidence/history/<date>.json               the day's summary, rebuilt from that day's run records

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


def write_history(hist: Path, now: datetime, ksis: list[dict]) -> Path:
    """Keep a record of every run, and rebuild the day's summary from all of that day's runs.

    A run record is never overwritten, so a failure seen in one run and fixed by a later run on the
    same day stays on record. Each record keeps the IDs of the methods that did not pass, which the
    historical metrics (SDR-CSX-KMT) need.
    """
    runs = hist / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    date = now.date().isoformat()
    run = {"date": date, "generated_at": now.isoformat(timespec="seconds"), "synthetic": False,
           "ksi_status": {k["id"]: k["status"] for k in ksis},
           "methods_not_passing": {k["id"]: [m["method_id"] for m in k["methods"] if m["status"] != "pass"]
                                   for k in ksis if any(m["status"] != "pass" for m in k["methods"])}}
    stem, n = now.strftime("%Y-%m-%dT%H%M%SZ"), 1
    path = runs / f"{stem}.json"
    while path.exists():  # two runs in the same second keep separate records
        n += 1
        path = runs / f"{stem}-{n}.json"
    path.write_text(json.dumps(run, indent=2) + "\n")

    day_runs = [json.loads(p.read_text()) for p in sorted(runs.glob(f"{date}T*.json"))]
    day_runs.sort(key=lambda r: r["generated_at"])
    day = {"date": date, "synthetic": False,
           "ksi_status": day_runs[-1]["ksi_status"],
           "runs": [r["generated_at"] for r in day_runs],
           "not_passing_in_any_run": sorted({k for r in day_runs for k, v in r["ksi_status"].items() if v != "pass"})}
    (hist / f"{date}.json").write_text(json.dumps(day, indent=2) + "\n")
    return path


def main() -> int:
    registry = load("evidence/ksi-registry.json")
    env = Env(company=load("environment/company.json"),
              iac=load("environment/iac-plan.json"),
              live=load("environment/live-state.json"),
              backup_jobs=load("environment/backup-jobs.json"),
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

    write_history(ROOT / "evidence/history", now, ksis)
    print("summary:", out["summary"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
