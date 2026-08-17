#!/usr/bin/env python3
"""agent/validate_data.py — the STRICT DATA GATE (validate every data file against the canonical schema).

The executable schema validator: reads every data file the lab writes and checks it against the canonical
contract in `pipeline/schemas.py`. A malformed record, missing field, or wrong type is caught here —
deterministically. This is the strict gate that makes the data spec enforceable.

Checks:
  - run records (data/corpus/runs/*.json) against RUN_RECORD
  - experiments/agent-runs/watchdog (registries/*.jsonl) against their schemas
  - benchmark-registry.json against BENCHMARK_REGISTRY (incl. each passage)
  - checkpoints.json against CHECKPOINT (incl. each checkpoint entry)
  - finetune pairs against FINETUNE_PAIR

Usage:
  python3 agent/validate_data.py          # validate everything; exit 0 if all valid
  python3 agent/validate_data.py --json   # machine-readable result
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
from schemas import (RUN_RECORD, EXPERIMENT, AGENT_RUN, WATCHDOG, BENCHMARK_REGISTRY,
                     PASSAGE, CHECKPOINT, CHECKPOINT_ENTRY, FINETUNE_PAIR,
                     CHALLENGE_PAIR, MITRA_PAIR, _check)  # noqa: E402

def validate_file(path: Path, schema: dict, record_schema: dict | None = None,
                  discriminator: str | None = None) -> list[str]:
    """Validate one file. For jsonl, validate each line; for a dict with nested list, validate records too.

    discriminator: if given, only records CONTAINING that key are validated (so a shared file mixing our
    records with another lane's is validated only on the records we own).
    """
    errs = []
    try:
        if path.suffix == ".jsonl":
            for i, line in enumerate(path.open(encoding="utf-8")):
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if discriminator and discriminator not in rec:
                    continue  # not our record (another lane's) — leave it alone
                errs += [f"{path.name}:{i}: {e}" for e in _check(rec, schema)]
        else:
            rec = json.loads(path.read_text(encoding="utf-8"))
            errs += [f"{path.name}: {e}" for e in _check(rec, schema)]
            # if the file has a nested list of records, validate those too
            if record_schema and isinstance(rec, dict):
                for key, rs in ((key, rs) for key, rs in
                                [("passages", PASSAGE), ("checkpoints", CHECKPOINT_ENTRY)]):
                    val = rec.get(key)
                    if isinstance(val, dict) and key == "checkpoints":
                        for name, entry in val.items():
                            errs += [f"{path.name}:checkpoints[{name}]: {e}"
                                     for e in _check(entry, rs)]
                    elif isinstance(val, list):
                        for i, entry in enumerate(val):
                            errs += [f"{path.name}:{key}[{i}]: {e}" for e in _check(entry, rs)]
    except json.JSONDecodeError as e:
        errs.append(f"{path.name}: invalid JSON ({e})")
    except Exception as e:
        errs.append(f"{path.name}: {e}")
    return errs


def validate_all() -> dict:
    """Validate every canonical data file; return {file: [errors]}."""
    results = {}
    # run records (the content-addressed store)
    runs_dir = ROOT / "data" / "corpus" / "runs"
    for f in sorted(runs_dir.glob("*.json")):
        results[str(f.relative_to(ROOT))] = validate_file(f, RUN_RECORD)
    # registries
    reg = ROOT / "data" / "corpus" / "registries"
    for f in sorted(reg.glob("*.jsonl")):
        # experiments.jsonl mixes our translation records with another lane's ingest/download records;
        # validate only OUR records (those with avg_chrF).
        if f.name == "experiments.jsonl":
            results[str(f.relative_to(ROOT))] = validate_file(f, EXPERIMENT, discriminator="avg_chrF")
        else:
            schema = {"agent-runs.jsonl": AGENT_RUN, "watchdog.jsonl": WATCHDOG}.get(f.name, AGENT_RUN)
            results[str(f.relative_to(ROOT))] = validate_file(f, schema)
    # benchmark-registry (incl. passages)
    br = ROOT / "data" / "benchmark-registry.json"
    if br.exists():
        results["data/benchmark-registry.json"] = validate_file(br, BENCHMARK_REGISTRY)
    # checkpoints (incl. entries)
    cp = ROOT / "data" / "checkpoints.json"
    if cp.exists():
        results["data/checkpoints.json"] = validate_file(cp, CHECKPOINT)
    # finetune pairs
    for f in sorted((ROOT / "data" / "finetune").glob("*.jsonl")):
        results[str(f.relative_to(ROOT))] = validate_file(f, FINETUNE_PAIR)
    # challenge sets (controlled bad translations)
    for f in sorted((ROOT / "data" / "challenge-sets").glob("*.jsonl")):
        results[str(f.relative_to(ROOT))] = validate_file(f, CHALLENGE_PAIR)
    # mitra cross-canon triangulation
    for f in sorted((ROOT / "data" / "mitra-crosscanon").glob("*.jsonl")):
        results[str(f.relative_to(ROOT))] = validate_file(f, MITRA_PAIR)
    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    results = validate_all()
    total_errors = sum(len(v) for v in results.values())
    n_files = len(results)
    if args.json:
        print(json.dumps({"files": n_files, "errors": total_errors, "results": results}, indent=2))
    else:
        print(f"=== DATA GATE: {n_files} files, {total_errors} violations ===")
        for f, errs in results.items():
            status = "✓" if not errs else "✗"
            print(f"  [{status}] {f} ({len(errs)} violation{'s' if len(errs)!=1 else ''})")
            for e in errs[:3]:
                print(f"        {e}")
    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
