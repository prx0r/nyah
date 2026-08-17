#!/usr/bin/env python3
"""pipeline/failure_handler.py — retry, reassign, escalate on agent failure.

Handles the failure lifecycle:
  1. Detect failure (heartbeat timeout, explicit error, process exit)
  2. Classify failure (transient vs permanent)
  3. Retry transient failures (up to max_retries)
  4. Reassign to different agent type if retry fails
  5. Escalate permanent failures to human
  6. Log all failure events for evolution system

Failure classification:
  TRANSIENT: timeout, rate limit, temporary network error → retry
  PERMANENT: auth failure, data corruption, schema mismatch → escalate
  UNKNOWN: → retry once, then escalate

Usage:
  python3 pipeline/failure_handler.py --status
  python3 pipeline/failure_handler.py --handle <agent_id> --error "timeout"
  python3 pipeline/failure_handler.py --demo
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FAILURE_LOG = ROOT / "data" / "runs" / "failures.jsonl"

# Failure classification
TRANSIENT_ERRORS = ["timeout", "rate limit", "connection", "temporary", "busy", "oom", "refused"]
PERMANENT_ERRORS = ["authentication", "permission", "not found", "corrupt", "schema", "invalid", "denied"]
MAX_RETRIES = 3

# Retry strategy: which worker types can substitute
REASSIGN_MAP = {
    "discovery": ["discovery"],  # discovery tasks need discovery agents
    "resolver": ["resolver"],
    "fetcher": ["fetcher"],
    "normalizer": ["normalizer"],
    "searcher": ["searcher"],
    "translator": ["translator"],
    "aligner": ["aligner"],
}


def classify_failure(error: str) -> str:
    """Classify an error as TRANSIENT, PERMANENT, or UNKNOWN."""
    error_lower = error.lower()
    for pattern in TRANSIENT_ERRORS:
        if pattern in error_lower:
            return "TRANSIENT"
    for pattern in PERMANENT_ERRORS:
        if pattern in error_lower:
            return "PERMANENT"
    return "UNKNOWN"


def log_failure(agent_id: str, task_id: str, error: str, classification: str,
                action: str, details: dict | None = None) -> None:
    """Log a failure event."""
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "agent_id": agent_id, "task_id": task_id,
        "error": error, "classification": classification,
        "action": action, "details": details or {},
    }
    FAILURE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(FAILURE_LOG, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def handle_failure(agent_id: str, task_id: str, error: str,
                   current_retries: int = 0) -> dict:
    """Handle an agent failure. Returns the action taken.

    Actions:
      RETRY — put task back in queue for retry
      REASSIGN — try a different agent
      ESCALATE — needs human intervention
      SKIP — task is impossible, move on
    """
    classification = classify_failure(error)

    if classification == "PERMANENT":
        log_failure(agent_id, task_id, error, classification, "ESCALATE")
        return {"action": "ESCALATE", "reason": f"permanent error: {error}",
                "classification": classification}

    if classification == "TRANSIENT":
        if current_retries < MAX_RETRIES:
            log_failure(agent_id, task_id, error, classification, "RETRY",
                        {"retry": current_retries + 1})
            return {"action": "RETRY", "reason": f"transient (retry {current_retries + 1}/{MAX_RETRIES})",
                    "classification": classification}
        else:
            log_failure(agent_id, task_id, error, classification, "ESCALATE",
                        {"retries_exhausted": True})
            return {"action": "ESCALATE", "reason": f"transient but max retries ({MAX_RETRIES}) exceeded",
                    "classification": classification}

    # UNKNOWN
    if current_retries < 1:
        log_failure(agent_id, task_id, error, classification, "RETRY",
                    {"retry": current_retries + 1, "note": "unknown error, trying once"})
        return {"action": "RETRY", "reason": f"unknown error, trying once",
                "classification": classification}
    else:
        log_failure(agent_id, task_id, error, classification, "ESCALATE",
                    {"note": "unknown error, retry failed"})
        return {"action": "ESCALATE", "reason": f"unknown error after retry: {error}",
                "classification": classification}


def get_failure_stats() -> dict:
    """Get failure statistics from the log."""
    if not FAILURE_LOG.exists():
        return {"total": 0, "by_classification": {}, "by_action": {}}

    records = []
    for line in FAILURE_LOG.read_text().splitlines():
        if line.strip():
            records.append(json.loads(line))

    by_class = {}
    by_action = {}
    for r in records:
        c = r.get("classification", "UNKNOWN")
        a = r.get("action", "UNKNOWN")
        by_class[c] = by_class.get(c, 0) + 1
        by_action[a] = by_action.get(a, 0) + 1

    return {"total": len(records), "by_classification": by_class, "by_action": by_action}


def demo() -> None:
    print("=== FAILURE CLASSIFICATION ===")
    tests = [
        ("timeout connecting to provider", "TRANSIENT"),
        ("rate limit exceeded", "TRANSIENT"),
        ("authentication failed", "PERMANENT"),
        ("schema validation error", "PERMANENT"),
        ("something weird happened", "UNKNOWN"),
    ]
    for error, expected in tests:
        got = classify_failure(error)
        marker = "✓" if got == expected else "✗"
        print(f"  {marker} '{error}' → {got} (expected {expected})")

    print("\n=== HANDLING FAILURES ===")
    # transient, first retry
    r1 = handle_failure("agent_001", "task_001", "timeout", current_retries=0)
    print(f"  timeout (retry 0): {r1['action']} — {r1['reason']}")

    # transient, max retries
    r2 = handle_failure("agent_001", "task_001", "timeout", current_retries=3)
    print(f"  timeout (retry 3): {r2['action']} — {r2['reason']}")

    # permanent
    r3 = handle_failure("agent_002", "task_002", "authentication failed", current_retries=0)
    print(f"  auth failed: {r3['action']} — {r3['reason']}")

    # unknown, first try
    r4 = handle_failure("agent_003", "task_003", "weird error", current_retries=0)
    print(f"  weird (retry 0): {r4['action']} — {r4['reason']}")

    print("\n=== FAILURE STATS ===")
    stats = get_failure_stats()
    print(f"  total: {stats['total']}")
    print(f"  by classification: {stats['by_classification']}")
    print(f"  by action: {stats['by_action']}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--handle", default="", help="agent_id to handle")
    ap.add_argument("--task-id", default="")
    ap.add_argument("--error", default="")
    ap.add_argument("--retries", type=int, default=0)
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        demo()
        return 0
    if a.status:
        stats = get_failure_stats()
        print(json.dumps(stats, indent=2))
        return 0
    if a.handle and a.error:
        result = handle_failure(a.handle, a.task_id or "unknown", a.error, a.retries)
        print(json.dumps(result, indent=2))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
