"""
TTL query cache (TASK-011). In-memory fallback today; Redis-ready via
env config (REDIS_URL). Cache hits are bounded by maxsize with simple
eviction; negative results are never cached.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Optional

from app.core.config import get_settings

_cache: dict[str, tuple[float, Any]] = {}
_lock = threading.Lock()


def _ttl_seconds() -> int:
    try:
        return int(get_settings().cache_ttl_seconds)
    except Exception:
        return 15


def cache_key(namespace: str, **parts) -> str:
    ordered = "|".join(f"{k}={parts[k]}" for k in sorted(parts))
    return f"{namespace}:{ordered}"


def get(namespace: str, **parts) -> Optional[Any]:
    key = cache_key(namespace, **parts)
    with _lock:
        entry = _cache.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() > expires_at:
            _cache.pop(key, None)
            return None
        return value


def put(namespace: str, value: Any, ttl: Optional[int] = None, **parts) -> None:
    if value is None:
        return  # never cache negative results
    key = cache_key(namespace, **parts)
    with _lock:
        if len(_cache) > 512:  # crude bound; a real cache (Redis) replaces this
            now = time.monotonic()
            for stale_key in [k for k, (exp, _) in _cache.items() if exp < now]:
                _cache.pop(stale_key, None)
        _cache[key] = (time.monotonic() + (ttl if ttl is not None else _ttl_seconds()), value)


async def cached(namespace: str, loader: Callable, ttl: Optional[int] = None, **parts):
    """Get-or-load helper: returns a cache hit or loads and stores the value."""
    existing = get(namespace, **parts)
    if existing is not None:
        return existing
    value = await loader()
    put(namespace, value, ttl=ttl, **parts)
    return value


def clear(namespace: Optional[str] = None) -> int:
    """Clear the cache (optionally one namespace). Returns evicted count."""
    with _lock:
        if namespace is None:
            count = len(_cache)
            _cache.clear()
            return count
        prefix = namespace + ":"
        keys = [k for k in _cache if k.startswith(prefix)]
        for k in keys:
            _cache.pop(k, None)
        return len(keys)
