"""Resilience helpers: cached external data and safe fallbacks."""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Callable

CACHE_DIR = Path(os.getenv("CYCLONESHIELD_CACHE_DIR", ".cycloneshield_cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_TTL_SECONDS = int(os.getenv("CYCLONESHIELD_CACHE_TTL", "21600"))


def _key(prefix: str, payload: Any) -> Path:
    raw = json.dumps(payload, sort_keys=True, default=str).encode()
    digest = hashlib.sha256(raw).hexdigest()[:24]
    return CACHE_DIR / f"{prefix}_{digest}.json"


def get_cached(prefix: str, payload: Any, allow_stale: bool = True):
    path = _key(prefix, payload)
    if not path.exists():
        return None, None
    try:
        item = json.loads(path.read_text(encoding="utf-8"))
        age = time.time() - float(item.get("saved_at", 0))
        if age <= CACHE_TTL_SECONDS or allow_stale:
            return item.get("data"), age
    except Exception:
        return None, None
    return None, None


def set_cached(prefix: str, payload: Any, data: Any):
    path = _key(prefix, payload)
    path.write_text(
        json.dumps({"saved_at": time.time(), "data": data}, default=str),
        encoding="utf-8",
    )


def cached_call(prefix: str, payload: Any, loader: Callable[[], Any]):
    try:
        data = loader()
        set_cached(prefix, payload, data)
        return data, {"source": "live", "cache_age_seconds": 0}
    except Exception as exc:
        cached, age = get_cached(prefix, payload, allow_stale=True)
        if cached is not None:
            return cached, {"source": "cache", "cache_age_seconds": age, "error": str(exc)}
        raise
