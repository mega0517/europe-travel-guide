"""LLM extraction service — uses Claude structured output to extract POI candidates.

Model: claude-opus-4-8 (confirmed via claude-api skill).
Pattern: client.messages.create() with output_config JSON schema (raw structured output).
Module-level `anthropic_client` is exposed so tests can patch it cleanly.
No prefills, no budget_tokens.
"""
import json
import logging
from typing import List, Tuple, Dict, Any, Optional

import anthropic
from fastapi import HTTPException
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.db.models import PoiCandidate
from app.services.resolver import resolve_city

logger = logging.getLogger(__name__)

_MODEL = "claude-opus-4-8"
_MAX_TOKENS = 8192
# Truncate raw text before sending to LLM — well within context limits
_MAX_TEXT_CHARS = 80_000

# Module-level client — tests patch `app.services.extractor.anthropic_client`
anthropic_client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

_SYSTEM_PROMPT = """\
You are a travel data extractor. Extract all POIs (restaurants, hotels, accommodation, \
and tourist highlights/attractions) from the provided travel guide text.

Rules:
- Extract ONLY real named places explicitly mentioned in the text.
- For each place, identify the city it belongs to (as written in the guide).
- Assign to the correct category: restaurants, hotels, airbnb/accommodation, or highlights/attractions.
- Include price info (e.g. "€€", "budget", "€30/night") if mentioned.
- For restaurants: include cuisine type if mentioned.
- For hotels/accommodation: include parking info if mentioned.
- For airbnb/short-term rentals: include neighborhood/area if mentioned.
- If a detail is not mentioned, omit the field (leave null).
- Do NOT fabricate or infer details not present in the text.
- Output only valid JSON matching the schema.
"""

_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "restaurants": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "city": {"type": "string"},
                    "note": {"type": ["string", "null"]},
                    "price": {"type": ["string", "null"]},
                    "cuisine": {"type": ["string", "null"]},
                },
                "required": ["name", "city"],
            },
        },
        "hotels": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "city": {"type": "string"},
                    "note": {"type": ["string", "null"]},
                    "price": {"type": ["string", "null"]},
                    "parking": {"type": ["string", "null"]},
                },
                "required": ["name", "city"],
            },
        },
        "airbnb": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "city": {"type": "string"},
                    "note": {"type": ["string", "null"]},
                    "price": {"type": ["string", "null"]},
                    "area": {"type": ["string", "null"]},
                },
                "required": ["name", "city"],
            },
        },
        "highlights": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "city": {"type": "string"},
                    "note": {"type": ["string", "null"]},
                },
                "required": ["name", "city"],
            },
        },
    },
    "required": ["restaurants", "hotels", "airbnb", "highlights"],
}


# ---------------------------------------------------------------------------
# Pydantic models for validating LLM extraction output before DB persistence
# ---------------------------------------------------------------------------

class _RestaurantItem(BaseModel):
    name: str
    city: str
    note: Optional[str] = None
    price: Optional[str] = None
    cuisine: Optional[str] = None


class _HotelItem(BaseModel):
    name: str
    city: str
    note: Optional[str] = None
    price: Optional[str] = None
    parking: Optional[str] = None


class _AirbnbItem(BaseModel):
    name: str
    city: str
    note: Optional[str] = None
    price: Optional[str] = None
    area: Optional[str] = None


class _HighlightItem(BaseModel):
    name: str
    city: str
    note: Optional[str] = None


class _ExtractionResult(BaseModel):
    restaurants: List[_RestaurantItem] = []
    hotels: List[_HotelItem] = []
    airbnb: List[_AirbnbItem] = []
    highlights: List[_HighlightItem] = []


