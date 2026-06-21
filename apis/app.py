"""
apis.app — FastAPI 应用入口（企业级 v9.0）

安全措施：
1. 基于 IP 的请求限流（生成接口每分钟 10 次，支持Redis分布式）
2. 安全响应头（CSP, X-Frame-Options, HSTS 等）
3. CORS 白名单
4. 全局异常处理（不泄漏内部错误）
5. 请求体大小限制

企业级特性：
- 结构化日志（JSON格式，日志轮转）
- Prometheus 监控指标
- 请求追踪ID（X-Request-ID）
- Redis 缓存+限流（内存降级）
- 增强健康检查（存活/就绪/详情探针）
- 类型安全配置管理（Pydantic Settings）
"""

import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

# 加载 .env（本地开发用，Render通过环境变量注入）
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

# ── 企业级配置管理（降级安全：模块不存在时用默认值）──────
try:
    from core.config import get_config
    config = get_config()
    _HAS_ENTERPRISE = True
except ImportError:
    _HAS_ENTERPRISE = False
    # 降级：简易配置对象
    import logging as _logging_mod
    class _FallbackConfig:
        version = os.environ.get("APP_VERSION", "9.0.0")
        site_domain = os.environ.get("SITE_DOMAIN", "lz-sg-sg-site-builder.hf.space")
        is_production = os.environ.get("APP_ENVIRONMENT", "development") == "production"
        is_development = not is_production
        cors_origin_list = os.environ.get("SECURITY_CORS_ORIGINS", "http://localhost:8000,http://localhost:3000,http://127.0.0.1:8000,http://127.0.0.1:3000,https://lz-sg-sg-site-builder.hf.space").split(",")
        class environment:
            value = os.environ.get("APP_ENVIRONMENT", "development")
        class observability:
            log_level = os.environ.get("OBS_LOG_LEVEL", "INFO")
            log_format = os.environ.get("OBS_LOG_FORMAT", "text")
            log_file = os.environ.get("OBS_LOG_FILE", "")
            log_max_bytes = 10 * 1024 * 1024
            log_backup_count = 5
            metrics_enabled = os.environ.get("OBS_METRICS_ENABLED", "true").lower() == "true"
            metrics_path = os.environ.get("OBS_METRICS_PATH", "/metrics")
            request_id_header = "X-Request-ID"
        class cache:
            enabled = os.environ.get("CACHE_ENABLED", "true").lower() == "true"
            backend = os.environ.get("CACHE_BACKEND", "memory")
            max_entries = 200
            ttl_seconds = 3600
            redis_ttl_seconds = 3600
        class security:
            jwt_secret = os.environ.get("JWT_SECRET", "sg-site-builder-secret-change-me")
        class rate_limit:
            enabled = os.environ.get("RATELIMIT_ENABLED", "true").lower() == "true"
            backend = os.environ.get("RATELIMIT_BACKEND", "memory")
            generate_per_minute = int(os.environ.get("RATELIMIT_GENERATE_PER_MINUTE", "10"))
            preview_per_minute = 60
            download_per_minute = 60
            default_per_minute = 100
            auth_per_minute = 10
        class redis:
            enabled = os.environ.get("REDIS_ENABLED", "false").lower() == "true"
            url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
            password = os.environ.get("REDIS_PASSWORD", "")
            max_connections = 20
            socket_timeout = 5.0
    config = _FallbackConfig()

# ── 企业级日志（降级安全）────────────────────
try:
    from core.observability import setup_logging, RequestTracingMiddleware, metrics_endpoint
    logger = setup_logging(config)
except ImportError:
    RequestTracingMiddleware = None
    metrics_endpoint = None
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S")
    logger = logging.getLogger("site-builder.api")

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, PlainTextResponse

from core.engine import get_engine

# ── 日志已由 core.observability 统一配置 ────────

STATIC_DIR = Path(__file__).parent.parent / "static"

# ── 企业级限流（降级安全：模块不存在时用内存限流）──────
try:
    from core.ratelimit import get_ratelimit_manager
    _ratelimit = get_ratelimit_manager(config)
    _HAS_RATELIMIT_MODULE = True
