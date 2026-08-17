# HANDSOVER-2026-08-17-nyah.md — build notes

*2026-08-17T06:35:00Z · What nyah actually does, what's wired, what's not.*

---

## WHAT WORKS (tested, end-to-end, real data)

### The live path (all tested with real OpenPatala API + mimo-v2.5)

```
OpenPatala API (254 works, live at :8800)
  → openpatala_bridge.py (fetch via /works endpoint)
  → gap_analyzer.py (priority-score gaps)
  → task_generator.py (deterministic tasks)
  → kanban_board.py (state machine)
  → agent_executor.py (call mimo-v2.5 directly)
  → kanban update (task marked DONE with result)
```

### Test results (5 autonomous cycles)

| Cycle | Task | Work | Time | Tokens | Answer |
|---|---|---|---|---|---|
| 1 | RESOLVE_RIGHTS | Aghoraśiva corpus | 10.9s | 425 | OPEN |
| 2 | RESOLVE_RIGHTS | Aghoraśiva Tattvaprakāśikā | 9.4s | 418 | OPEN |
| 3 | ANCHOR_TRANSLATION | Akulavīratantra | 11.1s | 671 | alignment info |
| 4 | TRANSLATE | Akulavīratantra | 8.8s | 673 | translation attempt |
| 5 | RESOLVE_RIGHTS | Aghoraśiva Tattvasaṃgraha | 6.7s | 432 | OPEN |

**Total: 5 tasks, ~46s, ~2600 tokens, all DONE.**

### Module status

| Module | Status | Evidence |
|---|---|---|
| `openpatala_bridge.py` | ✓ LIVE | Reads from API: 254 works |
| `gap_analyzer.py` | ✓ WORKS | 520 gaps from 254 works |
| `task_generator.py` | ✓ WORKS | 326 tasks generated |
| `kanban_board.py` | ✓ WORKS | State transitions working |
| `agent_executor.py` | ✓ LIVE | mimo-v2.5 calls, ~10s/task |
| `api_client.py` | ✓ LIVE | Direct API, no hermes overhead |
| `pipeline_runner.py` | ✓ LIVE | 5 cycles completed |
| `openpatala_executor.py` | ✓ WORKS | Calls OpenPatala compile/report |
| `check.py` | ✓ PASS | Gate passes |

## WHAT'S NOT WIRED YET

1. **failure_handler** — classifies errors but doesn't retry
2. **discovery.py** — static adapter list, no real HTTP
3. **copied modules** — checkpoint, objective, run_recorder, schemas, system (from agentic-infra, not adapted)
4. **content-addressing** — results not content-addressed
5. **verification gate** — no check that task results are valid

## HOW TO RUN

```bash
cd /root/nyah

# live autonomous (5 cycles, real API, mimo-v2.5)
python3 pipeline/pipeline_runner.py --autonomous --max-cycles 5

# single cycle
python3 pipeline/pipeline_runner.py --cycle

# check what's been done
ls data/tasks/results/

# gate
python3 check.py --status
```

## INTEGRATION WITH OPENPATALA

Nyah reads from OpenPatala's live API:
- `GET /works` → list all works
- Each work has `translation_status` (none/partial/full/machine) and `verified`
- Nyah identifies works needing translation, generates tasks, executes via mimo-v2.5

OpenPatala is the data source. Nyah is the task coordinator.
