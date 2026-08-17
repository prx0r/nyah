#!/usr/bin/env python3
"""pipeline/mcp_server.py — MCP server for nyah.

From newbuildplayers §21:
- MCP standardizes model-discoverable tools
- Expose nyah as an MCP server so other agents can use it

Usage:
  python3 pipeline/mcp_server.py --tools   # list available tools
  python3 pipeline/mcp_server.py --call gap_analysis
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT / "pipeline"))


TOOLS = {
    "nyah.gaps": {
        "description": "Analyze OpenPatala completeness state and return prioritized gaps",
        "parameters": {},
    },
    "nyah.tasks": {
        "description": "Generate deterministic tasks from OpenPatala gaps",
        "parameters": {"max_tasks": {"type": "integer", "default": 10}},
    },
    "nyah.status": {
        "description": "Get nyah coordinator status (kanban, pool, results)",
        "parameters": {},
    },
    "nyah.execute": {
        "description": "Execute a task via mimo-v2.5",
        "parameters": {
            "task_type": {"type": "string", "enum": ["RESOLVE_RIGHTS", "FIND_SOURCE", "SEARCH_TRANSLATION", "RESOLVE_IDENTITY"]},
            "work_title": {"type": "string"},
        },
    },
    "nyah.cycle": {
        "description": "Run one coordination cycle (scan → dispatch → execute)",
        "parameters": {},
    },
    "nyah.changes": {
        "description": "Get incremental changes since a cursor",
        "parameters": {"since": {"type": "integer", "default": 0}},
    },
}


def handle_tool(name: str, params: dict) -> dict:
    """Handle an MCP tool call."""
    if name == "nyah.gaps":
        from gap_analyzer import analyze_work
        from openpatala_bridge import convert_all
        works = convert_all()
        all_gaps = []
        for w in works:
            gaps = analyze_work(w)
            all_gaps.extend([{"work": g.work_title, "type": g.gap_type, "priority": g.priority}
                             for g in gaps])
        all_gaps.sort(key=lambda g: g["priority"], reverse=True)
        return {"gaps": all_gaps[:20], "total": len(all_gaps)}

    elif name == "nyah.tasks":
        from pipeline_runner import get_tasks_for_execution
        from kanban_board import KanbanBoard
        from openpatala_bridge import convert_all
        board = KanbanBoard()
        works = convert_all()
        tasks = get_tasks_for_execution(board, works, params.get("max_tasks", 10))
        return {"tasks": tasks, "count": len(tasks)}

    elif name == "nyah.status":
        from kanban_board import KanbanBoard
        from agent_pool import AgentPool
        board = KanbanBoard()
        pool = AgentPool()
        return {"board": board.status(), "pool": pool.status()}

    elif name == "nyah.execute":
        from agent_executor import execute_task
        r = execute_task(
            task_type=params["task_type"],
            task_id=f"mcp_{params['task_type']}_{params['work_title'][:10]}",
            work_id="",
            work_title=params["work_title"],
        )
        return {"result": r["status"], "answer": r["raw"][:200], "tokens": r["tokens"]}

    elif name == "nyah.cycle":
        from pipeline_runner import run_cycle
        from kanban_board import KanbanBoard
        c = run_cycle(KanbanBoard())
        return {"cycle": c}

    elif name == "nyah.changes":
        from change_feed import get_changes
        return get_changes(params.get("since", 0))

    return {"error": f"unknown tool: {name}"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tools", action="store_true", help="list tools")
    ap.add_argument("--call", default="", help="call a tool")
    ap.add_argument("--params", default="{}", help="JSON params")
    a = ap.parse_args()

    if a.tools:
        print(json.dumps(TOOLS, indent=2))
        return 0

    if a.call:
        params = json.loads(a.params)
        result = handle_tool(a.call, params)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
