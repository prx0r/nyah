# HANDSOVER-2026-08-17-nyah.md — build notes

*2026-08-17T06:40:00Z · nyah status after newbuild1.md architecture integration.*

---

## WHAT WORKS (tested, end-to-end)

### Live path (all tested with real OpenPatala API + mimo-v2.5 + newbuild1.md architecture)

```
OpenPatala API (254 works, live at :8800)
  → openpatala_bridge.py (fetch via /works endpoint)
  → gap_analyzer.py (priority-score gaps)
  → task_generator.py (deterministic tasks)
  → kanban_board.py (state machine)
  → agent_executor.py (call mimo-v2.5)
    → event_log.py (TaskStarted/TaskCompleted events)
    → provenance.py (nanopub: {assertion, evidence, provenance})
    → digest.py (content-addressed result)
    → kanban update (DONE with result)
```

### newbuild1.md architecture (all implemented)

| Component | File | Status |
|---|---|---|
| Schema registry | `schema_registry.py` | ✓ 5 core schemas registered, immutable |
| Event log | `event_log.py` | ✓ append-only, TaskStarted/TaskCompleted |
| Digests | `digest.py` | ✓ sha256/sha512, canonical JSON |
| Entity IDs | `entity_id.py` | ✓ opaque UUIDv7-style with prefix |
| Provenance | `provenance.py` | ✓ nanopub triples for every result |

### Test results (5 autonomous cycles)

| Cycle | Task | Work | Time | Tokens | Answer |
|---|---|---|---|---|---|
| 1 | RESOLVE_RIGHTS | Aghoraśiva corpus | 19.0s | 397 | OPEN |
| 2 | RESOLVE_RIGHTS | Aghoraśiva Tattvaprakāśikā | 9.1s | 346 | OPEN |
| 3 | ANCHOR_TRANSLATION | Akulavīratantra | 13.5s | 671 | alignment info |
| 4 | TRANSLATE | Akulavīratantra | 11.8s | 673 | translation attempt |
| 5 | RESOLVE_RIGHTS | Aghoraśiva Tattvasaṃgraha | 22.7s | 429 | Open |

**Evidence:** 10 events logged, 5 nanopubs created, 5 content-addressed results.

### What nyah is now

- **Reads live OpenPatala** — 254 works via API
- **Identifies gaps** — 222 works need translation
- **Generates tasks** — deterministic from completeness state
- **Executes via mimo-v2.5** — ~14s per task, ~500 tokens
- **Full provenance** — every result has event log + nanopub + digest
- **Schema registry** — 5 core schemas, immutable
- **Gate** — check.py passes

### What's still incomplete

1. **failure_handler** — not wired to scheduler for retry
2. **discovery.py** — static adapter list, no real HTTP
3. **copied modules** — checkpoint, objective, run_recorder not adapted
4. **verification gate** — no check that results are valid
5. **autonomous budget** — no max-completions stop condition

### Commands

```bash
cd /root/nyah
python3 pipeline/pipeline_runner.py --autonomous --max-cycles 5
python3 pipeline/event_log.py --recent 10
python3 pipeline/schema_registry.py --list
ls data/provenance/
ls data/tasks/results/
python3 check.py --status
```
