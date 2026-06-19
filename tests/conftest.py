"""pytest 配置 — 共享 fixtures"""
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 测试环境用 SQLite 内存数据库
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from core.database import Base, get_db
from core.models import Tenant, User


@pytest.fixture(scope="session")
def engine():
    """测试用引擎（内存 SQLite）"""
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)


@pytest.fixture
def db_session(engine):
    """每个测试用例独立的数据库会话"""
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def default_tenant(db_session):
    """创建默认租户"""
    tenant = Tenant(name="测试企业", slug="test-tenant", plan="free")
    db_session.add(tenant)
    db_session.commit()
    return tenant


@pytest.fixture
def admin_user(db_session, default_tenant):
    """创建管理员用户"""
    import hashlib, secrets
    salt = secrets.token_hex(16)
    pw_hash = hashlib.sha256(("admin123" + salt).encode()).hexdigest()
    user = User(
        tenant_id=default_tenant.id,
        email="admin@test.com",
        username="admin",
        password_hash=pw_hash,
        password_salt=salt,
        role="admin",
    )
    db_session.add(user)
    db_session.commit()
    return user
