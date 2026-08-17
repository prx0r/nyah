#!/usr/bin/env python3
"""agent/run.py — the NYAH COORDINATOR (advanced agent orchestration).

This is the real nyah: an advanced agent coordinator that manages hermes subagents,
runs the full autonomous pipeline, handles failures, and coordinates OpenPatala's
epistemic work queue.

Generic steps (from agentic-infra):
  report, verify, trace, ramwatch, checkpoints, autonomous

Domain coordinator steps (nyah-specific):
  gaps        — scan OpenPatala state + generate gap-prioritized tasks
  scan        — register tasks on kanban board
  dispatch    — assign READY tasks to idle/spawned agents
  cycle       — run one full coordination cycle (scan→register→promote→dispatch→handle)
  agents      — agent pool status
  kanban      — kanban board status
  pipeline    — pipeline runner status
  failure     — failure handler stats
  spawn       — spawn an agent for a specific task
  kill        — kill an agent by ID

Usage:
  python3 agent/run.py --step cycle          # one full coordination cycle
  python3 agent/run.py --step agents         # who's running
  python3 agent/run.py --step kanban         # task board
  python3 agent/run.py --step dispatch       # dispatch now
  python3 agent/run.py --step report         # summary
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))


def _sh(*args: str, timeout: int = 300) -> str:
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return f"__TIMEOUT__ {' '.join(args)}"


def _log(record: dict) -> None:
    reg = ROOT / "data" / "runs" / "agent-steps.jsonl"
    reg.parent.mkdir(parents=True, exist_ok=True)
    record["ts"] = datetime.now(timezone.utc).isoformat()
    with open(reg, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ── COORDINATOR STEPS ──────────────────────────────────────────────────────

def step_cycle() -> dict:
    """Run one full coordination cycle: scan→register→promote→dispatch→handle."""
    from pipeline_runner import PipelineRunner
    runner = PipelineRunner()
    cycle = runner.run_cycle()
    runner.print_cycle(cycle)

    s = cycle["summary"]
    out = (f"cycle complete: {s['total_tasks']} tasks, "
           f"agents: idle={s['agents']['idle']} working={s['agents']['working']}")
    rec = {"step": "cycle", "output": out, "cycle_summary": s}
    _log(rec)
    return rec


def step_gaps() -> dict:
    """Scan OpenPatala state and show gap priorities."""
    from pipeline_runner import PipelineRunner
    runner = PipelineRunner()
    tasks = runner.scan_gaps()

    out = f"gap analysis: {len(tasks)} gaps found"
    print(out)
    print(f"\n{'PRIORITY':>8}  {'TYPE':22}  {'WORK':30}  DESCRIPTION")
    print("-" * 90)
    for t in tasks[:20]:
        print(f"{t['priority']:8.3f}  {t['task_type']:22}  {t['work_title']:30}  {t['description']}")

    rec = {"step": "gaps", "n_gaps": len(tasks), "output": out}
    _log(rec)
    return rec


def step_scan() -> dict:
    """Register gaps as tasks on the kanban board."""
    from pipeline_runner import PipelineRunner
    runner = PipelineRunner()
    tasks = runner.scan_gaps()
    registered = runner.register_tasks(tasks)
    promoted = runner.promote_ready()

    out = f"scan: {len(tasks)} gaps → {registered} new tasks → {promoted} promoted to READY"
    print(out)
    rec = {"step": "scan", "n_gaps": len(tasks), "registered": registered, "promoted": promoted}
    _log(rec)
    return rec


def step_dispatch() -> dict:
    """Dispatch READY tasks to agents."""
    from scheduler import Scheduler
    sched = Scheduler()
    dispatched = sched.dispatch_batch()

    out = f"dispatch: {len(dispatched)} tasks dispatched"
    for d in dispatched:
        out += f"\n  {d['task_type']:22} → {d['work_title']:30} agent={d['agent_id']}"
    print(out)
    rec = {"step": "dispatch", "n_dispatched": len(dispatched), "output": out}
    _log(rec)
    return rec


def step_agents() -> dict:
    """Agent pool status."""
    from agent_pool import AgentPool
    pool = AgentPool()
    pool.print_status()

    st = pool.status()
    out = f"agents: {st['total']} total, idle={st['idle']}, working={st['working']}, failed={st['failed']}"
    rec = {"step": "agents", "output": out}
    _log(rec)
    return rec


def step_kanban() -> dict:
    """Kanban board status."""
    from kanban_board import KanbanBoard
    board = KanbanBoard()
    board.print_status()

    st = board.status()
    out = f"kanban: {st['total']} tasks, {st['blocked']} blocked"
    rec = {"step": "kanban", "output": out}
    _log(rec)
    return rec


def step_pipeline() -> dict:
    """Pipeline runner status."""
    from pipeline_runner import PipelineRunner
    runner = PipelineRunner()
    board_status = runner.board.status()
    pool_status = runner.pool.status()

    out = (f"pipeline: {board_status['total']} tasks, "
           f"agents: {pool_status['total']}")
    print(out)
    rec = {"step": "pipeline", "output": out}
    _log(rec)
    return rec


def step_autonomous() -> dict:
    """Run autonomous mode: up to 3 cycles, executing real tasks."""
    from pipeline_runner import PipelineRunner
    runner = PipelineRunner()
    results = []
    completions = 0

    for i in range(3):
        cycle = runner.run_cycle()
        runner.print_cycle(cycle)
        r = cycle["summary"].get("last_result", {})
        results.append(r)
        if r.get("status") == "DONE":
            completions += 1

    out = f"autonomous: 3 cycles, {completions} completions"
    rec = {"step": "autonomous", "completions": completions, "results": results}
    _log(rec)
    print(out)
    return rec


def step_watchdog() -> dict:
    """Kill stale agents that exceeded their token budget."""
    from hermes_integration import check_and_kill_stale
    from agent_pool import AgentPool
    pool = AgentPool()
    killed = check_and_kill_stale(pool)
    out = f"watchdog: {len(killed)} agents handled"
    for k in killed:
        out += f"\n  {k}"
    print(out)
    rec = {"step": "watchdog", "killed": len(killed), "output": out}
    _log(rec)
    return rec


def step_killall() -> dict:
    """Kill all running agents (emergency stop)."""
    from hermes_integration import kill_all
    from agent_pool import AgentPool
    pool = AgentPool()
    count = kill_all(pool)
    out = f"kill-all: {count} agents killed"
    print(out)
    rec = {"step": "killall", "killed": count, "output": out}
    _log(rec)
    return rec


def step_results() -> dict:
    """Show task execution results."""
    from agent_executor import get_results_summary, RESULTS_DIR
    summary = get_results_summary()
    print(json.dumps(summary, indent=2))
    if RESULTS_DIR.exists():
        for f in sorted(RESULTS_DIR.glob("*.json"))[-5:]:
            r = json.loads(f.read_text())
            status = r.get("status", "?")
            task = r.get("task_id", "?")
            dur = r.get("duration_s", 0)
            print(f"  {status:8} {task:40} {dur:.0f}s")
            if r.get("parsed"):
                print(f"           parsed: {json.dumps(r['parsed'], ensure_ascii=False)[:150]}")
    rec = {"step": "results", "output": json.dumps(summary)}
    _log(rec)
    return rec


def step_report() -> dict:
    """Full coordinator report."""
    from agent_pool import AgentPool
    from kanban_board import KanbanBoard
    from failure_handler import get_failure_stats
    from openpatala_bridge import convert_all

    pool = AgentPool()
    board = KanbanBoard()
    failures = get_failure_stats()
    works = convert_all()

    pool_st = pool.status()
    board_st = board.status()

    out = f"""=== NYAH COORDINATOR REPORT ===

