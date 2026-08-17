#!/usr/bin/env python3
"""pipeline/agent_executor.py — execute tasks via mimo-v2.5 API calls.

Usage:
  python3 pipeline/agent_executor.py --task-type RESOLVE_RIGHTS --work-title Mrgendragama
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT / "pipeline"))

from api_client import call_json

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


def execute_task(task_type: str, work_id: str, work_title: str) -> dict:
    """Execute a task via mimo-v2.5."""
    prompt_template = PROMPTS.get(task_type, "Process {work}.")
    prompt = prompt_template.replace("{work}", f"{work_title}")

    start = time.time()
    result = call_json(prompt, max_tokens=400)
    duration = time.time() - start

    status = "DONE" if result["parsed"] else ("FAILED" if result["error"] else "DONE")

    record = {
        "task_id": f"{task_type}_{work_id}",
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

    (RESULTS_DIR / f"{task_type}_{work_id}.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False))
    return record


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--task-type", default="RESOLVE_RIGHTS")
    ap.add_argument("--work-id", default="PTW_mrgendragama")
    ap.add_argument("--work-title", default="Mrgendragama")
    a = ap.parse_args()

    r = execute_task(a.task_type, a.work_id, a.work_title)
    print(json.dumps(r, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
