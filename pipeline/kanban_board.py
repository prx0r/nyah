#!/usr/bin/env python3
"""pipeline/kanban_board.py — kanban state machine for task lifecycle.

Manages tasks as kanban cards through states:
  BACKLOG → READY → DISPATCHED → IN_PROGRESS → DONE
                                        ↓
                                     FAILED → BACKLOG (retry) or ESCALATED

Each state transition is logged. The board answers:
  What's in each column?
  What's ready to dispatch?
  What's blocked?
  What failed and needs retry?

Usage:
  python3 pipeline/kanban_board.py --status
  python3 pipeline/kanban_board.py --move <task_id> --to <state>
  python3 pipeline/kanban_board.py --demo
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOARD_FILE = ROOT / "data" / "kanban.json"

# Valid states and transitions
STATES = ["BACKLOG", "READY", "DISPATCHED", "IN_PROGRESS", "DONE", "FAILED", "ESCALATED"]
TRANSITIONS = {
    "BACKLOG": ["READY"],
    "READY": ["DISPATCHED", "IN_PROGRESS", "DONE", "FAILED"],
    "DISPATCHED": ["IN_PROGRESS"],
    "IN_PROGRESS": ["DONE", "FAILED"],
    "FAILED": ["BACKLOG", "ESCALATED"],
    "DONE": [],
    "ESCALATED": [],
}


class KanbanBoard:
    """Kanban board for task lifecycle management."""

    def __init__(self):
        self.tasks: dict[str, dict] = {}
        self.history: list[dict] = []
        self._load()

    def _load(self) -> None:
        if BOARD_FILE.exists():
            data = json.loads(BOARD_FILE.read_text())
            self.tasks = data.get("tasks", {})
            self.history = data.get("history", [])

    def _save(self) -> None:
        BOARD_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "updated": datetime.now(timezone.utc).isoformat(),
            "tasks": self.tasks,
            "history": self.history[-500:],  # keep last 500 transitions
        }
        BOARD_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def add_task(self, task_id: str, task_type: str, work_id: str, work_title: str,
                 priority: float = 0.0, assigned_agent: str | None = None,
                 metadata: dict | None = None) -> None:
        """Add a new task to the BACKLOG."""
        now = datetime.now(timezone.utc).isoformat()
        self.tasks[task_id] = {
            "task_id": task_id, "task_type": task_type,
            "work_id": work_id, "work_title": work_title,
            "state": "BACKLOG", "priority": priority,
            "assigned_agent": assigned_agent,
            "metadata": metadata or {},
            "created_at": now, "updated_at": now,
            "state_history": [{"state": "BACKLOG", "at": now}],
            "retry_count": 0,
        }
        self._save()

    def move(self, task_id: str, new_state: str, reason: str = "") -> bool:
        """Move a task to a new state. Returns False if invalid transition."""
        task = self.tasks.get(task_id)
        if not task:
            print(f"task not found: {task_id}")
            return False

        old_state = task["state"]
        if new_state not in TRANSITIONS.get(old_state, []):
            print(f"invalid transition: {old_state} → {new_state} (allowed: {TRANSITIONS.get(old_state, [])})")
            return False

        now = datetime.now(timezone.utc).isoformat()
        task["state"] = new_state
        task["updated_at"] = now
        task["state_history"].append({"state": new_state, "at": now, "reason": reason})

        # auto-increment retry count on FAILED → BACKLOG
        if old_state == "FAILED" and new_state == "BACKLOG":
            task["retry_count"] = task.get("retry_count", 0) + 1

        # log to history
        self.history.append({
            "task_id": task_id, "from": old_state, "to": new_state,
            "at": now, "reason": reason,
        })

        self._save()
        return True

    def assign(self, task_id: str, agent_id: str) -> bool:
        """Assign an agent to a task and move to DISPATCHED."""
        task = self.tasks.get(task_id)
        if not task:
            return False
        task["assigned_agent"] = agent_id
        self.move(task_id, "DISPATCHED", f"assigned to {agent_id}")
        return True

    def start_work(self, task_id: str) -> bool:
        """Move task to IN_PROGRESS."""
        return self.move(task_id, "IN_PROGRESS")

    def complete(self, task_id: str, success: bool = True, reason: str = "") -> bool:
        """Complete a task (DONE or FAILED)."""
        if success:
            return self.move(task_id, "DONE", reason or "completed")
        else:
            return self.move(task_id, "FAILED", reason or "failed")

    def escalate(self, task_id: str, reason: str = "") -> bool:
        """Escalate a failed task."""
        return self.move(task_id, "ESCALATED", reason)

    def retry(self, task_id: str, max_retries: int = 3) -> bool:
        """Retry a failed task (move back to BACKLOG if under retry limit)."""
        task = self.tasks.get(task_id)
        if not task:
            return False
        if task.get("retry_count", 0) >= max_retries:
            return self.escalate(task_id, f"max retries ({max_retries}) exceeded")
        return self.move(task_id, "BACKLOG", f"retry #{task.get('retry_count', 0) + 1}")

    def ready_tasks(self, task_type: str | None = None) -> list[dict]:
        """Get tasks in READY state, optionally filtered by type."""
        return [
            t for t in self.tasks.values()
            if t["state"] == "READY" and (task_type is None or t["task_type"] == task_type)
        ]

    def blocked_tasks(self) -> list[dict]:
        """Get tasks in FAILED or ESCALATED state."""
        return [t for t in self.tasks.values() if t["state"] in ("FAILED", "ESCALATED")]

    def by_state(self) -> dict[str, list[dict]]:
        """Group tasks by state."""
        result = {s: [] for s in STATES}
        for t in self.tasks.values():
            result[t["state"]].append(t)
        return result

    def status(self) -> dict:
        """Board status summary."""
        by_state = {}
        for t in self.tasks.values():
            s = t["state"]
            by_state[s] = by_state.get(s, 0) + 1
        return {
            "total": len(self.tasks),
            "by_state": by_state,
            "blocked": len(self.blocked_tasks()),
        }

    def print_status(self) -> None:
        st = self.status()
        print(f"=== KANBAN BOARD ({st['total']} tasks) ===")
        for s in STATES:
            n = st["by_state"].get(s, 0)
            if n > 0:
                print(f"  {s:15} {n}")

        # show ready tasks
        ready = self.ready_tasks()
        if ready:
            print(f"\n=== READY TO DISPATCH ({len(ready)}) ===")
            for t in sorted(ready, key=lambda x: -x.get("priority", 0))[:10]:
                print(f"  {t['task_type']:22} {t['work_title']:30} p={t.get('priority', 0):.3f}")

        # show blocked
        blocked = self.blocked_tasks()
        if blocked:
            print(f"\n=== BLOCKED ({len(blocked)}) ===")
            for t in blocked[:5]:
                retries = t.get("retry_count", 0)
                print(f"  {t['state']:10} {t['task_type']:22} {t['work_title']:30} retries={retries}")


def demo() -> None:
    board = KanbanBoard()

    print("=== INITIAL ===")
    board.print_status()

    # add tasks
    board.add_task("t1", "FIND_SOURCE", "PTW_003", "Vijnanabhairava", priority=0.8)
    board.add_task("t2", "TRANSLATE", "PTW_001", "Tantraloka", priority=0.7)
    board.add_task("t3", "RESOLVE_IDENTITY", "PTW_002", "Spandakarika", priority=0.9)
    board.add_task("t4", "ANCHOR_TRANSLATION", "PTW_004", "Isvarapratyabhijnavimarsini", priority=0.5)

    # move through states
    board.move("t1", "READY")
    board.move("t2", "READY")
    board.move("t3", "READY")
    board.move("t4", "READY")

    board.assign("t1", "agent_discovery_001")
    board.assign("t2", "agent_translator_001")

    board.start_work("t1")
    board.start_work("t2")

    board.complete("t1", success=True)
    board.complete("t2", success=False, reason="model timeout")

    # retry the failed one
    board.retry("t2")

    print("\n=== AFTER OPERATIONS ===")
    board.print_status()

    print("\n=== HISTORY ===")
    for h in board.history:
        print(f"  {h['task_id']:5} {h['from']:15} → {h['to']:15} {h.get('reason', '')}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--move", default="", help="task_id to move")
    ap.add_argument("--to", default="", help="target state")
    ap.add_argument("--reason", default="")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        demo()
        return 0
    board = KanbanBoard()
    if a.status:
        board.print_status()
        return 0
    if a.move and a.to:
        board.move(a.move, a.to, a.reason)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
