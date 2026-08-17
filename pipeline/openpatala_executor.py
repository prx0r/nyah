#!/usr/bin/env python3
"""pipeline/openpatala_executor.py — call OpenPatala's actual pipeline steps.

Nyah doesn't duplicate OpenPatala. It calls OpenPatala's agent/run.py steps
and tracks results.

OpenPatala steps:
  compile --work X    → build translation availability
  verify --work X     → pipeline checks
  ingest              → extract + register SOURCE
  report              → index summary
  watchdog --work X   → full autonomous cycle

Usage:
  python3 pipeline/openpatala_executor.py --step compile --work tantraloka
  python3 pipeline/openpatala_executor.py --step report
  python3 pipeline/openpatala_executor.py --status
"""
from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPENPATALA = Path("/root/openpatalaproject")
PY = "/root/patalacheckpoints/.venv-atlas/bin/python"
RESULTS_DIR = ROOT / "data" / "tasks" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def run_step(step: str, work: str | None = None, extra_args: list[str] | None = None,
             timeout_s: int = 300) -> dict:
    """Run an OpenPatala step and return the result."""
    cmd = [PY, str(OPENPATALA / "agent" / "run.py"), "--step", step]
    if work:
        cmd.extend(["--work", work])
    if extra_args:
        cmd.extend(extra_args)

    start = time.time()
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout_s,
            cwd=str(OPENPATALA),
            env={**__import__("os").environ, "PATALA_ROOT": str(OPENPATALA),
                 "PYTHONPATH": str(OPENPATALA / "python")},
        )
        duration = time.time() - start
        return {
            "step": step, "work": work,
            "status": "DONE" if proc.returncode == 0 else "FAILED",
            "exit_code": proc.returncode,
            "stdout": proc.stdout[-2000:],
            "stderr": proc.stderr[-500:],
            "duration_s": round(duration, 1),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except subprocess.TimeoutExpired:
        return {
            "step": step, "work": work,
            "status": "TIMEOUT",
            "exit_code": -1,
            "stdout": "", "stderr": "timeout",
            "duration_s": timeout_s,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "step": step, "work": work,
            "status": "ERROR",
            "exit_code": -1,
            "stdout": "", "stderr": str(e),
            "duration_s": round(time.time() - start, 1),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def compile_work(work: str) -> dict:
    """Compile translation availability for one work."""
    return run_step("compile", work, timeout_s=300)


def verify_work(work: str) -> dict:
    """Run pipeline verification for one work."""
    return run_step("verify", work, timeout_s=120)


def ingest() -> dict:
    """Ingest curated works."""
    return run_step("ingest", timeout_s=300)


def report() -> dict:
    """Get index summary."""
    return run_step("report", timeout_s=60)


def watchdog(work: str) -> dict:
    """Run full autonomous cycle for one work."""
    return run_step("watchdog", work, timeout_s=600)


def status() -> dict:
    """Get OpenPatala status."""
    r = report()
    return {
        "openpatala_root": str(OPENPATALA),
        "python": PY,
        "report": r,
    }


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", default="report")
    ap.add_argument("--work", default=None)
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()

    if a.status:
        s = status()
        print(json.dumps(s, indent=2))
        return 0

    step_map = {
        "compile": lambda: compile_work(a.work or "tantraloka"),
        "verify": lambda: verify_work(a.work or "tantraloka"),
        "ingest": ingest,
        "report": report,
        "watchdog": lambda: watchdog(a.work or "tantraloka"),
    }

    if a.step in step_map:
        r = step_map[a.step]()
        print(json.dumps(r, indent=2))

        # Save result
        fname = f"openpatala_{a.step}_{a.work or 'all'}.json"
        (RESULTS_DIR / fname).write_text(json.dumps(r, indent=2))
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
