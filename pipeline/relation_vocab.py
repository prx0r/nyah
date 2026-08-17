#!/usr/bin/env python3
"""pipeline/relation_vocab.py — versioned relation vocabulary.

From newbuild1.md §54-55:
- Typed relations need versions
- Versioned relation vocabulary should be first-class
- Each relation: definition, allowed subject/object types, staleness, schema version

Usage:
  python3 pipeline/relation_vocab.py --list
  python3 pipeline/relation_vocab.py --validate --relation AUTHORED_BY --subject-type WORK --object-type PERSON
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOCAB_FILE = ROOT / "data" / "relation_vocab.json"

# The core relation vocabulary
RELATIONS = {
    "AUTHORED_BY": {
        "version": "1.0.0",
        "domain": ["WORK"],
        "range": ["PERSON"],
        "inverse": "AUTHOR_OF",
        "transitive": False,
        "deprecated": False,
        "semantics": "Work W was authored by Person P",
    },
    "EDITION_OF": {
        "version": "1.0.0",
        "domain": ["EDITION"],
        "range": ["WORK"],
        "inverse": "HAS_EDITION",
        "transitive": False,
        "deprecated": False,
        "semantics": "Edition E is an edition of Work W",
    },
    "WITNESS_OF": {
        "version": "1.0.0",
        "domain": ["WITNESS"],
        "range": ["WORK"],
        "inverse": "HAS_WITNESS",
        "transitive": False,
        "deprecated": False,
        "semantics": "Witness M is a manuscript witness of Work W",
    },
    "TRANSLATION_OF": {
        "version": "1.0.0",
        "domain": ["TRANSLATION"],
        "range": ["WORK"],
        "inverse": "HAS_TRANSLATION",
        "transitive": False,
        "deprecated": False,
        "semantics": "Translation T is a translation of Work W",
    },
    "SAME_WORK": {
        "version": "1.0.0",
        "domain": ["WORK"],
        "range": ["WORK"],
        "inverse": "SAME_WORK",
        "transitive": True,
        "deprecated": False,
        "semantics": "Two records refer to the same intellectual work",
    },
    "SUPPORTS": {
        "version": "1.0.0",
        "domain": ["ASSERTION"],
        "range": ["ASSERTION"],
        "inverse": "SUPPORTED_BY",
        "transitive": False,
        "deprecated": False,
        "semantics": "Assertion A provides evidence for Assertion B",
    },
    "CONTRADICTS": {
        "version": "1.0.0",
        "domain": ["ASSERTION"],
        "range": ["ASSERTION"],
        "inverse": "CONTRADICTED_BY",
        "transitive": False,
        "deprecated": False,
        "semantics": "Assertion A contradicts Assertion B",
    },
    "DEPENDS_ON": {
        "version": "1.0.0",
        "domain": ["ENTITY"],
        "range": ["ENTITY"],
        "inverse": None,
        "transitive": True,
        "deprecated": False,
        "semantics": "If X changes, Y must be reconsidered",
    },
    "DERIVED_FROM": {
        "version": "1.0.0",
        "domain": ["ENTITY"],
        "range": ["ENTITY"],
        "inverse": "HAS_DERIVATIVE",
        "transitive": False,
        "deprecated": False,
        "semantics": "Entity B was produced from Entity A",
    },
    "PART_OF": {
        "version": "1.0.0",
        "domain": ["PASSAGE"],
        "range": ["WORK"],
        "inverse": "HAS_PART",
        "transitive": False,
        "deprecated": False,
        "semantics": "Passage P is part of Work W",
    },
}


def _load_vocab() -> dict:
    if VOCAB_FILE.exists():
        return json.loads(VOCAB_FILE.read_text())
    # Initialize from RELATIONS
    vocab = {"version": "1.0.0", "relations": RELATIONS}
    VOCAB_FILE.parent.mkdir(parents=True, exist_ok=True)
    VOCAB_FILE.write_text(json.dumps(vocab, indent=2, ensure_ascii=False))
    return vocab


def list_relations() -> list[dict]:
    vocab = _load_vocab()
    return [{"name": k, **v} for k, v in vocab.get("relations", {}).items()]


def validate_relation(relation: str, subject_type: str, object_type: str) -> dict:
    """Validate that a relation can be used with given subject/object types."""
    vocab = _load_vocab()
    rel = vocab.get("relations", {}).get(relation)
    if not rel:
        return {"valid": False, "error": f"unknown relation: {relation}"}

    if subject_type not in rel["domain"]:
        return {"valid": False, "error": f"{relation} domain is {rel['domain']}, not {subject_type}"}
    if object_type not in rel["range"]:
        return {"valid": False, "error": f"{relation} range is {rel['range']}, not {object_type}"}

    return {"valid": True, "relation": relation, "semantics": rel["semantics"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--relation", default="")
    ap.add_argument("--subject-type", default="")
    ap.add_argument("--object-type", default="")
    a = ap.parse_args()

    if a.list:
        for r in list_relations():
            dep = " [DEPRECATED]" if r.get("deprecated") else ""
            print(f"  {r['name']:20} {r['domain']} → {r['range']}{dep}")
        return 0

    if a.validate and a.relation:
        result = validate_relation(a.relation, a.subject_type, a.object_type)
        print(json.dumps(result, indent=2))
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
