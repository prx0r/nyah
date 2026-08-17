#!/usr/bin/env python3
"""pipeline/event_log.py — append-only event log.

From newbuild1.md §8-9:
- The event is the real durable semantic record
- Do not mutate events — append new ones
- Every event has: event_id, event_type, entity_ids[], schema_uri, payload, payload_digest

Usage:
  python3 pipeline/event_log.py --append --type TaskCompleted --entity task_001 --payload '{"status":"DONE"}'
  python3 pipeline/event_log.py --recent 5
"""
from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVENT_LOG = ROOT / "data" / "event_log.jsonl"


def append(event_type: str, entity_ids: list[str], payload: dict,
           schema_uri: str = "nyah/event/1.0.0", actor: str = "nyah") -> dict:
    """Append an event to the log. Returns the event record."""
    EVENT_LOG.parent.mkdir(parents=True, exist_ok=True)

    payload_bytes = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
    payload_digest = f"sha256:{hashlib.sha256(payload_bytes).hexdigest()}"

    event = {
        "event_id": f"evt_{uuid.uuid4().hex[:16]}",
        "event_type": event_type,
        "entity_ids": entity_ids,
        "schema_uri": schema_uri,
        "actor_id": actor,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
        "payload_digest": payload_digest,
    }

    with open(EVENT_LOG, "a") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

    return event


def recent(n: int = 10) -> list[dict]:
    """Get the last N events."""
    if not EVENT_LOG.exists():
        return []
    lines = EVENT_LOG.read_text().splitlines()
    events = []
    for line in lines[-n:]:
        if line.strip():
            events.append(json.loads(line))
    return events


def count() -> int:
    if not EVENT_LOG.exists():
        return 0
    return sum(1 for line in EVENT_LOG.read_text().splitlines() if line.strip())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--append", action="store_true")
    ap.add_argument("--type", default="TestEvent")
    ap.add_argument("--entity", default="test_001")
    ap.add_argument("--payload", default="{}")
    ap.add_argument("--recent", type=int, default=0)
    ap.add_argument("--count", action="store_true")
    a = ap.parse_args()

    if a.append:
        payload = json.loads(a.payload)
        event = append(a.type, [a.entity], payload)
        print(json.dumps(event, indent=2))
        return 0

    if a.recent > 0:
        events = recent(a.recent)
        for e in events:
            print(f"  {e['event_type']:25} {e['entity_ids'][0]:30} {e['recorded_at'][:19]}")
        return 0

    if a.count:
        print(f"events: {count()}")
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
