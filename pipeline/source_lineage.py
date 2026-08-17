#!/usr/bin/env python3
"""pipeline/source_lineage.py — track whether sources are independent or copied.

From newbuildmainspec §30:
- SourceLineage { source_a, source_b, relationship }
- Relationship: INDEPENDENT | COPIED_FROM | MIRROR_OF | DERIVED_FROM | UNKNOWN
- Matters because 3 catalogues can be 1 source copied 3 times

Usage:
  python3 pipeline/source_lineage.py --list
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINEAGE_FILE = ROOT / "data" / "source_lineage.json"

KNOWN_LINEAGE = {
    ("gretil", "muktabodha"): "INDEPENDENT",
    ("gretil", "archive.org"): "INDEPENDENT",
    ("pandit", "muktabodha"): "INDEPENDENT",
    ("pandit", "archive.org"): "INDEPENDENT",
    ("archive.org", "muktabodha"): "INDEPENDENT",
    ("openalex", "crossref"): "DERIVED_FROM",
}


def _load() -> dict:
    if LINEAGE_FILE.exists():
        return json.loads(LINEAGE_FILE.read_text())
    LINEAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    reg = {"version": "1.0.0", "lineage": []}
    for (a, b), rel in KNOWN_LINEAGE.items():
        reg["lineage"].append({"source_a": a, "source_b": b, "relationship": rel})
    LINEAGE_FILE.write_text(json.dumps(reg, indent=2))
    return reg


def list_lineage() -> list[dict]:
    return _load().get("lineage", [])


def check_independence(sources: list[str]) -> dict:
    """Check if sources are independent of each other."""
    reg = _load()
    pairs = []
    for i, a in enumerate(sources):
        for b in sources[i+1:]:
            for entry in reg.get("lineage", []):
                if (entry["source_a"] == a and entry["source_b"] == b) or \
                   (entry["source_a"] == b and entry["source_b"] == a):
                    pairs.append({"a": a, "b": b, "relationship": entry["relationship"]})

    independent = all(p["relationship"] == "INDEPENDENT" for p in pairs) if pairs else True
    return {"independent": independent, "pairs": pairs}


def main() -> int:
    for l in list_lineage():
        print(f"  {l['source_a']:15} {l['relationship']:15} {l['source_b']}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
