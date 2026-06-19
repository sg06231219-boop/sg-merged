"""简单的文件锁，防止并发写JSON时数据丢失"""
import threading
import json
from pathlib import Path
from functools import wraps

_locks = {}
_global_lock = threading.Lock()

def _get_lock(path: str):
    with _global_lock:
        if path not in _locks:
            _locks[path] = threading.Lock()
        return _locks[path]

def safe_read_json(path: Path, default=None):
    """线程安全读取JSON"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default if default is not None else {}

def safe_write_json(path: Path, data):
    """线程安全写入JSON，加锁防竞态"""
    lock = _get_lock(str(path))
    with lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
