# VISION-SYSTEMS — composing agentic-infra into a cohesive organism of systems

*2026-08-16 · The modularity vision: each agentic-infra instance is a SYSTEM with a role + an explicit
interface. Compose 5+ systems into a **cohesive organism** that runs as one coordinated whole — each
system an agentic subsystem, handing verified artifacts to the next. This is the "5 systems, different
roles, working as one" architecture.*

---

## 1. THE CONCEPT (one paragraph)

Each agentic-infra instance is a **System** with:
- a **role** (what it does),
- **produces** (the artifact types it outputs),
- **consumes** (the artifact types it needs as input),
- a **gate** (the deterministic "is it real" check),
- **depends_on** (which systems must run first).

Multiple systems compose into an **organism** — a DAG where each system consumes the verified artifacts of
its dependencies and produces the inputs for its consumers. A coordinator validates the handoffs resolve
and the graph is acyclic, so the whole runs as one system.

## 2. THE SYSTEM CONTRACT (`pipeline/system.py`)

```python
# register one system
python3 pipeline/system.py --register --name translate \
  --role "translate verses" --produces translations --consumes verses \
  --gate "true" --depends ingest

# compose + verify an organism
python3 pipeline/system.py --compose organism.json
# ✓ ORGANISM VALID: N systems, acyclic, handoffs resolve. Order: ingest → translate → serve
```

The compose check enforces:
1. every `depends_on` names a real system,
2. every consumed artifact is produced by a dependency (except the root system, which takes external input),
3. no cycles (topological order exists).

## 3. A CONCRETE ORGANISM — the Sanskrit corpus, 5 systems

```
sources (external: archive.org/DLI/scans)
  → [ingest]     find+normalize sources   → verses
  → [ocr]        OCR the Devanagari scans → devanagari_text
  → [translate]  translate the verses     → translations
  → [verify]     gate + audit the output  → verified
  → [serve]      serve via the API        → api
```
```json
{ "schema": "agentic-infra.systems.v1", "name": "sanskrit-corpus",
  "systems": {
    "ingest":    {"name":"ingest","role":"find+normalize sources","produces":["verses"],"consumes":["sources"],"gate":"test -f data/corpus.json"},
    "ocr":       {"name":"ocr","role":"OCR Devanagari scans","produces":["devanagari_text"],"consumes":["sources"],"gate":"true","depends_on":["ingest"]},
    "translate": {"name":"translate","role":"translate verses","produces":["translations"],"consumes":["verses"],"gate":"true","depends_on":["ingest","ocr"]},
    "verify":    {"name":"verify","role":"gate+audit","produces":["verified"],"consumes":["translations"],"gate":"python3 agent/verify.py --registry","depends_on":["translate"]},
    "serve":     {"name":"serve","role":"serve via API","produces":["api"],"consumes":["verified"],"gate":"true","depends_on":["verify"]}
  } }
```

## 4. THE INSANE RECIPES (what you can do with composed systems)

### Recipe S1 — The Research Lab (5 systems)
```
discover → experiment → evaluate → publish → teach
```
Each is an agentic-infra instance: the experiment system proposes hypotheses (objective), the evaluate
system gates them (Kendall's tau vs gold), the publish system emits number-injected papers.

### Recipe S2 — The Content Factory (6 systems)
```
ingest-sources → summarize → structure(graph) → verify-citations → render(site) → serve
```
Sources → summarized/structured → citation-verified → rendered → served. The verify-citations system
enforces "only cite real edges" (the darshana-graph anti-hallucination).

### Recipe S3 — The Data Engine (5 systems)
```
discover → fetch(R2) → normalize → label → queue
```
Exactly our openpatala ingestor, as a composed organism.

### Recipe S4 — The Self-Improving Agent (4 systems)
```
learn → improve(skill) → verify(no-regression) → re-learn
```
The loop: learn from runs → improve the skill → verify no regression → re-learn. The verify system's gate
is "tests still pass + no regression," so self-improvement can't silently break things.

### Recipe S5 — The Multi-Domain Organism (N systems, shared spine)
Run N domain systems (Sanskrit, Western-Philosophy, Science) each producing `verified` artifacts into a
shared `verify` + `serve` spine. Each domain is a swappable module; the spine is the same.

## 5. HOW TO COMPOSE ONE (the 5 steps)

1. **Each system = one agentic-infra instance.** Copy the scaffolding per system, give it a role + its
   kernels + its own checkpoint DAG.
2. **Define the interface.** In each system's `pipeline/system.py`, declare `produces` + `consumes` (the
   artifact types).
