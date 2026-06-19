"""
UniPulse Router — AI选校报告工具，集成到SG智能建站
原独立应用 server.py → FastAPI Router，前缀 /api/v1/unipulse
认证系统保持独立（自有session token），不耦合SG auth
"""
import sqlite3, json, hashlib, secrets, threading, uuid, time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends, Security, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field


# ── AI报告限流 ──
_ai_report_attempts = {}

def _check_ai_report_rate(ip: str):
    import time
    now = time.time()
    attempts = _ai_report_attempts.get(ip, [])
    attempts = [t for t in attempts if now - t < 3600]
    if len(attempts) >= 3:
        raise HTTPException(429, "AI报告生成次数已达上限，请1小时后再试")
    _ai_report_attempts[ip] = attempts

router = APIRouter(prefix="/unipulse", tags=["UniPulse 选校报告"])

# ── 路径 ────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent.parent  # auto_site_builder/
DB_PATH = ROOT / "data" / "unipulse.db"
STATIC_UNIPULSE = ROOT / "static" / "unipulse"

# ── Auth（UniPulse 自有认证，独立于 SG）─────────────────
security = HTTPBearer(auto_error=False)


def hash_pw(pwd: str) -> str:
    return hashlib.sha256(pwd.encode()).hexdigest()


def _get_db() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise HTTPException(500, "UniPulse 数据库未初始化，请确认 data/unipulse.db 存在")
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def make_token(db, user_id: int) -> str:
    token = secrets.token_hex(32)
    exp = (datetime.now() + timedelta(days=7)).isoformat()
    db.execute("INSERT INTO sessions(token, user_id, expires_at) VALUES(?,?,?)",
               (token, user_id, exp))
    db.commit()
    return token


def get_current_user(
    creds: HTTPAuthorizationCredentials = Security(security)
):
    if not creds:
        return None
    db = _get_db()
    row = db.execute(
        "SELECT user_id FROM sessions WHERE token=? AND expires_at > datetime('now')",
        (creds.credentials,)
    ).fetchone()
    if not row:
        db.close()
        return None
    user = db.execute(
        "SELECT id, username, email, role FROM users WHERE id=?", (row['user_id'],)
    ).fetchone()
    db.close()
    return dict(user) if user else None


def require_user(user=Depends(get_current_user)) -> dict:
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    return user


def require_admin(user=Depends(get_current_user)) -> dict:
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    db = _get_db()
    row = db.execute("SELECT role FROM users WHERE id=?", (user['id'],)).fetchone()
    db.close()
    if not row or row['role'] != 'admin':
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


# ── Pydantic Models ─────────────────────────────────────

class CreatePostBody(BaseModel):
    title: str = Field(..., max_length=100)
    category: str = "全部话题"
    content: str
    tags: list = Field(default_factory=list)
    uni_id: Optional[int] = None
    program_name: Optional[str] = None


class CreateCommentBody(BaseModel):
    text: str = Field(..., min_length=1)


