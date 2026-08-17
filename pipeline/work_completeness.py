#!/usr/bin/env python3
"""pipeline/work_completeness.py — gap map per work.

From newbuildmainspec §27:
- WorkCompleteness { work_id, identity, source, translation, alignment, evaluation, bibliography }
- Each field has states (e.g. identity: UNRESOLVED/CANDIDATE/RESOLVED/CONTESTED)
- This is a projection, not primary truth

Usage:
  python3 pipeline/work_completeness.py --from-api
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "work_completeness.json"

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


def compute_completeness(work: dict) -> dict:
    """Compute completeness state for a work."""
    translation = work.get("translation_status", "none")
    verified = work.get("verified", "false") == "true"

    # Identity
    identity = "RESOLVED"  # all works in DB are resolved

    # Source
    source = "ETEXT" if translation in ("complete", "partial", "machine") else "CATALOG"

    # Translation
    trans_map = {"complete": "EXISTING", "partial": "PARTIAL", "machine": "PATALA_MACHINE"}
    trans_state = trans_map.get(translation, "NONE_KNOWN")

    # Alignment
    alignment = "NONE"

    # Evaluation
    evaluation = "HUMAN" if verified else "NONE"

    return {
        "work_id": work.get("id", ""),
        "identity": identity,
        "source": source,
        "translation": trans_state,
        "alignment": alignment,
        "evaluation": evaluation,
        "bibliography": "NONE",
    }


def build_completeness() -> list[dict]:
    """Build completeness for all works from API."""
    works_data = _get("/works?limit=300")
    if not works_data:
        return []
    return [compute_completeness(w) for w in works_data.get("works", [])]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-api", action="store_true")
    a = ap.parse_args()

    if a.from_api:
        states = build_completeness()
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(states, indent=2, ensure_ascii=False))
        print(f"built completeness for {len(states)} works → {OUTPUT}")

        # Summary
        by_trans = {}
        for s in states:
            t = s["translation"]
            by_trans[t] = by_trans.get(t, 0) + 1
        for k, n in sorted(by_trans.items(), key=lambda x: -x[1]):
            print(f"  {k:20} {n}")
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
