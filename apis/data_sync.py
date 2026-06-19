"""
data_sync — 数据持久化同步器

Render免费实例每次部署重置data/目录。
本模块在写入本地JSON后，同步推送到GitHub私有仓库的data/分支，
启动时从GitHub拉取最新数据恢复。

策略：本地优先 + GitHub备份
- 每次写入data/*.json后，延迟3秒批量同步到GitHub
- 启动时如果data/为空，从GitHub拉取
- 冲突解决：以时间戳较新的为准
"""
import os, json, time, logging, base64, ssl, threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger("data_sync")

# GitHub配置
OWNER = "SG06231219-boop"
REPO = "auto-site-builder"
DATA_BRANCH = "data"  # 独立分支存数据，不污染main
DATA_DIR = Path("data")

_ctx = ssl.create_default_context()

# 清除代理
for k in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
    os.environ.pop(k, None)


def _get_pat() -> Optional[str]:
    """从git credential获取PAT"""
    try:
        import subprocess
        r = subprocess.run(
            ["git", "credential", "fill"],
            input=b"protocol=https\nhost=github.com\n\n",
            capture_output=True, timeout=10
        )
        cred = {}
        for line in r.stdout.decode().split("\n"):
            if "=" in line:
                k2, v = line.split("=", 1)
                cred[k2] = v
        return cred.get("password")
    except Exception:
        return None


def _api(method: str, path: str, data=None, pat: str = None):
    """GitHub API调用"""
    if not pat:
        return None, {"error": "no PAT"}
    import urllib.request, urllib.error
    url = f"https://api.github.com{path}"
    headers = {
        "Authorization": f"token {pat}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, context=_ctx, timeout=30)
        if resp.status == 204:
            return resp.status, {}
        return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode())
        except Exception:
            err = {"message": str(e)}
        return e.code, err
    except Exception as e:
        return 0, {"error": str(e)}


# ── 批量同步（延迟合并写入）──
_pending_files: set = set()
_sync_lock = threading.Lock()
_sync_timer: Optional[threading.Timer] = None
_DEBOUNCE_SEC = 5  # 5秒内合并多次写入


def mark_dirty(filename: str):
    """标记文件需要同步（延迟批量处理）"""
    global _sync_timer
    with _sync_lock:
        _pending_files.add(filename)
    # 重置定时器
    if _sync_timer:
        _sync_timer.cancel()
    _sync_timer = threading.Timer(_DEBOUNCE_SEC, _do_sync)
    _sync_timer.daemon = True
    _sync_timer.start()


def _do_sync():
    """批量推送脏文件到GitHub"""
    global _pending_files
    with _sync_lock:
        files = _pending_files.copy()
        _pending_files.clear()

    if not files:
        return

    pat = _get_pat()
    if not pat:
        logger.debug("无PAT，跳过数据同步")
        return

    # 确保data分支存在
    code, _ = _api("GET", f"/repos/{OWNER}/{REPO}/branches/{DATA_BRANCH}", pat=pat)
    if code != 200:
        # 创建data分支（从main的HEAD）
        code, main_data = _api("GET", f"/repos/{OWNER}/{REPO}/git/ref/heads/main", pat=pat)
        if code == 200 and "object" in main_data:
            sha = main_data["object"]["sha"]
            _api("POST", f"/repos/{REPO}/git/refs", {
                "ref": f"refs/heads/{DATA_BRANCH}",
                "sha": sha,
            }, pat=pat)
            logger.info(f"创建data分支")

    synced = 0
    for fname in files:
        local_path = DATA_DIR / fname
        if not local_path.exists():
            continue
        content = local_path.read_bytes()
        # 获取远程SHA
        remote_path = f"data/{fname}"
        code, remote = _api("GET", f"/repos/{OWNER}/{REPO}/contents/{remote_path}?ref={DATA_BRANCH}", pat=pat)
        sha = remote.get("sha") if code == 200 else None

        payload = {
            "message": f"sync: {fname}",
            "branch": DATA_BRANCH,
            "content": base64.b64encode(content).decode(),
        }
        if sha:
            payload["sha"] = sha

        code, _ = _api("PUT", f"/repos/{OWNER}/{REPO}/contents/{remote_path}", payload, pat=pat)
        if code in (200, 201):
            synced += 1
        else:
            logger.warning(f"同步{fname}失败: {code}")

    if synced:
        logger.info(f"同步{synced}/{len(files)}个数据文件到GitHub")


def pull_from_github():
    """启动时从GitHub拉取数据恢复（仅当本地data/为空时）"""
    # 检查是否有本地数据
    local_jsons = list(DATA_DIR.glob("*.json"))
    local_sizes = sum(f.stat().st_size for f in local_jsons)
    if local_sizes > 100:  # 本地有实质数据，不覆盖
        logger.info(f"本地有{len(local_jsons)}个数据文件({local_sizes}B)，跳过拉取")
        return

    pat = _get_pat()
    if not pat:
        logger.info("无PAT，跳过数据拉取")
        return

    # 列出data分支的所有data/文件
    code, result = _api("GET", f"/repos/{OWNER}/{REPO}/contents/data?ref={DATA_BRANCH}", pat=pat)
    if code != 200 or not isinstance(result, list):
        logger.info(f"data分支无数据或不存在(code={code})")
        return

    DATA_DIR.mkdir(exist_ok=True)
    pulled = 0
    for item in result:
        if item.get("type") != "file" or not item["name"].endswith(".json"):
            continue
        # 下载文件内容
        code, file_data = _api("GET", f"/repos/{OWNER}/{REPO}/contents/{item['path']}?ref={DATA_BRANCH}", pat=pat)
        if code == 200 and "content" in file_data:
            try:
                content = base64.b64decode(file_data["content"])
                (DATA_DIR / item["name"]).write_bytes(content)
                pulled += 1
            except Exception as e:
                logger.warning(f"拉取{item['name']}失败: {e}")

    if pulled:
        logger.info(f"从GitHub恢复{pulled}个数据文件")


# ── 启动时自动拉取 ──
def init():
    """应用启动时调用，恢复数据"""
    try:
        pull_from_github()
    except Exception as e:
        logger.warning(f"数据恢复失败: {e}")


# ── 定期全量同步（每小时） ──
def start_periodic_sync(interval_sec: int = 3600):
    """启动定期全量同步"""
    def _periodic():
        while True:
            time.sleep(interval_sec)
            try:
                # 标记所有JSON为脏
                for f in DATA_DIR.glob("*.json"):
                    mark_dirty(f.name)
            except Exception as e:
                logger.warning(f"定期同步失败: {e}")

    t = threading.Thread(target=_periodic, daemon=True)
    t.start()
    logger.info(f"启动定期数据同步(间隔{interval_sec}s)")
