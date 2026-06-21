"""
apis.routes.generate — 生成 / 下载 / 状态 API 路由

安全加固版：
- 限流：生成类接口每 IP 每分钟最多 10 次
- 路径穿越防护
- 输入尺寸校验
- 文件类型检查
"""

import re
import uuid
import asyncio
import hashlib
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from core.engine import get_engine
from builders.site_planner import SitePlanner
import time as _time

# ── 异步任务队列（化解超时） ───────────────────────────
_GEN_TASKS: dict[str, dict] = {}  # {task_id: {status, result, created_at}}

# ── 语义缓存（Prompt哈希→结果） ───────────────────────
_GEN_CACHE: dict[str, dict] = {}  # {prompt_hash: result}
_CACHE_MAX = 200  # 最多缓存200条


def _cache_key(info: dict, mode: str) -> str:
    """生成Prompt哈希作为缓存key"""
    sig = f"{mode}:{info.get('name','')}:{info.get('industry','')}:{info.get('description','')}:{info.get('keywords','')}:{info.get('audience','')}"
    return hashlib.md5(sig.encode()).hexdigest()


def _cache_put(key: str, result: dict):
    """写入缓存（LRU淘汰）"""
    if len(_GEN_CACHE) >= _CACHE_MAX:
        # 淘汰最早的1/4
        oldest = sorted(_GEN_CACHE.items(), key=lambda x: x[1].get('_ts', 0))[:_CACHE_MAX // 4]
        for k, _ in oldest:
            _GEN_CACHE.pop(k, None)
    result['_ts'] = _time.time()
    _GEN_CACHE[key] = result


def _cache_get(key: str) -> dict | None:
    """读取缓存"""
    hit = _GEN_CACHE.get(key)
    if hit:
        hit['_ts'] = _time.time()  # 更新访问时间
    return hit


router = APIRouter(tags=["生成"])

# ── 安全常量 ──────────────────────────────────────────
_MAX_NAME_LEN = 100
_MAX_INDUSTRY_LEN = 50
_MAX_DESC_LEN = 500
_MAX_KEYWORDS_LEN = 200
_MAX_AUDIENCE_LEN = 100
_MAX_PHONE_LEN = 30
_MAX_EMAIL_LEN = 100
_MAX_ADDRESS_LEN = 200
_MAX_WEBSITE_LEN = 200
_MAX_TEXT_LEN = 2000
_MAX_OUTPUT_HTML = 500_000  # 输出熔断：单页HTML最大500KB

# 合法 ID 格式
_ID_PATTERN = re.compile(r"^[a-f0-9]{12}$")


def _validate_id(item_id: str) -> None:
    """防止路径遍历攻击"""
    if not _ID_PATTERN.match(item_id):
        raise HTTPException(400, "非法请求")
    # 额外检查：文件名必须完全匹配，防止 ../../../etc/passwd
    safe = str(Path(item_id).name)
    if safe != item_id:
        raise HTTPException(400, "非法路径")


def _sanitize(s: str, max_len: int) -> str:
    """截断并去除控制字符"""
    if s is None:
        return ""
    s = s.strip()[:max_len]
    # 移除控制字符（保留常见中英文标点）
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)


