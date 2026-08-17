#!/usr/bin/env python3
"""pipeline/entity_id.py — opaque entity IDs.

From newbuild1.md §2:
- Use opaque entity IDs, never encode content in the ID
- A Work remains the same Work if its title changes
- Prefix = convenience, UUID = identity

Usage:
  python3 pipeline/entity_id.py --generate WORK
"""
from __future__ import annotations

import argparse
import hashlib
import time
import uuid


def generate_id(prefix: str = "PT") -> str:
    """Generate a time-ordered ID with prefix."""
    ts_ms = int(time.time() * 1000)
    # Use timestamp hex + random for time-ordering
    ts_hex = format(ts_ms, '012x')
    rand_hex = uuid.uuid4().hex[:20]
    return f"{prefix}_{ts_hex}{rand_hex}"


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
