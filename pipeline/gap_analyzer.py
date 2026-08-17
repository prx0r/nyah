#!/usr/bin/env python3
"""pipeline/gap_analyzer.py — reads OpenPatala completeness state, emits gap priorities.

The gap analyzer is nyah's eyes: it reads the completeness projection from OpenPatala and computes
priority scores for each gap. These scores feed into the scheduler for worker dispatch.

Gap priority formula (intuition, not frozen):
  Priority = GapValue × ExpectedYield × SourceAuthority × RightsUsability × DownstreamReach / Cost

Usage:
  python3 pipeline/gap_analyzer.py --input data/openpatala_state.json --output data/tasks/gaps.jsonl
  python3 pipeline/gap_analyzer.py --demo
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "data" / "tasks"


@dataclass
class Gap:
    """A single gap in OpenPatala's completeness state."""
    work_id: str
    work_title: str
    gap_type: str          # FIND_SOURCE, FIND_ETEXT, SEARCH_TRANSLATION, etc.
    description: str
    gap_value: float       # 0..1, how valuable filling this gap is
    expected_yield: float  # 0..1, probability of success
    source_authority: float  # 0..1, quality of available sources
    rights_usability: float  # 0..1, can we legally use the result
    downstream_reach: float  # 0..1, how many other tasks this unblocks
    cost: float            # 0..1, estimated effort
    priority: float = 0.0  # computed

    def compute_priority(self) -> float:
        self.priority = round(
            (self.gap_value * self.expected_yield * self.source_authority *
             self.rights_usability * self.downstream_reach) / max(self.cost, 0.01),
            4,
        )
        return self.priority


def analyze_work(work: dict) -> list[Gap]:
    """Analyze a single work record for gaps."""
    gaps = []
    work_id = work.get("id", "")
    title = work.get("preferred_title", "")
    identity = work.get("identity_state", "UNRESOLVED")
    source = work.get("source_state", "NONE")
    translation = work.get("translation_state", "NONE_KNOWN")
    alignment = work.get("alignment_state", "NONE")
    rights = work.get("rights_state", "UNKNOWN")

    # Gap: unresolved identity
    if identity in ("UNRESOLVED", "CONTESTED"):
        gaps.append(Gap(
            work_id=work_id, work_title=title, gap_type="RESOLVE_IDENTITY",
            description=f"Identity state is {identity}",
            gap_value=0.9 if identity == "CONTESTED" else 0.7,
            expected_yield=0.6, source_authority=0.5, rights_usability=1.0,
            downstream_reach=0.8, cost=0.4,
        ))

    # Gap: no source
    if source == "NONE":
        gaps.append(Gap(
            work_id=work_id, work_title=title, gap_type="FIND_SOURCE",
            description="No source material available",
            gap_value=0.8, expected_yield=0.5, source_authority=0.5,
            rights_usability=0.7, downstream_reach=0.9, cost=0.6,
        ))

    # Gap: scan-only needs OCR
    if source == "SCAN":
        gaps.append(Gap(
            work_id=work_id, work_title=title, gap_type="OCR_RESOURCE",
            description="Scan available but no machine-readable text",
            gap_value=0.6, expected_yield=0.7, source_authority=0.8,
            rights_usability=0.5, downstream_reach=0.7, cost=0.5,
        ))

    # Gap: catalog-only needs etext
    if source == "CATALOG":
        gaps.append(Gap(
            work_id=work_id, work_title=title, gap_type="FIND_ETEXT",
            description="Catalog record only, no text acquired",
            gap_value=0.7, expected_yield=0.4, source_authority=0.6,
            rights_usability=0.6, downstream_reach=0.8, cost=0.7,
        ))

    # Gap: no translation
    if source in ("ETEXT", "SCHOLARLY_ETEXT", "TRANSCRIPTION") and translation == "NONE_KNOWN":
        gaps.append(Gap(
            work_id=work_id, work_title=title, gap_type="SEARCH_TRANSLATION",
            description=f"Source ready ({source}) but no translation found",
            gap_value=0.7, expected_yield=0.6, source_authority=0.7,
            rights_usability=0.8, downstream_reach=0.5, cost=0.3,
        ))

    # Gap: Factory candidate (source-ready, no/partial translation)
    if source in ("ETEXT", "SCHOLARLY_ETEXT") and translation in ("NONE_KNOWN", "PARTIAL"):
        gaps.append(Gap(
            work_id=work_id, work_title=title, gap_type="TRANSLATE",
            description=f"Ready for translation (source={source}, translation={translation})",
            gap_value=0.8, expected_yield=0.7, source_authority=0.8,
            rights_usability=0.7, downstream_reach=0.6, cost=0.7,
        ))

    # Gap: translation not aligned
    if translation in ("EXISTING", "PARTIAL", "PATALA_MACHINE") and alignment == "NONE":
        gaps.append(Gap(
            work_id=work_id, work_title=title, gap_type="ANCHOR_TRANSLATION",
            description=f"Translation exists ({translation}) but not passage-aligned",
            gap_value=0.5, expected_yield=0.8, source_authority=0.7,
            rights_usability=0.9, downstream_reach=0.4, cost=0.3,
        ))

    # Gap: rights unknown
    if rights == "UNKNOWN":
        gaps.append(Gap(
            work_id=work_id, work_title=title, gap_type="RESOLVE_RIGHTS",
            description="Rights status unknown, blocks downstream use",
            gap_value=0.6, expected_yield=0.5, source_authority=0.5,
            rights_usability=0.3, downstream_reach=0.6, cost=0.2,
        ))

    # Compute priorities
    for g in gaps:
        g.compute_priority()

    return gaps


