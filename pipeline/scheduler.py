#!/usr/bin/env python3
"""pipeline/scheduler.py — agent-aware, diversity-preserving task dispatch.

The scheduler:
  - Reads READY tasks from kanban
  - Picks DIVERSE task types (not all same type)
  - Spawns agents with budgets
  - Dispatches and tracks via kanban

Usage:
  python3 pipeline/scheduler.py --status
  python3 pipeline/scheduler.py --dispatch
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT / "pipeline"))

from agent_pool import AgentPool
from kanban_board import KanbanBoard
from hermes_integration import spawn_with_budget, BUDGETS, TokenBudget

TASK_WORKER_MAP = {
    "FIND_SOURCE": "discovery", "FIND_ETEXT": "discovery", "FIND_EDITION": "discovery",
    "RESOLVE_IDENTITY": "resolver", "RESOLVE_RIGHTS": "resolver",
    "FETCH_RESOURCE": "fetcher", "OCR_RESOURCE": "fetcher",
    "NORMALIZE_ETEXT": "normalizer",
    "SEARCH_TRANSLATION": "searcher",
    "TRANSLATE": "translator",
    "ANCHOR_TRANSLATION": "aligner",
}


class Scheduler:
    def __init__(self):
        self.pool = AgentPool()
        self.board = KanbanBoard()

    def dispatch_batch(self, max_dispatch: int = 8, max_agents: int = 8) -> list[dict]:
        """Dispatch READY tasks with type diversity.

        Picks at most 2 tasks per type to prevent all-aligner problem.
        """
        dispatched = []
        ready = self.board.ready_tasks()
        ready.sort(key=lambda t: -t.get("priority", 0))

        # Track how many of each type we've dispatched this batch
        type_count: dict[str, int] = {}
        MAX_PER_TYPE = 2

        working = self.pool.working_agents()

        for task in ready:
            if len(dispatched) >= max_dispatch:
                break
            if len(working) + len(dispatched) >= max_agents:
                break

            task_type = task["task_type"]

            # Enforce diversity: max 2 per type per batch
            if type_count.get(task_type, 0) >= MAX_PER_TYPE:
                continue

            worker_type = TASK_WORKER_MAP.get(task_type, "discovery")

            # Find idle agent
            idle = self.pool.idle_agents(agent_type=worker_type)
            if idle:
                agent_id = idle[0].agent_id
            else:
                if len(working) + len(dispatched) + 1 > max_agents:
                    break
                rec, cmd = spawn_with_budget(
                    self.pool, task_type, task["task_id"],
                    task.get("work_id", ""), task.get("work_title", ""),
                )
                agent_id = rec.agent_id

            self.board.assign(task["task_id"], agent_id)
            self.board.start_work(task["task_id"])
            type_count[task_type] = type_count.get(task_type, 0) + 1

            dispatched.append({
                "task_id": task["task_id"],
                "task_type": task_type,
                "work_id": task.get("work_id", ""),
                "work_title": task.get("work_title", ""),
                "agent_id": agent_id,
                "priority": task.get("priority", 0),
            })

        return dispatched

    def status(self) -> dict:
        board_status = self.board.status()
        pool_status = self.pool.status()
        return {
            "board": board_status,
            "pool": pool_status,
            "ready": len(self.board.ready_tasks()),
        }

    def print_status(self) -> None:
        st = self.status()
        print(f"=== SCHEDULER STATUS ===")
        print(f"  board: {st['board']['total']} tasks ({st['ready']} ready)")
        print(f"  pool: {st['pool']['total']} agents ({st['pool']['idle']} idle, "
              f"{st['pool']['working']} working, {st['pool']['failed']} failed)")
        for state, n in st["board"]["by_state"].items():
            print(f"    {state:15} {n}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--dispatch", action="store_true")
    ap.add_argument("--max-dispatch", type=int, default=8)
    a = ap.parse_args()
    sched = Scheduler()
    if a.status:
        sched.print_status()
        return 0
    if a.dispatch:
        dispatched = sched.dispatch_batch(a.max_dispatch)
        print(f"dispatched {len(dispatched)} tasks")
        for d in dispatched:
            print(f"  {d['task_type']:22} → {d['work_title']:30} agent={d['agent_id']}")
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
