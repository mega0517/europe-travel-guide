"""API routes: /api/health, /api/analyze, /api/poi/approve, /api/poi/{id}/unapprove, /api/candidates, /api/poi."""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Poi, PoiCandidate
from app.schemas import (
    HealthResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    ApproveRequest,
    ApproveResponse,
    UnapproveResponse,
    CandidateOut,
    PoiOut,
)
from app.services.exporter import ExportError, export_to_index_html
from app.services.fetcher import fetch_url
from app.services.extractor import extract_candidates

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:
        logger.error("health check db error: %s", exc)
        db_status = "error"
    return HealthResponse(status="ok", db=db_status)


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest, db: Session = Depends(get_db)):
    """Fetch URL, run LLM extraction, persist candidates."""
    source, raw_text = fetch_url(req.url, db)
    candidates, counts = extract_candidates(raw_text, source.id, db)
    # Serialise before commit while objects are still in session
    source_id = source.id
    candidates_out = [CandidateOut.model_validate(c) for c in candidates]
    db.commit()
    return AnalyzeResponse(
        source_id=source_id,
        candidates=candidates_out,
        counts=counts,
    )


@router.post("/poi/approve", response_model=ApproveResponse)
def approve_poi(req: ApproveRequest, db: Session = Depends(get_db)):
    candidate = db.get(PoiCandidate, req.candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if candidate.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Candidate status is '{candidate.status}', expected 'pending'",
        )
    if not candidate.resolved_stop_id:
        raise HTTPException(status_code=400, detail="Candidate has no resolved_stop_id (unresolved city)")

    # Dedupe: same stop_id + category + name already approved?
    existing_poi = (
        db.query(Poi)
        .filter(
            Poi.stop_id == candidate.resolved_stop_id,
            Poi.category == candidate.category,
            Poi.name == candidate.name,
        )
        .first()
    )
    if existing_poi:
        candidate.status = "approved"
        db.commit()
        return ApproveResponse(
            poi_id=existing_poi.id,
            stop_id=existing_poi.stop_id,
            category=existing_poi.category,
            name=existing_poi.name,
        )

    poi = Poi(
        candidate_id=candidate.id,
        stop_id=candidate.resolved_stop_id,
        category=candidate.category,
        name=candidate.name,
        note=candidate.note,
        price=candidate.price,
        cuisine=candidate.cuisine,
        parking=candidate.parking,
        area=candidate.area,
        origin="extracted",
    )
    db.add(poi)
    candidate.status = "approved"
    db.flush()

    # Export — if it fails, roll back the entire transaction (no orphan poi row)
    try:
        export_to_index_html(db)
    except ExportError as exc:
        db.rollback()
        logger.error("export failed during approve, transaction rolled back: %s", exc)
        raise HTTPException(status_code=500, detail=f"Export failed: {exc}") from exc

    db.commit()
    logger.info("approved candidate %d -> poi %d (%s/%s)", candidate.id, poi.id, poi.stop_id, poi.name)
    return ApproveResponse(poi_id=poi.id, stop_id=poi.stop_id, category=poi.category, name=poi.name)


@router.post("/poi/{poi_id}/unapprove", response_model=UnapproveResponse)
def unapprove_poi(poi_id: int, db: Session = Depends(get_db)):
    poi = db.get(Poi, poi_id)
    if not poi:
        raise HTTPException(status_code=404, detail="POI not found")
    if poi.origin != "extracted":
        raise HTTPException(status_code=400, detail="Only extracted POIs can be unapproved")

    candidate = poi.candidate
    db.delete(poi)
    if candidate:
        candidate.status = "pending"
        cid = candidate.id
    else:
        cid = None

    # Export — if it fails, roll back (poi row stays, candidate stays approved)
    try:
        export_to_index_html(db)
    except ExportError as exc:
        db.rollback()
        logger.error("export failed during unapprove, transaction rolled back: %s", exc)
        raise HTTPException(status_code=500, detail=f"Export failed: {exc}") from exc

    db.commit()
    logger.info("unapproved poi %d (candidate %s)", poi_id, cid)
    return UnapproveResponse(candidate_id=cid, status="pending")


@router.get("/candidates", response_model=List[CandidateOut])
def list_candidates(db: Session = Depends(get_db)):
    rows = db.query(PoiCandidate).order_by(PoiCandidate.id.desc()).all()
    return [CandidateOut.model_validate(r) for r in rows]


@router.get("/poi", response_model=List[PoiOut])
def list_poi(db: Session = Depends(get_db)):
    rows = db.query(Poi).order_by(Poi.stop_id, Poi.category, Poi.id).all()
    return [PoiOut.model_validate(r) for r in rows]
