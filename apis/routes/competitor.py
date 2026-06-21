"""AI竞品分析器 — 基于共享工具基类"""
from __future__ import annotations
import logging
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from apis.routes._tool_base import (
    check_rate_limit, check_daily_quota, get_quota_info,
    call_ai_with_retry, parse_ai_json, _clean_expired_tasks
)

router = APIRouter(prefix="/competitor", tags=["competitor"])
log = logging.getLogger("competitor")

_COMP_TASKS: dict = {}

_COMP_DIMS = {
    "pricing": {"name": "定价策略", "emoji": "💰"},
    "features": {"name": "功能对比", "emoji": "⚡"},
    "marketing": {"name": "营销策略", "emoji": "📊"},
    "ux": {"name": "用户体验", "emoji": "🎨"},
    "full": {"name": "全面分析", "emoji": "🔍"},
}

def _build_comp_prompt(my_product: str, competitors: str, dimension: str, lang: str) -> str:
    dim_info = _COMP_DIMS.get(dimension, _COMP_DIMS["full"])
    return f"""你是一位资深商业分析师。请对以下产品进行竞品分析。

## 分析对象
- 我的产品/服务：{my_product}
- 竞品：{competitors}
- 分析维度：{dim_info['name']}
- 输出语言：{lang}

## 输出要求（严格JSON格式）
{{
  "executive_summary": "3-5句的核心发现",
  "market_position": {{
    "my_position": "我的定位描述",
    "competitor_positions": ["竞品1定位", "竞品2定位"],
    "gaps": ["市场空白1", "市场空白2"],
    "opportunities": ["机会1", "机会2", "机会3"]
  }},
  "comparison": [
    {{
      "dimension": "对比维度名",
      "my_score": 1-10,
      "comp_scores": [{{"name": "竞品名", "score": 1-10}}],
      "analysis": "简短分析",
      "action": "建议行动"
    }}
  ],
  "swot": {{
    "strengths": ["优势1", "优势2"],
    "weaknesses": ["劣势1", "劣势2"],
    "opportunities": ["机会1", "机会2"],
    "threats": ["威胁1", "威胁2"]
  }},
  "action_plan": [
    {{"priority": 1, "action": "行动项", "timeline": "时间线", "impact": "预期影响"}}
  ]
}}

要求：
1. comparison至少4个维度
2. SWOT每项至少2条
3. action_plan至少3项，按优先级排序
4. 所有分析和建议必须具体可执行，不要泛泛而谈
5. 用{lang}输出
6. 绝对禁止使用：最强、最佳、第一、顶级等违反广告法的词汇"""

class CompRequest(BaseModel):
    my_product: str = Field(..., min_length=2, max_length=500)
    competitors: str = Field(..., min_length=2, max_length=500)
    dimension: str = Field(default="full")
    lang: str = Field(default="zh")

@router.post("/analyze")
async def analyze_competitor(req: CompRequest, request: Request):
    client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() \
                or (request.client.host if request.client else "unknown")
    if not check_rate_limit(client_ip, "comp", 3, 60):
        raise HTTPException(429, "请求过于频繁")
    
    await check_daily_quota(request)
    
    if req.dimension not in _COMP_DIMS:
        raise HTTPException(422, f"不支持的维度: {req.dimension}")
    
    import uuid, time
    task_id = str(uuid.uuid4())
    _COMP_TASKS[task_id] = {
        "status": "pending", "progress": "任务已提交", "_created": time.time(),
        "my_product": req.my_product, "competitors": req.competitors,
        "dimension": req.dimension, "result": None, "error": None,
    }
    
    import asyncio
    asyncio.create_task(_run_comp_analysis(task_id, req.my_product, req.competitors, req.dimension, req.lang))
    return {"success": True, "task_id": task_id}

async def _run_comp_analysis(task_id: str, my_product: str, competitors: str, dimension: str, lang: str):
    _COMP_TASKS[task_id]["status"] = "generating"
    _COMP_TASKS[task_id]["progress"] = "AI正在分析竞品..."
    try:
        prompt = _build_comp_prompt(my_product, competitors, dimension, lang)
        raw = await call_ai_with_retry(prompt)
        
        _COMP_TASKS[task_id]["progress"] = "正在整理报告..."
        result = parse_ai_json(raw)
        
        if result:
            _COMP_TASKS[task_id]["status"] = "done"
            _COMP_TASKS[task_id]["result"] = result
            _COMP_TASKS[task_id]["progress"] = "分析完成"
        else:
            _COMP_TASKS[task_id]["status"] = "error"
            _COMP_TASKS[task_id]["error"] = "AI返回格式异常，请重试"
    except Exception as e:
        log.error(f"competitor analysis error: {e}", exc_info=True)
        _COMP_TASKS[task_id]["status"] = "error"
        _COMP_TASKS[task_id]["error"] = "分析失败，请稍后重试"

@router.get("/task/{task_id}")
async def get_comp_task(task_id: str):
    _clean_expired_tasks(_COMP_TASKS)
    task = _COMP_TASKS.get(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    resp = {"success": True, "status": task["status"], "progress": task.get("progress", "")}
    if task["status"] == "done" and task.get("result"):
        resp["result"] = task["result"]
    elif task["status"] == "error":
        resp["error"] = task.get("error", "分析失败")
    return resp

@router.get("/quota")
async def get_comp_quota(request: Request):
    return get_quota_info(request)

@router.get("/dimensions")
async def list_dimensions():
    return {"dimensions": [{"id": k, "name": v["name"], "emoji": v["emoji"]} 
                            for k, v in _COMP_DIMS.items()]}
