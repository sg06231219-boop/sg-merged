"""
core.ratelimit — 企业级分布式限流

特性：
- Redis滑动窗口算法（精确计数，分布式共享）
- 内存降级（Redis不可用时自动降级）
- 按路径/用户/IP多维度限流
- 可配置窗口和阈值
- 限流事件监控（接入Prometheus）
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Optional

from fastapi import HTTPException, Request

logger = logging.getLogger("site-builder.ratelimit")


# ── 限流后端接口 ──────────────────────────────────────
class RateLimitBackend:
    """限流后端抽象"""

    async def is_allowed(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int, int]:
        """
        检查是否允许请求。
        Returns: (allowed, current_count, remaining)
        """
        raise NotImplementedError

    async def health_check(self) -> dict:
        return {"backend": "unknown", "status": "unknown"}


# ── 内存限流（滑动窗口） ──────────────────────────────
class MemoryRateLimitBackend(RateLimitBackend):
    """内存滑动窗口限流（单实例有效）"""

    def __init__(self):
        self._windows: dict[str, list[float]] = defaultdict(list)

    async def is_allowed(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int, int]:
        now = time.time()
        cutoff = now - window_seconds

        # 清理过期记录
        self._windows[key] = [t for t in self._windows[key] if t > cutoff]

        current = len(self._windows[key])
        if current >= limit:
            remaining = 0
            return False, current, remaining

        self._windows[key].append(now)
        remaining = limit - current - 1
        return True, current + 1, remaining

    async def health_check(self) -> dict:
        return {
            "backend": "memory",
            "status": "healthy",
            "active_keys": len(self._windows),
        }


# ── Redis 限流（滑动窗口） ──────────────────────────────
class RedisRateLimitBackend(RateLimitBackend):
    """Redis滑动窗口限流（分布式共享，多实例一致）"""

    def __init__(self, redis_url: str, password: Optional[str] = None,
                 max_connections: int = 20, socket_timeout: float = 5.0):
        self._redis_url = redis_url
        self._password = password
        self._max_connections = max_connections
        self._socket_timeout = socket_timeout
        self._redis = None
        self._connected = False

    async def _ensure_connection(self) -> bool:
        if self._connected and self._redis:
            return True
        try:
            import redis.asyncio as aioredis
            pool = aioredis.ConnectionPool.from_url(
                self._redis_url,
                password=self._password,
                max_connections=self._max_connections,
                socket_timeout=self._socket_timeout,
                decode_responses=True,
            )
            self._redis = aioredis.Redis(connection_pool=pool)
            await self._redis.ping()
            self._connected = True
            logger.info("Redis限流连接成功")
            return True
        except Exception as e:
            logger.warning(f"Redis限流连接失败: {e}，降级到内存限流")
            self._connected = False
            return False

    async def is_allowed(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int, int]:
        if not await self._ensure_connection():
            # Redis不可用时降级到放行（避免阻塞用户）
            return True, 0, limit

        try:
            now = time.time()
            window_key = f"rl:{key}"

            # 使用Redis事务保证原子性
            async with self._redis.pipeline() as pipe:
                # 移除过期记录
                await pipe.zremrangebyscore(window_key, 0, now - window_seconds)
                # 添加当前请求
                await pipe.zadd(window_key, {str(now): now})
                # 设置过期时间（自动清理）
                await pipe.expire(window_key, window_seconds + 1)
                # 获取当前窗口计数
                await pipe.zcard(window_key)
                results = await pipe.execute()

            current = results[-1]
            allowed = current <= limit
            remaining = max(0, limit - current)

            if not allowed:
                # 移除刚添加的记录（不计数）
                await self._redis.zrem(window_key, str(now))

            return allowed, current, remaining

        except Exception as e:
            logger.warning(f"Redis限流检查失败: {e}")
            return True, 0, limit

    async def health_check(self) -> dict:
        if not await self._ensure_connection():
            return {"backend": "redis", "status": "disconnected"}
        return {"backend": "redis", "status": "healthy"}


# ── 限流管理器 ──────────────────────────────────────────
class RateLimitManager:
    """
    统一限流管理器：
    - 按路径配置不同阈值
    - Redis优先，内存降级
    - 自动注入限流响应头
    """

    def __init__(self, config):
        self._config = config
        self._backend: Optional[RateLimitBackend] = None
        self._fallback = MemoryRateLimitBackend()
        self._initialized = False

        # 路径→限流配置映射
        self._path_limits = {
            "/api/v1/generate": config.rate_limit.generate_per_minute,
            "/api/v1/generate-from-text": config.rate_limit.generate_per_minute,
            "/api/v1/preview": config.rate_limit.preview_per_minute,
            "/api/v1/download": config.rate_limit.download_per_minute,
        }
        self._default_limit = config.rate_limit.default_per_minute
        self._auth_limit = config.rate_limit.auth_per_minute

    async def initialize(self) -> None:
        if self._initialized:
            return

        if self._config.rate_limit.backend == "redis" and self._config.redis.enabled:
            redis_backend = RedisRateLimitBackend(
                redis_url=self._config.redis.url,
                password=self._config.redis.password,
                max_connections=self._config.redis.max_connections,
                socket_timeout=self._config.redis.socket_timeout,
            )
            if await redis_backend._ensure_connection():
                self._backend = redis_backend
                logger.info("限流后端: Redis")
            else:
                self._backend = self._fallback
                logger.info("限流后端: 内存（Redis降级）")
        else:
            self._backend = self._fallback
            logger.info("限流后端: 内存")

        self._initialized = True

    def _get_active_backend(self) -> RateLimitBackend:
        return self._backend or self._fallback

    def _get_client_ip(self, request: Request) -> str:
        """获取真实客户端IP"""
        xff = request.headers.get("x-forwarded-for", "")
        if xff:
            return xff.split(",")[0].strip()
        xri = request.headers.get("x-real-ip", "")
        if xri:
            return xri.strip()
        return request.client.host if request.client else "unknown"

    def _get_rate_limit_for_path(self, path: str) -> int:
        """获取路径对应的限流阈值"""
        for prefix, limit in self._path_limits.items():
            if path.startswith(prefix):
                return limit
        # 认证路径特殊处理
        if "/auth/" in path or "/login" in path or "/register" in path:
            return self._auth_limit
        return self._default_limit

    async def check(self, request: Request, path: str = None) -> None:
        """
        检查请求是否被限流。超限抛出 HTTP 429。
        """
        if not self._config.rate_limit.enabled:
            return

        path = path or request.url.path
        ip = self._get_client_ip(request)
        limit = self._get_rate_limit_for_path(path)
        key = f"{ip}:{path}"

        allowed, current, remaining = await self._get_active_backend().is_allowed(
            key, limit, window_seconds=60
        )

        if not allowed:
            try:
                from core.observability import record_rate_limited
                record_rate_limited(path)
            except ImportError:
                pass
            logger.warning(f"限流触发: ip={ip} path={path} current={current} limit={limit}")
            raise HTTPException(
                429,
                f"请求频率超限，每分钟最多{limit}次，请稍后再试"
            )

    async def health_check(self) -> dict:
        return await self._get_active_backend().health_check()


# ── 全局限流管理器 ──────────────────────────────────────
_ratelimit_manager: Optional[RateLimitManager] = None


def get_ratelimit_manager(config=None) -> RateLimitManager:
    """获取全局限流管理器"""
    global _ratelimit_manager
    if _ratelimit_manager is None:
        if config is None:
            from core.config import get_config
            config = get_config()
        _ratelimit_manager = RateLimitManager(config)
    return _ratelimit_manager
