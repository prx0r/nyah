#!/usr/bin/env python3
"""pipeline/openpatala_bridge.py — reads OpenPatala's live API.

Replaces the static JSON bridge with real API calls.
OpenPatala API: http://127.0.0.1:8800

Usage:
  python3 pipeline/openpatala_bridge.py --convert
  python3 pipeline/openpatala_bridge.py --stats
  python3 pipeline/openpatala_bridge.py --gaps
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "openpatala_state.json"
API = "http://127.0.0.1:8800"


def _api_get(path: str) -> dict | None:
    """GET from OpenPatala API."""
    try:
        proc = subprocess.run(
            ["curl", "-s", "--max-time", "10", f"{API}{path}"],
            capture_output=True, text=True, timeout=15,
        )
        return json.loads(proc.stdout)
    except Exception:
        return None


def fetch_works(limit: int = 300) -> list[dict]:
    """Fetch all works from OpenPatala API."""
    works = []
    cursor = None
    while len(works) < limit:
        path = f"/works?limit=100"
        if cursor:
            path += f"&cursor={cursor}"
        data = _api_get(path)
        if not data or "works" not in data:
            break
        works.extend(data["works"])
        cursor = data.get("next_cursor")
        if not cursor:
            break
    return works


def work_to_state(work: dict) -> dict:
    """Convert OpenPatala work to nyah completeness state."""
    translation = work.get("translation_status", "none")
    verified = work.get("verified", "false") == "true"

    # Map translation_status to nyah states
    if translation == "full":
        source_state = "ETEXT"
        trans_state = "EXISTING"
    elif translation == "partial":
        source_state = "ETEXT"
        trans_state = "PARTIAL"
    elif translation == "machine":
        source_state = "ETEXT"
        trans_state = "PATALA_MACHINE"
    else:
        source_state = "CATALOG"
        trans_state = "NONE_KNOWN"

    return {
        "id": work.get("id", ""),
        "preferred_title": work.get("title", ""),
        "identity_state": "RESOLVED",
        "source_state": source_state,
        "translation_state": trans_state,
        "alignment_state": "NONE",
        "evaluation_state": "NONE" if not verified else "HUMAN",
        "rights_state": "UNKNOWN",
        "_openpatala": {
            "translation_status": translation,
            "verified": verified,
        },
    }


def convert_all() -> list[dict]:
    """Fetch from API and convert to nyah state."""
    works = fetch_works()
    return [work_to_state(w) for w in works]


def convert_and_save() -> None:
    """Convert and save to nyah state file."""
    states = convert_all()
    if states:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(states, indent=2, ensure_ascii=False))
        print(f"converted {len(states)} works from API → {OUTPUT}")


def stats() -> None:
    """Print stats about the converted data."""
    states = convert_all()
    if not states:
        print("no data from API")
        return

    print(f"=== OPENPATALA → NYAH BRIDGE ({len(states)} works) ===\n")

    by_source = {}
    by_trans = {}
    for s in states:
        v = s["source_state"]
        by_source[v] = by_source.get(v, 0) + 1
        t = s["translation_state"]
        by_trans[t] = by_trans.get(t, 0) + 1

    print("SOURCE STATE:")
    for k, n in sorted(by_source.items(), key=lambda x: -x[1]):
        print(f"  {k:20} {n:4}")

    print("\nTRANSLATION STATE:")
    for k, n in sorted(by_trans.items(), key=lambda x: -x[1]):
        print(f"  {k:20} {n:4}")

    needs_trans = [s for s in states if s["translation_state"] == "NONE_KNOWN"]
    print(f"\nNEED TRANSLATION: {len(needs_trans)}")


def gaps() -> None:
    """Show works that need action."""
    states = convert_all()
    no_trans = [s for s in states if s["translation_state"] == "NONE_KNOWN"]
    print(f"Works needing translation: {len(no_trans)}")
    for s in no_trans[:10]:
        print(f"  {s['id']:40} {s['preferred_title'][:40]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--convert", action="store_true")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--gaps", action="store_true")
    a = ap.parse_args()
    if a.convert:
        convert_and_save()
        return 0
    if a.stats:
        stats()
        return 0
    if a.gaps:
        gaps()
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
