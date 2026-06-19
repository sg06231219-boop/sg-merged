#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多智能体协同学习平台路由模块
来源：multi-agent-edu/app.py (v6.2.0)
转换：app → APIRouter(prefix="/edu")
SG-MERGED: 所有文件路径已改为从 sg-merged 根目录出发的相对路径
7个Agent协同：诊断→生成→审核→实操→测试→迭代→导学
"""
import os
import json
import time
import asyncio
import hashlib
import uuid
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, HTTPException, Depends, Cookie, Response
from pydantic import BaseModel, Field
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse

# SG-MERGED: 确保 stdout 编码为 UTF-8（原在 lifespan 中设置）
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

router = APIRouter(prefix="/edu", tags=["多智能体教育"])

# ============================================================
# 配置
# ============================================================
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
ADMIN_COOKIE_NAME = "mae_admin_token"
CST = timezone(timedelta(hours=8))

# ============================================================
# 会话存储（内存，Render重启后清空）
# ============================================================
class SessionStore:
    def __init__(self, max_sessions=500):
        self.sessions = {}  # id -> session data
        self.max = max_sessions
    
    def create(self, profile: dict) -> str:
        sid = uuid.uuid4().hex[:12]
        self.sessions[sid] = {
            "id": sid,
            "profile": profile,
            "created_at": datetime.now(CST).isoformat(),
            "status": "pending",
            "results": {},
            "agent_count": 0,
            "total_seconds": 0,
            "error": None,
        }
        # 淘汰最旧的
        if len(self.sessions) > self.max:
            oldest = min(self.sessions, key=lambda k: self.sessions[k]["created_at"])
            del self.sessions[oldest]
        return sid
    
    def update(self, sid: str, **kwargs):
        if sid in self.sessions:
            self.sessions[sid].update(kwargs)
    
    def get(self, sid: str) -> Optional[dict]:
        return self.sessions.get(sid)
    
    def list_recent(self, limit=50) -> list:
        items = sorted(self.sessions.values(), key=lambda x: x.get("created_at", ""), reverse=True)
        return items[:limit]
    
    def stats(self) -> dict:
        total = len(self.sessions)
        completed = sum(1 for s in self.sessions.values() if s.get("status") == "completed")
        failed = sum(1 for s in self.sessions.values() if s.get("status") == "error")
        running = sum(1 for s in self.sessions.values() if s.get("status") == "running")
        return {"total": total, "completed": completed, "failed": failed, "running": running}

store = SessionStore()

# ============================================================
# Rate Limiter（滑动窗口，每IP每分钟10次）
# ============================================================
class RateLimiter:
    def __init__(self, max_requests=10, window_seconds=60):
        self.max = max_requests
        self.window = window_seconds
        self.requests = defaultdict(list)
    
    def check(self, key: str) -> bool:
        now = time.time()
        cutoff = now - self.window
        self.requests[key] = [t for t in self.requests[key] if t > cutoff]
        if len(self.requests[key]) >= self.max:
            return False
        self.requests[key].append(now)
        return True

rate_limiter = RateLimiter(max_requests=10, window_seconds=60)

# ============================================================
# 全局调度器（模块级别初始化，原在 lifespan 中初始化）
# ============================================================

# SG-MERGED: Agent imports — 确保 multi-agent-edu 的 agents 包可被 Python 找到
from agents.orchestrator import Orchestrator
from agents.diagnosis import DiagnosisAgent
from agents.knowledge_gen import KnowledgeGenAgent
from agents.practice_guide import PracticeGuideAgent
from agents.reviewer import ReviewerAgent
from agents.quiz import QuizAgent
from agents.iteration import IterationAgent
from agents.socratic import SocraticAgent

orchestrator = Orchestrator()
orchestrator.register("diagnosis", DiagnosisAgent())
orchestrator.register("knowledge_gen", KnowledgeGenAgent())
orchestrator.register("practice_guide", PracticeGuideAgent())
orchestrator.register("reviewer", ReviewerAgent())
orchestrator.register("quiz", QuizAgent())
orchestrator.register("iteration", IterationAgent())
orchestrator.register("socratic", SocraticAgent())

# ============================================================
# SSE超时配置（Render 30秒硬限制，留5秒余量）
# ============================================================
SSE_TIMEOUT_SECONDS = 25
# SG-MERGED: 原 @app.middleware("http") sse_timeout_middleware 已移除
# SSE 超时检测已内联到 stream_pipeline 的 event_generator 中


# ============================================================
# 请求模型
# ============================================================
class LearnerProfile(BaseModel):
    background: str = Field(default="", max_length=500)
    experience: str = Field(default="无")
    goal: str = Field(default="", max_length=200)
    level: str = Field(default="beginner", pattern="^(beginner|intermediate|advanced)$")

class StartRequest(BaseModel):
    profile: LearnerProfile = Field(default_factory=LearnerProfile)

class StreamRequest(BaseModel):
    profile: LearnerProfile = Field(default_factory=LearnerProfile)

class FeedbackRequest(BaseModel):
    quiz_result: dict = Field(default_factory=dict)
    diagnosis: dict = Field(default_factory=dict)
    knowledge: dict = Field(default_factory=dict)

class SocraticChatRequest(BaseModel):
    knowledge: dict = Field(default_factory=dict)
    conversation_history: list = Field(default_factory=list, max_length=50)

class ReviewRequest(BaseModel):
    content: str = Field(default="", max_length=10000)
    source_refs: list = Field(default_factory=list)

class GenerateRequest(BaseModel):
    diagnosis: dict = Field(default_factory=dict)

class QuizRequest(BaseModel):
    knowledge: dict = Field(default_factory=dict)
    difficulty: str = Field(default="medium", pattern="^(easy|medium|hard|beginner|intermediate|advanced)$")

class PracticeRequest(BaseModel):
    topic: str = Field(default="", max_length=200)
    level: str = Field(default="beginner", pattern="^(beginner|intermediate|advanced)$")

class SocraticEmbedRequest(BaseModel):
    knowledge: dict = Field(default_factory=dict)

class AdminLoginRequest(BaseModel):
    password: str = Field(default="", max_length=100)

# ============================================================
# 工具函数
# ============================================================
def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "0.0.0.0"

def _check_rate(request: Request):
    ip = _get_client_ip(request)
    if not rate_limiter.check(ip):
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")

def _check_admin(request: Request) -> bool:
    token = request.cookies.get(ADMIN_COOKIE_NAME, "")
    expected = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()[:32]
    return token == expected

# ============================================================
# 页面路由
# ============================================================
@router.get("/", response_class=HTMLResponse)
async def index():
    # SG-MERGED: 静态文件路径改为 static/edu/
    with open("static/edu/index.html", "r", encoding="utf-8") as f:
        return f.read()

@router.get("/admin", response_class=HTMLResponse)
async def admin_page():
    # SG-MERGED: 静态文件路径改为 static/edu/
    with open("static/edu/admin.html", "r", encoding="utf-8") as f:
        return f.read()

# ============================================================
# Health
# ============================================================
@router.get("/api/health")
async def health():
    agents_list = ["diagnosis", "knowledge_gen", "reviewer", "practice_guide", "quiz", "iteration", "socratic"]
    has_api_key = bool(os.environ.get("ZHIPUAI_API_KEY", ""))
    return {
        "status": "ok" if has_api_key else "degraded",
        "version": "6.2.0",
        "agents": agents_list,
        "ai_backend": "glm-4-flash",
        "api_key_configured": has_api_key,
    }

# ============================================================
# 全流程API
# ============================================================
# SSE流式端点（含超时优雅降级）
# ============================================================
@router.post("/api/stream")
async def stream_pipeline(body: StreamRequest, request: Request):
    _check_rate(request)
    profile = body.profile.model_dump()
    sid = store.create(profile)
    store.update(sid, status="running")
    start_time = time.time()
    # SG-MERGED: SSE超时检测在 generator 内部进行，不再依赖中间件注入
    sse_deadline = time.time() + SSE_TIMEOUT_SECONDS
    timed_out = False
    
    async def event_generator():
        nonlocal timed_out
        try:
            yield f"data: {json.dumps({'type': 'start', 'session_id': sid, 'profile': profile}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0)
            async for event in orchestrator.run_streaming(profile):
                # 检查SSE超时：如果即将达到Render 30s限制，优雅降级
                if time.time() > sse_deadline:
                    timed_out = True
                    completed = store.get(sid).get("results", {}) if store.get(sid) else {}
                    yield f"data: {json.dumps({'type': 'timeout', 'message': '响应时间较长，已返回部分结果，请使用前端直调模式完成剩余步骤', 'completed_agents': list(completed.keys())}, ensure_ascii=False)}\n\n"
                    store.update(sid, status="timeout", error="SSE超时，部分结果已返回")
                    break
                
                # 记录Agent完成事件
                if event.get("type") == "agent_done":
                    agent = event.get("agent", "")
                    results = store.get(sid).get("results", {}) if store.get(sid) else {}
                    results[agent] = event.get("result", {})
                    store.update(sid, results=results, agent_count=len(results))
                
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0)
            
            if not timed_out:
                elapsed = round(time.time() - start_time, 1)
                store.update(sid, status="completed", total_seconds=elapsed)
                yield f"data: {json.dumps({'type': 'complete', 'message': '全流程完成', 'session_id': sid}, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            store.update(sid, status="cancelled")
            yield f"data: {json.dumps({'type': 'cancelled', 'message': '用户取消'}, ensure_ascii=False)}\n\n"
        except Exception as e:
            store.update(sid, status="error", error="internal_error")
            yield f"data: {json.dumps({'type': 'error', 'message': '处理出错，请重试'}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-SSE-Timeout": str(SSE_TIMEOUT_SECONDS),
        }
    )

# 单步Agent API
# ============================================================
@router.post("/api/diagnosis")
async def run_diagnosis(body: StartRequest, request: Request):
    _check_rate(request)
    try:
        return await orchestrator.run_agent("diagnosis", profile=body.profile.model_dump())
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail="服务暂时不可用，请稍后重试")

@router.post("/api/generate")
async def run_generate(body: GenerateRequest, request: Request):
    _check_rate(request)
    try:
        return await orchestrator.run_agent("knowledge_gen", diagnosis=body.diagnosis)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail="服务暂时不可用，请稍后重试")

@router.post("/api/review")
async def run_review(body: ReviewRequest, request: Request):
    _check_rate(request)
    try:
        return await orchestrator.run_agent("reviewer", content=body.content, source_refs=body.source_refs)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail="服务暂时不可用，请稍后重试")

@router.post("/api/quiz")
async def run_quiz(body: QuizRequest, request: Request):
    _check_rate(request)
    try:
        return await orchestrator.run_agent("quiz", knowledge=body.knowledge, difficulty=body.difficulty)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail="服务暂时不可用，请稍后重试")

@router.post("/api/practice")
async def run_practice(body: PracticeRequest, request: Request):
    _check_rate(request)
    try:
        return await orchestrator.run_agent("practice_guide", topic=body.topic, level=body.level)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail="服务暂时不可用，请稍后重试")

@router.post("/api/feedback")
async def submit_feedback(body: FeedbackRequest, request: Request):
    _check_rate(request)
    try:
        iteration = await orchestrator.run_agent("iteration", quiz_result=body.quiz_result, diagnosis=body.diagnosis, knowledge=body.knowledge)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail="服务暂时不可用，请稍后重试")
    
    decision = iteration.get("decision", "consolidate")
    adjustments = iteration.get("adjustments", {})
    
    new_content = None
    try:
        if decision == "simplify":
            new_content = await orchestrator.run_agent("knowledge_gen", diagnosis={**body.diagnosis, "learner_level": "beginner"}, revision_hints=["请大幅简化内容，用最通俗的语言讲解"])
        elif decision == "advance":
            new_content = await orchestrator.run_agent("knowledge_gen", diagnosis={**body.diagnosis, "learner_level": "advanced"}, revision_hints=["请提供更高难度的进阶内容"])
        else:
            new_content = await orchestrator.run_agent("knowledge_gen", diagnosis=body.diagnosis, revision_hints=adjustments.get("focus_topics", []))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail="服务暂时不可用，请稍后重试")
    
    return {"iteration_decision": iteration, "new_content": new_content}

@router.post("/api/socratic/embed")
async def embed_socratic(body: SocraticEmbedRequest, request: Request):
    _check_rate(request)
    try:
        return await orchestrator.run_agent("socratic", knowledge=body.knowledge, mode="embed_questions")
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail="服务暂时不可用，请稍后重试")

@router.post("/api/socratic/chat")
async def socratic_chat(body: SocraticChatRequest, request: Request):
    _check_rate(request)
    try:
        return await orchestrator.run_agent("socratic", knowledge=body.knowledge, conversation_history=body.conversation_history, mode="respond")
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail="服务暂时不可用，请稍后重试")

# ============================================================
# 管理员 API
# ============================================================
@router.post("/api/admin/login")
async def admin_login(body: AdminLoginRequest, response: Response):
    if body.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="密码错误")
    token = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()[:32]
    response = JSONResponse({"ok": True})
    response.set_cookie(ADMIN_COOKIE_NAME, token, httponly=True, max_age=86400 * 7, samesite="lax")
    return response

@router.post("/api/admin/logout")
async def admin_logout():
    response = JSONResponse({"ok": True})
    response.delete_cookie(ADMIN_COOKIE_NAME)
    return response

@router.get("/api/admin/stats")
async def admin_stats(request: Request):
    if not _check_admin(request):
        raise HTTPException(status_code=401, detail="未登录")
    return {
        "version": "6.2.0",
        "sessions": store.stats(),
        "agents": orchestrator.list_agents() if orchestrator else [],
        "api_key_configured": bool(os.environ.get("ZHIPUAI_API_KEY", "")),
        "rate_limiter": {
            "tracked_ips": len(rate_limiter.requests),
            "max_per_minute": rate_limiter.max,
        },
        "uptime_note": "内存存储，Render重启后清空",
    }

@router.get("/api/admin/sessions")
async def admin_sessions(request: Request, limit: int = 50):
    if not _check_admin(request):
        raise HTTPException(status_code=401, detail="未登录")
    limit = min(limit, 200)
    sessions = store.list_recent(limit)
    # 脱敏：不返回完整results（可能很大）
    for s in sessions:
        s.pop("results", None)
    return {"sessions": sessions, "count": len(sessions)}

@router.get("/api/admin/sessions/{sid}")
async def admin_session_detail(sid: str, request: Request):
    if not _check_admin(request):
        raise HTTPException(status_code=401, detail="未登录")
    session = store.get(sid)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return session

@router.delete("/api/admin/sessions/{sid}")
async def admin_delete_session(sid: str, request: Request):
    if not _check_admin(request):
        raise HTTPException(status_code=401, detail="未登录")
    if sid in store.sessions:
        del store.sessions[sid]
        return {"ok": True}
    raise HTTPException(status_code=404, detail="会话不存在")

@router.get("/api/admin/agents")
async def admin_agents(request: Request):
    if not _check_admin(request):
        raise HTTPException(status_code=401, detail="未登录")
    agents_info = []
    if orchestrator:
        for name, agent in orchestrator.agents.items():
            agents_info.append({
                "name": agent.name,
                "role": agent.role,
                "description": agent.description,
                "has_result": bool(agent.last_result),
            })
    return {"agents": agents_info}

# ============================================================
# WebSocket（保留兼容）
# ============================================================
@router.websocket("/ws/pipeline")
async def ws_pipeline(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        profile = data.get("profile", {}) if isinstance(data, dict) else {}
        await websocket.send_json({"type": "start", "message": "开始多智能体协同调度", "profile": profile})
        async for event in orchestrator.run_streaming(profile):
            await websocket.send_json(event)
        await websocket.send_json({"type": "complete", "message": "全流程完成"})
    except WebSocketDisconnect:
        pass
    except RuntimeError as e:
        try:
            await websocket.send_json({"type": "error", "message": "连接异常，请刷新重试"})
        except:
            pass

# ============================================================
# 学情可视化报告 API（评分标准要求：知识盲区定位/资源难度匹配曲线/学习路径规划图）
# ============================================================
@router.post("/api/report")
async def generate_report(body: StartRequest, request: Request):
    """生成完整的学情可视化报告"""
    _check_rate(request)
    profile = body.profile.model_dump()
    
    try:
        # Step 1: 学情诊断
        diagnosis = await orchestrator.run_agent("diagnosis", profile=profile)
        
        # Step 2: 知识生成
        knowledge = await orchestrator.run_agent("knowledge_gen", diagnosis=diagnosis)
        
        # Step 3: 审核
        review = await orchestrator.run_agent("reviewer", 
            content=knowledge.get("content", ""), 
            source_refs=knowledge.get("source_refs", []),
            debate_round=1)
        
        # Step 4: 测验
        quiz = await orchestrator.run_agent("quiz", 
            knowledge=knowledge, 
            difficulty=profile.get("level", "medium"))
        
        # Step 5: 迭代决策
        iteration = await orchestrator.run_agent("iteration", 
            quiz_result=quiz, diagnosis=diagnosis, knowledge=knowledge)
        
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail="服务暂时不可用，请稍后重试")
    except Exception as e:
        raise HTTPException(status_code=500, detail="内部错误，请稍后重试")
    
    # 构建可视化报告数据
    report = _build_visual_report(profile, diagnosis, knowledge, review, quiz, iteration)
    return report


def _build_visual_report(profile: dict, diagnosis: dict, knowledge: dict, 
                          review: dict, quiz: dict, iteration: dict) -> dict:
    """构建学情可视化报告"""
    
    # 1. 知识盲区定位（雷达图数据）
    blind_spots = diagnosis.get("blind_spots", [])
    strengths = diagnosis.get("strengths", [])
    focus_topic = diagnosis.get("focus_topic", "Python编程基础")
    learner_level = diagnosis.get("learner_level", profile.get("level", "beginner"))
    
    # 从知识内容提取知识点维度
    knowledge_dimensions = [
        {"name": "基础概念", "score": _calc_dimension_score("基础", diagnosis, 0.7)},
        {"name": "核心原理", "score": _calc_dimension_score("原理", diagnosis, 0.5)},
        {"name": "实操技能", "score": _calc_dimension_score("实操|实践", diagnosis, 0.4)},
        {"name": "进阶应用", "score": _calc_dimension_score("进阶|高级", diagnosis, 0.3)},
        {"name": "综合理解", "score": _calc_dimension_score("综合|理解", diagnosis, 0.45)},
        {"name": "知识溯源", "score": _calc_dimension_score("溯源|来源", diagnosis, 0.6)},
    ]
    
    # 2. 资源难度匹配曲线
    level_map = {"beginner": 1, "intermediate": 2, "advanced": 3}
    learner_score = level_map.get(learner_level, 1)
    
    # 模拟不同知识点的难度梯度
    difficulty_curve = []
    topics = ["基础语法", "数据结构", "算法思维", "框架应用", "系统设计", "前沿技术"]
    for i, topic in enumerate(topics):
        topic_difficulty = 1 + i * 0.4  # 难度递增
        match_score = max(0, 1 - abs(learner_score - topic_difficulty) / 3) * 100
        difficulty_curve.append({
            "topic": topic,
            "difficulty": round(topic_difficulty, 1),
            "match_score": round(match_score, 1),
            "recommendation": "重点学习" if match_score > 70 else "适当了解" if match_score > 40 else "暂不需要"
        })
    
    # 3. 学习路径规划图
    path_stages = []
    decision = iteration.get("decision", "consolidate")
    
    if decision == "simplify":
        path_stages = [
            {"stage": 1, "title": "基础夯实", "status": "current", "desc": f"当前阶段：从{focus_topic}的基础概念开始"},
            {"stage": 2, "title": "核心掌握", "status": "next", "desc": "掌握核心原理和基本操作"},
            {"stage": 3, "title": "进阶提升", "status": "future", "desc": "学习进阶内容和实战项目"},
        ]
    elif decision == "advance":
        path_stages = [
            {"stage": 1, "title": "基础夯实", "status": "done", "desc": "已掌握基础知识"},
            {"stage": 2, "title": "核心掌握", "status": "done", "desc": "已掌握核心原理"},
            {"stage": 3, "title": "进阶提升", "status": "current", "desc": f"当前阶段：深入学习{focus_topic}的高级特性"},
            {"stage": 4, "title": "专家突破", "status": "next", "desc": "探索前沿技术和创新应用"},
        ]
    else:
        path_stages = [
            {"stage": 1, "title": "基础夯实", "status": "done", "desc": "已掌握基础知识"},
            {"stage": 2, "title": "核心掌握", "status": "current", "desc": f"当前阶段：巩固{focus_topic}的核心技能"},
            {"stage": 3, "title": "进阶提升", "status": "next", "desc": "学习进阶内容和实战项目"},
        ]
    
    # 4. 幻觉防控报告
    hallucination_score = review.get("hallucination_score", 50)
    
    return {
        "report_version": "1.0",
        "learner_profile": profile,
        "summary": {
            "learner_level": learner_level,
            "focus_topic": focus_topic,
            "blind_spots_count": len(blind_spots),
            "strengths_count": len(strengths),
            "hallucination_score": hallucination_score,
            "iteration_decision": decision,
            "quiz_questions_count": len(quiz.get("questions", [])),
        },
        "radar_chart": {
            "title": "知识能力雷达图",
            "dimensions": knowledge_dimensions,
            "blind_spots": blind_spots[:5],
            "strengths": strengths[:5],
        },
        "difficulty_curve": {
            "title": "资源难度匹配曲线",
            "learner_level_score": learner_score,
            "data_points": difficulty_curve,
            "overall_match": round(sum(d["match_score"] for d in difficulty_curve) / len(difficulty_curve), 1),
        },
        "learning_path": {
            "title": "学习路径规划图",
            "stages": path_stages,
            "current_stage": next((s for s in path_stages if s["status"] == "current"), path_stages[0]),
            "total_stages": len(path_stages),
        },
        "hallucination_report": {
            "score": hallucination_score,
            "level": "低风险" if hallucination_score < 20 else "中等" if hallucination_score < 50 else "高风险",
            "debate_rounds": review.get("debate_rounds", 1),
            "issues_count": len(review.get("issues", [])),
            "verdict": review.get("verdict", "unknown"),
        },
        "source_traceability": {
            "knowledge_sources": knowledge.get("source_refs", []),
            "review_notes": review.get("summary", ""),
        },
    }


def _calc_dimension_score(keyword: str, diagnosis: dict, default: float) -> float:
    """根据诊断结果计算某维度的得分(0-1)"""
    import re
    level = diagnosis.get("learner_level", "beginner")
    level_scores = {"beginner": 0.3, "intermediate": 0.6, "advanced": 0.85}
    base = level_scores.get(level, 0.3)
    
    # 检查该关键词是否在强项中
    strengths_text = " ".join(diagnosis.get("strengths", []))
    blind_text = " ".join(diagnosis.get("blind_spots", []))
    
    if re.search(keyword, strengths_text):
        base = min(1.0, base + 0.2)
    if re.search(keyword, blind_text):
        base = max(0.1, base - 0.2)
    
    return round(base, 2)


# ============================================================
# 测试数据下载 API（提交要求：完整的输入输出示例）
# ============================================================
@router.get("/api/test-data")
async def get_test_data():
    """返回3组差异化学习者的完整输入输出示例"""
    # SG-MERGED: 数据路径相对于 sg-merged 根目录
    # 原使用的 os.path.dirname(os.path.abspath(__file__)) 已替换
    test_data_path = os.path.join("data", "edu", "test_profiles.json")
    profiles = []
    if os.path.exists(test_data_path):
        try:
            with open(test_data_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, list):
                profiles = raw
            elif isinstance(raw, dict):
                # 兼容 {"test_profiles": [...]} 结构
                profiles = raw.get("test_profiles", raw.get("profiles", []))
        except Exception:
            pass
    
    # 加载测试结果（兼容dict和list格式）
    test_result_path = os.path.join("data", "edu", "test_result.json")
    results = []
    if os.path.exists(test_result_path):
        try:
            with open(test_result_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, list):
                results = raw
            elif isinstance(raw, dict):
                results = [raw]  # 单个结果包装成列表
        except Exception:
            pass
    
    # 加载知识库文件列表
    kb_dir = os.path.join("knowledge_base")
    kb_files = []
    if os.path.isdir(kb_dir):
        kb_files = [{"name": f, "path": f"knowledge_base/{f}"}
                     for f in os.listdir(kb_dir) if f.endswith(".md")]
    
    return {
        "description": "XH-202630赛题测试数据：3组差异化学习者输入输出示例",
        "profiles": profiles[:3],
        "sample_results": results[:3],
        "knowledge_base_files": kb_files,
        "evaluation_report": None  # 可扩展
    }


# ============================================================
# 知识库搜索 API（TF-IDF语义检索）
# ============================================================
# SG-MERGED: 确保 knowledge_base 包可被 Python 找到
@router.post("/api/knowledge/search")
async def search_knowledge_api(request: Request):
    """TF-IDF语义检索知识库"""
    _check_rate(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="无效请求体")
    query = body.get("query", "").strip()
    top_k = min(body.get("top_k", 5), 20)
    source_filter = body.get("source_filter", None)
    if not query:
        raise HTTPException(status_code=400, detail="查询内容不能为空")
    try:
        from knowledge_base.search import search_knowledge
        results = search_knowledge(query, top_k=top_k, source_filter=source_filter)
        return {"query": query, "results": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail="搜索失败，请重试")

@router.get("/api/knowledge/stats")
async def knowledge_stats():
    """知识库索引统计"""
    try:
        from knowledge_base.search import get_search_engine
        engine = get_search_engine()
        return engine.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail="获取统计失败，请重试")

# ============================================================
# Agent结果解析 API（前端直调LLM后，后端解析结构化数据）
# ============================================================
@router.post("/api/agent/process")
async def process_agent_output(request: Request):
    """接收前端直调智谱API后的LLM原始输出，后端解析为结构化数据"""
    _check_rate(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="无效请求体")
    agent_name = body.get("agent_name", "").strip()
    llm_output = body.get("llm_output", "").strip()
    context = body.get("context", {})
    if not agent_name or not llm_output:
        raise HTTPException(status_code=400, detail="agent_name和llm_output不能为空")
    if not orchestrator or agent_name not in orchestrator.agents:
        raise HTTPException(status_code=400, detail=f"未知Agent: {agent_name}")
    agent = orchestrator.agents[agent_name]
    try:
        parsed = agent._parse_llm_output(llm_output)
        # Agent结果schema
        schemas = {
            "diagnosis": {"learner_level": {"type": str, "required": True, "default": "beginner"}, "level_score": {"type": (int, float), "required": False, "default": 50}, "strengths": {"type": list, "required": False, "default": []}, "blind_spots": {"type": list, "required": False, "default": []}, "focus_topic": {"type": str, "required": False, "default": ""}, "learning_path": {"type": list, "required": False, "default": []}},
            "knowledge_gen": {"title": {"type": str, "required": False, "default": "个性化学习内容"}, "content": {"type": str, "required": False, "default": llm_output[:500]}, "concepts": {"type": list, "required": False, "default": []}, "source_refs": {"type": list, "required": False, "default": []}},
            "reviewer": {"verdict": {"type": str, "required": False, "default": "pass"}, "hallucination_score": {"type": (int, float), "required": False, "default": 0}, "accuracy_score": {"type": (int, float), "required": False, "default": 80}, "issues": {"type": list, "required": False, "default": []}, "debate_rounds": {"type": int, "required": False, "default": 1}},
            "practice_guide": {"steps": {"type": list, "required": False, "default": []}, "difficulty": {"type": str, "required": False, "default": "medium"}, "estimated_time": {"type": str, "required": False, "default": "2-4小时"}},
            "quiz": {"questions": {"type": list, "required": False, "default": []}, "total_score": {"type": (int, float), "required": False, "default": 100}, "passing_score": {"type": (int, float), "required": False, "default": 60}},
            "iteration": {"decision": {"type": str, "required": False, "default": "consolidate"}, "adjustments": {"type": dict, "required": False, "default": {}}, "suggestion": {"type": str, "required": False, "default": ""}},
            "socratic": {"response": {"type": str, "required": False, "default": ""}, "questions": {"type": list, "required": False, "default": []}},
        }
        schema = schemas.get(agent_name, {})
        is_valid, errors = agent._validate_result(parsed, schema)
        parsed["_meta"] = {"agent": agent_name, "parsed": True, "valid": is_valid, "errors": errors, "source": "client_llm"}
        return {"ok": True, "result": parsed, "valid": is_valid, "errors": errors}
    except ValueError as e:
        return {"ok": False, "error": "处理失败"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="处理失败，请重试")

# SG-MERGED: 原 app.mount("/static", StaticFiles(directory="static"), name="static") 已移除
# 静态文件挂载需在主 app 中配置：
#   app.mount("/edu/static", StaticFiles(directory="static/edu"), name="edu_static")
#
# SG-MERGED: 原 analytics 子路由已移除（app.include_router(analytics_router)）
# 如需访客统计功能，请在主 app 中单独挂载：
#   if _HAS_ANALYTICS:
#       app.include_router(analytics_router, prefix="/api/v1/edu", tags=["访问统计"])

@router.get("/robots.txt")
async def robots():
    from fastapi.responses import FileResponse
    # SG-MERGED: 静态文件路径改为 static/edu/
    return FileResponse("static/edu/robots.txt", media_type="text/plain")

# SG-MERGED: 原 if __name__ == "__main__" 和 uvicorn.run 已移除
