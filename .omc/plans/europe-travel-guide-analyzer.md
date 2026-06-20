# Work Plan: 유럽 가이드 분석·통합 웹 서비스 (Phase 1 / C2 MVP) — CONSENSUS-REVISED

**Status:** APPROVED for execution via `team` (user-approved). Consensus loop: Planner → Architect (NEEDS-REWORK) → Critic (REJECT) → **revised here with all 10 required changes applied.**
**Source spec:** `.omc/specs/deep-interview-europe-travel-guide-analyzer.md` (Ambiguity 16%, PASSED)
**Project dir:** `/Users/bhkim/MyClaude/europe-travel`

> ⚠️ CRITICAL CORRECTION (Architect+Critic): The existing `index.html` does **NOT** fetch `02_poi.json` at runtime. It renders an **inline `const POI = {...}` literal at index.html:110**. `_workspace/02_poi.json` is git-ignored and is currently a **hand-copied byte-twin** of that inline block. Therefore the integration seam targets the **inline block inside index.html**, and the exporter must **preserve existing hand-curated Korean content**.

---

## 1. Requirements Summary
Local-dev, single-user, learning-purpose service that turns an external travel-guide URL into curated POIs merged into the existing Central Europe road-trip guide.

Flow: paste URL → FastAPI **server-side** fetch → Claude **structured LLM extraction** → React **city-grouped candidate cards** → user **"add"** → persist **SQLite (source of truth)** → **regenerate the inline `POI` block in `index.html`** (preserve-merge) and keep `_workspace/02_poi.json` in sync → guide reflects the new POI.

**Out of scope (Phase 2):** C1 full migration; **geocoding/coords (no Phase-1 consumer)**; per-POI map markers; auto-merge/scoring; multi-guide comparison; auth; deploy.

---

## 2. Acceptance Criteria (deterministic)
- **AC1** React exposes URL input + "Analyze"; submit → `POST /api/analyze`.
- **AC2 (smoke, non-gating)** Against a **live** guide URL, `/api/analyze` returns ≥1 structured candidate. *Live, non-deterministic → smoke test only, NOT a release gate.*
- **AC3 (gating, deterministic)** Against a **committed fixture HTML** (`backend/tests/fixtures/guide_sample.html`), `/api/analyze` (extractor run on fixture text) produces output matching the **golden snapshot** (`backend/tests/fixtures/extraction_golden.json`).
- **AC4** React groups candidates into per-city cards; unresolved-city candidates appear in an explicit **"미해결(Unresolved)" bucket**.
- **AC5** "add" → `POST /api/poi/approve` → `poi` row in SQLite with `status=approved` (verify via `GET /api/poi`).
- **AC6** On approve, the inline `POI` block in `index.html` is regenerated so the new POI appears under the correct **stop-id key** and **correct category array** in the **correct entry shape** (`restaurants`→`{name,note,price,cuisine}`, `hotels`→`{name,note,price,parking}`, `airbnb`→`{name,note,price,area}`, `highlights`→bare string). `_workspace/02_poi.json` is written identically. **Existing hand-curated entries are preserved.** File remains valid; Hangul intact.
- **AC7 (gating)** Opening `index.html` after approve shows the **newly approved** POI in its city's right-side panel. *(Must distinguish from pre-existing inline POIs — verified via golden merged-output diff, not "a POI renders".)*
- **AC8 (gating, deterministic E2E)** From **defined clean state** (empty SQLite seeded only from committed baseline; `index.html` POI block restored to committed baseline marker), running fixture → approve 1 → produces the **golden merged `index.html` POI block**. Re-running approve is idempotent (dedupe, no duplicate).

---

## 3. Architecture (revised)

### 3.1 Backend (`backend/app/`)
- `main.py` — FastAPI app, router registration, startup seed hook, `/api/health`.
- `config.py` — `.env` via python-dotenv; **fail-fast if `ANTHROPIC_API_KEY` missing at startup**; paths.
- `api/routes.py` — `POST /api/analyze`, `POST /api/poi/approve`, `POST /api/poi/{id}/unapprove`, `GET /api/candidates`, `GET /api/poi`.
- `services/fetcher.py` — httpx server fetch: UA, timeout, on-disk/SQLite HTML cache. **Unsupported-source guard (M3):** compute text density / visible-text length; below threshold → return `unsupported_source` error (fail loud, never pass thin HTML to LLM).
- `services/extractor.py` — Claude structured extraction. **MUST read the `claude-api` skill first** for current model id + structured-output (tool/JSON-schema) pattern + token limits. Strip HTML → text before sending. Output validated by Pydantic.
- `services/resolver.py` — **curated bidirectional city↔stop-id alias map** (Korean/English/native) for the 11 ids; unresolved → `unresolved` bucket; **budapest vs budapest_end policy** (default: POIs → `budapest`; `budapest_end` reserved for return-day items, configurable).
- `services/exporter.py` — **the integration heart (revised):** regenerate-from-SQLite **with preserve-merge**; sentinel-delimited splice of the inline `POI` block in `index.html`; sync-write `_workspace/02_poi.json`; atomic temp+rename; **timestamped backup before every mutate**; `ensure_ascii=False`.
- `db/models.py`, `db/session.py` — SQLAlchemy + SQLite (`backend/europe.db`).
- `seed.py` — **on first run, seed SQLite from existing `_workspace/02_poi.json`** (or inline block) so curated content becomes managed, not clobbered.
- `schemas.py` — Pydantic models. `logging_conf.py` — structured logging + per-run summary (counts: extracted / unresolved-dropped / dedupe-collisions / written).

