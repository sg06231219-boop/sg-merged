"""
职慧Agent — 职业教育岗位技能智能体
合并路由模块 (zhihui-agent/app.py + apis/routes/* 子模块)
XA-202603 挑战杯揭榜挂帅参赛项目

路由前缀: /zhihui
"""
import os
import json
import time
import threading
import secrets
import traceback
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Request, Response, Cookie, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

import requests

# ============================================================
# 路径常量（从 sg-merged 根出发）
# ============================================================
ROOT_DIR = Path(__file__).resolve().parent.parent.parent  # sg-merged/
DATA_DIR = ROOT_DIR / "data"
STATIC_DIR = ROOT_DIR / "static" / "zhihui"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# 环境变量 / 配置
# ============================================================
ZHIPUAI_API_KEY = os.environ.get(
    "ZHIPUAI_API_KEY",
    "a3a3123abff546999aeb4547885c4ae8.PocEri894pv9APeu"
)
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Lys13579")

# ============================================================
# 主路由
# ============================================================
router = APIRouter(prefix="/zhihui", tags=["zhihui"])


# ============================================================
# 一、app.py 原始路由
# ============================================================

@router.get("/")
async def index():
    """首页"""
    return FileResponse(str(STATIC_DIR / "index.html"))


@router.get("/api/v1/health")
async def health():
    """健康检查"""
    api_key = bool(os.environ.get("ZHIPUAI_API_KEY"))
    return {
        "status": "ok" if api_key else "degraded",
        "service": "zhihui-agent",
        "version": "1.3.2",
        "api_key_configured": api_key,
    }


@router.get("/api/v1/stats")
async def get_stats():
    """返回服务统计信息"""
    kb_path = DATA_DIR / "knowledge_base.json"
    history_path = DATA_DIR / "skill_map_history.json"
    kb_count = 0
    history_count = 0
    try:
        with open(kb_path, "r", encoding="utf-8") as f:
            kb_count = len(json.load(f))
    except Exception:
        pass
    try:
        with open(history_path, "r", encoding="utf-8") as f:
            history_count = len(json.load(f))
    except Exception:
        pass
    return {
        "service": "zhihui-agent",
        "version": "1.3.2",
        "knowledge_base_entries": kb_count,
        "skill_map_history_count": history_count,
        "api_key_configured": bool(os.environ.get("ZHIPUAI_API_KEY")),
    }


@router.get("/robots.txt")
async def robots():
    """robots.txt"""
    return FileResponse(str(STATIC_DIR / "robots.txt"), media_type="text/plain")


@router.get("/admin")
async def admin_page():
    """管理后台页面"""
    return FileResponse(str(STATIC_DIR / "admin.html"))


