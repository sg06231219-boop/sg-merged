"""短视频去水印 API — 解析抖音/快手/小红书/微博/B站链接
注：国内平台反爬严格，免费方案下服务端解析成功率极低。
此工具保留为"外部工具导航"模式，提供平台识别+跳转建议。
"""
from __future__ import annotations
import re, logging
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from apis.routes._tool_base import (
    check_rate_limit, check_daily_quota, get_quota_info
)

router = APIRouter(prefix="/watermark", tags=["watermark"])
log = logging.getLogger("watermark")

# ── 平台识别 ──────────────────────────────────────────
_PATTERNS = [
    (r"(douyin\.com|iesdouyin\.com)", "douyin"),
    (r"(kuaishou\.com|gifshow\.com)", "kuaishou"),
    (r"(xiaohongshu\.com|xhslink\.com)", "xiaohongshu"),
    (r"(weibo\.com|weibo\.cn)", "weibo"),
    (r"(bilibili\.com|b23\.tv)", "bilibili"),
]

def _detect_platform(url: str) -> str:
    for pat, name in _PATTERNS:
        if re.search(pat, url, re.I):
            return name
    return "unknown"

# ── 外部工具推荐 ──
_EXTERNAL_TOOLS = {
    "douyin": [
        {"name": "抖音解析", "url": "https://douyin.wtf/", "desc": "在线抖音视频下载"},
        {"name": "SnapTik", "url": "https://snaptik.app/", "desc": "TikTok/抖音下载"},
    ],
    "kuaishou": [
        {"name": "快手解析", "url": "https://douyin.wtf/", "desc": "支持快手链接"},
    ],
    "xiaohongshu": [
        {"name": "小红书解析", "url": "https://douyin.wtf/", "desc": "支持小红书笔记"},
    ],
    "bilibili": [
        {"name": "B站下载", "url": "https://xbeibeix.com/api/bilibili/", "desc": "B站视频解析"},
    ],
    "weibo": [
        {"name": "微博视频", "url": "https://douyin.wtf/", "desc": "支持微博视频"},
    ],
}

class ParseRequest(BaseModel):
    url: str = Field(..., min_length=5, max_length=2048)

@router.post("/parse")
async def parse_video(req: ParseRequest, request: Request):
    """识别平台+返回外部工具推荐"""
    client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() \
                or (request.client.host if request.client else "unknown")
    if not check_rate_limit(client_ip, "wm", 10, 60):
        raise HTTPException(429, "请求过于频繁，请稍后再试")
    
    await check_daily_quota(request)
    
    url = req.url.strip()
    if not re.match(r"https?://", url, re.I):
        if "://" not in url and re.match(r"[\w.-]+\.\w+", url):
            url = "https://" + url
        else:
            raise HTTPException(422, "请输入有效的视频链接")
    
    platform = _detect_platform(url)
    if platform == "unknown":
        raise HTTPException(422, "暂不支持该平台，目前支持：抖音、快手、小红书、微博、B站")
    
    tools = _EXTERNAL_TOOLS.get(platform, [])
    return {
        "success": True,
        "mode": "external",
        "platform": platform,
        "platform_name": {"douyin":"抖音","kuaishou":"快手","xiaohongshu":"小红书","weibo":"微博","bilibili":"B站"}.get(platform, platform),
        "message": f"检测到{platform}链接，由于平台反爬限制，请使用以下工具解析",
        "external_tools": tools,
        "tip": "复制链接到上方工具即可下载无水印视频"
    }

@router.get("/quota")
async def get_quota(request: Request):
    return get_quota_info(request)

@router.get("/platforms")
async def list_platforms():
    return {
        "platforms": [
            {"id": "douyin", "name": "抖音", "icon": "🎵", "domains": ["douyin.com", "iesdouyin.com"]},
            {"id": "kuaishou", "name": "快手", "icon": "🎬", "domains": ["kuaishou.com", "gifshow.com"]},
            {"id": "xiaohongshu", "name": "小红书", "icon": "📕", "domains": ["xiaohongshu.com", "xhslink.com"]},
            {"id": "weibo", "name": "微博", "icon": "📢", "domains": ["weibo.com", "weibo.cn"]},
            {"id": "bilibili", "name": "B站", "icon": "📺", "domains": ["bilibili.com", "b23.tv"]},
        ]
    }
