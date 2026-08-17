# CODING-AGENT.md — the strict operational discipline for this lab

*2026-08-16 · The non-negotiable HOW of working on sanskritbenchy. Read this after `AGENTS.md`. This is
the discipline distilled from this session: how to run long jobs without timing out, how to keep working
while they run, the file conventions, the "review" protocol, and how to test properly (run logs +
monitor). Violating any rule here is a bug in your process.*

---

## 1. THE #1 RULE — NEVER TIMEOUT, ALWAYS KEEP WORKING

### 1.1 The problem
This box (8GB/4-core, shared with another agent) is SLOW. Model calls (hermes → deepseek-v4-flash) take
15–40s each, and a real experiment (re-render, tree-search, benchmark) makes MANY of them serially. If you
run a heavy job in the FOREGROUND, the shell times out (120s default) and you lose the thread.

### 1.2 The rule
**NEVER run a long job in the foreground.** Start it backgrounded with `setsid nohup`, write to a log,
note the PID, then DO OTHER REAL WORK while it runs. Check the log later — never `sleep` to wait.

```
GOOD:  setsid nohup python3 /tmp/sb-task.py > /tmp/sb-task.log 2>&1 &  echo "PID $!"
       # ...immediately do real work (read a doc, fix a schema, write code)...
       tail /tmp/sb-task.log     # check on it later
BAD:   python3 /tmp/sb-task.py    # foreground — the shell times out, you stall
BAD:   sleep 60; python3 ...      # idle waiting = wasted box time
```

### 1.3 The background pattern (memorize it)
```
# 1. write the task as a script that PRINTS progress + writes a result file at the end
cat > /tmp/sb-task.py << 'EOF'
import sys; sys.path.insert(0,'pipeline')
# ... the work, print() each step, write a result file at the end ...
EOF
# 2. run it backgrounded, log everything
setsid nohup python3 /tmp/sb-task.py > /tmp/sb-task.log 2>&1 &
echo "started PID $!"
# 3. note the PID — you OWN it; you may kill it by exact PID
# 4. do real work; poll the log by READING it (tail), not by sleeping
```

**Never `pkill`** — find the exact PID (`ps -eo pid,etime,cmd | grep <name>`) and `kill <PID>`.

---

## 2. THE BOX BUDGET — CHECK BEFORE + DURING EVERY HEAVY JOB

```
python3 agent/ramwatch.py     # SAFE / CAUTION / CRITICAL
free -h | head -2 && uptime   # the raw numbers
```
- **SAFE** (avail ≥1GiB, load <3): OK to start a heavy job.
- **CAUTION** (avail <1GiB OR load ≥3): do light work; don't start a RAM-heavy job.
- **CRITICAL** (avail <400MiB OR load ≥3.5): a new job can OOM-kill BOTH agents. STOP heavy work.
- Re-check `ramwatch.py` WHILE a job runs; if it drops to CRITICAL, `kill <PID>` the job and let the box
  recover.
- Run SMALL samples (n=2–3). Never run two heavy jobs at once.

---

## 3. FILE CONVENTIONS (strict)

### 3.0 THE CANONICAL PLACES (hardcoded — never guess where things live)

| Thing | Canonical location | Rule |
|---|---|---|
| **The up-to-date dev plan** | `DEV-PLAN-NO-GPU.md` (CPU box) · `DEV-PLAN-WITH-GPU.md` (GPU) | These are ALWAYS the current plan. If work advances, update THEM — never create a new plan file. |
| **The most up-to-date handover** | `HANDSOVER-YYYY-MM-DD-*.md` (highest date) | One CURRENT handover. The previous dated handovers are kept, timestamped, as history. |
| **The live checkpoint DAG** | `data/checkpoints.json` (via `agent/run.py --step checkpoints`) | The machine truth of what's done/next. Never hand-edit — use `pipeline/checkpoint.py`. |
| **The canonical schema spec** | `CANONICAL-DATA-SPEC.md` + `pipeline/schemas.py` | The source of truth for every data contract. |
| **The machine resolver** | `MANIFEST.json` | Every doc/script → id/owner/validator. |
| **The governing rules** | `AGENTS.md` (rules) · `CODING-AGENT.md` (how to work) | Read both. |

