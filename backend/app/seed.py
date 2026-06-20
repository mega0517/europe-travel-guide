"""Seed SQLite poi table from _workspace/02_poi.json on first run.

Only seeds if the poi table is empty (idempotent).
Curated Korean content becomes managed rows with origin='seed'.
"""
import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.models import Poi

logger = logging.getLogger(__name__)

# Category keys present in 02_poi.json
_CATEGORY_KEYS = ("restaurants", "hotels", "airbnb", "highlights")


def seed_from_poi_json(db: Session, poi_json_path: Path) -> int:
    """Insert all entries from 02_poi.json as origin='seed' poi rows.

    Returns the number of rows inserted (0 if already seeded).
    """
    existing = db.query(Poi).filter(Poi.origin == "seed").count()
    if existing > 0:
        logger.info("seed: poi table already has %d seed rows, skipping", existing)
        return 0

    if not poi_json_path.exists():
        logger.warning("seed: %s not found, skipping seed", poi_json_path)
        return 0

    with open(poi_json_path, encoding="utf-8") as fh:
        data: dict = json.load(fh)

    inserted = 0
    for stop_id, city_data in data.items():
        for category in _CATEGORY_KEYS:
            entries = city_data.get(category, [])
            for entry in entries:
                if category == "highlights":
                    # highlights are bare strings
                    name = entry if isinstance(entry, str) else str(entry)
                    row = Poi(
                        stop_id=stop_id,
                        category=category,
                        name=name,
                        origin="seed",
                    )
                else:
                    row = Poi(
                        stop_id=stop_id,
                        category=category,
                        name=entry.get("name", ""),
                        note=entry.get("note"),
                        price=entry.get("price"),
                        cuisine=entry.get("cuisine"),
                        parking=entry.get("parking"),
                        area=entry.get("area"),
                        origin="seed",
                    )
                db.add(row)
                inserted += 1

    db.commit()
    logger.info("seed: inserted %d poi rows from %s", inserted, poi_json_path)
    return inserted