class RegisterBody(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    email: str
    password: str = Field(..., min_length=6)


class LoginBody(BaseModel):
    email: str
    password: str


# ── Helpers ─────────────────────────────────────────────

def row_to_dict(row) -> dict:
    return dict(row) if row else None


def parse_json_field(v):
    if v is None:
        return None
    if isinstance(v, (dict, list)):
        return v
    try:
        return json.loads(v)
    except Exception:
        return v


# ════════════════════════════════════════════════════════
#  Auth API
# ════════════════════════════════════════════════════════

@router.post("/auth/register")
def auth_register(body: RegisterBody):
    db = _get_db()
    if db.execute("SELECT 1 FROM users WHERE email=?", (body.email,)).fetchone():
        db.close()
        raise HTTPException(400, "邮箱已被注册")
    if db.execute("SELECT 1 FROM users WHERE username=?", (body.username,)).fetchone():
        db.close()
        raise HTTPException(400, "用户名已被占用")
    pw_hash = hash_pw(body.password)
    cur = db.execute("INSERT INTO users(username,email,password_hash) VALUES(?,?,?)",
                     (body.username, body.email, pw_hash))
    db.commit()
    user_id = cur.lastrowid
    token = make_token(db, user_id)
    user = db.execute("SELECT id,username,email FROM users WHERE id=?", (user_id,)).fetchone()
    db.close()
    return {"token": token, "user": dict(user)}


@router.post("/auth/login")
def auth_login(body: LoginBody):
    db = _get_db()
    row = db.execute("SELECT id,username,email,password_hash FROM users WHERE email=?",
                     (body.email,)).fetchone()
    if not row or hash_pw(body.password) != row['password_hash']:
        db.close()
        raise HTTPException(401, "邮箱或密码错误")
    token = make_token(db, row['id'])
    db.close()
    return {"token": token, "user": {"id": row['id'], "username": row['username'], "email": row['email']}}


@router.get("/auth/me")
def auth_me(user: dict = Depends(require_user)):
    return user


@router.post("/auth/logout")
def auth_logout(creds: HTTPAuthorizationCredentials = Security(security)):
    if creds:
        db = _get_db()
        db.execute("DELETE FROM sessions WHERE token=?", (creds.credentials,))
        db.commit()
        db.close()
    return {"ok": True}


# ════════════════════════════════════════════════════════
#  University API
# ════════════════════════════════════════════════════════

@router.get("/universities")
def list_universities(
    search: str = Query(""),
    region: str = Query("all"),
    country: str = Query(""),
    page: int = Query(1, ge=1),
    size: int = Query(30, ge=1, le=100),
):
    db = _get_db()
    q = "SELECT * FROM universities WHERE 1=1"
    params = []
    if region and region != "all":
        q += " AND region = ?"
        params.append(region)
    if country:
        q += " AND country = ?"
        params.append(country)
    if search:
        q += " AND (cn LIKE ? OR name LIKE ? OR description LIKE ? OR loc LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s, s])
    cnt_q = q.replace("SELECT *", "SELECT COUNT(*)")
    total = db.execute(cnt_q, params).fetchone()[0]
    q += " ORDER BY rank ASC LIMIT ? OFFSET ?"
    params.extend([size, (page - 1) * size])
    rows = db.execute(q, params).fetchall()
    result = []
    for r in rows:
        d = row_to_dict(r)
        d['metrics'] = parse_json_field(d['metrics'])
        d['tags'] = parse_json_field(d['tags'])
        result.append(d)
    db.close()
    return {"total": total, "page": page, "size": size, "items": result}


@router.get("/universities/{uni_id}")
def get_university(uni_id: int):
    db = _get_db()
    r = db.execute("SELECT * FROM universities WHERE id = ?", (uni_id,)).fetchone()
    if not r:
        db.close()
        raise HTTPException(404, "高校不存在")
    d = row_to_dict(r)
    d['metrics'] = parse_json_field(d['metrics'])
    d['tags'] = parse_json_field(d['tags'])
    progs = db.execute("SELECT * FROM uni_programs WHERE uni_id=?", (uni_id,)).fetchall()
    d['programs'] = [dict(p) for p in progs]
    db.close()
    return d


@router.get("/universities/{uni_id}/programs")
def get_uni_programs(uni_id: int):
    db = _get_db()
    rows = db.execute("SELECT * FROM uni_programs WHERE uni_id=?", (uni_id,)).fetchall()
    db.close()
    return [dict(r) for r in rows]


# ════════════════════════════════════════════════════════
#  Employment / Majors API
# ════════════════════════════════════════════════════════

@router.get("/majors/overview")
def majors_overview():
    db = _get_db()
    rows = db.execute("""
        SELECT program_name,
               COUNT(*) as uni_count,
               ROUND(AVG(salary_avg)) as avg_salary,
               ROUND(AVG(salary_entry)) as avg_entry,
               ROUND(AVG(employment_rate),1) as avg_employment,
               ROUND(AVG(pressure),1) as avg_pressure,
               ROUND(AVG(prospects),1) as avg_prospects
        FROM uni_programs
        GROUP BY program_name
        ORDER BY avg_salary DESC
    """).fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.get("/majors/{program_name}")
def get_major_detail(program_name: str):
    db = _get_db()
    rows = db.execute("""
        SELECT up.*, u.cn as uni_cn, u.name as uni_name, u.country, u.rank
        FROM uni_programs up
        JOIN universities u ON up.uni_id = u.id
        WHERE up.program_name = ?
        ORDER BY up.salary_avg DESC
    """, (program_name,)).fetchall()
    db.close()
    if not rows:
        raise HTTPException(404, f"未找到专业「{program_name}」的数据")
    return [dict(r) for r in rows]


@router.get("/majors")
def list_majors():
    db = _get_db()
    rows = db.execute("SELECT DISTINCT program_name FROM uni_programs ORDER BY program_name").fetchall()
    db.close()
    return [r['program_name'] for r in rows]


# ════════════════════════════════════════════════════════
#  Ranking API
# ════════════════════════════════════════════════════════

@router.get("/rankings")
def get_rankings(dimension: str = Query("academic")):
    valid = {'academic', 'research', 'reputation', 'campus', 'support', 'international', 'value', 'career'}
    if dimension not in valid:
        raise HTTPException(400, f"无效维度，可选: {valid}")
    db = _get_db()
    rows = db.execute("SELECT id,cn,name,country,metrics FROM universities").fetchall()
    result = []
    for r in rows:
        d = row_to_dict(r)
        metrics = parse_json_field(d['metrics'])
        d['dim_value'] = metrics.get(dimension)
        d.pop('metrics', None)
        result.append(d)
    result.sort(key=lambda x: x.get('dim_value') or 0, reverse=True)
    db.close()
    return result


@router.get("/dimensions")
def get_dimensions():
    return [
        {"key": "academic", "label": "学术水平", "weight": 25},
        {"key": "research", "label": "科研产出", "weight": 20},
        {"key": "reputation", "label": "行业声誉", "weight": 15},
        {"key": "campus", "label": "校园环境", "weight": 10},
        {"key": "support", "label": "学生关怀", "weight": 10},
        {"key": "international", "label": "国际化", "weight": 10},
        {"key": "value", "label": "性价比", "weight": 5},
        {"key": "career", "label": "就业前景", "weight": 5},
    ]


# ════════════════════════════════════════════════════════
#  Programs API
# ════════════════════════════════════════════════════════

@router.get("/programs")
def get_programs():
    db = _get_db()
    rows = db.execute("SELECT * FROM programs").fetchall()
    result = []
    for r in rows:
        d = row_to_dict(r)
        d['univs'] = parse_json_field(d['ranking'])
        d.pop('ranking', None)
        result.append(d)
    db.close()
    return result


# ════════════════════════════════════════════════════════
#  Forum API
# ════════════════════════════════════════════════════════

@router.get("/forum/categories")
def get_forum_categories():
    db = _get_db()
    rows = db.execute("SELECT category as cat, COUNT(*) as count FROM forum_posts GROUP BY category").fetchall()
    cats = [
        {"key": "all", "label": "🔥 全部", "count": 0},
        {"key": "选校咨询", "label": "🏫 选校咨询", "count": 0},
        {"key": "专业对比", "label": "📊 专业对比", "count": 0},
        {"key": "就业前景", "label": "💼 就业前景", "count": 0},
        {"key": "留学申请", "label": "✈️ 留学申请", "count": 0},
        {"key": "考研交流", "label": "📖 考研交流", "count": 0},
        {"key": "校园生活", "label": "🏠 校园生活", "count": 0},
        {"key": "奖学金", "label": "💰 奖学金", "count": 0},
        {"key": "实习经验", "label": "🏢 实习经验", "count": 0},
    ]
    total = 0
    cat_map = {r['cat']: r['count'] for r in rows}
    for c in cats:
        cnt = cat_map.get(c['key'], 0)
        c['count'] = cnt
        total += cnt
    cats[0]['count'] = total
    db.close()
    return cats


@router.get("/forum/posts")
def list_forum_posts(
    category: str = Query("all"),
    search: str = Query(""),
    uni_id: int = Query(None),
    program_name: str = Query(""),
    sort: str = Query("new"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    db = _get_db()
    q = "SELECT p.* FROM forum_posts p WHERE 1=1"
    params = []
    if category and category != "all":
        q += " AND p.category = ?"
        params.append(category)
    if search:
        q += " AND (p.title LIKE ? OR p.content LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s])
    if uni_id:
        q += " AND p.uni_id = ?"
        params.append(uni_id)
    if program_name:
        q += " AND p.program_name = ?"
        params.append(program_name)
    cnt_q = q.replace("SELECT p.*", "SELECT COUNT(*)")
    total = db.execute(cnt_q, params).fetchone()[0]
    if sort == "hot":
        q += " ORDER BY (p.views + p.likes*3) DESC"
    else:
        q += " ORDER BY p.id DESC"
    q += " LIMIT ? OFFSET ?"
    params.extend([size, (page - 1) * size])
    rows = db.execute(q, params).fetchall()
    result = []
    for r in rows:
        d = row_to_dict(r)
        d['tags'] = parse_json_field(d['tags'])
        d['replies'] = db.execute("SELECT COUNT(*) FROM forum_comments WHERE post_id=?", (d['id'],)).fetchone()[0]
        if d.get('uni_id'):
            uni = db.execute("SELECT cn FROM universities WHERE id=?", (d['uni_id'],)).fetchone()
            d['uni_cn'] = uni['cn'] if uni else None
        result.append(d)
    db.close()
    return {"total": total, "page": page, "size": size, "items": result}


@router.get("/forum/posts/{post_id}")
def get_forum_post(post_id: int):
    db = _get_db()
    post = db.execute("SELECT * FROM forum_posts WHERE id = ?", (post_id,)).fetchone()
    if not post:
        db.close()
        raise HTTPException(404, "帖子不存在")
    db.execute("UPDATE forum_posts SET views = views + 1 WHERE id = ?", (post_id,))
    db.commit()
    comments = db.execute("SELECT * FROM forum_comments WHERE post_id = ? ORDER BY id ASC", (post_id,)).fetchall()
    result = row_to_dict(post)
    result['tags'] = parse_json_field(result['tags'])
    result['comments'] = [row_to_dict(c) for c in comments]
    if result.get('uni_id'):
        uni = db.execute("SELECT cn FROM universities WHERE id=?", (result['uni_id'],)).fetchone()
        result['uni_cn'] = uni['cn'] if uni else None
    db.close()
    return result


@router.post("/forum/posts")
def create_post(data: CreatePostBody, user: dict = Depends(require_user)):
    db = _get_db()
    tags = json.dumps(data.tags, ensure_ascii=False)
    cur = db.execute(
        "INSERT INTO forum_posts(user_id,title,category,author,content,tags,uni_id,program_name) VALUES(?,?,?,?,?,?,?,?)",
        (user['id'], data.title, data.category, user['username'], data.content, tags,
         data.uni_id, data.program_name))
    db.commit()
    new_id = cur.lastrowid
    db.close()
    return {"id": new_id, "message": "✅ 发帖成功！"}


@router.post("/forum/posts/{post_id}/like")
def like_post(post_id: int):
    db = _get_db()
    if not db.execute("SELECT 1 FROM forum_posts WHERE id=?", (post_id,)).fetchone():
        db.close()
        raise HTTPException(404, "帖子不存在")
    db.execute("UPDATE forum_posts SET likes = likes + 1 WHERE id = ?", (post_id,))
    db.commit()
    new_likes = db.execute("SELECT likes FROM forum_posts WHERE id=?", (post_id,)).fetchone()[0]
    db.close()
    return {"likes": new_likes}


@router.post("/forum/posts/{post_id}/comments")
def create_comment(post_id: int, data: CreateCommentBody, user: dict = Depends(require_user)):
    db = _get_db()
    if not db.execute("SELECT 1 FROM forum_posts WHERE id=?", (post_id,)).fetchone():
        db.close()
        raise HTTPException(404, "帖子不存在")
    cur = db.execute(
        "INSERT INTO forum_comments(post_id,user_id,author,text) VALUES(?,?,?,?)",
        (post_id, user['id'], user['username'], data.text))
    db.commit()
    new_id = cur.lastrowid
    db.close()
    return {"id": new_id, "message": "✅ 回复成功！"}


@router.post("/forum/comments/{comment_id}/like")
def like_comment(comment_id: int):
    db = _get_db()
    if not db.execute("SELECT 1 FROM forum_comments WHERE id=?", (comment_id,)).fetchone():
        db.close()
        raise HTTPException(404, "评论不存在")
    db.execute("UPDATE forum_comments SET likes = likes + 1 WHERE id = ?", (comment_id,))
    db.commit()
    new_likes = db.execute("SELECT likes FROM forum_comments WHERE id=?", (comment_id,)).fetchone()[0]
    db.close()
    return {"likes": new_likes}


@router.get("/forum/hot")
def get_hot_topics(limit: int = Query(10)):
    db = _get_db()
    rows = db.execute("SELECT id, title, views, likes, category FROM forum_posts ORDER BY (views + likes*3) DESC LIMIT ?",
                      (limit,)).fetchall()
    result = [dict(r) for r in rows]
    db.close()
    return result


# ════════════════════════════════════════════════════════
#  AI Report Generation
# ════════════════════════════════════════════════════════

report_jobs: dict = {}
report_lock = threading.Lock()


def generate_ai_report(report_id: str, gpa: float, major: str, regions: list, budget: str, language: str):
    """后台线程：基于规则 + 数据库高校数据生成选校报告"""
    db = _get_db()
    rows = db.execute("SELECT id,name,cn,country,loc,rank,description,tags FROM universities").fetchall()
    db.close()

    results = []
    for u in rows:
        d = dict(u)
        score = 0
        reasons = []
        rank = d.get('rank', 999)
        if rank <= 10:
            score += 40
        elif rank <= 20:
            score += 30
        elif rank <= 50:
            score += 20
        elif rank <= 100:
            score += 10
        else:
            score += 5
        reasons.append("QS排名" + str(rank))

        desc_lower = (d.get('description') or '').lower()
        major_lower = major.lower()
        major_categories = {
            '计算机/软件': ['cs', 'computer', '软件', '计算机', '编程', 'ai', '人工智能', '信息科学', '数据', '算法',
                         'machine learning', 'software', '信息技术'],
            '商科': ['business', 'management', 'economics', 'finance', '商', '管理', '经济', '金融', '会计',
                    'marketing', 'mba'],
            '工程': ['engineering', 'mechanical', 'electrical', '工科', '工程', '制造', '电子', '机械', '土木',
                   '建筑', 'civil', 'aerospace', '航空'],
            '医学/健康': ['medicine', 'medical', 'health', '临床', '医学', '健康', '护理', '药学', 'nursing',
                      'pharmacy'],
            '艺术/设计': ['art', 'design', 'architecture', 'music', '艺术', '设计', '音乐', '建筑', '美术',
                      'fashion', '创意'],
            '法律': ['law', 'legal', '法学', '法律', '司法', 'justice'],
            '理科': ['physics', 'chemistry', 'biology', 'science', '物理', '化学', '生物', '数学', '统计',
                   'mathematics', 'statistics', '自然'],
        }
        user_cat = None
        for cat, keywords in major_categories.items():
            if any(k in major_lower for k in keywords):
                user_cat = (cat, keywords)
                break
        if user_cat:
            cat_name, cat_keywords = user_cat
            if any(k in desc_lower for k in cat_keywords):
                score += 20
                reasons.append(cat_name + "方向突出")
            else:
                score += 10
                reasons.append("综合实力强")

        budget_ok = False
        if budget in ['0-20万', '20万以下']:
            budget_ok = d.get('country', '') in ['中国', '日本', '新加坡', '韩国', '马来西亚']
        elif budget in ['20-50万']:
            budget_ok = d.get('country', '') in ['英国', '澳洲', '加拿大', '欧洲']
        elif budget in ['50万以上']:
            budget_ok = True
        if budget_ok:
            score += 20
        else:
            reasons.append("⚠️ 费用可能超标")

        if regions and regions != ['不限']:
            if d.get('region', '') in regions or d.get('country', '') in regions:
                score += 15

        results.append({
            'id': d['id'], 'name': d['name'], 'cn': d['cn'],
            'country': d.get('country', ''), 'loc': d.get('loc', ''),
            'rank': rank, 'score': min(score, 100),
            'match_reasons': reasons[:4],
            'tuition_hint': d.get('country', '')
        })

    results.sort(key=lambda x: x['score'], reverse=True)
    report = {
        'report_id': report_id,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'input': {'gpa': gpa, 'major': major, 'regions': regions, 'budget': budget, 'language': language},
        'summary': f"基于您的{gpa} GPA + {major}专业偏好，为您精选{len(results)}所院校",
        'top_recommendations': results[:3],
        'other_options': results[3:10],
        'total_matched': len(results),
        'ai_notice': "本报告基于公开数据综合分析，仅供参考。"
    }
    with report_lock:
        report_jobs[report_id] = {'status': 'done', 'result': report}


@router.post("/ai/report")
async def create_ai_report(
    background_tasks: BackgroundTasks,
    gpa: float = Query(..., ge=0, le=5),
    major: str = Query("..."),
    regions: str = Query("不限"),
    budget: str = Query("不限"),
    language: str = Query("待定"),
):
    if not major.strip():
        raise HTTPException(400, "请填写意向专业")
    report_id = str(uuid.uuid4())[:8]
    region_list = [r.strip() for r in regions.split(',') if r.strip()]
    with report_lock:
        report_jobs[report_id] = {'status': 'processing', 'result': None}
    background_tasks.add_task(generate_ai_report, report_id, gpa, major, region_list, budget, language)
    return {'report_id': report_id, 'status': 'processing', 'poll_url': '/api/v1/unipulse/ai/report/' + report_id}


@router.get("/ai/report/{report_id}")
async def get_ai_report(report_id: str):
    with report_lock:
        job = report_jobs.get(report_id)
    if not job:
        raise HTTPException(404, "报告不存在或已过期")
    if job['status'] == 'processing':
        return {'status': 'processing', 'progress': '50%'}
    return {'status': 'done', 'result': job['result']}


@router.get("/ai/wait/{report_id}")
async def wait_ai_report(report_id: str, timeout: int = Query(30)):
    for _ in range(timeout):
        with report_lock:
            job = report_jobs.get(report_id)
        if not job:
            raise HTTPException(404, "报告不存在")
        if job['status'] == 'done':
            return job['result']
        time.sleep(1)
    raise HTTPException(504, "报告生成超时，请稍后重试")


# ════════════════════════════════════════════════════════
#  Countries / Regions
# ════════════════════════════════════════════════════════

@router.get("/countries")
def list_countries():
    db = _get_db()
    rows = db.execute("SELECT DISTINCT country FROM universities ORDER BY country").fetchall()
    db.close()
    return [r['country'] for r in rows]


@router.get("/regions")
def list_regions():
    db = _get_db()
    rows = db.execute("SELECT DISTINCT region FROM universities WHERE region IS NOT NULL ORDER BY region").fetchall()
    db.close()
    return [r['region'] for r in rows]


# ════════════════════════════════════════════════════════
#  Admin API（保留管理员功能）
# ════════════════════════════════════════════════════════

@router.get("/admin/stats")
def admin_stats(_: dict = Depends(require_admin)):
    db = _get_db()
    users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    posts = db.execute("SELECT COUNT(*) FROM forum_posts").fetchone()[0]
    comments = db.execute("SELECT COUNT(*) FROM forum_comments").fetchone()[0]
    unis = db.execute("SELECT COUNT(*) FROM universities").fetchone()[0]
    programs_cnt = db.execute("SELECT COUNT(*) FROM programs").fetchone()[0]
    emp_cnt = db.execute("SELECT COUNT(*) FROM uni_programs").fetchone()[0]
    recent = db.execute("SELECT COUNT(*) FROM users WHERE created_at > datetime('now','localtime','-7 days')").fetchone()[0]
    recent_posts = db.execute("SELECT COUNT(*) FROM forum_posts WHERE created_at > datetime('now','localtime','-7 days')").fetchone()[0]
    db.close()
    return {"users": users, "posts": posts, "comments": comments,
            "universities": unis, "programs": programs_cnt, "employment_records": emp_cnt,
            "recent_users": recent, "recent_posts": recent_posts}


@router.get("/admin/users")
def admin_list_users(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
                    _: dict = Depends(require_admin)):
    db = _get_db()
    total = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    rows = db.execute("SELECT id,username,email,role,created_at FROM users ORDER BY id DESC LIMIT ? OFFSET ?",
                      (size, (page - 1) * size)).fetchall()
    db.close()
    return {"total": total, "items": [dict(r) for r in rows]}


@router.put("/admin/users/{user_id}/role")
def admin_set_role(user_id: int, role: str = Query(...), _: dict = Depends(require_admin)):
    if role not in ('user', 'admin'):
        raise HTTPException(400, "role 必须是 user 或 admin")
    db = _get_db()
    if not db.execute("SELECT 1 FROM users WHERE id=?", (user_id,)).fetchone():
        db.close()
        raise HTTPException(404, "用户不存在")
    db.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))
    db.commit()
    db.close()
    return {"ok": True, "user_id": user_id, "role": role}


@router.delete("/admin/users/{user_id}")
def admin_delete_user(user_id: int, _: dict = Depends(require_admin)):
    db = _get_db()
    if not db.execute("SELECT 1 FROM users WHERE id=?", (user_id,)).fetchone():
        db.close()
        raise HTTPException(404, "用户不存在")
    db.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
    db.execute("UPDATE forum_posts SET user_id=NULL, author='[已删除用户]' WHERE user_id=?", (user_id,))
    db.execute("UPDATE forum_comments SET user_id=NULL, author='[已删除用户]' WHERE user_id=?", (user_id,))
    db.execute("DELETE FROM users WHERE id=?", (user_id,))
    db.commit()
    db.close()
    return {"ok": True}


@router.get("/admin/posts")
def admin_list_posts(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
                    _: dict = Depends(require_admin)):
    db = _get_db()
    total = db.execute("SELECT COUNT(*) FROM forum_posts").fetchone()[0]
    rows = db.execute(
        "SELECT p.*, (SELECT COUNT(*) FROM forum_comments WHERE post_id=p.id) as comment_count "
        "FROM forum_posts p ORDER BY p.id DESC LIMIT ? OFFSET ?",
        (size, (page - 1) * size)).fetchall()
    db.close()
    return {"total": total, "items": [dict(r) for r in rows]}


@router.delete("/admin/posts/{post_id}")
def admin_delete_post(post_id: int, _: dict = Depends(require_admin)):
    db = _get_db()
    if not db.execute("SELECT 1 FROM forum_posts WHERE id=?", (post_id,)).fetchone():
        db.close()
        raise HTTPException(404, "帖子不存在")
    db.execute("DELETE FROM forum_comments WHERE post_id=?", (post_id,))
    db.execute("DELETE FROM forum_posts WHERE id=?", (post_id,))
    db.commit()
    db.close()
    return {"ok": True}


@router.get("/health")
def health():
    return {"status": "ok", "module": "UniPulse", "version": "2.0", "universities": 573, "majors": 21, "time": datetime.now().isoformat()}