#!/usr/bin/env python3
"""pipeline/crawl_policy.py — crawl policies per provider.

From newbuildmainspec §39:
- CrawlPolicy { robots_behavior, max_requests_per_second, max_concurrency,
  allowed_paths, denied_paths, metadata_only, content_fetch_allowed }

Usage:
  python3 pipeline/crawl_policy.py --list
  python3 pipeline/crawl_policy.py --check --provider gretil
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POLICIES_FILE = ROOT / "data" / "crawl_policies.json"

DEFAULT_POLICIES = {
    "gretil": {
        "robots_behavior": "respect",
        "max_requests_per_second": 2,
        "max_concurrency": 1,
        "metadata_only": False,
        "content_fetch_allowed": True,
        "contact_email": None,
        "notes": "Academic resource, be gentle",
    },
    "archive.org": {
        "robots_behavior": "respect",
        "max_requests_per_second": 1,
        "max_concurrency": 1,
        "metadata_only": False,
        "content_fetch_allowed": True,
        "contact_email": None,
        "notes": "Rate limited, 1 req/sec recommended",
    },
    "muktabodha": {
        "robots_behavior": "respect",
        "max_requests_per_second": 1,
        "max_concurrency": 1,
        "metadata_only": True,
        "content_fetch_allowed": False,
        "contact_email": None,
        "notes": "Login required for content, metadata only without auth",
    },
    "pandit": {
        "robots_behavior": "respect",
        "max_requests_per_second": 1,
        "max_concurrency": 1,
        "metadata_only": True,
        "content_fetch_allowed": False,
        "contact_email": None,
        "notes": "Metadata only, no bulk download",
    },
    "openalex": {
        "robots_behavior": "respect",
        "max_requests_per_second": 10,
        "max_concurrency": 3,
        "metadata_only": False,
        "content_fetch_allowed": True,
        "contact_email": None,
        "notes": "Polite pool: 10 req/sec with email in header",
    },
}


def _load() -> dict:
    if POLICIES_FILE.exists():
        return json.loads(POLICIES_FILE.read_text())
    POLICIES_FILE.parent.mkdir(parents=True, exist_ok=True)
    reg = {"version": "1.0.0", "policies": DEFAULT_POLICIES}
    POLICIES_FILE.write_text(json.dumps(reg, indent=2))
    return reg


def check_policy(provider: str) -> dict:
    reg = _load()
    return reg.get("policies", {}).get(provider, {"error": f"no policy for {provider}"})


def list_policies() -> list[dict]:
    reg = _load()
    return [{"provider": k, **v} for k, v in reg.get("policies", {}).items()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--provider", default="")
    a = ap.parse_args()

    if a.list:
        for p in list_policies():
            print(f"  {p['provider']:15} rps={p['max_requests_per_second']} meta_only={p['metadata_only']}")
        return 0

    if a.check and a.provider:
        p = check_policy(a.provider)
        print(json.dumps(p, indent=2))
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
