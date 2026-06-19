"""
Tool Base Module - 共享工具后端基础设施
消除 seo_tool/copywrite/competitor/naming 的重复代码
"""
from __future__ import annotations
import re, json, logging, asyncio, uuid, time
from datetime import datetime
from typing import Optional, Callable
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field

log = logging.getLogger("tool-base")

# ── 共享任务存储 ─────────────────────────────────────
_TASK_STORES = {}  # task_id -> dict
_TASK_OWNERS = {}  # task_id -> ip
_TASK_EXPIRY = 1800  # 30分钟过期

def _clean_expired_tasks(store: dict):
    """清理过期任务，防止内存泄漏"""
    now = time.time()
    expired = [k for k, v in store.items() 
               if v.get("_created", 0) + _TASK_EXPIRY < now]
    for k in expired:
        del store[k]
        _TASK_OWNERS.pop(k, None)
    if expired:
        log.debug(f"cleaned {len(expired)} expired tasks")

def _task_store_get(store: dict, task_id: str) -> Optional[dict]:
    task = store.get(task_id)
    if task:
        task["_last_access"] = time.time()
    return task

# ── 共享限流 ────────────────────────────────────────
_RATE_LIMITS = {}  # f"{prefix}:{ip}" -> [timestamp, ...]

def check_rate_limit(ip: str, prefix: str, max_req: int = 5, window: int = 60) -> bool:
    """通用IP限流"""
    key = f"{prefix}:{ip}"
    now = time.time()
    _RATE_LIMITS[key] = [t for t in _RATE_LIMITS.get(key, []) if now - t < window]
    if len(_RATE_LIMITS[key]) >= max_req:
        return False
    _RATE_LIMITS[key].append(now)
    return True

# ── 共享AI调用 + JSON解析 ──────────────────────────
_async_ai_cache = {}  # 简单语义缓存（可选）

async def call_ai_with_retry(prompt: str, max_retry: int = 2) -> str:
    """调用AI后端，带重试和超时"""
    from core.engine import get_engine
    
    for attempt in range(max_retry + 1):
        try:
            engine = await get_engine()
            ai = engine.ai_backend
            if not ai:
                raise RuntimeError("AI后端未初始化")
            
            raw = await asyncio.wait_for(ai.generate(prompt), timeout=120)
            return raw
        except asyncio.TimeoutError:
            if attempt < max_retry:
                log.warning(f"AI timeout, retry {attempt+1}/{max_retry}")
                await asyncio.sleep(2 ** attempt)
                continue
            raise RuntimeError("AI生成超时，请重试")
        except Exception as e:
            if attempt < max_retry:
                log.warning(f"AI error: {e}, retry {attempt+1}/{max_retry}")
                await asyncio.sleep(1)
                continue
            raise

def parse_ai_json(raw) -> Optional[dict]:
    """三级降级解析AI输出的JSON"""
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return None
    
    raw = raw.strip()
    
    # 1. 直接解析
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    
    # 2. 提取markdown代码块
    m = re.search(r"```(?:json)?\s*\n(.*?)```", raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    
    # 3. 提取花括号内容
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    
    return None

# ── 共享配额检查 ────────────────────────────────────
# 使用统一的配额存储（所有工具共享3次/天）
_DAILY_QUOTA = {}  # ip -> {date, count}

async def check_daily_quota(request: Request, redis_client=None) -> int:
    """
    免费用户每日3次配额检查
    返回：已使用次数
    """
    # 专业版跳过限制
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            from apis.routes.auth import get_current_user
            user = await get_current_user(auth_header[7:])
            if user and getattr(user, 'is_pro', False):
                return 0
        except Exception:
            pass
    
    client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() \
                or (request.client.host if request.client else "unknown")
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    if client_ip not in _DAILY_QUOTA:
        _DAILY_QUOTA[client_ip] = {"date": today, "count": 0}
    
    quota = _DAILY_QUOTA[client_ip]
    if quota["date"] != today:
        quota["date"] = today
        quota["count"] = 0
    
    if quota["count"] >= 3:
        raise HTTPException(403, "免费用户每日限3次，升级专业版解锁无限次")
    
    quota["count"] += 1
    return quota["count"]

def get_quota_info(request: Request) -> dict:
    """返回当前IP的配额信息"""
    client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() \
                or (request.client.host if request.client else "unknown")
    today = datetime.now().strftime("%Y-%m-%d")
    
    quota = _DAILY_QUOTA.get(client_ip, {"date": today, "count": 0})
    used = quota["count"] if quota["date"] == today else 0
    return {"remaining": max(0, 3 - used), "limit": 3, "used": used}

# ── 异步任务装饰器 ──────────────────────────────────
def create_task_router(prefix: str, tags: list, task_store: dict):
    """
    创建标准的工具任务路由（quota/styles/task/{id}）
    """
    router = APIRouter(prefix=prefix, tags=tags)
    
    @router.get("/quota")
    async def get_quota(request: Request):
        return get_quota_info(request)
    
    @router.get("/task/{task_id}")
    async def get_task(task_id: str):
        _clean_expired_tasks(task_store)
        task = _task_store_get(task_store, task_id)
        if not task:
            raise HTTPException(404, "任务不存在")
        
        resp = {
            "success": True,
            "status": task["status"],
            "progress": task.get("progress", "")
        }
        if task["status"] == "done" and task.get("result"):
            resp["result"] = task["result"]
        elif task["status"] == "error":
            resp["error"] = task.get("error", "生成失败")
        return resp
    
    return router
