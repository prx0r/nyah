#!/usr/bin/env python3
"""check.py — the nyah drift gate.

Validates:
  1. Every doc/script in MANIFEST.json exists
  2. Data files are valid JSON/JSONL
  3. Task results exist and are valid
  4. Event log is consistent
  5. Schema registry is intact

Usage:
  python3 check.py --status
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "MANIFEST.json"


def check_manifest() -> tuple[bool, list[str]]:
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

        if not path.exists():
            errors.append(f"MISSING: {eid} → {path}")

        if role:
            if role in seen_roles:
                errors.append(f"DUPLICATE ROLE: {role} in {eid} and {seen_roles[role]}")
            seen_roles[role] = eid

    return len(errors) == 0, errors


def check_data() -> tuple[bool, list[str]]:
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


def check_results() -> tuple[bool, list[str]]:
    """Verify task results are valid."""
    errors = []
    results_dir = ROOT / "data" / "tasks" / "results"
    if not results_dir.exists():
        return True, []

    for f in results_dir.glob("*.json"):
        try:
            r = json.loads(f.read_text())
            if "task_id" not in r:
                errors.append(f"RESULT MISSING task_id: {f.name}")
            if "status" not in r:
                errors.append(f"RESULT MISSING status: {f.name}")
            if "_digest" not in r:
                errors.append(f"RESULT MISSING digest: {f.name}")
        except Exception as e:
            errors.append(f"INVALID RESULT: {f.name} — {e}")

    return len(errors) == 0, errors


def check_events() -> tuple[bool, list[str]]:
    """Verify event log consistency."""
    errors = []
    event_log = ROOT / "data" / "event_log.jsonl"
    if not event_log.exists():
        return True, []

    events = []
    for i, line in enumerate(event_log.read_text().splitlines()):
        if line.strip():
            try:
                e = json.loads(line)
                if "event_id" not in e:
                    errors.append(f"EVENT {i} MISSING event_id")
                if "event_type" not in e:
                    errors.append(f"EVENT {i} MISSING event_type")
                events.append(e)
            except Exception as ex:
                errors.append(f"INVALID EVENT {i} — {ex}")

    # Check pairing: every TaskStarted should have a TaskCompleted
    started = {e["entity_ids"][0] for e in events if e["event_type"] == "TaskStarted"}
    completed = {e["entity_ids"][0] for e in events if e["event_type"] == "TaskCompleted"}
    orphaned = started - completed
    if orphaned:
        errors.append(f"ORPHANED TASKS (started but not completed): {len(orphaned)}")

    return len(errors) == 0, errors


def check_schemas() -> tuple[bool, list[str]]:
    """Verify schema registry is intact."""
    errors = []
    reg_file = ROOT / "data" / "schema_registry.json"
    if not reg_file.exists():
        return True, []

    try:
        reg = json.loads(reg_file.read_text())
        schemas = reg.get("schemas", {})
        for uri, s in schemas.items():
            if not s.get("immutable"):
                errors.append(f"SCHEMA NOT IMMUTABLE: {uri}")
            if "digest" not in s:
                errors.append(f"SCHEMA MISSING digest: {uri}")
    except Exception as e:
        errors.append(f"INVALID SCHEMA REGISTRY — {e}")

    return len(errors) == 0, errors


def main() -> int:
    all_errors = []

    for name, check in [
        ("manifest", check_manifest),
        ("data", check_data),
        ("results", check_results),
        ("events", check_events),
        ("schemas", check_schemas),
    ]:
        ok, errors = check()
        if not ok:
            all_errors.extend(errors)

    if not all_errors:
        print("PASS — all docs registered, data valid, results valid, events consistent, schemas intact")
        return 0
    else:
        print(f"FAIL — {len(all_errors)} error(s):")
        for e in all_errors:
            print(f"  {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
