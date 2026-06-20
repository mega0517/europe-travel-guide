"""Exporter: regenerate inline POI block in index.html with sentinel markers.

Algorithm on every call:
1. Read approved POIs from SQLite (source of truth).
2. Load current POI dict from between sentinels in index.html (or from the
   bare `const POI = {...};` block on first run before sentinels exist).
3. Preserve-merge: for each stop_id, keep all existing hand-curated entries;
   append extracted POIs that are not already present (dedupe by name).
4. Back up index.html to backend/.backups/ (capped at _MAX_BACKUPS) before mutating.
5. Atomic write (temp file + rename) with ensure_ascii=False.
6. Sync 02_poi.json to the same merged dict.
7. Validate the written files; restore from backup on any failure so the two
   projections never diverge (plan R8).

Category shapes (per §3.3):
  restaurants → {name, note?, price?, cuisine?}
  hotels      → {name, note?, price?, parking?}
  airbnb      → {name, note?, price?, area?}
  highlights  → bare string (name only)

Sentinels inserted on first run:
  /* POI_BLOCK_START */
  const POI = {...};
  /* POI_BLOCK_END */

Failure contract:
  export_to_index_html RAISES ExportError on any failure so callers can
  roll back their DB transaction.  It never swallows errors silently.
"""

import json
import logging
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.config import INDEX_HTML_PATH, POI_JSON_PATH
from app.db.models import Poi

logger = logging.getLogger(__name__)

POI_BLOCK_START = "/* POI_BLOCK_START */"
POI_BLOCK_END = "/* POI_BLOCK_END */"

# Directory for timestamped backups — backend/.backups/ alongside app/
_BACKUP_DIR = Path(INDEX_HTML_PATH).parent / "backend" / ".backups"
_MAX_BACKUPS = 20

# Regex that matches the sentinel-wrapped block (DOTALL)
_SENTINEL_RE = re.compile(
    r"/\* POI_BLOCK_START \*/(.*?)/\* POI_BLOCK_END \*/",
    re.DOTALL,
)

# Regex for the bare `const POI = {...};` block (first-run, no sentinels).
# Uses a greedy match anchored to `};` so nested objects are not truncated.
_BARE_RE = re.compile(
    r"(const\s+POI\s*=\s*)(\{.*\})\s*;",
    re.DOTALL,
)


class ExportError(RuntimeError):
    """Raised when export_to_index_html cannot complete safely.

    Callers should roll back their DB transaction on receipt.
    """


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_current_poi(html: str) -> Dict[str, Any]:
    """Extract the current POI dict from html (sentinel or bare).

    Raises ExportError on parse failure — never returns a partial result.
    """
    m = _SENTINEL_RE.search(html)
    if m:
        block_text = m.group(1)
    else:
        m = _BARE_RE.search(html)
        if not m:
            raise ExportError(
                "Could not locate `const POI = {...};` block in index.html"
            )
        block_text = m.group(0)  # full `const POI = {...};`

    # Extract the JSON object from `const POI = {...};`
    obj_m = re.search(r"const\s+POI\s*=\s*(\{.*\})\s*;", block_text, re.DOTALL)
    if not obj_m:
        raise ExportError("Could not parse JSON object from POI block")

    try:
        return json.loads(obj_m.group(1))
    except json.JSONDecodeError as exc:
        raise ExportError(f"JSON parse failed for POI block: {exc}") from exc


def _poi_row_to_dict(poi: Poi) -> Dict[str, Any]:
    """Convert a SQLite Poi ORM row to the category-appropriate dict shape."""
    cat = poi.category
    if cat == "restaurants":
        d: Dict[str, Any] = {"name": poi.name}
        if poi.note:
            d["note"] = poi.note
        if poi.price:
            d["price"] = poi.price
        if poi.cuisine:
            d["cuisine"] = poi.cuisine
        return d
    elif cat == "hotels":
        d = {"name": poi.name}
        if poi.note:
            d["note"] = poi.note
        if poi.price:
            d["price"] = poi.price
        if poi.parking:
            d["parking"] = poi.parking
        return d
    elif cat == "airbnb":
        d = {"name": poi.name}
        if poi.note:
            d["note"] = poi.note
        if poi.price:
            d["price"] = poi.price
        if poi.area:
            d["area"] = poi.area
        return d
    else:
        # highlights → bare string
        return poi.name  # type: ignore[return-value]


def _merge_into_stop(
    stop_dict: Dict[str, Any],
    category: str,
    new_entry: Any,
) -> bool:
    """Append new_entry to stop_dict[category] if not already present.

    Returns True if a new entry was added, False if it was a duplicate.
    Highlights are stored as bare strings; others as dicts with a 'name' key.
    """
    bucket: List[Any] = stop_dict.setdefault(category, [])

    if category == "highlights":
        name = new_entry if isinstance(new_entry, str) else new_entry.get("name", "")
        if any((e if isinstance(e, str) else e.get("name", "")) == name for e in bucket):
            return False
        bucket.append(name)
    else:
        name = new_entry.get("name", "") if isinstance(new_entry, dict) else str(new_entry)
        if any(
            (e.get("name", "") if isinstance(e, dict) else str(e)) == name
            for e in bucket
        ):
            return False
        bucket.append(new_entry)
    return True


