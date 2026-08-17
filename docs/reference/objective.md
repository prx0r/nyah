# REFERENCE — the objective kernel (`pipeline/objective.py`)

*The objective function: a reusable kernel that scores a candidate (action / checkpoint / result) on
multiple weighted axes and returns a single comparable utility. This is what lets an agent pick the NEXT
checkpoint that maximizes progress per unit of effort, rather than guessing.*

---

## The core

### `class Objective(axes, weights)`
A weighted multi-axis scorer over candidate objects.
- `axes` = `{name: callable(candidate) -> float in [0,1]}` (the objective components)
- `weights` = `{name: float}` (positive; normalized internally)

### `Objective.normalize() -> dict`
Normalize the weights to sum to 1 (deterministic).

### `Objective.candidate_value(obj) -> (utility, breakdown)`
Score a candidate: `Σ wᵢ · axisᵢ(obj)`, clamped to [0,1]. Returns the utility + a per-axis breakdown.
**CLI:** `python3 pipeline/objective.py --demo`

### `Objective.pick_next(candidates, done=None, done_penalty=0.5) -> (best, value, breakdown)`
Return the candidate maximizing utility; penalize already-done candidates (so it doesn't redo them).

## The built-in axes (reusable objective components)

| Factory | What it scores |
|---|---|
| `axis_progress_toward_vision(value)` | how much a candidate moves toward the vision (0-1) |
| `axis_effort(cost, max_cost=1.0)` | LOWER cost = higher utility (inverted, normalized) |
| `axis_pass_rate(pass_count, total)` | the historical pass rate of similar candidates |

## The default factory

### `value_over_cost(progress_weight=0.7, cost_weight=0.3) -> Objective`
The default objective: **maximize progress toward the vision per unit of effort.** (You fill in the axis
functions with your domain's progress/cost.)

## The demo
```bash
python3 pipeline/objective.py --demo
# best next = ingest-corpus (utility 0.75, {progress: 0.9, cost: 0.4})
```
It picks the high-progress, moderate-cost candidate — the argmax of value÷cost.

## How it's used in the autonomous driver
`checkpoint.next_cp()` uses `pick_next` over the OPEN checkpoints (value=progress, cost=cheap-is-better)
to choose the next most-valuable-cheapest one. The driver then runs that checkpoint's gate.

## The smoke test
```bash
python3 agent/test_objective.py   # 7 assertions: normalization, argmax, done-penalty, value/cost weighting
```