OPENPATALA: {len(works)} works loaded

AGENT POOL: {pool_st['total']} agents
  idle: {pool_st['idle']}  working: {pool_st['working']}  failed: {pool_st['failed']}

KANBAN BOARD: {board_st['total']} tasks"""
    for state, n in board_st["by_state"].items():
        out += f"\n  {state:15} {n}"

    out += f"""

FAILURES: {failures['total']} total
  {failures['by_classification']}

GATE: """
    gate = _sh("python3", str(ROOT / "check.py"), "--status", timeout=60)
    out += gate

    print(out)
    rec = {"step": "report", "output": out[-2000:]}
    _log(rec)
    return rec


def step_trace(q: str) -> dict:
    out = _sh("python3", str(ROOT / "agent" / "trace.py"),
              *(["--search", q] if q else ["--recent", "10"]), timeout=120)
    rec = {"step": "trace", "query": q, "output": out[-1000:]}
    _log(rec)
    print(out)
    return rec


def step_ramwatch() -> dict:
    out = _sh("python3", str(ROOT / "agent" / "ramwatch.py"), timeout=60)
    rec = {"step": "ramwatch", "output": out[-500:]}
    _log(rec)
    print(out)
    return rec


def step_checkpoint() -> dict:
    out = _sh("python3", str(ROOT / "pipeline" / "checkpoint.py"), "--status", timeout=120)
    rec = {"step": "checkpoint", "output": out[-1500:]}
    _log(rec)
    print(out)
    return rec


STEPS = {
    "cycle": step_cycle, "gaps": step_gaps, "scan": step_scan,
    "dispatch": step_dispatch, "agents": step_agents, "kanban": step_kanban,
    "pipeline": step_pipeline, "autonomous": step_autonomous,
    "results": step_results, "watchdog": step_watchdog,
    "killall": step_killall, "report": step_report,
    "trace": step_trace, "ramwatch": step_ramwatch, "checkpoint": step_checkpoint,
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", required=True, choices=list(STEPS))
    ap.add_argument("--search", default="")
    a = ap.parse_args()
    if a.step == "trace":
        step_trace(a.search)
    else:
        STEPS[a.step]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
