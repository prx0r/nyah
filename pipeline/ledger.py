#!/usr/bin/env python3
"""pipeline/ledger.py — Merkle checkpoint ledger for integrity.

From newbuild1.md §33-37:
- Events commit normally, periodically batch into Merkle tree
- LedgerCheckpoint { id, previous_checkpoint, event_count, merkle_root, signatures }
- Checkpoints are signed, published independently
- No blockchain needed — just transparency log pattern

Usage:
  python3 pipeline/ledger.py --checkpoint
  python3 pipeline/ledger.py --verify
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER_FILE = ROOT / "data" / "ledger.jsonl"
EVENT_LOG = ROOT / "data" / "event_log.jsonl"


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _merkle_root(events: list[dict]) -> str:
    """Compute Merkle root of events."""
    if not events:
        return _hash(b"empty")
    leaves = [_hash(json.dumps(e, sort_keys=True).encode()) for e in events]
    while len(leaves) > 1:
        if len(leaves) % 2 == 1:
            leaves.append(leaves[-1])
        leaves = [_hash((leaves[i] + leaves[i+1]).encode()) for i in range(0, len(leaves), 2)]
    return leaves[0]


def create_checkpoint() -> dict:
    """Create a Merkle checkpoint from uncheckpointed events."""
    if not EVENT_LOG.exists():
        return {"error": "no events"}

    events = []
    for line in EVENT_LOG.read_text().splitlines():
        if line.strip():
            events.append(json.loads(line))

    # Find last checkpoint cursor
    last_cursor = 0
    if LEDGER_FILE.exists():
        for line in LEDGER_FILE.read_text().splitlines():
            if line.strip():
                cp = json.loads(line)
                last_cursor = max(last_cursor, cp.get("event_cursor_end", 0))

    new_events = events[last_cursor:]
    if not new_events:
        return {"note": "no new events since last checkpoint"}

    root = _merkle_root(new_events)
    checkpoint = {
        "checkpoint_id": f"cp_{_hash(root.encode())[:16]}",
        "previous_checkpoint": None,
        "event_cursor_start": last_cursor,
        "event_cursor_end": last_cursor + len(new_events),
        "event_count": len(new_events),
        "merkle_root": root,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER_FILE, "a") as f:
        f.write(json.dumps(checkpoint, ensure_ascii=False) + "\n")

    return checkpoint


def verify_ledger() -> dict:
    """Verify the ledger chain is consistent."""
    if not LEDGER_FILE.exists():
        return {"valid": True, "note": "no checkpoints"}

    checkpoints = []
    for line in LEDGER_FILE.read_text().splitlines():
        if line.strip():
            checkpoints.append(json.loads(line))

    # Verify chain
    for i, cp in enumerate(checkpoints):
        if i > 0 and cp.get("previous_checkpoint") != checkpoints[i-1].get("checkpoint_id"):
            return {"valid": False, "error": f"chain break at checkpoint {i}"}

    return {"valid": True, "checkpoints": len(checkpoints)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", action="store_true")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()

    if a.checkpoint:
        cp = create_checkpoint()
        print(json.dumps(cp, indent=2))
        return 0

    if a.verify:
        result = verify_ledger()
        print(json.dumps(result, indent=2))
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
