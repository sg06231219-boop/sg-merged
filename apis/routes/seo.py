"""
apis.routes.seo — 程序化SEO引擎 API

核心差异化接口：
- POST /seo/seed    → 提交种子词，启动SEO生成流水线
- GET  /seo/task/{id} → 查询任务状态与进度
- GET  /seo/pages/{id} → 获取已生成的页面列表+关键词矩阵
- GET  /seo/sitemap/{id} → 下载sitemap.xml
- GET  /seo/demo     → 快速Demo（预置参数，一键展示）
"""

from __future__ import annotations

import asyncio
import logging
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import PlainTextResponse

from core.seo_engine import get_seo_engine, SEOEngine

logger = logging.getLogger("site-builder.api.seo")


_seo_task_owners = {}

def _verify_seo_owner(task_id: str, request: Request):
    owner_ip = _seo_task_owners.get(task_id)
    if not owner_ip:
        return
    client_ip = request.client.host if request.client else "unknown"
    if client_ip != owner_ip:
        raise HTTPException(403, "无权访问此资源")

router = APIRouter(prefix="/seo", tags=["SEO引擎"])


def _get_seo() -> SEOEngine:
    return get_seo_engine()


@router.post("/seed")
async def seed_keywords(
    request: Request,
    industry: str = Form(..., description="行业，如：科技、教育、医疗"),
    keywords: str = Form(default="", description="种子关键词，逗号分隔"),
    city: str = Form(default="", description="目标城市"),
    max_keywords: int = Form(default=50, description="最大关键词数"),
    max_pages: int = Form(default=50, description="最大生成页面数"),
):
    """
    提交SEO种子词，启动程序化SEO流水线：
    关键词挖掘 → 聚类 → 批量生成 → 内链 → Sitemap
    """
    seo = _get_seo()

    # 解析种子词
    seed_list = [k.strip() for k in keywords.split(",") if k.strip()]
    if not seed_list:
        # 如果没提供种子词，从行业模板取默认
        from core.seo_engine import _INDUSTRY_TEMPLATES, _DEFAULT_TEMPLATE
        tpl = _DEFAULT_TEMPLATE
        for key, t in _INDUSTRY_TEMPLATES.items():
            if key in industry or industry in key:
                tpl = t
                break
        seed_list = tpl["seeds"][:3]

    # 限制数量
    max_keywords = min(max_keywords, 200)
    max_pages = min(max_pages, 100)

    # 创建任务
    task = seo.create_task(industry, seed_list, city, max_keywords)

    # 后台执行流水线
    engine = None
    try:
        from core.engine import get_engine
        engine = await get_engine()
    except Exception:
        logger.warning("SiteBuilderEngine不可用，使用mock生成")

    base_url = str(request.base_url).rstrip("/")

    # 启动后台任务
    asyncio.create_task(
        seo.run_full_pipeline(task, engine, max_keywords, max_pages, base_url)
    )

    return {
        "task_id": task.task_id,
        "industry": task.industry,
        "seed_keywords": task.seed_keywords,
        "city": task.city,
        "status": task.status,
        "max_keywords": max_keywords,
        "max_pages": max_pages,
        "message": f"SEO流水线已启动，预计生成{max_keywords}个关键词、{max_pages}个页面",
    }


@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """查询SEO任务状态"""
    seo = _get_seo()
    task = seo.get_task(task_id)
    if not task:
        raise HTTPException(404, f"任务不存在: {task_id}")

    return {
        "task_id": task.task_id,
        "industry": task.industry,
        "seed_keywords": task.seed_keywords,
        "city": task.city,
        "status": task.status,
        "progress": task.progress,
        "total_keywords": task.total_keywords,
        "total_pages": task.total_pages,
        "error": task.error,
        "created_at": task.created_at,
        "finished_at": task.finished_at,
    }


@router.get("/pages/{task_id}")
async def get_pages(task_id: str):
    """获取任务生成的页面列表+关键词矩阵"""
    seo = _get_seo()
    task = seo.get_task(task_id)
    if not task:
        raise HTTPException(404, f"任务不存在: {task_id}")

    # 关键词统计
    intent_stats = {}
    for kw in task.keywords:
        intent = kw.intent.value
        intent_stats[intent] = intent_stats.get(intent, 0) + 1

    # 难度分布
    difficulty_avg = 0
    if task.keywords:
        difficulty_avg = round(sum(kw.difficulty for kw in task.keywords) / len(task.keywords), 2)

    # 搜索量TOP10
    top_keywords = sorted(task.keywords, key=lambda k: k.search_volume, reverse=True)[:10]

    return {
        "task_id": task.task_id,
        "status": task.status,
        "total_keywords": task.total_keywords,
        "total_pages": task.total_pages,
        "intent_distribution": intent_stats,
        "avg_difficulty": difficulty_avg,
        "top_keywords": [
            {
                "keyword": kw.text,
                "volume": kw.search_volume,
                "difficulty": kw.difficulty,
                "intent": kw.intent.value,
                "cluster": kw.cluster_id,
            }
            for kw in top_keywords
        ],
        "pages": task.pages[:50],  # 最多返回50条
        "sitemap_path": task.sitemap_path,
    }


@router.get("/sitemap/{task_id}")
async def get_sitemap(task_id: str):
    """下载sitemap.xml"""
    seo = _get_seo()
    task = seo.get_task(task_id)
    if not task:
        raise HTTPException(404, f"任务不存在: {task_id}")
    if not task.sitemap_path:
        raise HTTPException(404, "Sitemap尚未生成")

    from pathlib import Path
    path = Path(task.sitemap_path)
    if not path.exists():
        raise HTTPException(404, "Sitemap文件不存在")

    content = path.read_text(encoding="utf-8")
    return PlainTextResponse(content, media_type="application/xml")


@router.get("/demo")
async def seo_demo(request: Request):
    """
    一键Demo：使用预置参数快速展示程序化SEO效果
    评委/投资人打开就能看到结果
    """
    seo = _get_seo()

    # 预置参数：科技行业 + 杭州
    task = seo.create_task("科技", ["软件开发", "APP开发", "小程序"], "杭州", 30)

    # 先做关键词扩展（快速，不需要AI）
    keywords = seo.expand_keywords(task, 30)

    # 立即返回关键词矩阵（不需要等页面生成完）
    intent_stats = {}
    for kw in keywords:
        intent = kw.intent.value
        intent_stats[intent] = intent_stats.get(intent, 0) + 1

    top_keywords = sorted(keywords, key=lambda k: k.search_volume, reverse=True)[:15]

    # 后台继续生成页面
    engine = None
    try:
        from core.engine import get_engine
        engine = await get_engine()
    except Exception:
        pass

    base_url = str(request.base_url).rstrip("/")
    asyncio.create_task(
        seo.run_full_pipeline(task, engine, max_keywords=30, max_pages=30, base_url=base_url)
    )

    return {
        "task_id": task.task_id,
        "demo": True,
        "industry": "科技",
        "city": "杭州",
        "seed_keywords": ["软件开发", "APP开发", "小程序"],
        "total_keywords": len(keywords),
        "intent_distribution": intent_stats,
        "top_keywords": [
            {
                "keyword": kw.text,
                "volume": kw.search_volume,
                "difficulty": kw.difficulty,
                "intent": kw.intent.value,
            }
            for kw in top_keywords
        ],
        "status": task.status,
        "message": f"关键词矩阵已生成（{len(keywords)}个），页面正在后台批量生成中...",
    }


@router.get("/tasks")
async def list_tasks():
    """列出所有SEO任务"""
    seo = _get_seo()
    return {"tasks": seo.list_tasks()}
