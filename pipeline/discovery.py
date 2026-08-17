#!/usr/bin/env python3
"""pipeline/discovery.py — the 5 discovery modes for source acquisition.

From newbuildmainspec §32-36:
  Mode A — Known Adapter Sweeps (PANDiT, GRETIL, FoJin, Archive.org, etc.)
  Mode B — Protocol Discovery (homepage → robots → sitemap → feeds → API → IIIF → OAI-PMH)
  Mode C — Graph Expansion (every observed item yields leads)
  Mode D — Gap-Driven Discovery (system generates DiscoveryObjectives from missing state)
  Mode E — Frontier Source Discovery (agents find genuinely unknown sources)

Each mode produces SourceCandidate records. No mode auto-authorizes crawling — all go through
policy check first.

Usage:
  python3 pipeline/discovery.py --demo
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "data" / "tasks"


# Mode A: known adapters (the reliable ones)
KNOWN_ADAPTERS = [
    {"name": "PANDiT", "url": "https://pandit.cds.iisc.ac.in/", "type": "CATALOG",
     "capabilities": ["discover", "metadata"], "adapter": "PANDiT"},
    {"name": "GRETIL", "url": "https://www.sub.uni-goettingen.de/ebt_www/gretil/", "type": "REPOSITORY",
     "capabilities": ["discover", "metadata", "content"], "adapter": "GRETIL"},
    {"name": "FoJin", "url": "https://fojin.io/", "type": "REPOSITORY",
     "capabilities": ["discover", "metadata", "content"], "adapter": "FOJIN"},
    {"name": "Archive.org", "url": "https://archive.org/", "type": "REPOSITORY",
     "capabilities": ["discover", "metadata", "content"], "adapter": "ARCHIVE_ORG"},
    {"name": "OpenAlex", "url": "https://api.openalex.org/", "type": "AGGREGATOR",
     "capabilities": ["discover", "metadata", "search"], "adapter": "OPENALEX"},
    {"name": "Crossref", "url": "https://api.crossref.org/", "type": "AGGREGATOR",
     "capabilities": ["metadata", "search"], "adapter": "CROSSREF"},
    {"name": "Muktabodha", "url": "https://muktabodha.org/digital-library/", "type": "REPOSITORY",
     "capabilities": ["discover", "metadata", "content"], "adapter": "MUKTABODHA"},
    {"name": "SARIT", "url": "https://sangamproject.in/sarit/", "type": "REPOSITORY",
     "capabilities": ["discover", "metadata", "content"], "adapter": "SARIT"},
]


def mode_a_adapter_sweeps() -> list[dict]:
    """Mode A: emit discovery tasks for known adapters."""
    candidates = []
    for adapter in KNOWN_ADAPTERS:
        candidates.append({
            "discovery_mode": "A_ADAPTER_SWEEP",
            "source_name": adapter["name"],
            "source_url": adapter["url"],
            "source_type": adapter["type"],
            "suspected_capabilities": adapter["capabilities"],
            "adapter": adapter["adapter"],
            "requires_policy_review": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    return candidates


def mode_b_protocol_discovery(homepage: str) -> dict:
    """Mode B: for a new domain, probe standard protocol surfaces.

    Returns a checklist of things to probe (not actual network calls — that's the worker's job).
    """
    return {
        "discovery_mode": "B_PROTOCOL_DISCOVERY",
        "target_url": homepage,
        "probe_sequence": [
            "robots.txt",
            "sitemap.xml",
            "RSS/Atom feeds",
            "known API endpoints",
            "IIIF manifests",
            "OAI-PMH endpoint",
            "GitHub/Git repos",
            "bulk dump links",
        ],
        "requires_policy_review": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def mode_c_graph_expansion(observation: dict) -> list[dict]:
    """Mode C: extract leads from an observed item.

    Every observation can yield leads: publisher, institution, series, editor,
    author, repository, external identifier, linked edition, citation.
    """
    leads = []
    # Extract leads from observation fields
    for field_name in ["publisher", "institution", "series", "editor", "author", "repository"]:
        value = observation.get(field_name)
        if value:
            leads.append({
                "discovery_mode": "C_GRAPH_EXPANSION",
                "source_observation": observation.get("id", ""),
                "target_type": field_name,
                "candidate_name": value,
                "reason": f"observed {field_name} in source data",
                "status": "PENDING",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
    # External IDs
    for ext_id in observation.get("external_ids", []):
        leads.append({
            "discovery_mode": "C_GRAPH_EXPANSION",
            "source_observation": observation.get("id", ""),
            "target_type": "external_id",
            "candidate_name": ext_id.get("value", ""),
            "reason": f"external ID: {ext_id.get('scheme', '?')}",
            "status": "PENDING",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    return leads


def mode_d_gap_driven(work: dict) -> list[dict]:
    """Mode D: generate discovery objectives from missing state.

    If a work has a translation that references an unknown edition → FIND_EDITION.
    If a work has no source → FIND_SOURCE.
    """
    objectives = []
    source = work.get("source_state", "NONE")
    translation = work.get("translation_state", "NONE_KNOWN")

    if source == "NONE":
        objectives.append({
            "discovery_mode": "D_GAP_DRIVEN",
            "objective_type": "FIND_SOURCE",
            "work_id": work.get("id", ""),
            "work_title": work.get("preferred_title", ""),
            "reason": "work has no source material",
            "status": "PENDING",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    if source in ("ETEXT", "SCHOLARLY_ETEXT") and translation == "NONE_KNOWN":
        objectives.append({
            "discovery_mode": "D_GAP_DRIVEN",
            "objective_type": "SEARCH_TRANSLATION",
            "work_id": work.get("id", ""),
            "work_title": work.get("preferred_title", ""),
            "reason": "source-ready but no translation found",
            "status": "PENDING",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    return objectives


def mode_e_frontier(domain: str = "sanskrit") -> dict:
    """Mode E: frontier source discovery — agents find genuinely unknown sources.

    Returns an objective spec for an agent to search for new sources.
    """
    return {
        "discovery_mode": "E_FRONTIER",
        "domain": domain,
        "objective": (
            "Find machine-readable or catalog-accessible sources likely to contain "
            f"{domain} works absent from OpenPatala."
        ),
        "agent_output_contract": {
            "candidate_sources": [{
                "url": "...",
                "name": "...",
                "evidence": [{"url": "...", "observed_text": "..."}],
                "suspected_capabilities": ["catalog", "etext"],
                "estimated_relevance": 0.0,
                "reason": "...",
                "requires_policy_review": True,
            }]
        },
        "requires_policy_review": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def demo() -> None:
    """Demo all 5 discovery modes."""
    print("=== MODE A: Known Adapter Sweeps ===")
    mode_a = mode_a_adapter_sweeps()
    for c in mode_a:
        print(f"  {c['source_name']:15} {c['source_type']:12} {c['adapter']}")

    print("\n=== MODE B: Protocol Discovery ===")
    mode_b = mode_b_protocol_discovery("https://example-sanskrit-archive.org/")
    for step in mode_b["probe_sequence"]:
        print(f"  probe: {step}")

    print("\n=== MODE C: Graph Expansion ===")
    sample_obs = {"id": "obs_001", "publisher": "Motilal Banarsidass", "author": "Abhinavagupta",
                  "institution": "IFP", "external_ids": [{"scheme": "PANDiT", "value": "12345"}]}
    mode_c = mode_c_graph_expansion(sample_obs)
    for lead in mode_c:
        print(f"  lead: {lead['target_type']:15} → {lead['candidate_name']}")

    print("\n=== MODE D: Gap-Driven ===")
    sample_work = {"id": "PTW_003", "preferred_title": "Vijnanabhairava",
                   "source_state": "NONE", "translation_state": "NONE_KNOWN"}
    mode_d = mode_d_gap_driven(sample_work)
    for obj in mode_d:
        print(f"  objective: {obj['objective_type']} → {obj['work_title']}")

    print("\n=== MODE E: Frontier ===")
    mode_e = mode_e_frontier("sanskrit")
    print(f"  objective: {mode_e['objective'][:80]}...")

    total = len(mode_a) + 1 + len(mode_c) + len(mode_d) + 1
    print(f"\n=== TOTAL: {total} candidates from 5 modes ===")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        demo()
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
