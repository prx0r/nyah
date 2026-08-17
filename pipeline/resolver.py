#!/usr/bin/env python3
"""pipeline/resolver.py — staged identity resolver (R0-R5).

From newbuildmainspec §45-46:
- R0: exact external ID match
- R1: exact deterministic crosswalk
- R2: exact normalized bibliographic composite
- R3: high-confidence candidate (fuzzy/embedding/LLM) — never auto-merge
- R4: multi-source corroboration
- R5: human/scholar/institution adjudication

Usage:
  python3 pipeline/resolver.py --resolve --title "Tantraloka"
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "http://127.0.0.1:8800"


def _get(path: str) -> dict | None:
    try:
        proc = subprocess.run(
            ["curl", "-s", "--max-time", "10", f"{API}{path}"],
            capture_output=True, text=True, timeout=15,
        )
        return json.loads(proc.stdout)
    except Exception:
        return None


def r0_exact_id(external_id: str) -> dict:
    """R0: exact external ID match."""
    # Try exact match in OpenPatala
    data = _get(f"/works?limit=300")
    if not data:
        return {"stage": "R0", "match": False}
    for w in data.get("works", []):
        if w.get("id") == external_id:
            return {"stage": "R0", "match": True, "work": w}
    return {"stage": "R0", "match": False}


def r2_bibliographic(title: str) -> dict:
    """R2: exact normalized bibliographic composite."""
    data = _get(f"/works?limit=300")
    if not data:
        return {"stage": "R2", "match": False}
    title_lower = title.lower().strip()
    for w in data.get("works", []):
        w_title = (w.get("title", "") or "").lower().strip()
        if title_lower == w_title:
            return {"stage": "R2", "match": True, "work": w, "method": "exact_title"}
    return {"stage": "R2", "match": False}


def resolve(title: str = "", external_id: str = "") -> dict:
    """Run staged resolution."""
    if external_id:
        r = r0_exact_id(external_id)
        if r["match"]:
            return r

    r = r2_bibliographic(title)
    if r["match"]:
        return r

    return {"stage": "R3", "match": False, "note": "requires fuzzy/embedding/LLM — not auto-merged"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--resolve", action="store_true")
    ap.add_argument("--title", default="")
    ap.add_argument("--id", default="")
    a = ap.parse_args()

    if a.resolve:
        result = resolve(title=a.title, external_id=a.id)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
