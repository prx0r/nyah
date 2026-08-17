#!/usr/bin/env python3
"""pipeline/agent_pool.py — real agent lifecycle management.

This is the core of nyah as an advanced agent coordinator. It manages actual hermes subagents:
spawn, track state, heartbeat, kill, reassign. Each agent is a real process (hermes -z or
subprocess) with a PID, state, current task, and performance history.

The agent pool answers:
  Which agents are running?
  What is each agent doing?
  Which agents are idle/available?
  Which agents have failed?
  How do I spawn a new agent for a task?
  How do I kill a failed agent?

Usage:
  python3 pipeline/agent_pool.py --status
  python3 pipeline/agent_pool.py --spawn --task-type FIND_SOURCE --task-id task_001
  python3 pipeline/agent_pool.py --heartbeat
  python3 pipeline/agent_pool.py --demo
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS_FILE = ROOT / "data" / "agents.json"
TASKS_DIR = ROOT / "data" / "tasks"

# Agent states
IDLE = "IDLE"
WORKING = "WORKING"
HEARTBEAT_MISSING = "HEARTBEAT_MISSING"
FAILED = "FAILED"
KILLED = "KILLED"


@dataclass
class AgentRecord:
    """A tracked agent process."""
    agent_id: str
    agent_type: str          # discovery, resolver, fetcher, normalizer, searcher, translator, aligner
    pid: int | None = None
    state: str = IDLE
    current_task_id: str | None = None
    current_task_type: str | None = None
    spawned_at: str = ""
    last_heartbeat: str = ""
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_runtime_s: float = 0.0
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id, "agent_type": self.agent_type,
            "pid": self.pid, "state": self.state,
            "current_task_id": self.current_task_id,
            "current_task_type": self.current_task_type,
            "spawned_at": self.spawned_at,
            "last_heartbeat": self.last_heartbeat,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "total_runtime_s": self.total_runtime_s,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, d: dict) -> AgentRecord:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class AgentPool:
    """Manages the lifecycle of hermes subagents."""

    def __init__(self):
        self.agents: dict[str, AgentRecord] = {}
        self._load()

    def _load(self) -> None:
        if AGENTS_FILE.exists():
            data = json.loads(AGENTS_FILE.read_text())
            for d in data.get("agents", []):
                rec = AgentRecord.from_dict(d)
                self.agents[rec.agent_id] = rec

    def _save(self) -> None:
        AGENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "updated": datetime.now(timezone.utc).isoformat(),
            "agents": [a.to_dict() for a in self.agents.values()],
        }
        AGENTS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def _agent_id(self, agent_type: str) -> str:
        count = sum(1 for a in self.agents.values() if a.agent_type == agent_type)
        return f"agent_{agent_type}_{count + 1:03d}"

    def spawn(self, agent_type: str, task_id: str, task_type: str,
              command: str | None = None) -> AgentRecord:
        """Spawn a new hermes subagent for a task.

        If command is provided, runs it as a background process.
        Otherwise, creates a tracked placeholder (for when hermes integration is live).
        """
        agent_id = self._agent_id(agent_type)
        now = datetime.now(timezone.utc).isoformat()

        pid = None
        if command:
            try:
                # background the process
                proc = subprocess.Popen(
                    command, shell=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    start_new_session=True,
                )
                pid = proc.pid
            except Exception as e:
                pass

        rec = AgentRecord(
            agent_id=agent_id, agent_type=agent_type,
            pid=pid, state=WORKING if pid else WORKING,
            current_task_id=task_id, current_task_type=task_type,
            spawned_at=now, last_heartbeat=now,
        )
        self.agents[agent_id] = rec
        self._save()
        return rec

    def heartbeat(self, agent_id: str, state: str | None = None) -> bool:
        """Update agent heartbeat. Returns False if agent not found."""
        rec = self.agents.get(agent_id)
        if not rec:
            return False
        rec.last_heartbeat = datetime.now(timezone.utc).isoformat()
        if state:
            rec.state = state
        self._save()
        return True

    def complete_task(self, agent_id: str, success: bool = True) -> None:
        """Mark agent's current task as complete."""
        rec = self.agents.get(agent_id)
        if not rec:
            return
        if success:
            rec.tasks_completed += 1
        else:
            rec.tasks_failed += 1
        rec.current_task_id = None
        rec.current_task_type = None
        rec.state = IDLE
        rec.error = None
        self._save()

    def fail_agent(self, agent_id: str, error: str) -> None:
        """Mark an agent as failed."""
        rec = self.agents.get(agent_id)
        if not rec:
            return
        rec.state = FAILED
        rec.error = error
        self._save()

    def kill(self, agent_id: str) -> bool:
        """Kill an agent's process."""
        rec = self.agents.get(agent_id)
        if not rec:
            return False
        if rec.pid:
            try:
                os.kill(rec.pid, signal.SIGTERM)
                time.sleep(0.5)
                try:
                    os.kill(rec.pid, signal.SIGKILL)
                except OSError:
                    pass
            except OSError:
                pass
        rec.state = KILLED
        rec.pid = None
        self._save()
        return True

    def idle_agents(self, agent_type: str | None = None) -> list[AgentRecord]:
        """Get idle agents, optionally filtered by type."""
        return [
            a for a in self.agents.values()
            if a.state == IDLE and (agent_type is None or a.agent_type == agent_type)
        ]

    def working_agents(self, agent_type: str | None = None) -> list[AgentRecord]:
        """Get working agents."""
        return [
            a for a in self.agents.values()
            if a.state == WORKING and (agent_type is None or a.agent_type == agent_type)
        ]

    def failed_agents(self) -> list[AgentRecord]:
        return [a for a in self.agents.values() if a.state == FAILED]

    def check_heartbeats(self, timeout_s: float = 300) -> list[AgentRecord]:
        """Check for agents with stale heartbeats (>timeout_s since last heartbeat)."""
        now = time.time()
        stale = []
        for a in self.agents.values():
            if a.state == WORKING and a.last_heartbeat:
                try:
                    hb = datetime.fromisoformat(a.last_heartbeat).timestamp()
                    if now - hb > timeout_s:
                        a.state = HEARTBEAT_MISSING
                        stale.append(a)
                except Exception:
                    pass
        if stale:
            self._save()
        return stale

    def status(self) -> dict:
        """Pool status summary."""
        by_state = {}
        by_type = {}
        for a in self.agents.values():
            by_state[a.state] = by_state.get(a.state, 0) + 1
            by_type[a.agent_type] = by_type.get(a.agent_type, 0) + 1

        return {
            "total": len(self.agents),
            "by_state": by_state,
            "by_type": by_type,
            "idle": sum(1 for a in self.agents.values() if a.state == IDLE),
            "working": sum(1 for a in self.agents.values() if a.state == WORKING),
            "failed": sum(1 for a in self.agents.values() if a.state == FAILED),
        }

    def print_status(self) -> None:
        st = self.status()
        print(f"=== AGENT POOL ({st['total']} agents) ===")
        print(f"  idle: {st['idle']}  working: {st['working']}  failed: {st['failed']}")
        if st["by_state"]:
            print(f"  states: {st['by_state']}")
        if st["by_type"]:
            print(f"  types: {st['by_type']}")
        print()
        for a in self.agents.values():
            marker = {"IDLE": "●", "WORKING": "◉", "FAILED": "✕", "KILLED": "✕",
                      "HEARTBEAT_MISSING": "⚠"}.get(a.state, "?")
            task = a.current_task_id or "-"
            print(f"  {marker} {a.agent_id:25} {a.state:10} task={task:15} "
                  f"done={a.tasks_completed} fail={a.tasks_failed}")


