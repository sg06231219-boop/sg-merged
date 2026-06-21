"""AI营销文案生成器 — 基于共享工具基类"""
from __future__ import annotations
import logging
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from apis.routes._tool_base import (
    check_rate_limit, check_daily_quota, get_quota_info,
    call_ai_with_retry, parse_ai_json, _clean_expired_tasks
)

router = APIRouter(prefix="/copywrite", tags=["copywrite"])
log = logging.getLogger("copywrite")

_COPY_TASKS: dict = {}

_COPY_TYPES = {
    "ad": {"name": "广告语", "emoji": "📢", "desc": "简短有力的广告标语"},
    "social": {"name": "社媒文案", "emoji": "📱", "desc": "适合小红书/抖音/Instagram"},
    "email": {"name": "邮件营销", "emoji": "📧", "desc": "开发信/促销邮件/Newsletter"},
    "landing": {"name": "着陆页文案", "emoji": "🖥️", "desc": "Headline+Features+CTA"},
    "product": {"name": "产品描述", "emoji": "📦", "desc": "电商产品详情文案"},
}

def _build_copy_prompt(product: str, copy_type: str, tone: str, audience: str, lang: str) -> str:
    type_info = _COPY_TYPES.get(copy_type, _COPY_TYPES["ad"])
    return f"""你是一位顶尖营销文案师。请为以下产品生成{type_info['name']}。

## 产品信息
- 产品/品牌：{product}
- 文案类型：{type_info['name']}（{type_info['desc']}）
- 语调：{tone}
- 目标受众：{audience or '通用'}
- 输出语言：{lang}

## 输出要求（严格JSON格式）
{{
  "headline": "主标题/核心卖点（1句话）",
  "copies": [
    {{
      "title": "方案标题",
      "body": "文案正文",
      "hook": "开头钩子（吸引注意的第一句）",
      "cta": "行动号召语",
      "platform": "适用平台",
      "tips": "使用建议"
    }}
  ],
  "variations": ["备选短文案1", "备选短文案2", "备选短文案3"],
  "hashtags": ["#标签1", "#标签2", "#标签3", "#标签4", "#标签5"]
}}

要求：
1. copies至少3个方案，风格各有侧重
2. 每个方案的body长度适合对应平台（广告语<50字，社媒100-300字，邮件200-500字，着陆页300-800字，产品描述200-400字）
3. hook必须能在3秒内抓住注意力
4. CTA必须有紧迫感或利益驱动
5. 文案必须用{lang}书写
6. 绝对禁止使用：最强、最佳、第一、顶级、爆款、全网最低、永久免费等违反广告法的词汇
7. 不要空洞的口号，每个字都要有信息量"""

class CopyRequest(BaseModel):
    product: str = Field(..., min_length=2, max_length=500)
    copy_type: str = Field(default="ad")
    tone: str = Field(default="professional")
    audience: str = Field(default="", max_length=200)
    lang: str = Field(default="zh")

@router.post("/generate")
async def generate_copy(req: CopyRequest, request: Request):
    client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() \
                or (request.client.host if request.client else "unknown")
    if not check_rate_limit(client_ip, "copy", 5, 60):
        raise HTTPException(429, "请求过于频繁")
    
    await check_daily_quota(request)
    
    if req.copy_type not in _COPY_TYPES:
        raise HTTPException(422, f"不支持的文案类型: {req.copy_type}")
    
    import uuid, time
    task_id = str(uuid.uuid4())
    _COPY_TASKS[task_id] = {
        "status": "pending", "progress": "任务已提交", "_created": time.time(),
        "product": req.product, "copy_type": req.copy_type,
        "result": None, "error": None,
    }
    
    import asyncio
    asyncio.create_task(_run_copy_generation(task_id, req.product, req.copy_type, req.tone, req.audience, req.lang))
    return {"success": True, "task_id": task_id}

async def _run_copy_generation(task_id: str, product: str, copy_type: str, tone: str, audience: str, lang: str):
    _COPY_TASKS[task_id]["status"] = "generating"
    _COPY_TASKS[task_id]["progress"] = "AI正在创作文案..."
    try:
        prompt = _build_copy_prompt(product, copy_type, tone, audience, lang)
        raw = await call_ai_with_retry(prompt)
        
        _COPY_TASKS[task_id]["progress"] = "正在整理文案..."
        result = parse_ai_json(raw)
        
        if result:
            _COPY_TASKS[task_id]["status"] = "done"
            _COPY_TASKS[task_id]["result"] = result
            _COPY_TASKS[task_id]["progress"] = "生成完成"
        else:
            _COPY_TASKS[task_id]["status"] = "error"
            _COPY_TASKS[task_id]["error"] = "AI返回格式异常，请重试"
    except Exception as e:
        log.error(f"copy generation error: {e}", exc_info=True)
        _COPY_TASKS[task_id]["status"] = "error"
        _COPY_TASKS[task_id]["error"] = "文案生成失败，请稍后重试"

@router.get("/task/{task_id}")
async def get_copy_task(task_id: str):
    _clean_expired_tasks(_COPY_TASKS)
    task = _COPY_TASKS.get(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    resp = {"success": True, "status": task["status"], "progress": task.get("progress", "")}
    if task["status"] == "done" and task.get("result"):
        resp["result"] = task["result"]
    elif task["status"] == "error":
        resp["error"] = task.get("error", "生成失败")
    return resp

@router.get("/quota")
async def get_copy_quota(request: Request):
    return get_quota_info(request)

@router.get("/types")
async def list_copy_types():
    return {"types": [{"id": k, "name": v["name"], "emoji": v["emoji"], "desc": v["desc"]} 
                       for k, v in _COPY_TYPES.items()]}
