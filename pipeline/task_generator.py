#!/usr/bin/env python3
"""pipeline/task_generator.py — deterministic TaskCandidate generation.

Given OpenPatala's completeness state (a list of work records with their completeness fields),
this module deterministically emits TaskCandidates. No LLM needed — pure state-machine transitions.

Task types (from newbuildmainspec §42-43):
  FIND_SOURCE, FIND_ETEXT, FIND_EDITION, RESOLVE_IDENTITY, RESOLVE_RIGHTS,
  FETCH_RESOURCE, NORMALIZE_ETEXT, SEARCH_TRANSLATION, TRANSLATE, ANCHOR_TRANSLATION, OCR_RESOURCE

Usage:
  python3 pipeline/task_generator.py --input data/openpatala_state.json --output data/tasks/generated.jsonl
  python3 pipeline/task_generator.py --demo
"""
from __future__ import annotations

import argparse
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "data" / "tasks"


def _task_id(task_type: str, work_id: str, extra: str = "") -> str:
    """Content-addressed task ID: sha256(type + work_id + extra)."""
    raw = f"{task_type}:{work_id}:{extra}"
    return f"task_{hashlib.sha256(raw.encode()).hexdigest()[:16]}"


def generate_tasks_from_work(work: dict) -> list[dict]:
    """Given a work record with completeness fields, emit deterministic TaskCandidates.

    Expected work fields (from OpenPatala completeness projection):
      id, preferred_title, identity_state, source_state, translation_state,
      alignment_state, evaluation_state, rights_state
    """
    tasks = []
    work_id = work.get("id", "")
    title = work.get("preferred_title", "")
    identity = work.get("identity_state", "UNRESOLVED")
    source = work.get("source_state", "NONE")
    translation = work.get("translation_state", "NONE_KNOWN")
    alignment = work.get("alignment_state", "NONE")
    evaluation = work.get("evaluation_state", "NONE")
    rights = work.get("rights_state", "UNKNOWN")

    # Rule 1: Unresolved identity → RESOLVE_IDENTITY
    if identity in ("UNRESOLVED", "CONTESTED"):
        tasks.append({
            "task_id": _task_id("RESOLVE_IDENTITY", work_id),
            "task_type": "RESOLVE_IDENTITY",
            "work_id": work_id,
            "work_title": title,
            "priority_reason": f"identity={identity}",
            "status": "PENDING",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    # Rule 2: No source → FIND_SOURCE
    if source == "NONE":
        tasks.append({
            "task_id": _task_id("FIND_SOURCE", work_id),
            "task_type": "FIND_SOURCE",
            "work_id": work_id,
            "work_title": title,
            "priority_reason": "source=NONE",
            "status": "PENDING",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    # Rule 3: Catalog-only or scan-only → FIND_ETEXT or OCR_RESOURCE
    if source in ("CATALOG", "SCAN"):
        if source == "SCAN":
            tasks.append({
                "task_id": _task_id("OCR_RESOURCE", work_id),
                "task_type": "OCR_RESOURCE",
                "work_id": work_id,
                "work_title": title,
                "priority_reason": "source=SCAN, needs OCR",
                "status": "PENDING",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        else:
            tasks.append({
                "task_id": _task_id("FIND_ETEXT", work_id),
                "task_type": "FIND_ETEXT",
                "work_id": work_id,
                "work_title": title,
                "priority_reason": "source=CATALOG, needs etext",
                "status": "PENDING",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

    # Rule 4: Clean etext but no translation → SEARCH_TRANSLATION
    if source in ("TRANSCRIPTION", "ETEXT", "SCHOLARLY_ETEXT") and translation == "NONE_KNOWN":
        tasks.append({
            "task_id": _task_id("SEARCH_TRANSLATION", work_id),
            "task_type": "SEARCH_TRANSLATION",
            "work_id": work_id,
            "work_title": title,
            "priority_reason": f"source={source}, translation=NONE_KNOWN",
            "status": "PENDING",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    # Rule 5: Source-ready + no translation → TRANSLATE (Factory candidate)
    if source in ("ETEXT", "SCHOLARLY_ETEXT", "TRANSCRIPTION") and translation in ("NONE_KNOWN", "PARTIAL"):
        tasks.append({
            "task_id": _task_id("TRANSLATE", work_id),
            "task_type": "TRANSLATE",
            "work_id": work_id,
            "work_title": title,
            "priority_reason": f"source={source}, translation={translation}, Factory candidate",
            "status": "PENDING",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    # Rule 6: Translation exists but not aligned → ANCHOR_TRANSLATION
    if translation in ("EXISTING", "PARTIAL", "PATALA_MACHINE") and alignment == "NONE":
        tasks.append({
            "task_id": _task_id("ANCHOR_TRANSLATION", work_id),
            "task_type": "ANCHOR_TRANSLATION",
            "work_id": work_id,
            "work_title": title,
            "priority_reason": f"translation={translation}, alignment=NONE",
            "status": "PENDING",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    # Rule 7: Rights unknown → RESOLVE_RIGHTS
    if rights == "UNKNOWN":
        tasks.append({
            "task_id": _task_id("RESOLVE_RIGHTS", work_id),
            "task_type": "RESOLVE_RIGHTS",
            "work_id": work_id,
            "work_title": title,
            "priority_reason": "rights=UNKNOWN",
            "status": "PENDING",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    return tasks


def generate_from_state(state_path: str, output_path: str | None = None) -> list[dict]:
    """Read a completeness state file (JSON array of works) and emit all tasks."""
    p = Path(state_path)
    if not p.exists():
        print(f"state file not found: {p}")
        return []
    works = json.loads(p.read_text())
    all_tasks = []
    for work in works:
        all_tasks.extend(generate_tasks_from_work(work))

    # deduplicate by task_id
    seen = set()
    unique = []
    for t in all_tasks:
        if t["task_id"] not in seen:
            seen.add(t["task_id"])
            unique.append(t)

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            for t in unique:
                f.write(json.dumps(t, ensure_ascii=False) + "\n")
        print(f"generated {len(unique)} tasks → {out}")
    else:
        print(f"generated {len(unique)} tasks")
    return unique


def demo() -> None:
    """Demo with sample completeness data."""
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
    all_tasks = []
    for w in sample:
        tasks = generate_tasks_from_work(w)
        print(f"\n{w['preferred_title']} ({w['id']}):")
        for t in tasks:
            print(f"  {t['task_type']:22} → {t['priority_reason']}")
            all_tasks.append(t)
    print(f"\ntotal: {len(all_tasks)} tasks from {len(sample)} works")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="", help="path to completeness state JSON")
    ap.add_argument("--output", default="", help="path to write generated tasks JSONL")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        demo()
        return 0
    if a.input:
        out = a.output or str(TASKS_DIR / "generated.jsonl")
        generate_from_state(a.input, out)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