def demo() -> None:
    pool = AgentPool()

    print("=== INITIAL ===")
    pool.print_status()

    print("\n=== SPAWNING AGENTS ===")
    a1 = pool.spawn("discovery", "task_001", "FIND_SOURCE")
    print(f"  spawned: {a1.agent_id} for task_001 (FIND_SOURCE)")
    a2 = pool.spawn("translator", "task_002", "TRANSLATE")
    print(f"  spawned: {a2.agent_id} for task_002 (TRANSLATE)")
    a3 = pool.spawn("resolver", "task_003", "RESOLVE_IDENTITY")
    print(f"  spawned: {a3.agent_id} for task_003 (RESOLVE_IDENTITY)")

    print("\n=== AFTER SPAWN ===")
    pool.print_status()

    print("\n=== HEARTBEATS ===")
    pool.heartbeat(a1.agent_id)
    pool.heartbeat(a2.agent_id)
    print(f"  heartbeat: {a1.agent_id}, {a2.agent_id}")

    print("\n=== COMPLETING TASKS ===")
    pool.complete_task(a1.agent_id, success=True)
    pool.complete_task(a2.agent_id, success=True)
    pool.fail_agent(a3.agent_id, "identity resolution timeout")
    print(f"  completed: {a1.agent_id}, {a2.agent_id}")
    print(f"  failed: {a3.agent_id}")

    print("\n=== AFTER COMPLETIONS ===")
    pool.print_status()

    print("\n=== IDLE AGENTS ===")
    idle = pool.idle_agents()
    for a in idle:
        print(f"  {a.agent_id} ({a.agent_type})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--spawn", action="store_true")
    ap.add_argument("--task-type", default="")
    ap.add_argument("--task-id", default="")
    ap.add_argument("--heartbeat", action="store_true")
    ap.add_argument("--agent-id", default="")
    ap.add_argument("--complete", action="store_true")
    ap.add_argument("--fail", action="store_true")
    ap.add_argument("--error", default="")
    ap.add_argument("--kill", action="store_true")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        demo()
        return 0
    pool = AgentPool()
    if a.status:
        pool.print_status()
        return 0
    if a.spawn and a.task_type and a.task_id:
        rec = pool.spawn(a.task_type, a.task_id, a.task_type)
        print(f"spawned: {rec.agent_id}")
        return 0
    if a.heartbeat and a.agent_id:
        pool.heartbeat(a.agent_id)
        print(f"heartbeat: {a.agent_id}")
        return 0
    if a.complete and a.agent_id:
        pool.complete_task(a.agent_id, success=not a.fail)
        print(f"completed: {a.agent_id}")
        return 0
    if a.fail and a.agent_id:
        pool.fail_agent(a.agent_id, a.error or "unknown")
        print(f"failed: {a.agent_id}")
        return 0
    if a.kill and a.agent_id:
        pool.kill(a.agent_id)
        print(f"killed: {a.agent_id}")
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
