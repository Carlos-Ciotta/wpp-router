import json
import asyncio
from typing import Any, Dict, List
from redis.asyncio import Redis


class Cache:
    def __init__(self, redis_url) -> None:
        self._client = Redis.from_url(
            redis_url,
            decode_responses=True  # já retorna str
        )
        self._lock = asyncio.Lock()

    async def ensure(self) -> bool:
        try:
            await self._client.ping()
            return True
        except Exception:
            return False

    # --------------------
    # STRING
    # --------------------
    async def get(self, key: str):
        return await self._client.get(key)

    async def set(self, key: str, value: str):
        async with self._lock:
            await self._client.set(key, value)

    async def delete(self, key: str):
        async with self._lock:
            await self._client.delete(key)

    # --------------------
    # HASH (attendants)
    # --------------------
    async def hset(self, key: str, mapping: Dict[str, Any]):
        async with self._lock:
            await self._client.hset(key, mapping=mapping)

    async def hgetall(self, key: str) -> Dict[str, Any] | None:
        data = await self._client.hgetall(key)
        return data if data else None

    # --------------------
    # SET (indexes)
    # --------------------
    async def sadd(self, key: str, value: str):
        async with self._lock:
            await self._client.sadd(key, value)

    async def smembers(self, key: str) -> List[str]:
        return list(await self._client.smembers(key))

    # --------------------
    # Helpers
    # --------------------
    async def invalidate_prefix(self, prefix: str):
        async with self._lock:
            keys = await self._client.keys(f"{prefix}*")
            if keys:
                await self._client.delete(*keys)