**The rule:** there is exactly ONE current dev plan, ONE current handover, ONE checkpoint DAG, ONE schema
spec. When something changes, UPDATE the canonical file — never leave a stale copy and start a new one.

### 3.0b THE FILE LIFECYCLE (new → current → stale → legacy)

```
NEW       you create it → timestamp + register in MANIFEST
CURRENT   it's the canonical source (one per concern) → keep it accurate
STALE     its claim no longer matches the code/data → FIX it, or mark it
LEGACY     superseded by a newer version → ARCHIVE, don't delete
```

**Stale files** — a doc that points at a non-existent file/feature, or a claim that contradicts the code:
- **FIX it** (update the doc to match reality), OR
- **Mark it** `> ⚠️ STALE — superseded by <newer> · 2026-08-16` at the top, and reference the replacement.
- Never leave a doc silently claiming something false.

**Legacy files** — a superseded version (e.g. a previous handover, an old plan):
- **Keep them**, timestamped, as history — do NOT delete (reference-traceability + the anti-mess rule).
- A superseded plan/handover gets a `> **SUPERSEDED** by <newer> · <date>` banner at the top.
- The current file is always the highest-date one.

**Orphaned files** — a script in the MANIFEST not wired into `agent/run.py`, or a file not registered:
- **Wire it or register it** — never leave it dangling (run the §4.2 registration audit).

### 3.1 Timestamps
- **Every build note / handover / new doc carries a date**: `HANDSOVER-YYYY-MM-DD.md` or `*YYYY-MM-DD*` in
  the first lines. An undated note is not a build record.
- Every new doc: timestamp + a clear `# TITLE — what it is` first line.
- Every script/module: a docstring stating what it does + input + output.
- **Handovers**: `HANDSOVER-YYYY-MM-DD-<topic>.md`. The most recent date = the current one. Old ones stay as
  timestamped history.
- **Dev plans**: exactly `DEV-PLAN-NO-GPU.md` and `DEV-PLAN-WITH-GPU.md` — update them, don't proliferate.

### 3.2 Naming
- **Kernels / python modules:** `snake_case.py` (in `pipeline/`).
- **Agent scripts:** `dash-case.py` or `snake_case.py` (in `agent/`).
- **Data files:** `snake_case.ext` (in `data/`).
- **Docs:** `TITLE-WITH-PURPOSE.md` (e.g. `CANONICAL-DATA-SPEC.md`, `DEV-PLAN-WITH-GPU.md`).

### 3.3 Registration (the anti-mess standard)
- Every new doc → add a `MANIFEST.json` entry (id + owner + validator) or `check.py` flags it.
- Every new script/kernel → add an `implementation` entry.
- If it writes data → add a schema in `pipeline/schemas.py` + wire it into `agent/validate_data.py`.
- If an agent should run it → add a `step_<name>` in `agent/run.py` + a line in
  `skills/sanskrit-benchy/SKILL.md`.

### 3.4 The gate after any change
```
python3 check.py --status          # MUST PASS (docs registered + data validates)
PYTHONPATH=. python3 agent/validate_data.py   # the strict data gate
```

---

## 4. THE "REVIEW" PROTOCOL (what to do when asked to "review")

When asked to "review" (docs, code, data, a stale artifact):

### 4.1 Review = AUDIT against reality, not admire
- **Check for STALE docs** — a doc that claims something that no longer matches the code/data. Grep for
  the thing the doc claims and verify it exists/works. A doc that points at a non-existent file/feature is
  stale — fix the doc or flag it.
- **Check for ORPHANED code** — a module in the MANIFEST not referenced anywhere, or a file that exists but
  isn't wired into `agent/run.py`. Either wire it or register it.
- **Check for UNREGISTERED docs/code** — run the registration audit.

### 4.2 The registration audit
```
python3 -c "
import json, glob
m = json.load(open('MANIFEST.json'))
reg = set(m['docs']) | set(m['implementation'])
un = [f for f in glob.glob('*.md')+glob.glob('research/*.md')+glob.glob('pipeline/*.py')+glob.glob('agent/*.py') if f not in reg and f != 'check.py']
print('unregistered:', un if un else 'NONE')"
```

