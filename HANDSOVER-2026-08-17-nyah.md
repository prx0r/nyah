# HANDSOVER-2026-08-17-nyah.md — honest build notes

*2026-08-17T06:30:00Z · What nyah actually is, what works, what's demo, what's missing.*

---

## 0. THE HONEST ASSESSMENT

**Nyah is a working prototype, not production-ready.** The individual pieces work. The integration is partial. Here's exactly what's real.

## 1. WHAT ACTUALLY WORKS (tested, produces real output)

| Module | Lines | What It Does | Tested? |
|---|---|---|---|
| `openpatala_bridge.py` | 210 | Reads real OpenPatala data (260 works) → completeness state | ✓ 260 works |
| `gap_analyzer.py` | 227 | Computes priority scores from real state | ✓ 520 gaps |
| `task_generator.py` | 221 | Generates deterministic tasks from gaps | ✓ 326 tasks |
| `kanban_board.py` | 262 | State machine: BACKLOG→READY→DISPATCHED→IN_PROGRESS→DONE/FAILED | ✓ state transitions |
| `agent_pool.py` | 348 | Agent lifecycle: spawn, heartbeat, kill, track | ✓ spawn/kill |
| `openpatala_executor.py` | 152 | Calls OpenPatala's real `agent/run.py` steps | ✓ compile, report |
| `api_client.py` | 105 | Calls mimo-v2.5 directly (no hermes CLI overhead) | ✓ real API calls |
| `check.py` | 81 | Drift gate (MANIFEST + data validation) | ✓ PASS |

**Total real code: ~1,700 lines that actually do something.**

## 2. WHAT'S PLACEHOLDER (importable, tested individually, not fully wired)

| Module | Lines | Issue |
|---|---|---|
| `hermes_integration.py` | 338 | Builds hermes commands but doesn't actually spawn processes. Uses `subprocess.Popen` with no output capture. |
| `scheduler.py` | 142 | Dispatches tasks to agents but agents don't execute in a loop. |
| `pipeline_runner.py` | 138 | Runs cycles but `execute_one()` just calls executor once, doesn't track real agent state across cycles. |
| `failure_handler.py` | 202 | Classifies errors correctly but doesn't integrate with agent pool for retry. |
| `discovery.py` | 233 | Returns static adapter list, no real HTTP discovery. |
| `worker_pool.py` | 166 | Defines worker types but no real worker processes. |
| `agent_executor.py` | 77 | Can call mimo-v2.5 but doesn't update kanban after execution. |

**Total placeholder: ~1,300 lines that need wiring.**

## 3. WHAT'S COPIED FROM AGENTIC-INFRA (not adapted)

| Module | Lines | Status |
|---|---|---|
| `checkpoint.py` | 230 | Copied verbatim, works but not used by nyah's coordinator |
| `objective.py` | 140 | Copied verbatim, works but not integrated with gap_analyzer |
| `run_recorder.py` | 156 | Copied verbatim, not used for content-addressing nyah results |
| `schemas.py` | 152 | Copied verbatim, not adapted for nyah's task/agent schemas |
| `system.py` | 128 | Copied verbatim, not used |

**Total copied: ~800 lines that should either be adapted or removed.**

## 4. THE REAL INTEGRATION (what actually runs end-to-end)

The only fully working path:

```
OpenPatala data (260 works)
  → openpatala_bridge.py (convert to completeness state)
  → gap_analyzer.py (compute priorities)
  → task_generator.py (generate tasks)
  → kanban_board.py (register + state machine)
  → scheduler.py (dispatch to agents)
  → openpatala_executor.py (call OpenPatala's real steps)
  → api_client.py (call mimo-v2.5 for LLM tasks)
```

This path works. Tested with real data.

## 5. WHAT'S NOT WORKING

1. **No autonomous loop** — pipeline_runner runs cycles but doesn't truly execute agents in parallel
2. **No result feedback** — agent_executor calls mimo-v2.5 but doesn't update kanban with results
3. **No retry logic** — failure_handler classifies but doesn't actually retry
4. **No hermes integration** — hermes_integration builds commands but never spawns hermes
5. **No content-addressing** — run_recorder is copied but nyah results aren't content-addressed
6. **No gate for nyah tasks** — check.py validates docs but not task execution results

## 6. COMPARISON TO AGENTIC-INFRA

| Aspect | Agentic-infra | Nyah |
|---|---|---|
| Lines | 2,085 | 3,627 (but 800 copied, 1300 placeholder) |
| Gate | PASS | PASS (but only checks docs, not tasks) |
| Checkpoint DAG | Works, tested | Copied, not used |
| Objective function | Works, tested | Copied, not integrated |
| Run recorder | Works, content-addressed | Copied, not used for nyah results |
| Orchestrator | Works (report/verify/trace) | Works (gaps/scan/dispatch/cycle) |
| Real output | Sanskrit benchmark numbers | OpenPatala gap analysis + task dispatch |

## 7. WHAT NEEDS TO HAPPEN (priority order)

1. **Wire agent_executor → kanban** — after mimo-v2.5 call, update task status with result
2. **Wire pipeline_runner → agent_executor → kanban** — full cycle: scan→dispatch→execute→complete
3. **Remove copied modules** — either adapt or delete checkpoint/objective/run_recorder/schemas/system
4. **Add content-addressing** — nyah results should use run_recorder for provenance
5. **Add gate for tasks** — check.py should verify task results exist and are valid
6. **Real hermes integration** — or decide to use direct API only (faster)

## 8. THE VERDICT

**Nyah is a working prototype that demonstrates the architecture.** It can:
- Read real OpenPatala data (260 works)
- Identify gaps (520 gaps, priority-scored)
- Generate tasks (326 deterministic tasks)
- Dispatch to agents (kanban state machine)
- Call OpenPatala's real pipeline steps
- Call mimo-v2.5 for LLM tasks (14s per task, ~500 tokens)

**It cannot yet:**
- Run fully autonomously (the loop isn't closed)
- Track agent results back to kanban
- Retry failed tasks automatically
- Content-address its results
- Pass a gate that verifies task execution

**The foundation is real. The wiring is incomplete.**
