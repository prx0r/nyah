# HERMES + NYAH — how hermes drives the NRAH task coordinator

*2026-08-17 · Hermes is the execution engine; nyah is the brain. Hermes runs subagents, manages kanban,
and handles cron-driven autonomous cycles. Nyah decides what work to do; hermes does it.*

---

## 1. THE DIVISION OF LABOR

| Concern | Owns | How |
|---|---|---|
| What tasks exist | nyah | gap_analyzer + task_generator |
| Which task next | nyah | scheduler (objective function) |
| Execute a task | hermes | subagents, kanban dispatch |
| Track progress | nyah | trace (agent-steps.jsonl) |
| Autonomous loops | hermes cron | triggers nyah scan/dispatch cycles |
| Review/audit | hermes | review gates, verification |

## 2. HERMES COMMANDS FOR NYAH

```bash
# scan for new tasks
hermes -z "cd /root/nyah && python3 agent/run.py --step scan"

# analyze gaps
hermes -z "cd /root/nyah && python3 agent/run.py --step gaps"

# dispatch next batch
hermes -z "cd /root/nyah && python3 agent/run.py --step dispatch"

# full report
hermes -z "cd /root/nyah && python3 agent/run.py --step report"

# worker pool status
hermes -z "cd /root/nyah && python3 agent/run.py --step pool"

# discovery modes
hermes -z "cd /root/nyah && python3 agent/run.py --step discovery"

# autonomous cycle (checkpoint DAG)
hermes -z "cd /root/nyah && python3 agent/run.py --step autonomous --max-steps 100"
```

## 3. KANBAN INTEGRATION

Nyah tasks map to kanban cards:
- `PENDING` → backlog
- `DISPATCHED` → in-progress
- `DONE` → done
- `FAILED` → blocked (needs human)

Board: `nyah` (create with `hermes kanban create nyah`)

## 4. CRON-DRIVEN AUTONOMOUS CYCLE

Set up a hermes cron job to run nyah's scan→gap→dispatch cycle periodically:

```bash
hermes cron add --name "nrah-cycle" --schedule "0 */6 * * *" \
  --command "cd /root/nyah && python3 agent/run.py --step scan && python3 agent/run.py --step gaps && python3 agent/run.py --step dispatch"
```

This runs every 6 hours: scan for new tasks, analyze gaps, dispatch to workers.

## 5. SUBAGENT PATTERN

When nyah dispatches a task, hermes spawns a subagent for the worker type:

```
nyah dispatches FIND_SOURCE task to "discovery" worker
  → hermes spawns subagent with discovery objective
  → subagent runs adapter sweeps / protocol discovery
  → subagent writes results to data/tasks/
  → nyah picks up results in next cycle
```

## 6. REVIEW GATES

Every dispatched task has a deterministic gate:
- nyah generates the task with a gate command
- hermes subagent executes the work
- gate command verifies the state changed
- only then is the task marked DONE

The gate is never the agent's opinion. It's a deterministic check.
