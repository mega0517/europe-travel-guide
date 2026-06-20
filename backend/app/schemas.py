from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, field_validator
from datetime import datetime


class HealthResponse(BaseModel):
    status: str
    db: str


# --- Candidate schemas ---

class CandidateOut(BaseModel):
    id: int
    name: str
    city_raw: Optional[str]
    resolved_stop_id: Optional[str]
    category: str
    note: Optional[str]
    price: Optional[str]
    cuisine: Optional[str]
    parking: Optional[str]
    area: Optional[str]
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalyzeRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def url_must_be_http_or_https(cls, v: str) -> str:
        from urllib.parse import urlparse
        scheme = urlparse(v).scheme
        if scheme not in {"http", "https"}:
            raise ValueError(f"URL scheme '{scheme}' not allowed. Use http or https.")
        return v


class AnalyzeResponse(BaseModel):
    source_id: int
    candidates: List[CandidateOut]
    counts: dict


# --- Approve / unapprove ---

class ApproveRequest(BaseModel):
    candidate_id: int


class ApproveResponse(BaseModel):
    poi_id: int
    stop_id: str
    category: str
    name: str


class UnapproveResponse(BaseModel):
    candidate_id: Optional[int]
    status: str


# --- POI schemas ---

class PoiOut(BaseModel):
    id: int
    candidate_id: Optional[int]
    stop_id: str
    category: str
    name: str
    note: Optional[str]
    price: Optional[str]
    cuisine: Optional[str]
    parking: Optional[str]
    area: Optional[str]
    origin: str
    exported_at: Optional[datetime]

    model_config = {"from_attributes": True}
