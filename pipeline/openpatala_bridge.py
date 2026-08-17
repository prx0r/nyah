#!/usr/bin/env python3
"""pipeline/openpatala_bridge.py — converts OpenPatala data to nyah's completeness state format.

Reads OpenPatala's translation-availability.json (260 works) and emits nyah's completeness state
format so the gap analyzer and task generator can work with real data.

Usage:
  python3 pipeline/openpatala_bridge.py --convert
  python3 pipeline/openpatala_bridge.py --stats
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPENPATALA_DATA = Path("/root/openpatalaproject/data/corpus/translation-availability.json")
OUTPUT = ROOT / "data" / "openpatala_state.json"


def convert_coverage(work: dict) -> str:
    """Map OpenPatala coverage to nyah source_state."""
    cov = work.get("coverage", "none")
    has_en = work.get("has_english", False)
    translations = work.get("translations", [])

    if cov == "full" and has_en:
        return "ETEXT"  # has full English translation = source-ready
    elif cov == "partial" and has_en:
        return "ETEXT"
    elif cov == "none" and has_en:
        return "TRANSCRIPTION"  # has some text but no clean etext
    elif cov == "none":
        # check if factory says we need to acquire source
        factory = work.get("factory", {})
        action = factory.get("next_action")
        if action == "ACQUIRE_SOURCE":
            return "NONE"
        elif action == "BUILD_L0_SOURCE_MODE":
            return "CATALOG"  # catalog record exists, needs source
        else:
            return "NONE"
    return "NONE"


def convert_translation(work: dict) -> str:
    """Map OpenPatala translations to nyah translation_state."""
    translations = work.get("translations", [])
    if not translations:
        return "NONE_KNOWN"

    # check tiers
    tiers = [t.get("tier", "") for t in translations]
    complete = [t for t in translations if t.get("complete", False)]

    if complete:
        return "EXISTING"
    elif translations:
        return "PARTIAL"
    return "NONE_KNOWN"


def convert_alignment(work: dict) -> str:
    """Map factory state to alignment_state."""
    factory = work.get("factory", {})
    t1 = factory.get("t1", "UNKNOWN")
    if t1 in ("DONE", "COMPLETE"):
        return "COMPLETE"
    elif t1 in ("NOT_STARTED", "IN_PROGRESS"):
        return "PARTIAL"
    return "NONE"


def convert_rights(work: dict) -> str:
    """Map copyright_hint to rights_state."""
    hint = work.get("copyright_hint", "")
    if hint == "IN_COPYRIGHT":
        return "RESTRICTED"
    elif hint in ("PUBLIC_DOMAIN", "CC-BY", "CC0"):
        return "OPEN"
    return "UNKNOWN"


def convert_work(name: str, work: dict) -> dict:
    """Convert one OpenPatala work to nyah completeness state format."""
    return {
        "id": f"PTW_{name[:12]}",
        "preferred_title": name.replace("-", " ").title(),
        "identity_state": "RESOLVED",  # OpenPatala already resolved these
        "source_state": convert_coverage(work),
        "translation_state": convert_translation(work),
        "alignment_state": convert_alignment(work),
        "evaluation_state": "NONE",
        "rights_state": convert_rights(work),
        # extra context from OpenPatala
        "_openpatala": {
            "work": name,
            "has_english": work.get("has_english", False),
            "coverage": work.get("coverage", "none"),
            "n_translations": len(work.get("translations", [])),
            "factory_next_action": work.get("factory", {}).get("next_action"),
        },
    }


def convert_all() -> list[dict]:
    """Convert all OpenPatala works to nyah completeness state."""
    if not OPENPATALA_DATA.exists():
        print(f"OpenPatala data not found: {OPENPATALA_DATA}")
        return []

    data = json.loads(OPENPATALA_DATA.read_text())
    works = data.get("works", {})

    states = []
    for name, work in works.items():
        states.append(convert_work(name, work))

    return states


def stats() -> None:
    """Print stats about the converted data."""
    states = convert_all()
    if not states:
        return

    print(f"=== OPENPATALA → NYAH BRIDGE ({len(states)} works) ===\n")

    # source state distribution
    by_source = {}
    for s in states:
        v = s["source_state"]
        by_source[v] = by_source.get(v, 0) + 1
    print("SOURCE STATE:")
    for k, n in sorted(by_source.items(), key=lambda x: -x[1]):
        print(f"  {k:20} {n:4}")

    # translation state distribution
    by_trans = {}
    for s in states:
        v = s["translation_state"]
        by_trans[v] = by_trans.get(v, 0) + 1
    print("\nTRANSLATION STATE:")
    for k, n in sorted(by_trans.items(), key=lambda x: -x[1]):
        print(f"  {k:20} {n:4}")

    # rights distribution
    by_rights = {}
    for s in states:
        v = s["rights_state"]
        by_rights[v] = by_rights.get(v, 0) + 1
    print("\nRIGHTS STATE:")
    for k, n in sorted(by_rights.items(), key=lambda x: -x[1]):
        print(f"  {k:20} {n:4}")

    # factory readiness
    by_factory = {}
    for s in states:
        v = s["_openpatala"]["factory_next_action"] or "none"
        by_factory[v] = by_factory.get(v, 0) + 1
    print("\nFACTORY NEXT ACTION:")
    for k, n in sorted(by_factory.items(), key=lambda x: -x[1]):
        print(f"  {k:30} {n:4}")

    # top gap candidates (source=NONE or CATALOG, no translation)
    gap_candidates = [s for s in states
                      if s["source_state"] in ("NONE", "CATALOG")
                      and s["translation_state"] == "NONE_KNOWN"]
    print(f"\nGAP CANDIDATES (no source, no translation): {len(gap_candidates)}")
    for s in gap_candidates[:10]:
        print(f"  {s['preferred_title']:30} source={s['source_state']}")

    # Factory-ready (source=ETEXT, no/partial translation)
    factory_ready = [s for s in states
                     if s["source_state"] in ("ETEXT", "SCHOLARLY_ETEXT")
                     and s["translation_state"] in ("NONE_KNOWN", "PARTIAL")]
    print(f"\nFACTORY READY (source-ready, needs translation): {len(factory_ready)}")
    for s in factory_ready[:10]:
        print(f"  {s['preferred_title']:30} trans={s['translation_state']}")


def convert_and_save() -> None:
    """Convert and save to nyah's state file."""
    states = convert_all()
    if states:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(states, indent=2, ensure_ascii=False))
        print(f"converted {len(states)} works → {OUTPUT}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--convert", action="store_true", help="convert and save")
    ap.add_argument("--stats", action="store_true", help="print stats")
    a = ap.parse_args()
    if a.convert:
        convert_and_save()
        return 0
    if a.stats:
        stats()
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
