"""
core.database — SQLAlchemy 数据库引擎 + 会话管理

支持：
- SQLite（单租户/本地开发，零配置）
- PostgreSQL（多租户/生产环境，通过 DATABASE_URL 切换）
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Generator, AsyncGenerator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from sqlalchemy.pool import StaticPool

# ── 数据库URL ──────────────────────────────────────
# 生产：DATABASE_URL=postgresql://user:pass@host:5432/dbname
# 开发：默认SQLite，零配置
DATABASE_URL = os.environ.get("DATABASE_URL", "")

if not DATABASE_URL:
    # 本地开发：SQLite
    DB_DIR = Path(__file__).parent.parent / "data"
    DB_DIR.mkdir(exist_ok=True)
    DB_PATH = DB_DIR / "sg_builder.db"
    DATABASE_URL = f"sqlite:///{DB_PATH}"
    _IS_SQLITE = True
elif DATABASE_URL.startswith("sqlite"):
    _IS_SQLITE = True
else:
    _IS_SQLITE = False

# ── 引擎 ────────────────────────────────────────────
_engine_kwargs = {}
if _IS_SQLITE:
    _engine_kwargs.update({
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,  # SQLite单连接
    })
else:
    _engine_kwargs.update({
        "pool_size": 5,
        "max_overflow": 10,
        "pool_pre_ping": True,  # 自动重连
    })

engine = create_engine(DATABASE_URL, **_engine_kwargs)

# SQLite WAL模式（并发读写性能）
if _IS_SQLITE:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# ── 会话 ────────────────────────────────────────────
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """所有模型的基类"""
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖注入：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """创建所有表（首次启动/开发环境用，生产用Alembic迁移）"""
    # 确保所有模型被导入
    import core.models  # noqa: F401
    Base.metadata.create_all(bind=engine)


def get_db_info() -> dict:
    """返回数据库信息（health check用）"""
    return {
        "url": DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL,
        "type": "sqlite" if _IS_SQLITE else "postgresql",
    }