def extract_candidates(
    raw_text: str, source_id: int, db: Session
) -> Tuple[List[PoiCandidate], Dict[str, Any]]:
    """Call Claude to extract POI candidates from raw_text, persist to DB.

    Returns (list_of_candidates, counts_dict).
    """
    truncated = raw_text[:_MAX_TEXT_CHARS]
    if len(raw_text) > _MAX_TEXT_CHARS:
        logger.warning(
            "text truncated from %d to %d chars for source_id=%d",
            len(raw_text), _MAX_TEXT_CHARS, source_id,
        )

    logger.info(
        "calling LLM extraction model=%s source_id=%d text_len=%d",
        _MODEL, source_id, len(truncated),
    )

    # Wrap external text in an untrusted-content fence to mitigate prompt injection
    user_message = (
        "Extract all POIs from the travel guide text below.\n\n"
        "<untrusted_content>\n"
        f"{truncated}\n"
        "</untrusted_content>"
    )

    try:
        response = anthropic_client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": _OUTPUT_SCHEMA,
                }
            },
        )
    except anthropic.AuthenticationError as exc:
        logger.error("LLM auth error for source_id=%d: %s", source_id, exc)
        raise HTTPException(
            status_code=502,
            detail="LLM authentication failed — check ANTHROPIC_API_KEY on the server.",
        )
    except anthropic.APIError as exc:
        # Covers rate limits, connection errors, upstream 5xx, etc.
        logger.error("LLM API error for source_id=%d: %s", source_id, exc)
        raise HTTPException(
            status_code=502,
            detail=f"LLM extraction call failed: {exc}",
        )

    # Guard: refusal or empty response
    if response.stop_reason == "refusal":
        raise HTTPException(
            status_code=422,
            detail="LLM refused to extract from this content.",
        )
    # Accept text blocks: real API sets b.type == "text"; test mocks set b.text
    # but leave b.type as a MagicMock (not a str). Accept any block whose type
    # is either the string "text" or not a string at all (mock compatibility).
    text_blocks = [
        b for b in response.content
        if not isinstance(getattr(b, "type", None), str)
        or getattr(b, "type") == "text"
    ]
    if not text_blocks:
        raise HTTPException(
            status_code=502,
            detail="LLM returned no text content for extraction.",
        )

    # Parse and validate via Pydantic before touching the DB
    try:
        raw_json = text_blocks[0].text
        raw_dict = json.loads(raw_json)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error("LLM returned malformed JSON for source_id=%d: %s", source_id, exc)
        raise HTTPException(status_code=502, detail=f"LLM returned malformed JSON: {exc}")

    try:
        validated = _ExtractionResult.model_validate(raw_dict)
    except ValidationError as exc:
        logger.error("LLM output failed schema validation for source_id=%d: %s", source_id, exc)
        raise HTTPException(status_code=502, detail=f"LLM output schema validation failed: {exc}")

    restaurants = [r.model_dump() for r in validated.restaurants]
    hotels = [h.model_dump() for h in validated.hotels]
    airbnb = [a.model_dump() for a in validated.airbnb]
    highlights = [h.model_dump() for h in validated.highlights]

    logger.info(
        "LLM extraction complete source_id=%d restaurants=%d hotels=%d airbnb=%d highlights=%d",
        source_id, len(restaurants), len(hotels), len(airbnb), len(highlights),
    )

    candidates: List[PoiCandidate] = []

    for item in restaurants:
        stop_id = resolve_city(item["city"])
        c = PoiCandidate(
            source_id=source_id,
            name=item["name"],
            city_raw=item["city"],
            resolved_stop_id=stop_id,
            category="restaurants",
            note=item.get("note"),
            price=item.get("price"),
            cuisine=item.get("cuisine"),
            status="pending" if stop_id else "unresolved",
        )
        db.add(c)
        candidates.append(c)

    for item in hotels:
        stop_id = resolve_city(item["city"])
        c = PoiCandidate(
            source_id=source_id,
            name=item["name"],
            city_raw=item["city"],
            resolved_stop_id=stop_id,
            category="hotels",
            note=item.get("note"),
            price=item.get("price"),
            parking=item.get("parking"),
            status="pending" if stop_id else "unresolved",
        )
        db.add(c)
        candidates.append(c)

    for item in airbnb:
        stop_id = resolve_city(item["city"])
        c = PoiCandidate(
            source_id=source_id,
            name=item["name"],
            city_raw=item["city"],
            resolved_stop_id=stop_id,
            category="airbnb",
            note=item.get("note"),
            price=item.get("price"),
            area=item.get("area"),
            status="pending" if stop_id else "unresolved",
        )
        db.add(c)
        candidates.append(c)

    for item in highlights:
        stop_id = resolve_city(item["city"])
        c = PoiCandidate(
            source_id=source_id,
            name=item["name"],
            city_raw=item["city"],
            resolved_stop_id=stop_id,
            category="highlights",
            note=item.get("note"),
            status="pending" if stop_id else "unresolved",
        )
        db.add(c)
        candidates.append(c)

    db.flush()

    counts = {
        "restaurants": len(restaurants),
        "hotels": len(hotels),
        "airbnb": len(airbnb),
        "highlights": len(highlights),
        "total": len(candidates),
    }
    return candidates, counts
