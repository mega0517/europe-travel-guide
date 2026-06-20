"""Deterministic unit tests for services/resolver.py (task #3).

Covers:
- All 11 stop ids resolve from at least one English, one Korean, and one
  native-language alias.
- Case-insensitivity and whitespace tolerance.
- "밀라노"/"Milano" → "milan" (spec-required example).
- Unknown inputs → None (unresolved bucket, never silently dropped).
- budapest vs budapest_end policy.
- Empty / whitespace input → None.
- resolve_city_strict raises ValueError on unresolved input.
"""

from __future__ import annotations

import pytest

from app.services.resolver import VALID_STOP_IDS, resolve_city, resolve_city_strict


# ---------------------------------------------------------------------------
# All 11 stop ids must be reachable
# ---------------------------------------------------------------------------

ALL_STOP_IDS = {
    "budapest",
    "hallstatt",
    "salzburg",
    "feldkirch",
    "lucerne",
    "jungfraujoch",
    "interlaken",
    "zermatt",
    "milan",
    "bled",
    "budapest_end",
}


def test_valid_stop_ids_complete():
    assert ALL_STOP_IDS == VALID_STOP_IDS, (
        f"VALID_STOP_IDS mismatch. Extra: {VALID_STOP_IDS - ALL_STOP_IDS}, "
        f"Missing: {ALL_STOP_IDS - VALID_STOP_IDS}"
    )


# ---------------------------------------------------------------------------
# Per-city: English + Korean + native alias
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("city_raw, expected", [
    # budapest
    ("budapest", "budapest"),
    ("Budapest", "budapest"),
    ("부다페스트", "budapest"),
    ("buda", "budapest"),

    # budapest_end
    ("budapest_end", "budapest_end"),
    ("Budapest_End", "budapest_end"),
    ("부다페스트 도착", "budapest_end"),
    ("budapest end", "budapest_end"),

    # hallstatt
    ("hallstatt", "hallstatt"),
    ("Hallstatt", "hallstatt"),
    ("할슈타트", "hallstatt"),
    ("Hallstadt", "hallstatt"),

    # salzburg
    ("salzburg", "salzburg"),
    ("Salzburg", "salzburg"),
    ("잘츠부르크", "salzburg"),
    ("잘쯔부르크", "salzburg"),

    # feldkirch
    ("feldkirch", "feldkirch"),
    ("Feldkirch", "feldkirch"),
    ("펠트키르히", "feldkirch"),

    # lucerne
    ("lucerne", "lucerne"),
    ("Lucerne", "lucerne"),
    ("루체른", "lucerne"),
    ("Luzern", "lucerne"),
    ("luzern", "lucerne"),

    # jungfraujoch
    ("jungfraujoch", "jungfraujoch"),
    ("Jungfraujoch", "jungfraujoch"),
    ("융프라우요흐", "jungfraujoch"),
    ("융프라우", "jungfraujoch"),
    ("jungfrau", "jungfraujoch"),
    ("top of europe", "jungfraujoch"),

    # interlaken
    ("interlaken", "interlaken"),
    ("Interlaken", "interlaken"),
    ("인터라켄", "interlaken"),

    # zermatt
    ("zermatt", "zermatt"),
    ("Zermatt", "zermatt"),
    ("체르마트", "zermatt"),
    ("마터호른", "zermatt"),
    ("matterhorn", "zermatt"),

    # milan — spec-required examples
    ("밀라노", "milan"),
    ("Milano", "milan"),
    ("milan", "milan"),
    ("Milan", "milan"),

    # bled
    ("bled", "bled"),
    ("Bled", "bled"),
    ("블레드", "bled"),
    ("lake bled", "bled"),
    ("블레드 호수", "bled"),
])
def test_resolve_city_known(city_raw, expected):
    assert resolve_city(city_raw) == expected, (
        f"resolve_city({city_raw!r}) expected {expected!r}"
    )


# ---------------------------------------------------------------------------
# Unknown inputs → None (unresolved bucket, never silently dropped)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("city_raw", [
    "xyz",
    "Paris",
    "파리",
    "unknown city",
    "Rome",
    "로마",
    "Vienna",
    "빈",
    "unknown",
    "???",
])
def test_resolve_city_unknown_returns_none(city_raw):
    result = resolve_city(city_raw)
    assert result is None, (
        f"resolve_city({city_raw!r}) should return None (unresolved), got {result!r}"
    )


# ---------------------------------------------------------------------------
# Edge cases: empty / whitespace
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("city_raw", ["", "   ", "\t", "\n"])
def test_resolve_city_empty_returns_none(city_raw):
    assert resolve_city(city_raw) is None


# ---------------------------------------------------------------------------
# Whitespace tolerance
# ---------------------------------------------------------------------------

def test_resolve_city_leading_trailing_whitespace():
    assert resolve_city("  milan  ") == "milan"
    assert resolve_city("\t밀라노\n") == "milan"
    assert resolve_city("  Budapest  ") == "budapest"


# ---------------------------------------------------------------------------
# budapest vs budapest_end policy
# ---------------------------------------------------------------------------

def test_budapest_default_is_not_budapest_end():
    """General "budapest" must resolve to "budapest", not "budapest_end"."""
    assert resolve_city("budapest") == "budapest"
    assert resolve_city("부다페스트") == "budapest"


def test_budapest_end_is_distinct():
    """Return-day alias must resolve to "budapest_end", not "budapest"."""
    assert resolve_city("budapest_end") == "budapest_end"
    assert resolve_city("부다페스트 도착") == "budapest_end"
    assert resolve_city("budapest end") == "budapest_end"


def test_budapest_and_budapest_end_are_different_stops():
    assert resolve_city("budapest") != resolve_city("budapest_end")


# ---------------------------------------------------------------------------
# resolve_city_strict
# ---------------------------------------------------------------------------

def test_resolve_city_strict_known():
    assert resolve_city_strict("밀라노") == "milan"
    assert resolve_city_strict("Hallstatt") == "hallstatt"


def test_resolve_city_strict_unknown_raises():
    with pytest.raises(ValueError, match="Cannot resolve city"):
        resolve_city_strict("Narnia")


def test_resolve_city_strict_empty_raises():
    with pytest.raises(ValueError):
        resolve_city_strict("")
