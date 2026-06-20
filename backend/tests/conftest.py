"""pytest configuration — adds the backend root to sys.path so `app.*` imports work."""
import sys
from pathlib import Path

# backend/ directory (parent of tests/)
sys.path.insert(0, str(Path(__file__).parent.parent))
