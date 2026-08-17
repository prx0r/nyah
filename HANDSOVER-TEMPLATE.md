# HANDSOVER TEMPLATE — the canonical spec for every handover

*2026-08-16 · THE hardcoded standard: what a handover MUST contain so a fresh agent gets complete context
in one read. Every handover file (`HANDSOVER-YYYY-MM-DD-<topic>.md`) follows this exact template — no
sections dropped, no invented structure. A handover is the complete orientation for a fresh agent, not a
progress log.*

---

## THE RULES (hardcoded)

1. **One current handover** — `HANDSOVER-YYYY-MM-DD-<topic>.md` with the HIGHEST date is the current one.
   Older ones are kept, timestamped, as history.
2. **Every handover uses THIS template** — fill every numbered section. If a section is N/A, write "N/A"
   with one line why — don't omit it.
3. **A handover is timestamped** (`*YYYY-MM-DD*` in the header) and registered in `MANIFEST.json`.
4. **A handover tells the fresh agent HOW to continue** — it resolves to the live checkpoint DAG, the
   current dev plans, and the gates. It never just lists what was done.

---

# [HANDSOVER-YYYY-MM-DD-TOPIC] — <one-line what this handover covers>

*YYYY-MM-DD · <who/what/when> · Complete orientation for the next agent. Read this top-to-bottom, then
the files it points to. Run the gates before building anything.*

## 0. THE ONE-LINE STATE (the current truth in one sentence)
> <what is real and working right now — not aspiration, not history>

## 1. THE PROJECT (what this is + why)
- **What:** <the project, 2-3 sentences>
- **The vision:** <the north-star goal> (full: `VISION.md`)
- **The moat:** <what makes it defensible>

## 2. THE READ ORDER (60-second orientation — what to read first)
| # | File | Why |
|---|---|---|
| 1 | `AGENTS.md` | the ONE RULE + the anti-mess standard |
| 2 | `CODING-AGENT.md` | the strict operational discipline (how to work) |
| 3 | `VISION.md` | the goal + the checkpointed roadmap |
| 4 | `HANDSOVER-<current>.md` | THIS file — the complete state |
| 5 | `DEV-PLAN-NO-GPU.md` / `DEV-PLAN-WITH-GPU.md` | the current plans |
| 6 | `HOW-IT-WORKS.md` / `INTEGRATION.md` | the mechanisms + the integration |
| 7 | `RECIPES.md` | every command + how to expand |
| 8 | `CANONICAL-DATA-SPEC.md` | the schemas (every data contract) |

## 3. THE CURRENT STATE — WHAT'S DONE (verified, content-addressed)
| Capability | Status | Where |
|---|---|---|
| <capability> | ✅ / ⬜ | <module/doc> |
... (every built thing, with its verified status)

## 4. THE LIVE CHECKPOINT DAG (the machine truth of what's done/next)
```
$ python3 agent/run.py --step checkpoints
[DONE] <gate>  ...
[OPEN] <next-gate>  ← the NEXT thing to do
```
> **The next gate is: <gate>.** To start: <exact command>.

## 5. THE DEV PLANS (which to follow, when)
- **CPU box (now):** `DEV-PLAN-NO-GPU.md` — the N1..N6 items (what to keep building without torch).
- **GPU box (when available):** `DEV-PLAN-WITH-GPU.md` — the G1..G8 full ML path.
- **The immediate next action:** <one concrete step>.

## 6. THE VERIFIED RESULTS (real numbers, content-addressed)
| Result | Value | Evidence |
|---|---|---|
| <result> | <number> | <run record / log> |

## 7. THE DATA (what exists, what's source-of-truth)
| Dataset | Size | Role |
|---|---|---|
| <dataset> | <size> | <role> |
... (everything the lab uses; note what's regenerable vs source)

## 8. THE GATES (must be green — run these)
```bash
python3 check.py --status                 # PASS = docs registered + data validates
PYTHONPATH=. python3 agent/validate_data.py   # the strict data gate
python3 agent/ramwatch.py                 # SAFE (box budget)
```

## 9. THE HONEST GAPS / BLOCKERS
| Gap | Blocked on | How to proceed |
|---|---|---|
| <gap> | <GPU / human gold / code> | <next step> |

## 10. THE INFRA I NEED (if the vision is not yet complete)
From `INFRA-REQUIREMENTS.md`: <GPU spec + human gold + access>.

## 11. THE RECENT CHANGES (this handover's delta — what's new since the last handover)
- <what changed this session>
- <git commits made>

## 12. THE GIT STATE
- Remote: <repo> · branch: <branch> · HEAD: <commit>
- Clean / dirty: <N uncommitted files — what they are>
- **Commit rule:** timestamped handover + dev plans + code together; run gates first.

## 13. HOW TO VERIFY THE PROJECT IS HEALTHY (the fresh-agent smoke test)
```bash
cd /root/sanskritbenchy
python3 agent/ramwatch.py                  # 1. box ok?
python3 check.py --status                  # 2. gate ok?
python3 agent/run.py --step checkpoints    # 3. what's next?
python3 agent/trace.py --recent            # 4. see the recent runs
python3 agent/verify.py --registry         # 5. every result content-addressed?
```
If all five pass, the project is healthy and you can start on the next gate.

## 14. THE SIGN-OFF (the last line of every handover)
> **<the single most important thing the next agent must know>**

---

*This is the template. Fill every section. The next agent reads this + runs §13, then starts on the next
checkpoint gate (§4) using the current dev plan (§5). If a handover doesn't follow this template, it isn't
a handover.*
