# COMPARATIVE AUDIT — openpatalaproject vs openpatalanew

*2026-08-17 · Full test suite, both systems running live.*

## 1. SYSTEM INVENTORY

| Component | openpatalaproject (8800) | openpatalanew (8801) |
|---|---|---|
| Works | 254 (JSON files) | 935 (Postgres) |
| Backend | `legacy` (JSON) | `postgres` |
| Pipeline files | 15 | 15 |
| Adapters | 1 (GRETIL) | 1 (GRETIL) |
| Schemas | 28 (v1+v2) | 22 (v2 only) |
| API endpoints | 15 | 25+ |
| Assertions | 0 linked | 77 in DB, 0 linked to works |
| External IDs | 0 | 38 in DB, 0 linked |
| Events | 0 | 933 |
| Translations | 0 | 0 |

## 2. API ENDPOINT COMPARISON

| Operation | openpatalaproject | openpatalanew | Winner |
|---|---|---|---|
| List works | ✓ (254, paginated) | ✓ (935, paginated) | new (more data) |
| Get work | ✓ (by slug ID) | ✓ (by UUID) | tie |
| Bundle | ✓ (flat record) | ✓ (full dossier structure) | new (richer) |
| Translations | ✓ (per-work) | ✓ (global endpoint) | old (more useful) |
| Traditions | ✓ (5 traditions) | ✗ (not implemented) | old |
| Search | ✓ (returns 0) | ✓ (returns 7) | new (slightly better) |
| Resolve | ✓ (returns ?) | ✓ (returns NONE) | tie (both empty) |
| Frontier | ✓ (50 items) | ✓ (3 items) | old (more data) |
| Verses | ✓ (endpoint exists) | ✓ (passages endpoint) | old (real data) |
| Download | ✓ (302 redirect) | ✓ (etexts/content) | old (proven) |
| People | ✗ | ✓ (endpoint exists) | new |
| Institutions | ✗ | ✓ (endpoint exists) | new |
| Editions | ✓ (filterable) | ✓ (endpoint exists) | tie |
| Witnesses | ✗ | ✓ (endpoint exists) | new |
| Changes | ✗ | ✓ (incremental) | new |
| Assertions | ✗ | ✓ (per-work) | new |

## 3. DATA QUALITY TEST

### openpatalaproject (8800)

```
Work: tantraloka
  title: ? (empty)
  translations: 0
  editions: 0
  traditions: 5 (Trika, Pratyabhijña, etc.)
  verses: 0
  factory: t1=UNKNOWN, l2=UNKNOWN, c1=UNKNOWN
```

**Honest assessment:** The traditions endpoint works. Everything else returns empty data. The 254 works are indexed but have no translations/editions/verses linked.

### openpatalanew (8801)

```
Work: PTW_00068039f45a7fe5 (A Sanskrit-English Dictionary)
  title: ✓ populated
  translations: 0
  assertions: 0
  external_ids: 0
  completeness: all NONE/UNRESOLVED
  events: 1 (EntityCreated)
```

**Honest assessment:** 935 works in DB, but no data linked. 77 assertions exist but not connected to works. Search works (7 results). Frontier exists (3 items). Bundle structure is richer but empty.

## 4. BUNDLE COMPARISON

### openpatalaproject bundle
```json
{
  "data": {
    "title": null,
    "translations": [],
    "editions": [],
    "factory": {"t1": "UNKNOWN", "l2": "UNKNOWN", "c1": "UNKNOWN"}
  },
  "provenance": {}
}
```
**Problem:** Returns flat record, no linked data.

### openpatalanew bundle
```json
{
  "data": {
    "entity": {"id": "PTW_...", "preferred_title": "..."},
    "aliases": [],
    "external_ids": [],
    "assertions": {"authorship": [], "date": [], "tradition": []},
    "editions": [],
    "witnesses": [],
    "etexts": [],
    "translations": [],
    "passages": [],
    "passage_stats": {"count": 0},
    "completeness": {"identity": "RESOLVED", "source": "NONE", ...}
  }
}
```
**Better structure** (matches newbuild1.md §6 — small permanent core + projections), but all arrays empty.

## 5. DATA FLOW COMPARISON

### openpatalaproject flow
```
Muktabodha/GRETIL → harvest_to_factory → verse JSONL → register SOURCE → deepfind translations → download → compile index → serve via FastAPI
```
- **Working:** harvest, compile, serve
- **Not working:** translations not linked, editions empty, search broken

### openpatalanew flow
```
? → ??? → Postgres → serve via FastAPI (v1)
```
- **Working:** Postgres has 935 works, 77 assertions, 38 ext_ids, 933 events
- **Not working:** No ingestion pipeline visible, data not linked, most endpoints return empty

## 6. VERDICT: WHICH IS BETTER?

**Neither is production-ready.** Both are incomplete in different ways:

| Aspect | openpatalaproject | openpatalanew |
|---|---|---|
| **Data** | 254 works, traditions work | 935 works, but all empty |
| **Architecture** | Flat JSON files (fragile) | Postgres + v2 schemas (future-proof) |
| **API** | 15 endpoints, some work | 25+ endpoints, mostly empty |
| **Ingestion** | harvest_to_factory exists | No visible ingestion pipeline |
| **Traditions** | ✓ works | ✗ not implemented |
| **Search** | ✗ broken | ✓ returns results |
| **Bundle** | Flat record | Rich structure (empty) |
| **Future-proofing** | ❌ (JSON files) | ✓ (Postgres + schemas) |

**openpatalaproject is more useful today** — traditions work, harvest pipeline exists, 254 works indexed.

**openpatalanew is better architecture** — Postgres, v2 schemas, richer API structure, 935 works.

**Neither has what Pāṭala 1 needs:** linked translations, real assertions, working bundle with data.

## 7. WHAT ACTUALLY NEEDS BUILDING

For Pāṭala 1, we need ONE system that:
1. Has works with linked translations (from translation-availability.json)
2. Has assertions (authorship, date, tradition)
3. Has external IDs (PANDiT, GRETIL, OpenAlex)
4. Serves a bundle with real data
5. Has the permanent core (entity_identity + event + artifact + schema + ledger)

**Recommendation:** Use openpatalaproject's working pipeline (harvest, compile, serve) and add the newbuild1.md permanent core on top. Don't rebuild from scratch.
