from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Enum
)
from sqlalchemy.orm import DeclarativeBase, relationship
import enum


class Base(DeclarativeBase):
    pass


class ExternalSource(Base):
    __tablename__ = "external_source"

    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True, nullable=False)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    raw_text = Column(Text)
    status = Column(String, default="fetched")

    candidates = relationship("PoiCandidate", back_populates="source")


class CandidateStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    unresolved = "unresolved"


class PoiCandidate(Base):
    __tablename__ = "poi_candidate"

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("external_source.id"), nullable=True)
    name = Column(String, nullable=False)
    city_raw = Column(String)
    resolved_stop_id = Column(String, nullable=True)
    category = Column(
        Enum("restaurants", "hotels", "airbnb", "highlights", name="category_enum"),
        nullable=False,
    )
    note = Column(Text)
    price = Column(String)
    cuisine = Column(String)
    parking = Column(String)
    area = Column(String)
    status = Column(
        Enum("pending", "approved", "rejected", "unresolved", name="candidate_status_enum"),
        default="pending",
        nullable=False,
    )
    created_at = Column(DateTime, default=datetime.utcnow)

    source = relationship("ExternalSource", back_populates="candidates")
    poi = relationship("Poi", back_populates="candidate", uselist=False)


class PoiOrigin(str, enum.Enum):
    seed = "seed"
    extracted = "extracted"


class Poi(Base):
    __tablename__ = "poi"

    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("poi_candidate.id"), nullable=True)
    stop_id = Column(String, nullable=False)
    category = Column(
        Enum("restaurants", "hotels", "airbnb", "highlights", name="poi_category_enum"),
        nullable=False,
    )
    name = Column(String, nullable=False)
    note = Column(Text)
    price = Column(String)
    cuisine = Column(String)
    parking = Column(String)
    area = Column(String)
    origin = Column(
        Enum("seed", "extracted", name="poi_origin_enum"),
        default="seed",
        nullable=False,
    )
    exported_at = Column(DateTime, nullable=True)

    candidate = relationship("PoiCandidate", back_populates="poi")