except ImportError:
    _HAS_RATELIMIT_MODULE = False
    # 降级：简易内存限流
    import time as _time
    from collections import defaultdict as _defaultdict
    _rate_store: _defaultdict = _defaultdict(list)
    RATE_LIMITS = {
        "/api/v1/generate": (10, 60),
        "/api/v1/generate-from-text": (10, 60),
        "/api/v1/preview": (60, 60),
        "/api/v1/download": (60, 60),
        "/api/v1/download-zip": (30, 60),
    }
    RATE_FALLBACK = (100, 60)
    def _check_rate_limit_fallback(ip: str, path: str) -> None:
        now = _time.time()
        limit, window = RATE_FALLBACK
        for prefix, (lim, win) in RATE_LIMITS.items():
            if path.startswith(prefix):
                limit, window = lim, win
                break
        cutoff = now - window
        _rate_store[ip] = [t for t in _rate_store[ip] if t > cutoff]
        if len(_rate_store[ip]) >= limit:
            raise HTTPException(429, "请求太频繁，请稍后重试")
        _rate_store[ip].append(now)
        if len(_rate_store) > 1000:
            for k in list(_rate_store.keys()):
                _rate_store[k] = [t for t in _rate_store[k] if t > now - 300]
                if not _rate_store[k]:
                    del _rate_store[k]


# ── 生命周期 ───────────────────────────────────────────
from apis.data_sync import init as _data_sync_init, start_periodic_sync as _start_sync

@asynccontextmanager
async def lifespan(app: FastAPI):
    Path("data").mkdir(exist_ok=True)
    Path("outputs").mkdir(exist_ok=True)
    _data_sync_init()
    _start_sync()

    # ── 企业级模块初始化（降级安全）─────────────
    # 缓存管理器
    try:
        from core.cache import get_cache_manager
        cache_mgr = get_cache_manager(config)
        await cache_mgr.initialize()
        cache_health = await cache_mgr.health_check()
        logger.info(f"📦 缓存就绪 — {cache_health}")
    except ImportError:
        logger.info("📦 缓存模块未安装，使用默认行为")
    except Exception as e:
        logger.warning(f"⚠️ 缓存初始化失败: {e}")

    # 限流管理器
    try:
        if _HAS_RATELIMIT_MODULE:
            await _ratelimit.initialize()
            rl_health = await _ratelimit.health_check()
            logger.info(f"🔒 限流就绪 — {rl_health}")
    except Exception as e:
        logger.warning(f"⚠️ 限流初始化失败: {e}")

    # 数据库初始化（降级安全：失败不阻塞启动）
    try:
        from core.database import init_db, get_db_info
        init_db()
        db_info = get_db_info()
        logger.info(f"📊 数据库就绪 — {db_info['type']}: {db_info['url']}")
    except ImportError:
        logger.info("📊 数据库模块未安装，使用JSON存储模式")
    except Exception as e:
        logger.warning(f"⚠️ 数据库初始化失败（降级为JSON模式）: {e}")

    engine = await get_engine()
    logger.info(f"🚀 SG营收引擎启动 v{config.version} — env={config.environment.value} AI: {engine.active_ai} | Template: {engine.active_template} | Shop: {_HAS_SHOP}")
    yield
    logger.info("站点构建器关闭")


app = FastAPI(
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    title="SG 智能建站 — AI独立站营收引擎",
    description="不是建网站，是帮你赚钱。输入一句话，AI生成高转化独立站，含支付、SEO、询盘漏斗。",
    version=config.version,
    lifespan=lifespan,
)

# ── CORS（企业级配置管理）────────────────────────
ALLOWED_ORIGINS = config.cors_origin_list
if config.is_production:
    domain = config.site_domain
    if domain and f"https://{domain}" not in ALLOWED_ORIGINS:
        ALLOWED_ORIGINS.append(f"https://{domain}")

# ── 中间件注册顺序（从外到内）───────────────────
# Gzip压缩（4KB以上才压缩，减少CPU开销）
app.add_middleware(GZipMiddleware, minimum_size=4096)

# Session 中间件（小说翻改等合并项目需要 request.session）
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", config.security.jwt_secret),
    session_cookie="sg_session",
    max_age=86400,  # 24小时
)

# 请求追踪（X-Request-ID + Prometheus指标，降级安全）
if RequestTracingMiddleware is not None:
    app.add_middleware(RequestTracingMiddleware, header_name=config.observability.request_id_header)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.middleware("http")
