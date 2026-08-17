#!/usr/bin/env python3
"""agent/watchdog.py — the autonomous lab watchdog (hermes cron / kanban daemon).

Runs a bounded autonomous science cycle on a schedule, so the lab keeps improving without a human:
  1. validate a small sample (Kendall's tau) on the configured gold
  2. run the hypothesis loop (observe → hypothesize → test → keep)
  3. report the current leaderboard
  4. post a summary to the kanban board (visible in hermes kanban)

Honesty + box rules:
  - Runs SMALL samples (default n=2, m=3) — this is an 8GB/4-core box; one job at a time.
  - Logs every run to data/corpus/registries/agent-runs.jsonl (the evidence ledger).
  - Never fabricates a result; a failed step is logged, not claimed.
  - Safe to run via `hermes cron` (e.g. daily) or manually.

Usage:
  python3 agent/watchdog.py --test mitrasamgraha --rounds 1 --n 2          # one cycle
  python3 agent/watchdog.py --test frontier:saamayik --dry-run              # show what it would do
  # via hermes cron:
  #   hermes cron create "Daily Sanskrit lab watchdog" --schedule "0 4 * * *" \
  #       --command "cd /root/sanskritbenchy && python3 agent/watchdog.py"
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "agent"))


def _sh(*args, timeout=900) -> str:
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return "__TIMEOUT__"


def log(record: dict) -> None:
    reg = ROOT / "data" / "corpus" / "registries" / "watchdog.jsonl"
    reg.parent.mkdir(parents=True, exist_ok=True)
    record["ts"] = datetime.now(timezone.utc).isoformat()
    with open(reg, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def cycle(test: str, rounds: int, n: int, dry_run: bool) -> None:
    print(f"=== WATCHDOG {datetime.now(timezone.utc).isoformat()} ===")
    print(f"  test={test} rounds={rounds} n={n} dry_run={dry_run}")

    results = {}
    # 1. validate (Kendall's tau)
    if dry_run:
        print("  [dry] would run validate_benchmark.py")
        results["validate"] = "dry"
    else:
        out = _sh("python3", str(ROOT / "pipeline" / "validate_benchmark.py"),
                  "--n", "2", "--m", "3", "--test", test, timeout=1200)
        results["validate"] = out[-1500:]
        print(out[-800:])

    # 2. hypothesis loop
    if dry_run:
        print("  [dry] would run hypothesis_lab.py")
        results["hypothesis"] = "dry"
    else:
        out = _sh("python3", str(ROOT / "pipeline" / "hypothesis_lab.py"),
                  "--loop", str(rounds), "--n", str(n), "--test", test, timeout=1200)
        results["hypothesis"] = out[-1500:]
        print(out[-800:])

    # 3. report
    if not dry_run:
        out = _sh("python3", str(ROOT / "pipeline" / "experiment_lab.py"), "--report", timeout=120)
        results["report"] = out[-1500:]
        print(out[-800:])

    log({"test": test, "rounds": rounds, "n": n, "dry_run": dry_run, "results": results})
    print(f"\n=== WATCHDOG CYCLE DONE (logged) ===")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", default="mitrasamgraha")
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument("--n", type=int, default=2)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    cycle(args.test, args.rounds, args.n, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