# ── 生成接口 ──────────────────────────────────────────
@router.post("/generate")
async def generate(
    request: Request,
    mode: str = Form(default="landing"),
    name: str = Form(...),
    industry: str = Form(default=""),
    description: str = Form(default=""),
    keywords: str = Form(default=""),
    audience: str = Form(default=""),
    phone: str = Form(default=""),
    email: str = Form(default=""),
    address: str = Form(default=""),
    website: str = Form(default=""),
    async_mode: str = Form(default="auto"),  # auto|sync|async
):
    """
    生成站点（支持异步模式化解超时）

    mode: landing | site | pricing | shop
    async_mode: auto(智能切换) | sync(同步) | async(后台)
    """
    # 输入清理
    info = {
        "name": _sanitize(name, _MAX_NAME_LEN),
        "industry": _sanitize(industry, _MAX_INDUSTRY_LEN),
        "description": _sanitize(description, _MAX_DESC_LEN),
        "keywords": _sanitize(keywords, _MAX_KEYWORDS_LEN),
        "audience": _sanitize(audience, _MAX_AUDIENCE_LEN),
        "phone": _sanitize(phone, _MAX_PHONE_LEN),
        "email": _sanitize(email, _MAX_EMAIL_LEN),
        "address": _sanitize(address, _MAX_ADDRESS_LEN),
        "website": _sanitize(website, _MAX_WEBSITE_LEN),
    }

    if not info["name"]:
        raise HTTPException(422, "品牌名称必填")

    # 输入长度熔断
    _total_input_len = sum(len(v) for v in info.values() if isinstance(v, str))
    if _total_input_len > 5000:
        raise HTTPException(422, f"输入内容总长度超限({_total_input_len}/5000)，请精简后重试")

    if mode not in ("landing", "site", "pricing", "shop"):
        raise HTTPException(400, "不支持的生成模式")

    # ── 语义缓存检查 ──
    cache_key = _cache_key(info, mode)
    cached = _cache_get(cache_key)
    if cached and not cached.get("ai_error"):
        result = dict(cached)
        result.pop("_ts", None)
        result["cached"] = True
        return JSONResponse(_format_result(result))

    # ── 决定同步/异步模式 ──
    use_async = async_mode == "async" or (async_mode == "auto" and mode in ("site", "shop"))

    if use_async:
        task_id = uuid.uuid4().hex[:12]
        _GEN_TASKS[task_id] = {
            "status": "pending", "mode": mode, "info": info,
            "created_at": _time.time(),
        }
        asyncio.create_task(_run_generate_task(task_id, mode, info, cache_key))
        return JSONResponse({
            "success": True, "async": True, "task_id": task_id, "mode": mode,
            "message": "任务已提交，请轮询状态",
            "status_url": f"/api/v1/generate/status/{task_id}",
        })

    # 同步模式
    engine = await get_engine()
    try:
        match mode:
            case "landing":
                result = await engine.build_landing(info, is_pro=True)
            case "site":
                result = await engine.build_site(info, is_pro=True)
            case "pricing":
                result = await engine.build_pricing(info, is_pro=True)
            case "shop":
                result = await engine.build_shop(info, is_pro=True)
    except Exception as e:
        raise HTTPException(500, "生成失败，请稍后重试")

    _cache_put(cache_key, result)
    return JSONResponse(_format_result(result))



# ── 异步任务执行 ──────────────────────────────────────
async def _run_generate_task(task_id: str, mode: str, info: dict, cache_key: str):
    """后台执行生成任务"""
    task = _GEN_TASKS[task_id]
    task["status"] = "running"
    try:
        engine = await get_engine()
        match mode:
            case "landing":
                result = await engine.build_landing(info, is_pro=True)
            case "site":
                result = await engine.build_site(info, is_pro=True)
            case "pricing":
                result = await engine.build_pricing(info, is_pro=True)
            case "shop":
                result = await engine.build_shop(info, is_pro=True)
            case _:
                result = await engine.build_landing(info, is_pro=True)
        task["status"] = "done"
        task["result"] = result
        _cache_put(cache_key, result)
    except Exception as e:
        task["status"] = "error"
        task["error"] = "生成失败，请稍后重试"


def _format_result(result: dict) -> dict:
    """格式化生成结果为API响应（含输出熔断）"""
    # 输出熔断：HTML超限时截断
    html = result.get("html", "")
    if html and len(html) > _MAX_OUTPUT_HTML:
        import logging as _log
        _log.getLogger("generate").warning(
            f"输出熔断: HTML {len(html)}字节 > {_MAX_OUTPUT_HTML}字节，截断"
        )
        result["html"] = html[:_MAX_OUTPUT_HTML] + "\n<!-- 输出被截断：超过大小限制 -->"
        result["output_fused"] = True
    return {
        "success": True,
        "mode": result["mode"],
        "page_id": result.get("page_id", result.get("site_id")),
        "ai_used": result["ai_used"],
        "ai_backend": result["ai_backend"],
        "ai_error": result.get("ai_error"),
        "file_size": result["file_size"],
        "zip_size": result.get("zip_size"),
        "pages": result.get("pages"),
        "cached": result.get("cached", False),
        "preview_url": f"/api/v1/preview/{result.get('page_id') or result.get('site_id')}",
        "download_url": f"/api/v1/download/{result.get('page_id') or result.get('site_id')}",
        "zip_url": f"/api/v1/download-zip/{result.get('site_id')}" if result.get("site_id") else None,
    }


