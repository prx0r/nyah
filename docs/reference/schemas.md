# REFERENCE — the schema contracts (`pipeline/schemas.py`)

*The canonical data spec: every data file the project writes has an EXACT field contract, enforced by a
strict validator. A malformed record, missing field, or wrong type is caught deterministically.*

---

## The validators

| Function | Checks |
|---|---|
| `_str(v)` | is a string |
| `_int(v)` | is an int (not bool) |
| `_float(v)` | is an int/float (not bool) |
| `_bool(v)` | is a bool |
| `_list(v)` / `_dict(v)` | is a list / dict |
| `_sha256(v)` | a 64-hex sha256 string |
| `_iso_ts(v)` | an ISO timestamp string |

## The core

### `validate(record, schema) -> bool`
Check a record against a schema: every required field present with the right type, no unknown fields
(strict), and content checks where needed. Returns True if it conforms.

## A schema is a dict
```python
SCHEMA = {
  "object_id": _str, "verse_idx": _int, "layer": _str,
  "source_sha256": _sha256, "sanskrit": _str, "status": _str,
}
```

## How it's used
- `agent/validate_data.py` runs the strict gate over the live data.
- Wired into `check.py --status` → a malformed record fails the gate.

## The rule
The schema is the contract — the spec is exact. No field may silently drift; `validate()` catches it
before it reaches consumers.