3. **Write the organism spec.** One `organism.json` listing all systems + their `depends_on`.
4. **Validate it.** `python3 pipeline/system.py --compose organism.json` → the handoffs resolve + acyclic.
5. **Run it.** Each system runs its own `--step autonomous`; the coordinator ensures dependencies run first
   (the topological order from compose).

## 6. THE MODULARITY RULES

1. **Each system owns its role + its gate.** No system "trusts" another's output — it consumes artifacts
   and runs its own gate.
2. **Artifacts are the contract.** A system's `produces`/`consumes` are the handoff interface; they must
   resolve (the compose check).
3. **A system is a swappable module.** Replace a domain system without touching the spine — as long as it
   produces/consumes the same artifacts, the organism still validates.
4. **The whole is gated.** The organism is valid only when every handoff resolves + the graph is acyclic.

## 7. THE ONE-SENTENCE VISION

> **agentic-infra becomes a composable operating system: any number of agentic-infra instances (each a
> system with a role + a verified-artifact interface) compose into a cohesive organism via a validated
> DAG — each system working autonomously, handing verified artifacts to the next, so a whole pipeline
> (research lab, content factory, data engine, self-improving agent, multi-domain corpus) runs as one
> coordinated whole.**

---

## 8. THE FUTURE DEV ROADMAP (grounded in the cloned agentic infra)

Each step adopts a mechanism from a cloned repo — reuse, don't rebuild. Steps are in dependency order.

### F1 — Adversarial review (from `adversarial-review`)
Adopt the multi-agent adversarial debate as a **verifier for a checkpoint's gate** (not just a
deterministic command): two independent profiles review a checkpoint's output, critique each other, and
the synthesis becomes an additional review-layer gate before DONE. **Value:** catches what a single
deterministic gate can't (judgment errors, edge cases). **Box:** RAM-light (prompts), runs on the GPU box.

### F2 — Self-organization / topology (from `EverOS`)
Make the organism **self-organizing**: a system that observes the others' throughput/failure rates and
**re-weights the objective** (value/cost) so the bottleneck system gets priority. The objective function
already supports dynamic weights — wire them to live failure rates. **Value:** the organism routes effort
to where it's stuck, not where it's easy.

### F3 — Agent memory graph (from `graphiti` / `MemOS`)
Replace the linear `agent/memory.py` with a **temporal knowledge-graph memory** (graphiti): systems
remember decisions + their outcomes as graph edges, so the objective's `axis_pass_rate` uses real
historical success, and a system doesn't repeat a failed approach. **Value:** the organism learns.

### F4 — Open-ended self-improvement (from `agent-evolution` / DGM / `self-improving-agent`)
The Darwin-Godel loop: each system proposes a **minimal improvement to its own skill/kernel** (a diff),
the verify gate checks **no regression** (tests still pass + a fixed-gold score), and only no-regression
improvements are kept. **Value:** the scaffolding improves itself without breaking. This is the strongest
autonomous primitive.

### F5 — Ensemble verifier (from `agent-review-panel` / `cmu-paper-reviewer`)
A checkpoint whose gate is a "judgment" (not a shell command) uses **multiple independent reviewers** whose
votes must cross a threshold to mark DONE — anti-circularity at the system level.

### F6 — Cross-system hypothesis + experiment (from `EvoScientist`)
A system that proposes experiments across the whole organism (not just its own domain): "if I change
system X's gate, does the whole pipeline score better on gold?" — a metric-grounded, A/B-tested
improvement, logged + gated like every step.

### F7 — Cryptographic compute-integrity (from `run_recorder` + the ezkl/risc0 research)
Optional: wrap a checkpoint's gate in an **ezkl / RISC Zero** ZK receipt so a consumer can cryptographically
verify "this gate computation ran" — integrity, never quality (the honest rule).

---

## 9. THE PHASE-ORDERED DEV PLAN

| Phase | Step(s) | Gate |
|---|---|---|
| P1 (this box) | F1 adversarial review as a review-layer gate | a fabricated review is caught |
| P2 (this box) | F2 self-organizing objective (live failure-rate weights) | the bottleneck system gets priority |
| P3 (GPU box) | F3 agent memory graph (graphiti) | a past failed approach isn't retried |
| P4 (GPU box) | F4 open-ended self-improvement (DGM loop) | a no-regression improvement is kept, a regression is rejected |
| P5 (GPU box) | F5–F7 ensemble verifier + cross-system experiments + crypto receipts | a gated, gold-scored, verified improvement ships |

**The rule for every step:** reuse the cloned mechanism, gate it deterministically (no-regression on fixed
gold), log + content-address it, and register it in the MANIFEST. If it isn't gated + logged, it isn't real.
