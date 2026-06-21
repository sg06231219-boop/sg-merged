"""AI短剧生成 API — 基于共享工具基类"""
from __future__ import annotations
import logging
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from apis.routes._tool_base import (
    check_rate_limit, check_daily_quota, get_quota_info,
    call_ai_with_retry, parse_ai_json, _clean_expired_tasks
)

router = APIRouter(prefix="/drama", tags=["drama"])
log = logging.getLogger("drama")

_DRAMA_TASKS: dict = {}

_STYLES = {
    "urban_romance": {"name": "都市情感", "emoji": "💕", "desc": "都市爱情故事，甜蜜虐恋交织"},
    "mystery": {"name": "悬疑推理", "emoji": "🔍", "desc": "烧脑悬疑，层层揭秘"},
    "ancient_fantasy": {"name": "古风仙侠", "emoji": "⚔️", "desc": "古风仙侠世界，修仙问道"},
    "workplace": {"name": "职场励志", "emoji": "💼", "desc": "职场成长，逆袭人生"},
    "campus": {"name": "校园青春", "emoji": "🎓", "desc": "青涩校园，热血青春"},
    "comedy": {"name": "搞笑日常", "emoji": "😂", "desc": "轻松幽默，笑料不断"},
}

def _build_drama_prompt(theme: str, style: str, episodes: int, duration: int) -> str:
    style_info = _STYLES.get(style, {"name": "通用", "emoji": "🎭", "desc": ""})
    return f"""你是一位专业的短剧编剧和导演，擅长创作高节奏、强冲突的短视频剧本。

## 任务
请根据以下要求创作一部完整的短剧剧本：

- **主题**: {theme}
- **风格**: {style_info['name']}
- **集数**: {episodes}集
- **每集时长**: {duration}分钟

## 输出要求
请严格按以下JSON格式输出，不要输出任何其他内容：

{{
  "title": "短剧名称(4-10字，朗朗上口)",
  "episodes": [
    {{
      "ep": 1,
      "title": "第1集标题",
      "scenes": [
        {{
          "scene": 1,
          "location": "场景描述(如：咖啡厅、办公室、公园)",
          "characters": "出场人物(如：女主林小夏、男主陆言)",
          "action": "画面动作描述(如：林小夏低头搅动咖啡，手机突然响起)",
          "dialogue": "台词内容(用角色名+冒号，多人用换行分隔)",
          "camera": "镜头语言(如：特写手部动作→切中景对坐→推近表情)",
          "duration": "预估时长(如：30秒)"
        }}
      ],
      "bgm": "配乐建议(如：轻柔钢琴曲，渐入弦乐)",
      "cliffhanger": "本集悬念/钩子(吸引观众看下一集)"
    }}
  ],
  "total_scenes": 总场景数,
  "total_duration": "总时长估算(如：约6分钟)",
  "tags": ["标签1", "标签2", "标签3"]
}}

## 创作规则
1. **节奏要快**: 每集开场3秒内必须有冲突或悬念
2. **对白精炼**: 每句台词不超过30字，多用潜台词
3. **视觉优先**: 动作描写具体可拍，少用内心独白
4. **钩子设计**: 每集结尾必须有强悬念(反转/揭露/意外)
5. **人物鲜明**: 主角有明确动机和性格特征
6. **每集场景数**: {duration}分钟约{duration * 3}-{duration * 5}个场景
7. **绝对禁止**: 不要写"镜头缓缓推进"等含糊描述，要写具体的镜头运动

直接输出JSON，不要用markdown代码块包裹。"""

class DramaRequest(BaseModel):
    theme: str = Field(..., min_length=2, max_length=500)
    style: str = Field(default="urban_romance")
    episodes: int = Field(default=1, ge=1, le=5)
    duration: int = Field(default=2, ge=1, le=3)

@router.post("/generate")
async def generate_drama(req: DramaRequest, request: Request):
    client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() \
                or (request.client.host if request.client else "unknown")
    if not check_rate_limit(client_ip, "drama", 5, 60):
        raise HTTPException(429, "请求过于频繁，请稍后再试")
    
    await check_daily_quota(request)
    
    if req.style not in _STYLES:
        raise HTTPException(422, f"不支持的风格: {req.style}")
    
    import uuid, time
    task_id = str(uuid.uuid4())
    _DRAMA_TASKS[task_id] = {
        "status": "pending", "progress": "任务已提交", "_created": time.time(),
        "theme": req.theme, "style": req.style,
        "episodes": req.episodes, "duration": req.duration,
        "result": None, "error": None,
    }
    
    import asyncio
    asyncio.create_task(_run_drama_generation(task_id, req.theme, req.style, req.episodes, req.duration))
    return {"success": True, "task_id": task_id}

async def _run_drama_generation(task_id: str, theme: str, style: str, episodes: int, duration: int):
    _DRAMA_TASKS[task_id]["status"] = "generating"
    _DRAMA_TASKS[task_id]["progress"] = "AI正在构思剧情..."
    try:
        prompt = _build_drama_prompt(theme, style, episodes, duration)
        raw = await call_ai_with_retry(prompt)
        
        _DRAMA_TASKS[task_id]["progress"] = "正在解析剧本..."
        result = parse_ai_json(raw)
        
        if result:
            # 确保episodes有实际内容
            eps = result.get("episodes", [])
            if eps and len(eps) > 0:
                total_scenes = sum(len(e.get("scenes", [])) for e in eps)
                if total_scenes == 0:
                    log.warning(f"drama task {task_id}: episodes exist but 0 scenes, result may be truncated")
            _DRAMA_TASKS[task_id]["status"] = "done"
            _DRAMA_TASKS[task_id]["result"] = result
            _DRAMA_TASKS[task_id]["progress"] = "生成完成"
        else:
            _DRAMA_TASKS[task_id]["status"] = "error"
            _DRAMA_TASKS[task_id]["error"] = "AI返回格式异常，请重试"
    except Exception as e:
        log.error(f"drama generation error: {e}", exc_info=True)
        _DRAMA_TASKS[task_id]["status"] = "error"
        _DRAMA_TASKS[task_id]["error"] = "短剧生成失败，请稍后重试"

@router.get("/task/{task_id}")
async def get_task(task_id: str):
    _clean_expired_tasks(_DRAMA_TASKS)
    task = _DRAMA_TASKS.get(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    resp = {"success": True, "status": task["status"], "progress": task.get("progress", "")}
    if task["status"] == "done" and task.get("result"):
        resp["result"] = task["result"]
    elif task["status"] == "error":
        resp["error"] = task.get("error", "生成失败")
    return resp

@router.get("/quota")
async def get_drama_quota(request: Request):
    return get_quota_info(request)

@router.get("/styles")
async def list_styles():
    return {"styles": [{"id": k, "name": v["name"], "emoji": v["emoji"], "desc": v["desc"]} 
                        for k, v in _STYLES.items()]}

@router.get("/examples")
async def get_examples():
    return {"examples": [
        {"theme": "实习生发现总裁的秘密", "style": "urban_romance"},
        {"theme": "一封匿名信牵出的十年悬案", "style": "mystery"},
        {"theme": "废柴修仙逆袭记", "style": "ancient_fantasy"},
        {"theme": "外卖小哥的创业路", "style": "workplace"},
    ]}