### 4.3 The timestamp audit
```
for f in $(find . -name "*.md" -not -path "./data/*" -not -path "./hermes/*" | sort); do
  grep -qiE "2026-0[0-9]-[0-9]{2}" "$f" || echo "NO-TS: $f"; done
```

### 4.4 The review output
- **Report what's TRUE** (verified against real code/data, with counts).
- **Report what's STALE** (claims that don't match reality) — fix it, or mark it `> ⚠️ STALE` + reference
  the replacement. Never silently accept.
- **Report what's LEGACY** (superseded) — keep it, timestamped, with a `> **SUPERSEDED**` banner; the
  current file is the highest-date one. Never delete history.
- **Report what's MISSING** (unregistered, orphaned, untested) — wire/register it.
- **Confirm the canonical files are accurate**: the current dev plan (`DEV-PLAN-NO-GPU.md` /
  `DEV-PLAN-WITH-GPU.md`) and the current handover (highest-date `HANDSOVER-*.md`). If work has moved past
  them, UPDATE them.
- **Never** present a file's existence as proof it works — run the gate.

---

## 5. HOW TO TEST PROPERLY (run logs + monitor)

### 5.1 Run the gate + the strict data gate
```
python3 check.py --status                # manifest + refs + data
PYTHONPATH=. python3 agent/validate_data.py   # every data file vs its schema
```

### 5.2 Test a specific capability
- Run the relevant `agent/run.py --step X` — it logs to the trace automatically.
- Verify the result is content-addressed: `PYTHONPATH=. python3 agent/audit.py --list` (every run has a
  signature + nanopublication).
- Verify the trace: `python3 agent/trace.py --recent` / `--all`.

### 5.3 Monitor a running job (the proper way)
```
# 1. is it alive + how long?
ps -eo pid,etime,cmd | grep <job-name> | grep -v grep
# 2. is it making progress? (are model calls in flight?)
ps -eo pid,etime,cmd | grep "hermes -z" | grep -v grep | wc -l
# 3. read the log (NEVER sleep-wait)
tail /tmp/<job>.log
# 4. box health while it runs
python3 agent/ramwatch.py
```
- **If the log is empty but the process is alive + model calls are in flight → it's working; keep doing
  real work.**
- **If the process is gone but the result file wasn't written → it errored; read the full log.**
- **If ramwatch goes CRITICAL → kill by PID.**

### 5.4 Test against FIXED gold, not vibes
- A result is real only when it's a logged, content-addressed number on fixed gold, passed by a
  deterministic gate. Run `verify.py` / `audit.py` to enforce it. Never accept a model's own judgment.

---

## 6. THE ANTI-THEATRE DOCTRINE (the one that matters)

- **A green test on unchanged code is noise** — running tests is not work.
- **A file existing is not proof it works** — run the gate.
- **A number with no content-addressed run record is theater** — use `run_recorder`.
- **The scorer ≠ the generator** — the verifier (verify/audit/xCOMET/SaQE) is not the translator.
- **Never fabricate a result** — a failed step is logged as failed.

---

## 7. THE WORKFLOW CHECKLIST (every session)

```
1. python3 agent/ramwatch.py          # box safety
2. python3 check.py --status          # gate before
3. python3 agent/run.py --step checkpoints   # what's the next checkpoint?
4. Do the work:
   - write code → register in MANIFEST → add schema if data → wire into run.py + skill
   - or run a long job → setsid nohup ... & → note PID → do other real work → tail the log
5. python3 check.py --status          # gate after
6. PYTHONPATH=. python3 agent/validate_data.py   # data gate
7. python3 agent/trace.py --recent    # confirm it's logged
8. If asked to "review" → the §4 audit protocol
```

---

*This is the strict discipline. Memorize the three hard rules: (1) never run a long job in the foreground —
background + do real work + check the log; (2) never pkill — kill by exact PID; (3) never claim a result
without a logged, content-addressed number on fixed gold. Follow the checklist every session.*
