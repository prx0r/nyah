#!/usr/bin/env python3
"""pipeline/pipeline_runner.py — the autonomous coordination loop.

Reads OpenPatala API → finds gaps → generates tasks → dispatches → executes via mimo-v2.5 → updates kanban.
Failed tasks are retried via failure_handler (up to 2 retries).

Usage:
  python3 pipeline/pipeline_runner.py --cycle
  python3 pipeline/pipeline_runner.py --autonomous --max-cycles 5
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT / "pipeline"))

from openpatala_bridge import convert_all
from gap_analyzer import analyze_work
from kanban_board import KanbanBoard
from agent_executor import execute_task, RESULTS_DIR
from failure_handler import handle_failure

CYCLE_LOG = ROOT / "data" / "runs" / "pipeline-cycles.jsonl"
CYCLE_LOG.parent.mkdir(parents=True, exist_ok=True)


def get_tasks_for_execution(board: KanbanBoard, works: list[dict],
                            max_tasks: int = 5) -> list[dict]:
    """Generate tasks from works that don't already have tasks on the board."""
    tasks = []
    for work in works:
        if len(tasks) >= max_tasks:
            break
        gaps = analyze_work(work)
        for g in gaps:
            if len(tasks) >= max_tasks:
                break
            task_id = f"{g.gap_type}_{g.work_id}"
            if task_id not in board.tasks:
                tasks.append({
                    "task_id": task_id,
                    "task_type": g.gap_type,
                    "work_id": g.work_id,
                    "work_title": g.work_title,
                    "priority": g.priority,
                })
    return tasks


def handle_failed_tasks(board: KanbanBoard) -> int:
    """Check for FAILED tasks and retry via failure_handler. Returns count retried."""
    retried = 0
    failed = [t for t in board.tasks.values() if t["state"] == "FAILED"]

    for task in failed:
        retries = task.get("retry_count", 0)
        result = handle_failure(
            agent_id="system",
            task_id=task["task_id"],
            error=task.get("error", "unknown"),
            current_retries=retries,
        )

        if result["action"] == "RETRY":
            board.retry(task["task_id"])
            retried += 1
        elif result["action"] == "ESCALATE":
            board.escalate(task["task_id"], result["reason"])
        else:
            board.retry(task["task_id"])
            retried += 1

    return retried


def run_cycle(board: KanbanBoard) -> dict:
    """Run one coordination cycle."""
    now = datetime.now(timezone.utc).isoformat()
    cycle = {"at": now}

    # 0. Handle failed tasks first (retry them)
    retried = handle_failed_tasks(board)
    cycle["retried"] = retried

    # 1. Fetch OpenPatala state
    works = convert_all()
    cycle["works"] = len(works)

    # 2. Generate tasks not yet on board
    new_tasks = get_tasks_for_execution(board, works, max_tasks=5)
    for t in new_tasks:
        board.add_task(t["task_id"], t["task_type"], t["work_id"],
                       t["work_title"], t["priority"])
        board.move(t["task_id"], "READY")
    cycle["new_tasks"] = len(new_tasks)

    # 3. Pick next READY task by priority (including retried)
    ready = board.ready_tasks()
    if not ready:
        cycle["action"] = "no tasks ready"
        return cycle

    ready.sort(key=lambda t: -t.get("priority", 0))
    task = ready[0]

    # 4. Mark as in progress
    board.start_work(task["task_id"])

    # 5. Execute via mimo-v2.5
    result = execute_task(
        task_type=task["task_type"],
        task_id=task["task_id"],
        work_id=task.get("work_id", ""),
        work_title=task.get("work_title", ""),
        board=board,
    )

    cycle["action"] = task["task_type"]
    cycle["work"] = task.get("work_title", "")
    cycle["result_status"] = result["status"]
    cycle["duration_s"] = result["duration_s"]
    cycle["tokens"] = result["tokens"]
    cycle["answer"] = result["raw"][:200] if result["raw"] else ""

    # 6. Log cycle
    with open(CYCLE_LOG, "a") as f:
        f.write(json.dumps(cycle, ensure_ascii=False) + "\n")

    return cycle


def print_cycle(cycle: dict) -> None:
    print(f"\n=== CYCLE @ {cycle['at'][:19]} ===")
    if cycle.get("retried"):
        print(f"  retried: {cycle['retried']}")
    print(f"  works: {cycle.get('works', '?')}")
    print(f"  new_tasks: {cycle.get('new_tasks', 0)}")
    print(f"  action: {cycle.get('action', '?')}")
    if cycle.get("work"):
        print(f"  work: {cycle['work']}")
    if cycle.get("result_status"):
        print(f"  status: {cycle['result_status']} ({cycle.get('duration_s',0):.1f}s, {cycle.get('tokens',0)} tokens)")
    if cycle.get("answer"):
        print(f"  answer: {cycle['answer'][:150]}")


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycle", action="store_true")
    ap.add_argument("--autonomous", action="store_true")
    ap.add_argument("--max-cycles", type=int, default=5)
    a = ap.parse_args()

    board = KanbanBoard()

    if a.cycle:
        c = run_cycle(board)
        print_cycle(c)
        return 0

    if a.autonomous:
        print(f"=== AUTONOMOUS ({a.max_cycles} cycles, mimo-v2.5) ===")
        for i in range(a.max_cycles):
            print(f"\n--- Cycle {i+1}/{a.max_cycles} ---")
            c = run_cycle(board)
            print_cycle(c)

        # Summary
        print(f"\n=== SUMMARY ===")
        st = board.status()
        print(f"  total tasks: {st['total']}")
        for s, n in st["by_state"].items():
            print(f"    {s:15} {n}")

        results = list(RESULTS_DIR.glob("*.json"))
        print(f"  results saved: {len(results)}")
        for f in sorted(results)[-3:]:
            r = json.loads(f.read_text())
            print(f"    {r['status']:6} {r['task_type']:22} {r['work_title']:25} {r['duration_s']:.0f}s")

        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