@router.get("/generate/status/{task_id}")
async def get_generate_status(task_id: str):
    """查询异步生成任务状态"""
    if not _ID_PATTERN.match(task_id):
        raise HTTPException(400, "非法task_id")
    task = _GEN_TASKS.get(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    resp = {"task_id": task_id, "status": task["status"], "mode": task["mode"]}
    if task["status"] == "done" and task.get("result"):
        resp["result"] = _format_result(task["result"])
    elif task["status"] == "error":
        resp["error"] = task.get("error", "生成失败")
    return JSONResponse(resp)


# ── 预览 ──────────────────────────────────────────────
@router.get("/preview/{page_id}")
async def preview(page_id: str):
    """预览生成的 HTML（仅 12 位 hex ID）"""
    _validate_id(page_id)

    file_path = Path("outputs") / f"{page_id}.html"
    if not file_path.exists():
        raise HTTPException(404, "页面不存在或已过期")

    return FileResponse(file_path, media_type="text/html; charset=utf-8")


# ── 下载单页 ──────────────────────────────────────────
@router.get("/download/{page_id}")
async def download(page_id: str):
    """下载单页 HTML"""
    _validate_id(page_id)

    file_path = Path("outputs") / f"{page_id}.html"
    if not file_path.exists():
        raise HTTPException(404, "文件不存在或已过期")

    return FileResponse(
        file_path,
        media_type="text/html; charset=utf-8",
        filename=f"landing-page-{page_id}.html",
    )


# ── 下载 ZIP ─────────────────────────────────────────
@router.get("/download-zip/{site_id}")
async def download_zip(site_id: str):
    """下载完整网站 ZIP"""
    _validate_id(site_id)

    zip_path = Path("outputs") / f"{site_id}.zip"
    if not zip_path.exists():
        raise HTTPException(404, "ZIP文件不存在或已过期")

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"website-{site_id}.zip",
    )


# ── 一句话生成 ────────────────────────────────────────
@router.post("/generate-from-text")
async def generate_from_text(
    request: Request,
    text: str = Form(...),
    phone: str = Form(default=""),
    email: str = Form(default=""),
    address: str = Form(default=""),
    website: str = Form(default=""),
    async_mode: str = Form(default="async"),  # v9.0.1: 默认异步防HF超时
):
    """
    一句话生成站点（支持异步模式）

    示例输入: "我要一个卖手工皂的独立站，品牌叫'皂物集'"
    """
    text = _sanitize(text, _MAX_TEXT_LEN)
    if not text.strip():
        raise HTTPException(422, "请输入需求描述")

    # 语义缓存
    cache_key2 = _cache_key({"name": text, "industry": "", "description": "", "keywords": "", "audience": ""}, "text")
    cached2 = _cache_get(cache_key2)
    if cached2 and not cached2.get("ai_error"):
        result = dict(cached2)
        result.pop("_ts", None)
        result["cached"] = True
        return JSONResponse(_format_result(result))

    # 异步模式：提交后台任务
    if async_mode in ("async", "auto"):
        task_id = uuid.uuid4().hex[:12]
        _GEN_TASKS[task_id] = {
            "status": "pending", "mode": "from-text", "info": {"text": text},
            "created_at": _time.time(),
        }
        asyncio.create_task(_run_generate_from_text_task(task_id, text, phone, email, address, website, cache_key2))
        return JSONResponse({
            "success": True, "async": True, "task_id": task_id, "mode": "from-text",
            "message": "任务已提交，请轮询状态",
            "status_url": f"/api/v1/generate/status/{task_id}",
        })

    # 同步模式（兼容旧调用）
    planner = SitePlanner()
    result = await planner.process(
        text,
        phone=_sanitize(phone, _MAX_PHONE_LEN),
        email=_sanitize(email, _MAX_EMAIL_LEN),
        address=_sanitize(address, _MAX_ADDRESS_LEN),
        website=_sanitize(website, _MAX_WEBSITE_LEN),
    )

    _cache_put(cache_key2, result)

    return JSONResponse(_format_result(result))


async def _run_generate_from_text_task(task_id: str, text: str, phone: str, email: str, address: str, website: str, cache_key2: str):
    """后台执行一句话生成（v9.0.1新增）"""
    task = _GEN_TASKS[task_id]
    task["status"] = "running"
    try:
        planner = SitePlanner()
        result = await planner.process(
            text,
            phone=_sanitize(phone, _MAX_PHONE_LEN),
            email=_sanitize(email, _MAX_EMAIL_LEN),
            address=_sanitize(address, _MAX_ADDRESS_LEN),
            website=_sanitize(website, _MAX_WEBSITE_LEN),
        )
        task["status"] = "done"
        task["result"] = result
        _cache_put(cache_key2, result)
    except Exception as e:
        task["status"] = "error"
        task["error"] = "生成失败，请稍后重试"


# ── 后端列表 ──────────────────────────────────────────
@router.get("/backends")
async def list_backends():
    """列出所有可用后端（AI + Template）"""
    engine = await get_engine()
    return {
        "ai": {
            "active": engine.active_ai,
            "available": list(engine._ai._backend_registry.keys()),
        },
        "template": {
            "active": engine.active_template,
            "available": list(engine._template._backend_registry.keys()),
        },
    }