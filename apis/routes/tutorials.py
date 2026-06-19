"""
Embedded Dev Tutorials - APIRouter 模块
v1.6.4 → v1.7.0
提取自 embedded-dev-site/app.py，作为独立 APIRouter 挂载
"""
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/tutorials", tags=["tutorials"])

# 静态文件目录（从 sg-merged 根出发的相对路径）
ROOT_DIR = Path(__file__).resolve().parent.parent.parent  # sg-merged/
STATIC_DIR = ROOT_DIR / "static" / "embedded-dev-site"


@router.get("/")
async def index():
    """首页"""
    return FileResponse(str(STATIC_DIR / "index.html"))


@router.get("/api/health")
async def health():
    """健康检查"""
    return {"status": "ok", "version": "1.7.0", "service": "embedded-dev-tutorials"}


@router.get("/{page_name:path}")
async def tutorial_page(page_name: str):
    """SPA fallback: 所有 /tutorials/* 路由返回 index.html"""
    return FileResponse(str(STATIC_DIR / "index.html"))
