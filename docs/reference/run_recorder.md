# REFERENCE — the run recorder + provenance (`pipeline/run_recorder.py`)

*The content-addressed RUN RECORDER — bulletproof provenance. Every run becomes a reproducible,
anti-fabrication record, and every headline number ships as a nanopublication with an epistemic kind.
This is the crypto-proof layer: it proves INTEGRITY (this exact run → this exact output), never quality.*

---

## The content-addressing (the anti-fabrication key)

### `sha256(obj) -> str`
SHA-256 of any JSON-serializable object (canonical, sort_keys). The reproducibility key.

### `run_signature(gold, config) -> str`
`sha256({gold: gold_hash(gold), code: code_sha(), config: config_sha(config)})`. **Same input + code +
config ⇒ same signature ⇒ same reproducible run.**

### `gold_hash(gold) -> str`
Hash the fixed input (source+gold), not the file path.

### `code_sha() -> str`
Hash every pipeline/agent .py file that affects the result (frozen code).

### `config_sha(config) -> str`
Hash the resolved config (all overrides applied).

### `git_state() -> dict`
Auto-capture `{commit, diff}` (wandb-style code-saving trio).

### `file_sha(path) -> str`
Hash a file's content.

## The epistemic kind

### `epistemic_kind(verified=False, derived=True, observed=True) -> str`
The "how-known" label: `VERIFIED ⊂ DERIVED ⊂ OBSERVED ⊂ DECLARED`. A result is only VERIFIED when a
deterministic/proven check confirms it (not just observed or derived).

## The recorder

### `class RunRecorder(runs_dir)`
Persists a content-addressed run record per run.

### `RunRecorder.record(*, step, gold, config, metrics, raw, assertion, evidence_code) -> dict`
Write one run record:
```json
{ "step": "…", "run_signature": "…", "out_hash": "…", "gold_hash": "…",
  "code_sha": "…", "config_sha": "…", "config": {}, "metrics": {},
  "git": {"commit":"","diff":""}, "ts": "…",
  "nanopublication": { "assertion": "…", "evidence": {"code": "ECO:…","artifact": "run:…"},
                       "provenance": {"run_signature": "…","out_hash": "…","generated_by": "…","ts": "…"} } }
```
Stored as `data/corpus/runs/<signature>.json`.

### `RunRecorder.get(signature)` / `.all()`
Fetch one / all committed run records.

## The honest rule
- The **crypto proves integrity** (this run → this output), never quality.
- Only the **deterministic gate + gold** prove quality.
- A number with no content-addressed run record is **theater** — `agent/audit.py` enforces this by
  recomputing on fixed gold and failing on mismatch.
