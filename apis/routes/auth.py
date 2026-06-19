import os
"""
apis.routes.auth — 用户认证 & 付费墙路由（零成本激活码方案）

安全特性：
- JWT token 认证（HS256）
- 密码 sha256 + salt 哈希
- 用量追踪（免费3次/天，付费无限）
- 激活码系统（管理员生成，用户输入激活）
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
    # 保留最近5分钟的尝试
    attempts = [t for t in attempts if now - t < 300]
    if len(attempts) >= 5:
        raise HTTPException(429, "登录尝试过多，请5分钟后再试")
    _admin_login_attempts[ip] = attempts

def _record_admin_attempt(ip: str):
    import time
    if ip not in _admin_login_attempts:
        _admin_login_attempts[ip] = []
    _admin_login_attempts[ip].append(time.time())


# ── 激活码全局限流 ──
_activate_code_attempts = {}

def _check_activate_rate(ip: str):
    import time
    now = time.time()
    attempts = _activate_code_attempts.get(ip, [])
    attempts = [t for t in attempts if now - t < 300]
    if len(attempts) >= 5:
        raise HTTPException(429, "激活尝试过多，请5分钟后再试")
    _activate_code_attempts[ip] = attempts

router = APIRouter(tags=["用户"])

# ── 配置 ──────────────────────────────────────────────
# 管理员密码
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Lys13579")
if ADMIN_PASSWORD == "Lys13579":
    import logging; logging.getLogger(__name__).warning("⚠️ 使用默认管理员密码，请设置环境变量 ADMIN_PASSWORD")

# JWT_SECRET 独立于密码，避免密码泄露时JWT可被伪造
# 优先从环境变量读取，其次使用启动时随机生成（仅单实例有效，重启后旧token失效）
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

FREE_DAILY_LIMIT = 3
ACTIVATION_CODE_PREFIX = "SB"  # 激活码前缀

# ── 登录/注册速率限制 ───────────────────────────────
from collections import defaultdict as _dd
_auth_attempts: dict[str, list] = _dd(list)
AUTH_RATE_LIMIT = 10   # 每IP每分钟最多10次
AUTH_RATE_WINDOW = 60  # 秒

def _get_client_ip(request: Request) -> str:
    """获取真实客户端IP（优先X-Forwarded-For，兼容反代）"""
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

# 管理员密码默认 Lys13579，可通过环境变量 ADMIN_PASSWORD 覆盖

# ── 数据库（JSON文件）──────────────────────────────────
DB_PATH = Path("data")
DB_PATH.mkdir(exist_ok=True)
USERS_DB = DB_PATH / "users.json"
CODES_DB = DB_PATH / "codes.json"

def _load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}

def _save_json(path: Path, data: dict):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    # 数据持久化同步
    try:
        from apis.data_sync import mark_dirty
        mark_dirty(path.name)
    except Exception:
        pass

def _load_users() -> dict:
    return _load_json(USERS_DB)

def _save_users(users: dict):
    _save_json(USERS_DB, users)

def _load_codes() -> dict:
    return _load_json(CODES_DB)

def _save_codes(codes: dict):
    _save_json(CODES_DB, codes)

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

# ── 用量追踪 ──────────────────────────────────────────
def _today_key() -> str:
    return datetime.now().strftime("%Y-%m-%d")

def _get_daily_usage(user: dict) -> int:
    return user.get("usage", {}).get(_today_key(), 0)

def _increment_usage(user: dict) -> int:
    usage = user.get("usage", {})
    today = _today_key()
    usage[today] = usage.get(today, 0) + 1
    # 清理7天前记录
    cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    for k in list(usage.keys()):
        if k < cutoff:
            del usage[k]
    user["usage"] = usage
    return usage[today]

def _is_pro(user: dict) -> bool:
    expire = user.get("pro_expire")
    if not expire:
        return False
    try:
        return datetime.fromisoformat(expire) > datetime.now()
    except Exception:
        return False

# ── 激活码生成 ────────────────────────────────────────
def _generate_code(plan_type: str = "monthly", count: int = 1) -> list[str]:
    codes = _load_codes()
    result = []
    for _ in range(count):
        code = f"{ACTIVATION_CODE_PREFIX}-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"
        codes[code] = {
            "code": code,
            "plan_type": plan_type,
            "used": False,
            "used_by": None,
                    "trial_available": True,  # 新用户有一次专业版试用机会
        "trial_used_at": None,
"created_at": datetime.now().isoformat(),
    }
        result.append(code)
    _save_codes(codes)
    return result

# ── 请求模型 ──────────────────────────────────────────
class RegisterReq(BaseModel):
    username: str = ""
    password: str
    email: str = ""

class LoginReq(BaseModel):
    username: str = ""
    email: str = ""
    password: str

class ActivateReq(BaseModel):
    code: str

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

async def check_usage_limit(user: dict = Depends(get_current_user)) -> dict:
    if _is_pro(user):
        return user
    if _get_daily_usage(user) >= FREE_DAILY_LIMIT:
        raise HTTPException(429, f"免费用户每日限{FREE_DAILY_LIMIT}次，升级专业版无限制")
    return user

async def require_admin(request: Request) -> dict:
    """管理员JWT认证依赖（替代明文密码查询参数）"""
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
    # 智能提取用户名：如果username看起来像邮箱，自动取@前部分
    raw_username = req.username.strip()
    raw_email = req.email.strip()
    if raw_username and "@" in raw_username and raw_email == raw_username:
        # 前端传 username=email, email=email 的情况，取@前缀作为用户名
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
        "plan": "free",
        "pro_expire": None,
        "usage": {},
                "trial_available": True,  # 新用户有一次专业版试用机会
        "trial_used_at": None,
"created_at": datetime.now().isoformat(),
    }
    _save_users(users)
    
    token = _create_jwt({
        "uid": uid, "username": username, "plan": "free",
        "exp": time.time() + JWT_EXPIRE_HOURS * 3600,
    })
    return {
        "success": True, "token": token, "access_token": token,
        "user": {"uid": uid, "username": username, "email": email, "plan": "free", "pro_expire": None},
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
                plan = "pro" if _is_pro(u) else "free"
                token = _create_jwt({
                    "uid": uid, "username": u["username"], "plan": plan,
                    "exp": time.time() + JWT_EXPIRE_HOURS * 3600,
                })
                return {
                    "success": True, "token": token, "access_token": token,
                    "user": {"uid": uid, "username": u["username"], "email": u.get("email", ""), "plan": plan, "pro_expire": u.get("pro_expire")},
                }
    raise HTTPException(401, "用户名或密码错误")

@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    plan = "pro" if _is_pro(user) else "free"
    return {
        "uid": user["uid"], "username": user["username"], "email": user.get("email", ""), "plan": plan,
        "pro_expire": user.get("pro_expire"),
        "usage_today": _get_daily_usage(user),
        "daily_limit": FREE_DAILY_LIMIT if plan == "free" else -1,
    }

@router.get("/history")
async def get_history(user: dict = Depends(get_current_user)):
    """获取用户生成历史"""
    return user.get("history", [])


# ── 专业版试用 ──────────────────────────────────────────
@router.get("/trial/status")
async def get_trial_status(request: Request):
    """查询专业版试用状态（无需认证，按IP判断）"""
    ip = request.client.host if request.client else "unknown"
    # 尝试从token获取用户信息
    user = None
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            user = await get_current_user(auth_header.split(" ", 1)[1])
        except Exception:
            pass
    if user:
        return {
            "trial_available": user.get("trial_available", False),
            "trial_used_at": user.get("trial_used_at"),
            "is_pro": _is_pro(user),
            "message": "您有一次专业版试用机会" if user.get("trial_available", False) else "试用机会已使用"
        }
    # 未登录：返回通用状态
    return {
        "trial_available": True,
        "trial_used_at": None,
        "is_pro": False,
        "message": "登录后可使用专业版试用功能"
    }

@router.post("/trial/use")
async def use_trial(user: dict = Depends(get_current_user)):
    """使用专业版试用机会（仅限一次）"""
    if not user.get("trial_available", False):
        raise HTTPException(400, "试用机会已使用或不存在")
    if _is_pro(user):
        raise HTTPException(400, "您已是专业版用户，无需使用试用")
    
    users = _load_users()
    uid = user["uid"]
    users[uid]["trial_available"] = False
    users[uid]["trial_used_at"] = datetime.now().isoformat()
    _save_users(users)
    
    return {
        "success": True,
        "message": "试用机会已激活！本次生成将享受专业版待遇",
        "trial_used_at": users[uid]["trial_used_at"]
    }

# ── 激活码 API ────────────────────────────────────────
@router.post("/activate")
async def activate_code(req: ActivateReq, user: dict = Depends(get_current_user)):
    """用户输入激活码升级专业版"""
    code = req.code.strip().upper()
    codes = _load_codes()
    
    if code not in codes:
        raise HTTPException(400, "激活码无效")
    
    code_info = codes[code]
    if code_info["used"]:
        raise HTTPException(400, "激活码已被使用")
    
    # 激活
    code_info["used"] = True
    code_info["used_by"] = user["uid"]
    code_info["used_at"] = datetime.now().isoformat()
    _save_codes(codes)
    
    # 更新用户
    users = _load_users()
    uid = user["uid"]
    plan_type = code_info["plan_type"]
    
    # 如果已是专业版，在现有基础上延长
    current_expire = users[uid].get("pro_expire")
    if current_expire:
        try:
            base = datetime.fromisoformat(current_expire)
            if base < datetime.now():
                base = datetime.now()
        except Exception:
            base = datetime.now()
    else:
        base = datetime.now()
    
    if plan_type == "yearly":
        new_expire = base + timedelta(days=365)
    else:
        new_expire = base + timedelta(days=30)
    
    users[uid]["plan"] = "pro"
    users[uid]["pro_expire"] = new_expire.isoformat()
    _save_users(users)
    
    return {
        "success": True,
        "plan": "pro",
        "pro_expire": new_expire.isoformat(),
        "days": 365 if plan_type == "yearly" else 30,
        "message": f"专业版激活成功！有效期至 {new_expire.strftime('%Y-%m-%d')}",
    }

# ══════════════════════════════════════════════════════
# 管理员 API（JWT认证，非明文密码）
# ══════════════════════════════════════════════════════

@router.post("/admin/login")
async def admin_login(req: AdminLoginReq, request: Request):
    """管理员登录，返回JWT token"""
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
    """管理员查看统计"""
    users = _load_users()
    codes = _load_codes()
    
    total_users = len(users)
    pro_users = sum(1 for u in users.values() if _is_pro(u))
    total_codes = len(codes)
    used_codes = sum(1 for c in codes.values() if c["used"])
    
    # 生成文件统计
    outputs_dir = Path("outputs")
    html_files = list(outputs_dir.glob("*.html")) if outputs_dir.exists() else []
    zip_files = list(outputs_dir.glob("*.zip")) if outputs_dir.exists() else []
    
    # 今日活跃
    today = _today_key()
    active_today = sum(1 for u in users.values() if u.get("usage", {}).get(today, 0) > 0)
    
    return {
        "total_users": total_users,
        "pro_users": pro_users,
        "free_users": total_users - pro_users,
        "active_today": active_today,
        "total_codes": total_codes,
        "used_codes": used_codes,
        "unused_codes": total_codes - used_codes,
        "generated_pages": len(html_files),
        "generated_sites": len(zip_files),
    }

@router.post("/admin/generate-codes")
async def admin_generate_codes(request: Request, admin: dict = Depends(require_admin)):
    """管理员批量生成激活码"""
    body = await request.json()
    
    plan_type = body.get("plan", "monthly")
    count = min(body.get("count", 1), 100)
    
    if plan_type not in ("monthly", "yearly"):
        raise HTTPException(400, "plan 只能是 monthly 或 yearly")
    
    codes = _generate_code(plan_type, count)
    
    return {
        "success": True,
        "plan_type": plan_type,
        "codes": codes,
        "count": len(codes),
    }

@router.get("/admin/codes")
async def admin_list_codes(admin: dict = Depends(require_admin)):
    """管理员查看所有激活码"""
    codes = _load_codes()
    return sorted(codes.values(), key=lambda c: c.get("created_at", ""), reverse=True)

@router.get("/admin/users")
async def admin_list_users(admin: dict = Depends(require_admin)):
    """管理员查看所有用户"""
    users = _load_users()
    result = []
    for u in users.values():
        plan = "pro" if _is_pro(u) else "free"
        result.append({
            "uid": u["uid"],
            "username": u.get("username", ""),
            "email": u.get("email", ""),
            "plan": plan,
            "pro_expire": u.get("pro_expire"),
            "usage_today": _get_daily_usage(u),
            "daily_limit": FREE_DAILY_LIMIT if plan == "free" else -1,
            "history_count": len(u.get("history", [])),
            "created_at": u.get("created_at"),
        })
    return sorted(result, key=lambda u: u.get("created_at", ""), reverse=True)

@router.delete("/admin/users/{uid}")
async def admin_delete_user(uid: str, admin: dict = Depends(require_admin)):
    """管理员删除用户"""
    users = _load_users()
    if uid not in users:
        raise HTTPException(404, "用户不存在")
    del users[uid]
    _save_users(users)
    return {"success": True, "message": "用户已删除"}

@router.put("/admin/users/{uid}/plan")
async def admin_update_user_plan(uid: str, request: Request, admin: dict = Depends(require_admin)):
    """管理员修改用户方案"""
    body = await request.json()
    new_plan = body.get("plan")
    days = body.get("days", 30)
    
    if new_plan not in ("free", "pro"):
        raise HTTPException(400, "plan 只能是 free 或 pro")
    
    users = _load_users()
    if uid not in users:
        raise HTTPException(404, "用户不存在")
    
    if new_plan == "pro":
        base = datetime.now()
        current_expire = users[uid].get("pro_expire")
        if current_expire:
            try:
                existing = datetime.fromisoformat(current_expire)
                if existing > base:
                    base = existing
            except Exception:
                pass
        users[uid]["pro_expire"] = (base + timedelta(days=days)).isoformat()
        users[uid]["plan"] = "pro"
    else:
        users[uid]["plan"] = "free"
        users[uid]["pro_expire"] = None
    
    _save_users(users)
    return {"success": True, "plan": users[uid]["plan"], "pro_expire": users[uid].get("pro_expire")}

@router.get("/admin/pages")
async def admin_list_pages(admin: dict = Depends(require_admin)):
    """管理员查看所有生成的页面"""
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
    """管理员删除生成的页面"""
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
    """清理过期文件和无效数据"""
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
