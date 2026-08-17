---
name: <project>-agent
description: "Drive the <project> lab: run the orchestrator, verify results, audit, query the trace, check the box — all gate-green."
version: 1.0.0
date: YYYY-MM-DD
author: <owner>
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [Agent, Lab, Orchestration, Verification]
    related_skills: [research]
---

# <Project> Agent

You drive the lab at `<project>`. **The ONE RULE: nothing is real unless it is a logged, content-addressed
number on fixed gold, passed by a deterministic gate.**

## The command map

| Command | When to use it |
|---|---|
| `python3 agent/ramwatch.py` | BEFORE any heavy job — is the box SAFE? |
| `python3 check.py --status` | before + after ANY change — is the gate green? |
| `python3 agent/run.py --step checkpoints` | what's the next checkpoint to work? |
| `python3 agent/run.py --step <X>` | run a lab step (logs + content-addresses) |
| `python3 agent/verify.py --source X --candidate Y --gold Z` | prove a result is real |
| `python3 agent/trace.py --recent` | see the recent runs |

## The standard workflow

```bash
cd <project>
python3 agent/ramwatch.py                 # 1. box
python3 check.py --status                 # 2. gate
python3 agent/run.py --step checkpoints   # 3. what's next
# ... do the next checkpoint ...
python3 agent/trace.py --recent           # 4. logged?
python3 check.py --status                 # 5. gate still green
```

## The honest rules
1. Never claim a result without a logged number on fixed gold.
2. Never pkill — kill by exact PID.
3. Never fabricate a result — a failed step is logged as failed.
4. Check ramwatch before + during heavy jobs.
