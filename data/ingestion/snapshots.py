from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.core.settings import get_settings


def snapshot_path(source: str, endpoint: str, captured_at: datetime) -> Path:
    settings = get_settings()
    stamp = captured_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_endpoint = endpoint.strip("/").replace("/", "_") or "root"
    directory = settings.snapshot_dir / source / captured_at.strftime("%Y") / captured_at.strftime("%m")
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{stamp}_{safe_endpoint}.json"


def write_json_snapshot(payload: Any, source: str, endpoint: str, captured_at: datetime | None = None) -> dict:
    captured_at = captured_at or datetime.now(timezone.utc)
    path = snapshot_path(source, endpoint, captured_at)
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
    path.write_text(encoded, encoding="utf-8")
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return {
        "captured_at": captured_at,
        "source": source,
        "endpoint": endpoint,
        "storage_path": str(path),
        "content_hash": digest,
    }
