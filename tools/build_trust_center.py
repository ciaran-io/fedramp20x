#!/usr/bin/env python3
"""Build the single-file trust center page.

Reads trust-center/src/page.html (page content with a snapshot placeholder),
injects a JSON snapshot of the evidence, and writes trust-center/index.html as
a complete HTML document. With --artifact PATH it also writes the content-only
form that the Claude Artifact tool wraps itself.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "trust-center/src/page.html"
PUBLIC_DOCS = {"company-and-offering", "policies-index", "rules-matrix", "brand-guidelines"}
DOC_NOTES = {
    "company-and-offering": "What Orrinwick Beacon is, who uses it and why the company is pursuing FedRAMP 20x.",
    "policies-index": "The ten security policies and the KSIs each one covers.",
    "rules-matrix": "Every FedRAMP 20x rule for this class with its implementation status.",
    "brand-guidelines": "Name, mark, colour and voice.",
    "minimum-assessment-scope": "The assessed boundary, data flows, security categories and conditional exclusions.",
    "federal-data-and-information-resources": "Federal customer data categories and the decision for each information resource.",
    "security-decision-record": "Recorded security decisions with verification and validation links.",
    "vdr-report": "Vulnerability detection and response findings.",
    "incident-response-plan": "Roles, PAIN ratings and reporting steps.",
    "cryptographic-modules": "Cryptographic modules in use.",
    "significant-change-log": "Significant changes and their notices.",
    "secure-configuration-guide": "Recommended secure configuration for agencies.",
}


def title(stem: str) -> str:
    t = stem.replace("-", " ").title()
    for a in ("Vdr", "Mas", "Scn"):
        t = t.replace(a, a.upper())
    return t


def snapshot() -> dict:
    latest = json.loads((ROOT / "evidence/latest.json").read_text())
    mas = json.loads((ROOT / "mas/mas-record.json").read_text())
    pol = json.loads((ROOT / "evidence/policies.json").read_text())
    res = {r["id"]: r for r in mas["information_resources"]}
    days = [json.loads(p.read_text()) for p in sorted((ROOT / "evidence/history").glob("*.json"))]
    hist = []
    for d in days:
        c = {"pass": 0, "partial": 0, "fail": 0, "not_implemented": 0}
        for s in d["ksi_status"].values():
            c[s] = c.get(s, 0) + 1
        hist.append({"d": d["date"], "s": d.get("synthetic", False), **c})
    ksis = [{"id": k["id"], "theme": k["theme"], "name": k["name"],
             "status": k["status"], "gap": k.get("coverage_gap"), "note": k.get("coverage_note"),
             "methods": [{"id": m["method_id"], "kind": m["kind"], "status": m["status"],
                          "description": m["description"], "expected": m["expected"], "observed": m["observed"],
                          "findings": [f if isinstance(f, str) else json.dumps(f) for f in m["findings"]]}
                         for k2 in [k] for m in k2["methods"]]} for k in latest["ksis"]]
    tpr = [{"id": t["id"], "name": res[t["resource_id"]]["name"], "type": t["provider_type"],
            "auth": t["authorization_status"], "usage": t["usage_and_configuration"],
            "impact": t["potential_impact"], "mitigation": t["mitigation_measures"],
            "data": res[t["resource_id"]]["handles"]} for t in mas["third_party_resources"]]
    docs = []
    for p in sorted((ROOT / "docs").glob("*.md")):
        docs.append({"id": p.stem, "name": title(p.stem), "note": DOC_NOTES.get(p.stem, ""),
                     "tier": "public" if p.stem in PUBLIC_DOCS else "gated", "md": p.read_text()})
    for p in sorted((ROOT / "docs/policies").glob("*.md")):
        docs.append({"id": p.stem, "name": p.stem + " " + next(x["title"] for x in pol["policies"] if x["id"] == p.stem),
                     "note": "Security policy", "tier": "gated", "md": p.read_text()})
    rules = [{"id": r["id"], "p": r["process"], "n": r["name"], "f": r["force"], "w": r["affects"], "s": r["status"]} for r in json.loads((ROOT / "evidence/rules-matrix.json").read_text())]
    return {"rules": rules, "notice": latest["demo_notice"], "company": latest["company"], "class": latest["class"],
            "frmr": latest["frmr_version"], "generated": latest["generated_at"], "summary": latest["summary"],
            "themes": json.loads((ROOT / "evidence/ksi-registry.json").read_text())["themes"],
            "ksis": ksis, "history": hist, "tpr": tpr, "docs": docs,
            "policies": [{"id": p["id"], "title": p["title"], "owner": p["owner"], "cadence": p["review_cadence"]} for p in pol["policies"]],
            "scope": json.loads((ROOT / "evidence/mas-summary.json").read_text())["decisions"]}


def main() -> int:
    page = SRC.read_text()
    blob = json.dumps(snapshot(), separators=(",", ":")).replace("</", "<\\/")
    if "__SNAPSHOT__" not in page:
        print("placeholder missing", file=sys.stderr)
        return 1
    content = page.replace("__SNAPSHOT__", blob)
    full = ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>\n'
            + content + "\n</body></html>\n")
    (ROOT / "trust-center/index.html").write_text(full)
    if "--artifact" in sys.argv:
        Path(sys.argv[sys.argv.index("--artifact") + 1]).write_text(content)
    print(f"trust center page written: {len(full) // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
