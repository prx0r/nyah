# NAVIGATION — the master index (resolve anything)

*The OpenAlex-style map for agentic-infra. Read `AGENTS.md` + `README.md` first, then this index to resolve
any concern to its doc, kernel, and command. Everything is a projection; the truth is the checkpoint DAG +
the trace + run_recorder.*

---

## 1. THE ONE-LINE MAP
> **A reusable, objective scaffolding: write a vision → it decomposes into granular checkpoints → the
> autonomous driver works them (objective-ordered, gate-decided) → hands over cleanly. Any project adopting
> it becomes agent-runnable.**

## 2. THE DOCS (read order)

| Doc | What | Read when |
|---|---|---|
| `AGENTS.md` | the governing rules + anti-mess standard | orienting / before any work |
| `CODING-AGENT.md` | the strict operational discipline | writing code |
| `HANDSOVER-TEMPLATE.md` | the canonical handover spec | handing over |
| `VISION.md` | the vision (three pillars) | understanding the goal |
| `README.md` | the project index | orienting |
| `docs/guide/AUTONOMOUS.md` | **the set-and-forget flow** — one autonomous system | driving it as an agent |
| `docs/recipes/` | **every command** an agent runs | doing a task |
| `docs/reference/` | **every kernel + function** explained | understanding a specific piece |

## 3. THE KERNELS (reference)

| Kernel | File | Role | Key functions |
|---|---|---|---|
| Checkpoint DAG | `pipeline/checkpoint.py` | the vision→checkpoint DAG | `define` `decompose` `advance` `next_cp` `mark` `run_gate` `status` |
| Objective | `pipeline/objective.py` | weighted multi-axis scoring + pick-next | `Objective` `candidate_value` `pick_next` `value_over_cost` |
| Run recorder | `pipeline/run_recorder.py` | content-addressed provenance + nanopublication | `RunRecorder` `run_signature` `epistemic_kind` `sha256` |
| Schemas | `pipeline/schemas.py` | the canonical data contracts | `validate(record, schema)` |

## 4. THE ORCHESTRATOR STEPS (`agent/run.py`)

| Step | What | Use |
|---|---|---|
| `report` | project summary (docs, runs, gate) | orienting |
| `verify` | the verification gate (registry audit) | before claiming done |
| `trace` | query the run/experiment trace | "what ran" |
| `memory` | query the DML deterministic memory | recall a past decision |
| `ramwatch` | the RAM/CPU budget verdict | box safety |
| `checkpoints` | the checkpoint DAG status | "what's done / next" |
| `objective` | the objective demo + objective-ordered next | choosing what's next |
| `autonomous` | **the set-and-forget DAG driver** | running the vision autonomously |

## 5. THE GATE

```bash
python3 check.py --status          # docs registered + refs resolve
python3 agent/test_objective.py    # the objective-kernel smoke test
python3 agent/ramwatch.py          # box budget
```

## 6. THE THREE-PILLAR MAP (VISION)

```
ORGANIZE   → AGENTS/CODING-AGENT/HANDSOVER/README/VISION + the file lifecycle
VERIFY     → check.py + run_recorder + eigenius kind + verify/audit/trace
AUTONOMOUS → checkpoint DAG (decompose) + objective (pick) + advance (drive)
```
