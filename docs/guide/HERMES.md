# HERMES INTEGRATION — how the autonomous system uses Hermes

*2026-08-16 · How agentic-infra's autonomous driver rides on Hermes: the subagents (kanban swarm), the
review gate (request-review), the MCP/API interface, cron (unattended), and the cryptography/provenance
(spine). This is the execution engine under the checkpoint DAG — the agent proposes, Hermes executes, the
deterministic gate decides.*

---

## 1. THE DIVISION (Hermes executes, the DAG decides)

```
VISION → decompose → checkpoint DAG
   ↓
Hermes (the execution engine) works the next checkpoint:
   - the deterministic GATE decides "done" (never Hermes)
   - Hermes executes the work, logs via run_recorder (content-addressed)
   - a FAILED gate → back to the human (or a subagent swarm re-plans)
   ↓
ALL DONE → handover
```

**The rule:** Hermes (the model) proposes and executes; the checkpoint gate + run_recorder (deterministic)
dispose. This is the anti-hallucination spine — "the agent proposes, the gate disposes."

## 2. SUBAGENTS — the kanban swarm (parallel workers → verifier → synthesizer)

For a checkpoint that needs parallel work or independent verification, use **hermes kanban swarm**:
```
hermes kanban swarm "achieve <checkpoint effect>" \
  --worker P1:work-item-1:skill1 --worker P2:work-item-2:skill2 \
  --verifier <reviewer-profile> --synthesizer <writer-profile>
```
- **workers** = parallel subagents, each claims a card
- **verifier** = an independent profile that checks the result (the anti-circularity: verifier ≠ worker)
- **synthesizer** = merges the verified outputs
- The swarm's outcome then faces the checkpoint's deterministic gate (never just the swarm's claim).

## 3. THE REVIEW GATE — `request-review` / `request-changes`

A checkpoint is NOT "done" because Hermes says so. Move the card to **review** and let a reviewer profile
(or the deterministic gate) accept/reject:
```
hermes kanban request-review <task> --summary "<the result>" --reviewer <profile>
hermes kanban request-changes <task>   # reject → back to the worker
hermes kanban complete <task>          # only after the gate passes
```
This is the "don't move on until it's real" machinery — the gate is external to Hermes.

## 4. THE MCP / API INTERFACE

The project exposes its kernels to Hermes via the MCP/API pattern (see `HERMES-MCP-API.md` in the worked
example, sanskritbenchy). Every agent-facing call:
| Call | What |
|---|---|
| `python3 agent/run.py --step X` | the orchestrator (logs + content-addresses every step) |
| `python3 pipeline/checkpoint.py --decompose vision.jsonl` | vision → granular checkpoints |
| `python3 agent/run.py --step autonomous` | the set-and-forget driver |
| `python3 agent/trace.py --all` | what ran (the trace) |
| `python3 agent/verify.py --registry` | the crypto-committed runs |

## 5. CRON — unattended autonomous re-validation

```
hermes cron create "0 4 * * *" --name "<project>-watchdog" --no-agent \
  --script <project>-watchdog.sh --workdir /root/<project>
```
The watchdog runs the autonomous driver (or a bounded cycle) daily; a gate failure posts a summary so a
human reviews — the "human-on-the-loop" model.

## 6. CRYPTOGRAPHY / PROVENANCE (the spine)

- **`run_recorder.py`** content-addresses every run: `run_signature = sha256(gold‖code‖config) → out_hash`,
  persisted with a **nanopublication** `{assertion, evidence, provenance}` + the **eigenius kind**
  (`VERIFIED ⊂ DERIVED ⊂ OBSERVED ⊂ DECLARED`).
- **`git_state()`** captures the commit + diff on every record (wandb-style code-saving).
- **`audit.py`** recomputes on fixed gold and **fails on mismatch** — the executable ONE RULE.
- **The honest rule:** the crypto proves *integrity* (this run → this output), never quality. Only the
  deterministic gate + gold prove quality.
- (Roadmap: `ezkl`/`risc0` ZK receipts for compute-integrity, per the cloned research — see
  `research/DEEP-DIVE-COMET-CRYPTO-VERIFICATION.md` in sanskritbenchy.)

## 7. THE FULL AUTONOMOUS LOOP (all the machinery together)

```
1. HUMAN: writes vision.jsonl (goal → granular checkpoints with gates)
2. --decompose → the DAG
3. Hermes: --step autonomous → works the next checkpoint (objective-ordered)
4. Hermes executes the work (kanban swarm for parallel subagents when needed)
5. The deterministic GATE runs → PASS (DONE, content-addressed) or FAIL (→ human/re-plan)
6. request-review for a human reviewer on scholarly/major checkpoints
7. ALL DONE → the vision is complete → handover
   └── cron watchdog re-validates on a schedule, catches drift
```

## 8. HOW TO ADOPT (instruct the new agent)

Read: this doc → `docs/guide/AUTONOMOUS.md` → `docs/recipes/` → `docs/reference/`. Then:
1. Verify `hermes` is available (`hermes --version`) + a board exists.
2. Copy the scaffolding, write `VISION.md` + a `vision.jsonl`, `--decompose`, `--step autonomous`.
3. Add your domain kernels to `agent/run.py` (a `step_<name>` each) + register in MANIFEST.
4. Use `kanban swarm` for parallel/verifier work, `request-review` for the gate.
5. Wire the cron watchdog. Run the gate. Write a handover.
