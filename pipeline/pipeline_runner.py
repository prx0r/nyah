#!/usr/bin/env python3
"""pipeline/pipeline_runner.py — the autonomous coordination loop.

Runs cycles of: scan gaps → pick task → call OpenPatala step → log result → repeat

Usage:
  python3 pipeline/pipeline_runner.py --cycle
  python3 pipeline/pipeline_runner.py --autonomous --max-cycles 3
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT / "pipeline"))

from gap_analyzer import analyze_work
from openpatala_bridge import convert_all
from openpatala_executor import compile_work, verify_work, report, run_step

RESULTS_DIR = ROOT / "data" / "tasks" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def get_works_needing_work() -> list[dict]:
    """Find works that need actual pipeline steps run."""
    works = convert_all()
    needs_compile = []
    needs_verify = []

    for w in works:
        source = w.get("source_state", "NONE")
        translation = w.get("translation_state", "NONE_KNOWN")

        # Works with source ready but not compiled
        if source in ("ETEXT", "SCHOLARLY_ETEXT") and translation in ("NONE_KNOWN", "PARTIAL"):
            needs_compile.append(w)

        # Works with existing translations that could be verified
        if translation in ("EXISTING", "PARTIAL"):
            needs_verify.append(w)

    return needs_compile, needs_verify


def run_cycle() -> dict:
    """Run one coordination cycle."""
    now = datetime.now(timezone.utc).isoformat()
    cycle = {"at": now}

    # Step 1: Get OpenPatala status
    r = report()
    cycle["openpatala"] = r["stdout"][:200]

    # Step 2: Find works needing compilation
    needs_compile, needs_verify = get_works_needing_work()
    cycle["needs_compile"] = len(needs_compile)
    cycle["needs_verify"] = len(needs_verify)

    # Step 3: Pick the most valuable work to compile (first one)
    result = None
    if needs_compile:
        work = needs_compile[0]
        work_name = work.get("_openpatala", {}).get("work", work.get("preferred_title", "unknown"))
        print(f"  compiling: {work_name}")
        result = compile_work(work_name)
        cycle["action"] = f"compile:{work_name}"
        cycle["result"] = result["status"]
        cycle["duration_s"] = result["duration_s"]
        cycle["output"] = result["stdout"][:200]

        # Save result
        fname = f"compile_{work_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        (RESULTS_DIR / fname).write_text(json.dumps(result, indent=2))

    elif needs_verify:
        work = needs_verify[0]
        work_name = work.get("_openpatala", {}).get("work", work.get("preferred_title", "unknown"))
        print(f"  verifying: {work_name}")
        result = verify_work(work_name)
        cycle["action"] = f"verify:{work_name}"
        cycle["result"] = result["status"]
        cycle["duration_s"] = result["duration_s"]
        cycle["output"] = result["stdout"][:200]

        fname = f"verify_{work_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        (RESULTS_DIR / fname).write_text(json.dumps(result, indent=2))

    else:
        cycle["action"] = "none"
        cycle["result"] = "all caught up"

    return cycle


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycle", action="store_true")
    ap.add_argument("--autonomous", action="store_true")
    ap.add_argument("--max-cycles", type=int, default=3)
    a = ap.parse_args()

    if a.cycle:
        c = run_cycle()
        print(json.dumps(c, indent=2))
        return 0

    if a.autonomous:
        print(f"=== AUTONOMOUS MODE ({a.max_cycles} cycles) ===\n")
        for i in range(a.max_cycles):
            print(f"\n--- Cycle {i+1}/{a.max_cycles} ---")
            c = run_cycle()
            print(json.dumps(c, indent=2))

            if c.get("result") == "TIMEOUT":
                print("  TIMEOUT — stopping")
                break

        # Summary
        results = list(RESULTS_DIR.glob("*.json"))
        done = sum(1 for f in results if json.loads(f.read_text()).get("status") == "DONE")
        failed = sum(1 for f in results if json.loads(f.read_text()).get("status") == "FAILED")
        print(f"\n=== SUMMARY ===")
        print(f"  total results: {len(results)}")
        print(f"  done: {done}  failed: {failed}")
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
