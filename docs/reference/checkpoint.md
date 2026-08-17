# REFERENCE — the checkpoint DAG kernel (`pipeline/checkpoint.py`)

*The vision→checkpoint engine. A vision is decomposed into a DAG of falsifiable checkpoints, each with an
effect + prerequisites + a deterministic gate. An agent (or the autonomous driver) works the DAG: only a
checkpoint whose prereqs are DONE and whose gate PASSES is marked DONE.*

---

## The data model (`data/checkpoints.json`)
```json
{ "version": "0.1.0", "updated": "…",
  "checkpoints": {
    "ingest-corpus": { "name": "ingest-corpus", "effect": "ingest the corpus",
      "gate": "test -f data/corpus.json", "prereqs": ["setup-box"],
      "status": "OPEN|DONE|FAILED", "ts": null, "value": 0.9, "cost": 0.6 }
  } }
```
`status`: OPEN (not started) · DONE (gate passed) · FAILED (gate failed, needs re-plan).

## The functions

### `define(name, effect, gate, after, value=0.5, cost=0.5)`
Add one checkpoint to the DAG. **CLI:** `--define <name> --effect "…" --gate "<cmd>" --after a,b --value 0.9 --cost 0.6`

### `decompose(spec_path)`
Turn a vision spec (JSONL of checkpoint lines) into the whole DAG at once. **CLI:** `--decompose vision.jsonl`
This is the "my vision → tons of granular checkpoints" step.

### `_prereqs_done(dag, name) -> bool`
True if every prerequisite checkpoint is DONE. A checkpoint is only workable when its prereqs are done.

### `run_gate(cp) -> (ok, output)`
Run a checkpoint's gate (a shell command) → True if it exits 0, plus the output. **This is the
deterministic "done" test.**

### `mark(name, run=False)`
Mark a checkpoint DONE manually (or run its gate first if `--run-gate`). Skips if prereqs not done.
**CLI:** `--mark <name> [--run-gate]`

### `status()`
Print the DAG: every checkpoint + its status + the objective-ordered NEXT set. **CLI:** `--status`

### `next_cp() -> name`
Pick the next OPEN checkpoint whose prereqs are done. If checkpoints carry value/cost, uses the objective
(value÷cost, penalizing done) to pick the **most valuable-cheapest** — not just the first.

### `advance(max_steps=50) -> exit_code`
**THE AUTONOMOUS DRIVER.** Works the DAG: pick next → run gate → PASS (DONE, advance) / FAIL (FAILED, stop).
Returns 0 if all done, 1 if blocked/failed/budget-hit. **CLI:** `--advance --max-steps 100`

### `_load()` / `_save(dag)`
The DAG is persisted as `data/checkpoints.json`; `_load` reads it, `_save` writes it (timestamped).

---

## The CLI summary
| Command | What |
|---|---|
| `python3 pipeline/checkpoint.py --status` | the DAG + next |
| `python3 pipeline/checkpoint.py --decompose vision.jsonl` | vision → checkpoints |
| `python3 pipeline/checkpoint.py --advance --max-steps 100` | the autonomous driver |
| `python3 pipeline/checkpoint.py --next` | print the next checkpoint |
| `python3 pipeline/checkpoint.py --define <name> --effect "…" --gate "<cmd>" --after a --value 0.9 --cost 0.6` | add one |
| `python3 pipeline/checkpoint.py --mark <name> --run-gate` | mark done (via its gate) |
