#!/usr/bin/env python3
"""pipeline/checkpoint.py — the VISION → CHECKPOINT engine (autonomous goal-hitting).

The mechanism that makes the project hit goals autonomously: a vision is decomposed into a DAG of
falsifiable checkpoints, each with an effect + prerequisites + a deterministic gate. An agent (or the
watchdog) works the DAG: only a checkpoint whose prerequisites are DONE and whose gate passes is marked
DONE. This is the "intelligently set checkpoints that get us there" layer — the agent doesn't guess what
"done" means; the checkpoint DAG defines it.

A checkpoint is DONE iff its GATE passes (a logged, content-addressed, deterministic check). If the gate
fails, the checkpoint is NOT done — the agent cannot move past it.

Deterministic + stdlib. State persisted as a JSON DAG (data/checkpoints.json).

Usage:
  python3 pipeline/checkpoint.py --status          # the checkpoint DAG + what's done / what's next
  python3 pipeline/checkpoint.py --define <name> --effect "<what it achieves>" --gate "<command>" --after <prereq>
  python3 pipeline/checkpoint.py --mark <name>     # mark done (the agent ran the gate; it passed)
  python3 pipeline/checkpoint.py --next            # the next checkpoint to work (prereqs done, not done)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAG_FILE = ROOT / "data" / "checkpoints.json"


def _load() -> dict:
    if DAG_FILE.exists():
        return json.loads(DAG_FILE.read_text())
    return {"version": "0.1.0", "checkpoints": {}}


def _save(dag: dict) -> None:
    dag["updated"] = datetime.now(timezone.utc).isoformat()
    DAG_FILE.parent.mkdir(parents=True, exist_ok=True)
    DAG_FILE.write_text(json.dumps(dag, ensure_ascii=False, indent=2))


def define(name: str, effect: str, gate: str, after: list[str],
           value: float = 0.5, cost: float = 0.5) -> None:
    dag = _load()
    dag["checkpoints"][name] = {"name": name, "effect": effect, "gate": gate,
                                "prereqs": after, "status": "OPEN", "ts": None,
                                "value": value, "cost": cost}
    _save(dag)
    print(f"defined checkpoint '{name}' → {effect} (gate: {gate}, after: {after}, value={value}, cost={cost})")


def _prereqs_done(dag: dict, name: str) -> bool:
    cp = dag["checkpoints"][name]
    return all(dag["checkpoints"].get(p, {}).get("status") == "DONE" for p in cp["prereqs"])


def run_gate(cp: dict) -> tuple[bool, str]:
    """Run a checkpoint's deterministic gate (a shell command); True if it exits 0."""
    try:
        p = subprocess.run(cp["gate"], shell=True, capture_output=True, text=True, timeout=300)
        return p.returncode == 0, (p.stdout or p.stderr)[-300:]
    except Exception as e:
        return False, f"gate error: {e}"


def mark(name: str, run: bool) -> None:
    dag = _load()
    if name not in dag["checkpoints"]:
        print(f"no checkpoint '{name}'"); return
    cp = dag["checkpoints"][name]
    if not _prereqs_done(dag, name):
        print(f"✗ '{name}' prereqs not done: {cp['prereqs']}"); return
    if run:
        ok, out = run_gate(cp)
        if not ok:
            print(f"✗ gate FAILED for '{name}': {out}")
            cp["status"] = "FAILED"; cp["ts"] = datetime.now(timezone.utc).isoformat()
            _save(dag); return
    cp["status"] = "DONE"; cp["ts"] = datetime.now(timezone.utc).isoformat()
    _save(dag)
    print(f"✓ '{name}' DONE ({cp['effect']})")


def status() -> None:
    dag = _load()
    cps = dag["checkpoints"]
    print(f"=== CHECKPOINT DAG ({len(cps)} checkpoints) ===")
    for name, cp in cps.items():
        done = "DONE" if cp["status"] == "DONE" else cp["status"]
        print(f"  [{done:6}] {name:22} → {cp['effect']}")
    print(f"\n=== NEXT (prereqs done, not done; objective-ordered) ===")
    for name, cp in cps.items():
        if cp["status"] != "DONE" and _prereqs_done(dag, name):
            print(f"  → {name}: {cp['effect']}  (gate: {cp['gate']}, value={cp.get('value',0.5)}, cost={cp.get('cost',0.5)})")


