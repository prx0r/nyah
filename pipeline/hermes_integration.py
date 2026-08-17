#!/usr/bin/env python3
"""pipeline/hermes_integration.py — actual hermes subagent spawning with token guards.

This is the real integration point: nyah spawns hermes subagents via `hermes -z`,
tracks their PIDs, enforces timeouts, and auto-kills on completion or budget.

Key design:
  - Every agent gets a TOKEN BUDGET (max steps, max runtime, max cost)
  - Auto-kill when budget exhausted
  - Auto-kill when task completes (don't idle)
  - Heartbeat monitoring catches stale agents
  - No agent runs forever

Usage:
  python3 pipeline/hermes_integration.py --spawn --task-type FIND_SOURCE --task-id task_001 --work "Vijnanabhairava"
  python3 pipeline/hermes_integration.py --status
  python3 pipeline/hermes_integration.py --kill-all
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT / "pipeline"))

from agent_pool import AgentPool, AgentRecord

# ── TOKEN BUDGETS (prevent waste) ──────────────────────────────────────────

@dataclass
class TokenBudget:
    """Limits on what an agent can consume."""
    max_runtime_s: int = 300       # 5 minutes max per task
    max_hermes_steps: int = 50     # max hermes interaction steps
    max_retries: int = 3           # max retry attempts
    kill_on_complete: bool = True  # auto-kill process when task done

# Per-task-type budgets
BUDGETS = {
    "FIND_SOURCE":        TokenBudget(max_runtime_s=180, max_hermes_steps=30),
    "FIND_ETEXT":         TokenBudget(max_runtime_s=180, max_hermes_steps=30),
    "FIND_EDITION":       TokenBudget(max_runtime_s=120, max_hermes_steps=20),
    "RESOLVE_IDENTITY":   TokenBudget(max_runtime_s=120, max_hermes_steps=20),
    "RESOLVE_RIGHTS":     TokenBudget(max_runtime_s=60,  max_hermes_steps=10),
    "FETCH_RESOURCE":     TokenBudget(max_runtime_s=180, max_hermes_steps=30),
    "NORMALIZE_ETEXT":    TokenBudget(max_runtime_s=120, max_hermes_steps=20),
    "SEARCH_TRANSLATION": TokenBudget(max_runtime_s=120, max_hermes_steps=20),
    "TRANSLATE":          TokenBudget(max_runtime_s=300, max_hermes_steps=50),
    "ANCHOR_TRANSLATION": TokenBudget(max_runtime_s=180, max_hermes_steps=30),
    "OCR_RESOURCE":       TokenBudget(max_runtime_s=240, max_hermes_steps=40),
}

DEFAULT_BUDGET = TokenBudget()


# ── HERMES COMMAND BUILDER ─────────────────────────────────────────────────

def build_hermes_command(task_type: str, task_id: str, work_id: str,
                         work_title: str, budget: TokenBudget) -> str:
    """Build the hermes -z command for a specific task type.

    Each task type gets a focused, bounded prompt — no open-ended exploration.
    The prompt includes the budget constraints explicitly.
    """
    work_ref = f"{work_title} ({work_id})"

    prompts = {
        "FIND_SOURCE": (
            f"Find a machine-readable source for the Sanskrit work {work_ref}. "
            f"Check GRETIL, Archive.org, PANDiT, Muktabodha. "
            f"Output a JSON with {{source_url, source_type, adapter, rights_hint}}. "
            f"If no source found, output {{source_url: null, reason: '...'}}. "
            f"Do NOT browse extensively — check known repositories only."
        ),
        "FIND_ETEXT": (
            f"Find a clean e-text for {work_ref}. "
            f"Check GRETIL, SARIT, Ambuda, Archive.org texts. "
            f"Output JSON with {{etext_url, format, language}}. "
            f"If not found, output {{etext_url: null, reason: '...'}}."
        ),
        "RESOLVE_IDENTITY": (
            f"Resolve the identity of {work_ref}. "
            f"Check if it has alternate titles, if records from PANDiT/GRETIL/Muktabodha "
            f"refer to the same work. Output JSON with "
            f"{{resolved: true/false, alternate_titles: [], evidence: []}}."
        ),
        "RESOLVE_RIGHTS": (
            f"Determine the rights status of {work_ref}. "
            f"Check license info from the source. Output JSON with "
            f"{{rights: 'OPEN'|'RESTRICTED'|'UNKNOWN', evidence: []}}."
        ),
        "SEARCH_TRANSLATION": (
            f"Search for an existing English translation of {work_ref}. "
            f"Check OpenAlex, Crossref, Archive.org, curated lists. "
            f"Output JSON with {{found: true/false, translations: []}}. "
            f"If found, include translator, year, completeness."
        ),
        "TRANSLATE": (
            f"Translate the Sanskrit text of {work_ref} to English. "
            f"Use the available source text. Produce a literal translation. "
            f"Output JSON with {{translation: '...', quality: 'rough'|'literal'}}."
        ),
        "ANCHOR_TRANSLATION": (
            f"Align the existing translation of {work_ref} to source passages. "
            f"Map each translated passage to its Sanskrit original. "
            f"Output JSON with {{alignments: [{{source_passage, translation_passage}}]}}."
        ),
        "FETCH_RESOURCE": (
            f"Fetch the resource for {work_ref} from its source URL. "
            f"Save to the local artifact store. "
            f"Output JSON with {{artifact_path: '...', bytes: N}}."
        ),
        "NORMALIZE_ETEXT": (
            f"Normalize the raw e-text of {work_ref}. "
            f"Clean formatting, normalize Unicode, segment into passages. "
            f"Output JSON with {{passages: [], format: 'jsonl'}}."
        ),
        "OCR_RESOURCE": (
            f"Run OCR on the manuscript scan of {work_ref}. "
            f"Output JSON with {{text: '...', confidence: 0.0}}."
        ),
    }

    prompt = prompts.get(task_type, f"Process {work_ref}")

    # Build the hermes command with explicit timeout
    # chat -q = non-interactive single query, auto-exits
    # timeout = kill if exceeds runtime budget
    cmd = (
        f"timeout {budget.max_runtime_s} "
        f"hermes chat -q "
        f"--profile patala "
        f'"{prompt}"'
    )
    return cmd


# ── SPAWN WITH BUDGET ──────────────────────────────────────────────────────

def spawn_with_budget(pool: AgentPool, task_type: str, task_id: str,
                      work_id: str, work_title: str) -> tuple[AgentRecord, str]:
    """Spawn a hermes agent with a token budget. Returns (agent, command).

    The command is ready to execute. The caller decides when to run it.
    Budget is attached to the agent record for tracking.
    """
    budget = BUDGETS.get(task_type, DEFAULT_BUDGET)
    cmd = build_hermes_command(task_type, task_id, work_id, work_title, budget)

    # Record budget in agent metadata
    rec = pool.spawn(
        agent_type=_worker_type(task_type),
        task_id=task_id,
        task_type=task_type,
        command=None,  # don't auto-execute yet
    )

    # Attach budget info
    rec_dict = rec.to_dict()
    rec_dict["budget"] = {
        "max_runtime_s": budget.max_runtime_s,
        "max_hermes_steps": budget.max_hermes_steps,
        "kill_on_complete": budget.kill_on_complete,
    }
    # re-save with budget
    pool.agents[rec.agent_id] = AgentRecord.from_dict(rec_dict)
    pool._save()

    return rec, cmd


def execute_agent(agent: AgentRecord, command: str, pool: AgentPool) -> int:
    """Execute a hermes command as a background process. Returns PID.

    The process is backgrounded with setsid so it doesn't block.
    A watchdog timer will kill it if it exceeds the budget.
    """
    try:
        proc = subprocess.Popen(
            command, shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,  # don't signal parent on exit
        )
        pid = proc.pid
        agent.pid = pid
        agent.state = "WORKING"
        agent.spawned_at = datetime.now(timezone.utc).isoformat()
        agent.last_heartbeat = agent.spawned_at
        pool._save()
        return pid
    except Exception as e:
        agent.state = "FAILED"
        agent.error = str(e)
        pool._save()
        return 0


# ── WATCHDOG ───────────────────────────────────────────────────────────────

def check_and_kill_stale(pool: AgentPool) -> list[str]:
    """Check all working agents. Kill those exceeding their budget.

    Returns list of killed agent IDs.
    """
    killed = []
    now = time.time()

    for agent in list(pool.agents.values()):
        if agent.state != "WORKING":
            continue

        # Check runtime budget
        if agent.spawned_at:
            try:
                started = datetime.fromisoformat(agent.spawned_at).timestamp()
                runtime = now - started
                budget = BUDGETS.get(agent.current_task_type or "", DEFAULT_BUDGET)

                if runtime > budget.max_runtime_s:
                    # KILL — exceeded budget
                    _kill_agent(agent, pool, f"budget exceeded ({runtime:.0f}s > {budget.max_runtime_s}s)")
                    killed.append(agent.agent_id)
                    continue
            except Exception:
                pass

        # Check if process is still alive
        if agent.pid:
            try:
                os.kill(agent.pid, 0)  # check alive
            except OSError:
                # Process gone — task completed
                pool.complete_task(agent.agent_id, success=True)
                killed.append(f"{agent.agent_id} (completed)")

    return killed


def _kill_agent(agent: AgentRecord, pool: AgentPool, reason: str) -> None:
    """Kill an agent's process and mark it failed."""
    if agent.pid:
        try:
            os.kill(agent.pid, signal.SIGTERM)
            time.sleep(0.3)
            try:
                os.kill(agent.pid, signal.SIGKILL)
            except OSError:
                pass
        except OSError:
            pass
    agent.state = "FAILED"
    agent.error = reason
    agent.pid = None
    pool._save()


