"""AI商业命名与Slogan生成器 — 基于共享工具基类"""
from __future__ import annotations
import logging
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from apis.routes._tool_base import (
    check_rate_limit, check_daily_quota, get_quota_info,
    call_ai_with_retry, parse_ai_json, _clean_expired_tasks
)

router = APIRouter(prefix="/naming", tags=["naming"])
log = logging.getLogger("naming")

_NAME_TASKS: dict = {}

_NAME_STYLES = {
    "tech": {"name": "科技感", "emoji": "⚡", "desc": "简洁、未来、创新"},
    "elegant": {"name": "优雅风", "emoji": "✨", "desc": "精致、高端、品味"},
    "fun": {"name": "趣味型", "emoji": "🎮", "desc": "活泼、记忆点、传播力"},
    "professional": {"name": "专业感", "emoji": "🏛️", "desc": "可信、权威、稳重"},
    "global": {"name": "国际化", "emoji": "🌍", "desc": "跨文化、易发音、.com可用"},
}

def _build_name_prompt(description: str, style: str, industry: str, lang: str) -> str:
    style_info = _NAME_STYLES.get(style, _NAME_STYLES["tech"])
    return f"""你是一位品牌命名专家。请为以下业务生成品牌名+Slogan方案。

## 业务信息
- 业务描述：{description}
- 行业：{industry or '通用'}
- 命名风格：{style_info['name']}（{style_info['desc']}）
- 输出语言：{lang}

## 输出要求（严格JSON格式）
{{
  "summary": "命名策略概述（2-3句）",
  "names": [
    {{
      "name": "品牌名",
      "name_en": "英文名（如有）",
      "slogan": "品牌标语",
      "domain_hint": "建议域名（如brand.com）",
      "rationale": "命名理由（50字以内）",
      "vibe": "给人的感觉（3个关键词）",
      "score": 1-10
    }}
  ],
  "taglines": [
    {{"tagline": "备选Slogan", "scenario": "适用场景"}}
  ],
  "brand_story": "一个段落的品牌故事模板（含{{brand_name}}占位符）",
  "naming_tips": ["命名建议1", "命名建议2", "命名建议3"]
}}

要求：
1. names至少5个方案，风格多样化
2. taglines至少3个备选
3. 每个name必须有rationale解释为什么好
4. 品牌名要易读易记，避免生僻字
5. Slogan要有节奏感，适合口头传播
6. 用{lang}输出（英文名除外）
7. 绝对禁止使用：最强、最佳、第一、顶级等违反广告法的词汇"""

class NameRequest(BaseModel):
    description: str = Field(..., min_length=2, max_length=500)
    style: str = Field(default="tech")
    industry: str = Field(default="", max_length=100)
    lang: str = Field(default="zh")

@router.post("/generate")
async def generate_names(req: NameRequest, request: Request):
    client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() \
                or (request.client.host if request.client else "unknown")
    if not check_rate_limit(client_ip, "name", 5, 60):
        raise HTTPException(429, "请求过于频繁")
    
    await check_daily_quota(request)
    
    if req.style not in _NAME_STYLES:
        raise HTTPException(422, f"不支持的风格: {req.style}")
    
    import uuid, time
    task_id = str(uuid.uuid4())
    _NAME_TASKS[task_id] = {
        "status": "pending", "progress": "任务已提交", "_created": time.time(),
        "description": req.description, "style": req.style,
        "result": None, "error": None,
    }
    
    import asyncio
    asyncio.create_task(_run_name_generation(task_id, req.description, req.style, req.industry, req.lang))
    return {"success": True, "task_id": task_id}

async def _run_name_generation(task_id: str, description: str, style: str, industry: str, lang: str):
    _NAME_TASKS[task_id]["status"] = "generating"
    _NAME_TASKS[task_id]["progress"] = "AI正在构思品牌名..."
    try:
        prompt = _build_name_prompt(description, style, industry, lang)
        raw = await call_ai_with_retry(prompt)
        
        _NAME_TASKS[task_id]["progress"] = "正在整理方案..."
        result = parse_ai_json(raw)
        
        if result:
            _NAME_TASKS[task_id]["status"] = "done"
            _NAME_TASKS[task_id]["result"] = result
            _NAME_TASKS[task_id]["progress"] = "生成完成"
        else:
            _NAME_TASKS[task_id]["status"] = "error"
            _NAME_TASKS[task_id]["error"] = "AI返回格式异常，请重试"
    except Exception as e:
        log.error(f"naming generation error: {e}", exc_info=True)
        _NAME_TASKS[task_id]["status"] = "error"
        _NAME_TASKS[task_id]["error"] = "品牌命名失败，请稍后重试"

@router.get("/task/{task_id}")
async def get_name_task(task_id: str):
    _clean_expired_tasks(_NAME_TASKS)
    task = _NAME_TASKS.get(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    resp = {"success": True, "status": task["status"], "progress": task.get("progress", "")}
    if task["status"] == "done" and task.get("result"):
        resp["result"] = task["result"]
    elif task["status"] == "error":
        resp["error"] = task.get("error", "生成失败")
    return resp

@router.get("/quota")
async def get_name_quota(request: Request):
    return get_quota_info(request)

@router.get("/styles")
async def list_name_styles():
    return {"styles": [{"id": k, "name": v["name"], "emoji": v["emoji"], "desc": v["desc"]} 
                        for k, v in _NAME_STYLES.items()]}
