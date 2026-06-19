"""
core.health — 企业级健康检查

特性：
- 存活探针（/health/live）：进程存活
- 就绪探针（/health/ready）：服务可用（数据库+Redis+AI后端）
- 详细状态（/health/detail）：全组件诊断信息
- 版本信息
"""

from __future__ import annotations

import os
import platform
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["健康检查"])

# 启动时间（模块加载时记录）
_START_TIME = time.time()


def _get_uptime() -> str:
    """运行时长"""
    delta = time.time() - _START_TIME
    hours = int(delta // 3600)
    minutes = int((delta % 3600) // 60)
    seconds = int(delta % 60)
    return f"{hours}h {minutes}m {seconds}s"


async def _check_database() -> dict:
    """数据库健康检查"""
    try:
        from core.database import engine, get_db_info
        with engine.connect() as conn:
            conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        info = get_db_info()
        return {"status": "healthy", **info}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def _check_redis() -> dict:
    """Redis健康检查"""
    try:
        from core.cache import get_cache_manager
        cm = get_cache_manager()
        return await cm.health_check()
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def _check_rate_limit() -> dict:
    """限流后端健康检查"""
    try:
        from core.ratelimit import get_ratelimit_manager
        rl = get_ratelimit_manager()
        return await rl.health_check()
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def _check_ai_backend() -> dict:
    """AI后端健康检查"""
    try:
        from core.engine import get_engine
        engine = await get_engine()
        return {
            "status": "healthy",
            "active": engine.active_ai,
            "available": list(engine._ai._backend_registry.keys()),
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def _check_disk() -> dict:
    """磁盘空间检查"""
    try:
        outputs = Path("outputs")
        outputs.mkdir(exist_ok=True)
        usage = __import__("shutil").disk_usage(str(outputs))
        free_gb = usage.free / (1024 ** 3)
        total_gb = usage.total / (1024 ** 3)
        return {
            "status": "healthy" if free_gb > 1 else "warning",
            "free_gb": round(free_gb, 2),
            "total_gb": round(total_gb, 2),
            "usage_percent": round((1 - usage.free / usage.total) * 100, 1),
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


# ── 存活探针 ──────────────────────────────────────────
@router.get("/health/live")
async def liveness():
    """存活探针：进程存活即返回200"""
    return {"status": "alive", "uptime": _get_uptime()}


# ── 就绪探针 ──────────────────────────────────────────
@router.get("/health/ready")
async def readiness():
    """就绪探针：核心依赖可用才返回200"""
    checks = {
        "database": await _check_database(),
        "ai": await _check_ai_backend(),
    }
    all_healthy = all(c.get("status") == "healthy" for c in checks.values())
    status_code = 200 if all_healthy else 503
    return JSONResponse(
        {"status": "ready" if all_healthy else "not_ready", "checks": checks},
        status_code=status_code,
    )


# ── 详细状态 ──────────────────────────────────────────
@router.get("/health/detail")
async def health_detail():
    """完整诊断信息"""
    try:
        from core.config import get_config
        config = get_config()
        version = config.version
        env = config.environment.value
    except Exception:
        version = "unknown"
        env = "unknown"

    checks = {
        "database": await _check_database(),
        "redis": await _check_redis(),
        "rate_limit": await _check_rate_limit(),
        "ai_backend": await _check_ai_backend(),
        "disk": await _check_disk(),
    }

    # 生成文件统计
    outputs_dir = Path("outputs")
    html_count = len(list(outputs_dir.glob("*.html"))) if outputs_dir.exists() else 0
    zip_count = len(list(outputs_dir.glob("*.zip"))) if outputs_dir.exists() else 0

    return {
        "status": "healthy",
        "version": version,
        "environment": env,
        "uptime": _get_uptime(),
        "started_at": datetime.fromtimestamp(_START_TIME).isoformat(),
        "system": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
        },
        "checks": checks,
        "stats": {
            "generated_pages": html_count,
            "generated_sites": zip_count,
        },
    }
