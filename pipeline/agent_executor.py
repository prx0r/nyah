#!/usr/bin/env python3
"""pipeline/agent_executor.py — execute tasks via mimo-v2.5 with full provenance.

From newbuild1.md: every result gets {assertion, evidence, provenance}.
Every execution is logged as an event.
Every result is content-addressed.

Usage:
  python3 pipeline/agent_executor.py --task-type RESOLVE_RIGHTS --work-title Mrgendragama
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

from api_client import call_json
from kanban_board import KanbanBoard
from event_log import append as log_event
from provenance import create_nanopub
from digest import canonical_digest

RESULTS_DIR = ROOT / "data" / "tasks" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

PROMPTS = {
    "FIND_SOURCE": "Find a machine-readable source for {work}. Check GRETIL, Archive.org, PANDiT, Muktabodha. What is the best source URL? If none found, say none.",
    "SEARCH_TRANSLATION": "Does an English translation exist for {work}? Check OpenAlex, Crossref, Archive.org. Say yes or no, and list any found.",
    "RESOLVE_RIGHTS": "What is the rights status of {work}? Is it public domain (OPEN), in copyright (RESTRICTED), or unknown? Say one word.",
    "RESOLVE_IDENTITY": "Does {work} have alternate titles? Check PANDiT, GRETIL, Muktabodha cross-references. List any alternate names.",
    "ANCHOR_TRANSLATION": "Align the translation of {work} to source passages. What passages are covered?",
    "TRANSLATE": "Translate a passage of {work} from Sanskrit to English. Provide a literal translation.",
}


def execute_task(task_type: str, task_id: str, work_id: str, work_title: str,
                 board: KanbanBoard | None = None) -> dict:
    """Execute a task with full provenance tracking."""
    prompt_template = PROMPTS.get(task_type, "Process {work}.")
    prompt = prompt_template.replace("{work}", f"{work_title}")

    # Log start event
    log_event("TaskStarted", [task_id], {
        "task_type": task_type, "work_id": work_id, "work_title": work_title,
    })

    # Execute via mimo-v2.5
    start = time.time()
    result = call_json(prompt, max_tokens=400)
    duration = time.time() - start

    has_answer = bool(result["raw"] and len(result["raw"].strip()) > 2)
    status = "DONE" if has_answer else ("FAILED" if result["error"] else "DONE")

    # Build result record
    record = {
        "task_id": task_id,
        "task_type": task_type,
        "work_id": work_id,
        "work_title": work_title,
        "status": status,
        "parsed": result["parsed"],
        "raw": result["raw"][:500] if result["raw"] else "",
        "duration_s": round(duration, 1),
        "tokens": result["usage"].get("total_tokens", 0),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Content-address the result
    record["_digest"] = canonical_digest(record)

    # Create nanopublication
    nanopub = create_nanopub(
        task_id=task_id,
        assertion=f"{task_type} for {work_title}: {result['raw'][:200] if result['raw'] else status}",
        evidence=f"mimo-v2.5 response ({result['usage'].get('total_tokens', 0)} tokens)",
        provenance={
            "model": "mimo-v2.5",
            "duration_s": round(duration, 1),
            "tokens": result["usage"].get("total_tokens", 0),
            "schema": "nyah/result/1.0.0",
        },
    )
    record["_nanopub"] = nanopub["id"]

    # Save result
    (RESULTS_DIR / f"{task_id}.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False))

    # Log completion event
    log_event("TaskCompleted", [task_id], {
        "status": status,
        "duration_s": round(duration, 1),
        "tokens": result["usage"].get("total_tokens", 0),
        "nanopub": nanopub["id"],
        "digest": record["_digest"],
    })

    # Update kanban
    if board and task_id in board.tasks:
        if status == "DONE":
            board.complete(task_id, success=True,
                           reason=f"mimo-v2.5: {result['raw'][:100] if result['raw'] else 'done'}")
        else:
            board.complete(task_id, success=False,
                           reason=result["error"] or "no answer")

    return record


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--task-type", default="RESOLVE_RIGHTS")
    ap.add_argument("--task-id", default="test_001")
    ap.add_argument("--work-id", default="PTW_mrgendragama")
    ap.add_argument("--work-title", default="Mrgendragama")
    a = ap.parse_args()

    board = KanbanBoard()
    r = execute_task(a.task_type, a.task_id, a.work_id, a.work_title, board)
    print(json.dumps(r, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
