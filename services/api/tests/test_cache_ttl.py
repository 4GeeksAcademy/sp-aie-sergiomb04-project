from __future__ import annotations

from trackflow_api.cache import TTLCache


def test_cache_miss_then_hit(monkeypatch) -> None:
    now = [100.0]
    monkeypatch.setattr("trackflow_api.cache.monotonic", lambda: now[0])

    cache = TTLCache()
    assert cache.get("alpha") is None

    cache.set("alpha", {"value": 1}, ttl_seconds=10)
    assert cache.get("alpha") == {"value": 1}


def test_cache_ttl_expiration(monkeypatch) -> None:
    now = [200.0]
    monkeypatch.setattr("trackflow_api.cache.monotonic", lambda: now[0])

    cache = TTLCache()
    cache.set("beta", "cached", ttl_seconds=5)
    assert cache.get("beta") == "cached"

    now[0] = 206.0
    assert cache.get("beta") is None


def test_cache_invalidate_and_prefix(monkeypatch) -> None:
    now = [300.0]
    monkeypatch.setattr("trackflow_api.cache.monotonic", lambda: now[0])

    cache = TTLCache()
    cache.set("suppliers:list:user=a", [1], ttl_seconds=60)
    cache.set("suppliers:detail:user=a:id=1", {"id": "1"}, ttl_seconds=60)
    cache.set("incidents:summary:user=a", {"total": 1}, ttl_seconds=60)

    removed = cache.invalidate_prefix("suppliers:")
    assert removed == 2
    assert cache.get("suppliers:list:user=a") is None
    assert cache.get("suppliers:detail:user=a:id=1") is None
    assert cache.get("incidents:summary:user=a") == {"total": 1}

    cache.invalidate("incidents:summary:user=a")
    assert cache.get("incidents:summary:user=a") is None
