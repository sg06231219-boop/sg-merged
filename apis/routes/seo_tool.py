"""AI SEO关键词分析器 — 基于共享工具基类"""
from __future__ import annotations
import logging
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from apis.routes._tool_base import (
    check_rate_limit, check_daily_quota, get_quota_info,
    call_ai_with_retry, parse_ai_json, _clean_expired_tasks
)

router = APIRouter(prefix="/seo-tool", tags=["seo-tool"])
log = logging.getLogger("seo-tool")

# ── 异步任务存储 ──────────────────────────────────────
_SEO_TASKS: dict = {}

# ── 风格定义 ──────────────────────────────────────────
_SEO_STYLES = {
    "ecommerce": {"name": "电商出海", "emoji": "🛒", "desc": "产品页/类目页/购物广告关键词"},
    "saas": {"name": "SaaS工具", "emoji": "💻", "desc": "功能词/替代词/长尾问题词"},
    "content": {"name": "内容媒体", "emoji": "📝", "desc": "信息词/话题词/趋势词"},
    "local": {"name": "本地服务", "emoji": "📍", "desc": "地域词/近我词/评价词"},
    "b2b": {"name": "B2B企业", "emoji": "🏢", "desc": "采购词/方案词/对比词"},
}

def _build_seo_prompt(industry: str, style: str, lang: str, competitor: str) -> str:
    style_info = _SEO_STYLES.get(style, _SEO_STYLES["ecommerce"])
    return f"""你是一位资深SEO策略师，擅长Google出海SEO。请为以下业务生成完整的关键词策略。

## 业务信息
- 行业/产品：{industry}
- 业务类型：{style_info['name']}（{style_info['desc']}）
- 目标市场语言：{lang}
{"- 竞品参考：" + competitor if competitor else ""}

## 输出要求（严格JSON格式）
{{
  "summary": "2-3句话的SEO策略总览",
  "keyword_matrix": [
    {{
      "keyword": "核心关键词",
      "search_intent": "informational/navigational/commercial/transactional",
      "difficulty": "low/medium/high",
      "volume": "预估月搜索量(数字)",
      "priority": 1-5,
      "content_type": "建议内容类型(blog/product/landing/faq)",
      "serp_features": ["featured_snippet", "people_also_ask", "image_pack"]
    }}
  ],
  "long_tail": [
    {{"keyword": "长尾关键词", "intent": "搜索意图", "volume": "预估量"}}
  ],
  "content_plan": [
    {{"keyword": "目标关键词", "title": "建议文章标题", "type": "blog/product/landing", "priority": 1-3}}
  ],
  "competitor_gaps": ["竞品有但我没有的关键词机会1", "机会2", "机会3"],
  "technical_tips": ["技术SEO建议1", "建议2", "建议3"]
}}

要求：
1. keyword_matrix至少8个关键词，覆盖4种搜索意图
2. long_tail至少5个
3. content_plan至少5篇
4. 所有关键词必须是{lang}语言
5. 不要编造具体搜索量数字，用合理预估
6. 绝对禁止使用：最强、最佳、第一、顶级、爆款、全网最低、永久免费等违反广告法的词汇"""

class SeoAnalyzeRequest(BaseModel):
    industry: str = Field(..., min_length=2, max_length=200)
    style: str = Field(default="ecommerce")
    lang: str = Field(default="en")
    competitor: str = Field(default="", max_length=200)

@router.post("/analyze")
async def analyze_seo(req: SeoAnalyzeRequest, request: Request):
    client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() \
                or (request.client.host if request.client else "unknown")
    if not check_rate_limit(client_ip, "seo", 5, 60):
        raise HTTPException(429, "请求过于频繁")
    
    await check_daily_quota(request)
    
    if req.style not in _SEO_STYLES:
        raise HTTPException(422, f"不支持的业务类型: {req.style}")
    
    import uuid, time
    task_id = str(uuid.uuid4())
    _SEO_TASKS[task_id] = {
        "status": "pending", "progress": "任务已提交", "_created": time.time(),
        "industry": req.industry, "style": req.style,
        "result": None, "error": None,
    }
    
    import asyncio
    asyncio.create_task(_run_seo_analysis(task_id, req.industry, req.style, req.lang, req.competitor))
    return {"success": True, "task_id": task_id}

async def _run_seo_analysis(task_id: str, industry: str, style: str, lang: str, competitor: str):
    _SEO_TASKS[task_id]["status"] = "generating"
    _SEO_TASKS[task_id]["progress"] = "AI正在分析关键词..."
    try:
        prompt = _build_seo_prompt(industry, style, lang, competitor)
        raw = await call_ai_with_retry(prompt)
        
        _SEO_TASKS[task_id]["progress"] = "正在整理分析结果..."
        result = parse_ai_json(raw)
        
        if result:
            _SEO_TASKS[task_id]["status"] = "done"
            _SEO_TASKS[task_id]["result"] = result
            _SEO_TASKS[task_id]["progress"] = "分析完成"
        else:
            _SEO_TASKS[task_id]["status"] = "error"
            _SEO_TASKS[task_id]["error"] = "AI返回格式异常，请重试"
    except Exception as e:
        log.error(f"seo analysis error: {e}", exc_info=True)
        _SEO_TASKS[task_id]["status"] = "error"
        _SEO_TASKS[task_id]["error"] = f"分析失败: {str(e)[:100]}"

@router.get("/task/{task_id}")
async def get_seo_task(task_id: str):
    _clean_expired_tasks(_SEO_TASKS)
    task = _SEO_TASKS.get(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    resp = {"success": True, "status": task["status"], "progress": task.get("progress", "")}
    if task["status"] == "done" and task.get("result"):
        resp["result"] = task["result"]
    elif task["status"] == "error":
        resp["error"] = task.get("error", "分析失败")
    return resp

@router.get("/quota")
async def get_seo_quota(request: Request):
    return get_quota_info(request)

@router.get("/styles")
async def list_seo_styles():
    return {"styles": [{"id": k, "name": v["name"], "emoji": v["emoji"], "desc": v["desc"]} 
                        for k, v in _SEO_STYLES.items()]}
