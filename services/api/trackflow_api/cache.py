from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from time import monotonic
from typing import Any


@dataclass(slots=True)
class _CacheEntry:
    value: Any
    expires_at: float


class TTLCache:
    """Simple in-memory TTL cache with prefix invalidation."""

    def __init__(self) -> None:
        self._store: dict[str, _CacheEntry] = {}
        self._lock = RLock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None

            if entry.expires_at <= monotonic():
                self._store.pop(key, None)
                return None

            return entry.value

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            return

        with self._lock:
            self._store[key] = _CacheEntry(value=value, expires_at=monotonic() + ttl_seconds)

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> int:
        removed = 0
        with self._lock:
            for key in list(self._store):
                if key.startswith(prefix):
                    self._store.pop(key, None)
                    removed += 1
        return removed

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


api_cache = TTLCache()