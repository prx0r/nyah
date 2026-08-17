#!/usr/bin/env python3
"""pipeline/schemas.py — the CANONICAL DATA SPEC (the schema contracts + strict validators).

Every data file the lab writes has an EXACT field contract here. A validator enforces each contract — so a
malformed record, a missing field, or a wrong type is caught deterministically (the strict gate). This is
the schema registry that makes validation exact.

Each schema is a dict of {field: type-or-validator}. `validate(record, schema)` checks:
  - every required field is present with the right type
  - no unknown fields (strict — the spec is the contract)
  - content checks where needed (e.g. a run_signature is a 64-hex sha256)

Deterministic + stdlib. Used by `agent/validate_data.py` (the strict gate) + wired into `check.py`.
"""
from __future__ import annotations

import re
from typing import Any, Callable

# ── the canonical field types / validators ──────────────────────────────────
def _str(v): return isinstance(v, str)
def _int(v): return isinstance(v, int) and not isinstance(v, bool)
def _float(v): return isinstance(v, (int, float)) and not isinstance(v, bool)
def _bool(v): return isinstance(v, bool)
def _list(v): return isinstance(v, list)
def _dict(v): return isinstance(v, dict)
def _sha256(v): return isinstance(v, str) and re.fullmatch(r"[0-9a-f]{64}", v or "")
def _iso_ts(v): return isinstance(v, str) and bool(re.search(r"\d{4}-\d{2}-\d{2}T", v or ""))


# shorthand: F = float, I = int, S = str, B = bool, L = list, D = dict, H = sha256
F, I, S, B, L, D, H = _float, _int, _str, _bool, _list, _dict, _sha256


def _check(record: dict, spec: dict) -> list[str]:
    """Validate a record against a schema; return a list of violations (empty = valid)."""
    errs = []
    for field, chk in spec.items():
        if field not in record:
            errs.append(f"missing '{field}'")
            continue
        if isinstance(chk, (list, tuple)):  # a list of allowed values
            if record[field] not in chk:
                errs.append(f"'{field}'={record[field]!r} not in allowed {chk}")
        elif callable(chk):
            if not chk(record[field]):
                errs.append(f"'{field}'={record[field]!r} failed type/format check")
    return errs


# ── THE CANONICAL SCHEMAS (the exact contracts) ─────────────────────────────
# each key = the data file/stream, value = the field contract

RUN_RECORD = {  # data/corpus/runs/<sig>.json — the content-addressed run record
    "step": S, "run_signature": H, "out_hash": H, "gold_hash": H,
    "code_sha": H, "config_sha": H, "config": D, "metrics": D,
    "git": D, "ts": _iso_ts, "nanopublication": D,
}

EXPERIMENT = {  # data/corpus/registries/experiments.jsonl — a logged experiment
    "experiment_id": S, "layer": S, "config_key": S, "model": S, "test": S,
    "data_hash": S, "n": I, "date": _iso_ts, "avg_chrF": F, "avg_bleu1": F,
    "rows": L,
}

AGENT_RUN = {  # data/corpus/registries/agent-runs.jsonl — an orchestrator step
    "step": S, "ts": _iso_ts,
}

WATCHDOG = {  # data/corpus/registries/watchdog.jsonl — a watchdog cycle
    "ts": _iso_ts,
}

BENCHMARK_REGISTRY = {  # data/benchmark-registry.json — the legitimate benchmark gold
    "version": S, "created": _iso_ts, "passages": L, "n_passages": I,
    "decontamination": D, "lineage_requirements": L, "manifest_hash": H,
}

PASSAGE = {  # an entry in benchmark-registry.json passages[]
    "passage_id": S, "hash": H, "source": S, "school": S, "period": S,
    "tier": I, "genre": S, "source_id": S, "source_date": S, "license": S,
    "term_density": F, "n_terms": I,
    "references": L,       # multi-reference (PaliBench) — one or more independent translations
    "alternative_senses": D,  # interpretive alternatives (e.g. {vimarśa: [senses]})
}

CHECKPOINT = {  # data/checkpoints.json — the vision→checkpoint DAG
    "version": S, "checkpoints": D,
}
CHECKPOINT_ENTRY = {  # an entry in checkpoints.json checkpoints{}
    "name": S, "effect": S, "gate": S, "prereqs": L, "status": S, "ts": S,
}

FINETUNE_PAIR = {  # data/finetune/*.jsonl — a LoRA-ready register pair
    "instruction": S, "input": S, "output": S, "register": S, "source": S,
}

TRANSLATION_CLAIM = {  # the proof/verify assertion contract
    "source": S, "candidate": S, "deterministic_gate": S,
    "blocking": L, "run_signature": H,
}

# the master registry: file-path-pattern → schema (for the validator)
FILES = {
    "data/corpus/runs/*.json": RUN_RECORD,
    "data/corpus/registries/experiments.jsonl": EXPERIMENT,
    "data/corpus/registries/agent-runs.jsonl": AGENT_RUN,
    "data/corpus/registries/watchdog.jsonl": WATCHDOG,
    "data/benchmark-registry.json": BENCHMARK_REGISTRY,
    "data/checkpoints.json": CHECKPOINT,
    "data/finetune/*.jsonl": FINETUNE_PAIR,
}


def validate_record(record: dict, schema_name: str) -> list[str]:
    """Validate one record against a named schema. Empty list = valid."""
    spec = globals().get(schema_name)
    if not spec:
        return [f"no schema named '{schema_name}'"]
    return _check(record, spec)


if __name__ == "__main__":
    # a self-test: the schemas are internally consistent
    import sys
    ok = True
    for name in ["RUN_RECORD", "EXPERIMENT", "AGENT_RUN", "WATCHDOG", "BENCHMARK_REGISTRY",
                 "PASSAGE", "CHECKPOINT", "CHECKPOINT_ENTRY", "FINETUNE_PAIR", "TRANSLATION_CLAIM"]:
        if not globals().get(name):
            print(f"  ✗ missing schema {name}"); ok = False
    print("schemas: " + ("OK" if ok else "FAIL"))


CHALLENGE_PAIR = {  # data/challenge-sets/*.jsonl — a controlled bad translation (T+/T-)
    "source": S, "good": S, "bad": S, "error_family": S, "instruction": S,
}

MITRA_PAIR = {  # data/mitra-crosscanon/*.jsonl — a cross-canon triangulation pair
    "id": S, "src_lang": S, "tgt_lang": S, "sanskrit": S, "parallel": S,
}

ANNOTATION_RECORD = {  # data/annotation/*.jsonl — a human MQM gold annotation
    "passage_id": S, "source": S, "candidate_a": S, "candidate_b": S,
    "preference": S, "preference_reason": S, "errors": L, "annotator": S,
}


PROOF_EVIDENCE = {  # the proof-carrying translation artifact (visionadvice §12)
    "source": D, "candidate": D, "deterministic_gate": S, "blocking": L,
    "parallel_evidence": D, "candidate_distribution": D,
    "provenance": D, "decision": S, "artifact_hash": H,
}
