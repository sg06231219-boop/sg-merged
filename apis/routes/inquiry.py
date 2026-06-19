"""询盘消息系统 - 解决商家联系收不到消息问题"""
from apis.routes.auth import require_admin
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime
from pathlib import Path
from apis.file_lock import safe_read_json, safe_write_json
import json, uuid, re


# ── 简单防刷：同IP 60秒内只能提交1次 ──
_inquiry_ips = {}

def _check_inquiry_rate(ip: str):
    import time
    now = time.time()
    last = _inquiry_ips.get(ip, 0)
    if now - last < 60:
        raise HTTPException(429, "提交太频繁，请60秒后再试")
    _inquiry_ips[ip] = now
    # 清理超过5分钟的记录
    _inquiry_ips.update({k: v for k, v in _inquiry_ips.items() if now - v < 300})

router = APIRouter()

# === 数据存储 ===
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
INQUIRIES_FILE = DATA_DIR / "inquiries.json"

def _load_inquiries() -> dict:
    if INQUIRIES_FILE.exists():
        return json.loads(INQUIRIES_FILE.read_text(encoding="utf-8"))
    return {}

def _save_inquiries(data: dict):
    INQUIRIES_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

# === 请求模型 ===
class InquirySubmit(BaseModel):
    site_id: str = ""      # 站点ID（可选）
    name: str = ""
    contact: str          # 手机号或邮箱
    message: str = ""
    source: str = ""      # 来源站点URL（可选）

# === API端点 ===
@router.post("/inquiry")
async def submit_inquiry(req: InquirySubmit, request: Request):
    """接收询盘/联系表单消息"""
    # 验证联系方式
    contact = req.contact.strip()
    if not contact:
        raise HTTPException(400, "请填写联系方式")
    
    # 验证是否为有效手机或邮箱
    phone_pattern = r"^1[3-9]\d{9}$"
    email_pattern = r"^[\w.-]+@[\w.-]+\.\w+$"
    if not (re.match(phone_pattern, contact) or re.match(email_pattern, contact)):
        raise HTTPException(400, "联系方式格式不正确（需手机号或邮箱）")
    
    # 创建询盘记录
    inquiry_id = uuid.uuid4().hex[:12]
    inquiries = _load_inquiries()
    inquiries[inquiry_id] = {
        "id": inquiry_id,
        "site_id": req.site_id,
        "name": req.name.strip(),
        "contact": contact,
        "message": req.message.strip(),
        "source": req.source,
        "ip": _get_client_ip(request),
        "created_at": datetime.now().isoformat(),
        "status": "new",  # new/read/replied/archived
    }
    _save_inquiries(inquiries)
    
    return {
        "success": True,
        "message": "询盘提交成功！商家会尽快联系您",
        "inquiry_id": inquiry_id,
    }

@router.get("/inquiries")
async def list_inquiries(limit: int = 50, status: str = None):
    """列出询盘消息（管理员查看）"""
    inquiries = _load_inquiries()
    items = list(inquiries.values())
    
    # 按时间倒序
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    # 状态筛选
    if status:
        items = [i for i in items if i.get("status") == status]
    
    # 限制数量
    items = items[:limit]
    
    return {
        "total": len(inquiries),
        "items": items,
    }

@router.patch("/inquiry/{inquiry_id}")
async def update_inquiry_status(inquiry_id: str, status: str, admin: dict = Depends(require_admin)):
    """更新询盘状态"""
    inquiries = _load_inquiries()
    if inquiry_id not in inquiries:
        raise HTTPException(404, "询盘不存在")
    
    if status not in ("new", "read", "replied", "archived"):
        raise HTTPException(400, "状态值无效")
    
    inquiries[inquiry_id]["status"] = status
    inquiries[inquiry_id]["updated_at"] = datetime.now().isoformat()
    _save_inquiries(inquiries)
    
    return {"success": True, "status": status}

def _get_client_ip(request: Request) -> str:
    """获取客户端IP"""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"