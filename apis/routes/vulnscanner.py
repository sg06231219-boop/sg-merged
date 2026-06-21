"""
VulnScanner - Web Vulnerability Scanner API Router
"""
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime

router = APIRouter(prefix="/vuln-scanner", tags=["vuln-scanner"])

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = ROOT_DIR / "static" / "vuln-scanner"


class ScanRequest(BaseModel):
    url: str
    speed: Literal["fast", "normal", "thorough"] = "normal"
    modules: Optional[list[str]] = None


@router.get("/", response_class=HTMLResponse)
async def vuln_scanner_page():
    idx = STATIC_DIR / "index.html"
    if idx.exists():
        return idx.read_text(encoding="utf-8")
    return HTMLResponse("<h1>VulnScanner Not Found</h1>", status_code=404)


@router.get("/{path:path}")
async def vulnscanner_static(path: str):
    file_path = STATIC_DIR / path
    if file_path.exists() and file_path.is_file():
        return FileResponse(str(file_path))
    idx = STATIC_DIR / "index.html"
    if idx.exists():
        return FileResponse(str(idx))
    raise HTTPException(status_code=404)


@router.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "service": "vuln-scanner",
        "modules": ["sqli", "xss", "sensitive", "headers", "redirect", "info"]
    }


@router.post("/api/scan")
async def scan(req: ScanRequest):
    from scanner.core import Scanner
    
    risk_map = {"fast": "low", "normal": "medium", "thorough": "high"}
    scanner = Scanner(config={
        "target": req.url,
        "risk_level": risk_map.get(req.speed, "medium"),
        "concurrency": 5 if req.speed == "thorough" else 10,
        "delay": 0.5 if req.speed == "thorough" else 0,
    })
    
    async with scanner:
        report = await scanner.scan(req.url)
    
    result_list = []
    for r in report.results:
        result_list.append({
            "module": r.check_name,
            "title": r.title,
            "risk": r.severity,
            "url": req.url,
            "detail": r.description,
            "evidence": r.evidence or "",
        })
    
    return {
        "success": True,
        "target": req.url,
        "speed": req.speed,
        "results": result_list,
        "summary": report.summary,
        "scanned_at": datetime.now().isoformat()
    }
