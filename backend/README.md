# Europe Travel Guide Analyzer — Backend

FastAPI backend that extracts POIs from travel guide URLs and merges approved entries into `index.html`.

---

## Prerequisites

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/)

---

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY=sk-ant-...
```

---

## Running the server

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Health check:
```bash
curl http://localhost:8000/api/health
# → {"status": "ok", "seeded_rows": <n>}
```

On first start the server seeds SQLite (`backend/europe.db`) from `_workspace/02_poi.json`.

---

## Running the frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

Vite proxies `/api` → `http://localhost:8000` — no CORS configuration needed.

---

## Running tests

```bash
cd backend
pytest tests/ -v
```

### Test categories

| Mark | Description | Gating? |
|------|-------------|---------|
| (none) | Unit + deterministic fixture tests | Yes — must pass |
| `smoke` | Live LLM call against a real URL | No — informational only |

### Gating acceptance criteria

| AC | Test | What it checks |
|----|------|----------------|
| AC3 | `TestAC3FixtureExtraction` | Extractor on fixture HTML matches golden snapshot |
| AC6 | `TestAC6ExporterShape` | Regenerated POI block has correct stop-id/category/shape |
| AC7 | `TestAC7IndexHtmlRendering` | Approved POI appears in correct city block |
| AC8 | `TestAC8MasterE2E` | Full clean-state → extract → approve → golden merge → idempotent |

---

## Clean state reset

The E2E tests manage clean state automatically via the `clean_state` pytest fixture.
To reset manually:

```bash
rm -f backend/europe.db
# Restore index.html POI block from git:
git checkout index.html
# Restore 02_poi.json from git:
git checkout _workspace/02_poi.json
```

---

## Fixtures

Committed test fixtures live in `backend/tests/fixtures/`:

| File | Purpose |
|------|---------|
| `guide_sample.html` | Minimal deterministic travel guide HTML |
| `extraction_golden.json` | Expected extractor output for `guide_sample.html` |
| `golden_merged_poi.json` | Expected `index.html` POI block after approving one candidate |

**Do not edit fixture files without updating the corresponding golden file.**

---

## Project structure

```
backend/
  app/
    main.py            # FastAPI app, router registration, startup seed
    config.py          # .env loading, fail-fast key check, paths
    schemas.py         # Pydantic request/response models
    logging_conf.py    # Structured logging + per-run summary
    api/
      routes.py        # POST /api/analyze, /api/poi/approve, GET /api/poi, etc.
    db/
      models.py        # SQLAlchemy models (external_source, poi_candidate, poi)
      session.py       # DB engine + session factory
    services/
      fetcher.py       # Server-side httpx fetch + unsupported-source guard
      extractor.py     # Claude structured LLM extraction
      resolver.py      # City→stop-id alias map + unresolved bucket
      exporter.py      # Regenerate inline POI block in index.html (sentinel splice)
    seed.py            # Seed SQLite from 02_poi.json on first run
  tests/
    fixtures/
      guide_sample.html
      extraction_golden.json
      golden_merged_poi.json
    test_e2e.py        # Deterministic E2E + resilience tests (AC3, AC8)
  requirements.txt
  .env.example
  README.md            # this file
```

---

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key — server fails to start without it |

Copy `.env.example` to `.env` and fill in the key. The `.env` file is git-ignored.
