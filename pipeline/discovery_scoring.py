#!/usr/bin/env python3
"""pipeline/discovery_scoring.py — score sources by value.

From newbuildmainspec §40:
- SourceUtility { novelty_yield, works_per_request, source_quality, rights_clarity,
  structuredness, authority_value, target_gap_match, acquisition_cost, failure_rate }

Usage:
  python3 pipeline/discovery_scoring.py --score gretil
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Pre-scored known providers
PROVIDER_SCORES = {
    "gretil": {"novelty_yield": 0.7, "works_per_request": 0.8, "source_quality": 0.9,
               "rights_clarity": 0.7, "structuredness": 0.9, "authority_value": 0.8,
               "target_gap_match": 0.7, "acquisition_cost": 0.3, "failure_rate": 0.1},
    "archive.org": {"novelty_yield": 0.6, "works_per_request": 0.5, "source_quality": 0.5,
                    "rights_clarity": 0.3, "structuredness": 0.3, "authority_value": 0.5,
                    "target_gap_match": 0.6, "acquisition_cost": 0.4, "failure_rate": 0.3},
    "muktabodha": {"novelty_yield": 0.9, "works_per_request": 0.7, "source_quality": 0.95,
                   "rights_clarity": 0.4, "structuredness": 0.8, "authority_value": 0.9,
                   "target_gap_match": 0.9, "acquisition_cost": 0.5, "failure_rate": 0.1},
    "pandit": {"novelty_yield": 0.8, "works_per_request": 0.6, "source_quality": 0.85,
               "rights_clarity": 0.5, "structuredness": 0.7, "authority_value": 0.9,
               "target_gap_match": 0.8, "acquisition_cost": 0.3, "failure_rate": 0.15},
    "openalex": {"novelty_yield": 0.4, "works_per_request": 0.9, "source_quality": 0.7,
                 "rights_clarity": 0.9, "structuredness": 0.95, "authority_value": 0.6,
                 "target_gap_match": 0.5, "acquisition_cost": 0.1, "failure_rate": 0.05},
}


def score_provider(provider: str) -> dict:
    """Score a provider. Higher = more valuable to check."""
    scores = PROVIDER_SCORES.get(provider)
    if not scores:
        return {"provider": provider, "score": 0, "error": "unknown provider"}

    # Weighted composite
    weights = {"source_quality": 0.2, "target_gap_match": 0.2, "authority_value": 0.15,
               "structuredness": 0.15, "novelty_yield": 0.1, "acquisition_cost": 0.1,
               "rights_clarity": 0.1}

    composite = sum(scores[k] * w for k, w in weights.items())
    return {"provider": provider, "score": round(composite, 3), "breakdown": scores}


def rank_providers() -> list[dict]:
    """Rank all known providers by score."""
    results = [score_provider(p) for p in PROVIDER_SCORES]
    results.sort(key=lambda r: r["score"], reverse=True)
    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--score", default="", help="score one provider")
    ap.add_argument("--rank", action="store_true")
    a = ap.parse_args()

    if a.score:
        r = score_provider(a.score)
        print(json.dumps(r, indent=2))
        return 0

    if a.rank:
        for r in rank_providers():
            print(f"  {r['score']:.3f}  {r['provider']:15}")
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