async def unified_middleware(request: Request, call_next):
    """统一中间件：限流 → 安全头 → 缓存"""
    # 1. 限流检查（企业级：Redis + 内存降级；无模块时用fallback）
    try:
        if _HAS_RATELIMIT_MODULE:
            await _ratelimit.check(request)
        else:
            ip = request.client.host if request.client else "unknown"
            _check_rate_limit_fallback(ip, request.url.path)
    except HTTPException:
        resp = JSONResponse(
            {"detail": "请求太频繁，请稍后重试", "retry_after_seconds": 60},
            status_code=429,
        )
        # 429响应也带安全头
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["X-XSS-Protection"] = "1; mode=block"
        resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        resp.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; img-src 'self' data: https:; font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; connect-src 'self' https://api.qrserver.com; frame-ancestors 'none';"
        return resp

    # 2. 执行请求
    response = await call_next(request)

    # 3. 安全头(所有响应)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; img-src 'self' data: https:; font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; connect-src 'self' https://api.qrserver.com; frame-ancestors 'none';"

    # 4. 缓存策略
    # 静态资源：长缓存（文件内容不变时）
    if request.url.path.startswith("/static/"):
        if any(request.url.path.endswith(ext) for ext in ['.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2']):
            response.headers["Cache-Control"] = "public, max-age=604800"
        else:
            response.headers["Cache-Control"] = "public, max-age=3600"

    # 5. HTML页面不缓存（避免版本更新后用户看到旧页面）
    if request.url.path.endswith('.html') or request.url.path == '/' or (
        request.url.path.startswith('/tools/') and '.' not in request.url.path.split('/')[-1]):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"

    return response

# ── 安全头中间件(必须最先注册，确保所有响应都带安全头) ──





# ── 限流中间件 ─────────────────────────────────────────

# ── 注册路由 ──────────────────────────────────────────
from apis.routes.generate import router as gen_router
from apis.routes.auth import router as auth_router

# 电商路由（可选，模块存在时加载）
try:
    from apis.routes.ecommerce import router as shop_router
    _HAS_SHOP = True
except ImportError:
    _HAS_SHOP = False

# 程序化SEO引擎路由（核心差异化功能）
try:
    from apis.routes.seo import router as seo_router
    _HAS_SEO = True
except ImportError:
    _HAS_SEO = False

# UniPulse 选校报告工具（可选）
try:
    from apis.routes.unipulse import router as unipulse_router
    _HAS_UNIPULSE = True
except ImportError:
    _HAS_UNIPULSE = False

# 短视频去水印工具（可选）
try:
    from apis.routes.watermark import router as watermark_router
    _HAS_WATERMARK = True
except ImportError:
    _HAS_WATERMARK = False

# AI短剧生成工具（可选）
try:
    from apis.routes.drama import router as drama_router
    _HAS_DRAMA = True
except ImportError:
    _HAS_DRAMA = False

# 询盘消息系统
try:
    from apis.routes.inquiry import router as inquiry_router
    from apis.routes.seo_tool import router as seo_tool_router
    from apis.routes.copywrite import router as copywrite_router
    from apis.routes.competitor import router as competitor_router
    from apis.routes.naming import router as naming_router
    _HAS_INQUIRY = True
except ImportError:
    _HAS_INQUIRY = False

# ── 合并项目路由 ──────────────────────────────────────
# 职慧Agent
try:
    from apis.routes.zhihui import router as zhihui_router
    _HAS_ZHIHUI = True
except ImportError:
    _HAS_ZHIHUI = False

# 小说翻改工具
try:
    from apis.routes.novel import router as novel_router
    _HAS_NOVEL = True
except ImportError:
    _HAS_NOVEL = False

# Multi-Agent教育平台
try:
    from apis.routes.edu import router as edu_router
    _HAS_EDU = True
except ImportError:
    _HAS_EDU = False

# IP探测器
try:
    from apis.routes.ip_detector import router as ip_router
    _HAS_IP = True
except ImportError:
    _HAS_IP = False

# 嵌入式开发教程
try:
    from apis.routes.tutorials import router as tutorials_router
    _HAS_TUTORIALS = True
except ImportError:
    _HAS_TUTORIALS = False

# VulnScanner Web漏洞扫描器
try:
    from apis.routes.vulnscanner import router as vulnscanner_router
    _HAS_VULNSCANNER = True
except ImportError:
    _HAS_VULNSCANNER = False

