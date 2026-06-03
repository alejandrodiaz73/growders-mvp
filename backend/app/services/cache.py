"""
growders.services.cache
────────────────────────
Cache abstraction with two implementations:

  MemoryCache  — single-process dict, zero dependencies (Tier 0)
  RedisCache   — Redis-backed, survives restarts (Tier 1)

Switch by setting REDIS_URL in .env.
The rest of the application only imports `get_cache()` and never
knows which backend is running.

Usage:
    cache = get_cache()
    await cache.set("key", value, ttl=60)
    value = await cache.get("key")
    await cache.delete("key")
    await cache.clear_pattern("tenant:uuid:*")
"""

import json
import time
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


# ── Interface ─────────────────────────────────────────────────────────────────

class CacheProvider(ABC):
    @abstractmethod
    async def get(self, key: str) -> Any | None: ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...

    @abstractmethod
    async def clear_pattern(self, pattern: str) -> int: ...

    @abstractmethod
    async def close(self) -> None: ...


# ── Tier 0: In-memory ─────────────────────────────────────────────────────────

class MemoryCache(CacheProvider):
    """
    Thread-safe enough for a single async process.
    Not shared across workers — fine for development and a single-instance pilot.
    When you add multiple workers or processes, switch to Redis.
    """

    def __init__(self, default_ttl: int = 300):
        self._store: dict[str, tuple[Any, float | None]] = {}
        self._default_ttl = default_ttl

    def _is_expired(self, expires_at: float | None) -> bool:
        if expires_at is None:
            return False
        return time.monotonic() > expires_at

    async def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if self._is_expired(expires_at):
            del self._store[key]
            return None
        return value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        effective_ttl = ttl if ttl is not None else self._default_ttl
        expires_at = time.monotonic() + effective_ttl if effective_ttl > 0 else None
        self._store[key] = (value, expires_at)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def clear_pattern(self, pattern: str) -> int:
        """Simple prefix matching (no glob). E.g. pattern='tenant:uuid:' removes all keys starting with it."""
        prefix = pattern.rstrip("*")
        to_delete = [k for k in self._store if k.startswith(prefix)]
        for k in to_delete:
            del self._store[k]
        return len(to_delete)

    async def close(self) -> None:
        self._store.clear()


# ── Tier 1: Redis ─────────────────────────────────────────────────────────────

class RedisCache(CacheProvider):
    """
    Redis-backed cache. Requires REDIS_URL in .env.
    Uses redis.asyncio (bundled with redis>=4.2).
    """

    def __init__(self, redis_url: str, default_ttl: int = 300):
        import redis.asyncio as aioredis  # lazy import — not required in Tier 0

        self._client = aioredis.from_url(redis_url, decode_responses=True)
        self._default_ttl = default_ttl

    def _serialize(self, value: Any) -> str:
        return json.dumps(value, default=str)

    def _deserialize(self, raw: str) -> Any:
        return json.loads(raw)

    async def get(self, key: str) -> Any | None:
        raw = await self._client.get(key)
        if raw is None:
            return None
        return self._deserialize(raw)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        effective_ttl = ttl if ttl is not None else self._default_ttl
        serialized = self._serialize(value)
        if effective_ttl and effective_ttl > 0:
            await self._client.setex(key, effective_ttl, serialized)
        else:
            await self._client.set(key, serialized)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)

    async def clear_pattern(self, pattern: str) -> int:
        keys = await self._client.keys(pattern)
        if keys:
            return await self._client.delete(*keys)
        return 0

    async def close(self) -> None:
        await self._client.aclose()


# ── Factory ───────────────────────────────────────────────────────────────────

_cache_instance: CacheProvider | None = None


def get_cache() -> CacheProvider:
    """
    Return the singleton cache provider.
    First call initialises based on settings; subsequent calls return cached instance.
    """
    global _cache_instance
    if _cache_instance is not None:
        return _cache_instance

    if settings.cache_backend == "redis":
        logger.info("Cache backend: Redis (%s)", settings.redis_url.split("@")[-1])
        _cache_instance = RedisCache(
            redis_url=settings.redis_url,
            default_ttl=settings.cache_ttl_seconds,
        )
    else:
        logger.info("Cache backend: in-memory (single process)")
        _cache_instance = MemoryCache(default_ttl=settings.cache_ttl_seconds)

    return _cache_instance


async def close_cache() -> None:
    global _cache_instance
    if _cache_instance:
        await _cache_instance.close()
        _cache_instance = None


# ── Key helpers ───────────────────────────────────────────────────────────────

def cache_key(tenant_id: str, *parts: str) -> str:
    """
    Build a namespaced cache key so tenants never collide.
    Example: cache_key("uuid", "conversation", "session-token")
             → "t:uuid:conversation:session-token"
    """
    return "t:" + ":".join([tenant_id, *parts])