def analyze_state(state_path: str, output_path: str | None = None) -> list[Gap]:
    """Analyze a full completeness state file."""
    p = Path(state_path)
    if not p.exists():
        print(f"state file not found: {p}")
        return []
    works = json.loads(p.read_text())
    all_gaps = []
    for work in works:
        all_gaps.extend(analyze_work(work))

    # sort by priority descending
    all_gaps.sort(key=lambda g: g.priority, reverse=True)

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            for g in all_gaps:
                f.write(json.dumps({
                    "task_id": f"gap_{g.gap_type}_{g.work_id}",
                    "task_type": g.gap_type,
                    "work_id": g.work_id, "work_title": g.work_title,
                    "description": g.description,
                    "priority": g.priority,
                    "status": "PENDING",
                    "breakdown": {
                        "gap_value": g.gap_value, "expected_yield": g.expected_yield,
                        "source_authority": g.source_authority, "rights_usability": g.rights_usability,
                        "downstream_reach": g.downstream_reach, "cost": g.cost,
                    },
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }, ensure_ascii=False) + "\n")
        print(f"analyzed {len(works)} works → {len(all_gaps)} gaps → {out}")
    else:
        print(f"analyzed {len(works)} works → {len(all_gaps)} gaps")

    return all_gaps


def demo() -> None:
    """Demo with sample data."""
    sample = [
        {"id": "PTW_001", "preferred_title": "Tantraloka", "identity_state": "RESOLVED",
         "source_state": "ETEXT", "translation_state": "NONE_KNOWN",
         "alignment_state": "NONE", "evaluation_state": "NONE", "rights_state": "OPEN"},
        {"id": "PTW_002", "preferred_title": "Spandakarika", "identity_state": "CONTESTED",
         "source_state": "SCAN", "translation_state": "EXISTING",
         "alignment_state": "NONE", "evaluation_state": "MACHINE", "rights_state": "UNKNOWN"},
        {"id": "PTW_003", "preferred_title": "Vijnanabhairava", "identity_state": "RESOLVED",
         "source_state": "NONE", "translation_state": "NONE_KNOWN",
         "alignment_state": "NONE", "evaluation_state": "NONE", "rights_state": "UNKNOWN"},
    ]
    all_gaps = []
    for w in sample:
        gaps = analyze_work(w)
        print(f"\n{w['preferred_title']} ({w['id']}):")
        for g in gaps:
            print(f"  {g.gap_type:22} priority={g.priority:.3f}  {g.description}")
            all_gaps.append(g)
    all_gaps.sort(key=lambda g: g.priority, reverse=True)
    print(f"\n=== TOP GAPS (by priority) ===")
    for g in all_gaps[:5]:
        print(f"  {g.priority:.3f}  {g.gap_type:22}  {g.work_title}  ({g.description})")
    print(f"\ntotal: {len(all_gaps)} gaps")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="", help="path to completeness state JSON")
    ap.add_argument("--output", default="", help="path to write gap analysis JSONL")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        demo()
        return 0
    if a.input:
        out = a.output or str(TASKS_DIR / "gaps.jsonl")
        analyze_state(a.input, out)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
