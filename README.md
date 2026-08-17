# NYAH — NRAH task coordinator

*2026-08-17 · Autonomous task coordinator for OpenPatala. Reads completeness state, generates
deterministic tasks, prioritizes by objective function, dispatches workers.*

---

## What It Does

```
OpenPatala (254 works, live API)
  → nyah reads state (openpatala_bridge.py)
  → identifies gaps (gap_analyzer.py)
  → generates tasks (task_generator.py)
  → prioritizes (objective function)
  → dispatches (scheduler.py)
  → executes via mimo-v2.5 (agent_executor.py)
  → logs results (event_log + provenance + digest)
```

## Quick Start

```bash
cd /root/nyah
python3 check.py --status             # gate
python3 agent/run.py --step report    # full report
python3 agent/run.py --step gaps      # gap analysis
python3 agent/run.py --step scan      # register tasks
python3 agent/run.py --step dispatch  # dispatch to workers
```

## What's Built (verified, 56/56 tests pass)

### Core Coordination
- `gap_analyzer.py` — priority-score gaps from OpenPatala state
- `task_generator.py` — deterministic tasks from completeness
- `kanban_board.py` — state machine (BACKLOG→READY→IN_PROGRESS→DONE)
- `scheduler.py` — agent-aware dispatch (max 8 concurrent)
- `pipeline_runner.py` — autonomous cycle (scan→dispatch→execute→log)

### Execution
- `api_client.py` — direct mimo-v2.5 API (no hermes overhead)
- `agent_executor.py` — execute tasks + content-address results
- `agent_pool.py` — spawn/heartbeat/kill/track agents
- `failure_handler.py` — classify errors, retry/escalate

### newbuild1.md Architecture
- `entity_id.py` — opaque UUIDv7 IDs
- `event_log.py` — append-only event log
- `digest.py` — sha256/sha512/canonical JSON
- `schema_registry.py` — immutable schemas
- `provenance.py` — nanopublication triples
- `ledger.py` — Merkle checkpoints
- `relation_vocab.py` — 10 versioned typed relations
- `schema_migrations.py` — UPCAST/DOWNCAST registry

### Infrastructure
- `rights_policy.py` — per-source rights (5 providers)
- `crawl_policy.py` — rate limits per provider
- `source_lineage.py` — independent vs copied sources
- `discovery_scoring.py` — provider ranking
- `resolver.py` — staged R0-R3 identity resolution
- `work_completeness.py` — gap map from API
- `change_feed.py` — cursor-based incremental updates
- `mcp_server.py` — 6 tools for other agents

### OpenPatala Integration
- `openpatala_bridge.py` — reads from live API (254 works)
- `openpatala_executor.py` — calls OpenPatala pipeline steps

## Data Files

- `data/newbuild_checkpoints.json` — 80 checkpoints from newbuild docs (validated)
- `data/newbuild_numbered_items.json` — 128 numbered items (binary done/not_done)
- `data/comparative-audit.md` — openpatalaproject vs openpatalanew comparison
- `data/vision-patala1.jsonl` — Pāṭala 1 checkpoint DAG

## Docs

- `VISION.md` — project vision
- `AGENTS.md` — governing rules
- `HANDSOVER-2026-08-17-nyah.md` — session build notes
- `data/comparative-audit.md` — system comparison report

## Gate

```bash
python3 check.py --status   # PASS = all docs registered, data valid
```

## Rule

> **Timestamped, logged, content-addressed, registered.**
