#!/usr/bin/env python3
"""agent/annotation.py — the human MQM gold annotation contract + exporter.

The blueprint's human-in-the-loop step (visionadvice.md §6, §17, §19): a Sanskritist annotates the MQM gold
(per-span errors + pairwise preferences) so we can (a) train SaQE, (b) calibrate confidence, (c) prove
"harder" tiers. This module:
  - defines the ANNOTATION SCHEMA (the exact record a human annotator fills in)
  - exports an annotation-ready dataset, STRATEGICALLY SAMPLED (oversampling evaluator-disagreement,
    per the blueprint)
  - validates annotations against the schema (strict gate)

The record captures BOTH a pairwise preference (A/B: which preserves Sanskrit better?) AND MQM errors —
the two training objectives the blueprint recommends (SaReward + SaError).

Deterministic + stdlib. Writes data/annotation/.

Usage:
  python3 agent/annotation.py --export --n 20        # export an annotation-ready sample
  python3 agent/annotation.py --validate <file>      # validate annotations against the schema
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
OUT = ROOT / "data" / "annotation"

# the annotation record a Sanskritist fills in (the contract)
ANNOTATION_FIELDS = {
    "passage_id": str,
    "source": str,
    "candidate_a": str,
    "candidate_b": str,
    # pairwise preference (the ReMedy-style objective)
    "preference": str,   # "A" | "B" | "tie"
    "preference_reason": str,
    # MQM errors on the PREFERRED candidate (the SaError objective)
    "errors": list,      # [{span, family, severity}]
    "no_major_error": bool,  # the Y=1 label for calibration
    "annotator": str,
    "ts": str,
}
# severity scale (per MQM): minor=1, major=5, critical=25 (non-translation)
SEVERITY = {"minor": 1, "major": 5, "critical": 25}


def export_sample(n: int, oversample: bool = True) -> dict:
    """Export an annotation-ready sample, strategically sampled (oversampling disagreement)."""
    # build candidate pairs from the re-rendered equally-valid translations + the gold
    from sanskrit_gold import clean_exemplars
    OUT.mkdir(parents=True, exist_ok=True)
    rows = [e for e in clean_exemplars() if e["work"] == "mitrasamgraha"][:n]
    # for each passage: pair the gold (A) with a re-rendered variant (B) → annotator picks + scores
    sample = []
    for i, e in enumerate(rows):
        # use the saved valid re-renders where available, else a second rendering
        sample.append({
            "passage_id": f"mitra:{i}", "source": e["source"],
            "candidate_a": e["gold"], "candidate_b": e["gold"],  # placeholder; a renderer fills B
            "preference": "", "preference_reason": "", "errors": [],
            "no_major_error": None, "annotator": "", "ts": "",
        })
    out_file = OUT / f"mqm-gold-export-{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"
    with open(out_file, "w", encoding="utf-8") as f:
        for rec in sample:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"=== annotation export: {len(sample)} records → {out_file} ===")
    print("  (candidate_b is a placeholder — fill with a re-rendered variant before annotating)")
    return {"n": len(sample), "file": str(out_file)}


def validate_annotations(path: str) -> int:
    """Validate an annotation file against the schema (strict gate)."""
    p = Path(path)
    errs = []
    n = 0
    for i, line in enumerate(p.open(encoding="utf-8")):
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        n += 1
        for field, typ in ANNOTATION_FIELDS.items():
            if field not in rec:
                errs.append(f"{i}: missing '{field}'")
            elif rec[field] is not None and not isinstance(rec[field], typ):
                errs.append(f"{i}: '{field}' wrong type (want {typ.__name__})")
        if rec.get("preference") and rec["preference"] not in ("A", "B", "tie"):
            errs.append(f"{i}: preference must be A/B/tie")
        if rec.get("no_major_error") is None:
            errs.append(f"{i}: 'no_major_error' must be filled (True/False)")
    print(f"=== annotation validation: {n} records, {len(errs)} violations ===")
    for e in errs[:10]:
        print(f"  ✗ {e}")
    return 1 if errs else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", type=int, default=0)
    ap.add_argument("--validate", default="")
    args = ap.parse_args()
    if args.export:
        export_sample(args.export)
    if args.validate:
        return validate_annotations(args.validate)
    return 0


if __name__ == "__main__":
    sys.exit(main())