def _atomic_write(path: Path, text: str) -> None:
    """Write text to path atomically via a temp file + rename."""
    dir_ = path.parent
    fd, tmp = tempfile.mkstemp(dir=dir_, prefix=".tmp_", suffix=path.suffix)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        shutil.move(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _backup_index_html(html_path: Path) -> Path:
    """Copy index.html to .backups/index.html.YYYYMMDD_HHMMSS.bak.

    Backup dir is backend/.backups/ (not the project root).
    Old backups beyond _MAX_BACKUPS are pruned.
    Returns the backup path.
    """
    _BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    # Human-readable local timestamp for the filename
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = _BACKUP_DIR / f"index.html.{ts}.bak"
    shutil.copy2(html_path, bak)
    logger.info("backed up index.html → %s", bak)

    # Cap retention
    backups = sorted(_BACKUP_DIR.glob("index.html.*.bak"))
    for old in backups[:-_MAX_BACKUPS]:
        try:
            old.unlink()
        except OSError:
            pass

    return bak


def _splice_sentinel_block(html: str, new_poi_json: str) -> str:
    """Replace or insert the sentinel-wrapped block in html.

    On first run (no sentinels), wraps the existing bare `const POI = {...};`.
    On subsequent runs, splices between existing sentinels.
    Raises ExportError if neither pattern is found.
    """
    new_block = (
        f"{POI_BLOCK_START}\nconst POI = {new_poi_json};\n{POI_BLOCK_END}"
    )

    if _SENTINEL_RE.search(html):
        # Sentinels exist — splice between them
        return _SENTINEL_RE.sub(new_block, html, count=1)
    else:
        # First run — wrap the bare const POI = {...}; with sentinels
        result, n = _BARE_RE.subn(lambda _m: new_block, html, count=1)
        if n == 0:
            raise ExportError(
                "Could not locate `const POI = {...};` for sentinel insertion"
            )
        return result


def _validate_written_html(path: Path) -> None:
    """Verify that the written index.html still contains a parseable POI block.

    Raises ExportError if the file is unreadable or the block is gone.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ExportError(f"Could not read written index.html for validation: {exc}") from exc
    _load_current_poi(text)  # raises ExportError on parse failure


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def export_to_index_html(db: Session) -> None:
    """Merge approved SQLite POIs into index.html inline block + 02_poi.json.

    Safe to call multiple times — idempotent by name-based dedupe.

    Raises ExportError on any failure so the caller can roll back its DB
    transaction.  On write failure, attempts to restore from the timestamped
    backup so index.html and 02_poi.json never diverge.
    """
    index_path = Path(INDEX_HTML_PATH)
    poi_json_path = Path(POI_JSON_PATH)

    if not index_path.exists():
        raise ExportError(f"index.html not found at {index_path}")

    # 1. Load approved POIs from SQLite
    approved_pois: List[Poi] = (
        db.query(Poi)
        .filter(Poi.stop_id.isnot(None))
        .order_by(Poi.stop_id, Poi.category, Poi.id)
        .all()
    )
    logger.info("exporting %d approved POIs to index.html", len(approved_pois))

    # 2. Read current index.html and extract POI dict (raises ExportError on failure)
    html = index_path.read_text(encoding="utf-8")
    poi_dict = _load_current_poi(html)

    # 3. Preserve-merge: append extracted POIs not already present
    added = 0
    for poi in approved_pois:
        stop_id = poi.stop_id
        if stop_id not in poi_dict:
            poi_dict[stop_id] = {}
        entry = _poi_row_to_dict(poi)
        if _merge_into_stop(poi_dict[stop_id], poi.category, entry):
            added += 1

    logger.info("preserve-merge: %d new entries added", added)

    # 4. Serialize merged POI dict (ensure_ascii=False to preserve Korean)
    new_poi_json = json.dumps(poi_dict, ensure_ascii=False, indent=2)

    # 5. Splice sentinel block (raises ExportError on failure)
    new_html = _splice_sentinel_block(html, new_poi_json)

    # 6. Back up index.html before any mutation (raises on copy failure)
    try:
        bak_path = _backup_index_html(index_path)
    except OSError as exc:
        raise ExportError(f"Could not back up index.html: {exc}") from exc

    # 7. Atomic-write index.html, validate, then write 02_poi.json.
    #    On any failure: restore from backup so the two projections stay in sync.
    index_written = False
    try:
        _atomic_write(index_path, new_html)
        index_written = True

        # Validate the written file (R8)
        _validate_written_html(index_path)

        # Write 02_poi.json only after index.html is confirmed valid
        _atomic_write(poi_json_path, new_poi_json + "\n")

        logger.info(
            "export complete — index.html and 02_poi.json updated (UTC %s)",
            datetime.now(timezone.utc).isoformat(),
        )
    except Exception as exc:
        # Restore index.html from backup so it stays in sync with 02_poi.json
        if index_written and bak_path.exists():
            try:
                shutil.copy2(bak_path, index_path)
                logger.warning("restored index.html from backup after export failure")
            except OSError as restore_exc:
                logger.error("CRITICAL: could not restore index.html: %s", restore_exc)
        raise ExportError(f"Export failed and was rolled back: {exc}") from exc
