"""HTTP fetcher with unsupported-source guard.

Returns (ExternalSource, raw_text) — caches raw_text in DB so repeat
calls to the same URL skip the network round-trip.

Unsupported-source guard: if the visible text-to-HTML ratio is below
TEXT_DENSITY_MIN the page is almost certainly a JS-rendered SPA or
anti-bot wall; we raise HTTPException(422) rather than wasting an LLM call.
"""
import ipaddress
import logging
import re
import socket
from typing import Tuple
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models import ExternalSource

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,ko;q=0.8",
}
_TIMEOUT = 20.0          # seconds
_MAX_HTML_BYTES = 2_000_000  # 2 MB — truncate before sending to LLM
TEXT_DENSITY_MIN = 0.03  # visible text / raw HTML length ratio threshold


_ALLOWED_SCHEMES = {"http", "https"}
_MAX_REDIRECT_HOPS = 5


def _validate_url_safety(url: str) -> None:
    """Reject non-http/https schemes and private/loopback/reserved IPs (SSRF guard)."""
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise HTTPException(status_code=400, detail=f"URL scheme '{parsed.scheme}' not allowed. Use http or https.")

    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=400, detail="URL has no hostname.")

    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        # DNS resolution failure — httpx.get will also fail; not an SSRF risk
        return

    for _family, _type, _proto, _canonname, sockaddr in addr_infos:
        raw_ip = sockaddr[0]
        try:
            ip = ipaddress.ip_address(raw_ip)
        except ValueError:
            continue
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise HTTPException(
                status_code=400,
                detail=f"URL resolves to a non-public IP address ({ip}) — request blocked.",
            )


def _strip_tags(html: str) -> str:
    """Naive tag stripper — good enough for density heuristic."""
    no_tags = re.sub(r"<[^>]+>", " ", html)
    no_ws = re.sub(r"\s+", " ", no_tags)
    return no_ws.strip()


def _check_text_density(html: str) -> None:
    """Raise 422 if the page looks like a JS-shell or bot-wall."""
    visible = _strip_tags(html)
    ratio = len(visible) / max(len(html), 1)
    if ratio < TEXT_DENSITY_MIN:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Page appears to be JS-rendered or bot-blocked "
                f"(text density {ratio:.3f} < {TEXT_DENSITY_MIN}). "
                "Please provide a static/server-rendered travel guide URL."
            ),
        )


def fetch_url(url: str, db: Session) -> Tuple[ExternalSource, str]:
    """Fetch *url*, persist to ExternalSource, return (source, raw_text).

    Uses DB cache: if the URL was already fetched, returns the cached row.
    """
    # --- SSRF guard: validate before any network contact ---
    _validate_url_safety(url)

    # --- cache hit ---
    existing = db.query(ExternalSource).filter(ExternalSource.url == url).first()
    if existing and existing.raw_text:
        logger.info("cache hit for url=%s source_id=%d", url, existing.id)
        return existing, existing.raw_text

    # --- network fetch with per-hop SSRF re-validation ---
    logger.info("fetching url=%s", url)
    try:
        resp = httpx.get(
            url,
            headers=_HEADERS,
            timeout=_TIMEOUT,
            follow_redirects=False,
        )
        hops = 0
        while getattr(resp, "is_redirect", False) and hops < _MAX_REDIRECT_HOPS:
            redirect_url = resp.headers.get("location", "")
            _validate_url_safety(redirect_url)
            resp = httpx.get(
                redirect_url,
                headers=_HEADERS,
                timeout=_TIMEOUT,
                follow_redirects=False,
            )
            hops += 1
        if getattr(resp, "is_redirect", False):
            raise HTTPException(status_code=502, detail="Too many redirects fetching URL.")
        resp.raise_for_status()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail=f"Timeout fetching URL: {url}")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Upstream HTTP {exc.response.status_code} for URL: {url}",
        )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Network error fetching URL: {exc}")

    html = resp.text
    if len(html) > _MAX_HTML_BYTES:
        html = html[:_MAX_HTML_BYTES]

    _check_text_density(html)

    # --- strip to readable text for LLM ---
    raw_text = _strip_tags(html)

    # --- persist ---
    if existing:
        existing.raw_text = raw_text
        existing.status = "fetched"
        source = existing
    else:
        source = ExternalSource(url=url, raw_text=raw_text, status="fetched")
        db.add(source)

    db.flush()
    logger.info("fetched and persisted source_id=%d url=%s text_len=%d", source.id, url, len(raw_text))
    return source, raw_text
