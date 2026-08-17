#!/usr/bin/env python3
"""pipeline/discovery.py — real HTTP discovery across repositories.

Checks GRETIL, Archive.org, PANDiT, Muktabodha via HTTP.
No agent needed — deterministic probes.

Usage:
  python3 pipeline/discovery.py --probe "tantraloka"
  python3 pipeline/discovery.py --gretil
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _curl(url: str, timeout: int = 10) -> str:
    """Quick HTTP GET."""
    try:
        proc = subprocess.run(
            ["curl", "-s", "--max-time", str(timeout), "-L", url],
            capture_output=True, text=True, timeout=timeout + 5,
        )
        return proc.stdout[:5000]
    except Exception:
        return ""


def search_archive_org(query: str) -> list[dict]:
    """Search Archive.org for Sanskrit texts."""
    url = f"https://archive.org/advancedsearch.php?q={query.replace(' ', '+')}&fl[]=identifier&fl[]=title&rows=5&output=json"
    raw = _curl(url)
    try:
        data = json.loads(raw)
        docs = data.get("response", {}).get("docs", [])
        return [{"source": "archive.org", "id": doc.get("identifier", ""),
                 "title": doc.get("title", doc.get("identifier", ""))}
                for doc in docs]
    except Exception:
        return []


def search_gretil() -> list[dict]:
    """Check GRETIL for available e-texts."""
    raw = _curl("https://gretil.sub.uni-goettingen.de/gretil.htm")
    results = []
    # Parse basic listing
    for line in raw.split("\n"):
        if "href" in line and ".htm" in line:
            parts = line.split('"')
            if len(parts) >= 2:
                href = parts[1]
                name = href.replace(".htm", "").replace("_", " ")
                if any(k in name.lower() for k in ["tantra", "agama", "yoga", "veda"]):
                    results.append({"source": "gretil", "id": href, "title": name})
    return results[:5]


def search_pandit(query: str) -> list[dict]:
    """Check PANDiT for works."""
    url = f"https://pandit.cds.iisc.ac.in/api/search?q={query}"
    raw = _curl(url)
    try:
        data = json.loads(raw)
        return [{"source": "pandit", "id": str(r.get("id", "")),
                 "title": r.get("title", "")}
                for r in data.get("results", [])[:5]]
    except Exception:
        return []


def probe_all(query: str) -> list[dict]:
    """Probe all sources for a query."""
    results = []
    results.extend(search_archive_org(query))
    results.extend(search_gretil())
    results.extend(search_pandit(query))
    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", default="", help="search query")
    ap.add_argument("--gretil", action="store_true")
    a = ap.parse_args()

    if a.gretil:
        results = search_gretil()
        for r in results:
            print(f"  {r['source']:10} {r['id']:30} {r['title']}")
        return 0

    if a.probe:
        print(f"Probing: {a.probe}")
        results = probe_all(a.probe)
        if results:
            for r in results:
                print(f"  {r['source']:10} {r['id']:30} {r['title'][:40]}")
        else:
            print("  no results")
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
