import os
"""
apis.routes.auth — 用户认证路由（永久免费版）

安全特性：
- JWT token 认证（HS256）
- 密码 sha256 + salt 哈希
- 管理员JWT认证（非明文密码查询参数）
"""

import hashlib
import hmac
from apis.file_lock import safe_read_json, safe_write_json
import json
import time
import uuid
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel


# ── 管理员登录限流 ──
_admin_login_attempts = {}

def _check_admin_rate(ip: str):
    import time
    now = time.time()
    attempts = _admin_login_attempts.get(ip, [])
    attempts = [t for t in attempts if now - t < 300]
    if len(attempts) >= 5:
        raise HTTPException(429, "登录尝试过多，请5分钟后再试")
    _admin_login_attempts[ip] = attempts

def _record_admin_attempt(ip: str):
    import time
    if ip not in _admin_login_attempts:
        _admin_login_attempts[ip] = []
    _admin_login_attempts[ip].append(time.time())


router = APIRouter(tags=["用户"])

# ── 配置 ──────────────────────────────────────────────
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Lys13579")
if ADMIN_PASSWORD == "Lys13579":
    import logging; logging.getLogger(__name__).warning("⚠️ 使用默认管理员密码，请设置环境变量 ADMIN_PASSWORD")

# JWT_SECRET 独立于密码，避免密码泄露时JWT可被伪造
_JWT_SECRET_PATH = Path("data") / ".jwt_secret"
def _init_jwt_secret() -> str:
    env = os.environ.get("JWT_SECRET")
    if env:
        return env
    if _JWT_SECRET_PATH.exists():
        return _JWT_SECRET_PATH.read_text().strip()
    secret = secrets.token_hex(32)
    _JWT_SECRET_PATH.write_text(secret)
    return secret
JWT_SECRET = _init_jwt_secret()
JWT_EXPIRE_HOURS = 72
ADMIN_JWT_EXPIRE_HOURS = 72

# ── 登录/注册速率限制 ───────────────────────────────
from collections import defaultdict as _dd
_auth_attempts: dict[str, list] = _dd(list)
AUTH_RATE_LIMIT = 10
AUTH_RATE_WINDOW = 60

def _get_client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    xri = request.headers.get("x-real-ip", "")
    if xri:
        return xri.strip()
    return request.client.host if request.client else "unknown"

def _check_auth_rate(ip: str) -> None:
    now = time.time()
    cutoff = now - AUTH_RATE_WINDOW
    _auth_attempts[ip] = [t for t in _auth_attempts[ip] if t > cutoff]
    if len(_auth_attempts[ip]) >= AUTH_RATE_LIMIT:
        raise HTTPException(429, "尝试太频繁，请稍后再试")
    _auth_attempts[ip].append(now)

# ── 数据库（JSON文件）──────────────────────────────────
DB_PATH = Path("data")
DB_PATH.mkdir(exist_ok=True)
USERS_DB = DB_PATH / "users.json"

def _load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}

def _save_json(path: Path, data: dict):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        from apis.data_sync import mark_dirty
        mark_dirty(path.name)
    except Exception:
        pass

def _load_users() -> dict:
    return _load_json(USERS_DB)

def _save_users(users: dict):
    _save_json(USERS_DB, users)

# ── 密码哈希 ──────────────────────────────────────────
def _hash_password(password: str, salt: str = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return hashed, salt

def _verify_password(password: str, hashed: str, salt: str) -> bool:
    check, _ = _hash_password(password, salt)
    return hmac.compare_digest(check, hashed)

# ── JWT ───────────────────────────────────────────────
import base64

def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)

