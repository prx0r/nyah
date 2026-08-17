#!/usr/bin/env python3
"""pipeline/provenance.py — nanopublication triples for results.

From newbuild1.md + agentic-infra:
- Every headline number ships as {assertion, evidence, provenance}
- Content-addressed run records
- The crypto layer proves integrity, never quality

Usage:
  python3 pipeline/provenance.py --create --task-id t1 --assertion "rights=OPEN" --evidence "mimo-v2.5 response"
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROVENANCE_DIR = ROOT / "data" / "provenance"
PROVENANCE_DIR.mkdir(parents=True, exist_ok=True)


def create_nanopub(task_id: str, assertion: str, evidence: str,
                   provenance: dict | None = None) -> dict:
    """Create a nanopublication triple."""
    assertion_hash = hashlib.sha256(assertion.encode()).hexdigest()
    evidence_hash = hashlib.sha256(evidence.encode()).hexdigest()

    nanopub = {
        "id": f"np_{task_id}_{assertion_hash[:8]}",
        "assertion": assertion,
        "assertion_hash": f"sha256:{assertion_hash}",
        "evidence": evidence,
        "evidence_hash": f"sha256:{evidence_hash}",
        "provenance": provenance or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Save
    (PROVENANCE_DIR / f"{nanopub['id']}.json").write_text(
        json.dumps(nanopub, indent=2, ensure_ascii=False))

    return nanopub


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--create", action="store_true")
    ap.add_argument("--task-id", default="test")
    ap.add_argument("--assertion", default="")
    ap.add_argument("--evidence", default="")
    a = ap.parse_args()

    if a.create:
        np = create_nanopub(a.task_id, a.assertion, a.evidence)
        print(json.dumps(np, indent=2))
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