app.include_router(gen_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")

if _HAS_SHOP:
    app.include_router(shop_router, prefix="/api/v1")
if _HAS_SEO:
    app.include_router(seo_router, prefix="/api/v1")
if _HAS_UNIPULSE:
    app.include_router(unipulse_router, prefix="/api/v1")
if _HAS_WATERMARK:
    app.include_router(watermark_router, prefix="/api/v1")
if _HAS_DRAMA:
    app.include_router(drama_router, prefix="/api/v1")
if _HAS_INQUIRY:
    app.include_router(inquiry_router, prefix="/api/v1")
    app.include_router(seo_tool_router, prefix="/api/v1")
    app.include_router(copywrite_router, prefix="/api/v1")
    app.include_router(competitor_router, prefix="/api/v1")
    app.include_router(naming_router, prefix="/api/v1")

# ── 合并项目路由注册 ─────────────────────────────────
if _HAS_ZHIHUI:
    app.include_router(zhihui_router)
if _HAS_NOVEL:
    app.include_router(novel_router)
if _HAS_EDU:
    app.include_router(edu_router)
if _HAS_IP:
    app.include_router(ip_router)
if _HAS_TUTORIALS:
    app.include_router(tutorials_router)
if _HAS_VULNSCANNER:
    app.include_router(vulnscanner_router)

# 静态文件
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
# 合并项目静态文件
for _sub, _dir in [("zhihui", "zhihui"), ("novel", "novel"), ("edu", "edu"), ("ip", "ip"), ("tutorials", "tutorials"), ("worldcup", "worldcup"), ("vuln-scanner", "vuln-scanner")]:
    _sub_dir = STATIC_DIR / _dir
    if _sub_dir.exists():
        app.mount(f"/{_sub}/static", StaticFiles(directory=str(_sub_dir)), name=f"static-{_sub}")


# ── 主页 ──────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return index_path.read_text(encoding="utf-8")
    return HTMLResponse("<h1>前端文件未找到</h1>", status_code=404)


# ── Favicon ──────────────────────────────────────────────
@app.get("/favicon.ico")
async def favicon():
    favicon_path = STATIC_DIR / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(str(favicon_path), media_type="image/x-icon")
    raise HTTPException(status_code=404)


# ── 管理员后台 ──────────────────────────────────────────
@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    admin_path = STATIC_DIR / "admin.html"
    if admin_path.exists():
        return admin_path.read_text(encoding="utf-8")
    return HTMLResponse("<h1>管理后台未找到</h1>", status_code=404)


# ── UniPulse 选校报告工具 ──────────────────────────────
@app.get("/tools/unipulse", response_class=HTMLResponse)
async def unipulse_page():
    """UniPulse 前端SPA — 选校·选专业·看就业"""
    idx = STATIC_DIR / "unipulse" / "index.html"
    if idx.exists():
        return idx.read_text(encoding="utf-8")
    return HTMLResponse("<h1>UniPulse 工具未找到</h1>", status_code=404)


@app.get("/tools/unipulse/{path:path}")
async def unipulse_static(path: str):
    """UniPulse 静态资源代理"""
    file_path = STATIC_DIR / "unipulse" / path
    if file_path.exists() and file_path.is_file():
        return FileResponse(str(file_path))
    # SPA fallback
    idx = STATIC_DIR / "unipulse" / "index.html"
    if idx.exists():
        return FileResponse(str(idx))
    raise HTTPException(status_code=404)


# ── 短视频去水印工具 ────────────────────────────────────
@app.get("/tools/watermark", response_class=HTMLResponse)
async def watermark_page():
    """短视频去水印工具页面"""
    idx = STATIC_DIR / "watermark-remover" / "index.html"
    if idx.exists():
        return idx.read_text(encoding="utf-8")
    return HTMLResponse("<h1>去水印工具未找到</h1>", status_code=404)


# ── AI短剧生成工具 ──────────────────────────────────────
@app.get("/tools/drama", response_class=HTMLResponse)
async def drama_page():
    """AI短剧生成工具页面"""
    idx = STATIC_DIR / "drama-gen" / "index.html"
    if idx.exists():
        return idx.read_text(encoding="utf-8")
    return HTMLResponse("<h1>短剧生成工具未找到</h1>", status_code=404)


@app.get("/tools/seo-keyword", response_class=HTMLResponse)
async def seo_keyword_page():
    idx = STATIC_DIR / "seo-keyword" / "index.html"
    if idx.exists():
        return idx.read_text(encoding="utf-8")
    return HTMLResponse("<h1>SEO关键词分析器未找到</h1>", status_code=404)

@app.get("/tools/copywrite", response_class=HTMLResponse)
async def copywrite_page():
    idx = STATIC_DIR / "ai-copywrite" / "index.html"
    if idx.exists():
        return idx.read_text(encoding="utf-8")
    return HTMLResponse("<h1>AI营销文案工坊未找到</h1>", status_code=404)

@app.get("/tools/competitor", response_class=HTMLResponse)
async def competitor_page():
    idx = STATIC_DIR / "competitor-analysis" / "index.html"
    if idx.exists():
        return idx.read_text(encoding="utf-8")
    return HTMLResponse("<h1>AI竞品分析器未找到</h1>", status_code=404)

@app.get("/tools/naming", response_class=HTMLResponse)
async def naming_page():
    idx = STATIC_DIR / "brand-naming" / "index.html"
    if idx.exists():
        return idx.read_text(encoding="utf-8")
    return HTMLResponse("<h1>AI品牌命名工坊未找到</h1>", status_code=404)




# ── SEO路由：robots.txt + sitemap.xml ─────────────────
@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    domain = os.environ.get("SITE_DOMAIN", "lz-sg-sg-site-builder.hf.space")
    return f"User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /api/\nSitemap: https://{domain}/sitemap.xml"

@app.get("/sitemap.xml", response_class=HTMLResponse)
async def sitemap_xml():
    domain = os.environ.get("SITE_DOMAIN", "lz-sg-sg-site-builder.hf.space")
    return Response(
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f'<url><loc>https://{domain}/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>'
        f'<url><loc>https://{domain}/tools/unipulse</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>'
        f'<url><loc>https://{domain}/tools/watermark</loc><changefreq>monthly</changefreq><priority>0.6</priority></url>'
        f'<url><loc>https://{domain}/tools/drama</loc><changefreq>monthly</changefreq><priority>0.6</priority></url>'
        f'<url><loc>https://{domain}/tools/seo-keyword</loc><changefreq>monthly</changefreq><priority>0.7</priority></url>'
        f'<url><loc>https://{domain}/tools/copywrite</loc><changefreq>monthly</changefreq><priority>0.7</priority></url>'
        f'<url><loc>https://{domain}/tools/competitor</loc><changefreq>monthly</changefreq><priority>0.7</priority></url>'
        f'<url><loc>https://{domain}/tools/naming</loc><changefreq>monthly</changefreq><priority>0.7</priority></url>'
        f'<url><loc>https://{domain}/vuln-scanner</loc><changefreq>monthly</changefreq><priority>0.8</priority></url>'
        f'</urlset>',
        media_type="application/xml"
    )


# ── 企业级健康检查（降级安全）─────────────────────
try:
    from core.health import router as health_router
    app.include_router(health_router)
except ImportError:
    pass  # 健康检查模块未安装，跳过

# 兼容旧路径 /api/v1/health
@app.get("/api/v1/health")
async def health_legacy():
    engine = await get_engine()
    # 企业级组件状态（降级安全）
    cache_status = {"status": "not_installed"}
    ratelimit_status = {"status": "not_installed"}
    try:
        from core.cache import get_cache_manager
        cache_mgr = get_cache_manager(config)
        cache_status = await cache_mgr.health_check()
    except Exception:
        pass
    try:
        if _HAS_RATELIMIT_MODULE:
            ratelimit_status = await _ratelimit.health_check()
        else:
            ratelimit_status = {"status": "memory_fallback"}
    except Exception:
        pass
    return {
        "status": "ok",
        "version": config.version,
        "environment": config.environment.value,
        "ai_backend": engine.active_ai,
        "template_backend": engine.active_template,
        "tools": {
            "watermark": _HAS_WATERMARK,
            "drama": _HAS_DRAMA,
            "unipulse": _HAS_UNIPULSE,
            "vuln-scanner": _HAS_VULNSCANNER,
            "seo_keyword": _HAS_INQUIRY,
            "copywrite": _HAS_INQUIRY,
            "competitor": _HAS_INQUIRY,
            "naming": _HAS_INQUIRY,
        },
        "enterprise": {
            "cache": cache_status,
            "rate_limit": ratelimit_status,
        },
    }

# ── Prometheus 监控指标端点（降级安全）──────────────
if metrics_endpoint is not None and getattr(config.observability, 'metrics_enabled', False):
    @app.get(getattr(config.observability, 'metrics_path', '/metrics'))
    async def prometheus_metrics(request: Request):
        return await metrics_endpoint(request)


# ── 全局404处理 ─────────────────────────────────────────
@app.exception_handler(404)
async def custom_404(request: Request, exc):
    # API路径返回JSON
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Not found"}, status_code=404)
    # 其他返回自定义404页面
    return HTMLResponse(
        '<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>404 - 页面不存在 | SG智能建站</title>'
        '<style>*{margin:0;padding:0;box-sizing:border-box}body{min-height:100vh;display:flex;align-items:center;justify-content:center;background:#0a0e1a;color:#fff;font-family:system-ui}'
        '.card{text-align:center;padding:48px 32px}h1{font-size:96px;font-weight:800;background:linear-gradient(135deg,#667eea,#764ba2);-webkit-background-clip:text;-webkit-text-fill-color:transparent}p{color:rgba(255,255,255,.6);margin:16px 0 32px;font-size:18px}a{color:#667eea;text-decoration:none;font-weight:600}a:hover{text-decoration:underline}</style>'
        '</head><body><div class="card"><h1>404</h1><p>页面不存在或已过期</p><a href="/">返回首页</a></div></body></html>',
        status_code=404
    )