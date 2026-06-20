"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.logging_conf import configure_logging
from app.db.session import create_tables, SessionLocal
from app.config import POI_JSON_PATH
from app.seed import seed_from_poi_json
from app.api.routes import router

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("startup: creating tables")
    create_tables()
    db = SessionLocal()
    try:
        seed_from_poi_json(db, POI_JSON_PATH)
    finally:
        db.close()
    logger.info("startup: complete")
    yield
    # Shutdown (nothing to clean up for SQLite)


app = FastAPI(title="Europe Travel Guide Analyzer", lifespan=lifespan)
app.include_router(router, prefix="/api")
