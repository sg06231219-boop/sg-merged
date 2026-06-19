"""
core.cache — 企业级缓存层

特性：
- Redis主存储（分布式共享、TTL自动过期）
- 内存降级（Redis不可用时自动降级，零影响启动）
- 语义缓存（Prompt哈希→结果）
- LRU淘汰（内存模式）
- 缓存命中率监控（接入Prometheus）
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections import OrderedDict
from typing import Any, Optional

logger = logging.getLogger("site-builder.cache")


# ── 缓存接口 ──────────────────────────────────────────
class CacheBackend:
    """缓存后端抽象"""

    async def get(self, key: str) -> Optional[dict]:
        raise NotImplementedError

    async def put(self, key: str, value: dict, ttl: int = 0) -> None:
        raise NotImplementedError

    async def delete(self, key: str) -> None:
        raise NotImplementedError

    async def clear(self) -> None:
        raise NotImplementedError

    async def health_check(self) -> dict:
        return {"backend": "unknown", "status": "unknown"}


# ── 内存缓存（LRU + TTL） ──────────────────────────────
class MemoryCacheBackend(CacheBackend):
    """内存缓存后端，支持LRU淘汰和TTL过期"""

    def __init__(self, max_entries: int = 200):
        self._store: OrderedDict[str, dict] = OrderedDict()
        self._max_entries = max_entries
        self._hits = 0
        self._misses = 0

    async def get(self, key: str) -> Optional[dict]:
        entry = self._store.get(key)
        if entry is None:
            self._misses += 1
            return None
        # TTL检查
        if entry.get("_expires_at") and time.time() > entry["_expires_at"]:
            del self._store[key]
            self._misses += 1
            return None
        # LRU：移到末尾
        self._store.move_to_end(key)
        self._hits += 1
        result = dict(entry)
        result.pop("_expires_at", None)
        result.pop("_ts", None)
        return result

    async def put(self, key: str, value: dict, ttl: int = 0) -> None:
        # 超容量淘汰最早的1/4
        if len(self._store) >= self._max_entries:
            evict_count = max(1, self._max_entries // 4)
            for _ in range(evict_count):
                self._store.popitem(last=False)
        entry = dict(value)
        entry["_ts"] = time.time()
        entry["_expires_at"] = (time.time() + ttl) if ttl > 0 else None
        self._store[key] = entry
        self._store.move_to_end(key)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def clear(self) -> None:
        self._store.clear()
        self._hits = 0
        self._misses = 0

    async def health_check(self) -> dict:
        return {
            "backend": "memory",
            "status": "healthy",
            "entries": len(self._store),
            "max_entries": self._max_entries,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{self._hits / (self._hits + self._misses) * 100:.1f}%"
                if (self._hits + self._misses) > 0 else "N/A",
        }


# ── Redis 缓存 ──────────────────────────────────────────
class RedisCacheBackend(CacheBackend):
    """Redis缓存后端，支持TTL和集群"""

    def __init__(self, redis_url: str, password: Optional[str] = None,
                 max_connections: int = 20, socket_timeout: float = 5.0):
        self._redis_url = redis_url
        self._password = password
        self._max_connections = max_connections
        self._socket_timeout = socket_timeout
        self._pool = None
        self._redis = None
        self._connected = False

    async def _ensure_connection(self) -> bool:
        """确保Redis连接可用"""
        if self._connected and self._redis:
            return True
        try:
            import redis.asyncio as aioredis
            self._pool = aioredis.ConnectionPool.from_url(
                self._redis_url,
                password=self._password,
                max_connections=self._max_connections,
                socket_timeout=self._socket_timeout,
                decode_responses=True,
            )
            self._redis = aioredis.Redis(connection_pool=self._pool)
            # 测试连接
            await self._redis.ping()
            self._connected = True
            logger.info(f"Redis缓存连接成功: {self._redis_url.split('@')[-1] if '@' in self._redis_url else self._redis_url}")
            return True
        except ImportError:
            logger.warning("redis[hiredis]未安装，Redis缓存不可用")
            return False
        except Exception as e:
            logger.warning(f"Redis缓存连接失败: {e}，将降级到内存缓存")
            self._connected = False
            return False

    async def get(self, key: str) -> Optional[dict]:
        if not await self._ensure_connection():
            return None
        try:
            data = await self._redis.get(f"cache:{key}")
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning(f"Redis GET失败: {e}")
            return None

    async def put(self, key: str, value: dict, ttl: int = 0) -> None:
        if not await self._ensure_connection():
            return
        try:
            serialized = json.dumps(value, ensure_ascii=False, default=str)
            if ttl > 0:
                await self._redis.setex(f"cache:{key}", ttl, serialized)
            else:
                await self._redis.set(f"cache:{key}", serialized)
        except Exception as e:
            logger.warning(f"Redis SET失败: {e}")

    async def delete(self, key: str) -> None:
        if not await self._ensure_connection():
            return
        try:
            await self._redis.delete(f"cache:{key}")
        except Exception as e:
            logger.warning(f"Redis DEL失败: {e}")

    async def clear(self) -> None:
        if not await self._ensure_connection():
            return
        try:
            # 仅清除 cache: 前缀的键
            async for key in self._redis.scan_iter("cache:*"):
                await self._redis.delete(key)
        except Exception as e:
            logger.warning(f"Redis CLEAR失败: {e}")

    async def health_check(self) -> dict:
        if not await self._ensure_connection():
            return {"backend": "redis", "status": "disconnected"}
        try:
            info = await self._redis.info()
            return {
                "backend": "redis",
                "status": "healthy",
                "used_memory_human": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "keys": await self._redis.dbsize(),
            }
        except Exception as e:
            return {"backend": "redis", "status": f"error: {e}"}


# ── 缓存管理器 ──────────────────────────────────────────
class CacheManager:
    """
    统一缓存管理器：
    - Redis可用 → Redis主存储
    - Redis不可用 → 自动降级到内存
    - 提供语义缓存Key生成
    """

    def __init__(self, config):
        self._config = config
        self._backend: Optional[CacheBackend] = None
        self._fallback = MemoryCacheBackend(max_entries=config.cache.max_entries)
        self._initialized = False

    async def initialize(self) -> None:
        """初始化缓存后端"""
        if self._initialized:
            return

        if self._config.cache.backend == "redis" and self._config.redis.enabled:
            redis_backend = RedisCacheBackend(
                redis_url=self._config.redis.url,
                password=self._config.redis.password,
                max_connections=self._config.redis.max_connections,
                socket_timeout=self._config.redis.socket_timeout,
            )
            if await redis_backend._ensure_connection():
                self._backend = redis_backend
                logger.info("缓存后端: Redis")
            else:
                self._backend = self._fallback
                logger.info("缓存后端: 内存（Redis降级）")
        else:
            self._backend = self._fallback
            logger.info("缓存后端: 内存")

        self._initialized = True

    def _get_active_backend(self) -> CacheBackend:
        return self._backend or self._fallback

    @staticmethod
    def semantic_key(info: dict, mode: str) -> str:
        """生成语义缓存Key（Prompt哈希）"""
        sig = (
            f"{mode}:"
            f"{info.get('name', '')}:"
            f"{info.get('industry', '')}:"
            f"{info.get('description', '')}:"
            f"{info.get('keywords', '')}:"
            f"{info.get('audience', '')}"
        )
        return hashlib.md5(sig.encode()).hexdigest()

    async def get(self, key: str) -> Optional[dict]:
        """获取缓存"""
        result = await self._get_active_backend().get(key)
        if result:
            try:
                from core.observability import record_cache_hit
                record_cache_hit()
            except ImportError:
                pass
        else:
            try:
                from core.observability import record_cache_miss
                record_cache_miss()
            except ImportError:
                pass
        return result

    async def put(self, key: str, value: dict) -> None:
        """写入缓存"""
        ttl = (
            self._config.cache.redis_ttl_seconds
            if isinstance(self._get_active_backend(), RedisCacheBackend)
            else self._config.cache.ttl_seconds
        )
        await self._get_active_backend().put(key, value, ttl=ttl)

    async def delete(self, key: str) -> None:
        await self._get_active_backend().delete(key)

    async def clear(self) -> None:
        await self._get_active_backend().clear()

    async def health_check(self) -> dict:
        return await self._get_active_backend().health_check()


# ── 全局缓存管理器 ──────────────────────────────────────
_cache_manager: Optional[CacheManager] = None


def get_cache_manager(config=None) -> CacheManager:
    """获取全局缓存管理器"""
    global _cache_manager
    if _cache_manager is None:
        if config is None:
            from core.config import get_config
            config = get_config()
        _cache_manager = CacheManager(config)
    return _cache_manager