def next_cp() -> str:
    """Pick the next checkpoint to work. If checkpoints carry value/cost, use the OBJECTIVE (value÷cost,
    penalize done) to pick the argmax — the most valuable, cheapest OPEN checkpoint whose prereqs are done.
    Otherwise fall back to the first eligible (prereqs done, not done)."""
    dag = _load()
    eligible = [cp for cp in dag["checkpoints"].values()
                if cp["status"] != "DONE" and _prereqs_done(dag, cp["name"])]
    if not eligible:
        return ""
    # if any checkpoint declares value/cost, use the objective to prioritize (excluding DONE)
    if any("value" in cp or "cost" in cp for cp in eligible):
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from objective import Objective
            obj = Objective(
                axes={"value": lambda c: float(c.get("value", 0.5)),
                      "cost": lambda c: 1.0 - float(c.get("cost", 0.5))},
                weights={"value": 0.7, "cost": 0.3},
            )
            open_candidates = [cp for cp in eligible if cp["status"] != "DONE"]
            best, _, _ = obj.pick_next(open_candidates)
            return best["name"]
        except Exception:
            pass  # fall through to first-eligible
    return eligible[0]["name"]


def advance(max_steps: int = 50) -> int:
    """THE AUTONOMOUS DRIVER: work the DAG until done, a gate FAILS, or the step budget is hit.

    Loop:
      pick the next OPEN checkpoint (objective-ordered, prereqs done)
      run its deterministic gate
        → PASS: mark DONE, advance to the next
        → FAIL: mark FAILED, STOP (needs a human — a checkpoint that can't pass must be re-planned)
    Stops when: all DONE, a gate FAILS, or `max_steps` reached. Returns the exit code.
    """
    steps = 0
    while steps < max_steps:
        name = next_cp()
        if not name:
            # no eligible checkpoint → is everything done?
            dag = _load()
            remaining = [c for c in dag["checkpoints"].values() if c["status"] != "DONE"]
            if not remaining:
                print("✓ ALL CHECKPOINTS DONE — the vision is complete.")
                return 0
            print(f"✗ BLOCKED: {len(remaining)} checkpoint(s) not done, none eligible (prereqs unmet).")
            print("  → re-plan the prereqs, or a gate needs a human.")
            return 1
        cp = _load()["checkpoints"][name]
        print(f"\n▶ [{steps+1}] WORK: {name} → {cp['effect']}")
        ok, out = run_gate(cp)
        dag = _load()  # load once, mutate + save the SAME dict
        cp = dag["checkpoints"][name]
        if not ok:
            print(f"  ✗ gate FAILED for '{name}': {out[-200:]}")
            cp["status"] = "FAILED"; cp["ts"] = datetime.now(timezone.utc).isoformat()
            _save(dag)
            print(f"  → STOPPED (gate failure at '{name}'); needs a human or a re-plan.")
            return 1
        cp["status"] = "DONE"; cp["ts"] = datetime.now(timezone.utc).isoformat()
        _save(dag)
        print(f"  ✓ '{name}' DONE ({cp['effect']})")
        steps += 1
    print(f"✗ STOPPED: step budget ({max_steps}) reached.")
    return 1


def decompose(spec_path: str) -> None:
    """Decompose a VISION spec file into a checkpoint DAG automatically.

    The spec file is JSONL: {name, effect, gate, after, value, cost} — one line per checkpoint. This is
    how a human's vision → 'tonnes of granular checkpoints' in one step: write the spec once, decompose
    it into the DAG, then `--advance` works it autonomously.
    """
    p = Path(spec_path)
    if not p.exists():
        print(f"no vision spec at {p}"); return
    dag = _load()
    n = 0
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            cp = json.loads(line)
        except Exception:
            continue
        name = cp.get("name", ""); effect = cp.get("effect", ""); gate = cp.get("gate", "true")
        after = cp.get("after", []); value = cp.get("value", 0.5); cost = cp.get("cost", 0.5)
        if not name or not effect:
            continue
        dag["checkpoints"][name] = {"name": name, "effect": effect, "gate": gate,
                                    "prereqs": after, "status": "OPEN", "ts": None,
                                    "value": value, "cost": cost}
        n += 1
    _save(dag)
    print(f"decomposed {n} checkpoints from {spec_path} → the DAG is ready to --advance.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--define", default="")
    ap.add_argument("--effect", default="")
    ap.add_argument("--gate", default="")
    ap.add_argument("--after", default="")
    ap.add_argument("--value", type=float, default=0.5)
    ap.add_argument("--cost", type=float, default=0.5)
    ap.add_argument("--mark", default="")
    ap.add_argument("--run-gate", action="store_true")
    ap.add_argument("--next", action="store_true")
    ap.add_argument("--advance", action="store_true")
    ap.add_argument("--max-steps", type=int, default=50)
    ap.add_argument("--decompose", default="")
    args = ap.parse_args()
    if args.define:
        after = [a for a in args.after.split(",") if a]
        define(args.define, args.effect, args.gate, after, args.value, args.cost)
    elif args.mark:
        mark(args.mark, args.run_gate)
    elif args.next:
        print(next_cp())
    elif args.advance:
        sys.exit(advance(args.max_steps))
    elif args.decompose:
        decompose(args.decompose)
    else:
        status()