### 3.2 SQLite schema (geocode_cache REMOVED — M1)
```
external_source(id, url UNIQUE, fetched_at, raw_text, status)
poi_candidate(id, source_id FK, name, city_raw, resolved_stop_id NULLABLE,
              category['restaurants'|'hotels'|'airbnb'|'highlights'],
              note, price, cuisine, parking, area,
              status['pending'|'approved'|'rejected'|'unresolved'], created_at)
poi(id, candidate_id FK, stop_id, category, name, note, price, cuisine, parking, area,
    origin['seed'|'extracted'], exported_at)
```
SQLite = source of truth for **all** POIs (seeded + extracted). `index.html` inline block + `02_poi.json` are **derived projections, fully regenerated** from SQLite.

### 3.3 Extraction → consumer schema mapping (C2 — was missing)
Extractor returns per item: `{ name, city, kind, note?, price?, cuisine? }` where `kind ∈ {restaurant, hotel, apartment, sight}`.
Projection:
| kind | category array | entry shape | field rules |
|------|----------------|-------------|-------------|
| restaurant | `restaurants` | `{name,note,price,cuisine}` | note←note/desc; price←price or `""`; cuisine←cuisine or `""` |
| hotel | `hotels` | `{name,note,price,parking}` | parking←`""` if absent |
| apartment | `airbnb` | `{name,note,price,area}` | area←`""` if absent |
| sight | `highlights` | **bare string** = `name` | note/price dropped (shape asymmetry honored) |

### 3.4 Frontend (`frontend/`, Vite+React+TS+Tailwind)
- `UrlAnalyzer.tsx`, `CityCandidateGroup.tsx` (+ Unresolved group), `CandidateCard.tsx` ("add"→approve), `ApprovedList.tsx` (+ open index.html link, unapprove), `api/client.ts`.
- **M4 — wiring:** Vite `server.proxy` maps `/api` → `http://localhost:8000` (preferred over CORS for single-user local).

### 3.5 index.html seam (C1)
Add stable sentinel comments around the inline literal:
```
/* POI_BLOCK_START */ const POI = { ... }; /* POI_BLOCK_END */
```
Exporter replaces only between sentinels. One-time prep step inserts sentinels around the current `index.html:110` block (with backup).

---

## 4. Implementation Steps (revised order)
1. **Scaffold backend + DB + config + seed.** FastAPI/SQLAlchemy/httpx/anthropic/pydantic/python-dotenv; models (no geocode_cache); `.env.example`; fail-fast key check; `/api/health`. **Seed SQLite from existing 02_poi.json.** *AC: server starts; health 200; DB has seeded rows matching curated content.*
2. **Fetch + unsupported-source guard + LLM extraction (`POST /api/analyze`).** Consult `claude-api` skill. Persist source + candidates (pending/unresolved). *AC: AC3 golden-snapshot match on fixture; thin-HTML fixture → `unsupported_source`.*
3. **Resolver + alias map.** Bidirectional KR/EN/native map for 11 ids; unresolved bucket; budapest policy. *AC: known cities resolve; "밀라노"/"Milano"→`milan`; unknown→unresolved, never silently dropped.*
4. **React console + approve/unapprove.** Components, Vite proxy, city groups + Unresolved group. *AC: AC1, AC4, AC5.*
5. **Exporter: regenerate inline POI block + 02_poi.json (preserve-merge, sentinels, backup, atomic).** Projection per §3.3; dedupe key `stop_id+category+name`. *AC: AC6, AC7, idempotent re-approve.*
6. **Deterministic E2E + fixtures + docs.** Commit `guide_sample.html`, `extraction_golden.json`, golden merged POI block, baseline index.html marker; structured logging + per-run summary; `backend/README.md`. *AC: AC8 reproducible; route final check through `verifier` agent.*

---

