# AGENTS.md — nyah (NRAH task coordinator)

*2026-08-17 · Governing file for any agent working in nyah. Read this FIRST, then VISION.md, then
CODING-AGENT.md, then the root AGENTS.md for box rules. Nyah is the autonomous task coordinator for
OpenPatala: it reads completeness state, generates tasks, prioritizes by objective function, and
dispatches workers.*

---

## 0. THE ONE RULE

> **Nothing is "real" because a task exists. It is real only when a worker executes it, a deterministic
> gate verifies the state changed, and the result is logged in the trace.** A task that was dispatched
> but never verified is theater.

## 1. THE DETERMINISTIC ANTI-MESS STANDARD

### 1.1 Every build note is TIMESTAMPED
- Filename or header: `HANDSOVER-YYYY-MM-DD.md` or `*YYYY-MM-DD*`.
- No undated notes.

### 1.2 Every run is TRACKED
- Every step goes through `agent/run.py --step X` → logs to `data/runs/agent-steps.jsonl`.
- Query: `python3 agent/trace.py --recent`.
- **If it isn't in the trace, it didn't happen.**

### 1.3 Every NUMBER is content-addressed
- Headline numbers require a content-addressed run record.
- `agent/audit.py` enforces by recomputing.

### 1.4 Every doc is REGISTERED
- `MANIFEST.json` entry required for every doc/script.
- `python3 check.py --status` must PASS.

### 1.5 One concern = one doc
- Reference, don't copy.

## 2. THE WORKFLOW

```bash
# 1. gate first
python3 check.py --status

# 2. run a step
python3 agent/run.py --step gaps         # analyze OpenPatala gaps
python3 agent/run.py --step scan         # scan for new tasks
python3 agent/run.py --step dispatch     # dispatch highest-priority task
python3 agent/run.py --step report       # project summary

# 3. verify
python3 agent/trace.py --recent

# 4. gate again
python3 check.py --status
```

## 3. THE BOX RULES (non-negotiable)

- **Never `sleep` to wait** — background long jobs, note PID, do real work.
- **Never `pkill`** — find exact PID, `kill <PID>`.
- **RAM is scarcest** (4-core / 8GB / no swap / 2 agents) — check `free -h` before heavy jobs.
- **One heavy job at a time.**
- **If available < 400MiB while running, KILL the job by PID.**
- **The crypto layer proves integrity, never quality.**
- **Reuse, don't rebuild.**

## 4. THE STANDARD IN ONE SENTENCE

> **Timestamped, logged, content-addressed, registered.** Gap analysis is deterministic, tasks are
> content-addressed, dispatch is objective-ordered, and `check.py` + `trace.py` enforce it all — so
> nyah can't get messy even if an agent forgets.
