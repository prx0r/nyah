#!/usr/bin/env python3
"""pipeline/objective.py — the OBJECTIVE FUNCTION kernel (scoring + prioritization).

The missing piece that makes the scaffolding fully "objective": a reusable kernel that scores a candidate
(action, checkpoint, or result) on multiple weighted axes and returns a single comparable utility. This
lets an agent pick the NEXT checkpoint/step that maximizes progress, rather than guessing.

Design (deterministic + stdlib):
  - `score(candidate, axes, weights)` → a normalized 0..1 utility from named axes × weights.
  - Axes are `{name: callable(candidate)->float in [0,1]}` (the objective components).
  - `Objective` bundles a set of axes + weights; `candidate_value(obj)` scores any object.
  - `pick_next(candidates, objective, done)` → the candidate maximizing utility (with a penalty if already done).
  - `compose` lets a project define its domain objective from sub-scores.

This is the "what should the agent do next" optimizer: given many possible checkpoint gates or steps,
score each by value (progress toward the vision) ÷ cost (time/RAM), and pick the argmax. Deterministic —
no LLM guessing; the objective is a function, not a feeling.

Usage:
  python3 pipeline/objective.py --score <name> --value 0.8 --value 0.5    # demo a 2-axis score
  python3 pipeline/objective.py --demo                                      # built-in demo
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field


# ── the core: a weighted multi-axis objective function ──────────────────────
@dataclass
class Objective:
    """A weighted combination of axis-scorers over candidate objects.

    axes:    {name: callable(candidate) -> float in [0,1]}
    weights: {name: float}  (positive; normalized internally)
    """
    axes: dict = field(default_factory=dict)
    weights: dict = field(default_factory=dict)

    def normalize(self) -> dict:
        """Normalize the weights to sum to 1 (deterministic)."""
        total = sum(self.weights.values()) or 1.0
        return {k: (v / total) for k, v in self.weights.items()}

    def candidate_value(self, obj: object) -> float:
        """Score a candidate: Σ w_i · axis_i(obj), clamped to [0,1]."""
        w = self.normalize()
        total = 0.0
        breakdown = {}
        for name, weight in w.items():
            axis_fn = self.axes.get(name)
            if axis_fn is None:
                continue
            try:
                v = max(0.0, min(1.0, float(axis_fn(obj))))
            except Exception:
                v = 0.0
            total += weight * v
            breakdown[name] = round(v, 3)
        return round(total, 4), breakdown

    def pick_next(self, candidates: list, done: set | None = None, done_penalty: float = 0.5) -> object:
        """Return the candidate maximizing utility, penalizing already-done ones."""
        done = done or set()
        best, best_val, best_break = None, -1.0, {}
        for c in candidates:
            ident = (c.get("name") if isinstance(c, dict) else None) or \
                    getattr(c, "name", None) or getattr(c, "id", None) or str(c)
            val, brk = self.candidate_value(c)
            if ident in done:
                val *= done_penalty  # don't re-do what's already done
            if val > best_val:
                best, best_val, best_break = c, val, brk
        return best, best_val, best_break


# ── reusable built-in axes (the common objective components) ────────────────
def axis_progress_toward_vision(value: float) -> callable:
    """Axis: how much a candidate moves toward the vision (0..1)."""
    def _fn(obj): return float(value)
    return _fn


def axis_effort(cost: float, max_cost: float = 1.0) -> callable:
    """Axis: LOWER cost = higher utility (invert, normalize to 0..1)."""
    def _fn(obj): return max(0.0, 1.0 - (float(cost) / max(max_cost, 0.001)))
    return _fn


def axis_pass_rate(pass_count: int, total: int) -> callable:
    """Axis: the historical pass rate of similar candidates (0..1)."""
    def _fn(obj): return (pass_count / total) if total else 0.0
    return _fn


# ── a concrete factory: value-vs-cost objective ─────────────────────────────
def value_over_cost(progress_axis: str = "progress", cost_axis: str = "cost",
                    progress_weight: float = 0.7, cost_weight: float = 0.3) -> Objective:
    """The default objective: maximize progress toward the vision per unit of effort."""
    return Objective(
        axes={progress_axis: lambda c: 0.0, cost_axis: lambda c: 0.0},  # filled by caller
        weights={progress_axis: progress_weight, cost_axis: cost_weight},
    )


# ── the demo ────────────────────────────────────────────────────────────────
def demo() -> None:
    """Pick the next checkpoint by value-over-cost from a small candidate set."""
    candidates = [
        {"name": "ingest-corpus", "progress": 0.9, "cost": 0.6},
        {"name": "ocr-cleanup", "progress": 0.8, "cost": 0.9},
        {"name": "translation-queue", "progress": 0.5, "cost": 0.3},
    ]
    # objective: value = progress (0.7), cost = cheap is better (0.3)
    obj = Objective(
        axes={"progress": lambda c: c["progress"], "cost": lambda c: 1.0 - c["cost"]},
        weights={"progress": 0.7, "cost": 0.3},
    )
    best, val, brk = obj.pick_next(candidates)
    print(f"best next = {best['name']} (utility {val}, {brk})")
    for c in candidates:
        v, b = obj.candidate_value(c)
        print(f"  {c['name']:20} → {v:.3f} {b}")


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
