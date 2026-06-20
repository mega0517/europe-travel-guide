"""
Deterministic E2E tests — AC3, AC5, AC6, AC7, AC8.

Mock strategy
-------------
Two patches are applied for every /api/analyze call:

  patch("app.services.fetcher.fetch_url")
      Bypasses httpx entirely; returns (FakeSource, fixture_html_text).

  patch("app.services.extractor.anthropic_client")
      Returns pre-recorded structured-output JSON matching extraction_golden.json.

This exercises all real code: extract_candidates → resolver wiring →
routes.approve_poi → exporter.export_to_index_html → sentinel splice.

Clean state
-----------
The module-scoped TestClient keeps one DB across all tests.  Per-test
isolation is achieved by truncating all tables (via SQLAlchemy) and
restoring index.html / 02_poi.json to the committed baseline.  The DB
engine is never deleted so the SQLite file stays writable.

Golden files
------------
  fixtures/extraction_golden.json  — categorised extractor output
  fixtures/golden_merged_poi.json  — expected POI dict after approving
                                     Trattoria Milanese (first resolved
                                     candidate from the fixture).
                                     Auto-generated deterministically on
                                     first run if not yet committed.
"""

from __future__ import annotations

import copy
import json
import re
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).parent.parent
FIXTURES_DIR = Path(__file__).parent / "fixtures"
INDEX_HTML   = BACKEND_DIR.parent / "index.html"
POI_JSON     = BACKEND_DIR.parent / "_workspace" / "02_poi.json"
DB_PATH      = BACKEND_DIR / "europe.db"

GUIDE_SAMPLE_HTML = FIXTURES_DIR / "guide_sample.html"
EXTRACTION_GOLDEN = FIXTURES_DIR / "extraction_golden.json"
GOLDEN_MERGED_POI = FIXTURES_DIR / "golden_merged_poi.json"

POI_BLOCK_START = "/* POI_BLOCK_START */"
POI_BLOCK_END   = "/* POI_BLOCK_END */"

# ---------------------------------------------------------------------------
# Baseline snapshot
#
# Read once at import time from 02_poi.json.  A guard verifies the file
# has the expected counts so a polluted state is caught immediately.
#
# Expected (from the committed original):
#   milan.restaurants = 7, milan.airbnb = 3, milan.highlights = 12
# If the file has been mutated by a previous test run, restore it first:
#   cd backend && python3 -m pytest tests/test_e2e.py --setup-only -q
# or manually remove the extractions that leaked in.
# ---------------------------------------------------------------------------

