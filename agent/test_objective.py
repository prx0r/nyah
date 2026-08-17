#!/usr/bin/env python3
"""agent/test_objective.py — the smoke test for the objective-function kernel.

Verifies the objective kernel (pipeline/objective.py) is deterministic and correct:
  1. `candidate_value` computes Σ w_i·axis_i, clamped to [0,1].
  2. `pick_next` returns the argmax utility.
  3. `pick_next` penalizes already-done candidates.
  4. value-over-cost prioritizes cheap wins when cost is weighted, value when value is weighted.

Exit 0 if all pass (the gate), 1 otherwise. Wired into the gate via run.py --step objective.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

from objective import Objective  # noqa: E402

fails = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        fails.append(f"{name}: {detail}")
        print(f"  ✗ {name}: {detail}")
    else:
        print(f"  ✓ {name}")


# 1. candidate_value is normalized + clamped
obj = Objective(axes={"a": lambda c: c["a"], "b": lambda c: c["b"]},
                weights={"a": 0.5, "b": 0.5})
val, brk = obj.candidate_value({"a": 0.8, "b": 0.2})
check("value-normalized", abs(val - 0.5) < 1e-6, f"got {val} (want 0.5)")
check("breakdown-keys", set(brk) == {"a", "b"})

# 2. pick_next returns argmax
cands = [{"name": "x", "a": 0.9, "b": 0.1}, {"name": "y", "a": 0.1, "b": 0.9}]
best, v, _ = obj.pick_next(cands)
check("pick-argmax", best["name"] == "x", f"got {best['name']}")
check("pick-value", abs(v - 0.5) < 1e-6, f"got {v}")

# 3. pick_next penalizes done
best2, _, _ = obj.pick_next(cands, done={"x"})
check("pick-penalizes-done", best2["name"] == "y", f"got {best2['name']}")

# 4. value-over-cost: cheap win wins when cost weighted; value win wins when value weighted
cheap = {"name": "cheap", "value": 0.4, "cost": 0.1}
big = {"name": "big", "value": 0.9, "cost": 0.9}
value_obj = Objective(axes={"value": lambda c: c["value"], "cost": lambda c: 1.0 - c["cost"]},
                      weights={"value": 0.8, "cost": 0.2})
cost_obj = Objective(axes={"value": lambda c: c["value"], "cost": lambda c: 1.0 - c["cost"]},
                     weights={"value": 0.2, "cost": 0.8})
b_val, _, _ = value_obj.pick_next([cheap, big])
b_cost, _, _ = cost_obj.pick_next([cheap, big])
check("value-weighted-picks-big", b_val["name"] == "big", f"got {b_val['name']}")
check("cost-weighted-picks-cheap", b_cost["name"] == "cheap", f"got {b_cost['name']}")

print(f"\nobjective smoke test: {'ALL PASS' if not fails else f'{len(fails)} FAIL'}")
sys.exit(1 if fails else 0)
