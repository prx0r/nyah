# RECIPES — every command, one autonomous system

*2026-08-16 · The complete command set for agentic-infra, organized as recipes for each goal. Everything
an agent runs to operate the autonomous system. Each recipe is a copy-paste command + its expected result.*

**Python:** `/root/patalacheckpoints/.venv-atlas/bin/python` (or `python3` — this scaffolding is stdlib).
Run from `<your-project>` (the project that adopted the scaffolding).

---

## R1 — Set it and forget it (the vision → autonomous completion)
```bash
# write your vision (goal → granular checkpoints with gates)
cat > vision.jsonl << 'EOF'
{"name":"setup","effect":"prep the box","gate":"true","value":0.3,"cost":0.1}
{"name":"ingest","effect":"ingest the corpus","gate":"test -f data/corpus.json","after":["setup"],"value":0.9,"cost":0.6}
{"name":"gate","effect":"all gates pass","gate":"python3 check.py --status","after":["ingest"],"value":0.5,"cost":0.2}
EOF
# your vision → the DAG
python3 pipeline/checkpoint.py --decompose vision.jsonl
# see what it planned
python3 pipeline/checkpoint.py --status
# set it and forget it
python3 agent/run.py --step autonomous --max-steps 100
```

## R2 — Orient (what's here, what ran)
```bash
python3 agent/run.py --step report        # project summary (docs, runs, gate)
python3 agent/run.py --step trace --recent 20   # what ran recently
python3 agent/run.py --step trace --search <q>  # search the trace
python3 agent/run.py --step checkpoints   # the DAG status + next
```

## R3 — Add a domain capability (extend the system)
1. Add a `step_<name>()` to `agent/run.py` (logs via `_log`, content-addresses via run_recorder).
2. Add it to the `STEPS` dict.
3. Register in `MANIFEST.json` (id + owner + validator).
4. Add a line to the skill / README command table.
5. `python3 check.py --status` → PASS.

## R4 — Verify + audit (before claiming anything)
```bash
python3 agent/run.py --step verify              # the registry audit (every run has a valid signature)
python3 agent/audit.py --list                   # the crypto-committed runs
python3 agent/audit.py --bench <name> --record  # freeze a golden baseline
python3 agent/audit.py --bench <name>           # recompute; fail on mismatch
```

## R5 — The objective (pick the most valuable next)
```bash
python3 pipeline/objective.py --demo            # the objective demo
python3 agent/run.py --step objective           # demo + the objective-ordered next
python3 pipeline/checkpoint.py --next           # the next checkpoint (by value÷cost)
```

## R6 — Box safety
```bash
python3 agent/ramwatch.py          # SAFE (available RAM + load) or a warning
```

## R7 — Subagents / parallel work (Hermes swarm)
```bash
hermes kanban swarm "<checkpoint effect>" \
  --worker P1:item-1:skill1 --worker P2:item-2:skill2 \
  --verifier <reviewer> --synthesizer <writer>
```
The swarm's outcome then faces the checkpoint's deterministic gate.

## R8 — The daily watchdog (unattended)
```bash
hermes cron create "0 4 * * *" --name "<project>-watchdog" --no-agent \
  --script <project>-watchdog.sh --workdir <your-project>
```
The watchdog runs `--step autonomous` (or a bounded cycle) daily; a gate failure posts a summary.

## R9 — Handover (so a fresh agent picks up)
Write `HANDSOVER-YYYY-MM-DD-*.md` per `HANDSOVER-TEMPLATE.md`: the DAG status, what's done, the frontier,
the gate. Keep one current, old ones as history.

## R10 — The gate (always before "done")
```bash
python3 check.py --status          # docs registered + refs resolve
python3 agent/test_objective.py    # the objective kernel (7 assertions)
python3 agent/ramwatch.py          # box budget
```

---

## The recipe map

| You want to… | Use |
|---|---|
| run the whole vision autonomously | **R1** |
| orient / see what ran | **R2** |
| add a capability | **R3** |
| prove a result is real | **R4** |
| choose the best next step | **R5** |
| check the box budget | **R6** |
| parallelize with subagents | **R7** |
| automate it on a schedule | **R8** |
| hand over cleanly | **R9** |
| confirm it's consistent | **R10** |
