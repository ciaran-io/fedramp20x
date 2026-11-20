#!/usr/bin/env python3
"""Validate the FRMR dataset against its published schema."""
import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:
    sys.exit("pip install jsonschema")

ROOT = Path(__file__).resolve().parent.parent
data = json.loads((ROOT / "frmr/fedramp-consolidated-rules.json").read_text())
schema = json.loads((ROOT / "frmr/fedramp-consolidated-rules.schema.json").read_text())
errs = sorted(jsonschema.Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.path))
for e in errs[:10]:
    print("ERROR", "/".join(map(str, e.path)), e.message[:160])
print(f"FRMR {data['info']['version']}: {'valid' if not errs else str(len(errs)) + ' schema error(s)'}")
sys.exit(1 if errs else 0)