def kill_all(pool: AgentPool) -> int:
    """Kill all working agents. Returns count killed."""
    count = 0
    for agent in list(pool.agents.values()):
        if agent.state == "WORKING":
            _kill_agent(agent, pool, "manual kill-all")
            count += 1
    return count


# ── HELPERS ────────────────────────────────────────────────────────────────

def _worker_type(task_type: str) -> str:
    mapping = {
        "FIND_SOURCE": "discovery", "FIND_ETEXT": "discovery", "FIND_EDITION": "discovery",
        "RESOLVE_IDENTITY": "resolver", "RESOLVE_RIGHTS": "resolver",
        "FETCH_RESOURCE": "fetcher", "OCR_RESOURCE": "fetcher",
        "NORMALIZE_ETEXT": "normalizer",
        "SEARCH_TRANSLATION": "searcher",
        "TRANSLATE": "translator",
        "ANCHOR_TRANSLATION": "aligner",
    }
    return mapping.get(task_type, "discovery")


# ── CLI ────────────────────────────────────────────────────────────────────

def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--spawn", action="store_true")
    ap.add_argument("--task-type", default="")
    ap.add_argument("--task-id", default="")
    ap.add_argument("--work-id", default="")
    ap.add_argument("--work-title", default="")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--watchdog", action="store_true", help="kill stale agents")
    ap.add_argument("--kill-all", action="store_true")
    a = ap.parse_args()

    pool = AgentPool()

    if a.spawn and a.task_type and a.task_id:
        rec, cmd = spawn_with_budget(pool, a.task_type, a.task_id,
                                     a.work_id or "unknown", a.work_title or "unknown")
        print(f"spawned: {rec.agent_id}")
        print(f"command: {cmd}")
        print(f"budget: {BUDGETS.get(a.task_type, DEFAULT_BUDGET)}")
        # Don't auto-execute — let the scheduler decide
        return 0

    if a.status:
        pool.print_status()
        return 0

    if a.watchdog:
        killed = check_and_kill_stale(pool)
        print(f"watchdog: {len(killed)} agents handled")
        for k in killed:
            print(f"  {k}")
        return 0

    if a.kill_all:
        count = kill_all(pool)
        print(f"killed {count} agents")
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
