# AUTONOMOUS — the set-and-forget flow (one autonomous system)

*2026-08-16 · How to use agentic-infra as ONE autonomous system: say your vision once, it marks out
granular checkpoints, then works them independently until done. This is the human-on-the-loop model —
you only return when a gate genuinely can't pass.*

---

## 1. THE FLOW (one paragraph)

```
YOU: write vision.jsonl (a list of {name, effect, gate, after, value, cost})
   → --decompose → the checkpoint DAG (tons of granular checkpoints)
   → --step autonomous → the driver works the DAG:
        pick the next most-valuable-cheapest OPEN checkpoint (objective)
        run its deterministic gate → PASS (DONE, advance) or FAIL (STOP for you)
   → ALL DONE → "the vision is complete"
```

## 2. THE VISION SPEC (the only thing you write)

`vision.jsonl` — one checkpoint per line:
```jsonl
{"name":"setup-box","effect":"verify the box budget","gate":"true","value":0.3,"cost":0.1}
{"name":"ingest-corpus","effect":"ingest the corpus","gate":"test -f data/corpus.json","after":["setup-box"],"value":0.9,"cost":0.6}
{"name":"run-gate","effect":"all gates pass","gate":"python3 check.py --status","after":["ingest-corpus"],"value":0.5,"cost":0.2}
```

| field | what | notes |
|---|---|---|
| `name` | the checkpoint id | unique |
| `effect` | what it achieves (the human-readable goal) | shown in status |
| `gate` | a shell command that exits 0 = DONE | **the deterministic "done" test** |
| `after` | prerequisite checkpoint names | the DAG edges |
| `value` | how much it moves toward the vision (0-1) | the objective weights it |
| `cost` | how expensive it is (0-1) | cheaper is better |

## 3. THE COMMANDS (the whole thing)

```bash
cd /root/<project>
# 1. your vision → the DAG
python3 pipeline/checkpoint.py --decompose vision.jsonl

# 2. see what it planned
python3 pipeline/checkpoint.py --status

# 3. set it and forget it (works autonomously until done/fail/budget)
python3 agent/run.py --step autonomous --max-steps 100
#    or directly:
python3 pipeline/checkpoint.py --advance --max-steps 100
```

## 4. WHAT THE DRIVER DOES (exactly)

For each step, the driver:
1. `next_cp()` — picks the OPEN checkpoint whose prereqs are done, **maximizing value ÷ cost** (objective).
2. `run_gate(cp)` — runs the checkpoint's gate command.
3. `PASS` → marks `DONE`, advances. `FAIL` → marks `FAILED`, **STOPS** (you re-plan or fix).
4. Repeats until: all DONE, a gate FAILS, or the step budget is hit.

**The guarantee:** the deterministic gate decides "done," never the agent. It cannot mark a checkpoint
done by declaring it so.

## 5. THE STOP CONDITIONS (when it returns to you)

| Condition | Message | What to do |
|---|---|---|
| All checkpoints DONE | `✓ ALL CHECKPOINTS DONE` | review the handover |
| A gate FAILED | `✗ STOPPED (gate failure at '<name>')` | fix the gate or re-plan the checkpoint |
| Blocked (prereqs unmet) | `✗ BLOCKED: N not done, none eligible` | fix the prereqs (DAG issue) |
| Step budget hit | `✗ STOPPED: step budget reached` | raise `--max-steps` or re-plan |

## 6. THE SUBAGENT / PARALLEL OPTION

For a checkpoint that needs parallel work or independent verification, use Hermes's kanban swarm (see
`docs/guide/HERMES.md`) — the swarm's outcome then still faces the checkpoint's deterministic gate.

## 7. THE GATE (before claiming done)

```bash
python3 check.py --status          # docs + refs + manifest
python3 agent/test_objective.py    # the objective kernel works
python3 agent/ramwatch.py          # box budget
```
