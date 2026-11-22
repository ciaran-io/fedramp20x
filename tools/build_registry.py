#!/usr/bin/env python3
"""Generate evidence/ksi-registry.json from the downloaded FRMR dataset.

Resolves the statement for the target class (default: c), applying class
variants where present. The statement text is read here to resolve class variants but is not written out:
the committed outputs keep IDs, names and controls only (see frmr/PROVENANCE.md).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLASS = sys.argv[1] if len(sys.argv) > 1 else "c"


def main() -> None:
    d = json.loads((ROOT / "frmr/fedramp-consolidated-rules.json").read_text())
    registry = {
        "frmr_version": d["info"]["version"],
        "frmr_last_updated": d["info"]["last_updated"],
        "class": CLASS,
        "themes": [],
        "indicators": [],
    }
    for key, theme in d["KSI"].items():
        registry["themes"].append({"key": key, "name": theme["name"], "status": theme["status"]})
        for kid, ind in theme["indicators"].items():
            variants = ind.get("varies_by_class")
            statement = ind.get("statement")
            if variants:
                if CLASS not in variants:
                    continue  # indicator does not apply at this class
                statement = variants[CLASS].get("statement", statement)
            optional = bool(statement and statement.startswith("**Optional:**"))
            registry["indicators"].append({
                "id": kid,
                "theme": key,
                "name": ind["name"],
                "optional_at_class": optional,
                "controls": ind.get("controls", []),
            })
    out = ROOT / "evidence/ksi-registry.json"
    out.write_text(json.dumps(registry, indent=2) + "\n")
    print(f"wrote {out.relative_to(ROOT)}: {len(registry['indicators'])} KSIs for class {CLASS}")


if __name__ == "__main__":
    main()
