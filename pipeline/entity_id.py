#!/usr/bin/env python3
"""pipeline/entity_id.py — opaque entity IDs (UUIDv7-style).

From newbuild1.md §2:
- Use opaque entity IDs, never encode content in the ID
- A Work remains the same Work if its title changes
- Prefix = convenience, UUID = identity

Usage:
  python3 pipeline/entity_id.py --generate WORK
  python3 pipeline/entity_id.py --generate TASK
"""
from __future__ import annotations

import argparse
import json
import time
import uuid


def generate_id(prefix: str = "PT") -> str:
    """Generate a time-ordered ID with prefix.
    Uses UUIDv7 pattern: timestamp + random, giving time-ordered IDs."""
    ts_ms = int(time.time() * 1000)
    # UUIDv7: 48 bits timestamp + 12 bits random + 62 bits random
    u = uuid.uuid4()
    # Override first 6 bytes with timestamp for time-ordering
    u bytes = ts_ms.to_bytes(6, "big") + u.bytes[6:]
    return f"{prefix}_{u.hex}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--generate", default="PT", help="prefix (WORK, TASK, EVENT, etc.)")
    ap.add_argument("--count", type=int, default=1)
    a = ap.parse_args()

    prefix_map = {
        "WORK": "PTW", "TASK": "PTT", "EVENT": "PTEVT", "SCHEMA": "PTSC",
        "ARTIFACT": "PTART", "AGENT": "PTAG", "ASSERTION": "PTA",
    }
    prefix = prefix_map.get(a.generate, a.generate)

    for _ in range(a.count):
        print(generate_id(prefix))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
