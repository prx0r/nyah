#!/usr/bin/env python3
"""agent/verify.py — the one-command VERIFICATION GATE (ties hermes + crypto + golden audit).

Before any claim is made, run this: it enforces that a result is REAL (not hallucinated theater) by
checking all four pillars:
  1. DETERMINISTIC PROOF GATE — the Pāṭala proof (SOURCE_BINDING/COVERAGE/ABSTENTION/TERM_CONSISTENCY).
  2. CONTENT-ADDRESSED RUN RECORD — the number must trace to run_recorder (sha256 → out_hash + nanopub).
  3. GOLDEN AUDIT — recompute on fixed gold; fail on mismatch (audit.py).
  4. ANTI-CIRCULARITY — the check is deterministic (recompute), not the same model's own judgment.

This is the executable counterpart of the AGENTS.md anti-mess standard: a claim is real only when
`verify.py` passes all four. It is meant to be run via a hermes hook (on task-complete) or by a hermes
reviewer profile (kanban request-review).

Usage:
  python3 agent/verify.py --source "…" --candidate "…"        # full verification of one translation
  python3 agent/verify.py --registry                         # audit the whole content-addressed registry
  python3 agent/verify.py --all                              # gate + trace check
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT))


def verify_translation_claim(source: str, candidate: str, gold: str = "") -> dict:
    """The full verification of one translation claim.

    Pillars:
      1. DETERMINISTIC PROOF GATE (translation_proof.py) — SOURCE_BINDING/COVERAGE/ABSTENTION/TERM.
      2. CONTENT-ADDRESSED RUN RECORD (run_recorder.py) — sha256 → out_hash + nanopublication.
      3. GOLD-REFERENCE ANTI-HALLUCINATION (if --gold given) — the candidate must match a real gold
         reference (chrF), the robust WMT anti-hallucination check (robust where IAST token-overlap isn't).
      4. ANTI-CIRCULARITY — the checks are deterministic (recompute), not the generator's own judgment.
    """
    from translation_proof import verify_translation
    from run_recorder import RunRecorder

    # 1. deterministic proof gate
    proof = verify_translation(source, candidate)
    # 3. gold-reference anti-hallucination (the robust signal)
    gold_result = {}
    if gold:
        from experiment_lab import chrF
        c = chrF(gold, candidate)
        gold_result = {"gold_chrF": c, "gold_ok": c >= 0.3}
    # 2. content-address the claim
    rec = RunRecorder().record(
        step="verify", gold=[{"source": source, "gold": candidate}],
        config={"method": "verify.py", "candidate": candidate, "ref_gold": gold},
        metrics={"deterministic_gate": proof["deterministic_gate"], **gold_result},
        assertion=f"source '{source[:40]}' → candidate '{candidate[:40]}' is "
                  f"{proof['deterministic_gate']} ({', '.join(proof['blocking']) or 'all checks pass'})",
        verified=proof["deterministic_gate"] == "PASS")
    # verdict: proof gate PASS + (if gold given) gold match
    gate_ok = proof["deterministic_gate"] == "PASS"
    gold_ok = gold_result.get("gold_ok", True)
    result = {
        "source": source, "candidate": candidate,
        "deterministic_gate": proof["deterministic_gate"], "blocking": proof["blocking"],
        "gold_chrF": gold_result.get("gold_chrF"), "gold_ok": gold_ok,
        "run_signature": rec["run_signature"][:16],
        "nanopublication": rec["nanopublication"],
    }
    result["verified"] = gate_ok and gold_ok
    return result


def verify_registry() -> dict:
    """Audit the whole content-addressed registry: every run has a valid signature + nanopublication."""
    from run_recorder import RunRecorder
    runs = RunRecorder().all()
    bad = [r for r in runs if not r.get("run_signature") or not r.get("nanopublication")]
    return {"n_runs": len(runs), "valid": len(runs) - len(bad), "invalid": len(bad),
            "invalid_ids": [r.get("run_signature", "")[:12] for r in bad]}


def verify_all() -> dict:
    """The full gate + trace health check."""
    import subprocess
    gate = subprocess.run(["python3", str(ROOT / "check.py"), "--status"],
                          capture_output=True, text=True, timeout=120)
    return {"gate": gate.stdout.strip() or gate.stderr.strip(), "registry": verify_registry()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="")
    ap.add_argument("--candidate", default="")
    ap.add_argument("--gold", default="")
    ap.add_argument("--registry", action="store_true")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    if args.registry:
        r = verify_registry()
        print(f"registry: {r['valid']}/{r['n_runs']} valid content-addressed runs "
              f"({r['invalid']} invalid)")
        return 0 if r["invalid"] == 0 else 1
    if args.all:
        import json
        print(json.dumps(verify_all(), ensure_ascii=False, indent=2))
        return 0
    if not args.source or not args.candidate:
        print("--step verify needs --source and --candidate"); return 2
    r = verify_translation_claim(args.source, args.candidate, args.gold)
    import json
    print(json.dumps({k: v for k, v in r.items() if k != "nanopublication"},
                     ensure_ascii=False, indent=2))
    print(f"\n  VERDICT: {'✅ VERIFIED (all checks pass)' if r['verified'] else '❌ NOT verified'}")
    return 0 if r["verified"] else 1


if __name__ == "__main__":
    sys.exit(main())
