import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///./fpl_test.db")
os.environ.setdefault("ADMIN_API_TOKEN", "test-token")

from backend.app.core.settings import get_settings
from backend.app.db.models import reset_engine

get_settings.cache_clear()
reset_engine()