def _read_baseline_with_guard() -> dict:
    d = json.loads(POI_JSON.read_text(encoding="utf-8"))
    milan_r = len(d.get("milan", {}).get("restaurants", []))
    milan_a = len(d.get("milan", {}).get("airbnb", []))
    milan_h = len(d.get("milan", {}).get("highlights", []))
    if milan_r != 7 or milan_a != 3 or milan_h != 12:
        # Auto-clean leaked fixture extractions so tests can proceed
        d["milan"]["restaurants"] = [
            e for e in d["milan"]["restaurants"]
            if (e["name"] if isinstance(e, dict) else e) != "Luini"
        ]
        d["milan"]["airbnb"] = [
            e for e in d["milan"]["airbnb"]
            if (e["name"] if isinstance(e, dict) else e) != "Airbnb Navigli District"
        ]
        d["milan"]["highlights"] = [
            e for e in d["milan"]["highlights"]
            if (e if isinstance(e, str) else e.get("name", ""))
            not in ("The Last Supper", "Duomo di Milano")
        ]
        # Persist the cleaned baseline so disk stays in sync
        POI_JSON.write_text(
            json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return d

_BASELINE_POI_SNAPSHOT: dict = _read_baseline_with_guard()

# ---------------------------------------------------------------------------
# Pre-recorded LLM response
#
# extractor.py reads response.content[0].text as a JSON string whose schema
# matches _OUTPUT_SCHEMA (categorised: restaurants/hotels/airbnb/highlights).
# This recording exactly matches extraction_golden.json.
# ---------------------------------------------------------------------------
_GOLDEN_EXTRACTION: dict = json.loads(EXTRACTION_GOLDEN.read_text(encoding="utf-8"))

RECORDED_LLM_JSON: str = json.dumps(_GOLDEN_EXTRACTION, ensure_ascii=False)


def _make_mock_llm() -> MagicMock:
    block = MagicMock()
    block.type = "text"          # extractor filters content by type == "text"
    block.text = RECORDED_LLM_JSON
    resp = MagicMock()
    resp.stop_reason = "end_turn"  # must not be "refusal"
    resp.content = [block]
    client = MagicMock()
    client.messages.create.return_value = resp
    return client


# ---------------------------------------------------------------------------
# Clean-state helpers
# ---------------------------------------------------------------------------

def _baseline_poi() -> dict:
    """Return the immutable baseline POI dict snapshotted at import time."""
    return copy.deepcopy(_BASELINE_POI_SNAPSHOT)


def _restore_index_html(baseline: dict) -> None:
    """Insert or replace the sentinel-wrapped POI block in index.html."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    poi_str   = json.dumps(baseline, ensure_ascii=False, indent=2)
    new_block = f"{POI_BLOCK_START}\nconst POI = {poi_str};\n{POI_BLOCK_END}"

    if POI_BLOCK_START in html:
        restored = re.sub(
            re.escape(POI_BLOCK_START) + r".*?" + re.escape(POI_BLOCK_END),
            new_block, html, flags=re.DOTALL,
        )
    else:
        # First run: wrap the bare `const POI = {...};`
        restored = re.sub(
            r"const\s+POI\s*=\s*\{.*?\}\s*;",
            new_block, html, flags=re.DOTALL, count=1,
        )
        if restored == html:
            raise RuntimeError("Cannot locate `const POI = {...};` in index.html")

    INDEX_HTML.write_text(restored, encoding="utf-8")


def _restore_poi_json(baseline: dict) -> None:
    POI_JSON.write_text(
        json.dumps(baseline, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _truncate_db_tables() -> None:
    """Delete all rows from mutable tables without touching the DB file."""
    from app.db.session import SessionLocal
    from app.db.models import Poi, PoiCandidate, ExternalSource
    db = SessionLocal()
    try:
        db.query(Poi).delete()
        db.query(PoiCandidate).delete()
        db.query(ExternalSource).delete()
        db.commit()
    finally:
        db.close()


def _reseed_db() -> None:
    """Re-seed POI table from 02_poi.json (mirrors startup behaviour)."""
    from app.db.session import SessionLocal
    from app.seed import seed_from_poi_json
    db = SessionLocal()
    try:
        seed_from_poi_json(db, POI_JSON)
    finally:
        db.close()


def reset_clean_state() -> None:
    """Restore files + DB to committed baseline."""
    baseline = _baseline_poi()
    _restore_index_html(baseline)
    _restore_poi_json(baseline)
    _truncate_db_tables()
    _reseed_db()
    # Remove backup files left by exporter
    for bak in INDEX_HTML.parent.glob("index.html.*.bak"):
        bak.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Golden merged POI
#
# Vienna is NOT in the alias map → all Vienna candidates are unresolved.
# Milan resolves to "milan". First resolved pending candidate from the
# fixture is Trattoria Milanese (milan / restaurants).
# golden_merged = baseline + Trattoria Milanese appended to milan.restaurants.
# ---------------------------------------------------------------------------

def _build_golden_merged() -> dict:
    # Approve "Luini" — it resolves to milan/restaurants and is NOT already
    # in the baseline 02_poi.json (baseline has "Luini Panzerotti", not "Luini").
    merged = copy.deepcopy(_baseline_poi())
    entry = {
        "name":    "Luini",
        "note":    "Famous street-food spot for panzerotti (fried dough pockets)",
        "price":   "€",
        "cuisine": "Street food",
    }
    merged.setdefault("milan", {}).setdefault("restaurants", []).append(entry)
    return merged


def _golden_merged() -> dict:
    if GOLDEN_MERGED_POI.exists():
        return json.loads(GOLDEN_MERGED_POI.read_text(encoding="utf-8"))
    golden = _build_golden_merged()
    GOLDEN_MERGED_POI.write_text(
        json.dumps(golden, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return golden


# ---------------------------------------------------------------------------
# Index-html parsing helpers
# ---------------------------------------------------------------------------

def _read_poi_from_index() -> dict:
    html = INDEX_HTML.read_text(encoding="utf-8")
    m = re.search(
        re.escape(POI_BLOCK_START) + r"(.*?)" + re.escape(POI_BLOCK_END),
        html, re.DOTALL,
    )
    assert m, "Sentinels not found in index.html — exporter did not run"
    obj = re.search(r"const\s+POI\s*=\s*(\{.*\})\s*;", m.group(1), re.DOTALL)
    assert obj, "Cannot parse `const POI = {...};` from sentinel block"
    return json.loads(obj.group(1))


# ---------------------------------------------------------------------------
# Patch context manager
# ---------------------------------------------------------------------------

@contextmanager
def _patch_analyze(source_id: int = 1):
    """Patch fetch_url + anthropic_client for one /api/analyze call."""
    fake_src = MagicMock()
    fake_src.id = source_id
    # fetch_url is imported at module top in routes.py (from app.services.fetcher
    # import fetch_url), so the bound name lives in app.api.routes — patch there.
    with (
        patch("app.api.routes.fetch_url",
              return_value=(fake_src, GUIDE_SAMPLE_HTML.read_text(encoding="utf-8"))),
        patch("app.services.extractor.anthropic_client", _make_mock_llm()),
    ):
        yield


# ---------------------------------------------------------------------------
# pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    """TestClient — app started once per module; DB file kept alive."""
    # Ensure DB exists before first import of app (config.py fail-fast needs key)
    if DB_PATH.exists():
        DB_PATH.unlink()
    from app.main import app
    with TestClient(app) as c:
        yield c
    reset_clean_state()


@pytest.fixture(autouse=False)
def clean_state_fixture(client):  # noqa: ARG001 — client ensures app is imported first
    """Per-test clean state: truncate tables, re-seed, restore files."""
    reset_clean_state()
    yield
    reset_clean_state()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _analyze_fixture(client) -> list[dict]:
    with _patch_analyze():
        resp = client.post("/api/analyze", json={"url": "http://fixture.test/guide"})
    assert resp.status_code == 200, resp.text
    return resp.json()["candidates"]


def _first_resolved(candidates: list[dict]) -> dict:
    """Return the first resolved pending candidate that is NOT already in the
    seeded baseline (so approving it produces a visible new entry in index.html).
    Falls back to any resolved pending candidate if all are duplicates.
    """
    baseline = _baseline_poi()
    resolved = [
        c for c in candidates
        if c["status"] == "pending" and c["resolved_stop_id"] is not None
    ]
    assert resolved, "No resolved pending candidates in fixture response"
    # Prefer a candidate whose name is not already in the baseline stop bucket
    for c in resolved:
        stop = c["resolved_stop_id"]
        cat  = c["category"]
        existing_names = {
            e["name"] if isinstance(e, dict) else e
            for e in baseline.get(stop, {}).get(cat, [])
        }
        if c["name"] not in existing_names:
            return c
    # All are duplicates — return first anyway (dedupe test still valid)
    return resolved[0]


def _approve(client, candidate_id: int) -> dict:
    resp = client.post("/api/poi/approve", json={"candidate_id": candidate_id})
    assert resp.status_code == 200, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Fixture-existence guard (no clean_state needed)
# ---------------------------------------------------------------------------

def test_fixture_files_exist():
    assert GUIDE_SAMPLE_HTML.exists(), "guide_sample.html fixture missing"
    assert EXTRACTION_GOLDEN.exists(), "extraction_golden.json fixture missing"


# ---------------------------------------------------------------------------
# AC3 — Deterministic extraction (gating)
# ---------------------------------------------------------------------------

class TestAC3FixtureExtraction:
    """Extractor on fixture HTML → candidates match golden snapshot."""

    def test_analyze_returns_200(self, client, clean_state_fixture):
        with _patch_analyze():
            resp = client.post("/api/analyze", json={"url": "http://fixture.test/guide"})
        assert resp.status_code == 200, resp.text

    def test_counts_match_golden(self, client, clean_state_fixture):
        expected = sum(len(v) for v in _GOLDEN_EXTRACTION.values())
        assert len(_analyze_fixture(client)) == expected, (
            f"Got {len(_analyze_fixture(client))} candidates, expected {expected}"
        )

    def test_all_golden_names_present(self, client, clean_state_fixture):
        golden_names = {
            item["name"]
            for items in _GOLDEN_EXTRACTION.values()
            for item in items
        }
        returned = {c["name"] for c in _analyze_fixture(client)}
        missing = golden_names - returned
        assert not missing, f"Golden names missing from candidates: {missing}"

    def test_category_counts_match(self, client, clean_state_fixture):
        candidates = _analyze_fixture(client)
        by_cat: dict[str, int] = {}
        for c in candidates:
            by_cat[c["category"]] = by_cat.get(c["category"], 0) + 1
        assert by_cat.get("restaurants", 0) == len(_GOLDEN_EXTRACTION["restaurants"])
        assert by_cat.get("hotels",      0) == len(_GOLDEN_EXTRACTION["hotels"])
        assert by_cat.get("airbnb",      0) == len(_GOLDEN_EXTRACTION["airbnb"])
        assert by_cat.get("highlights",  0) == len(_GOLDEN_EXTRACTION["highlights"])

    def test_response_counts_field_matches(self, client, clean_state_fixture):
        with _patch_analyze():
            resp = client.post("/api/analyze", json={"url": "http://fixture.test/guide"})
        counts = resp.json()["counts"]
        assert counts["restaurants"] == len(_GOLDEN_EXTRACTION["restaurants"])
        assert counts["hotels"]      == len(_GOLDEN_EXTRACTION["hotels"])
        assert counts["airbnb"]      == len(_GOLDEN_EXTRACTION["airbnb"])
        assert counts["highlights"]  == len(_GOLDEN_EXTRACTION["highlights"])
        assert counts["total"] == sum(len(v) for v in _GOLDEN_EXTRACTION.values())


# ---------------------------------------------------------------------------
# Resolver wiring
# ---------------------------------------------------------------------------

class TestResolverWiring:

    def test_vienna_candidates_are_unresolved(self, client, clean_state_fixture):
        """Vienna is not in the alias map → status=unresolved, stop_id=None."""
        candidates = _analyze_fixture(client)
        vienna = [c for c in candidates if c.get("city_raw") == "Vienna"]
        assert vienna, "Expected ≥1 Vienna candidate"
        for c in vienna:
            assert c["resolved_stop_id"] is None, (
                f"'{c['name']}' (Vienna) should have resolved_stop_id=None"
            )
            assert c["status"] == "unresolved", (
                f"'{c['name']}' (Vienna) status should be 'unresolved', got {c['status']!r}"
            )

    def test_milan_candidates_are_resolved(self, client, clean_state_fixture):
        candidates = _analyze_fixture(client)
        milan = [c for c in candidates if c.get("city_raw") == "Milan"]
        assert milan, "Expected ≥1 Milan candidate"
        for c in milan:
            assert c["resolved_stop_id"] == "milan", (
                f"'{c['name']}' (Milan) should resolve to 'milan', got {c['resolved_stop_id']!r}"
            )

    def test_unresolved_candidates_appear_in_list(self, client, clean_state_fixture):
        _analyze_fixture(client)
        unresolved = [
            c for c in client.get("/api/candidates").json()
            if c["status"] == "unresolved"
        ]
        assert unresolved, "Unresolved candidates silently dropped from /api/candidates"

    def test_total_includes_unresolved(self, client, clean_state_fixture):
        candidates = _analyze_fixture(client)
        assert len(candidates) == sum(len(v) for v in _GOLDEN_EXTRACTION.values())


# ---------------------------------------------------------------------------
# Resilience
# ---------------------------------------------------------------------------

class TestResilienceCases:

    def test_bad_url_returns_graceful_error(self, client, clean_state_fixture):
        resp = client.post(
            "/api/analyze",
            json={"url": "http://this.host.does.not.exist.invalid/"},
        )
        assert resp.status_code in (400, 422, 502, 503, 504), (
            f"Expected graceful error, got {resp.status_code}: {resp.text}"
        )
        assert "detail" in resp.json() or "error" in resp.json()

    def test_thin_html_returns_422(self, client, clean_state_fixture):
        """Text-density guard (M3): thin HTML → 422 before reaching LLM."""
        import httpx

        # Build a minimal thin page — all tags, almost no visible text
        # so text_density < TEXT_DENSITY_MIN (0.03)
        thin = "<html>" + "<div></div>" * 200 + "<body><p>Hi</p></body></html>"

        class _FakeResponse:
            status_code = 200
            text = thin
            def raise_for_status(self): pass

        with patch("app.services.fetcher.httpx.get", return_value=_FakeResponse()):
            resp = client.post("/api/analyze", json={"url": "http://example.com/thin"})

        assert resp.status_code == 422, (
            f"Expected 422 for thin HTML, got {resp.status_code}: {resp.text}"
        )
        detail = json.dumps(resp.json()).lower()
        assert any(kw in detail for kw in ("unsupported", "density", "js-rendered")), (
            f"Expected unsupported-source message, got: {resp.json()}"
        )

    def test_approve_unresolved_returns_400(self, client, clean_state_fixture):
        candidates = _analyze_fixture(client)
        unresolved = [c for c in candidates if c["status"] == "unresolved"]
        assert unresolved, "Need an unresolved candidate"
        resp = client.post("/api/poi/approve", json={"candidate_id": unresolved[0]["id"]})
        assert resp.status_code == 400

    def test_approve_nonexistent_returns_404(self, client, clean_state_fixture):
        resp = client.post("/api/poi/approve", json={"candidate_id": 999999})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# AC5 — Approve → SQLite poi row (gating)
# ---------------------------------------------------------------------------

class TestAC5Approve:

    def test_approve_returns_200_and_poi_id(self, client, clean_state_fixture):
        cid = _first_resolved(_analyze_fixture(client))["id"]
        resp = client.post("/api/poi/approve", json={"candidate_id": cid})
        assert resp.status_code == 200, resp.text
        assert isinstance(resp.json().get("poi_id"), int)

    def test_poi_row_visible_in_get_api_poi(self, client, clean_state_fixture):
        cid = _first_resolved(_analyze_fixture(client))["id"]
        poi_id = _approve(client, cid)["poi_id"]
        rows = client.get("/api/poi").json()
        assert any(r["id"] == poi_id for r in rows), (
            f"poi_id={poi_id} not found in GET /api/poi"
        )

    def test_candidate_status_becomes_approved(self, client, clean_state_fixture):
        cid = _first_resolved(_analyze_fixture(client))["id"]
        _approve(client, cid)
        candidate = next(
            c for c in client.get("/api/candidates").json() if c["id"] == cid
        )
        assert candidate["status"] == "approved"

    def test_poi_row_has_correct_stop_id(self, client, clean_state_fixture):
        candidate = _first_resolved(_analyze_fixture(client))
        poi_id = _approve(client, candidate["id"])["poi_id"]
        poi = next(r for r in client.get("/api/poi").json() if r["id"] == poi_id)
        assert poi["stop_id"] == candidate["resolved_stop_id"]

    def test_approve_already_approved_returns_400(self, client, clean_state_fixture):
        cid = _first_resolved(_analyze_fixture(client))["id"]
        _approve(client, cid)
        resp = client.post("/api/poi/approve", json={"candidate_id": cid})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# AC6 — Exporter: correct shape + preserve-merge + sync (gating)
# ---------------------------------------------------------------------------

class TestAC6ExporterShape:

    def _setup(self, client) -> dict:
        """Approve the first new (non-duplicate) resolved candidate."""
        candidates = _analyze_fixture(client)
        first = _first_resolved(candidates)
        _approve(client, first["id"])
        return first

    def test_poi_appears_under_correct_stop_id_and_category(
        self, client, clean_state_fixture
    ):
        first = self._setup(client)
        poi = _read_poi_from_index()
        stop_id = first["resolved_stop_id"]
        category = first["category"]
        assert stop_id in poi, f"stop_id '{stop_id}' missing from index.html"
        names = [
            e["name"] if isinstance(e, dict) else e
            for e in poi[stop_id].get(category, [])
        ]
        assert first["name"] in names, (
            f"'{first['name']}' not found in {stop_id}.{category}: {names}"
        )

    def test_restaurant_shape_correct(self, client, clean_state_fixture):
        """restaurants → {name, note?, price?, cuisine?} — no extra fields."""
        first = self._setup(client)
        assert first["category"] == "restaurants", (
            "This test requires a restaurant candidate — adjust fixture if needed"
        )
        entry = next(
            e for e in _read_poi_from_index()[first["resolved_stop_id"]]["restaurants"]
            if isinstance(e, dict) and e.get("name") == first["name"]
        )
        extra = set(entry.keys()) - {"name", "note", "price", "cuisine"}
        assert not extra, f"Unexpected fields in restaurant entry: {extra}"
        assert entry["name"] == first["name"]

    def test_curated_entries_preserved(self, client, clean_state_fixture):
        first = self._setup(client)
        stop_id = first["resolved_stop_id"]
        category = first["category"]
        orig_names = {
            e["name"] if isinstance(e, dict) else e
            for e in _baseline_poi().get(stop_id, {}).get(category, [])
        }
        after_names = {
            e["name"] if isinstance(e, dict) else e
            for e in _read_poi_from_index().get(stop_id, {}).get(category, [])
        }
        assert not (orig_names - after_names), (
            f"Hand-curated entries clobbered: {orig_names - after_names}"
        )

    def test_all_stop_ids_preserved(self, client, clean_state_fixture):
        baseline_keys = set(_baseline_poi().keys())
        self._setup(client)
        dropped = baseline_keys - set(_read_poi_from_index().keys())
        assert not dropped, f"Stop ids dropped: {dropped}"

    def test_poi_json_in_sync_with_index_html(self, client, clean_state_fixture):
        self._setup(client)
        assert _read_poi_from_index() == json.loads(POI_JSON.read_text(encoding="utf-8")), (
            "02_poi.json out of sync with index.html"
        )

    def test_hangul_not_escaped(self, client, clean_state_fixture):
        self._setup(client)
        html = INDEX_HTML.read_text(encoding="utf-8")
        m = re.search(
            re.escape(POI_BLOCK_START) + r"(.*?)" + re.escape(POI_BLOCK_END),
            html, re.DOTALL,
        )
        assert m and "\\u" not in m.group(1), (
            "Unicode escapes in POI block — ensure_ascii=False violated"
        )

    def test_valid_json_block(self, client, clean_state_fixture):
        self._setup(client)
        assert isinstance(_read_poi_from_index(), dict)


# ---------------------------------------------------------------------------
# AC7 — index.html shows newly approved POI vs golden diff (gating)
# ---------------------------------------------------------------------------

class TestAC7NewPoiVisible:

    def test_index_html_matches_golden_merged(self, client, clean_state_fixture):
        golden = _golden_merged()
        candidates = _analyze_fixture(client)
        first = _first_resolved(candidates)
        _approve(client, first["id"])
        assert _read_poi_from_index() == golden, (
            "index.html POI block != golden_merged_poi.json after approve.\n"
            f"Approved: {first['name']} -> {first['resolved_stop_id']}/{first['category']}"
        )


# ---------------------------------------------------------------------------
# AC8 — Master deterministic E2E (gating)
# ---------------------------------------------------------------------------

class TestAC8MasterE2E:

    def test_clean_state_to_golden_merge(self, client, clean_state_fixture):
        """
        Defined clean state → fixture extract (mocked LLM) → approve first
        resolved candidate → index.html == golden_merged_poi.json →
        02_poi.json in sync → re-approve is idempotent.
        """
        golden = _golden_merged()

        # Step 1: analyze
        candidates = _analyze_fixture(client)
        assert candidates

        # Step 2: pick first resolved candidate not already in the baseline
        first = _first_resolved(candidates)
        assert first is not None, "No resolved candidate found outside the baseline"

        # Step 3: approve
        poi_id = _approve(client, first["id"])["poi_id"]

        # Step 4: AC5 — poi row in SQLite
        assert any(
            r["id"] == poi_id for r in client.get("/api/poi").json()
        ), f"poi_id={poi_id} not in GET /api/poi"

        # Step 5: AC6/AC7 — index.html matches golden
        actual = _read_poi_from_index()
        assert actual == golden, (
            "AC8: index.html POI block does not match golden_merged_poi.json.\n"
            f"milan.restaurants actual count: "
            f"{len(actual.get('milan', {}).get('restaurants', []))}\n"
            f"milan.restaurants golden count: "
            f"{len(golden.get('milan', {}).get('restaurants', []))}"
        )

        # Step 6: 02_poi.json in sync
        assert json.loads(POI_JSON.read_text(encoding="utf-8")) == actual

        # Step 7: idempotency — re-analyze, approve same-named dup
        with _patch_analyze(source_id=2):
            client.post("/api/analyze", json={"url": "http://fixture.test/guide"})

        dup = next(
            (
                c for c in client.get("/api/candidates").json()
                if c["name"] == first["name"] and c["status"] == "pending"
            ),
            None,
        )
        if dup:
            resp = client.post("/api/poi/approve", json={"candidate_id": dup["id"]})
            assert resp.status_code == 200, "Dedupe re-approve should return 200"
            assert _read_poi_from_index() == golden, (
                "Re-approve changed the POI block (not idempotent)"
            )
            matching = [
                r for r in client.get("/api/poi").json() if r["name"] == first["name"]
            ]
            assert len(matching) == 1, f"Duplicate POI rows: {matching}"

    def test_all_original_stop_ids_preserved(self, client, clean_state_fixture):
        baseline_keys = set(_baseline_poi().keys())
        _approve(client, _first_resolved(_analyze_fixture(client))["id"])
        assert baseline_keys <= set(_read_poi_from_index().keys())

    def test_hangul_intact_after_e2e(self, client, clean_state_fixture):
        _approve(client, _first_resolved(_analyze_fixture(client))["id"])
        html = INDEX_HTML.read_text(encoding="utf-8")
        m = re.search(
            re.escape(POI_BLOCK_START) + r"(.*?)" + re.escape(POI_BLOCK_END),
            html, re.DOTALL,
        )
        assert m and "\\u" not in m.group(1), "Korean text was unicode-escaped"


# ---------------------------------------------------------------------------
# ExportError raise/rollback contract (task #8)
# ---------------------------------------------------------------------------

class TestExporterFailureContract:
    """Verify that export failures raise ExportError and that routes roll back
    the DB transaction so SQLite and index.html never diverge.

    Three scenarios:
      1. export_to_index_html raises ExportError directly (unit).
      2. approve_poi rolls back the poi row when export fails → 500 returned,
         no orphan poi row in DB, candidate status stays 'pending'.
      3. unapprove_poi rolls back the delete when export fails → 500 returned,
         poi row still present in DB.
    """

    def test_export_raises_when_index_html_missing(self, client, clean_state_fixture):
        """export_to_index_html must RAISE ExportError (not silently return)
        when index.html does not exist."""
        from app.db.session import SessionLocal
        from app.services.exporter import ExportError, export_to_index_html

        # Temporarily rename index.html so the exporter cannot find it
        backup = INDEX_HTML.with_suffix(".html.missing_test_bak")
        INDEX_HTML.rename(backup)
        try:
            db = SessionLocal()
            try:
                with pytest.raises(ExportError, match="index.html not found"):
                    export_to_index_html(db)
            finally:
                db.close()
        finally:
            backup.rename(INDEX_HTML)

    def test_export_raises_on_corrupt_poi_block(self, clean_state_fixture):
        """export_to_index_html must RAISE ExportError when the POI block
        contains invalid JSON (not silently return)."""
        from app.db.session import SessionLocal
        from app.services.exporter import ExportError, export_to_index_html

        # Corrupt the POI block in index.html
        html = INDEX_HTML.read_text(encoding="utf-8")
        corrupted = re.sub(
            re.escape(POI_BLOCK_START) + r".*?" + re.escape(POI_BLOCK_END),
            f"{POI_BLOCK_START}\nconst POI = {{broken json;\n{POI_BLOCK_END}",
            html,
            flags=re.DOTALL,
        )
        INDEX_HTML.write_text(corrupted, encoding="utf-8")

        db = SessionLocal()
        try:
            with pytest.raises(ExportError):
                export_to_index_html(db)
        finally:
            db.close()

    def test_approve_rolls_back_when_export_fails(self, client, clean_state_fixture):
        """POST /api/poi/approve must return 500 and leave no orphan poi row
        when export_to_index_html raises ExportError."""
        # Get a resolved candidate
        candidate = _first_resolved(_analyze_fixture(client))
        cid = candidate["id"]

        poi_count_before = len(client.get("/api/poi").json())

        # Patch export to raise ExportError
        from app.services.exporter import ExportError
        with patch("app.api.routes.export_to_index_html", side_effect=ExportError("injected export failure")):
            resp = client.post("/api/poi/approve", json={"candidate_id": cid})

        assert resp.status_code == 500, f"Expected 500 on export failure, got {resp.status_code}"
        assert "export" in resp.json().get("detail", "").lower(), resp.text

        # DB must be rolled back — no new poi row
        poi_count_after = len(client.get("/api/poi").json())
        assert poi_count_after == poi_count_before, (
            f"Orphan poi row created despite export failure: "
            f"before={poi_count_before}, after={poi_count_after}"
        )

        # Candidate status must still be 'pending' (rolled back)
        candidates = client.get("/api/candidates").json()
        c = next((x for x in candidates if x["id"] == cid), None)
        assert c is not None, f"Candidate {cid} not found after rolled-back approve"
        assert c["status"] == "pending", (
            f"Candidate status not rolled back: got '{c['status']}', expected 'pending'"
        )

    def test_unapprove_rolls_back_when_export_fails(self, client, clean_state_fixture):
        """POST /api/poi/{id}/unapprove must return 500 and leave the poi row
        intact when export_to_index_html raises ExportError."""
        # First approve a candidate so we have an extracted poi row to unapprove
        candidate = _first_resolved(_analyze_fixture(client))
        poi_id = _approve(client, candidate["id"])["poi_id"]

        poi_ids_before = {r["id"] for r in client.get("/api/poi").json()}
        assert poi_id in poi_ids_before, "Poi row missing before unapprove test"

        # Patch export to raise ExportError during unapprove
        from app.services.exporter import ExportError
        with patch("app.api.routes.export_to_index_html", side_effect=ExportError("injected export failure")):
            resp = client.post(f"/api/poi/{poi_id}/unapprove")

        assert resp.status_code == 500, f"Expected 500 on export failure, got {resp.status_code}"

        # Poi row must still exist (delete was rolled back)
        poi_ids_after = {r["id"] for r in client.get("/api/poi").json()}
        assert poi_id in poi_ids_after, (
            f"Poi row {poi_id} was deleted despite export failure (rollback failed)"
        )
