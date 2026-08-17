#!/usr/bin/env python3
"""pipeline/schema_registry.py — append-only schema registry.

From newbuild1.md §12-13:
- Every schema that has ever written permanent data must remain available
- Schema versions themselves must be immutable once published
- Never: schema = "latest" inside permanent data

Usage:
  python3 pipeline/schema_registry.py --list
  python3 pipeline/schema_registry.py --register --family nyah/task --version 1.0.0
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_FILE = ROOT / "data" / "schema_registry.json"


def _load() -> dict:
    if REGISTRY_FILE.exists():
        return json.loads(REGISTRY_FILE.read_text())
    return {"version": "1.0.0", "schemas": {}}


def _save(reg: dict) -> None:
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_FILE.write_text(json.dumps(reg, indent=2, ensure_ascii=False))


def register(family: str, version: str, schema: dict) -> str:
    """Register an immutable schema. Returns schema_uri."""
    reg = _load()
    uri = f"nyah/{family}/{version}"

    if uri in reg["schemas"]:
        # immutable — can't change a published schema
        existing = reg["schemas"][uri]
        if existing.get("schema") != schema:
            raise ValueError(f"Schema {uri} already exists with different content. "
                             f"Publish a new version instead.")
        return uri

    schema_bytes = json.dumps(schema, sort_keys=True, ensure_ascii=False).encode()
    digest = hashlib.sha256(schema_bytes).hexdigest()

    reg["schemas"][uri] = {
        "uri": uri,
        "family": family,
        "version": version,
        "schema": schema,
        "digest": f"sha256:{digest}",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "immutable": True,
    }
    _save(reg)
    return uri


def get_schema(uri: str) -> dict | None:
    """Get a schema by URI."""
    reg = _load()
    return reg["schemas"].get(uri)


def list_schemas(family: str | None = None) -> list[dict]:
    """List all schemas, optionally filtered by family."""
    reg = _load()
    schemas = list(reg["schemas"].values())
    if family:
        schemas = [s for s in schemas if s["family"] == family]
    return schemas


def latest_version(family: str) -> str | None:
    """Get the latest version for a schema family."""
    schemas = list_schemas(family)
    if not schemas:
        return None
    # sort by version (simple string sort works for semver X.Y.Z)
    schemas.sort(key=lambda s: s["version"])
    return schemas[-1]["version"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--family", default="")
    ap.add_argument("--register", action="store_true")
    ap.add_argument("--version", default="1.0.0")
    ap.add_argument("--schema-file", default="", help="JSON file with schema")
    a = ap.parse_args()

    if a.list:
        schemas = list_schemas(a.family if a.family else None)
        for s in schemas:
            print(f"  {s['uri']:40} {s['digest'][:20]}  {s['published_at']}")
        return 0

    if a.register and a.family:
        if a.schema_file:
            schema = json.loads(Path(a.schema_file).read_text())
        else:
            schema = {"type": "object", "properties": {}}
        uri = register(a.family, a.version, schema)
        print(f"registered: {uri}")
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
