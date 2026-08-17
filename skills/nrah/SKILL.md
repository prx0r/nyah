---
name: nrah
description: NRAH task coordinator — scan gaps, generate tasks, dispatch workers
version: "0.1.0"
---

# NRAH Skill — Autonomous Task Coordination

You are running as the NRAH (nyah) task coordinator. Your job is to read OpenPatala's completeness
state, identify gaps, generate tasks, prioritize them by objective function, and dispatch workers.

## Commands

### Scan for new tasks
```bash
cd /root/nyah && python3 agent/run.py --step scan
```
Reads OpenPatala state and generates deterministic TaskCandidates.

### Analyze gaps
```bash
cd /root/nyah && python3 agent/run.py --step gaps
```
Computes priority scores for each gap using the objective formula.

### Dispatch next batch
```bash
cd /root/nyah && python3 agent/run.py --step dispatch
```
Assigns highest-priority tasks to available workers.

### Full report
```bash
cd /root/nyah && python3 agent/run.py --step report
```
Shows task counts, gap analysis, and gate status.

### Worker pool status
```bash
cd /root/nyah && python3 agent/run.py --step pool
```

### Discovery modes
```bash
cd /root/nyah && python3 agent/run.py --step discovery
```
Runs all 5 discovery modes (adapter sweep, protocol, graph, gap-driven, frontier).

### Autonomous cycle
```bash
cd /root/nyah && python3 agent/run.py --step autonomous --max-steps 100
```
Works the checkpoint DAG until done or budget hit.

## Rules

1. **Tools don't become truth.** Every task has a deterministic trigger and gate.
2. **If it isn't in the trace, it didn't happen.** All steps go through run.py.
3. **Check RAM before heavy jobs.** `free -h | head -2 && uptime`
4. **Background long jobs.** `setsid nohup ... &` — never block the shell.
5. **Never pkill.** Find exact PID, `kill <PID>`.

## Priority Formula

```
Priority = GapValue × ExpectedYield × SourceAuthority × RightsUsability × DownstreamReach / Cost
```

## Task Types

| Type | When | Worker |
|---|---|---|
| FIND_SOURCE | source=NONE | discovery |
| FIND_ETEXT | catalog-only | discovery |
| RESOLVE_IDENTITY | identity=CONTESTED | resolver |
| RESOLVE_RIGHTS | rights=UNKNOWN | resolver |
| FETCH_RESOURCE | source known | fetcher |
| NORMALIZE_ETEXT | raw text acquired | normalizer |
| SEARCH_TRANSLATION | etext, no translation | searcher |
| TRANSLATE | source-ready, no translation | translator |
| ANCHOR_TRANSLATION | translation exists, not aligned | aligner |
| OCR_RESOURCE | scan-only | fetcher |
