"""
core.observability — 企业级可观测性

特性：
- 结构化日志（JSON格式，兼容ELK/Loki）
- 日志轮转（按大小切割，保留历史）
- Prometheus指标暴露（请求数、延迟、AI调用、缓存命中率）
- 请求追踪ID（X-Request-ID）
- 慢请求告警（>3秒自动记录）
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# ── Prometheus 指标 ──────────────────────────────────
try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    _HAS_PROM = True
except ImportError:
    _HAS_PROM = False

    # 占位符，避免ImportError
    class Counter:
        def __init__(self, *a, **kw): pass
        def inc(self, *a, **kw): pass
        def labels(self, *a, **kw): return self

    class Histogram:
        def __init__(self, *a, **kw): pass
        def observe(self, *a, **kw): pass
        def labels(self, *a, **kw): return self

    class Gauge:
        def __init__(self, *a, **kw): pass
        def set(self, *a, **kw): pass

    def generate_latest(*a, **kw): return b""
    CONTENT_TYPE_LATEST = "text/plain"


# ── 指标定义 ──────────────────────────────────────────
if _HAS_PROM:
    REQ_COUNT = Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["method", "path", "status"]
    )
    REQ_LATENCY = Histogram(
        "http_request_duration_seconds",
        "Request latency in seconds",
        ["method", "path"]
    )
    AI_CALLS = Counter(
        "ai_calls_total",
        "Total AI backend calls",
        ["backend", "status"]  # status: success|error|cache_hit
    )
    CACHE_HITS = Counter(
        "cache_hits_total",
        "Total cache hits/misses",
        ["type"]  # type: hit|miss
    )
    RATE_LIMITED = Counter(
        "rate_limited_total",
        "Total rate-limited requests",
        ["path"]
    )
    ACTIVE_USERS = Gauge(
        "active_users",
        "Active users in last 5 minutes",
        []
    )
else:
    REQ_COUNT = Counter()
    REQ_LATENCY = Histogram()
    AI_CALLS = Counter()
    CACHE_HITS = Counter()
    RATE_LIMITED = Counter()
    ACTIVE_USERS = Gauge()


# ── 结构化日志配置 ──────────────────────────────────
def setup_logging(config) -> logging.Logger:
    """
    配置结构化日志。
    - JSON格式（生产环境）→ 方便ELK/Loki采集
    - 文本格式（开发环境）→ 方便本地调试
    - 自动轮转（避免日志文件无限增大）
    """
    log_level = getattr(logging, config.observability.log_level.upper(), logging.INFO)
    log_format = config.observability.log_format
    log_file = config.observability.log_file
    max_bytes = config.observability.log_max_bytes
    backup_count = config.observability.log_backup_count

    logger = logging.getLogger("site-builder")
    logger.setLevel(log_level)
    logger.handlers.clear()  # 避免重复添加

    # 公共格式
    if log_format == "json":
        try:
            import structlog
            structlog.configure(
                processors=[
                    structlog.contextvars.merge_contextvars,
                    structlog.processors.add_log_level,
                    structlog.processors.TimeStamper(fmt="ISO"),
                    structlog.dev.ConsoleRenderer() if config.is_development else structlog.processors.JSONRenderer()
                ]
            )
            handler = logging.StreamHandler()
            formatter = structlog.stdlib.ProcessorFormatter(
                processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta],
                foreign_pre_chain=[structlog.stdlib.ExtraAdder()]
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        except ImportError:
            # structlog未安装，降级到标准JSON格式
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter('{"timestamp":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}')
            )
            logger.addHandler(handler)
    else:
        # 文本格式
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s: %(message)s", "%H:%M:%S")
        )
        logger.addHandler(handler)

    # 文件轮转
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        if log_format == "json":
            file_handler.setFormatter(
                logging.Formatter('{"timestamp":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}')
            )
        else:
            file_handler.setFormatter(
                logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s: %(message)s", "%H:%M:%S")
            )
        logger.addHandler(file_handler)

    return logger


# ── 请求追踪中间件 ──────────────────────────────────
class RequestTracingMiddleware(BaseHTTPMiddleware):
    """
    为每个请求分配唯一ID，注入响应头，方便全链路追踪。
    """

    def __init__(self, app: ASGIApp, header_name: str = "X-Request-ID"):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 获取或生成请求ID
        req_id = request.headers.get(self.header_name) or str(uuid.uuid4().hex[:12])
        start_time = time.time()

        # 注入上下文（日志中可自动携带）
        try:
            import structlog
            structlog.contextvars.clear_contextvars()
            structlog.contextvars.bind_contextvars(request_id=req_id)
        except ImportError:
            pass

        # 执行请求
        response = await call_next(request)

        # 记录延迟
        latency = time.time() - start_time
        response.headers[self.header_name] = req_id
        response.headers["X-Response-Time"] = f"{latency:.3f}s"

        # Prometheus指标
        if _HAS_PROM:
            path = request.url.path
            REQ_COUNT.labels(method=request.method, path=path, status=response.status_code).inc()
            REQ_LATENCY.labels(method=request.method, path=path).observe(latency)

        # 慢请求告警（>3秒）
        if latency > 3.0:
            logger = logging.getLogger("site-builder.slow")
            logger.warning(
                f"慢请求: {request.method} {request.url.path} → {latency:.2f}s | "
                f"req_id={req_id} | client={request.client.host if request.client else 'unknown'}"
            )

        return response


# ── Prometheus 指标端点 ──────────────────────────────
async def metrics_endpoint(request: Request):
    """暴露Prometheus指标（仅内网可访问）"""
    if not _HAS_PROM:
        return Response(content="Prometheus client not installed", status_code=501)
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# ── AI调用监控装饰器 ────────────────────────────────
def monitor_ai_call(backend: str):
    """
    AI调用监控装饰器，记录成功/失败/缓存命中。
    用法：
        @monitor_ai_call("deepseek")
        async def call_deepseek(prompt): ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                AI_CALLS.labels(backend=backend, status="success").inc()
                return result
            except Exception as e:
                AI_CALLS.labels(backend=backend, status="error").inc()
                raise
        return wrapper
    return decorator


# ── 缓存监控 ──────────────────────────────────────────
def record_cache_hit():
    CACHE_HITS.labels(type="hit").inc()


def record_cache_miss():
    CACHE_HITS.labels(type="miss").inc()


# ── 限流监控 ──────────────────────────────────────────
def record_rate_limited(path: str):
    RATE_LIMITED.labels(path=path).inc()


# ── 活跃用户更新 ──────────────────────────────────────
def update_active_users(count: int):
    ACTIVE_USERS.set(count)
