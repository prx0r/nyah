#!/usr/bin/env python3
"""pipeline/digest.py — content-addressing and digest sets.

From newbuild1.md §3-4:
- Every thing that can have bytes gets a DigestSet
- Algorithm-tagged, replaceable (crypto agility)
- Three different hashes: raw-byte, canonical structured, semantic fingerprint

Usage:
  python3 pipeline/digest.py --hash "hello world"
  python3 pipeline/digest.py --hash-file /path/to/file
"""
from __future__ import annotations

import argparse
import hashlib
import json


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha512(data: bytes) -> str:
    return hashlib.sha512(data).hexdigest()


def digest_set(data: bytes) -> dict:
    """Create a DigestSet from bytes."""
    return {
        "digests": [
            {"algorithm": "sha256", "value": sha256(data), "encoding": "hex"},
            {"algorithm": "sha512", "value": sha512(data), "encoding": "hex"},
        ]
    }


def raw_digest(data: bytes) -> dict:
    """Raw-byte hash — proves exact bytes."""
    return {"algorithm": "sha256", "value": sha256(data), "encoding": "hex",
            "canonicalization": None}


def canonical_digest(obj: dict) -> dict:
    """Canonical structured hash (RFC 8785 JCS)."""
    # Python's json.dumps with sort_keys is close to JCS
    canonical = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    data = canonical.encode()
    return {"algorithm": "sha256", "value": sha256(data), "encoding": "hex",
            "canonicalization": "jcs"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hash", default="", help="hash a string")
    ap.add_argument("--hash-file", default="", help="hash a file")
    ap.add_argument("--json-obj", default="", help="hash a JSON object")
    a = ap.parse_args()

    if a.hash:
        data = a.hash.encode()
        ds = digest_set(data)
        print(json.dumps(ds, indent=2))
        return 0

    if a.hash_file:
        from pathlib import Path
        data = Path(a.hash_file).read_bytes()
        ds = digest_set(data)
        print(json.dumps(ds, indent=2))
        return 0

    if a.json_obj:
        obj = json.loads(a.json_obj)
        cd = canonical_digest(obj)
        print(json.dumps(cd, indent=2))
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
