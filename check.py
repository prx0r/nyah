#!/usr/bin/env python3
"""check.py — the nyah drift gate.

Validates that:
  1. Every doc/script in MANIFEST.json exists
  2. Every file reference resolves
  3. Data files are valid JSONL/JSON
  4. No duplicate roles

Usage:
  python3 check.py --status   # PASS = everything resolves
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "MANIFEST.json"


def check_manifest() -> tuple[bool, list[str]]:
    """Check that every entry in MANIFEST.json resolves to a real file."""
    errors = []
    if not MANIFEST.exists():
        return False, ["MANIFEST.json not found"]

    manifest = json.loads(MANIFEST.read_text())
    entries = manifest.get("entries", [])

    seen_roles = {}
    for entry in entries:
        eid = entry.get("id", "")
        path = ROOT / entry.get("path", "")
        role = entry.get("role", "")

        # check file exists
        if not path.exists():
            errors.append(f"MISSING: {eid} → {path}")

        # check for duplicate roles
        if role:
            if role in seen_roles:
                errors.append(f"DUPLICATE ROLE: {role} in {eid} and {seen_roles[role]}")
            seen_roles[role] = eid

    return len(errors) == 0, errors


def check_data() -> tuple[bool, list[str]]:
    """Check that data files are valid JSON/JSONL."""
    errors = []
    data_dir = ROOT / "data"
    if not data_dir.exists():
        return True, []

    for p in data_dir.rglob("*.json"):
        try:
            json.loads(p.read_text())
        except Exception as e:
            errors.append(f"INVALID JSON: {p} — {e}")

    for p in data_dir.rglob("*.jsonl"):
        try:
            for i, line in enumerate(p.read_text().splitlines()):
                if line.strip():
                    json.loads(line)
        except Exception as e:
            errors.append(f"INVALID JSONL: {p}:{i} — {e}")

    return len(errors) == 0, errors


def main() -> int:
    ok_manifest, errors_manifest = check_manifest()
    ok_data, errors_data = check_data()

    all_errors = errors_manifest + errors_data

    if not all_errors:
        print("PASS — all docs registered, data valid")
        return 0
    else:
        print(f"FAIL — {len(all_errors)} error(s):")
        for e in all_errors:
            print(f"  {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
