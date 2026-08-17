#!/usr/bin/env python3
"""pipeline/schema_migrations.py — schema migration registry.

From newbuild1.md §20:
- SchemaMigration { id, from_schema, to_schema, migration_type, lossless, known_information_loss }
- Types: UPCAST (forward-compatible), DOWNCAST, REPROJECT
- Migrations are first-class, inspectable, deterministic

Usage:
  python3 pipeline/schema_migrations.py --list
  python3 pipeline/schema_migrations.py --register --from task/1.0.0 --to task/2.0.0 --type UPCAST
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_FILE = ROOT / "data" / "schema_migrations.json"


def _load() -> dict:
    if MIGRATIONS_FILE.exists():
        return json.loads(MIGRATIONS_FILE.read_text())
    return {"version": "1.0.0", "migrations": []}


def _save(reg: dict) -> None:
    MIGRATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    MIGRATIONS_FILE.write_text(json.dumps(reg, indent=2, ensure_ascii=False))


def register_migration(from_schema: str, to_schema: str, migration_type: str,
                       lossless: bool = True, description: str = "",
                       known_loss: list[str] | None = None) -> dict:
    """Register a schema migration."""
    reg = _load()

    migration = {
        "id": f"mig_{from_schema.replace('/', '_')}_to_{to_schema.replace('/', '_')}",
        "from_schema": from_schema,
        "to_schema": to_schema,
        "migration_type": migration_type,  # UPCAST, DOWNCAST, REPROJECT
        "lossless": lossless,
        "description": description,
        "known_information_loss": known_loss or [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Check for duplicates
    for m in reg["migrations"]:
        if m["from_schema"] == from_schema and m["to_schema"] == to_schema:
            print(f"migration already registered: {m['id']}")
            return m

    reg["migrations"].append(migration)
    _save(reg)
    return migration


def list_migrations(from_schema: str | None = None) -> list[dict]:
    reg = _load()
    migrations = reg.get("migrations", [])
    if from_schema:
        migrations = [m for m in migrations if m["from_schema"] == from_schema]
    return migrations


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--from-schema", default="", help="filter by from_schema")
    ap.add_argument("--register", action="store_true")
    ap.add_argument("--from", dest="from_schema_reg", default="")
    ap.add_argument("--to", default="")
    ap.add_argument("--type", default="UPCAST", choices=["UPCAST", "DOWNCAST", "REPROJECT"])
    ap.add_argument("--description", default="")
    a = ap.parse_args()

    if a.list:
        migrations = list_migrations(a.from_schema if a.from_schema else None)
        for m in migrations:
            print(f"  {m['id']:50} {m['migration_type']:10} lossless={m['lossless']}")
        return 0

    if a.register and a.from_schema_reg and a.to:
        m = register_migration(a.from_schema_reg, a.to, a.type, description=a.description)
        print(f"registered: {m['id']}")
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
