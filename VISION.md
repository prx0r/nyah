# NYAH (NRAH) — the autonomous task coordinator

*2026-08-17 · The high-level manager that sits above OpenPatala. Reads completeness state, generates
deterministic task candidates, prioritizes by objective function, and dispatches workers. Built on
agentic-infra's checkpoint DAG + objective scaffolding. Another agent builds OpenPatala; nyah coordinates
what work happens next.*

---

## 1. THE ONE SENTENCE

> **Nyah continuously notices what OpenPatala does not know and commissions the cheapest reliable action
> to fill that hole.**

## 2. WHAT NYAH IS (and isn't)

- **IS:** the task coordination layer — gap analysis, task generation, prioritization, worker dispatch.
- **ISN'T:** the data store (OpenPatala owns state), the translation engine (Factory), or the evaluation
  system (Eval). Nyah decides WHAT to do; workers do it.

## 3. THE THREE RESPONSIBILITIES

1. **GAP ANALYSIS** — read OpenPatala's completeness state, identify what's missing/uncertain/conflicted.
2. **TASK GENERATION** — deterministically emit TaskCandidates from gaps (no LLM needed for obvious
   state-machine transitions: `if source == NONE → emit FIND_SOURCE`).
3. **SCHEDULING** — use the objective function to prioritize tasks by `GapValue × Yield × Authority /
   Cost`, dispatch to the right worker type.

## 4. THE TASK TYPES (from newbuildmainspec §42-43)

| Task Type | When Generated | Worker |
|---|---|---|
| FIND_SOURCE | work.source == NONE | discovery agent |
| FIND_ETEXT | source-ready but no clean text | crawler/adapter |
| FIND_EDITION | translation references unknown edition | resolver |
| RESOLVE_IDENTITY | identity == CONTESTED | resolver agent |
| RESOLVE_RIGHTS | rights == UNKNOWN | policy checker |
| FETCH_RESOURCE | source known, not yet fetched | fetcher |
| NORMALIZE_ETEXT | raw text acquired | normalizer |
| SEARCH_TRANSLATION | clean etext, no known translation | search agent |
| TRANSLATE | source-ready + no translation | Factory pipeline |
| ANCHOR_TRANSLATION | translation exists, not aligned | aligner |
| OCR_RESOURCE | scan-only, no text | OCR pipeline |

## 5. THE FIVE DISCOVERY MODES (from newbuildmainspec §32-36)

1. **Mode A — Known Adapter Sweeps**: PANDiT, GRETIL, FoJin, Archive.org, OpenAlex, etc.
2. **Mode B — Protocol Discovery**: homepage → robots → sitemap → feeds → API → IIIF → OAI-PMH
3. **Mode C — Graph Expansion**: every observed item yields leads (publisher, institution, author, etc.)
4. **Mode D — Gap-Driven Discovery**: system generates DiscoveryObjectives from missing state
5. **Mode E — Frontier Source Discovery**: agents find genuinely unknown sources

## 6. THE OBJECTIVE FUNCTION

```
Priority = GapValue × ExpectedYield × SourceAuthority × RightsUsability × DownstreamReach / Cost
```

Not frozen — the formula is intuition. The objective kernel (from agentic-infra) scores candidates on
weighted axes and picks the argmax.

## 7. THE GATE

```bash
python3 check.py --status          # PASS = tasks registered + state validates
python3 agent/ramwatch.py          # SAFE (box budget)
python3 agent/run.py --step gaps   # current gap analysis
```

## 8. THE RULE

> **Tools don't become truth. Their outputs become observations.** Nyah never acts on an LLM's opinion
> alone. Every task has a deterministic trigger (completeness state change) and a deterministic gate
> (verification that the state actually changed).

## 9. INTEGRATION WITH OPENPATALA

Nyah reads OpenPatala's state via:
- `/v1/frontier/translations` — works needing translation
- `/v1/frontier/sources` — works needing source acquisition
- `/v1/works/{id}/completeness` — per-work completeness
- `/v1/assertions?state=CONTESTED` — conflicting assertions

Nyah writes tasks to `data/tasks/` as JSONL. Workers read tasks, execute, write results.

## 10. THE BOX RULES (from root AGENTS.md — non-negotiable)

- Never `sleep` to wait — background + move on.
- Never `pkill` — kill by exact PID.
- RAM budget: check `free -h` before every heavy job.
- One heavy job at a time.
- If it isn't in the trace, it didn't happen.
