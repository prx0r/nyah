#!/usr/bin/env python3
"""pipeline/rights_policy.py — per-source, per-field rights policy.

From newbuildmainspec §6:
- RightsPolicy { id, provider_id, license_uri, copyright_status, discovery, metadata_fetch,
  content_fetch, compute, derivative_generation, redistribution, training }
- Each field: ALLOWED | UNKNOWN | BLOCKED
- Rights cannot be inferred or silently broadened (newbuild1.md §11)

Usage:
  python3 pipeline/rights_policy.py --list
  python3 pipeline/rights_policy.py --check --provider gretil --field content_fetch
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POLICIES_FILE = ROOT / "data" / "rights_policies.json"

# Default policies for known providers
DEFAULT_POLICIES = {
    "gretil": {
        "provider": "gretil",
        "license_uri": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
        "copyright_status": "CC-BY-NC-SA",
        "discovery": "ALLOWED",
        "metadata_fetch": "ALLOWED",
        "content_fetch": "ALLOWED",
        "compute": "ALLOWED",
        "derivative_generation": "ALLOWED",
        "redistribution": "BLOCKED",
        "training": "BLOCKED",
    },
    "archive.org": {
        "provider": "archive.org",
        "license_uri": None,
        "copyright_status": "VARIABLE",
        "discovery": "ALLOWED",
        "metadata_fetch": "ALLOWED",
        "content_fetch": "UNKNOWN",
        "compute": "UNKNOWN",
        "derivative_generation": "UNKNOWN",
        "redistribution": "BLOCKED",
        "training": "UNKNOWN",
    },
    "muktabodha": {
        "provider": "muktabodha",
        "license_uri": None,
        "copyright_status": "IN_COPYRIGHT",
        "discovery": "ALLOWED",
        "metadata_fetch": "ALLOWED",
        "content_fetch": "BLOCKED",
        "compute": "BLOCKED",
        "derivative_generation": "BLOCKED",
        "redistribution": "BLOCKED",
        "training": "BLOCKED",
    },
    "pandit": {
        "provider": "pandit",
        "license_uri": None,
        "copyright_status": "IN_COPYRIGHT",
        "discovery": "ALLOWED",
        "metadata_fetch": "ALLOWED",
        "content_fetch": "UNKNOWN",
        "compute": "UNKNOWN",
        "derivative_generation": "UNKNOWN",
        "redistribution": "BLOCKED",
        "training": "BLOCKED",
    },
    "openalex": {
        "provider": "openalex",
        "license_uri": "https://creativecommons.org/publicdomain/zero/1.0/",
        "copyright_status": "CC0",
        "discovery": "ALLOWED",
        "metadata_fetch": "ALLOWED",
        "content_fetch": "ALLOWED",
        "compute": "ALLOWED",
        "derivative_generation": "ALLOWED",
        "redistribution": "ALLOWED",
        "training": "ALLOWED",
    },
}


def _load() -> dict:
    if POLICIES_FILE.exists():
        return json.loads(POLICIES_FILE.read_text())
    POLICIES_FILE.parent.mkdir(parents=True, exist_ok=True)
    reg = {"version": "1.0.0", "policies": DEFAULT_POLICIES}
    POLICIES_FILE.write_text(json.dumps(reg, indent=2, ensure_ascii=False))
    return reg


def check_policy(provider: str, field: str) -> dict:
    """Check if a field is allowed for a provider."""
    reg = _load()
    policy = reg.get("policies", {}).get(provider)
    if not policy:
        return {"allowed": False, "reason": f"no policy for provider: {provider}"}

    value = policy.get(field, "UNKNOWN")
    return {
        "allowed": value == "ALLOWED",
        "field": field,
        "value": value,
        "provider": provider,
        "license": policy.get("license_uri"),
        "copyright": policy.get("copyright_status"),
    }


def list_policies() -> list[dict]:
    reg = _load()
    return [{"provider": k, **v} for k, v in reg.get("policies", {}).items()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--provider", default="")
    ap.add_argument("--field", default="content_fetch")
    a = ap.parse_args()

    if a.list:
        for p in list_policies():
            print(f"  {p['provider']:15} {p['copyright_status']:15} fetch={p['content_fetch']} train={p['training']}")
        return 0

    if a.check and a.provider:
        result = check_policy(a.provider, a.field)
        print(json.dumps(result, indent=2))
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
