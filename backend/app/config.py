import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the backend directory
_backend_dir = Path(__file__).parent.parent
load_dotenv(_backend_dir / ".env")

ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")

# Fail fast at import time if key is missing
if not ANTHROPIC_API_KEY:
    raise RuntimeError(
        "ANTHROPIC_API_KEY is not set. Copy backend/.env.example to backend/.env and fill it in."
    )

DATABASE_URL: str = f"sqlite:///{_backend_dir / 'europe.db'}"
POI_JSON_PATH: Path = _backend_dir.parent / "_workspace" / "02_poi.json"
INDEX_HTML_PATH: Path = _backend_dir.parent / "index.html"
