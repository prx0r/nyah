#!/usr/bin/env python3
"""agent/trace.py — the CENTRAL RUN + EXPERIMENT TRACE (the anti-mess ledger).

Every hermes run, every experiment, every watchdog cycle, every agent step is logged to ONE
machine-greppable JSONL trace. This makes it deterministically impossible to lose track of what ran:

  data/runs/agent-steps.jsonl      — every `agent/run.py --step X` call (ts + step + result)
  data/runs/experiments.jsonl      — every experiment record (mirrors the lab registry)
  data/runs/watchdog.jsonl         — every watchdog cycle
  data/runs/hermes-calls.jsonl     — every hermes model call (if the lab records them)

`trace.py` indexes + queries all of them, so an agent can answer "what ran, when, with what result"
in one command. Deterministic + stdlib.

Usage:
  python3 agent/trace.py --recent 20          # last 20 trace entries across all ledgers
  python3 agent/trace.py --steps              # summary of every agent step type
  python3 agent/trace.py --step validate      # all 'validate' runs
  python3 agent/trace.py --search tau         # grep the traces
  python3 agent/trace.py --all                # count every ledger
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "data" / "runs"


def _ledgers() -> dict[str, Path]:
    return {
        "agent-steps": RUNS / "agent-steps.jsonl",
        "experiments": ROOT / "data" / "corpus" / "registries" / "experiments.jsonl",
        "watchdog": RUNS / "watchdog.jsonl",
        "agent-runs": ROOT / "data" / "corpus" / "registries" / "agent-runs.jsonl",
    }


def _read(p: Path) -> list[dict]:
    if not p.exists():
        return []
    out = []
    for line in open(p, encoding="utf-8", errors="ignore"):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out


def _all() -> list[dict]:
    rows = []
    for name, p in _ledgers().items():
        for r in _read(p):
            r["_ledger"] = name
            rows.append(r)
    rows.sort(key=lambda r: str(r.get("ts", "")))
    return rows


def cmd_recent(n: int):
    rows = _all()
    print(f"=== last {n} trace entries ===")
    for r in rows[-n:]:
        step = r.get("step") or r.get("experiment_id") or "?"
        print(f"  [{r.get('_ledger','?'):12}] {str(r.get('ts',''))[:19]} {step}")


def cmd_steps():
    rows = _all()
    c = Counter((r.get("_ledger"), r.get("step") or r.get("experiment_id") or "?") for r in rows)
    print("=== trace by ledger × step ===")
    for (led, step), n in sorted(c.items()):
        print(f"  {led:12} {step:28} {n}")


def cmd_step(name: str):
    rows = [r for r in _all() if (r.get("step") == name or name in str(r.get("experiment_id", "")))]
    print(f"=== {len(rows)} entries for '{name}' ===")
    for r in rows[-10:]:
        print(f"  {str(r.get('ts',''))[:19]} {json.dumps(r, ensure_ascii=False)[:200]}")


def cmd_search(q: str):
    rows = [r for r in _all() if q.lower() in json.dumps(r, ensure_ascii=False).lower()]
    print(f"=== {len(rows)} entries matching '{q}' ===")
    for r in rows[-10:]:
        print(f"  [{r.get('_ledger','?'):12}] {str(r.get('ts',''))[:19]} "
              f"{json.dumps(r, ensure_ascii=False)[:180]}")


def cmd_all():
    for name, p in _ledgers().items():
        print(f"  {name:14} {sum(1 for _ in open(p) if _.strip()) if p.exists() else 0} entries  ({p})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--recent", type=int, default=20)
    ap.add_argument("--steps", action="store_true")
    ap.add_argument("--step", default="")
    ap.add_argument("--search", default="")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    if args.steps:
        cmd_steps()
    elif args.step:
        cmd_step(args.step)
    elif args.search:
        cmd_search(args.search)
    elif args.all:
        cmd_all()
    else:
        cmd_recent(args.recent)
    return 0


if __name__ == "__main__":
    sys.exit(main())