def _create_jwt(payload: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    h = _b64url(json.dumps(header).encode())
    p = _b64url(json.dumps(payload).encode())
    sig = hmac.new(JWT_SECRET.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()
    return f"{h}.{p}.{_b64url(sig)}"

def _verify_jwt(token: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        h, p, s = parts
        expected_sig = hmac.new(JWT_SECRET.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(_b64url_decode(s), expected_sig):
            return None
        payload = json.loads(_b64url_decode(p))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None

# ── 请求模型 ──────────────────────────────────────────
class RegisterReq(BaseModel):
    username: str = ""
    password: str
    email: str = ""

class LoginReq(BaseModel):
    username: str = ""
    email: str = ""
    password: str

class AdminLoginReq(BaseModel):
    password: str

# ── 认证依赖 ──────────────────────────────────────────
async def get_current_user(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "未登录")
    payload = _verify_jwt(auth[7:])
    if not payload:
        raise HTTPException(401, "登录已过期")
    users = _load_users()
    uid = payload.get("uid")
    if uid not in users:
        raise HTTPException(401, "用户不存在")
    return users[uid]

async def require_admin(request: Request) -> dict:
    """管理员JWT认证依赖"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "请先登录管理员账号")
    payload = _verify_jwt(auth[7:])
    if not payload:
        raise HTTPException(401, "登录已过期，请重新登录")
    if payload.get("role") != "admin":
        raise HTTPException(403, "无管理员权限")
    return payload

# ── 用户 API ──────────────────────────────────────────
@router.post("/register")
async def register(req: RegisterReq, request: Request):
    ip = _get_client_ip(request)
    _check_auth_rate(ip)
    raw_username = req.username.strip()
    raw_email = req.email.strip()
    if raw_username and "@" in raw_username and raw_email == raw_username:
        username = raw_username.split("@")[0]
    elif raw_username:
        username = raw_username
    elif raw_email:
        username = raw_email.split("@")[0]
    else:
        username = ""
    password = req.password
    email = req.email.strip()
    if not username or len(username) > 30:
        raise HTTPException(400, "用户名2-30个字符")
    if len(password) < 6:
        raise HTTPException(400, "密码至少6位")
    
    users = _load_users()
    for u in users.values():
        if u.get("username") == username:
            raise HTTPException(400, "用户名已存在")
        if email and u.get("email") == email:
            raise HTTPException(400, "该邮箱已注册")
    
    uid = uuid.uuid4().hex[:12]
    hashed, salt = _hash_password(password)
    users[uid] = {
        "uid": uid,
        "username": username,
        "email": email,
        "password_hash": hashed,
        "password_salt": salt,
        "usage": {},
        "created_at": datetime.now().isoformat(),
    }
    _save_users(users)
    
    token = _create_jwt({
        "uid": uid, "username": username,
        "exp": time.time() + JWT_EXPIRE_HOURS * 3600,
    })
    return {
        "success": True, "token": token, "access_token": token,
        "user": {"uid": uid, "username": username, "email": email},
    }

@router.post("/login")
async def login(req: LoginReq, request: Request):
    ip = _get_client_ip(request)
    _check_auth_rate(ip)
    users = _load_users()
    login_id = req.username or req.email
    for uid, u in users.items():
        if u.get("username") == login_id or u.get("email") == login_id:
            if _verify_password(req.password, u["password_hash"], u["password_salt"]):
                token = _create_jwt({
                    "uid": uid, "username": u["username"],
                    "exp": time.time() + JWT_EXPIRE_HOURS * 3600,
                })
                return {
                    "success": True, "token": token, "access_token": token,
                    "user": {"uid": uid, "username": u["username"], "email": u.get("email", "")},
                }
    raise HTTPException(401, "用户名或密码错误")

@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    return {
        "uid": user["uid"], "username": user["username"], "email": user.get("email", ""),
        "usage_today": user.get("usage", {}).get(datetime.now().strftime("%Y-%m-%d"), 0),
    }

@router.get("/history")
async def get_history(user: dict = Depends(get_current_user)):
    return user.get("history", [])


# ══════════════════════════════════════════════════════
# 管理员 API（JWT认证）
# ══════════════════════════════════════════════════════

@router.post("/admin/login")
async def admin_login(req: AdminLoginReq, request: Request):
    ip = _get_client_ip(request)
    _check_auth_rate(ip)
    if not hmac.compare_digest(req.password, ADMIN_PASSWORD):
        raise HTTPException(403, "管理员密码错误")
    
    token = _create_jwt({
        "role": "admin",
        "exp": time.time() + ADMIN_JWT_EXPIRE_HOURS * 3600,
    })
    return {"success": True, "token": token}

@router.get("/admin/stats")
async def admin_stats(admin: dict = Depends(require_admin)):
    users = _load_users()
    total_users = len(users)
    
    today = datetime.now().strftime("%Y-%m-%d")
    active_today = sum(1 for u in users.values() if u.get("usage", {}).get(today, 0) > 0)
    
    outputs_dir = Path("outputs")
    html_files = list(outputs_dir.glob("*.html")) if outputs_dir.exists() else []
    zip_files = list(outputs_dir.glob("*.zip")) if outputs_dir.exists() else []
    
    return {
        "total_users": total_users,
        "active_today": active_today,
        "generated_pages": len(html_files),
        "generated_sites": len(zip_files),
    }

@router.get("/admin/users")
async def admin_list_users(admin: dict = Depends(require_admin)):
    users = _load_users()
    result = []
    for u in users.values():
        result.append({
            "uid": u["uid"],
            "username": u.get("username", ""),
            "email": u.get("email", ""),
            "usage_today": u.get("usage", {}).get(datetime.now().strftime("%Y-%m-%d"), 0),
            "history_count": len(u.get("history", [])),
            "created_at": u.get("created_at"),
        })
    return sorted(result, key=lambda u: u.get("created_at", ""), reverse=True)

@router.delete("/admin/users/{uid}")
async def admin_delete_user(uid: str, admin: dict = Depends(require_admin)):
    users = _load_users()
    if uid not in users:
        raise HTTPException(404, "用户不存在")
    del users[uid]
    _save_users(users)
    return {"success": True, "message": "用户已删除"}

@router.get("/admin/pages")
async def admin_list_pages(admin: dict = Depends(require_admin)):
    outputs_dir = Path("outputs")
    if not outputs_dir.exists():
        return []
    
    pages = []
    for f in outputs_dir.glob("*.html"):
        stat = f.stat()
        pages.append({
            "id": f.stem,
            "type": "html",
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
    for f in outputs_dir.glob("*.zip"):
        stat = f.stat()
        pages.append({
            "id": f.stem,
            "type": "zip",
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
    
    return sorted(pages, key=lambda p: p.get("created", ""), reverse=True)[:100]

@router.delete("/admin/pages/{page_id}")
async def admin_delete_page(page_id: str, admin: dict = Depends(require_admin)):
    import re
    if not re.match(r"^[a-f0-9]{12}$", page_id):
        raise HTTPException(400, "非法ID")
    
    deleted = []
    for ext in [".html", ".zip"]:
        f = Path("outputs") / f"{page_id}{ext}"
        if f.exists():
            f.unlink()
            deleted.append(ext)
    
    if not deleted:
        raise HTTPException(404, "页面不存在")
    
    return {"success": True, "deleted": deleted}

@router.post("/admin/cleanup")
async def admin_cleanup(request: Request, admin: dict = Depends(require_admin)):
    import logging; _log = logging.getLogger(__name__)
    try:
        body = await request.json() if request.headers.get("content-type") == "application/json" else {}
        days = body.get("days", 7)
        
        cutoff = datetime.now() - timedelta(days=days)
        outputs_dir = Path("outputs")
        cleaned = 0
        
        if outputs_dir.exists():
            for f in outputs_dir.iterdir():
                if f.is_file():
                    mtime = datetime.fromtimestamp(f.stat().st_mtime)
                    if mtime < cutoff:
                        f.unlink()
                        cleaned += 1
        
        return {"success": True, "cleaned_files": cleaned, "older_than_days": days}
    except HTTPException:
        raise
    except Exception as e:
        _log.error(f"清理失败: {e}")
        raise HTTPException(500, "清理操作失败")