## 5. Risks & Mitigations
| ID | Risk | Mitigation |
|----|------|-----------|
| R1 | LLM extraction unreliable / hallucination | Anthropic structured output + Pydantic validation + **human approval gate** (no auto-insert); golden-snapshot regression. |
| R2 | Scraping fragility / JS-rendered pages | **M3 unsupported-source guard (fail loud)**; UA+timeout+cache; optional headless fallback Phase 2. |
| R3 | ~~Nominatim limits~~ | **Deferred to Phase 2 (geocoding removed from MVP).** |
| R4 | **Clobbering hand-curated index.html / schema drift** | Regenerate-with-preserve-merge; seed SQLite from existing data; sentinel splice; **timestamped backup + atomic temp+rename** before every mutate; exact per-category shape; post-write JSON/JS validity check. |
| R5 | Claude API key exposure | `.env` (git-ignored) + `.env.example`; **fail-fast at startup**; server-side only, never to frontend. |
| R6 | city→stop-id misresolution / silent drop | Curated bidirectional alias map + explicit unresolved bucket surfaced in UI; budapest/budapest_end policy. |
| R7 | Non-deterministic tests (NEW) | Fixture HTML + golden snapshots gate; live calls are non-gating smoke only. |
| R8 | Mid-write corruption of tracked 54KB index.html (NEW) | Backup-before-mutate + atomic rename + validate-after-write + restore-on-failure. |

---

## 6. Verification Steps
1. Define clean state: empty `europe.db` seeded from committed baseline; `index.html` POI block = committed baseline between sentinels.
2. Backend up → `/api/health` 200; seed rows present.
3. **Gating:** run extractor on fixture → assert golden snapshot (AC3).
4. UI: city-grouped + Unresolved groups (AC4).
5. Approve one → SQLite `poi` row (AC5).
6. Inspect regenerated inline POI block + 02_poi.json → correct stop-id/category/shape, curated entries preserved, valid, Hangul intact (AC6).
7. Open index.html → newly approved POI visible; diff vs golden merged block (AC7).
8. **Master E2E (AC8):** clean state → fixture → approve 1 → golden merged output; re-approve idempotent.
9. Resilience: bad URL → graceful; thin HTML → unsupported_source; unknown city → unresolved bucket.
10. Independent `verifier` agent evidence pass before "done".

---

## 7. ADR
- **Decision:** SQLite-source-of-truth + **regenerate-with-preserve-merge** projection into **index.html inline `POI` block** (sentinel splice) and synced `02_poi.json`; **LLM** extraction; **geocoding deferred**.
- **Drivers:** (1) learning value (FastAPI+React+DB); (2) backward compatibility — must not break/clobber the finished hand-curated guide; (3) robustness to arbitrary external sites; (4) deterministic testability.
- **Alternatives considered:**
  - *Write only `_workspace/02_poi.json` (original plan)* — **REJECTED:** index.html doesn't read it → renders nothing (Architect/Critic FATAL).
  - *Append-to-JSON* — **REJECTED:** drifts from SQLite, no delete path, risks clobber.
  - *Convert index.html to runtime `fetch()` + un-ignore file* — viable alternative; deferred because sentinel splice keeps the zero-build `file://`-openable site behavior unchanged.
  - *Heuristic parsing* — REJECTED: not robust to arbitrary sites.
  - *Geocoder in MVP* — REJECTED: no Phase-1 consumer (POIs render as text cards with `gmaps()` search links; markers only for route stops).
- **Why chosen:** only path that actually renders new POIs while preserving curated content and staying deterministically testable.
- **Consequences:** string-splice on a tracked file (mitigated by sentinels+backup+atomic); seed/migration required first run; geocoder work shifts to Phase 2.
- **Follow-ups (Phase 2):** geocoding + per-POI markers; C1 full React migration; headless render; multi-guide compare; auth/deploy.

---

## 8. Changelog (consensus revisions applied)
Applied all 10 Critic REQUIRED CHANGES + Architect synthesis: (1) seam re-pointed to inline POI block; (2) extraction→consumer schema mapping defined; (3) seed-from-existing + preserve-merge + dedupe/unapprove; (4) deterministic fixtures/golden for AC2/AC8; (5) geocoder→Phase 2; (6) curated alias map + unresolved bucket + budapest policy; (7) JS-render/unsupported-source guard; (8) Vite proxy; (9) "clean state" defined; (10) backup+atomic write, structured logging, .env fail-fast.

## 9. Open Questions (non-blocking; default decisions taken)
- Automate the "edit JSON → paste into index.html" manual workflow? → **Default taken:** automate via sentinel splice + sync 02_poi.json.
- Bring `04_city_tips.json` / `01_route.json` into scope? → **Default:** out of scope (POI only).
- Confirm Claude model id at build time via `claude-api` skill (spec suggested `claude-sonnet-4-6`).
