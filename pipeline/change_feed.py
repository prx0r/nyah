#!/usr/bin/env python3
"""pipeline/change_feed.py — incremental change feed for agents.

From newbuildplayers §22:
- An agent shouldn't continually reread Pāṭala
- Give it GET /v1/changes?since=<cursor>
- Returns entity added, assertion superseded, translation added, etc.

The change feed is built on the event log. Agents poll with a cursor (last event_id they saw)
and get new events since then.

Usage:
  python3 pipeline/change_feed.py --since 0
  python3 pipeline/change_feed.py --tail 5
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT / "pipeline"))

from event_log import recent, count


def get_changes(since_cursor: int = 0, limit: int = 50) -> dict:
    """Get changes since a cursor (event sequence number)."""
    if not Path(ROOT / "data" / "event_log.jsonl").exists():
        return {"events": [], "cursor": 0, "has_more": False}

    all_events = []
    for line in (ROOT / "data" / "event_log.jsonl").read_text().splitlines():
        if line.strip():
            all_events.append(json.loads(line))

    # Filter by cursor (sequence number)
    changes = all_events[since_cursor:since_cursor + limit]
    new_cursor = since_cursor + len(changes)
    has_more = new_cursor < len(all_events)

    return {
        "events": changes,
        "cursor": new_cursor,
        "total": len(all_events),
        "has_more": has_more,
    }


def format_change(event: dict) -> str:
    """Format a change event for display."""
    etype = event.get("event_type", "?")
    entities = event.get("entity_ids", [])
    entity = entities[0] if entities else "?"
    ts = event.get("recorded_at", "?")[:19]
    payload = event.get("payload", {})

    if etype == "TaskCompleted":
        status = payload.get("status", "?")
        return f"  {ts} {etype:25} {entity:35} {status}"
    elif etype == "SchemaRegistered":
        schemas = payload.get("schemas", [])
        return f"  {ts} {etype:25} {len(schemas)} schemas registered"
    else:
        return f"  {ts} {etype:25} {entity}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", type=int, default=0, help="cursor (event sequence)")
    ap.add_argument("--tail", type=int, default=0, help="last N events")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.tail > 0:
        total = count()
        since = max(0, total - a.tail)
        changes = get_changes(since, a.tail)
    else:
        changes = get_changes(a.since)

    if a.json:
        print(json.dumps(changes, indent=2, ensure_ascii=False))
    else:
        print(f"Changes (cursor={changes['cursor']}/{changes['total']}):")
        for e in changes["events"]:
            print(format_change(e))
        if changes["has_more"]:
            print(f"  ... more available (use --since {changes['cursor']})")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
