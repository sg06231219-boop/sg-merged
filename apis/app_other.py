"""
其他工具合并版 — 职慧/小说/教育/IP/Tutorials/WorldCup
精简入口，不依赖建站工具企业级模块
"""
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware

ROOT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT_DIR / "static"

# ── 应用初始化 ─────────────────────────────────────────
app = FastAPI(
    title="SG工具集",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
)

# ── CORS ──────────────────────────────────────────────
_CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "https://lz-sg-sg.hf.space,http://localhost:8000,http://localhost:3000,http://127.0.0.1:8000,http://127.0.0.1:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Session（小说翻改等需要） ──────────────────────────
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", "sg-merged-tools-secret"),
    session_cookie="sg_session",
    max_age=86400,
)

# ── 安全头 ────────────────────────────────────────────
@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# ── 合并项目路由 ──────────────────────────────────────
# 职慧Agent
try:
    from apis.routes.zhihui import router as zhihui_router
    app.include_router(zhihui_router)
    _ZHIHUI = True
except ImportError:
    _ZHIHUI = False

# 小说翻改
try:
    from apis.routes.novel import router as novel_router
    app.include_router(novel_router)
    _NOVEL = True
except ImportError:
    _NOVEL = False

# Multi-Agent教育
try:
    from apis.routes.edu import router as edu_router
    app.include_router(edu_router)
    _EDU = True
except ImportError:
    _EDU = False

# IP探测器
try:
    from apis.routes.ip_detector import router as ip_router
    app.include_router(ip_router)
    _IP = True
except ImportError:
    _IP = False

# 嵌入式教程
try:
    from apis.routes.tutorials import router as tutorials_router
    app.include_router(tutorials_router)
    _TUTORIALS = True
except ImportError:
    _TUTORIALS = False

# ── 静态文件 ──────────────────────────────────────────
for _sub in ["zhihui", "novel", "edu", "ip", "tutorials", "worldcup"]:
    _dir = STATIC_DIR / _sub
    if _dir.exists():
        app.mount(f"/{_sub}/static", StaticFiles(directory=str(_dir)), name=f"static-{_sub}")

# ── 首页 ──────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index():
    tools = [
        {"name": "🧠 职慧Agent", "path": "/zhihui", "desc": "职业教育岗位技能智能体 · 挑战杯XA-202603", "color": "#6366f1"},
        {"name": "📚 小说翻改工具", "path": "/novel", "desc": "AI小说句式改写 · 多模型支持 · 流式翻改", "color": "#8b5cf6"},
        {"name": "🎓 Multi-Agent教育", "path": "/edu", "desc": "7 Agent协同教育平台 · 挑战杯XH-202630", "color": "#06b6d4"},
        {"name": "🌍 IP探测器", "path": "/ip", "desc": "IP地理位置检测 · 多源数据聚合", "color": "#10b981"},
        {"name": "📖 嵌入式教程", "path": "/tutorials", "desc": "嵌入式开发学习平台 · 分步教程", "color": "#f59e0b"},
        {"name": "⚽ World Cup 2026", "path": "/worldcup", "desc": "2026世界杯赛事信息 · 实时比分", "color": "#ef4444"},
    ]
    cards = "\n".join(
        f'''<a href="{t["path"]}" style="display:block;padding:20px 24px;border-radius:12px;background:linear-gradient(135deg,{t["color"]}22,{t["color"]}08);border:1px solid {t["color"]}33;text-decoration:none;color:inherit;transition:all .2s">
            <div style="font-size:20px;font-weight:700;margin-bottom:4px">{t["name"]}</div>
            <div style="font-size:13px;color:#94a3b8">{t["desc"]}</div>
        </a>''' for t in tools
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>SG 工具集</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}}
.container{{max-width:500px;width:100%}}
h1{{text-align:center;font-size:28px;font-weight:800;margin-bottom:8px;background:linear-gradient(135deg,#6366f1,#06b6d4,#10b981);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.subtitle{{text-align:center;font-size:13px;color:#64748b;margin-bottom:28px}}
.grid{{display:flex;flex-direction:column;gap:10px}}
a:hover{{transform:translateY(-2px);box-shadow:0 8px 25px rgba(0,0,0,.3)}}
</style>
</head>
<body>
<div class="container">
<h1>🚀 SG 工具集</h1>
<div class="subtitle">六大工具 · 一站直达</div>
<div class="grid">{cards}</div>
</div>
</body>
</html>"""

# ── Favicon ──────────────────────────────────────────
@app.get("/favicon.ico")
async def favicon():
    fp = STATIC_DIR / "favicon.ico"
    if fp.exists():
        return FileResponse(str(fp), media_type="image/x-icon")
    from fastapi import HTTPException
    raise HTTPException(404)

# ── 健康检查 ──────────────────────────────────────────
@app.get("/api/v1/health")
async def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "services": {
            "zhihui": "ok" if _ZHIHUI else "missing",
            "novel": "ok" if _NOVEL else "missing",
            "edu": "ok" if _EDU else "missing",
            "ip": "ok" if _IP else "missing",
            "tutorials": "ok" if _TUTORIALS else "missing",
        }
    }