@router.get("/api/v1/knowledge-base")
async def knowledge_base():
    """返回知识库数据（前端直调智谱API时需要）"""
    kb_path = DATA_DIR / "knowledge_base.json"
    try:
        with open(kb_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


# ============================================================
# 二、skill_map 子模块 (POST /skill-map, GET /skill-map/history, POST /new-job)
# ============================================================

class SkillMapRequest(BaseModel):
    job_name: str
    major: str = "软件技术"


class NewJobRequest(BaseModel):
    trend_keywords: List[str]


def _load_knowledge_base() -> list:
    """加载本地知识库"""
    kb_path = DATA_DIR / "knowledge_base.json"
    try:
        with open(kb_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_history(job_name: str, major: str, result: dict):
    """保存图谱生成历史"""
    history_file = DATA_DIR / "skill_map_history.json"
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
    except Exception:
        history = []
    history.append({"job_name": job_name, "major": major, "result": result})
    history = history[-20:]
    try:
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _fallback_skill_map(job_name: str, major: str) -> dict:
    """AI失败时的完整预置图谱数据"""
    return {
        "job_name": job_name,
        "major": major,
        "skill_tree": {
            "核心能力": [
                {"name": "HTML5语义化", "level": "基础", "description": "掌握HTML5语义化标签，理解Web标准与可访问性"},
                {"name": "CSS3布局与动画", "level": "基础", "description": "Flexbox/Grid布局，CSS动画与过渡，响应式设计"},
                {"name": "JavaScript核心", "level": "核心", "description": "ES6+语法、DOM操作、异步编程、模块化开发"},
                {"name": "前端框架应用", "level": "进阶", "description": "Vue3/React等主流框架，组件化开发模式"},
                {"name": "工程化工具", "level": "进阶", "description": "Webpack/Vite构建工具，代码规范与自动化"},
                {"name": "网络通信", "level": "核心", "description": "HTTP协议、RESTful API、跨域处理、WebSocket"},
                {"name": "性能优化", "level": "高级", "description": "加载优化、渲染优化、代码分割、监控告警"},
                {"name": "安全防护", "level": "进阶", "description": "XSS/CSRF防御、CSP策略、HTTPS与加密"},
            ],
            "专业技能": [
                {"name": "组件化开发", "tools": ["Vue3", "React"], "proficiency": "熟练掌握"},
                {"name": "状态管理", "tools": ["Pinia", "Redux", "Vuex"], "proficiency": "熟练掌握"},
                {"name": "前端路由", "tools": ["Vue Router", "React Router"], "proficiency": "熟练掌握"},
                {"name": "响应式设计", "tools": ["媒体查询", "Tailwind CSS", "Bootstrap"], "proficiency": "掌握"},
                {"name": "数据可视化", "tools": ["ECharts", "D3.js", "Chart.js"], "proficiency": "了解"},
                {"name": "移动端开发", "tools": ["Uni-app", "微信小程序", "React Native"], "proficiency": "掌握"},
                {"name": "TypeScript", "tools": ["TypeScript"], "proficiency": "熟练掌握"},
                {"name": "Node.js后端", "tools": ["Express", "Koa"], "proficiency": "了解"},
                {"name": "自动化测试", "tools": ["Jest", "Cypress", "Vitest"], "proficiency": "掌握"},
                {"name": "CI/CD部署", "tools": ["GitHub Actions", "Jenkins", "Docker"], "proficiency": "了解"},
            ],
            "工具技能": [
                {"name": "Git版本控制", "category": "协作工具", "importance": "必备"},
                {"name": "VS Code", "category": "开发工具", "importance": "必备"},
                {"name": "Chrome DevTools", "category": "调试工具", "importance": "必备"},
                {"name": "Postman / Apifox", "category": "测试工具", "importance": "推荐"},
                {"name": "Figma", "category": "设计工具", "importance": "推荐"},
                {"name": "Docker", "category": "部署工具", "importance": "推荐"},
            ],
            "软技能": [
                {"name": "沟通协作", "scenario": "团队协作、需求对接、代码评审"},
                {"name": "问题分析", "scenario": "Bug定位、性能排查、架构决策"},
                {"name": "持续学习", "scenario": "技术迭代跟进、社区参与"},
                {"name": "代码审查", "scenario": "Pull Request审查、规范执行"},
                {"name": "文档撰写", "scenario": "技术文档、README、API文档"},
            ],
        },
        "career_path": [
            {"stage": "入门期", "duration": "0-3个月", "milestones": ["掌握HTML/CSS/JS基础", "能独立完成静态页面", "理解Web标准与浏览器兼容"]},
            {"stage": "初级前端", "duration": "3-12个月", "milestones": ["掌握一个前端框架", "能完成完整项目", "理解组件化开发", "掌握基本调试技能"]},
            {"stage": "中级前端", "duration": "1-3年", "milestones": ["掌握工程化工具", "性能优化实践", "主导项目开发", "参与技术选型"]},
            {"stage": "高级前端", "duration": "3年+", "milestones": ["架构设计能力", "跨端开发经验", "技术选型决策", "团队技术指导"]},
        ],
        "related_jobs": ["全栈开发工程师", "前端架构师", "Web性能工程师", "小程序开发工程师", "前端技术经理"],
    }


@router.post("/api/v1/skill-map")
async def create_skill_map(req: SkillMapRequest):
    """生成岗位能力图谱（AI + fallback）"""
    from zhihui_core.agents.skill_map_agent import build_skill_map

    try:
        result = build_skill_map(req.job_name, req.major)
    except Exception as e:
        result = _fallback_skill_map(req.job_name, req.major)
        result["warning"] = "AI生成失败，使用预置数据"

    if not result.get("knowledge_points"):
        result["knowledge_points"] = _load_knowledge_base()

    _save_history(req.job_name, req.major, result)
    return result


@router.get("/api/v1/skill-map/history")
async def get_skill_map_history():
    """获取图谱生成历史"""
    history_file = DATA_DIR / "skill_map_history.json"
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


@router.post("/api/v1/new-job")
async def discover_new_job(req: NewJobRequest):
    """发现新岗位（赛题要求），AI失败时使用fallback"""
    from zhihui_core.agents.skill_map_agent import discover_new_job

    try:
        result = discover_new_job(req.trend_keywords)
    except Exception as e:
        kw = ", ".join(req.trend_keywords)
        result = {
            "job_name": f"{req.trend_keywords[0]}应用工程师",
            "core_responsibility": f"将{kw}技术应用于实际业务场景，推动技术落地与创新",
            "required_skills": [req.trend_keywords[0], "Python", "API集成", "问题分析"],
            "bonus_skills": ["项目管理", "团队协作", "行业知识"],
            "scenarios": ["企业数字化转型", "智能化产品开发", "技术咨询与服务"],
            "why_emerging": f"随着{kw}等技术的快速发展，市场对能够将新技术与业务结合的复合型人才需求激增。",
            "warning": "AI分析失败，使用基础模板",
        }
    return result


# ============================================================
# 三、learn_path 子模块 (POST /diagnose, POST /learn-path)
# ============================================================

class DiagnoseRequest(BaseModel):
    user_profile: Dict
    target_job: str


class LearnPathRequest(BaseModel):
    diagnosis: Dict
    target_job: str
    weeks: int = 12


@router.post("/api/v1/diagnose")
async def diagnose(req: DiagnoseRequest):
    """学情诊断"""
    from zhihui_core.agents.learn_path_agent import diagnose_learning

    try:
        result = diagnose_learning(req.user_profile, req.target_job)
    except Exception as e:
        skills = req.user_profile.get("skills", [])
        result = {
            "match_score": min(len(skills) * 8, 60),
            "gap_level": {
                "核心能力": {"gap": 2, "detail": "部分缺失"},
                "专业技能": {"gap": 2, "detail": "需要加强"},
                "工具技能": {"gap": 1, "detail": "基本掌握"},
                "软技能": {"gap": 1, "detail": "需实践提升"},
            },
            "diagnosis_summary": f"已掌握{len(skills)}项技能，与目标岗位{req.target_job}存在一定差距，建议系统学习。",
            "warning": "AI诊断失败，使用基础诊断",
        }

    diag_file = DATA_DIR / "diagnoses.json"
    try:
        with open(diag_file, "r", encoding="utf-8") as f:
            records = json.load(f)
    except Exception:
        records = []
    records.append({"target_job": req.target_job, "result": result})
    records = records[-20:]
    with open(diag_file, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    return result


@router.post("/api/v1/learn-path")
async def generate_learn_path(req: LearnPathRequest):
    """生成学习路径"""
    from zhihui_core.agents.learn_path_agent import generate_learning_path

    try:
        result = generate_learning_path(req.diagnosis, req.target_job, req.weeks)
    except Exception as e:
        result = {
            "path": [
                {
                    "phase": "Phase 1: 基础夯实",
                    "weeks": f"第1-{req.weeks // 3}周",
                    "tasks": [
                        {"task_name": "HTML5/CSS3核心", "knowledge_points": ["HTML5语义化", "CSS3 Flexbox/Grid"], "practice": "完成3个静态页面"},
                        {"task_name": "JavaScript核心", "knowledge_points": ["ES6+语法", "DOM操作", "异步编程"], "practice": "实现交互组件"},
                    ],
                    "milestone": "能独立完成响应式页面",
                },
                {
                    "phase": "Phase 2: 框架实战",
                    "weeks": f"第{req.weeks // 3 + 1}-{req.weeks * 2 // 3}周",
                    "tasks": [
                        {"task_name": "Vue3/React入门", "knowledge_points": ["组件化开发", "状态管理", "路由"], "practice": "完成SPA项目"},
                    ],
                    "milestone": "能使用框架完成完整项目",
                },
                {
                    "phase": "Phase 3: 进阶提升",
                    "weeks": f"第{req.weeks * 2 // 3 + 1}-{req.weeks}周",
                    "tasks": [
                        {"task_name": "工程化与性能优化", "knowledge_points": ["Webpack/Vite", "性能优化", "安全防护"], "practice": "优化项目性能"},
                    ],
                    "milestone": "达到岗位基本要求",
                },
            ],
            "growth_trajectory": [
                {"week": 0, "score": 30},
                {"week": req.weeks // 3, "score": 55},
                {"week": req.weeks * 2 // 3, "score": 75},
                {"week": req.weeks, "score": 85},
            ],
            "warning": "AI生成失败，使用预置学习路径",
        }
    return result


# ============================================================
# 四、chat 子模块 (POST /chat)
# ============================================================

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    context: Optional[str] = None


_FALLBACK_QA = {
    "html": "HTML5是前端开发的基础，重点掌握语义化标签（header/nav/main/article/footer）、表单增强、Canvas和多媒体API。建议参考MDN Web Docs系统学习。",
    "css": "CSS3核心包括：Flexbox/Grid布局、动画过渡、媒体查询响应式设计、CSS变量。推荐从Flexbox布局开始，逐步掌握Grid和动画。",
    "javascript": "JavaScript核心知识点：ES6+语法（解构/箭头函数/Promise/async-await）、DOM操作、事件机制、模块化。建议先打好基础再学框架。",
    "vue": "Vue3核心：组合式API（setup/ref/reactive）、组件通信（props/emit/provide）、Pinia状态管理、Vue Router路由。Vue3相比Vue2更轻量灵活。",
    "react": "React核心：函数组件+Hooks（useState/useEffect/useContext）、JSX语法、状态管理（Redux/Zustand）、React Router。React生态最丰富，就业需求大。",
    "工程化": "前端工程化包括：构建工具（Webpack/Vite）、代码规范（ESLint/Prettier）、Git工作流、CI/CD部署、性能监控。Vite开发体验最佳。",
    "面试": "前端面试高频考点：手写代码（防抖/节流/深拷贝）、算法（排序/链表/树）、框架原理（虚拟DOM/响应式）、网络（HTTP/HTTPS/缓存）、项目经验深挖。",
    "路径": "前端学习推荐路径：HTML/CSS基础 → JavaScript核心 → 一个框架（Vue/React）→ 工程化工具 → 性能优化 → 项目实战。一般6-12个月可达到初级前端水平。",
    "薪资": "前端开发薪资参考：初级6-10K、中级10-18K、高级18-30K、架构师30K+。一线城市薪资比二三线高30-50%。掌握Vue/React+TypeScript+工程化是高薪关键。",
}


def _match_fallback(question: str) -> str:
    """从预置知识库中匹配回答"""
    q = question.lower()
    for keyword, answer in _FALLBACK_QA.items():
        if keyword in q:
            return answer
    return "我是职慧Agent，当前AI服务暂时不可用。您可以问我关于HTML/CSS/JavaScript/Vue/React/前端工程化/面试/学习路径/薪资等方面的问题，我会尽力回答。"


@router.post("/api/v1/chat")
async def chat(req: ChatRequest):
    """多轮对话（支持追问），AI失败时使用预置知识库"""
    system_prompt = """你是「职慧Agent」，一位专业的职业教育顾问。
你的职责是：
1. 帮助用户了解岗位能力要求
2. 解答关于前端开发、软件技术相关的问题
3. 提供职业规划建议
4. 解释岗位能力图谱中各技能的含义和学习方法

回答要求：
- 专业准确，引用行业标准
- 通俗易懂，适合职校学生理解
- 提供具体可操作的建议
- 如果用户追问，给出更深入的解答"""

    if req.context:
        system_prompt += f"\n\n当前上下文：用户正在查看「{req.context}」相关内容。"

    messages = [{"role": "system", "content": system_prompt}]
    for msg in req.messages:
        messages.append({"role": msg.role, "content": msg.content})

    try:
        from zhihui_core.utils.jwt_helper import generate_token
        token = generate_token(ZHIPUAI_API_KEY)
        resp = requests.post(
            "https://open.bigmodel.cn/api/paas/v4/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            json={
                "model": "glm-4-flash",
                "messages": messages,
                "temperature": 0.5,
                "max_tokens": 1000,
            },
            timeout=20,
        )
        resp.raise_for_status()
        reply = resp.json()["choices"][0]["message"]["content"]
        return {"reply": reply}
    except Exception as e:
        last_msg = req.messages[-1].content if req.messages else ""
        reply = _match_fallback(last_msg)
        return {"reply": reply, "fallback": True, "error": "AI服务暂不可用"}


# ============================================================
# 五、task_convert 子模块 (POST /task-convert, GET /preset-tasks)
# ============================================================

class TaskConvertRequest(BaseModel):
    job_name: str = "前端开发工程师"
    task_name: str
    task_description: Optional[str] = ""


class PresetTasksRequest(BaseModel):
    job_name: str = "前端开发工程师"


@router.post("/api/v1/task-convert")
async def task_convert(req: TaskConvertRequest):
    """将岗位典型工作任务转化为学习型任务"""
    from zhihui_core.agents.task_convert_agent import convert_task_to_learning, get_fallback_tasks

    try:
        result = convert_task_to_learning(
            job_name=req.job_name,
            task_name=req.task_name,
            task_description=req.task_description or "",
        )
        return {"success": True, "data": result, "source": "ai"}
    except Exception as e:
        try:
            fallback = get_fallback_tasks(req.job_name)
            return {
                "success": True,
                "data": fallback,
                "source": "fallback",
                "warning": "AI服务暂不可用，已使用预置数据",
            }
        except Exception as fe:
            raise HTTPException(status_code=500, detail="服务暂时不可用，请稍后重试")


@router.get("/api/v1/preset-tasks")
async def preset_tasks(job_name: str = "前端开发工程师"):
    """获取预置的典型工作任务列表"""
    from zhihui_core.agents.task_convert_agent import get_fallback_tasks

    try:
        data = get_fallback_tasks(job_name)
        tasks = data.get("typical_tasks", [])
        summary = []
        for t in tasks:
            summary.append({
                "task_id": t.get("task_id"),
                "task_name": t.get("task_name"),
                "description": t.get("description", "")[:80],
                "total_hours": t.get("total_hours"),
                "learning_task_count": len(t.get("learning_tasks", [])),
                "mapped_courses": t.get("mapped_courses", []),
            })
        return {"success": True, "data": summary, "job_name": job_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务暂时不可用，请稍后重试")


@router.get("/api/v1/preset-tasks/{task_id}")
async def preset_task_detail(task_id: str, job_name: str = "前端开发工程师"):
    """获取某个预置典型工作任务的完整学习型任务详情"""
    from zhihui_core.agents.task_convert_agent import get_fallback_tasks

    try:
        data = get_fallback_tasks(job_name)
        tasks = data.get("typical_tasks", [])
        for t in tasks:
            if t.get("task_id") == task_id:
                return {"success": True, "data": t}
        raise HTTPException(status_code=404, detail=f"未找到任务: {task_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误")


# ============================================================
# 六、analytics 子路由 (POST /track, GET /dashboard, GET /realtime)
# ============================================================

_analytics_cache_lock = threading.Lock()
_analytics_cache = None
_analytics_cache_ts = 0

ANALYTICS_FILE = DATA_DIR / "analytics.json"


def _analytics_empty():
    return {"daily": {}, "pages": {}, "devices": {}, "browsers": {}, "referrers": {}, "recent": []}


def _analytics_today_str():
    return datetime.now().strftime("%Y-%m-%d")


def _analytics_load():
    global _analytics_cache, _analytics_cache_ts
    if _analytics_cache and time.time() - _analytics_cache_ts < 5:
        return _analytics_cache
    if ANALYTICS_FILE.exists():
        try:
            with open(ANALYTICS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = _analytics_empty()
    else:
        data = _analytics_empty()
    _analytics_cache, _analytics_cache_ts = data, time.time()
    return data


def _analytics_save(data):
    global _analytics_cache, _analytics_cache_ts
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(ANALYTICS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    _analytics_cache, _analytics_cache_ts = data, time.time()


class PageView(BaseModel):
    path: str = ""
    title: str = ""
    referrer: str = ""
    duration: int = 0


class TrackReq(BaseModel):
    page: PageView = PageView()
    device: dict = {}
    event: str = "pageview"


analytics_router = APIRouter(prefix="/analytics", tags=["访问统计"])


@analytics_router.post("/track")
async def track(request: Request, body: TrackReq):
    ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    ua = request.headers.get("user-agent", "")
    device = body.device.get("type") or (
        "mobile" if any(x in ua.lower() for x in ["mobile", "android", "iphone"]) else "desktop"
    )
    browser = (
        "Chrome" if "chrome" in ua.lower()
        else ("Edge" if "edg" in ua.lower()
              else ("Firefox" if "firefox" in ua.lower()
                    else ("Safari" if "safari" in ua.lower() else "Other")))
    )
    ref = body.page.referrer or ""
    if ref:
        try:
            from urllib.parse import urlparse
            ref = urlparse(ref).netloc or ref[:50]
        except Exception:
            ref = ref[:50]
    today = _analytics_today_str()
    with _analytics_cache_lock:
        data = _analytics_load()
        d = data["daily"].setdefault(today, {"pv": 0, "uv_ips": [], "sessions": 0, "pages": {}})
        d["pv"] += 1
        if ip not in d.get("uv_ips", []):
            d.setdefault("uv_ips", []).append(ip)
        path = body.page.path or "/"
        if body.event == "pageview":
            d["sessions"] = d.get("sessions", 0) + 1
            d["pages"][path] = d["pages"].get(path, 0) + 1
            p = data["pages"].setdefault(path, {"pv": 0, "title": body.page.title or path, "last_visit": ""})
            p["pv"] += 1
            p["title"] = body.page.title or p.get("title", path)
            p["last_visit"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        data["devices"][device] = data["devices"].get(device, 0) + 1
        data["browsers"][browser] = data["browsers"].get(browser, 0) + 1
        if ref:
            data["referrers"][ref] = data["referrers"].get(ref, 0) + 1
        data["recent"].append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "path": path,
            "title": body.page.title or path,
            "device": device,
            "browser": browser,
            "referrer": ref,
            "ip": ip[-8:].rjust(8, "*"),
            "event": body.event,
        })
        if len(data["recent"]) > 100:
            data["recent"] = data["recent"][-100:]
        cutoff = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        for k in [k for k in data["daily"] if k < cutoff]:
            del data["daily"][k]
        _analytics_save(data)
    return {"ok": True}


@analytics_router.get("/dashboard")
async def analytics_dashboard(days: int = Query(7, ge=1, le=90)):
    data = _analytics_load()
    today = _analytics_today_str()
    total_pv = total_uv = total_sessions = 0
    daily_trend = []
    for i in range(days - 1, -1, -1):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        dd = data.get("daily", {}).get(d, {})
        pv = dd.get("pv", 0)
        uv = len(dd.get("uv_ips", []))
        ss = dd.get("sessions", 0)
        total_pv += pv
        total_uv += uv
        total_sessions += ss
        daily_trend.append({"date": d, "pv": pv, "uv": uv, "sessions": ss})
    td = data.get("daily", {}).get(today, {})
    pages_sorted = sorted(data.get("pages", {}).items(), key=lambda x: x[1].get("pv", 0), reverse=True)[:10]
    return {
        "today": {"pv": td.get("pv", 0), "uv": len(td.get("uv_ips", [])), "sessions": td.get("sessions", 0)},
        "total_pv": total_pv,
        "total_uv": total_uv,
        "total_sessions": total_sessions,
        "daily_trend": daily_trend,
        "top_pages": [{"path": p, "pv": v.get("pv", 0), "title": v.get("title", p)} for p, v in pages_sorted],
        "devices": data.get("devices", {}),
        "browsers": data.get("browsers", {}),
        "referrers": data.get("referrers", {}),
        "recent": data.get("recent", [])[-20:],
    }


@analytics_router.get("/realtime")
async def realtime():
    data = _analytics_load()
    now = datetime.now()
    cutoff = (now - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M")
    active = [r for r in data.get("recent", []) if r.get("time", "") >= cutoff]
    return {
        "online_users": len(set(r.get("ip", "") for r in active)),
        "recent_actions": len(active),
        "last_5min": active[-10:],
    }


router.include_router(analytics_router)


# ============================================================
# 七、admin 子路由 (POST /login, POST /logout, GET /stats, ...)
# ============================================================

TOKENS_FILE = DATA_DIR / "admin_tokens.json"
SESSION_MAX_AGE = 3600 * 8


def _admin_load_tokens():
    if TOKENS_FILE.exists():
        try:
            with open(TOKENS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _admin_save_tokens(tokens):
    with open(TOKENS_FILE, "w", encoding="utf-8") as f:
        json.dump(tokens, f, ensure_ascii=False)


def _admin_verify_token(token: str) -> bool:
    tokens = _admin_load_tokens()
    if token not in tokens:
        return False
    info = tokens[token]
    if time.time() - info.get("created", 0) > SESSION_MAX_AGE:
        tokens.pop(token, None)
        _admin_save_tokens(tokens)
        return False
    return True


def _admin_cleanup_tokens():
    tokens = _admin_load_tokens()
    now = time.time()
    changed = False
    for t in list(tokens):
        if now - tokens[t].get("created", 0) > SESSION_MAX_AGE:
            del tokens[t]
            changed = True
    if changed:
        _admin_save_tokens(tokens)


def _admin_check_auth(request: Request):
    token = request.cookies.get("admin_token", "")
    if not _admin_verify_token(token):
        raise HTTPException(status_code=401, detail="未登录或会话过期")


class LoginReq(BaseModel):
    password: str


admin_router = APIRouter(prefix="/admin", tags=["管理后台"])


@admin_router.post("/login")
async def admin_login(body: LoginReq, response: Response):
    _admin_cleanup_tokens()
    if body.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="密码错误")
    token = secrets.token_hex(32)
    tokens = _admin_load_tokens()
    tokens[token] = {"created": time.time(), "ip": "admin"}
    _admin_save_tokens(tokens)
    response.set_cookie(
        key="admin_token", value=token, httponly=True,
        max_age=SESSION_MAX_AGE, samesite="lax",
    )
    return {"ok": True, "token": token}


@admin_router.post("/logout")
async def admin_logout(request: Request, response: Response):
    token = request.cookies.get("admin_token", "")
    tokens = _admin_load_tokens()
    tokens.pop(token, None)
    _admin_save_tokens(tokens)
    response.delete_cookie("admin_token")
    return {"ok": True}


@admin_router.get("/stats")
async def admin_stats(request: Request):
    _admin_check_auth(request)
    kb_path = DATA_DIR / "knowledge_base.json"
    kb_count = 0
    if kb_path.exists():
        try:
            with open(kb_path, "r", encoding="utf-8") as f:
                kb_count = len(json.load(f))
        except Exception:
            pass

    analytics_file = DATA_DIR / "analytics.json"
    today_pv = today_uv = total_pv = total_sessions = 0
    online_users = 0
    if analytics_file.exists():
        try:
            with open(analytics_file, "r", encoding="utf-8") as f:
                adata = json.load(f)
            today = datetime.now().strftime("%Y-%m-%d")
            td = adata.get("daily", {}).get(today, {})
            today_pv = td.get("pv", 0)
            today_uv = len(td.get("uv_ips", []))
            total_pv = sum(d.get("pv", 0) for d in adata.get("daily", {}).values())
            total_sessions = sum(d.get("sessions", 0) for d in adata.get("daily", {}).values())
            cutoff = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M")
            online_users = len(set(r.get("ip", "") for r in adata.get("recent", []) if r.get("time", "") >= cutoff))
        except Exception:
            pass

    history_path = DATA_DIR / "skill_map_history.json"
    history_count = 0
    if history_path.exists():
        try:
            with open(history_path, "r", encoding="utf-8") as f:
                history_count = len(json.load(f))
        except Exception:
            pass

    return {
        "version": "1.3.1",
        "knowledge_base_count": kb_count,
        "today_pv": today_pv,
        "today_uv": today_uv,
        "total_pv": total_pv,
        "total_sessions": total_sessions,
        "online_users": online_users,
        "history_count": history_count,
        "uptime": "running",
    }


@admin_router.get("/visitors")
async def admin_visitors(request: Request, days: int = 7):
    _admin_check_auth(request)
    analytics_file = DATA_DIR / "analytics.json"
    if not analytics_file.exists():
        return {"daily_trend": [], "top_pages": [], "devices": {}, "browsers": {}, "recent": []}
    try:
        with open(analytics_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {"daily_trend": [], "top_pages": [], "devices": {}, "browsers": {}, "recent": []}

    daily_trend = []
    for i in range(days - 1, -1, -1):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        dd = data.get("daily", {}).get(d, {})
        daily_trend.append({
            "date": d, "pv": dd.get("pv", 0),
            "uv": len(dd.get("uv_ips", [])), "sessions": dd.get("sessions", 0),
        })
    pages_sorted = sorted(data.get("pages", {}).items(), key=lambda x: x[1].get("pv", 0), reverse=True)[:10]
    return {
        "daily_trend": daily_trend,
        "top_pages": [{"path": p, "pv": v.get("pv", 0), "title": v.get("title", p)} for p, v in pages_sorted],
        "devices": data.get("devices", {}),
        "browsers": data.get("browsers", {}),
        "referrers": data.get("referrers", {}),
        "recent": data.get("recent", [])[-30:],
    }


@admin_router.get("/knowledge")
async def admin_knowledge(request: Request):
    _admin_check_auth(request)
    kb_path = DATA_DIR / "knowledge_base.json"
    if not kb_path.exists():
        return {"items": [], "total": 0}
    try:
        with open(kb_path, "r", encoding="utf-8") as f:
            items = json.load(f)
        return {"items": items[:20], "total": len(items)}
    except Exception:
        return {"items": [], "total": 0}


@admin_router.get("/system")
async def admin_system_info(request: Request):
    _admin_check_auth(request)
    import platform
    return {
        "python_version": platform.python_version(),
        "platform": platform.system(),
        "env_vars": {
            "PORT": os.environ.get("PORT", "not set"),
            "ADMIN_PASSWORD": "***" if ADMIN_PASSWORD else "not set",
            "ZHIPUAI_API_KEY": "***" if os.environ.get("ZHIPUAI_API_KEY") else "not set",
        },
        "data_files": [f.name for f in DATA_DIR.iterdir()] if DATA_DIR.exists() else [],
        "routes": ["skill_map", "learn_path", "chat", "task_convert", "analytics", "admin"],
    }


router.include_router(admin_router)
