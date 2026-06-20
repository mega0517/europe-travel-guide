"""City→stop-id resolver with curated bidirectional alias map.

All 11 stop ids from _workspace/01_route.json are covered:
  budapest, hallstatt, salzburg, feldkirch, lucerne,
  jungfraujoch, interlaken, zermatt, milan, bled, budapest_end

Policy: "budapest" is the default for general Budapest POIs.
        "budapest_end" is reserved for return-day / departure items only —
        callers must pass city_raw="budapest_end" (or a native-language alias
        that maps directly to it) to land in that bucket.

resolve_city(city_raw) → stop_id string  or  None (unresolved)
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Alias map: normalised lowercase input → stop_id
# ---------------------------------------------------------------------------
# Each entry covers: English, Korean (hangul), native-language name, and
# common abbreviations / alternate romanisations.
_ALIAS_MAP: dict[str, str] = {
    # ── budapest (departure / default) ──────────────────────────────────────
    "budapest": "budapest",
    "부다페스트": "budapest",
    "부다페스트 출발": "budapest",
    "부다 페스트": "budapest",
    "bp": "budapest",
    "buda": "budapest",
    "pest": "budapest",

    # ── budapest_end (arrival / return day) ─────────────────────────────────
    "budapest_end": "budapest_end",
    "부다페스트 도착": "budapest_end",
    "부다페스트 귀환": "budapest_end",
    "부다페스트 복귀": "budapest_end",
    "budapest end": "budapest_end",

    # ── hallstatt ────────────────────────────────────────────────────────────
    "hallstatt": "hallstatt",
    "할슈타트": "hallstatt",
    "할쉬타트": "hallstatt",
    "hallstadt": "hallstatt",
    "hall in oberösterreich": "hallstatt",
    "hall in oberosterreich": "hallstatt",

    # ── salzburg ─────────────────────────────────────────────────────────────
    "salzburg": "salzburg",
    "잘츠부르크": "salzburg",
    "잘쯔부르크": "salzburg",
    "salzburg city": "salzburg",
    "city of salzburg": "salzburg",

    # ── feldkirch ────────────────────────────────────────────────────────────
    "feldkirch": "feldkirch",
    "펠트키르히": "feldkirch",
    "펠트 키르히": "feldkirch",

    # ── lucerne ──────────────────────────────────────────────────────────────
    "lucerne": "lucerne",
    "루체른": "lucerne",
    "luzern": "lucerne",
    "루체른 호수": "lucerne",
    "lake lucerne": "lucerne",

    # ── jungfraujoch ─────────────────────────────────────────────────────────
    "jungfraujoch": "jungfraujoch",
    "융프라우요흐": "jungfraujoch",
    "융프라우": "jungfraujoch",
    "jungfrau": "jungfraujoch",
    "jungfrau region": "jungfraujoch",
    "top of europe": "jungfraujoch",

    # ── interlaken ───────────────────────────────────────────────────────────
    "interlaken": "interlaken",
    "인터라켄": "interlaken",
    "인터라킨": "interlaken",
    "interlaken ost": "interlaken",
    "interlaken west": "interlaken",

    # ── zermatt ──────────────────────────────────────────────────────────────
    "zermatt": "zermatt",
    "체르마트": "zermatt",
    "제르마트": "zermatt",
    "matterhorn": "zermatt",
    "마터호른": "zermatt",
    "zermatt matterhorn": "zermatt",
    "체르마트 마터호른": "zermatt",

    # ── milan ────────────────────────────────────────────────────────────────
    "milan": "milan",
    "밀라노": "milan",
    "milano": "milan",
    "milano city": "milan",
    "milan city": "milan",
    "米蘭": "milan",

    # ── bled ─────────────────────────────────────────────────────────────────
    "bled": "bled",
    "블레드": "bled",
    "블레드 호수": "bled",
    "lake bled": "bled",
    "bled lake": "bled",
    "blejsko jezero": "bled",
}

# ---------------------------------------------------------------------------
# Valid stop ids (for reverse lookups / assertions)
# ---------------------------------------------------------------------------
VALID_STOP_IDS: frozenset[str] = frozenset(_ALIAS_MAP.values())


def _normalise(city_raw: str) -> str:
    """Strip whitespace and lowercase for map lookup."""
    return city_raw.strip().lower()


def resolve_city(city_raw: str) -> str | None:
    """Return the stop_id for city_raw, or None if unresolvable.

    Lookup is case-insensitive and whitespace-tolerant.
    An empty or whitespace-only input returns None immediately.

    Examples:
        resolve_city("밀라노")    → "milan"
        resolve_city("Milano")   → "milan"
        resolve_city("Zermatt")  → "zermatt"
        resolve_city("xyz")      → None
    """
    if not city_raw or not city_raw.strip():
        return None
    return _ALIAS_MAP.get(_normalise(city_raw))


def resolve_city_strict(city_raw: str) -> str:
    """Like resolve_city but raises ValueError on unresolved input.

    Useful for contexts where a missing resolution is a hard error.
    """
    stop_id = resolve_city(city_raw)
    if stop_id is None:
        raise ValueError(f"Cannot resolve city to a stop_id: {city_raw!r}")
    return stop_id
