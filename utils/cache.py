import json
import os
import asyncio
from typing import Any, Dict, List, Callable, Awaitable
from redis.asyncio import Redis


class Cache:
    def __init__(self, redis_url) -> None:
        self._client = Redis.from_url(redis_url,
            decode_responses=True
        )
        self._lock = asyncio.Lock()

    async def ensure(self) -> bool:
        if not self._client:
            return False
        try:
            await self._client.ping()
            return True
        except Exception as err:
            self._log.error(f"[CacheService] Redis connection error: {err}")
            return False
    
    async def get(self, key: str) -> List[Dict[str, Any]] | Dict[str, Any] | None:
        async with self._lock:
            raw = await self._client.get(key)
            return json.loads(raw) if raw else None

    async def set(self, key: str, value: List[Dict[str, Any]] | Dict[str, Any]) -> None:
        # Validate if it is a List of Dicts OR a single Dict
        is_list_of_dicts = isinstance(value, list) and all(isinstance(v, dict) for v in value)
        is_single_dict = isinstance(value, dict)

        if not (is_list_of_dicts or is_single_dict):
            raise TypeError("Cache.set espera uma lista de dict ou um único dict")

        async with self._lock:
            await self._client.set(key, json.dumps(value))

    async def delete(self, key: str) -> None:
        async with self._lock:
            await self._client.delete(key)

    async def invalidate_prefix(self, prefix: str) -> None:
        async with self._lock:
            keys = await self._client.keys(f"{prefix}*")
            if keys:
                await self._client.delete(*keys)

    async def refresh(self, key: str, fetcher) -> List[Dict[str, Any]] | Dict[str, Any]:
        value = await fetcher()

        is_list_of_dicts = isinstance(value, list) and all(isinstance(v, dict) for v in value)
        is_single_dict = isinstance(value, dict)

        if not (is_list_of_dicts or is_single_dict):
            raise TypeError("Cache.refresh fetcher deve retornar uma lista de dict ou um único dict")

        async with self._lock:
            await self._client.set(key, json.dumps(value))

        return value

    async def append(self, key: str, item: Dict[str, Any]) -> None:
        if not isinstance(item, dict):
            raise TypeError("Cache.append espera um dict")

        async with self._lock:
            raw = await self._client.get(key)
            data = json.loads(raw) if raw else []
            data.append(item)
            await self._client.set(key, json.dumps(data))
